"""What tool discovery shares: a brief Redis cache under `provider:{type}:` and failure text safe to show.

The cache is only an accelerator; a miss or a Redis error discovers again.
"""

from a13n_harness.providers.connector.contracts import ConnectorProviderError
from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from a13n_service.infra.errors import ServiceError
from a13n_service.providers.tools.oauth import OAuthError


async def cached[T](redis: Redis, key: str, adapter: TypeAdapter[T]) -> T | None:
    try:
        value = await redis.get(key)
        return None if value is None else adapter.validate_json(value)
    except (RedisError, ValidationError):
        return None


async def cache[T](redis: Redis, key: str, adapter: TypeAdapter[T], value: T, *, ttl: int) -> None:
    try:
        await redis.set(key, adapter.dump_json(value), ex=ttl)
    except RedisError:
        pass


def failure_message(error: Exception) -> str:
    """Fixed text or a classified code: upstream bodies and inputs can carry credentials."""
    match error:
        case ServiceError():
            return error.message
        case OAuthError() | ConnectorProviderError():
            return f"The provider refused: {error.code}"
        case TimeoutError():
            return "The server did not answer in time"
        case ValueError():
            return "The endpoint is not permitted or returned an invalid tool list"
        case _:
            return "The server could not be reached or did not return a usable tool list"


def unavailable(dependency: str, error: Exception) -> ServiceError:
    return ServiceError("unavailable", failure_message(error), {"dependency": dependency})
