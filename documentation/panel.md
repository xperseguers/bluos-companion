# The sidebar player

**BluOS Companion** appears in the sidebar of Home Assistant for **every user** (it is not limited to
administrators). It is designed for touch screens: a tablet fixed to a wall in kiosk mode can browse
the music and control the players without leaving Home Assistant.

It only shows BluOS Companion players, not the other media players of Home Assistant.

![The home page](images/panel-home-scrolled.jpg)

## The bottom bar

Always visible, for the player you chose:

- the cover, the title and the artist. **Tap them** to open the full-screen view
- previous / play-pause / next, the **time played and left** (with a slider to move in the track), a button for the
  **queue**
- the **volume**, as a ring that shows the level: tap it and the bar turns into a slider with mute, **−** and **+**,
  then comes back by itself after a few seconds
- a **⋮ menu** with the **player** (it shows the player, or the group "Kitchen + Living room", and opens the list
  of players, to choose where the music plays and to group them), **move playback** (only while the player is
  playing) and the **input** and **sleep timer** of the player

On a phone the bar is more compact: cover, title, play-pause, volume and the ⋮ menu (which also has the queue), and a
thin line along its top edge shows the progress.

## Home page

From top to bottom: your **presets**, your **saved playlists** (with the cover of their first track), the
**library** (Artists, Albums, Songs, Genres...), **recently played**, **recent stations**, **recently added**
albums and your **sources** (services such as TuneIn or Deezer, and inputs such as Bluetooth). The titles
come from the player, in your language. Services you do not use can be hidden, see
[Configuration](configuration.md).

Presets belong to a player: a player without presets has no presets row.

## Browsing

- **Library**: artists, albums, songs and composers come with an **A–Z bar** (`# A B … Z`). Inside a
  letter the bar stays at the top, to jump to another letter. Long lists without letters (genres) get a bar of first
  letters. Very long lists are cut and offer **Show more**.
- **Going back**: the arrow goes up one level. From the second level on, a **home** button next to it takes you
  straight back to the start page.
- **Albums and artists** open on a page with **Play now, Shuffle, Add next, Add last** (the
  actions the player offers). Every tile has a **⋮** menu with the same actions, and a play button on albums.
- **Favourites**: albums, artists and songs of your library also offer **Add to favourites** (or **Remove from
  favourites** when they are one), on their page and in their **⋮** menu. For the **track that is playing**, use
  the heart in the full-screen view. The favourites are the player's own, you
  find them under **Favourites** in the library, in the BluOS app and on every player (they are shared). Removing
  from the *Favourites* list of the BluOS app works as well.
- **Playlists** open to their tracks. Tap a track to play it and carry on with the rest of the playlist.
  Entries the player cannot find anymore (moved files) are not listed.
- **Search** (the field at the top): searches the source you are in, the library from the home page.
  Results are grouped (artists, albums, songs...).
- Use the ⋮ menu next to the title in the full-screen view, in a queue row's ⋮ menu or in a song result's ⋮ menu
  to jump to its **album page** or **artist page**.

![An album page](images/panel-album.jpg)

![Artists, with the A–Z bar](images/panel-artists-letter.jpg)

## The queue

The queue button opens the tracks of the current queue, the playing one highlighted. Tap a track to
play it; use ⋮ to move it up or down; the cross removes it. **Shuffle** and **Repeat** (off, all, one track) are
here, since they belong to a queue, not to a single track. **Clear** empties the queue and **Save** keeps it as a
playlist under a name.

![The queue](images/panel-queue.jpg)

## Players, groups and moving music

- The **player** row of the ⋮ menu lists the players, with what each one plays and its group. Choosing one makes it
  the target of everything you do in the panel.
- **Group players**: switch players on or off in the group of the current one. Each member has its own
  volume (slider, − and +), and the group has a volume (− and +, in steps that keep the balance) and a
  mute. **Ungroup all** dissolves the group.
- **Move playback** (in the ⋮ menu) sends what a player is playing (queue and position) to another player, which
  starts it right away while the first pauses. It is only offered for a player that is playing.

![Choosing the player](images/panel-players.jpg)

![The group screen](images/panel-group.jpg)

## Full-screen view

Tap the cover or the title in the bar. The background is the cover itself, blurred. From top to bottom: a big
cover, the title and the artist with a **heart** (add to or remove from the favourites, for tracks of your library)
and a **⋮** menu (favourite, go to the album, go to the artist), the position and the time left, previous /
play-pause / next, and a bottom row with the **volume ring** and the **queue** button. The queue replaces the cover, with
shuffle, repeat, clear and save, and the title and the controls stay in place. On a phone a ⋮ menu in the top corner,
and on a tablet an icon next to the queue button, give the **player**, **move playback**, the **input** (Bluetooth,
TV...) and the **sleep timer**.

![The full-screen view](images/panel-fullscreen.jpg)

## Kiosk tips

- Use Home Assistant's kiosk mode of your choice to hide the sidebar and the header, and open
  `/bluos-companion` directly.
- Buttons get larger on touch screens.
- To keep a wall tablet from being turned up too loud, set the **maximum volume** of the player in its options
  (it applies to the panel, the cards and voice control, not to the BluOS app or the remote).
- The panel remembers the last player you chose in each browser.

## Languages

English, French and German, following the language of the Home Assistant user. Menu names (Artists,
Albums...) use the official names the BluOS player gives in your language.
