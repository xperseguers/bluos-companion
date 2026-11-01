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
def test_scripts_have_no_syntax_error(script: Path) -> None:
    """Every script parses."""
    subprocess.run(["node", "--check", str(script)], check=True, capture_output=True)
