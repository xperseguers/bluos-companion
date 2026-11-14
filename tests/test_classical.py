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
        (["K. 488 - 1. Allegro", "K. 488 - 2. Andante"], [("K. 488", "I. Allegro"), ("K. 488", "II. Andante")]),
        (
            ["Salve Regina, RV 1- Salve", "Salve Regina, RV 1- Amen (Allegro)", "Stabat, RV 2- Largo"],
            [("Salve Regina, RV 1", "I. Salve"), ("Salve Regina, RV 1", "II. Amen (Allegro)"), None],
        ),
        (["Song - Remix", "Song - Live"], [None, None]),
        (["Aida: Act 1. Scene 2", "Aida: Act 2. Scene 1"], [None, None]),
        (["Symphony No. 1. Allegro", "Symphony No. 2. Adagio"], [None, None]),
        (["Suite (AL) 1. A", "Suite (AL), 2. B"], [("Suite (AL)", "I. A"), ("Suite (AL)", "II. B")]),
        (["Suite En La 1. Prelude (1)", "Suite En La 2. Allemande (2)"], [("Suite En La", "I. Prelude (1)"), ("Suite En La", "II. Allemande (2)")]),
    ],
)
def test_split_movements(titles: list[str], expected: list[tuple[str, str] | None]) -> None:
    """Only consecutive movements 1, 2, 3... of the same work are grouped."""
    assert split_movements(titles, ["Composer"] * len(titles)) == expected


def test_unnumbered_movements_need_the_same_composer() -> None:
    """Titles of one work by two composers are not a work."""
    titles = ["Work- A", "Work- B"]
    assert split_movements(titles, ["X", "Y"]) == [None, None]
    assert split_movements(titles, ["", ""]) == [None, None]


def test_movements_need_a_composer() -> None:
    """Without a composer a numbered title is only a title (a musical, a compilation)."""
    titles = ["Cats - 1. Ouverture", "Cats - 2. Prologue"]
    assert split_movements(titles, ["", ""]) == [None, None]
    assert split_movements(titles, ["Webber", "Webber"]) == [
        ("Cats", "I. Ouverture"),
        ("Cats", "II. Prologue"),
    ]
