"""The `expire_credentials` sweep: one bounded SQL-only pass over tokens and invitations that are dead."""

from sqlalchemy import delete, or_, select

from a13n_service.infra.db import Storage, now, transaction
from a13n_service.tenancy.tables import InvitationRow, TokenRow


async def expire_credentials(storage: Storage, *, limit: int) -> int:
    """Delete expired or revoked tokens and unaccepted invitations that can no longer be used. Principals and
    accepted invitations stay for history."""
    async with transaction(storage) as session:
        current = await now(session)
        tokens = select(TokenRow.id).where(or_(TokenRow.expires_at <= current, TokenRow.revoked_at.is_not(None)))
        invitations = select(InvitationRow.id).where(
            InvitationRow.accepted_at.is_(None),
            or_(InvitationRow.expires_at <= current, InvitationRow.revoked_at.is_not(None)),
        )
        removed = 0
        for row, candidates in ((TokenRow, tokens), (InvitationRow, invitations)):
            ids = (await session.scalars(candidates.limit(limit).with_for_update(skip_locked=True))).all()
            if ids:
                await session.execute(delete(row).where(row.id.in_(ids)))
            removed += len(ids)
    return removed
