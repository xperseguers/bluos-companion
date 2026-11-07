# Developer tools and automations

Everything the integration offers can be tried in **Developer tools → Actions**, and used in automations
and scripts.

## Standard media player actions

BluOS Companion players are normal `media_player` entities, so the usual actions work:
`media_player.media_play`, `media_pause`, `media_next_track`, `volume_set`, `volume_up`,
`volume_mute`, `shuffle_set`, `repeat_set`, `select_source`, `clear_playlist`, `join` and `unjoin`.

```yaml
action: media_player.select_source
target:
  entity_id: media_player.living_room
data:
  source: Bluetooth
```

```yaml
action: media_player.join
target:
  entity_id: media_player.living_room   # becomes the primary player of the group
data:
  group_members:
    - media_player.kitchen
```

The volume actions are limited by the **maximum volume** option of the player.

### Muting a whole group

`media_player.volume_mute` only mutes the player it targets. To mute or unmute **every player of a group** in one
go, use `bluos_companion.mute_group` with any member of the group (a player that is not grouped is muted alone):

```yaml
action: bluos_companion.mute_group
data:
  entity_id: media_player.living_room
  mute: true
```

To toggle a mute, use a template: `mute: "{{ not is_state_attr('media_player.living_room', 'is_volume_muted', true) }}"`.
In a group, the volume and the mute of **each** player are its own (a secondary player does not show the
volume or the mute of the group).

## Playing something

`media_player.play_media` plays what the media browser offers. The easiest way to get the right values:
in Developer tools → Actions, choose `media_player.play_media`, click **Choose media**, browse your
library, a preset or a playlist, and pick it: the YAML is filled in for you.

```yaml
action: media_player.play_media
target:
  entity_id: media_player.living_room
data:
  media_content_type: music
  media_content_id: media-source://bluos_companion/<entry id>/preset/3
```

Presets are `.../preset/<number>` and queue positions `.../queue/<position>`. For everything else, copy the
value the picker gives you.

`media_content_id` can also be **a name**: the best match of a search is played (`media_content_type: artist`,
`album`, `track` or `playlist` narrows it, `music` does not). It fails with "No results found" when nothing
matches.

### What the player is playing

Besides the usual media player attributes (title, artist, album, volume...), the media player entity tells what the
player says of what it plays. An attribute is missing when the player does not give it.

| Attribute | Example | What it is |
|---|---|---|
| `service` | `TuneIn`, `LocalMusic`, `Deezer` | the music service or the library |
| `service_name` | `TuneIn`, `Library` | the name the player gives it |
| `stream_format` | `AAC 128 kb/s`, `Apple Lossless 16/44.1` | the format of the stream or the file |
| `quality` | `cd`, `hd`, `128` | `cd` and `hd` for lossless music, otherwise a bit rate |
| `preset_name` | `Rouge FM` | the preset that is playing, when one is |

```yaml
# In a template: say when a station or a CD quality song plays
{{ state_attr('media_player.living_room', 'service') == 'TuneIn' }}
{{ state_attr('media_player.living_room', 'quality') in ['cd', 'hd'] }}
```

### Asking what is playing

`bluos_companion.now_playing` answers what a player plays, as data a script can use, with nothing changed on the
player. It is an action with a **response**, so use `response_variable`:

```yaml
action: bluos_companion.now_playing
data:
  entity_id: media_player.living_room
response_variable: playing
```

`playing` then holds: `player` (its name), `state` (`playing`, `paused`, `buffering` or `idle`), `title`, `artist`,
`album`, `service`, `service_name`, `stream_format`, `quality`, `preset_name`, `position` and `duration` (seconds),
`queue_position` (from 1), `shuffle`, `repeat` (`off`, `all` or `one`), `volume` (0 to 100, `none` for a fixed volume),
`muted`, `group_name` and `grouped_with` (the names of the other players of the group). Every key is always there,
`none` when the player does not say (a radio has no album). `text` is a sentence ready to speak, in the language of
Home Assistant: *Skyfall by Adele*, the name of the station, or *Nothing is playing*.

```yaml
# Announce what plays in the kitchen on a speaker of your choice
sequence:
  - action: bluos_companion.now_playing
    data:
      entity_id: media_player.kitchen
    response_variable: playing
  - action: tts.speak
    target:
      entity_id: tts.home_assistant_cloud
    data:
      media_player_entity_id: media_player.living_room
      message: "{{ playing.text }}"
```

### Playing a preset

`bluos_companion.play_preset` starts a preset by its **number** or its **name**, with nothing to look up first:

```yaml
action: bluos_companion.play_preset
data:
  entity_id: media_player.living_room
  preset: Rouge FM    # or 2
```

