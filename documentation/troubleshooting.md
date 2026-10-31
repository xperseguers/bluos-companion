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

### "Artwork Too Large" instead of the cover

A cover embedded in a music file must stay **under 600 KB** (600 KiB, 614,400 bytes). With a heavier one the
player shows a placeholder reading "Artwork Too Large, Please Keep Artwork Under 600KB" instead of the cover,
in its own app as well as here. Tested with a library on a network share, on an amplifier with a BluOS module and on a streamer, both on firmware 4.18:

- The weight of the embedded picture is what counts: pictures up to 613,000 bytes showed, from 615,000
  bytes up they did not. The dimensions did not matter (from 300 x 300 up to 3000 x 3000 all showed), nor did
  the kind of JPEG (baseline or progressive, 4:2:0 or 4:4:4, grayscale, CMYK) or a PNG picture.
- To stay well below the limit, a square cover of 1000 x 1000 pixels saved as a JPEG is usually between 100
  and 400 KB. Reduce the quality or the dimensions of the picture, write it again into the file, then reindex
  the library (the *Reindex music library* button of the player) for the player to read it again.
- To find every album concerned, press the button **Check album covers** on the device page of the player
  (Settings → Devices), or run the service **BluOS Companion: Check the album covers** (Developer tools →
  Actions, choose the player), which waits for the result and returns the list. The button works in the
  background and the sensor shows the outcome. The check reads the cover of each album, a few at a time, and
  lists those the player replaced: about three minutes for 1,900 albums, so it only runs when you ask, and a
  second check cannot start before the first one ends. The sensor *Covers too large* of the player keeps the
  count of the last check (with the albums as an attribute), which an automation can use to warn you, for
  example after you add music. The check recognises the player's placeholder picture: if your player shows
  another one, the albums are not found, please report it.

  To see **which albums**: open the sensor *Covers too large* (on the device page of the player, under
  *Diagnostic*) and look at its attributes, the `albums` list holds the first 25 as "Artist - Album" (the
  attributes survive a restart). For the complete list, run the service from Developer tools → Actions: its
  response lists every album with its artist. For a warning when a check finds something:

  ```yaml
  triggers:
    - trigger: numeric_state
      entity_id: sensor.living_room_covers_too_large
      above: 0
  actions:
    - action: notify.notify
      data:
        message: "Covers too large: {{ state_attr('sensor.living_room_covers_too_large', 'albums') | join(', ') }}"
  ```
- A damaged picture (pictures downloaded from the internet sometimes are) does not give that placeholder. It
  shows as far as it can be read: a picture cut short shows its top part and the rest is flat grey, a damaged
  header can give wrong colours. A missing end marker alone is harmless. If a cover looks cut or discoloured,
  find the picture again or save it again from an image editor, write it into the file and reindex.
- A cover that does not show at all and is lighter than 600 KB is something else: a file without artwork, or
  a file the player has not indexed yet.

## A playlist looks empty or has fewer tracks than it should

Old playlists may keep entries for files that were moved or deleted. The player does not list those, so they
neither show nor play (and they cannot be backed up). Rebuild the playlist, or restore it from a text backup
after fixing the paths, see [Playlist backup and restore](backup-and-restore.md).

## No input select, no presets, no *Presets* row

- The inputs shown are the ones the player reports. A standalone streamer has no amplifier inputs.
- Presets belong to each player. A player without presets has no presets row, choose another player or add
  presets to it in the BluOS app.
- A service you do not use can be hidden in the options of the player.

## No *Amplifier power* switch

The switch only exists for a player built into an amplifier that accepts network control, and it is looked for
once, when the integration starts. If the amplifier was unreachable then, or if you enabled its network control
afterwards, reload the integration (Settings → Devices & services → BluOS Companion → the three dots of the
player → Reload). A streamer plugged into an amplifier has no such switch: it cannot switch the amplifier.

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
