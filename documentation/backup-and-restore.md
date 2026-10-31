# Playlist backup, restore and import

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

## Importing playlists from Apple Music

If you build your playlists in **Apple Music** (or iTunes) and your music is on the share the player reads, you
can bring them to the player:

1. In the Music app, select a playlist and choose **File → Library → Export Playlist…**, with the format **M3U**
   (`.m3u8`).
2. Put the file in the folder `bluos_companion/import` of your Home Assistant configuration folder (the one with
   `configuration.yaml`; the folder is created the first time you run the action).
3. Run the action **BluOS Companion: Import playlists exported from another music player** and choose a player
   that is not playing. For every file, it converts the paths of your computer into the ones of the share,
   writes the playlist like a backup file, and builds it on the player.

The paths are converted by themselves: the integration works out the folder of your music on the computer
(the beginning of the paths that is common to all your files) and finds where the same folder is for the player,
by looking for one of your tracks among the files of the player. It also takes care of the accents: a Mac writes
`é` as two characters in its file names, while a share usually holds one. If your music is not found, or if you
want to be sure, give the two folders yourself:

```yaml
action: bluos_companion.import_playlists
data:
  entity_id: media_player.living_room
  source_path: /Users/me/Music/Music/Media.localized/Music/
  library_path: /var/mnt/192.168.1.20-Music/Music/
```

- A playlist that already exists on the player (or already has a file) is left alone, unless you set
  `replace: true`. With `restore: false` the files are only converted, so that you can look at or change them
  and use **Restore playlists** later.
- Tracks that are not in the folder of your music (a file on another disk, a song of the Apple Music catalogue
  that you have no file for) are left out, and the action says how many.
- The player has to know the files: put the music on the share and let it index it first. The result of the action says
  how many files the player did not find (`files_not_found`), and the log has a warning: such files are not in the
  player's library (not indexed yet, or the share is not the one the player reads).
- The result of the action lists, for each playlist, how many tracks were converted and left out.

## Limits

- Only the entries the player can find are saved. Old playlists may hold entries for files that were moved or
  deleted; the player does not list them, so they cannot be saved (nor can they be played).
- Only the **saved playlists** of the players are covered, not the queue, the presets or the favourites.
- The import reads `.m3u8` files with the folders `Artist/Album/File` of Apple Music and iTunes. Another way to organise
  the music works if you give `source_path` and `library_path`.
- The files contain the names of your tracks and the paths of your music: treat them like any file of your
  Home Assistant backup.
