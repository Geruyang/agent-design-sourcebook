"""The private resources file is read only when private to its owner, and errors never echo its values."""

import os
import shutil
from pathlib import Path

import pytest

from dev.service import dev_resources

EXAMPLE = Path(__file__).parents[1] / "dev-resources.example.toml"


def private(path: Path, content: str) -> Path:
    path.write_text(content)
    path.chmod(0o600)
    return path


def test_the_example_is_a_valid_file_whose_blank_entries_apply_nothing(tmp_path: Path) -> None:
    copy = tmp_path / "resources.toml"
    shutil.copy(EXAMPLE, copy)
    copy.chmod(0o600)
    resources = dev_resources.load(copy)
    assert resources is not None
    assert [template.provider for template in resources.environment_templates] == ["E2B (local)"]
    entries = [*resources.model_providers, *resources.web_providers, *resources.environment_providers]
    assert not any(dev_resources.filled(entry.credential) for entry in entries)


def test_a_missing_file_is_nothing_to_apply(tmp_path: Path) -> None:
    assert dev_resources.load(tmp_path / "absent.toml") is None


def test_files_readable_by_others_or_symlinked_are_refused(tmp_path: Path) -> None:
    shared = private(tmp_path / "shared.toml", "version = 1\n")
    shared.chmod(0o640)
    with pytest.raises(ValueError, match="mode 0600"):
        dev_resources.load(shared)
    link = tmp_path / "link.toml"
    os.symlink(private(tmp_path / "target.toml", "version = 1\n"), link)
    with pytest.raises(ValueError, match="not a symlink"):
        dev_resources.load(link)


def test_invalid_entries_are_located_without_echoing_credentials(tmp_path: Path) -> None:
    content = """version = 1
[[web_providers]]
type = "brave"
name = "Brave"
credential = { api_key = "sk-private-value" }
unexpected = "sk-private-value"
"""
    with pytest.raises(ValueError, match=r"web_providers\.0\.unexpected") as raised:
        dev_resources.load(private(tmp_path / "invalid.toml", content))
    assert "sk-private-value" not in str(raised.value)


def test_templates_must_name_a_provider_of_the_file(tmp_path: Path) -> None:
    content = """version = 1
[[environment_templates]]
name = "Base"
provider = "Elsewhere"
configuration = {}
"""
    with pytest.raises(ValueError, match="names an environment provider"):
        dev_resources.load(private(tmp_path / "orphan.toml", content))
