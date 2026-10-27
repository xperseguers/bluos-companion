"""Tests for the translation files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "bluos_companion"


def _keys(value: dict, prefix: str = "") -> set[str]:
    return {
        path
        for key, item in value.items()
        for path in (
            _keys(item, f"{prefix}{key}.")
            if isinstance(item, dict)
            else {f"{prefix}{key}"}
        )
    }


@pytest.mark.parametrize("translation", ["strings.json", "translations/fr.json"])
def test_same_keys_as_english(translation: str) -> None:
    """Every translation defines exactly the keys of the English one."""
    english = json.loads((COMPONENT / "translations" / "en.json").read_text())
    other = json.loads((COMPONENT / translation).read_text())
    assert _keys(other) == _keys(english)
