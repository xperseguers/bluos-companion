"""Tell the movements of a classical work apart in the titles of an album."""

from __future__ import annotations

import re

NUMBERED = re.compile(r"^(?P<work>.+?)(?:[:,;]| -|-)? (?P<number>\d+|[IVX]+)\. (?P<name>\S.*)$")
UNNUMBERED = re.compile(r"^(?P<work>.+?\S)- (?P<name>\S.*)$")
# A work called "Aida: Act" or "Symphony No" is the number of a part of a bigger work, not a work
NUMBERING_WORDS = frozenset(
    "act acte akt atto scene scène scena part partie teil book livre buch no nr n° op vol volume disc cd".split()
)
ROMAN = (("X", 10), ("IX", 9), ("V", 5), ("IV", 4), ("I", 1))


def _number(text: str) -> int:
    if text.isdigit():
        return int(text)
    total, rest = 0, text
    for numeral, value in ROMAN:
        while rest.startswith(numeral):
            total += value
            rest = rest.removeprefix(numeral)
    return total if not rest else 0


def roman(number: int) -> str:
    """Return a number as roman numerals."""
    result = ""
    for numeral, value in ROMAN:
        count, number = divmod(number, value)
        result += numeral * count
    return result


def _is_work(work: str) -> bool:
    return work.rstrip(".").rsplit(" ", 1)[-1].lower() not in NUMBERING_WORDS


def split_movements(titles: list[str], composers: list[str]) -> list[tuple[str, str] | None]:
    """Return (work, "I. Movement") for each title that is a movement of a work, else None.

    Titles are "Work: 1. Movement" (also "Work - 1. Movement", arabic or roman numbers) with the
    movements numbered 1, 2, 3..., or "Work- Movement" for consecutive titles of the same work and
    composer. Titles without a composer are left as they are, and so is anything else.
    """
    numbered = [
        match if (match := NUMBERED.match(title)) and _is_work(match["work"]) else None
        for title in titles
    ]
    plain = [UNNUMBERED.match(title) for title in titles]
    result: list[tuple[str, str] | None] = [None] * len(titles)
    start = 0
    while start < len(titles):
        end = start + 1
        first = numbered[start]
        if first and composers[start] and _number(first["number"]) == 1:
            while (
                end < len(titles)
                and (found := numbered[end])
                and found["work"] == first["work"]
                and _number(found["number"]) == end - start + 1
            ):
                end += 1
            if end - start >= 2:
                for index in range(start, end):
                    match = numbered[index]
                    result[index] = (match["work"], f"{roman(index - start + 1)}. {match['name']}")
                start = end
                continue
        end = start + 1
        first = plain[start]
        if first and composers[start]:
            while (
                end < len(titles)
                and (found := plain[end])
                and found["work"] == first["work"]
                and composers[end] == composers[start]
            ):
                end += 1
            if end - start >= 2:
                for index in range(start, end):
                    match = plain[index]
                    result[index] = (match["work"], f"{roman(index - start + 1)}. {match['name']}")
                start = end
                continue
        start += 1
    return result
