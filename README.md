# BluOS Companion

A Home Assistant integration for players running BluOS (NAD, Bluesound, DALI...). It brings much of
the BluOS controller app into Home Assistant: a **sidebar player** made for a wall tablet, **dashboard
cards**, search and **voice** control, playlists with a **text backup** that Home Assistant's own
backup carries along.

> This project is independent. It is not affiliated with, endorsed by or sponsored by Lenbrook
> Industries or the BluOS brand. BluOS, NAD, Bluesound and the other names are trademarks of their
> respective owners and are only used to say which players the integration works with.

## What you get

- **A sidebar player** open to every user, ideal for a kiosk tablet: home page, library with an A–Z bar,
  search, queue, playlists with covers, group and volume of each player, move the music to another
  player. [Read more](documentation/panel.md)
- **Dashboard cards**: the presets of a player as a grid, and a compact player.
  [Read more](documentation/cards.md)
- **Voice and AI**: "play Adele on Kitchen" through Assist or an AI agent, with tolerance for typos.
  [Read more](documentation/voice-and-ai.md)
- **Playlist backup and restore** as text files, included in every Home Assistant backup, so that the
  playlists survive a reset of the player or a move of your music share.
  [Read more](documentation/backup-and-restore.md)
- **A normal media player** for every player: play, pause, seek, volume, shuffle, repeat, cover art,
  inputs, grouping, a sleep timer and the media browser. [Read more](documentation/configuration.md)
- English, French and German. Status is pushed by the player, no heavy polling. Cover art goes
  through Home Assistant, so it works over HTTPS.

| | |
|---|---|
| ![Home page of the panel](documentation/images/panel-home-scrolled.jpg) | ![Library with the A–Z bar](documentation/images/panel-artists-letter.jpg) |
| ![Full-screen view for a wall tablet](documentation/images/panel-fullscreen.jpg) | ![Dashboard cards](documentation/images/cards-dashboard.jpg) |

## Requirements

- A recent Home Assistant (developed and tested with 2026.10)
- A BluOS player reachable from Home Assistant on your network (TCP port 11000), ideally with a fixed
  IP address or a DHCP reservation

## Installation

### With HACS (custom repository)

1. In HACS, open the menu (three dots) → **Custom repositories**.
2. Add `https://github.com/xperseguers/bluos-companion` with the category **Integration**.
3. Search for *BluOS Companion*, download it and restart Home Assistant.

### Manually

Copy the folder `custom_components/bluos_companion` of this repository into the `custom_components`
folder of your Home Assistant configuration (next to `configuration.yaml`) and restart.

## Quick start

1. **Settings → Devices & services → Add integration → BluOS Companion**, and enter the IP address of a
   player. Repeat for each player (a player is identified by its MAC address, so a new IP address just
   updates the existing entry).
2. Open **BluOS Companion** in the sidebar. Pick the player with the button in the bottom bar.
3. On a dashboard, **Add card** and pick *BluOS Companion presets* or *BluOS Companion player*.
4. Optional: expose the players to Assist, then type or say "play Adele on Kitchen".

## Documentation

| | |
|---|---|
| [The sidebar player](documentation/panel.md) | home, library, search, queue, groups, kiosk use |
| [Dashboard cards](documentation/cards.md) | the presets card and the player card, with their options |
| [Configuration](documentation/configuration.md) | options of a player, entities, services |
| [Playlist backup and restore](documentation/backup-and-restore.md) | text files, restoring, moving your music share |
| [Voice and AI](documentation/voice-and-ai.md) | sentences, typos, volume, AI agents |
| [Developer tools and automations](documentation/developer-tools.md) | actions, attributes, examples |
| [Troubleshooting](documentation/troubleshooting.md) | if something does not work |
| [How it was tested](documentation/how-it-was-tested.md) | tested devices, automated tests, what is not tested |
| [Development](documentation/development.md) | run it, test it, contribute |

## License

Apache License 2.0, see [LICENSE](LICENSE) and [NOTICE](NOTICE). Copyright 2026 Xavier Perseguers.

Menu icons are based on [Material Design Icons](https://pictogrammers.com/library/mdi/)
(Apache License 2.0), see `custom_components/bluos_companion/icons/README.md`.
