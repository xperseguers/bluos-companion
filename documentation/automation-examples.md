# Automation examples

Ideas to copy and change. They use the actions of BluOS Companion described in
[Developer tools](developer-tools.md): replace the entities (`media_player.living_room`,
`switch.living_room_mute`...) and the names (the preset, the genre, the playlist) with yours. The entity ids of your
players are in Settings → Devices & services → BluOS Companion.

Every example is a complete automation or script: paste it in the YAML editor of a new automation (the three dots
at the top right) or script.

## Starting music

### Radio when you get home

Start a preset when you arrive, unless something already plays. A preset is chosen by its name or its number.

```yaml
alias: Radio when I get home
triggers:
  - trigger: state
    entity_id: person.me
    to: home
conditions:
  - condition: not
    conditions:
      - condition: state
        entity_id: media_player.living_room
        state: playing
actions:
  - action: bluos_companion.play_preset
    data:
      entity_id: media_player.living_room
      preset: Rouge FM
```

### A genre every weekday morning

A gentle start: set a low volume, then play a genre shuffled and replace what was in the queue.

```yaml
alias: Jazz on weekday mornings
triggers:
  - trigger: time
    at: "07:00:00"
conditions:
  - condition: time
    weekday: [mon, tue, wed, thu, fri]
actions:
  - action: media_player.volume_set
    target:
      entity_id: media_player.kitchen
    data:
      volume_level: 0.2
  - action: bluos_companion.play_genre
    data:
      entity_id: media_player.kitchen
      genre: Jazz
      shuffle: true
      clear_queue: true
```

`play_playlist` works the same for a saved playlist (`playlist: Morning Jazz`). A genre or a playlist asked for by
name from a voice assistant is shuffled for you, see [Voice and AI](voice-and-ai.md).

### Music everywhere

Group the kitchen with the living room, then play. In a group, the music plays for the whole group.

```yaml
alias: Music everywhere
triggers:
  - trigger: state
    entity_id: input_boolean.party
    to: "on"
actions:
  - action: media_player.join
    target:
      entity_id: media_player.living_room
    data:
      group_members:
        - media_player.kitchen
  - action: bluos_companion.play_genre
    data:
      entity_id: media_player.living_room
      genre: Dance
      shuffle: true
      clear_queue: true
```

## Stopping music

### Everybody left

Pause the music when the last person leaves.

```yaml
alias: Pause when nobody is home
triggers:
  - trigger: numeric_state
    entity_id: zone.home
    below: 1
conditions:
  - condition: state
    entity_id: media_player.living_room
    state: playing
actions:
  - action: media_player.media_pause
    target:
      entity_id: media_player.living_room
```

### Quiet while the doorbell rings

Mute the player with its **Mute** switch, then put it back, unless it was already muted. The wait ends when the
doorbell stops, or after 30 seconds.

```yaml
alias: Mute for the doorbell
triggers:
  - trigger: state
    entity_id: binary_sensor.doorbell
    to: "on"
conditions:
  - condition: state
    entity_id: switch.living_room_mute
    state: "off"
actions:
  - action: switch.turn_on
    target:
      entity_id: switch.living_room_mute
  - wait_for_trigger:
      - trigger: state
        entity_id: binary_sensor.doorbell
        to: "off"
    timeout: "00:00:30"
    continue_on_timeout: true
  - action: switch.turn_off
    target:
      entity_id: switch.living_room_mute
```

## Knowing what plays

### Announce what plays

`now_playing` answers with data and a sentence in the language of Home Assistant, ready for a text to speech
announcement. Make it a script and call it from a button, a voice sentence or an automation.

```yaml
alias: Say what plays in the kitchen
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

The sentence is *Skyfall by Adele* for a song, the name of the station for a radio, or *Nothing is playing*. The
answer also holds the artist, the album, the position, the volume and the players the kitchen is grouped with: see
[Developer tools](developer-tools.md).

### Tell the quality of what plays

The media player has attributes for what the player says of the stream: `service`, `service_name`, `stream_format`,
`quality` and `preset_name`. This notifies you when a song in CD or high resolution quality starts.

```yaml
alias: CD quality
triggers:
  - trigger: state
    entity_id: media_player.living_room
    attribute: media_title
conditions:
  - condition: state
    entity_id: media_player.living_room
    state: playing
  - condition: template
    value_template: "{{ state_attr('media_player.living_room', 'quality') in ['cd', 'hd'] }}"
actions:
  - action: persistent_notification.create
    data:
      title: "{{ state_attr('media_player.living_room', 'media_title') }}"
      message: >-
        {{ state_attr('media_player.living_room', 'media_artist') }},
        {{ state_attr('media_player.living_room', 'stream_format') }}
```

Other conditions you can build the same way: a radio plays
(`{{ is_state_attr('media_player.living_room', 'service', 'TuneIn') }}`), or a given preset plays
(`{{ is_state_attr('media_player.living_room', 'preset_name', 'Rouge FM') }}`).

## Housekeeping

### Start every day with a clean home page

Empty the recent stations and the recently played lists at night. The lists are emptied on the player, for everyone
who uses it.

```yaml
alias: Clear the history at night
triggers:
  - trigger: time
    at: "03:00:00"
actions:
  - action: bluos_companion.clear_history
    data:
      entity_id: media_player.living_room
      what: both
```

Use `stations` or `played` to clear only one of the two lists. In the same way the music library can be re-read every
night with the *Reindex music library* button of the player (`button.press`).

### Archive a playlist at the end of the year

Rename a playlist with the year in its name, from a script. A text file of the playlist is written first, and the
old name only goes once the copy is complete.

```yaml
alias: Archive the party playlist
sequence:
  - action: bluos_companion.rename_playlist
    data:
      entity_id: media_player.living_room
      playlist: Party
      new_name: "Party {{ now().year }}"
```

`delete_playlist` deletes one by its name, with no confirmation (a text file of it is kept, and
`bluos_companion.restore_playlists` brings it back). The player must have the playlist: an unknown name is an error.

## On a dashboard

The same actions can be put on a dashboard without any automation: the
[play button card](cards.md) plays a genre, a preset or a playlist with one tap, and a tile with the **Mute** switch
flips the mute of a player (`switch.toggle`, Home Assistant has no such toggle for a media player):

```yaml
type: tile
entity: switch.living_room_mute
name: Mute
tap_action:
  action: toggle
```
