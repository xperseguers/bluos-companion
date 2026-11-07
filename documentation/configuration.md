# Configuration

## Adding players

Players on your network are discovered: they appear under **Settings → Devices & services → Discovered**,
click **Add**.

To add one by hand, **Settings → Devices & services → Add integration → BluOS Companion**. If you have set
up players with the official Bluesound integration (even if it is disabled now), you can pick one of them
instead of typing its address. Otherwise enter the IP address of the player (the port is 11000 for all BluOS
players). Repeat for each player.

A player is identified by its MAC address: if its IP address changes, it is updated when the player is
discovered again, or when you add it again with the new address. A fixed IP address (or a DHCP reservation)
is still recommended.

## Options of a player

**Settings → Devices & services → BluOS Companion**, then the **gear icon** (Configure) at the right of the name of the player, for each player:

| Option | What it does |
|---|---|
| **Hidden services** | Hide, in the sidebar player, the sources you do not use (a music service you have no account for, Radio...). They stay available in the BluOS app. |
| **Maximum volume** | The highest volume (10 to 100) that Home Assistant will set: the sidebar player, the cards, voice and AI commands and the `media_player` services are limited. The BluOS app and the remote are not. Useful for a wall tablet that everybody can reach. |
| **Back up the playlists of this player** | Whether this player is a source of the playlist backup, see [Playlist backup and restore](backup-and-restore.md). When two players have the same playlist, the one added first is saved. |
| **Script to run before something starts playing** | An optional script that Home Assistant runs, and waits for, before something new plays and while the player is not playing yet. See below. |

### A script before something plays

A player that feeds an amplifier which is not a BluOS device (a standalone streamer plugged into an Onkyo, for
instance) cannot switch it on nor choose its input. Choose a Home Assistant **script** in this option and the
integration runs it first, and **waits until it has finished** before the player is asked to play.

- It applies to anything that starts playing: a preset, an album or a song from the sidebar player or the cards, a
  track of the queue, the play button, the `bluos_companion.play_preset` service and `media_player.play_media` /
  `media_player.media_play`. Adding to the queue without playing does not run it.
- It does **not** run while the player is already playing (the amplifier is then on), so changing track is not slowed
  down.
- The script receives the player as `player` (its `media_player` entity). If it fails, or takes more than a minute,
  the error is shown and nothing is played. Until the script has finished, nothing seems to happen: give it only what
  it needs.
- Everybody who can use the sidebar player or the cards starts it, administrator or not: only an administrator
  chooses which script runs.
- Use a script whose entity id is the name of the script (`script.onkyo_for_the_node` for the script
  `onkyo_for_the_node`), as the integration calls it as a service.

An example for an Onkyo (the entity `media_player.onkyo` comes from the Onkyo integration): switch the amplifier on
and wait a few seconds if it is off, then choose the input if it is not the one the streamer is plugged into, and
stop. Use the name of the input as the source list of your amplifier shows it.

```yaml
script:
  onkyo_for_the_node:
    alias: Onkyo for the NODE
    sequence:
      # 1. On, and a moment for it to wake up
      - if:
          - condition: state
            entity_id: media_player.onkyo
            state: "off"
        then:
          - action: media_player.turn_on
            target:
              entity_id: media_player.onkyo
          - wait_template: "{{ is_state('media_player.onkyo', 'on') }}"
            timeout: "00:00:20"
          - delay: "00:00:03"
      # 2. On the right input
      - if:
          - condition: not
            conditions:
              - condition: state
                entity_id: media_player.onkyo
                attribute: source
                state: "NET"
        then:
          - action: media_player.select_source
            target:
              entity_id: media_player.onkyo
            data:
              source: "NET"
```

## What each player gives Home Assistant

- A **media player** entity: play, pause, stop, previous, next, seek, volume (set, up, down), mute,
  shuffle, repeat, play media, select source, clear the queue, group and ungroup, and search media (for
  [voice and AI](voice-and-ai.md)). It shows the title, artist, album, cover and position.
- A **Mute** switch, the mute of the player itself (in a group, of that player only): on mutes, off unmutes, and
  `switch.toggle` flips it, which a media player cannot do, so one dashboard button or tile is enough. A player
  with a fixed volume has no such switch.
- A **sleep timer** select entity (off, 15, 30, 45, 60 or 90 minutes).
- An **Amplifier power** switch, for a player built into an amplifier that accepts network control (the NAD
  C368 with its BluOS module, for example): on, or off for standby. A **Speaker A** and a **Speaker B** switch
  (configuration entities) turn the speaker outputs on and off, only for the outputs the amplifier reports.
  There is nothing to configure: the amplifier is looked for at the address of the player when the integration
  starts, and a player that is not built into one has no such switch. Switching on takes about six seconds.
  The player itself stays reachable while the amplifier is in standby, and starting playback wakes the
  amplifier by itself. Volume, mute and inputs are not duplicated on purpose: the amplifier and its BluOS
  module share them, so the player's own controls are the amplifier's. The switches replace the old Home
  Assistant *NAD* integration: you can remove that one if you only used it to switch the amplifier (a volume
  window in dB that you set there is not reproduced, use the *Maximum volume* option).
- A **Tracks in library** sensor: the player only counts its tracks while it reads the library, so the sensor keeps
  the last count (empty until a first reindex) and shows the running count in its `indexing` attribute during a scan. The scan is followed closely only when started
  with the reindex button below; a scan started elsewhere (the BluOS app) is checked every 100 seconds or so and may be
  missed.
- A **Reindex music library** button, to run after you add music (press it from an automation to schedule it; in a
  group, the primary player reads the library, so the button of a secondary asks the primary), and a
  **Restart** button to restart the player. The restart button is disabled by default: enable it in the entity
  settings of the device.
- The **settings** the player offers, named as the player names them: listening mode, bass, treble, indicator
  brightness, Late Night... Which ones depend on the model (an amplifier such as the NAD C368 has almost none). They
  are configuration entities; the listening mode, bass and treble are enabled, enable the others from the entity
  settings of the device.
- The **media browser**, in the sidebar *Media* panel and in the media browser of the player's more-info
  dialog: library (with its favourites), saved playlists (with their covers), presets and the queue.

### Inputs

`source_list` holds the inputs the player reports. A player with a built-in amplifier (a NAD with a BluOS
module, for example) lists the inputs of the amplifier (TV, Phono, CD...) and its own. A standalone
streamer lists only its own (Bluetooth, HDMI ARC...). When a name exists twice (the Bluetooth of the module
and the Bluetooth of the amplifier), the module's one is called *Bluetooth (BluOS)*. An input can be chosen by its
exact name, or by a word or a common name such as *vinyl* for Phono, see [Developer tools](developer-tools.md).

The power of the amplifier (and its speaker outputs) are separate switches, see above.

### Groups

Use the standard `media_player.join` and `media_player.unjoin` actions, or the group screen of the sidebar
player. The group is shown in the `group_members` attribute (the primary player first). Only the primary
player of a group can add or remove players: the integration takes care of that. The volume of each
player of a group and the volume of the group are available in the sidebar player. The media player of a secondary
player shows **its own** volume and mute, not the group's. To mute or unmute a whole group, use the group button of
the sidebar player or the action `bluos_companion.mute_group` (see [Developer tools](developer-tools.md)).

Starting music on any player of a group (the sidebar player, `media_player.play_media`, voice or AI) plays it for
the **whole group**, whether you name the leader or a member. To play on one player alone, ungroup it first.

### Cover art

Covers are loaded through Home Assistant (the players speak plain HTTP), so they also work when you use
Home Assistant over HTTPS.
