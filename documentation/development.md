# Development

## Run it

```
docker compose up -d        # Home Assistant on http://localhost:8123, config in ./config (not committed)
docker compose restart      # after a change (wait about 40 seconds)
docker compose logs -f
```

Onboard Home Assistant once in the browser. The integration folder is mounted into the container.

### Try it on a phone or a tablet

The container publishes port 8123 on all the interfaces of your computer, so a phone on the same Wi-Fi can open
the development instance, which is the way to check the sidebar player on the real device (the status bar, the
home indicator and the browser toolbars cannot be reproduced by narrowing a desktop browser window):

1. Find the address of your computer (macOS: `ipconfig getifaddr en0`), then open `http://<address>:8123` in the
   browser of the phone. On macOS `http://<computer name>.local:8123` also works and survives a change of address.
2. Log in. In Safari, "Add to Home Screen" gives a full screen web app, close to the Home Assistant app.
3. In the Home Assistant Companion app, add the instance as a second server (Settings, Companion app, Servers).
   The app may ask for the permission to use the local network the first time.
4. After `docker compose restart`, reload the page. If the old scripts stay, clear the cache of the browser (in the
   app: Settings, Companion app, Debugging, Reset frontend cache).

The connection is plain HTTP, which is fine on a private network: do not open the port to the internet.

## Tests

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest -q
```

`requirements_test_oldest.txt` installs the oldest supported Home Assistant (2025.6, Python 3.13), which CI also
runs.

Tests use `pytest-homeassistant-custom-component` and a mocked player (`aioclient_mock`). Parametrize instead of
branching, annotate parameters, and set `hass.config.language` to test a translation. Every translation file must
have exactly the keys of `translations/en.json` (it is tested).

## Continuous integration

GitHub Actions run on every push and pull request (`.github/workflows`): the tests, Home Assistant's own
validator for integrations (**hassfest**) and the **HACS** validation. The validators also run every day, since
they change over time.

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
