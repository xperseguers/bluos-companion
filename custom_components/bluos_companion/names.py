"""Find an input or a preset from the name a person or an automation gives it."""

from __future__ import annotations

import re
import unicodedata


def normalize(text: str) -> str:
    """Return lower case words without accents or punctuation, to compare names."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", plain.lower()))


# Common ways to name an input, and the words that tell which inputs of a player they mean
INPUT_ALIASES: dict[str, tuple[str, ...]] = {
    "tv": ("tv", "arc", "earc"),
    "hdmi": ("hdmi", "arc", "earc"),
    "optical": ("optical", "toslink", "spdif"),
    "toslink": ("optical", "toslink", "spdif"),
    "coax": ("coax", "coaxial"),
    "analog": ("analog", "analogue", "aux", "line", "rca"),
    "analogue": ("analog", "analogue", "aux", "line", "rca"),
    "aux": ("analog", "analogue", "aux", "line", "rca"),
    "line": ("analog", "analogue", "aux", "line", "rca"),
    "phono": ("phono",),
    "vinyl": ("phono",),
    "turntable": ("phono",),
    "record player": ("phono",),
    "bluetooth": ("bluetooth",),
    "bt": ("bluetooth",),
    "cd": ("cd",),
    "dvd": ("dvd", "bd", "bluray"),
    "bluray": ("dvd", "bd", "bluray"),
    "blu ray": ("dvd", "bd", "bluray"),
}


def match_inputs(wanted: str, inputs: dict[str, set[str]]) -> list[str]:
    """Return the inputs a name designates, from the most to the least exact way.

    `inputs` maps the name of each input to the words that describe it. The same name,
    then the same words (case, accents and punctuation do not matter), then a word
    or a common way to say it ("vinyl" for Phono). Several matches mean the name is ambiguous.
    """
    if wanted in inputs:
        return [wanted]
    target = normalize(wanted)
    if same := [name for name in inputs if normalize(name) == target]:
        return same
    keywords = {target, *INPUT_ALIASES.get(target, ())}
    return [name for name, words in inputs.items() if keywords & words]


def match_presets(wanted: str, presets: list[str]) -> list[str]:
    """Return the presets a name designates: the same name, or all the words of it."""
    target = normalize(wanted)
    if not target:
        return []
    if same := [name for name in presets if normalize(name) == target]:
        return same
    words = set(target.split())
    return [name for name in presets if words <= set(normalize(name).split())]
