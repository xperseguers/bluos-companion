# Development

## Run it

```
docker compose up -d        # Home Assistant on http://localhost:8123, config in ./config (not committed)
docker compose restart      # after a change (wait about 40 seconds)
docker compose logs -f
```

Onboard Home Assistant once in the browser. The integration folder is mounted into the container.

## Tests

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest -q
```

Tests use `pytest-homeassistant-custom-component` and a mocked player (`aioclient_mock`). Parametrize instead of
branching, annotate parameters, and set `hass.config.language` to test a translation. Every translation file must
have exactly the keys of `translations/en.json` (it is tested).

## Layout

| Path | What |
|---|---|
| `custom_components/bluos_companion/api.py` | the HTTP client of a player and its dataclasses |
| `coordinator.py` | status of a player through long polling, its group and its inputs |
| `media_player.py`, `select.py` | the entities |
| `media_source.py`, `media_search.py`, `covers.py` | the media browser, the search, the covers |
| `websocket_api.py`, `panel.py`, `http.py` | what the sidebar player and the cards use, served files, the cover proxy |
| `playlist_backup.py`, `backup.py` | the playlist text backup, the hook before a Home Assistant backup |
| `frontend/*.js` | the sidebar player and the two cards: plain JavaScript, **no build step, no Node** |
| `strings.json`, `translations/{en,fr,de}.json` | texts of the setup, options, services, menus and of the sidebar player and cards |
| `icons/`, `brand/` | our own tiles and icons |

## Conventions

- Commit messages start with `[TASK]`, `[BUGFIX]` or `[DOC]`.
- The frontend files contain no text of their own: add a key to the translation files (all languages) and use
  `this._t("key")`.
- Use the official names that the player returns in a language for the menus (artists, albums...). Keep a label
  you do not know untranslated.
- Use our own icons, never logos or images of the BluOS brands or of the manufacturers.
- Do not paste material you do not have the right to share in issues or pull requests.

## Contributing

Issues and pull requests are welcome. Please run the tests, add tests for what you change, and describe what you
tried on which player.
