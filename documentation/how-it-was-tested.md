# How it was tested

## Devices

| Device | What it is | How it was tested |
|---|---|---|
| NAD C368 with the MDC2 BluOS-D module | an amplifier with a built-in BluOS module (inputs and standby are handled by the amplifier) | everything, live: playback, browsing, search, queue, playlists, presets, grouping, moving playback, backup and restore |
| Bluesound Pulse Mini 2i | a wireless speaker | everything, live, including grouping with the NAD, moving playback and restoring a playlist |
| Bluesound NODE | a standalone streamer | playback with version 1.2.0; the sidebar player, the cards and the playlists through read-only checks (inputs, presets, playlists, home page) |

All three run the same BluOS firmware family (4.18). Home Assistant 2026.10 was used. Players of other
models or firmware may behave differently: please report what you find.

## Automated tests

About 300 automated tests run with `pytest-homeassistant-custom-component`, against a **simulated player**
(no real device is needed). They cover the client, the setup and the options, the media player entity and
the media browser, the data and commands of the sidebar player and the cards, the search (with typos), the
playlist backup and restore, and that every translation has the same keys.

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```

## What is not tested

- other models and firmware, players with several secondary players in a group
- the accounts of music services (Deezer, Tidal...) and Amazon Music
- selecting the HDMI ARC input or using the sleep timer of the NODE
- the sidebar player in browsers and tablets other than the ones used during development, and Home Assistant
  versions other than 2026.10

If something does not work on your player, an [issue](https://github.com/xperseguers/bluos-companion/issues)
with the model and firmware helps a lot.
