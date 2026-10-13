"""One lifecycle owner per checkout, and the application processes it supervises. Stdlib only."""

from __future__ import annotations

import fcntl
import json
import os
import signal
import socket
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

APPLICATION_COMMANDS = frozenset({"dev", "dev-foreground", "service-dev"})
# Service drains in-flight runs for up to its shutdown timeout before exiting.
STOP_SECONDS = 40
START_SECONDS = 120


@dataclass(frozen=True, slots=True)
class Application:
    name: str
    command: tuple[str, ...]
    port: int
    environment: dict[str, str]


def _lock_file(root: Path) -> Path:
    return root / "var/dev/lifecycle.lock"


def owner(root: Path) -> dict[str, object] | None:
    """The command holding the checkout's lifecycle lock, if any."""
    try:
        fd = os.open(_lock_file(root), os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        if _try_lock(fd, fcntl.LOCK_SH):
            return None
        record = json.loads(os.pread(fd, 4096, 0) or b"null")
    except ValueError:
        return None
    finally:
        os.close(fd)
    return record if isinstance(record, dict) else None


def _busy(root: Path) -> str:
    record = owner(root)
    if record is None:
        return "Local development is busy; retry shortly"
    if record.get("command") in APPLICATION_COMMANDS:
        return (
            f"Applications are running ({record['command']}, pid {record['pid']}); stop them with make dev-stop first"
        )
    return f"Local development is busy with {record.get('command')} (pid {record['pid']}); retry when it finishes"


def _try_lock(fd: int, mode: int = fcntl.LOCK_EX) -> bool:
    """Take the lock unless another open file holds it; closing `fd` releases it."""
    try:
        fcntl.flock(fd, mode | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


def claim(fd: int, command: str) -> None:
    """Record the current process as the owner of a held (or inherited) lifecycle lock."""
    os.ftruncate(fd, 0)
    os.pwrite(fd, json.dumps({"command": command, "pid": os.getpid()}).encode(), 0)


@contextmanager
def owning(root: Path, command: str) -> Iterator[int]:
    """Hold the checkout's lifecycle lock: one setup, reset, down or application run at a time."""
    path = _lock_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not _try_lock(fd):
            raise ValueError(_busy(root))
        claim(fd, command)
        yield fd
    finally:
        os.close(fd)


def stop_applications(root: Path) -> bool:
    """Stop the checkout's running applications; False when none run."""
    path = _lock_file(root)
    if not path.exists():
        return False
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        if _try_lock(fd):
            return False
        record = owner(root)
        if record is None or record.get("command") not in APPLICATION_COMMANDS:
            raise ValueError(_busy(root))
        pid = record["pid"]
        assert isinstance(pid, int)
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + STOP_SECONDS + 5
        while not _try_lock(fd):
            if time.monotonic() > deadline:
                raise RuntimeError(f"Applications (pid {pid}) did not stop; see {root / 'var/dev/logs'}")
            time.sleep(0.1)
        return True
    finally:
        os.close(fd)


def listening(port: int) -> bool:
    with socket.socket() as client:
        client.settimeout(0.2)
        return client.connect_ex(("127.0.0.1", port)) == 0


class Applications:
    """Application processes, each leading its own process group so a stop reaches everything it spawned."""

    def __init__(self, root: Path, applications: tuple[Application, ...], logs: Path | None) -> None:
        self.root, self.applications, self.logs = root, applications, logs
        self.processes: list[tuple[Application, subprocess.Popen[bytes]]] = []

    def start(self) -> None:
        if self.logs:
            self.logs.mkdir(parents=True, exist_ok=True)
        for application in self.applications:
            output = open(self.logs / f"{application.name}.log", "ab") if self.logs else None
            try:
                process = subprocess.Popen(
                    application.command,
                    cwd=self.root,
                    env=application.environment,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT if output else None,
                    start_new_session=True,
                )
            finally:
                if output:
                    output.close()
            self.processes.append((application, process))

    def exited(self) -> str | None:
        return next((app.name for app, process in self.processes if process.poll() is not None), None)

    def wait_ready(self, timeout: float = START_SECONDS) -> None:
        deadline = time.monotonic() + timeout
        while not all(listening(app.port) for app in self.applications):
            if (name := self.exited()) is not None:
                raise RuntimeError(f"{name} exited during startup; see {self.logs or 'its output'}")
            if time.monotonic() > deadline:
                raise RuntimeError(f"Applications did not start listening within {timeout:.0f}s")
            time.sleep(0.2)

    def stop(self, force: Callable[[], bool] = lambda: False) -> None:
        for _, process in self.processes:
            _signal_group(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + STOP_SECONDS
        while live := [process for _, process in self.processes if _group_exists(process)]:
            if force() or time.monotonic() > deadline:
                for process in live:
                    _signal_group(process.pid, signal.SIGKILL)
            time.sleep(0.05)
        for _, process in self.processes:
            process.wait()


def _signal_group(group: int, signum: int) -> None:
    try:
        os.killpg(group, signum)
    except (ProcessLookupError, PermissionError):
        pass


def _group_exists(process: subprocess.Popen[bytes]) -> bool:
    process.poll()  # reap an exited leader so only live members keep its group
    try:
        os.killpg(process.pid, 0)
    except (ProcessLookupError, PermissionError):
        # macOS can report EPERM for a group that is exiting.
        return False
    return True


@contextmanager
def running(root: Path, applications: tuple[Application, ...], logs: Path) -> Iterator[None]:
    """Applications serving for the duration of the block, such as seeding."""
    group = Applications(root, applications, logs)
    try:
        group.start()
        group.wait_ready()
        yield
    finally:
        group.stop()


def supervise(
    root: Path,
    applications: tuple[Application, ...],
    *,
    logs: Path | None = None,
    on_ready: Callable[[], None] | None = None,
) -> int:
    """Run applications until a signal or until one exits, then stop them all; a second signal forces it."""
    signals: list[int] = []
    handlers = {
        signum: signal.signal(signum, lambda number, _: signals.append(number))
        for signum in (signal.SIGINT, signal.SIGTERM)
    }
    group = Applications(root, applications, logs)
    try:
        group.start()
        ready = False
        while not signals:
            if (name := group.exited()) is not None:
                print(f"{name} exited; stopping the other applications", flush=True)
                return 1
            if not ready and all(listening(app.port) for app in applications):
                ready = True
                if on_ready:
                    on_ready()
            time.sleep(0.2)
        return 0
    finally:
        group.stop(force=lambda: len(signals) > 1)
        for signum, handler in handlers.items():
            signal.signal(signum, handler)


def start_detached(root: Path, command: tuple[str, ...], lock: int, ports: tuple[int, ...], log: Path) -> None:
    """Start a supervisor in its own OS session, handing it the lifecycle lock; return once all ports listen."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as output:
        process = subprocess.Popen(
            command,
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            pass_fds=(lock,),
        )
    deadline = time.monotonic() + START_SECONDS
    while not all(listening(port) for port in ports):
        if process.poll() is not None:
            raise RuntimeError(f"Applications exited during startup; see {log.parent}")
        if time.monotonic() > deadline:
            process.terminate()
            process.wait(STOP_SECONDS + 5)
            raise RuntimeError(f"Applications did not start listening within {START_SECONDS}s; see {log.parent}")
        time.sleep(0.2)
