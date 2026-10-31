# How it was tested

## Devices

| Device | What it is | How it was tested |
|---|---|---|
| NAD C368 with the MDC2 BluOS-D module | an amplifier with a built-in BluOS module (inputs and standby are handled by the amplifier) | everything, live: playback, browsing, search, queue, playlists, presets, grouping, moving playback, backup and restore, the amplifier power and speaker switches, favourites, the cover size limit, the import of playlists |
| Bluesound Pulse Mini 2i | a wireless speaker | everything, live, including grouping with the NAD, moving playback, restoring a playlist, muting a group, the volume and mute of a secondary player, and favourites shared with the NAD |
| Bluesound NODE | a standalone streamer | playback with version 1.2.0; the sidebar player, the cards and the playlists through read-only checks (inputs, presets, playlists, home page) |

All three run the same BluOS firmware family (4.18). The live tests used Home Assistant 2026.10. Players of other
models or firmware may behave differently: please report what you find.

## Automated tests

More than 430 automated tests run with `pytest-homeassistant-custom-component`, against a **simulated player**
(no real device is needed), on **Home Assistant 2025.6** (the oldest supported version) and on the latest one,
for every change. They cover the client, the setup and the options, the media player entity and
the media browser, the data and commands of the sidebar player and the cards, the search (with typos), the
playlist and favourites backup and restore, the import of playlists, the cover check, the amplifier switches
(against a small simulated amplifier), and that every translation has the same keys.

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```

## Live checks of the newer features

These were tried on the real players, with nothing playing (or with the amplifier muted) and everything put back
afterwards:

- **Cover size**: more than forty test files with covers of different sizes, dimensions and formats, to find the
  limit the player has (600 KiB) and what it does with a damaged picture; the check of the covers of a whole library
  (about 1,900 albums) and its sensor.
- **Amplifier**: switching it on and off (about six seconds to switch on), the player staying reachable in
  standby, and the speaker outputs, checked against what the amplifier itself answers.
- **Groups**: muting a whole group from each of its members, and the own volume and mute of a secondary player.
- **Favourites**: adding and removing an album, an artist and a song, the players sharing them, the backup, and the
  restore (including a favourite the library does not have); adding and removing a favourite by hand in the sidebar
  player, from an album page and from the title of the playing track.
- **Sidebar player**: the home button of the breadcrumb, used by hand several levels deep.
- **Import**: a real playlist of 134 tracks exported from Apple Music, with accents written the way a Mac does, built
  on the player in its order; the tracks the player's library did not know were reported.
- **Presets and inputs by name**: a preset by a word of its name, inputs by common names, and the error for a name
  that fits several inputs.

## What is not tested

- other models and firmware, players with several secondary players in a group
- the amplifier switches on other amplifiers than the NAD C368 (the speaker outputs were checked through the
  amplifier's own answer, the sound itself was not listened to), and amplifiers without speaker outputs (simulated only)
- the favourites of the streaming services and favourite playlists, and the import of playlists exported in another
  format than `.m3u8` or from a library that is not organised as artist / album / file (the paths of Windows are
  covered by automated tests only)
- the accounts of music services (Deezer, Tidal...) and Amazon Music
- selecting the HDMI ARC input or using the sleep timer of the NODE
- the sidebar player in browsers and tablets other than the ones used during development, and live use on Home
  Assistant versions other than 2026.10

If something does not work on your player, an [issue](https://github.com/xperseguers/bluos-companion/issues)
with the model and firmware helps a lot.
