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

### Choosing an input

`media_player.select_source` takes the exact name of an input (the `source_list` attribute), but also the name
without its case or accents, a word of it (`wingo` for *Wingo TV*) and a common way to say it: `vinyl` or
`turntable` for *Phono*, `optical`, `hdmi`, `tv` (an HDMI ARC input), `analog` or `aux`, `bluetooth`, `cd`, `dvd`.
When a name fits several inputs (`tv` with two TV inputs), the action fails and lists them: use the exact name.

## Searching

`media_player.search_media` returns what a name matches, best match first (artists, albums, songs, saved
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

## An automation

Start a radio preset in the morning, at a modest volume, without a tablet:

```yaml
automation:
  - alias: Radio at 7
    triggers:
      - trigger: time
        at: "07:00:00"
    actions:
      - action: media_player.volume_set
        target: { entity_id: media_player.kitchen }
        data: { volume_level: 0.2 }
      - action: media_player.play_media
        target: { entity_id: media_player.kitchen }
        data:
          media_content_type: music
          media_content_id: media-source://bluos_companion/<entry id>/preset/1
```

And a sleep timer for the evening: use the `select` entity of the player (`select.living_room_sleep_timer`)
with `select.select_option`.
