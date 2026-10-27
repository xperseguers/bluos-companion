# BluOS Companion

A Home Assistant custom integration for players running BluOS (NAD, Bluesound, DALI, ...).
It aims to bring much of the BluOS controller app into Home Assistant.

> Not affiliated with, endorsed by or sponsored by Lenbrook Industries or the BluOS brand.
> BluOS is a trademark of its owner. This project only talks to the documented
> *BluOS Custom Integration API*.

## Features

- Config flow: enter the IP address of your player, no YAML needed
- Media player entity: play, pause, stop, previous/next, seek, volume, mute, shuffle, repeat
  and now-playing metadata with cover art
- Media browser (also in the sidebar **Media** panel), with cover art:
  - recently added albums of your local library
  - artists, albums, songs, genres and composers of your library, by letter where relevant
  - playlists and presets
- Play an album, a song, a playlist or a preset on the player
- Cover art is proxied through Home Assistant, so it works when you use HTTPS
- Status is pushed by the player (long polling), no heavy polling
- Available in English and French (follows the language set in Home Assistant)

Roadmap: sidebar panel with a dedicated UI, queue, search, playlist contents, player
grouping, input selection.

## Requirements

- Home Assistant 2025.6 or newer (2026.3 or newer to see the integration icon)
- A BluOS player reachable from Home Assistant on your network (TCP port 11000)
- A fixed IP address (or DHCP reservation) for the player is recommended

## Installation

### Option 1: HACS custom repository

1. In HACS, open the menu (three dots) > **Custom repositories**.
2. Add `https://github.com/xperseguers/bluos-companion` with category **Integration**.
3. Search for *BluOS Companion*, download it and restart Home Assistant.

### Option 2: manual

1. Download or clone this repository.
2. Copy the folder `custom_components/bluos_companion` into the `custom_components`
   folder of your Home Assistant configuration (next to `configuration.yaml`).
   Create `custom_components` if it does not exist.
3. Restart Home Assistant.

## Configuration

1. **Settings > Devices & services > Add integration**, search for *BluOS Companion*.
2. Enter the IP address of the player (the port is 11000 for all BluOS players).
3. Repeat for each player. A player is identified by its MAC address, so changing its
   IP address later and adding it again just updates the existing entry.

Browse the library from the **Media** panel in the sidebar (choose *BluOS Companion*), or
from the media browser of the player card. Choose the play button of an album/preset to
start it on the player.

## Development

```
docker compose up -d        # Home Assistant on http://localhost:8123
docker compose restart      # after code changes
docker compose logs -f
```

Tests:

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```
