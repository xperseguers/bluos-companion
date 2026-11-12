# How it was tested

## Devices

| Device | What it is | How it was tested |
|---|---|---|
| NAD C368 with the MDC2 BluOS-D module | an amplifier with a built-in BluOS module (inputs and standby are handled by the amplifier) | everything, live: playback, browsing, search, queue, playlists, presets, grouping, moving playback, backup and restore, the amplifier power and speaker switches, favourites, the cover size limit, the import of playlists |
| Bluesound Pulse Mini 2i | a wireless speaker | everything, live, including grouping with the NAD, moving playback, restoring a playlist, muting a group, the volume and mute of a secondary player, and favourites shared with the NAD |
| Bluesound NODE | a standalone streamer | used for real on a daily basis in a second home, and kept up to date with the releases: not tested as thoroughly as the owner's own devices above, but constantly checked in real life |

All three run the same BluOS firmware family (4.18). The live tests used Home Assistant 2026.10 and 2026.11. Players of other
models or firmware may behave differently: please report what you find.

## Automated tests

More than 565 automated tests run with `pytest-homeassistant-custom-component`, against a **simulated player**
(no real device is needed), on **Home Assistant 2025.6** (the oldest supported version) and on the latest one,
for every change. They cover the client, the setup and the options, the media player entity and
the media browser, the data and commands of the sidebar player and the cards, the search (with typos), the
playlist and favourites backup and restore, the import of playlists, renaming and deleting a playlist (against a
simulated player that keeps playlists), the cover check, the amplifier switches (against a small simulated
amplifier), the services (play a genre, a playlist or a preset, clear the history, mute), the mute switch and the
clear queue button, the status attributes, the cards' scripts (they must parse and use services and texts that exist),
and that every translation has the same keys.

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
- **Mute switch**: the Mute switch of a player flipped with one tap from a dashboard tile on the Pulse mini 2i,
  and put back.
- **Clear queue button**: pressed from a dashboard tile on the Pulse mini 2i with a queue loaded.
- **Play button card**: the editor (the lists of genres, presets and playlists, the options), the three layouts and
  a preset button, tried by hand on a dashboard.
- **Groups**: muting a whole group from each of its members, and the own volume and mute of a secondary player.
- **Favourites**: adding and removing an album, an artist and a song, the players sharing them, the backup, and the
  restore (including a favourite the library does not have); adding and removing a favourite by hand in the sidebar
  player, from an album page and from the title of the playing track.
- **Sidebar player**: the home button of the breadcrumb, used by hand several levels deep.
- **Sidebar player on a phone**: the compact bar, the volume strip, the More menu, the full screen view with its blurred cover (light and dark covers), tried by hand in a narrowed browser window; the safe areas of an iPhone still need a look on the phone itself.
- **Sidebar player, full screen view**: the queue inside it (shuffle, repeat, playing a track, the covers staying still while the state updates), the favourite heart and the menu of the playing track, and the input and sleep timer popup, tried by hand on a phone and a tablet.
- **Browsing the library in the sidebar player**: the lists of artists, albums, songs, composers and genres as flat rows with the letters, the A-Z index (touch and mouse, a library of about 17,000 songs), the sorts of the albums (year, decade, artist...), the landing pages of an artist and a genre, the album page, the item menu with Info, the home screen, and the covers at their size, tried by hand on a phone, a tablet and a desktop.
- **Technical info**: the Info of tracks of the library (CD, high resolution and lossy files), playing or not, from the lists, the search results and the queue, tried by hand on a desktop and on a phone, with the details compared with the ones of the BluOS app.
- **Playlists**: playing tracks of saved playlists (first and later pages, a playlist with 250 entries the player cannot find), tried by hand on the amplifier.
- **Editing the queue and the playlists**: the edit mode of the queue (drag and drop, remove) and of a saved playlist
  (reorder, remove, save), tried by hand on a desktop and on a phone; a playlist of 541 tracks (many of them repeated)
  was rebuilt from its backup in its order, and so was a playlist of 12 tracks, each checked track by track against
  the backup. Reading a long playlist can take a while: the page keeps loading instead of starting over.
- **Add to playlist**: adding a track, a whole album and a track of the queue to the end of an existing playlist, and
  to a playlist that did not exist yet, through the same commands the sidebar player uses, on the amplifier. The two
  dialogs (choosing a playlist, naming a new one) were tried by hand. The test playlist was deleted afterwards.
