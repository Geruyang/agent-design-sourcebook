"""What a Service operation's refusal means inside the Service's own agent tools."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from pydantic_ai.exceptions import ToolFailed

from a13n_service.infra.errors import ServiceError


def _message(error: ServiceError) -> str:
    return error.message


@contextmanager
def tool_failures(message: Callable[[ServiceError], str] = _message) -> Iterator[None]:
    """A refused operation fails the tool call with `message(error)`, which the model reads and can recover
    from. An unavailable dependency is not the call's fault: it ends the attempt, and a later attempt retries."""
    try:
        yield
    except ServiceError as error:
        if error.code == "unavailable":
            raise
        raise ToolFailed(message(error)) from None
