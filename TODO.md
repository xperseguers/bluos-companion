# Sidebar player: TODO

Branch `feature/sidebar-player`. Goal: bring the spirit of the official BluOS app into Home
Assistant as a sidebar panel, usable by every user, first target a wall-mounted tablet in kiosk
mode (touch friendly, no app switching). Plain JavaScript custom element, no Node toolchain.
Only BluOS Companion players are shown (no generic HA media entities).

Capabilities differ per player: input selection (TV, Phono...) exists only on players with a built-in
amplifier (like the NAD with its BluOS module); a standalone streamer plugged into an amplifier has none and
cannot switch the amplifier. The UI shows only what a player reports and never assumes an input list.

Rule for this file and the documentation: feature-level wording only, nothing private about the owner
(see `CLAUDE.md`).

Decisions: websocket API (`bluos_companion/*`) for the panel, library first (the streaming services come
for free from the player's own browse tree), panel not restricted to admins.

## P0 Foundation (done)
- [x] Panel registered in the sidebar (`panel_custom`, `require_admin=False`), files served from `frontend/`
- [x] Websocket: `subscribe` (live state of all players), `control`, `browse`, `play`
- [x] Frontend skeleton: player selector, browse grid with back navigation, now-playing bar

## P1 Core experience
- [x] Album and artist pages: play now / shuffle / add next / add last (from the player's context menus)
- [ ] Browse polish: sections (A-Z) jump bar (a "Show more" button exists for lists cut after a few pages)
- [x] Player picker: switch the target player from the now-playing bar (name, what it plays, group), instead of the header select
- [x] Search: library and services, results grouped Artists / Albums / Songs / Composers
- [x] Queue view: jump to a track, remove, reorder, clear, save as playlist
- [x] Jump around the library: from the playing track, a queue row or a song result, go to its album page or its artist page (back leads artist -> album -> home)
- [x] Home page: presets, recent albums and sources ("last played" is not available from the player)
- [x] Kiosk ergonomics: larger touch targets on touch screens and a full-screen "now playing" view (cover, transport, seek, volume, input, sleep timer). Not done: hiding the panel header, no hover-only controls were found
- [x] Options per player: hide the services you do not use (e.g. Deezer without an account)
- [x] Safety: maximum volume per player (option), enforced for the panel, the cards and the media player service; the BluOS app and the remote are not limited

## P2 Widgets for dashboards
- [x] Presets card (built, the playing preset is highlighted by matching what the player plays with the presets), replacing the owner's REST-based custom card (his tablet dashboard is the reference): a grid of square preset artworks (3 per row, rounded, thin border, tap = start the preset, the playing one highlighted), then a compact footer with the player name, its input select (BluOS, TV, Phono...), (no power button: no way to switch a player off was found) and a volume slider with play / pause. Options: player, columns, hide the footer, preset subset. Uses the preset images through the signed artwork proxy
- [x] Mini player card (cover, title, transport, volume) for one player
- [ ] Group / room picker card

## P2 Multi-room and inputs
- [x] Grouping UI: group / ungroup from the player picker, per-player volume and group volume (relative dB with `tell_slaves`). Tried live on the amp and the Pulse (group, group volume step, ungroup)
- [x] Input selection (TV, Phono, Bluetooth) in the full-screen view and in the presets card
- [x] Sleep timer in the full-screen view

## P2 Transfer playback
- [x] "Move playback" to another player, in the panel (bar and full-screen view) and in the player card: the player moves its queue and position, the source pauses, volumes stay. Only offered for a player that is playing. Tried live with a library album between the amp and the Pulse (position and queue carried over)

## P2 More from the player
- [x] Home page: "Recently played" (albums and songs), "Recent stations" and "Most used", titled by the player in the language of Home Assistant, then the presets, the latest albums and the sources. The Bluetooth input is playable from the sources
- [x] Playlists in the panel: open a playlist, list its tracks (tap = play from there, actions play now / shuffle / add next / add last), cover = first track, "Show more" on long lists, entries the player cannot find are skipped. Not done: delete (needs a decision on who may delete)
- [ ] Favourites menu (library favourites, other services), add / remove favourite
- [x] Playlist backup: text files (`.m3u8`, one per playlist) in `config/bluos_companion/playlists/`, written before every Home Assistant backup (so the HA backup contains them) and by the service `bluos_companion.backup_playlists`. Per-player option to leave a player out, the player added first wins for a playlist both have, an empty read keeps the previous file. Entries the player cannot find are not saved (it does not list them)
- [x] Playlist restore: service `bluos_companion.restore_playlists` (player, optional playlist names, `replace` off by default so an existing playlist is never touched unless asked). Per playlist: clear the queue, add each file, save the queue under the name; with `replace` the old playlist is deleted only after the new queue is ready. Warns when the player finds fewer files than the file lists (wrong paths). Tried live on the Pulse with a temporary playlist (new, skipped, replaced, deleted). Path changes are done by editing the files by hand. The players do not share saved playlists live: restore onto Séjour, the master

## P3 Polish and playlists
- [ ] Playlists: rename, delete and edit as far as the player allows (delete needs a decision on who may do it); optionally a read-only mode for non-admins
- [ ] en / fr translations of the panel (strings.json `common` plus a panel section), key-parity test
- [ ] Responsive layout, dark / light, accessibility
- [ ] README and `CLAUDE.md` documentation
- [ ] Last: make the README appealing for first-time users (what it does in a few lines, 4-6 good screenshots of the panel, the media browser and a dashboard card, install through HACS, short feature list). Screenshots to be taken at the end by the owner (or from the dev HA), without private data (IPs, names) and without third-party logos beyond what the player shows; keep the "not affiliated" notice

## Compatibility
- [ ] Try a standalone streamer (no built-in amplifier, possibly fixed volume, other firmware), read-only: no input select, fixed volume (sliders, steps and the maximum volume must cope), features the player lacks must simply not show. Results go to the local notes only

## Documentation plan
- [ ] "How it was tested" page (in the development documentation, summarised with a "Tested with" table in the README):
  - Automated: the pytest suite (about 260 tests with `pytest-homeassistant-custom-component`, the player is mocked), what it covers (client, config and options flow, entity, media browser, websocket API of the panel and cards, backup and restore, translations parity) and how to run it
  - Live, on real players: NAD C368 with the MDC2 BluOS-D module (everything), Bluesound Pulse Mini 2i (everything: grouping, move playback, queue, playlists, backup and restore with a temporary playlist), Bluesound NODE (playback with version 1.2.0 by the owner; the panel, cards and playlist work only through read-only checks: inputs, presets, playlists, home screen). Same firmware family 4.18 on all three
  - Not tested (say so and invite reports): other models and firmware, accounts of the music services (Deezer, Tidal...), selecting the NODE's HDMI ARC input, the sleep timer on the NODE, a player with several secondaries, the panel in other browsers and on other tablets, Home Assistant versions other than the one used
  - Device names as plain text, no logos or brand images, next to the "not affiliated" notice; say nothing about whose devices they are
- [ ] Short `README.md` (pitch, screenshots, HACS install, quick start) that links to pages in a folder named `documentation/` (not `docs/`, which is kept out of git): sidebar panel and kiosk use, dashboard cards (presets, player) with their options, playlist backup / restore and moving the NAS (edit the paths in the `.m3u8` files), options of a player (hidden services, maximum volume, backup flag), Home Assistant developer tools (the services `backup_playlists`, `restore_playlists`, the `media_player` services with our media ids, attributes such as `source_list` and `group_members`, templates), troubleshooting, development (dev setup, tests)
- [x] Decision: public documentation only describes what the integration does for users, technical notes about the players stay local. Squash the local commits before the first push. Contacting the player vendor is left for later, once the integration is widely used
## Publication: HACS default store (at the end, with help)
Submission is a pull request to `hacs/default` adding the repository to the `integration` list, after the repository passes HACS's checks. State today:
- [ ] `LICENSE` file at the root with an OSI-approved license (none yet; the README only credits the icons, which are Apache-2.0). To choose: MIT or Apache-2.0 are the usual picks, any OSI license is accepted
- [ ] GitHub Actions on the repository: the HACS action (`hacs/action`, category `integration`) and hassfest (`home-assistant/actions/hassfest`), both must pass, plus the test suite (none in `.github/workflows/` yet)
- [ ] A GitHub *release* (not only a tag) for the version in `manifest.json` (tags 1.0.0, 1.1.0, 1.2.0 exist locally; check they are releases). The panel and cards are a big step: bump the version (2.0.0 or 1.3.0) and write release notes
- [ ] `hacs.json`: `name` and `homeassistant` exist; set the minimum Home Assistant version to what the code really needs (it uses `ConfigEntry.created_at`, `async_loaded_entries`, the backup platform hooks; to be checked and tested against that version)
- [ ] `manifest.json`: required keys are there (domain, name, codeowners, documentation, issue_tracker, version); hassfest will check the order of the keys and the translations
- [ ] Repository settings: public, a description, topics (`home-assistant`, `hacs`, `bluos`...), issues enabled
- [ ] Brand images: `custom_components/bluos_companion/brand/` exists; HACS validates brands, check what it accepts today (local brand folder or the `home-assistant/brands` repository)
- [ ] README for first-time users (see the README task above) with install through HACS and the screenshots
- [ ] Naming: the BluOS API policy forbids BluOS names or marks in an integration's name, the owner chose "BluOS Companion" knowingly. Keep the "not affiliated" notice, never use Lenbrook, Bluesound or BluOS logos, and expect a reviewer to raise the name: be ready to answer or to rename (the domain `bluos_companion` would change too)
- [ ] Owner of the repository submits the pull request himself (the HACS default repository requires it to be the owner or a major contributor), following the current checklist at https://hacs.xyz/docs/publish/include/ (re-read it then, rules change)

## Ideas to discuss later
- [x] Voice and AI: "play Adele", "play NRJ", "play the playlist Tuning" through Assist (typed or spoken) and AI conversation agents. The player supports `media_player.search_media`, so Home Assistant's search-and-play intent finds an artist, album, song, saved playlist or radio preset and plays the best match. Names are compared without case, accents or punctuation; the artist plays as "play all". Tried read-only on the real library; typing it in Assist plays on the player (see the notes for how to try)
