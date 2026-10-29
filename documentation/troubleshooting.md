# Troubleshooting

## The player cannot be added

- Check that the player answers on the network: open `http://<ip>:11000/SyncStatus` in a browser, it should show
  a short XML text. If not, the address is wrong or Home Assistant cannot reach the player (another VLAN or
  subnet, a firewall, a guest network).
- Use the address of the BluOS player itself. For a NAD with a BluOS module that is the address of the module.
- If the address changed, add the player again with the new address: it updates the existing entry.

## The sidebar player or a card looks old after an update

The browser keeps the old script. Reload the page without cache (Cmd/Ctrl + Shift + R). A tablet in kiosk mode:
reload the page, or clear the cache of its browser or app.

## No covers

Covers are fetched by Home Assistant from the player and sent to your browser. If a cover is missing for a
track the player itself has none (a file without artwork). Playlists show the cover of their first track:
a playlist without any track the player can find has no cover.

## A playlist looks empty or has fewer tracks than it should

Old playlists may keep entries for files that were moved or deleted. The player does not list those, so they
neither show nor play (and they cannot be backed up). Rebuild the playlist, or restore it from a text backup
after fixing the paths, see [Playlist backup and restore](backup-and-restore.md).

## No input select, no presets, no *Presets* row

- The inputs shown are the ones the player reports. A standalone streamer has no amplifier inputs.
- Presets belong to each player. A player without presets has no presets row, choose another player or add
  presets to it in the BluOS app.
- A service you do not use can be hidden in the options of the player.

## Volume cannot go higher

The **maximum volume** option of the player (Configure) limits Home Assistant, including the sliders, voice
commands and automations. Raise it, or use the BluOS app or the remote.

## Voice or AI finds nothing

See [Voice and AI](voice-and-ai.md): the player must be exposed to Assist, say its name as it is written, and
the search can be tried in Developer tools → Actions with `media_player.search_media`.

## The backup files are not created

- The files appear in the folder `bluos_companion/playlists` of the Home Assistant configuration folder when a
  backup runs, or when you call `bluos_companion.backup_playlists`.
- A playlist with no track the player can find is not written (the previous file is kept).
- The option **Back up the playlists of this player** must be on for at least one player.

## Restoring says "found fewer files"

The paths in the file do not match the music share as the player sees it. Compare a path of the file with the
path of a track of that player and fix the beginning of the paths in the file, then restore again with
`replace: true`.

## Reporting a problem

Open an issue at https://github.com/xperseguers/bluos-companion/issues with:

- the version of the integration and of Home Assistant,
- the model and firmware of the player,
- what you did, what you expected and what happened (a screenshot helps),
- the relevant lines of the log (**Settings → System → Logs**). For more details add to
  `configuration.yaml` and restart:

  ```yaml
  logger:
    logs:
      custom_components.bluos_companion: debug
  ```

Please remove addresses and names you prefer to keep private before you post logs or screenshots, and do not
paste material you do not have the right to share.
