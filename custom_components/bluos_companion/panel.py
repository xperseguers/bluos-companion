"""Register the sidebar panel."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import PANEL_ELEMENT, PANEL_PATH, PANEL_URL

FRONTEND_DIR = Path(__file__).parent / "frontend"
MODULE = f"{PANEL_ELEMENT}.js"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Add the panel to the sidebar, for every user."""
    if PANEL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        return
    # The version in the URL makes browsers (and kiosk tablets) load a changed file.
    version = int((FRONTEND_DIR / MODULE).stat().st_mtime)
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_ELEMENT,
        frontend_url_path=PANEL_PATH,
        module_url=f"{PANEL_URL}/{MODULE}?v={version}",
        sidebar_title="BluOS Companion",
        sidebar_icon="mdi:speaker-wireless",
        require_admin=False,
    )


async def async_register_static_path(hass: HomeAssistant) -> None:
    """Serve the panel files."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_URL, str(FRONTEND_DIR), True)]
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the panel from the sidebar."""
    frontend.async_remove_panel(hass, PANEL_PATH)
