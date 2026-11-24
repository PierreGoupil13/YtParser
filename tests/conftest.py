from pathlib import Path

import pytest

from ytparser.adapters import configadapter


@pytest.fixture(autouse=True)
def no_user_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """Never read the developer's real config file; tests write their own when needed."""
    path = tmp_path_factory.mktemp("config") / "config.yaml"
    monkeypatch.setattr(configadapter, "default_config_path", lambda: path)
    return path
