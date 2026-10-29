# Voice and AI

BluOS Companion players work with Home Assistant's **Assist**, by voice or by typing, and with
AI conversation agents that use Assist. You can ask for music by name:

> *Play Adele on Living room.* — *Play the album 21 on Kitchen.* — *Play Radio Swiss Jazz.*

The integration searches the player's music library, its saved playlists and its radio presets, and
starts the best match.

## Set up

1. **Expose the players to Assist**: Settings → Voice assistants → *Expose*, and add your BluOS
   Companion players. A player that is not exposed does not exist for Assist. New media players
   are usually exposed by default.
2. **Give the players names you can say**, and optionally an area or aliases (Settings → Devices &
   services → your player → settings). "Living room" is easier to say than "NODE N132".
3. Make sure the language of your assistant matches the language you speak or type
   (Settings → Voice assistants).

You can try it by typing: click the **Assist** speech-bubble icon of a dashboard, or use
Developer tools → Actions → `conversation.process` with `text: play Adele on Living room`.
The music really starts, so mind the volume of the player you choose.

## What it can find

| You ask for | It starts |
|---|---|
| an artist | all the songs of the artist in your library |
| an album | the album |
| a song | that song |
| a saved playlist | the playlist |
| a radio preset | the station |

When several things match, the best match is played: an exact name first, then names that start
with what you said, then names that contain it. For the same quality of match a playlist or a
station wins over an artist, an album and a song. Say what you mean if a name is ambiguous
("the album Hello", "the artist Santa", "the playlist Tuning").

### Spelling mistakes

Names are compared without capital letters, accents or punctuation (*celine dion* finds
*Céline Dion*, *recommence moi* finds *Recommence-moi*). If nothing matches exactly, close names
are offered, so a few typos are fine: *Adelle*, *Led Zepelin*, *cold play*, *kuschel rok*.
It does not guess from a single shared word, so a name that resembles nothing finds nothing.
AI agents usually spell artists correctly, and can try again with another spelling when they get
no result.

## Sentences that work

These sentences were checked with Home Assistant's own sentences. They depend on the language of
your assistant.

**English**

- *Play Adele on Kitchen* · *Play the album 21 on Kitchen* · *Play the artist Santa on Kitchen*
- *Play the playlist Tuning on Kitchen* · *Play NRJ on Kitchen*
- *Pause Kitchen* · *Resume Kitchen* · *Next track on Kitchen* · *Mute Kitchen*
- *Set the volume to 20 percent on Kitchen* · *Increase the volume on Kitchen by 5*

**Français**

- *Mets Adele sur Cuisine* · *Joue Adele sur Cuisine* · *Mets l'album 21 sur Cuisine*
- *Mets l'artiste Santa sur Cuisine* · *Mets la playlist Tuning sur Cuisine*
- *Mets en pause Cuisine* · *Chanson suivante sur Cuisine*
- *Règle le volume à 20 pour cent sur Cuisine* · *Monte le volume de 5 sur Cuisine* · *Baisse le volume sur Cuisine*

**Deutsch**

- *Spiele Adele auf Küche* · *Spiele Album 21 auf Küche* · *Spiele Wiedergabeliste Tuning auf Küche*
- *Spiele Künstler Santa auf Küche*
- *Pausiere Küche* · *Nächster Titel auf Küche*
- *Stelle die Lautstärke auf 20 Prozent auf Küche* · *Lauter auf Küche*

You can also name an area instead of a player (*Play Adele in the living room*) when a single
player is in it, or leave the player out if only one player is exposed.

### Quirks of Home Assistant's sentences

These come from Home Assistant, not from the integration:

- English: *set the volume to 20 on Kitchen* (without "percent") is understood as a position of a
  blind. Say "percent". *Turn up the volume on Kitchen* may lose the name of the player, say
  *increase the volume on Kitchen*.
- English: there is no good sentence for "stop" or "previous song". Use *pause*.
- French: *mets le volume à 20 pour cent* is understood as a search for music. Use *règle le volume*.
- German and French: say the kind of item without an article (*Album 21*, *l'album 21*).

## Volume

The volume commands go through the normal Home Assistant volume of the player, so the
**maximum volume** option of the player (Settings → Devices & services → BluOS Companion →
Configure) applies to voice and AI commands as well. The volume of the BluOS app and of the
remote is not limited.

## AI conversation agents

An AI agent (OpenAI, Anthropic, Google, a local model...) that is allowed to control Home Assistant
through **Assist** gets the same capability for the exposed players: it can ask to play an artist,
an album, a song, a playlist or a station. Enable *Control Home Assistant → Assist* in the settings
of the agent, and expose the players.

Some agents do not use the search of Assist and call `media_player.play_media` themselves, with the title as
text (`media_content_id: les yeux revolver`, `media_content_type: music`). That works too: BluOS Companion
searches the name like Assist does and plays the best match. The type can narrow the search (`artist`, `album`,
`track`, `playlist`). If nothing matches, the action fails with "No results found for ...", which the agent can
use to try again.

## Trying the search without playing anything

Developer tools → Actions → `media_player.search_media`:

```yaml
action: media_player.search_media
target:
  entity_id: media_player.kitchen
data:
  search_query: adele
  media_filter_classes:   # optional: artist, album, track, playlist
    - artist
```

The response lists what would be played, best match first, up to 10 results.

## It does not work?

- **"No results"**: try the search above to see what the player finds. A library that is still
  being indexed by the player may be incomplete.
- **Assist does not know the player**: it is not exposed, or its name is different from what you
  say. Check the name and the aliases.
- **It plays something else**: say more ("the album …", "the artist …"), or look at the results of
  the search above.
