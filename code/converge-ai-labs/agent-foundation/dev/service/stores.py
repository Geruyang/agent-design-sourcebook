"""This checkout's PostgreSQL and Redis: one Compose project whose volumes only this checkout uses. Stdlib only."""

from __future__ import annotations

import os
import subprocess

from dev.service.checkout import ROOT
from dev.service.instance import Instance, require_free

COMPOSE_FILE = ROOT / "dev/service/compose.yaml"
PROJECT_PREFIX = "a13n-service-dev-"


def project(instance: Instance) -> str:
    return PROJECT_PREFIX + instance.id


def compose(instance: Instance, *arguments: str, capture: bool = False) -> str:
    ports = {"A13N_DEV_POSTGRES_PORT": str(instance.ports.postgres), "A13N_DEV_REDIS_PORT": str(instance.ports.redis)}
    command = ["docker", "compose", "--env-file", os.devnull, "--project-name", project(instance)]
    try:
        result = subprocess.run(
            [*command, "--file", str(COMPOSE_FILE), *arguments],
            env={**os.environ, **ports},
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError:
        raise RuntimeError("Docker is required for local development; install it and retry") from None
    return result.stdout or ""


def running(instance: Instance) -> set[str]:
    return set(compose(instance, "ps", "--services", "--status", "running", capture=True).split())


def start(instance: Instance) -> None:
    """Start the stores; an assigned port another process holds fails instead of moving."""
    stopped = {"postgres", "redis"} - running(instance)
    require_free({name: port for name, port in instance.ports.named().items() if name in stopped})
    compose(instance, "up", "--detach", "--wait")


def stop(instance: Instance) -> None:
    compose(instance, "stop")


def delete(instance: Instance) -> None:
    """Remove this checkout's containers and volumes; nothing else is touched."""
    compose(instance, "down", "--volumes", "--remove-orphans")