- **Languages of the actions**: play now, shuffle, add next and add last in French and German, compared with the
  BluOS app.
- **Import**: a real playlist of 134 tracks exported from Apple Music, with accents written the way a Mac does, built
  on the player in its order; the tracks the player's library did not know were reported.
- **Renaming and deleting a playlist**: a playlist of 10 tracks made for the test was renamed through the service on
  the amplifier (the copy checked track by track, the old one gone, a text file of it written), a name that
  exists already was refused, and the playlist was deleted again by its name in another case. The ⋮ menu of the panel
  (edit, rename, delete) was tried by hand. A rename of a playlist of moderate length was tried by hand as well; the rename of a very long playlist (hundreds of tracks) was not.
- **Automation examples**: every example of the page was loaded as an automation or a script in the Home Assistant of
  the development setup (so that its structure is accepted), and the templates were evaluated on the real players.
  Two were run: the announcement (with a notification instead of the speech, on the amplifier) and the mute for the
  doorbell (the Pulse mini 2i stayed muted while a test switch was on and was unmuted when it went off). The ones
  that start music, clear lists, rename or delete were not run as automations: the actions they use were tried one
  by one.
- **What is playing**: the `now_playing` answer asked of both players while one played a song and the other was paused
  on a radio station (read-only): the song with its artist, album, CD quality and position, the station with its
  stream format, and the group left empty.
- **Track on air**: a radio station playing on the Pulse mini 2i, with its on-air track shown in the sidebar player, the
  mini player and the media player entity, next to the native app. The "search the library for the artist" button
  found the albums and tracks of an artist of the library, and gave only the "library only" notice between two songs
  (when the station sends no artist).
- **Group attributes**: the Séjour joined to the Pulse mini 2i while it played a station, then taken out again. Both
  media players showed their role and the name of the group, and `none` and no name once alone again. The station was
  not interrupted. The Séjour went from paused to stopped, which changes nothing it plays.
- **Genres in the search**: searching the library of the Pulse mini 2i for *dance*, *jazz*, *eurodance* and a typo
  (*dnace*) returns the genre first, and a typed Assist request (*play dance on mini 2i*) starts the genre shuffled,
  so it no longer begins with the same song.
- **Clear history**: the Clear buttons of the recent stations and of the recently played rows of the home page, with
  their confirmation, on the Pulse mini 2i.
- **Presets and inputs by name**: a preset by a word of its name, inputs by common names, and the error for a name
  that fits several inputs.

## Music services

Browsing a music service in the sidebar player and the media browser is generic: the player describes what the
service offers and the integration shows it. Only the services below were tried on a real account.

| Service | What was tried |
|---|---|
| Radio (the player's own radio directory) | browsing it in its many ways, playing stations on a chosen player, by hand in the sidebar player |
| TuneIn | browsing and playing stations, presets that start a station, by hand in the sidebar player |
| Radio Paradise | the available stations (about seven), choosing one to send the broadcast to the chosen player, a preset that starts one, by hand in the sidebar player |
| Amazon Music | browsing My Music (playlists, artists, albums, songs, genres), opening an album, the actions of an album, playing a song and an album, by hand in the sidebar player |

The other services (Deezer, Tidal, Qobuz...) are expected to work the same way but were not tried: if you use one,
please tell us in an [issue](https://github.com/xperseguers/bluos-companion/issues) what works and what does not.

## What is not tested

- other models and firmware, players with several secondary players in a group
- the amplifier switches on other amplifiers than the NAD C368 (the speaker outputs were checked through the
  amplifier's own answer, the sound itself was not listened to), and amplifiers without speaker outputs (simulated only)
- the favourites of the streaming services and favourite playlists, and the import of playlists exported in another
  format than `.m3u8` or from a library that is not organised as artist / album / file (the paths of Windows are
  covered by automated tests only)
- the accounts of the music services other than Amazon Music (Deezer, Tidal...)
- selecting the HDMI ARC input or using the sleep timer of the NODE
- the sidebar player in browsers and tablets other than the ones used during development, and live use on Home
  Assistant versions other than 2026.10 and 2026.11

If something does not work on your player, an [issue](https://github.com/xperseguers/bluos-companion/issues)
with the model and firmware helps a lot.
