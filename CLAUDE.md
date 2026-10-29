# BluOS Companion

Home Assistant custom integration for BluOS players (NAD, Bluesound, ...), published at
https://github.com/xperseguers/bluos-companion. Domain `bluos_companion`, HACS-ready
(`hacs.json`, `custom_components/bluos_companion/`). The Home Assistant core repository is not
needed to work here.

## Naming and brand rules

- The BluOS API policy forbids BluOS names/marks in an integration's name; the owner chose
  "BluOS Companion" knowingly (private use). Keep the "not affiliated" notice in the README.
- Never use Lenbrook/Bluesound/BluOS logos or brand images. Icons are our own tiles
  (`brand/` for HA, `icons/` for the media browser).
- The API manual (`docs/BluOS-Custom-Integration-API_v1.7.pdf`) is confidential: it is
  gitignored, never commit or paste it. Extract text with `pdftotext -layout`. The same goes for
  `docs/player-notes.md`.

## Layout

- `api.py`: HTTP client (`BluOSClient`) and dataclasses.
- `coordinator.py`: playback status of a player through long polling, plus its group, inputs and the
  shared input logic.
- `media_player.py`: the entity. `media_source.py`: browse tree shared by the Media panel and the
  entity, `play_path_from_media_id` and `is_play_path` (the only paths allowed to start playback).
  `http.py`: signed artwork proxy (the player is HTTP only).
- `select.py`: sleep timer.
- `panel.py` + `frontend/bluos-companion-panel.js`: sidebar panel (plain JS custom element, no build
  step, for every user, aimed at a kiosk tablet). `frontend/bluos-companion-presets-card.js` and
  `frontend/bluos-companion-player-card.js`: dashboard cards, loaded by the integration itself.
  `websocket_api.py`: the `bluos_companion/*` commands they use.
- `playlist_backup.py` + `backup.py`: playlists saved as `.m3u8` text files before every Home Assistant
  backup, and the services `backup_playlists` / `restore_playlists`.
- `strings.json`, `translations/{en,fr,de}.json`: config flow, options, services and `common` (browse titles and, in `common.panel`, the texts of the panel and the cards, served by the `translations` websocket command; the scripts contain no English).
- `icons/*.svg`: tiles served from `/bluos_companion/icons/`.
- `TODO.md`: the plan, a local file that is not committed (gitignored).

## Commands

```
docker compose up -d        # HA on :8123, config in ./config (gitignored), mounts the integration
docker compose restart      # after code changes (wait ~40 s)
.venv/bin/pytest -q         # python3.14 venv, requirements_test.txt
```

- Dev HA user: see `docs/player-notes.md` (local), created by onboarding through the API. Access tokens expire
  after 30 minutes: POST `/auth/login_flow` (`handler: ["homeassistant", null]`), POST the
  username/password to `/auth/login_flow/<flow_id>`, then exchange the returned code at
  `/auth/token` (`grant_type=authorization_code`). On an empty `config/` (only
  `configuration.yaml`), onboard first with `POST /api/onboarding/users`.
- Live-test browsing with a websocket client run inside the container
  (`docker exec <container> python3 script.py`, aiohttp is available there).
- Commits: `[TASK] Summary`, `[BUGFIX]` for fixes, `[DOC]` for documentation, body optional,
  end with the `Co-Authored-By` line given by the harness. Do not `git add -A` blindly: check
  `git status` first (the IDE creates `.idea/`).
- Someone may amend commits outside the session. Look at `git log` / `git diff` before assuming.

## The player used for development

A NAD C368 with a BluOS module named "Séjour" (the master, everything lives there) and a Pulse mini 2i
named "Pulse", both configured in the dev HA; their addresses are in `docs/player-notes.md` (local). Probing
with GETs is fine. Playback, volume, queue and grouping commands change what the household hears: ask first,
keep volumes modest and put everything back as it was (the owner has agreed to live tests when told).

## What may be written in committed files

Keep committed files (this file, documentation, code comments, docstrings, commit messages, pull
requests) at the feature level:

- describe what the integration does for users ("the player moves its queue to another player") and say "the
  player";
- do not catalogue endpoints or describe how the players work inside: the code uses what it needs, with short
  factual docstrings;
- technical notes about the players, and anything private about the owner, go to `docs/player-notes.md`, which is
  gitignored (local only, read it before changing `api.py`).

## Conventions that matter

- Tests: `pytest-homeassistant-custom-component`, mocked player (`aioclient_mock`), annotate
  parameters, parametrize instead of branching. Fixtures that create a session must depend on
  `aioclient_mock`. Set `hass.config.language` to test translations.
- Every translation file must have exactly the keys of `translations/en.json` (tested).
- German uses the official names the player returns for `Accept-Language: de` (Künstler, Alben, Titel, Wiedergabelisten, Komponisten, Ordner, Favoriten, Neu, Warteschlange). French uses the official BluOS app names: Artistes, Albums, Chansons, Genres, Listes de
  lecture, Compositeurs, Nouveautés, Préréglages, Favoris, Dossiers (plural only). Unknown
  menu labels are kept untranslated on purpose; the singular "Folder" is intentionally unmapped.
- Only translate menu links of type `link`, never music called "Songs".
- HACS cannot show local `brand/` icons yet (HA shows them from 2026.3); not our bug.
- Home Assistant UI limits: browse requests do not carry the target player, so the source
  cannot grey itself out for other players; playing elsewhere raises a clear error.

## Roadmap

See the local `TODO.md`. Done: panel, search, queue, playlists, home page, grouping, move playback, cards, playlist
backup and restore. Next: voice and AI search, panel translations, A-Z bar, documentation, HACS submission.
Later: a "Clear queue" `button` entity (only `media_player.clear_playlist` exists, no UI button),
let library items play on any player (today items are tied to the player browsed from, by design).
