"""The OAuth 2.1 client of remote MCP servers, on the MCP SDK's discovery rules and models.

A person authorizes through the browser with the authorization-code grant; a confidential client registered in
advance may instead use the client-credentials grant, a machine account that needs no browser.

Plain protocol steps over a host-owned HTTP client (endpoint policy, bounds, no redirects). Persisting a flow,
fencing concurrent use and deciding what an uncertain outcome means belong to the caller.
"""

import base64
from dataclasses import dataclass, field
from urllib.parse import quote, urlencode

import httpx2
from a13n_harness.providers.endpoint_policy import EndpointPolicyError
from mcp.client.auth import OAuthFlowError
from mcp.client.auth.oauth2 import PKCEParameters, check_registration_usable
from mcp.client.auth.utils import (
    build_oauth_authorization_server_metadata_discovery_urls,
    build_protected_resource_metadata_discovery_urls,
    create_client_registration_request,
    create_oauth_metadata_request,
    handle_auth_metadata_response,
    handle_protected_resource_response,
    handle_registration_response,
    issuers_match,
)
from mcp.shared.auth import OAuthClientMetadata, OAuthMetadata, OAuthToken
from mcp.shared.auth_utils import check_resource_allowed, resource_url_from_server_url
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, ValidationError

from a13n_service.providers.tools.mcp import ClientAuthentication, OAuthGrant, OAuthSettings

# Transport failures before a request could be written, so it cannot have taken effect: waiting for a connection
# or establishing one. An endpoint the policy refuses is never dialed either.
_NOT_SENT = (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.PoolTimeout)


class OAuthError(Exception):
    """`code` is safe to store and show; `unknown` means the request may have taken effect upstream."""

    def __init__(self, code: str, *, unknown: bool = False):
        super().__init__(code)
        self.code = code
        self.unknown = unknown


class OAuthClient(BaseModel):
    """What token requests need: kept with a pending flow and then with the credential it produced."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issuer: str
    token_endpoint: str
    revocation_endpoint: str | None
    # RFC 8707 resource indicator of the MCP server.
    resource: str
    client_id: str
    client_secret: str | None = Field(default=None, repr=False)
    authentication: ClientAuthentication
    grant_type: OAuthGrant = "authorization_code"
    # The scope requested; a client-credentials token is requested with it again when it expires.
    scope: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorizationStart:
    client: OAuthClient
    # Where the browser goes; it carries `state` and the PKCE challenge of `verifier`.
    url: str
    verifier: str = field(repr=False)
    # RFC 9207: the server promised to send `iss` with its authorization response.
    iss_required: bool


async def start_authorization(
    http: httpx2.AsyncClient,
    *,
    server_url: str,
    settings: OAuthSettings,
    client_secret: str | None,
    redirect_uri: str,
    state: str,
    client_name: str,
) -> AuthorizationStart:
    """Discover the authorization server, register a client when none is set in advance, add PKCE."""
    server = await _discover(http, server_url, settings)
    metadata = server.metadata
    if "S256" not in (metadata.code_challenge_methods_supported or ()):
        raise OAuthError("pkce_unsupported")
    client_id, authentication = settings.client_id, settings.token_endpoint_auth_method
    if client_id is None:
        request = create_client_registration_request(
            metadata,
            OAuthClientMetadata(
                redirect_uris=[AnyUrl(redirect_uri)],
                token_endpoint_auth_method="none",
                client_name=client_name,
                application_type="web",
                scope=server.scope,
            ),
            str(metadata.issuer),
        )
        try:
            registered = await handle_registration_response(await _send(http, request))
            check_registration_usable(registered)
        except OAuthFlowError:
            raise OAuthError("client_registration_failed") from None
        client_id, client_secret = registered.client_id, registered.client_secret
        authentication = _authentication(registered.token_endpoint_auth_method, client_secret)
    pkce = PKCEParameters.generate()
    query = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": pkce.code_challenge,
        "code_challenge_method": "S256",
        "resource": server.resource,
        **({} if server.scope is None else {"scope": server.scope}),
    }
    endpoint = str(metadata.authorization_endpoint)
    return AuthorizationStart(
        client=server.client(client_id, client_secret, authentication, "authorization_code"),
        url=f"{endpoint}{'&' if '?' in endpoint else '?'}{urlencode(query)}",
        verifier=pkce.code_verifier,
        iss_required=bool(metadata.authorization_response_iss_parameter_supported),
    )


async def request_client_token(
    http: httpx2.AsyncClient, *, server_url: str, settings: OAuthSettings, client_secret: str
) -> tuple[OAuthClient, OAuthToken]:
    """RFC 6749 §4.4: a token for a confidential client registered in advance, obtained without a browser."""
    assert settings.grant_type == "client_credentials" and settings.client_id is not None
    server = await _discover(http, server_url, settings)
    client = server.client(settings.client_id, client_secret, settings.token_endpoint_auth_method, "client_credentials")
    return client, await _client_token(http, client)


def check_issuer(client: OAuthClient, iss: str | None, *, required: bool) -> None:
    """RFC 9207 mix-up defence: a present `iss` must name the issuer exactly; a promised one must be present."""
    if (iss is None and required) or (iss is not None and not issuers_match(iss, client.issuer)):
        raise OAuthError("issuer_mismatch")


async def exchange_code(
    http: httpx2.AsyncClient, client: OAuthClient, *, code: str, verifier: str, redirect_uri: str
) -> OAuthToken:
    return await _token(
        http,
        client,
        {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "code_verifier": verifier},
    )


async def renew_access(http: httpx2.AsyncClient, client: OAuthClient, refresh_token: str | None) -> OAuthToken:
    """A new access token: a client-credentials client asks again; any other presents its refresh token."""
    if client.grant_type == "client_credentials":
        return await _client_token(http, client)
    if refresh_token is None:
        raise OAuthError("refresh_token_missing")
    return await _token(http, client, {"grant_type": "refresh_token", "refresh_token": refresh_token})


async def revoke_token(http: httpx2.AsyncClient, client: OAuthClient, token: str) -> None:
    """RFC 7009; revoking a refresh token also ends the access tokens issued with it."""
    if client.revocation_endpoint is None:
        return
    response = await _post(http, client, client.revocation_endpoint, {"token": token})
    if response.status_code != 200:
        raise OAuthError("revocation_rejected", unknown=response.status_code >= 500)


@dataclass(frozen=True, slots=True)
class _AuthorizationServer:
    metadata: OAuthMetadata
    # RFC 8707 resource indicator of the MCP server.
    resource: str
    scope: str | None

    def client(
        self, client_id: str, secret: str | None, authentication: ClientAuthentication, grant_type: OAuthGrant
    ) -> OAuthClient:
        metadata = self.metadata
        return OAuthClient(
            issuer=str(metadata.issuer),
            token_endpoint=str(metadata.token_endpoint),
            revocation_endpoint=None if metadata.revocation_endpoint is None else str(metadata.revocation_endpoint),
            resource=self.resource,
            client_id=client_id,
            client_secret=secret,
            authentication=authentication,
            grant_type=grant_type,
            scope=self.scope,
        )


async def _discover(http: httpx2.AsyncClient, server_url: str, settings: OAuthSettings) -> _AuthorizationServer:
    """The server's authorization server (RFC 9728, RFC 8414); empty scopes request those the server advertises."""
    resource = resource_url_from_server_url(server_url)
    issuer: str | None = None
    scopes = settings.scopes
    for url in build_protected_resource_metadata_discovery_urls(None, server_url):
        protected = await handle_protected_resource_response(await _send(http, create_oauth_metadata_request(url)))
        if protected is not None:
            if not check_resource_allowed(server_url, str(protected.resource)):
                raise OAuthError("resource_mismatch")
            resource, issuer = str(protected.resource), str(protected.authorization_servers[0])
            scopes = scopes or tuple(protected.scopes_supported or ())
            break
    metadata = await _server_metadata(http, issuer, server_url)
    return _AuthorizationServer(metadata, resource, " ".join(scopes) or None)


