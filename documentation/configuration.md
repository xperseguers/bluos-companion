# Configuration

## Adding players

**Settings → Devices & services → Add integration → BluOS Companion**, then enter the IP address of the
player. The port is 11000 for all BluOS players. Repeat for each player.

A player is identified by its MAC address: if its IP address changes, add it again with the new address
and the existing entry is updated. A fixed IP address (or a DHCP reservation) is recommended.

## Options of a player

**Settings → Devices & services → BluOS Companion → Configure** (for each player):

| Option | What it does |
|---|---|
| **Hidden services** | Hide, in the sidebar player, the sources you do not use (a music service you have no account for, Radio...). They stay available in the BluOS app. |
| **Maximum volume** | The highest volume (10 to 100) that Home Assistant will set: the sidebar player, the cards, voice and AI commands and the `media_player` services are limited. The BluOS app and the remote are not. Useful for a wall tablet that everybody can reach. |
| **Back up the playlists of this player** | Whether this player is a source of the playlist backup, see [Playlist backup and restore](backup-and-restore.md). When two players have the same playlist, the one added first is saved. |

## What each player gives Home Assistant

- A **media player** entity: play, pause, stop, previous, next, seek, volume (set, up, down), mute,
  shuffle, repeat, play media, select source, clear the queue, group and ungroup, and search media (for
  [voice and AI](voice-and-ai.md)). It shows the title, artist, album, cover and position.
- A **sleep timer** select entity (off, 15, 30, 45, 60 or 90 minutes).
- The **media browser**, in the sidebar *Media* panel and in the media browser of the player's more-info
  dialog: library, saved playlists (with their covers), presets and the queue.

### Inputs

`source_list` holds the inputs the player reports. A player with a built-in amplifier (a NAD with a BluOS
module, for example) lists the inputs of the amplifier (TV, Phono, CD...) and its own. A standalone
streamer lists only its own (Bluetooth, HDMI ARC...). When a name exists twice (the Bluetooth of the module
and the Bluetooth of the amplifier), the module's one is called *Bluetooth (BluOS)*.

Switching an amplifier on or off is not possible with this integration.

### Groups

Use the standard `media_player.join` and `media_player.unjoin` actions, or the group screen of the sidebar
player. The group is shown in the `group_members` attribute (the primary player first). Only the primary
player of a group can add or remove players: the integration takes care of that. The volume of each
player of a group and the volume of the group are available in the sidebar player.

Starting music on any player of a group (the sidebar player, `media_player.play_media`, voice or AI) plays it for
the **whole group**, whether you name the leader or a member. To play on one player alone, ungroup it first.

### Cover art

Covers are loaded through Home Assistant (the players speak plain HTTP), so they also work when you use
Home Assistant over HTTPS.
