"""Read-only commands: status in any checkout, and the machine's environment list."""

import subprocess
import sys
from pathlib import Path

import pytest

from dev.service import envs
from dev.service.__main__ import status
from dev.service.checkout import Checkout

ROOT = Path(__file__).resolve().parents[3]


def test_status_of_a_fresh_checkout_changes_nothing(checkout_root: Path, machine: Path) -> None:
    assert status(checkout_root) == {
        "configured": False,
        "instance_file": str(checkout_root / "var/dev/instance.json"),
    }
    assert not (checkout_root / "var").exists() and not machine.exists()


def test_status_reports_urls_listeners_and_owner(checkout_root: Path) -> None:
    checkout = Checkout.resolve(checkout_root)
    reported = status(checkout_root)
    assert reported["console_url"] == checkout.console_url and reported["service_url"] == checkout.service_url
    assert reported["listeners"] == dict.fromkeys(checkout.instance.ports.named(), False)
    assert (reported["owner"], reported["seeded"]) == (None, False)


def test_status_runs_on_the_standard_library_alone() -> None:
    # `make dev-status` and `make dev-env-list` run before the repository environment exists; -S skips site packages.
    command = [sys.executable, "-S", "-c", "import dev.service.__main__, dev.service.envs"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_environment_list_shows_checkouts_and_unregistered_projects(
    checkout_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = Checkout.resolve(checkout_root)
    project = f"a13n-service-dev-{checkout.id}"
    monkeypatch.setattr(envs, "_worktrees", lambda: {str(checkout_root): "feature"})
    monkeypatch.setattr(
        envs, "_projects", lambda: {project: "running(2)", "a13n-service-dev-0123456789ab": "exited(2)"}
    )
    rows = envs.list_environments()
    assert rows[0] | {"ports": None} == {
        "instance": checkout.id,
        "root": str(checkout_root),
        "branch": "feature",
        "worktree": True,
        "ports": None,
        "stores": "running(2)",
        "owner": None,
    }
    assert rows[1] == {"instance": "0123456789ab", "stores": "exited(2)"}
