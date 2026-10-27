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
  gitignored, never commit or paste it. Extract text with `pdftotext -layout`.

## Layout

- `api.py`: HTTP client (`BluOSClient`) and dataclasses. `/Browse` is generic (`async_browse`).
- `coordinator.py`: status via long polling (`/Status?timeout&etag`), background task.
- `media_player.py`: entity. `media_source.py`: browse tree shared by the Media panel and the
  entity, plus `play_path_from_media_id`. `http.py`: signed artwork proxy (the player is HTTP only).
- `select.py`: sleep timer. `coordinator.py` also keeps `/SyncStatus` (group, external input) and
  the `/RadioBrowse?service=Capture` inputs, reloaded only when `syncStat` of `/Status` changes.
- `strings.json`, `translations/{en,fr}.json`: config flow and `common` (browse titles).
- `icons/*.svg`: tiles served from `/bluos_companion/icons/`.

## Commands

```
docker compose up -d        # HA on :8123, config in ./config (gitignored), mounts the integration
docker compose restart      # after code changes (wait ~40 s)
.venv/bin/pytest -q         # python3.14 venv, requirements_test.txt
```

- Dev HA user `dev` / `devpass123`, created by onboarding through the API. Access tokens expire
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

NAD C368 named "Séjour" at 10.20.30.41, port 11000, always on the TV input. Probing with GETs
is fine. Do NOT send playback, volume or preset commands live without asking first (volume is
84): playback code is covered by mocked tests only.

## Findings about the player API (verified on that player)

- `/Browse` library root: `LocalMusic:` (Artists, Albums, Songs, Genres, Playlists, Composers,
  Favourites). Keys must be URL-encoded; browse keys returned by the player are used as is.
- Artists, Albums, Songs, Composers return `sections` (letters) first, then the entries.
- Long lists have `nextKey`. The library repeats earlier entries in later pages (cumulative),
  so entries are merged in order (`MAX_BROWSE_PAGES`).
- Artist/Composer/Genre entries have no play URL; they lead to a menu (Albums, Songs, ...).
- Saved playlists live at `BluOS:` and play with `/Load?service=BluOS&name=...`; browsing their
  tracks returns nothing here, so playlists are playable but not expandable.
- Undocumented: `/Albums?service=LocalMusic&recent=1` returns the 50 latest albums (album and
  artist names only; keys, covers and play URLs are rebuilt from them).
- Library requests redirect from port 11000 to 11004; images under `/Artwork` may redirect too
  (aiohttp follows).
- Allowed play paths are restricted to `/Add?`, `/Preset?`, `/Load?`, `/Play?id=` (`PLAY_PATH_PREFIXES`).
- Grouping: the NAD is the primary of "Séjour+Pulse mini 2i" (Pulse at 10.20.30.167). The primary's
  `/SyncStatus` lists `<slave id=ip port name>`, the secondary has `<master port>ip</master>`.
  `/RemoveSlave` must go to the primary. Both report the same `/Status` (and `groupName`).
- The NAD's own inputs (TV, Phono, CD...) are in `/SyncStatus` `<externalSource>` (the active one
  is the element, the choices are its `<item id name>`; the `isBluos` item "BluOS" is the one the owner uses to play music from the BluOS module, keep it). Verified
  live: `/ExternalSource?id=<id>` selects one (`/Play?inputTypeIndex=phono-1` does nothing here).
  `/RadioBrowse?service=Capture` lists only Bluetooth. While one is active, `/Status` has
  `streamUrl` `Capture:External` and the name in `title2`.
- Queue: `/Playlist?start=0&end=N`, `/Play?id=<position>`, `/Clear`. Sleep: `/Sleep` only cycles to
  the next value (15, 30, 45, 60, 90, off, verified live), the code presses until `/Status` `<sleep>` matches.

## Conventions that matter

- Tests: `pytest-homeassistant-custom-component`, mocked player (`aioclient_mock`), annotate
  parameters, parametrize instead of branching. Fixtures that create a session must depend on
  `aioclient_mock`. Set `hass.config.language` to test translations.
- Every translation file must have exactly the keys of `translations/en.json` (tested).
- French uses the official BluOS app names: Artistes, Albums, Chansons, Genres, Listes de
  lecture, Compositeurs, Nouveautés, Préréglages, Favoris, Dossiers (plural only). Unknown
  menu labels are kept untranslated on purpose; the singular "Folder" is intentionally unmapped.
- Only translate menu links of type `link`, never music called "Songs".
- HACS cannot show local `brand/` icons yet (HA shows them from 2026.3); not our bug.
- Home Assistant UI limits: browse requests do not carry the target player, so the source
  cannot grey itself out for other players; playing elsewhere raises a clear error.

## Roadmap

Sidebar panel (the owner uses a `panel_custom` redirect to the recent albums for now), selecting
the external inputs (TV, Phono...), search, playlist contents, "Favourites" and "Folders" menus.
Done: queue, sleep timer, input selection, grouping.
