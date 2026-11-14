"""Tests for the movements of classical works."""

from __future__ import annotations

import pytest

from custom_components.bluos_companion.classical import roman, split_movements


@pytest.mark.parametrize(
    ("number", "expected"), [(1, "I"), (4, "IV"), (9, "IX"), (14, "XIV"), (27, "XXVII")]
)
def test_roman(number: int, expected: str) -> None:
    """Numbers are written as roman numerals."""
    assert roman(number) == expected


@pytest.mark.parametrize(
    ("titles", "expected"),
    [
        (
            ["K. 595: 1. Allegro", "K. 595: 2. Larghetto", "K. 466: 1. Allegro", "K. 466: 2. Romance"],
            [("K. 595", "I. Allegro"), ("K. 595", "II. Larghetto"), ("K. 466", "I. Allegro"), ("K. 466", "II. Romance")],
        ),
        (["Symphony: I. Adagio", "Symphony: II. Rondo"], [("Symphony", "I. Adagio"), ("Symphony", "II. Rondo")]),
        (["Op. 1: in C: 1. A", "Op. 1: in C: 2. B"], [("Op. 1: in C", "I. A"), ("Op. 1: in C", "II. B")]),
        (["Song: 1. Intro", "Other: 2. Outro"], [None, None]),
        (["Song: 1. Intro", "Song: 3. Outro"], [None, None]),
        (["Song: 2. Intro", "Song: 3. Outro"], [None, None]),
        (["Rehab", "Valerie"], [None, None]),
    ],
)
def test_split_movements(titles: list[str], expected: list[tuple[str, str] | None]) -> None:
    """Only consecutive movements 1, 2, 3... of the same work are grouped."""
    assert split_movements(titles) == expected
