"""Credential primitives: Argon2id passwords, random secrets, and login sessions and one-use links as tokens.

Every secret is random, returned once and stored only as `secret_hash`; passwords are never looked up by hash.
"""

import secrets
from datetime import timedelta
from typing import Literal

from anyio import CapacityLimiter
from anyio.lowlevel import RunVar
from anyio.to_thread import run_sync
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import Select, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from a13n_service.infra.crypto import secret_hash
from a13n_service.infra.db import now
from a13n_service.infra.ids import new_object_id
from a13n_service.tenancy.tables import ApiKeyRow, PasswordRow, TokenRow

type TokenKind = Literal["session", "password_reset", "email_change"]
type LinkKind = Literal["password_reset", "email_change"]

_TOKEN_PREFIXES: dict[TokenKind, str] = {"session": "ase", "password_reset": "prt", "email_change": "ect"}
_HASHER = PasswordHasher()
# Each Argon2id hash takes tens of milliseconds and 64 MiB. Hashing gets its own small thread limit per event
# loop, like anyio's default one, so a burst of logins cannot occupy the threads other blocking calls share.
_CONCURRENT_HASHES = 2
_HASHING: RunVar[CapacityLimiter] = RunVar("a13n_password_hashing")


def _hashing() -> CapacityLimiter:
    limiter = _HASHING.get(None)
    if limiter is None:
        limiter = CapacityLimiter(_CONCURRENT_HASHES)
        _HASHING.set(limiter)
    return limiter


def new_secret() -> str:
    return secrets.token_urlsafe(32)


async def hash_password(password: str) -> str:
    return await run_sync(_HASHER.hash, password, limiter=_hashing())


async def verify_password(password_hash: str | None, password: str) -> bool:
    """Missing identities still pay for one hash, so timing does not reveal whether an account exists."""
    if password_hash is None:
        await hash_password(password)
        return False
    try:
        return await run_sync(_HASHER.verify, password_hash, password, limiter=_hashing())
    except (VerificationError, InvalidHashError):
        return False


async def set_password(session: AsyncSession, principal_id: str, password_hash: str) -> None:
    await session.execute(
        insert(PasswordRow)
        .values(principal_id=principal_id, hash=password_hash)
        .on_conflict_do_update(index_elements=["principal_id"], set_={"hash": password_hash, "updated_at": func.now()})
    )


async def issue_token(
    session: AsyncSession, principal_id: str, kind: TokenKind, *, seconds: int, data: dict | None = None
) -> tuple[TokenRow, str]:
    secret = new_secret()
    token = TokenRow(
        id=new_object_id(_TOKEN_PREFIXES[kind]),
        principal_id=principal_id,
        kind=kind,
        secret_hash=secret_hash(secret),
        data=data,
        expires_at=await now(session) + timedelta(seconds=seconds),
    )
    session.add(token)
    await session.flush()
    return token, secret


async def issue_link(
    session: AsyncSession, principal_id: str, kind: LinkKind, *, seconds: int, data: dict | None = None
) -> str:
    """A new one-use link's secret; an earlier link of the same kind stops working."""
    await session.execute(
        update(TokenRow)
        .where(TokenRow.principal_id == principal_id, TokenRow.kind == kind, TokenRow.revoked_at.is_(None))
        .values(revoked_at=func.clock_timestamp())
    )
    _, secret = await issue_token(session, principal_id, kind, seconds=seconds, data=data)
    return secret


def _live_link(kind: LinkKind, secret: str) -> Select[tuple[TokenRow]]:
    return select(TokenRow).where(
        TokenRow.secret_hash == secret_hash(secret),
        TokenRow.kind == kind,
        TokenRow.revoked_at.is_(None),
        TokenRow.expires_at > func.clock_timestamp(),
    )


async def find_link(session: AsyncSession, kind: LinkKind, secret: str) -> TokenRow | None:
    """A live one-use link, read without a lock: the cheap check before costly work such as hashing."""
    return await session.scalar(_live_link(kind, secret))


async def consume_link(session: AsyncSession, kind: LinkKind, secret: str) -> TokenRow | None:
    """Lock and revoke a live one-use link; None when unknown, expired or already used."""
    token = await session.scalar(_live_link(kind, secret).with_for_update())
    if token is not None:
        token.revoked_at = await now(session)
    return token


async def revoke_tokens(session: AsyncSession, principal_id: str, *, keep: str | None = None) -> None:
    """End every outstanding login session and one-use link of an account, except the session `keep`."""
    await session.execute(
        update(TokenRow)
        .where(
            TokenRow.principal_id == principal_id,
            TokenRow.revoked_at.is_(None),
            TokenRow.id.is_distinct_from(keep),
        )
        .values(revoked_at=func.clock_timestamp())
    )


async def revoke_api_keys(session: AsyncSession, principal_id: str) -> int:
    revoked = await session.scalars(
        update(ApiKeyRow)
        .where(ApiKeyRow.principal_id == principal_id, ApiKeyRow.revoked_at.is_(None))
        .values(revoked_at=func.clock_timestamp())
        .returning(ApiKeyRow.id)
    )
    return len(revoked.all())
