"""Identity mail: queued in the outbox with the change that needs it, sent over SMTP by the delivery sweep.

The body carries a one-use link, so it is encrypted with outbox-row AAD and never logged.
"""

import contextlib
import smtplib
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

import anyio
from a13n_logging import get_logger
from anyio.to_thread import run_sync
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from a13n_service.infra.crypto import Envelope, KeyRing
from a13n_service.infra.db import Storage, transaction
from a13n_service.infra.ids import new_object_id
from a13n_service.infra.outbox import Claim, enqueue, secret_location, settle
from a13n_service.settings import Mail as MailSettings

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Mail:
    to: str
    subject: str
    text: str


class Mailer(Protocol):
    async def send(self, mail: Mail) -> None:
        """Deliver or raise; the outbox retries with backoff."""
        ...


class _Content(BaseModel):
    subject: str
    text: str


class SmtpMailer:
    """SMTP in a worker thread, bounded as a whole by `timeout` (smtplib bounds only each socket operation).

    At the deadline the connection is shut down, which ends any blocked exchange, so a slow server can neither
    hold a delivery past its outbox claim nor complete the mail after the outbox retried it. A connection still
    opening then is abandoned and shut as soon as it opens.
    """

    def __init__(self, config: MailSettings) -> None:
        self.config = config

    async def send(self, mail: Mail) -> None:
        deadline = time.monotonic() + self.config.timeout
        with anyio.fail_after(self.config.timeout):
            await run_sync(self._send, mail, deadline, abandon_on_cancel=True)

    def _send(self, mail: Mail, deadline: float) -> None:
        config = self.config
        assert config.smtp_host is not None and config.sender is not None
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = config.sender, mail.to, mail.subject
        message.set_content(mail.text)
        context = ssl.create_default_context()
        client = (
            smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=config.timeout, context=context)
            if config.smtp_security == "tls"
            else smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=config.timeout)
        )
        cutoff = threading.Timer(max(0.0, deadline - time.monotonic()), _shut, (client,))
        cutoff.start()
        try:
            with client:
                if config.smtp_security == "starttls":
                    client.starttls(context=context)
                if config.smtp_username is not None and config.smtp_password is not None:
                    client.login(config.smtp_username, config.smtp_password.get_secret_value())
                client.send_message(message)
        finally:
            cutoff.cancel()


def _shut(client: smtplib.SMTP) -> None:
    """End the connection's exchange from another thread; the blocked call then fails."""
    connection = client.sock
    if connection is not None:
        with contextlib.suppress(OSError):
            connection.shutdown(socket.SHUT_RDWR)


def link(public_url: str, path: str, token: str) -> str:
    """Console link carrying the token in the fragment, which browsers never send to a server."""
    return f"{public_url.rstrip('/')}{path}#token={token}"


def queue_mail(
    session: AsyncSession,
    keys: KeyRing,
    config: MailSettings,
    mail: Mail,
    *,
    organization_id: str | None,
    workspace_id: str | None,
    purpose: str,
) -> bool:
    """Stage one mail in the caller's transaction; False when email delivery is not configured."""
    if config.smtp_host is None:
        logger.info("Identity mail not sent: email delivery is not configured", extra={"purpose": purpose})
        return False
    row_id = new_object_id("obx")
    content = _Content(subject=mail.subject, text=mail.text).model_dump_json().encode()
    enqueue(
        session,
        organization_id=organization_id,
        workspace_id=workspace_id,
        kind="email",
        target={"to": mail.to, "purpose": purpose},
        payload={"content": keys.protect(content, secret_location(organization_id, row_id, "payload")).model_dump()},
        row_id=row_id,
    )
    return True


async def deliver_mail(storage: Storage, keys: KeyRing, mailer: Mailer, claimed: Claim) -> None:
    """Outbox handler for `email`: send outside any session, then settle."""
    envelope = Envelope.model_validate(claimed.payload["content"])
    location = secret_location(claimed.organization_id, claimed.id, "payload")
    content = _Content.model_validate_json(keys.reveal(envelope, location))
    await mailer.send(Mail(str(claimed.target["to"]), content.subject, content.text))
    async with transaction(storage) as session:
        await settle(session, claimed, "delivered")
