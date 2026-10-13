"""A connection as its users reach it: resolved in a short session under the caller's authority, as plain values
whose secrets stay encrypted until a transport presents them outside any session."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from a13n_service.infra.errors import disabled
from a13n_service.providers.tools.mcp import McpConfig
from a13n_service.resources.connections.schemas import ConnectorConfig
from a13n_service.resources.connections.tables import ConnectionAuth, ConnectionRow, ConnectionStatus
from a13n_service.resources.providers.service import ResolvedProvider, resolve_provider
from a13n_service.resources.providers.tables import ConnectorProviderRow
from a13n_service.resources.rows import find_row
from a13n_service.tenancy.authorize import ExecutionAuthority, Principal, Verb, WorkspaceScope, authorize


@dataclass(frozen=True, slots=True)
class _Connection:
    id: str
    organization_id: str
    workspace_id: str
    type: str
    version: int
    status: ConnectionStatus
    credential: dict | None = field(repr=False)

    @property
    def scope(self) -> WorkspaceScope:
        return WorkspaceScope(self.organization_id, self.workspace_id)


@dataclass(frozen=True, slots=True)
class McpConnection(_Connection):
    """A Remote MCP server; an `oauth` credential is the client it was granted to, with its tokens."""

    auth: ConnectionAuth
    config: McpConfig
    tokens: dict | None = field(repr=False)
    client_secret: dict | None = field(repr=False)
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class ConnectorConnection(_Connection):
    """A connector app; its credential is the account the serving provider keeps."""

    config: ConnectorConfig
    provider: ResolvedProvider


type ResolvedConnection = McpConnection | ConnectorConnection


async def resolve_connection(
    session: AsyncSession,
    actor: Principal,
    scope: WorkspaceScope,
    connection_id: str,
    *,
    verb: Verb,
    authority: ExecutionAuthority | None = None,
    require_enabled: bool = True,
) -> ResolvedConnection:
    """An enabled connection of the workspace and, for connectors, its usable provider, in a short session.

    Revocation alone reaches a disabled one (`require_enabled=False`), so its credential can still be ended.
    """
    authorize(actor, scope, verb, authority=authority)
    row = await find_row(session, actor, ConnectionRow, scope, connection_id, "read")
    if require_enabled and not row.enabled:
        raise disabled(row.KIND, row.id)
    if row.connector_provider_id is None:
        return McpConnection(
            id=row.id,
            organization_id=row.organization_id,
            workspace_id=row.workspace_id,
            type=row.type,
            version=row.version,
            status=row.status,
            credential=row.credential,
            auth=row.auth,
            config=McpConfig.model_validate(row.config),
            tokens=row.tokens,
            client_secret=row.client_secret,
            expires_at=row.expires_at,
        )
    provider = await resolve_provider(
        session, actor, ConnectorProviderRow, scope, row.connector_provider_id, verb="run", authority=authority
    )
    return ConnectorConnection(
        id=row.id,
        organization_id=row.organization_id,
        workspace_id=row.workspace_id,
        type=row.type,
        version=row.version,
        status=row.status,
        credential=row.credential,
        config=ConnectorConfig.model_validate(row.config),
        provider=provider,
    )
