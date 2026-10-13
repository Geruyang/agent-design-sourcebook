"""The apps a connector provider serves and their actions, for choosing a connection's app and actions."""

from pydantic import BaseModel, JsonValue

from a13n_service.providers.tools import ToolInfo


class ConnectorApp(BaseModel):
    key: str
    name: str
    description: str | None
    logo_url: str | None
    # Set when the provider lists the app but cannot connect it now.
    unavailable_reason: str | None
    # How the provider can authenticate the app's accounts, such as `OAUTH2`; empty when none is usable.
    authentication_methods: list[str]
    # What `ConnectorConfig.setup` accepts for this app.
    setup_schema: dict[str, JsonValue]


class ConnectorAppPage(BaseModel):
    items: list[ConnectorApp]
    next_cursor: str | None


class ConnectorActionPage(BaseModel):
    items: list[ToolInfo]
    next_cursor: str | None