async def _server_metadata(http: httpx2.AsyncClient, issuer: str | None, server_url: str) -> OAuthMetadata:
    for url in build_oauth_authorization_server_metadata_discovery_urls(issuer, server_url):
        found, metadata = await handle_auth_metadata_response(await _send(http, create_oauth_metadata_request(url)))
        if metadata is not None:
            if issuer is not None and not issuers_match(str(metadata.issuer), issuer):
                raise OAuthError("issuer_mismatch")
            return metadata
        if not found:
            break
    raise OAuthError("authorization_server_not_found")


async def _client_token(http: httpx2.AsyncClient, client: OAuthClient) -> OAuthToken:
    scope = {} if client.scope is None else {"scope": client.scope}
    return await _token(http, client, {"grant_type": "client_credentials", **scope})


async def _token(http: httpx2.AsyncClient, client: OAuthClient, form: dict[str, str]) -> OAuthToken:
    response = await _post(http, client, client.token_endpoint, {**form, "resource": client.resource})
    if response.status_code != 200:
        if response.status_code >= 500:
            raise OAuthError("token_endpoint_unavailable", unknown=True)
        raise OAuthError(_error_code(response))
    try:
        return OAuthToken.model_validate_json(response.content)
    except ValidationError:
        # The server answered; whether it issued or rotated tokens is unknown.
        raise OAuthError("invalid_token_response", unknown=True) from None


async def _post(http: httpx2.AsyncClient, client: OAuthClient, url: str, form: dict[str, str]) -> httpx2.Response:
    headers = {"content-type": "application/x-www-form-urlencoded", "accept": "application/json"}
    form = {**form, "client_id": client.client_id}
    if client.authentication == "client_secret_basic" and client.client_secret is not None:
        pair = f"{quote(client.client_id, safe='')}:{quote(client.client_secret, safe='')}"
        headers["authorization"] = "Basic " + base64.b64encode(pair.encode()).decode()
    elif client.authentication == "client_secret_post" and client.client_secret is not None:
        form["client_secret"] = client.client_secret
    try:
        return await http.post(url, content=urlencode(form), headers=headers)
    except EndpointPolicyError:
        raise OAuthError("token_endpoint_denied") from None
    except httpx2.TransportError as error:
        raise OAuthError("token_endpoint_unreachable", unknown=not isinstance(error, _NOT_SENT)) from None


async def _send(http: httpx2.AsyncClient, request: httpx2.Request) -> httpx2.Response:
    try:
        return await http.send(request)
    except EndpointPolicyError:
        raise OAuthError("authorization_server_denied") from None
    except httpx2.TransportError:
        raise OAuthError("authorization_server_unreachable") from None


def _authentication(method: str | None, secret: str | None) -> ClientAuthentication:
    if method in {"client_secret_post", "client_secret_basic"} and secret is not None:
        return "client_secret_post" if method == "client_secret_post" else "client_secret_basic"
    return "none"


def _error_code(response: httpx2.Response) -> str:
    """The RFC 6749 error code when the body carries a well-formed one; never other response text."""
    try:
        code = response.json().get("error")
    except (ValueError, AttributeError):
        code = None
    if isinstance(code, str) and code.isascii() and code.replace("_", "").isalpha() and len(code) <= 64:
        return code
    return "token_request_rejected"
