"""One owner per checkout; supervised applications stop as a whole, whatever ends them."""

import os
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from dev.service.lifecycle import Application, owner, owning, stop_applications, supervise

ROOT = Path(__file__).resolve().parents[3]


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def server(name: str, port: int) -> Application:
    command = (sys.executable, "-m", "http.server", "--bind", "127.0.0.1", str(port))
    return Application(name, command, port, dict(os.environ))


def test_a_second_owner_is_refused_with_the_first_named(checkout_root: Path) -> None:
    with owning(checkout_root, "reset"):
        assert owner(checkout_root) == {"command": "reset", "pid": os.getpid()}
        with pytest.raises(ValueError, match="busy with reset"):
            with owning(checkout_root, "dev"):
                pass
        with pytest.raises(ValueError, match="busy with reset"):
            stop_applications(checkout_root)
    with owning(checkout_root, "setup"):
        pass
    assert stop_applications(checkout_root) is False


def test_stop_drains_a_detached_supervisor_and_its_process_groups(checkout_root: Path) -> None:
    port = free_port()
    script = textwrap.dedent(f"""
        import os, sys
        from pathlib import Path
        from dev.service.lifecycle import Application, owning, supervise
        root = Path({str(checkout_root)!r})
        command = (sys.executable, "-m", "http.server", "--bind", "127.0.0.1", "{port}")
        with owning(root, "dev"):
            ready = lambda: print("ready", flush=True)
            raise SystemExit(supervise(root, (Application("web", command, {port}, dict(os.environ)),), on_ready=ready))
    """)
    supervisor = subprocess.Popen(
        [sys.executable, "-c", script], cwd=ROOT, stdout=subprocess.PIPE, text=True, start_new_session=True
    )
    assert supervisor.stdout is not None and supervisor.stdout.readline().strip() == "ready"
    assert owner(checkout_root) == {"command": "dev", "pid": supervisor.pid}

    assert stop_applications(checkout_root) is True
    assert supervisor.wait(timeout=10) == 0
    with socket.socket() as client:
        assert client.connect_ex(("127.0.0.1", port)) != 0
    assert stop_applications(checkout_root) is False


def test_one_exiting_application_stops_the_others(checkout_root: Path) -> None:
    port = free_port()
    failing = Application("failing", (sys.executable, "-c", "import time; time.sleep(0.5)"), free_port(), {})
    started = time.monotonic()
    assert supervise(checkout_root, (server("web", port), failing)) == 1
    assert time.monotonic() - started < 10
    with socket.socket() as client:
        assert client.connect_ex(("127.0.0.1", port)) != 0


def test_a_failed_start_stops_what_already_started(checkout_root: Path, tmp_path: Path) -> None:
    port = free_port()
    missing = Application("missing", (str(tmp_path / "missing"),), free_port(), {})
    with pytest.raises(FileNotFoundError):
        supervise(checkout_root, (server("web", port), missing))
    time.sleep(0.2)
    with socket.socket() as client:
        assert client.connect_ex(("127.0.0.1", port)) != 0
