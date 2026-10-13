from pathlib import Path

import pytest

from dev.service import instance


@pytest.fixture(autouse=True)
def machine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A private machine registry, so tests never reserve or read this machine's real port blocks."""
    directory = tmp_path / "machine"
    monkeypatch.setattr(instance, "machine_directory", lambda: directory)
    return directory


@pytest.fixture
def checkout_root(tmp_path: Path) -> Path:
    root = (tmp_path / "checkout").resolve()
    root.mkdir()
    return root
