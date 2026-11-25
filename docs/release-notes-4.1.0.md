# BluOS Companion 4.1.0

The back button of the browser works inside the sidebar player.

## New

- **The back button of the browser goes up one page of the panel.** Each page you open (an artist, an album, a genre, a playlist, the queue, the editor of a playlist, a search) becomes a step in the history of the browser. Back and forward walk through the pages of the panel, and the player you were browsing from, before leaving it. The arrow of the panel and the back button of the browser now do the same thing, and a new search replaces the previous one instead of adding a step. Coming back to the panel from another page of Home Assistant puts you on the page you were on, instead of the start page.

## Also

- **Documentation.** A section "Is this for me?" with a comparison with the built-in integration, a recommendation of the kiosk mode of the Home Assistant Companion app for a wall tablet, a note that the panel runs smoothly on an old iPad Pro, and *genre* among the filters of the voice and AI search page. The page on how it was tested lists the back button of the browser and the new number of automated tests.

## Upgrading

Restart Home Assistant once, then reload the browser page without cache. A tablet in kiosk mode: reload it, or clear the cache of its browser or app once.
