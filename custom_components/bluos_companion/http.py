"""Serve player artwork through Home Assistant so it works over HTTPS."""

from __future__ import annotations

import base64
from datetime import timedelta
from http import HTTPStatus

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .api import BluOSError
from .const import DOMAIN

ARTWORK_URL = "/api/bluos_companion/{entry_id}/artwork"
SIGN_EXPIRATION = timedelta(hours=1)


def encode_image(image: str) -> str:
    """Make an image path safe to sign: paths contain %XX, + and & that URL layers re-encode."""
    return base64.urlsafe_b64encode(image.encode()).decode().rstrip("=")


def decode_image(value: str) -> str:
    """Return the image path of an encoded value, or "" if it is not valid."""
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
    except ValueError:
        return ""


def async_artwork_url(hass: HomeAssistant, entry_id: str, image: str) -> str:
    """Return a URL the browser can load for a player image."""
    if image.startswith("https://"):
        return image
    base = ARTWORK_URL.format(entry_id=entry_id)
    return async_sign_path(hass, f"{base}?path={encode_image(image)}", SIGN_EXPIRATION)


class BluOSArtworkView(HomeAssistantView):
    """Proxy images from the plain-HTTP player."""

    url = ARTWORK_URL
    name = "api:bluos_companion:artwork"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the image."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        path = decode_image(request.query.get("path", ""))
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
            or not path.startswith(("/", "http://"))
        ):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        try:
            body, content_type = await entry.runtime_data.client.async_get_image(path)
        except BluOSError:
            return web.Response(status=HTTPStatus.BAD_GATEWAY)
        return web.Response(
            body=body,
            content_type=content_type,
            headers={"Cache-Control": "max-age=86400"},
        )
