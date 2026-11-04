"""Checks of the scripts of the sidebar panel and the cards (there is no build step to catch mistakes)."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

import pytest

FRONTEND = Path(__file__).parent.parent / "custom_components" / "bluos_companion" / "frontend"
SCRIPTS = sorted(FRONTEND.glob("*.js"))


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_properties_do_not_hide_methods(script: Path) -> None:
    """`this.name = ...` replaces the method `name(...)` of the class: calling it then fails."""
    source = script.read_text()
    methods = set(re.findall(r"^  (?:async )?(_?[A-Za-z]\w*)\([^)]*\) \{$", source, re.MULTILINE))
    methods -= {"constructor", "if", "for", "while", "switch", "catch"}
    properties = set(re.findall(r"\bthis\.(_?[A-Za-z]\w*) = (?!=)", source))
    assert not methods & properties


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_scripts_have_no_syntax_error(script: Path, tmp_path: Path) -> None:
    """Every script parses as a module (the browser loads them that way)."""
    module = tmp_path / f"{script.stem}.mjs"
    module.write_text(script.read_text())
    subprocess.run(["node", "--check", str(module)], check=True, capture_output=True)


@pytest.mark.parametrize("script", ["bluos-companion-card-controls.js", "bluos-companion-presets-card.js", "bluos-companion-player-card.js"])
def test_other_entities_are_read_under_their_group(script: str) -> None:
    """The entities of another player are only read under `other_entities`, as the card editor saves them."""
    source = (FRONTEND / script).read_text()
    assert not re.search(r"_config\.(volume|source|power)_entity", source)
