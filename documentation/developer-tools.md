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
