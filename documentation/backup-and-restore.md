# Playlist backup and restore

The playlists you saved on a BluOS player live on that player. If it is reset or replaced, or if you move
your music to another server, they are lost. BluOS Companion keeps a **text copy** of them that Home
Assistant's own backup carries along, and can rebuild them.

## How the backup works

- Before **every Home Assistant backup** (automatic or manual), the integration writes one file per
  playlist in the folder `bluos_companion/playlists` of your Home Assistant configuration folder (the
  one with `configuration.yaml`). Home Assistant's backup then contains them, with no schedule to set up.
- You can also write them whenever you want with the action **BluOS Companion: Save the playlists as
  text files now** (`bluos_companion.backup_playlists`, Developer tools → Actions). It answers with the
  playlists it saved and their number of tracks.
- A playlist that cannot be read, or has no track, **keeps its previous file**: a player that is off or
  has lost its playlist never erases your backup.
- When two players have the same playlist, the one of the player added first is saved. A player can be
  left out in its options.

## The files

Standard `.m3u8` playlists, one per playlist, easy to read and to edit:

```
#EXTM3U
#PLAYLIST:Tuning
# Saved by BluOS Companion from the player "Living room" on 2026-10-29T14:34:01+00:00.
#EXTINF:228,Adele - Rolling in the Deep
#EXTALB:21
/var/mnt/192.168.1.20-Music/Adele/21/01 Rolling in the Deep.m4a
```

Each track is the file of your music share as the player sees it. The lines starting with `#` are for
reading and can be edited or removed. Only the paths matter when restoring.

## Restoring

The action **BluOS Companion: Restore playlists from the text files**
(`bluos_companion.restore_playlists`):

```yaml
action: bluos_companion.restore_playlists
data:
  entity_id: media_player.living_room   # the player to rebuild the playlists on
  playlists:                            # optional, all the files if left out
    - Tuning
  replace: false                        # optional
```

- It rebuilds each playlist on the player: it empties the queue, adds the files one by one and saves the
  queue under the name of the playlist. **The queue of that player is replaced**, because the player can
  only save its own queue as a playlist, so choose a player that is not playing (adding to an empty queue may
  start it for a moment).
- A playlist that **exists already is left alone**, unless you set `replace: true`. The old one is then
  deleted only after the new queue is ready.
- The answer tells what was restored (with the number of tracks the player found), what was skipped and
  which names have no file. If the player finds fewer files than the playlist lists, a warning in the log
  says so: the paths are probably wrong.
- Saved playlists belong to a player and are not shared live between players. Restore on the player you
  use as your main one.

## Moving your music to another server

If the address or the name of your music share changes, the paths in the playlists change, and the
playlists stop working. With the text files you do not have to recreate them:

1. Run **Save the playlists as text files now** *before* the move (or use the latest Home Assistant backup).
2. Move your music, and let the player index the new share.
3. In the `.m3u8` files, **replace the beginning of the paths** with a find and replace (for example
   `/var/mnt/192.168.1.20-Music/` by `/var/mnt/192.168.1.50-Music/`). Any text editor will do.
4. Run **Restore playlists**, with `replace: true` for the playlists that still exist on the player.

## Limits

- Only the entries the player can find are saved. Old playlists may hold entries for files that were moved or
  deleted; the player does not list them, so they cannot be saved (nor can they be played).
- Only the **saved playlists** of the players are covered, not the queue, the presets or the favourites.
- The files contain the names of your tracks and the paths of your music: treat them like any file of your
  Home Assistant backup.
