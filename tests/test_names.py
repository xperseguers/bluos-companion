"""Tests for finding an input or a preset from the name it is given."""

from __future__ import annotations

import pytest

from custom_components.bluos_companion.names import match_inputs, match_presets, normalize

INPUTS = {
    "Phono": {"phono"},
    "CD": {"cd"},
    "Bluetooth": {"bluetooth"},
    "Bluetooth (BluOS)": {"bluetooth", "bluos"},
    "AppleTV": {"appletv"},
    "Wingo TV": {"wingo", "tv"},
    "HDMI ARC": {"hdmi", "arc"},
    "Optical": {"optical"},
}


def test_normalize() -> None:
    """Case, accents and punctuation do not matter."""
    assert normalize("L'été – Ça va!") == "l ete ca va"


@pytest.mark.parametrize(
    ("wanted", "expected"),
    [
        ("Phono", ["Phono"]),
        ("PHONO", ["Phono"]),
        ("vinyl", ["Phono"]),
        ("Turntable", ["Phono"]),
        ("wingo", ["Wingo TV"]),
        ("hdmi", ["HDMI ARC"]),
        ("optical", ["Optical"]),
        ("cd", ["CD"]),
        # The exact name wins over a word that also fits another input
        ("Bluetooth", ["Bluetooth"]),
        ("bt", ["Bluetooth", "Bluetooth (BluOS)"]),
        ("tv", ["Wingo TV", "HDMI ARC"]),
        ("dvd", []),
        ("nothing", []),
    ],
)
def test_match_inputs(wanted: str, expected: list[str]) -> None:
    """An input is found by its name, its words or a common way to say it."""
    assert match_inputs(wanted, INPUTS) == expected


PRESETS = ["RTS La Première", "Rouge FM", "Radio FM", "98.5"]


@pytest.mark.parametrize(
    ("wanted", "expected"),
    [
        ("Rouge FM", ["Rouge FM"]),
        ("rts la premiere", ["RTS La Première"]),
        ("rouge", ["Rouge FM"]),
        ("premiere", ["RTS La Première"]),
        ("fm", ["Rouge FM", "Radio FM"]),
        ("jazz", []),
        ("", []),
        ("  ", []),
    ],
)
def test_match_presets(wanted: str, expected: list[str]) -> None:
    """A preset is found by its name, or by all the words of what is asked."""
    assert match_presets(wanted, PRESETS) == expected