A name is understood without its case or accents, and a word of it is enough when only one preset has it
(`rouge`). A number is the number of the preset on the player. When the name fits several presets or none, the
action fails and says which presets there are. In a group, the music plays for the whole group.

### Playing a genre

`bluos_companion.play_genre` plays a genre of the music library by its **name**, the same as *Play now* (or
*Shuffle*) on the page of a genre in the sidebar player:

```yaml
action: bluos_companion.play_genre
data:
  entity_id: media_player.living_room
  genre: Dance
  shuffle: true       # optional, off by default
  clear_queue: true   # optional, off by default: replace the queue instead of adding to it
```

A name is understood without its case or accents, and a word of it is enough when only one genre has it
(`country` for *Folk, World, & Country*); the exact name always wins (*Alternative* is not ambiguous with
*Alternative & Punk*). When the name fits several genres or none, the action fails and says so. The genre is added
to the queue and starts playing, or replaces the queue with `clear_queue: true` (an unknown genre never empties
it), in a group for the whole group. `media_player.play_media` does the same with
`media_content_type: genre` and the name as `media_content_id`, but always shuffled (as voice and AI do), where
`play_genre` plays in order unless you ask for `shuffle`.

### Playing a playlist

`bluos_companion.play_playlist` plays a saved playlist by its **name**, the same way as `play_genre` (case and
accents are not needed, a word is enough when only one playlist has it, the options `shuffle` and `clear_queue` are
the same):

```yaml
action: bluos_companion.play_playlist
data:
  entity_id: media_player.living_room
  playlist: Morning Jazz
  shuffle: true
  clear_queue: true
```

### Clearing the history

`bluos_companion.clear_history` empties the list of **recent stations** and/or of what was **recently played** on a
player, like the *Clear* buttons of the home page (which ask for a confirmation: the action does not):

```yaml
action: bluos_companion.clear_history
data:
  entity_id: media_player.living_room
  what: both    # stations, played or both (the default)
```

It is cleared for everyone who uses the player, so a nightly automation is a way to start every day with a clean
home page.

### Renaming and deleting a playlist

```yaml
action: bluos_companion.rename_playlist
data:
  entity_id: media_player.living_room
  playlist: Morning Jazz
  new_name: Jazz for the morning
---
action: bluos_companion.delete_playlist
data:
  entity_id: media_player.living_room
  playlist: Jazz for the morning
```

The name of the playlist must be the exact one (its case and accents do not matter). `rename_playlist` copies the
playlist under the new name and deletes the old one only when the copy has the same tracks in the same order,
otherwise it fails and the old playlist stays. `delete_playlist` has no confirmation. Both write a text file of the
playlist first, in the folder of the [playlist backup](backup-and-restore.md).

### Choosing an input

`media_player.select_source` takes the exact name of an input (the `source_list` attribute), but also the name
without its case or accents, a word of it (`wingo` for *Wingo TV*) and a common way to say it: `vinyl` or
`turntable` for *Phono*, `optical`, `hdmi`, `tv` (an HDMI ARC input), `analog` or `aux`, `bluetooth`, `cd`, `dvd`.
When a name fits several inputs (`tv` with two TV inputs), the action fails and lists them: use the exact name.

## Searching

`media_player.search_media` returns what a name matches, best match first (artists, albums, songs, genres, saved
playlists and presets), without playing anything. It is what Assist uses, see [Voice and AI](voice-and-ai.md).

```yaml
action: media_player.search_media
target:
  entity_id: media_player.living_room
data:
  search_query: adele
  media_filter_classes: [artist]   # optional: artist, album, track, playlist
```

## Playlists

```yaml
action: bluos_companion.backup_playlists
```

```yaml
action: bluos_companion.restore_playlists
data:
  entity_id: media_player.living_room
  playlists: [Tuning]
  replace: false
```

See [Playlist backup and restore](backup-and-restore.md). Both actions can return a response
(`response_variable` in a script).

## Attributes and templates

Besides the standard attributes of a media player (`media_title`, `media_artist`, `media_album_name`,
`media_position`, `volume_level`, `is_volume_muted`, `shuffle`, `repeat`, `app_name`...):

- `source_list` and `source`: the inputs, and the active one
- `group_members`: the players that play together, the primary first (nothing when alone)

```jinja
{{ state_attr('media_player.living_room', 'source_list') }}
{{ state_attr('media_player.living_room', 'group_members') | length > 1 }}
{{ state_attr('media_player.living_room', 'media_title') }}
```

## Automations

Examples to copy, with the actions above, are on their own page: [Automation examples](automation-examples.md)
(radio when you arrive, a genre every morning, music everywhere, mute for the doorbell, announce what plays, clearing
the history at night, archiving a playlist...).

And a sleep timer for the evening: use the `select` entity of the player (`select.living_room_sleep_timer`)
with `select.select_option`.
