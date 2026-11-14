"""Tell the movements of a classical work apart in the titles of an album."""

from __future__ import annotations

import re

TITLE = re.compile(r"^(?P<work>.+?): (?P<number>\d+|[IVX]+)\. (?P<name>\S.*)$")
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


def split_movements(titles: list[str]) -> list[tuple[str, str] | None]:
    """Return (work, "I. Movement") for each title that is a movement of a work, else None.

    Titles are "Work: 1. Movement" (arabic or roman numbers). Only consecutive titles of the
    same work with the movements numbered 1, 2, 3... count, anything else is left as it is.
    """
    parsed = [TITLE.match(title) for title in titles]
    result: list[tuple[str, str] | None] = [None] * len(titles)
    start = 0
    while start < len(titles):
        first = parsed[start]
        end = start + 1
        if first and _number(first["number"]) == 1:
            while (
                end < len(titles)
                and (found := parsed[end])
                and found["work"] == first["work"]
                and _number(found["number"]) == end - start + 1
            ):
                end += 1
            if end - start >= 2:
                for index in range(start, end):
                    match = parsed[index]
                    result[index] = (
                        match["work"],
                        f"{roman(index - start + 1)}. {match['name']}",
                    )
        start = end
    return result
