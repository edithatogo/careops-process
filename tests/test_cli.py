"""Synthetic CLI smoke tests."""

import json
from typing import TYPE_CHECKING

from careops_process.cli import main

if TYPE_CHECKING:
    import pytest

EVENT_COUNT = 2


def test_cli_emits_projection(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The smoke command emits JSON and requires an injected secret."""
    test_secret = "cli-test-key"  # noqa: S105
    monkeypatch.setenv("CAREOPS_PSEUDONYM_SECRET", test_secret)
    assert main(["--log-id", "cli-test"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["quality"]["event_count"] == EVENT_COUNT
