/* BluOS Companion sidebar panel. Plain JavaScript, no build step. */

const STYLE = `
  [hidden] { display: none !important; }
  :host {
    display: flex;
    flex-direction: column;
    height: 100vh;
    height: 100dvh;
    overflow: hidden;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
  }
  header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, #fff);
    min-height: 56px;
    box-sizing: border-box;
    border-bottom: 1px solid var(--divider-color);
  }
  header h1 { font-size: 20px; font-weight: 400; margin: 0; flex: 1; cursor: pointer; }
  button {
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    padding: 8px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    --mdc-icon-size: 28px;
  }
  button:hover:not(:disabled) { background: rgba(127, 127, 127, 0.2); }
  button:disabled { opacity: 0.4; cursor: default; }
  button.on { color: var(--accent-color, var(--primary-color)); }
  button.player-pill {
    border: 1px solid var(--divider-color);
    border-radius: 20px;
    padding: 6px 14px 6px 10px;
    gap: 6px;
    font: inherit;
    --mdc-icon-size: 22px;
  }
  dialog button.player-row {
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    text-align: left;
  }
  dialog button.player-row.selected {
    border-color: var(--primary-color);
    background: var(--secondary-background-color);
  }
  .now .top button { min-width: 48px; min-height: 48px; }
  @media (pointer: coarse) {
    button { min-width: 48px; min-height: 48px; }
    input[type="range"] { height: 32px; }
  }
  dialog.now {
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    max-width: none;
    max-height: none;
    margin: 0;
    border-radius: 0;
    box-sizing: border-box;
    padding: max(12px, env(safe-area-inset-top)) max(24px, env(safe-area-inset-right))
      max(24px, env(safe-area-inset-bottom)) max(24px, env(safe-area-inset-left));
    background: var(--primary-background-color);
  }
  dialog.now { overflow: hidden; overscroll-behavior: none; }
  /* The cover, scaled up and blurred, as the background of the full screen view */
  .now .bg {
    position: absolute;
    inset: 0;
    z-index: 0;
    background-size: cover;
    background-position: center;
    filter: blur(48px) saturate(1.3);
    transform: scale(1.6);
  }
  .now .veil { position: absolute; inset: 0; z-index: 0; background: rgba(0, 0, 0, 0.4); }
  .now > *:not(.bg):not(.veil) { position: relative; z-index: 1; }
  dialog.now.has-art {
    color: #fff;
    --primary-text-color: #fff;
    --secondary-text-color: rgba(255, 255, 255, 0.72);
    --divider-color: rgba(255, 255, 255, 0.3);
    --secondary-background-color: rgba(255, 255, 255, 0.15);
  }
  dialog.now.has-art input[type="range"] { accent-color: #fff; }
  dialog.now.has-art button.on { color: #fff; }
  dialog.now.has-art button:focus-visible { outline: 2px solid #fff; }
  dialog.now.has-art select { background: rgba(255, 255, 255, 0.18); color: #fff; border: none; }
  dialog.now.has-art select option { color: initial; }
  dialog.now[open] { display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .now .top { align-self: stretch; display: flex; align-items: center; gap: 8px; }
  .now .top span { flex: 1; text-align: center; color: var(--secondary-text-color); }
  .now .art-box {
    flex: 1;
    min-height: 0;
    align-self: stretch;
    display: flex;
    align-items: center;
    justify-content: center;
    container-type: size;
    margin-bottom: 20px;
  }
  .now .art {
    width: min(100cqw, 100cqh);
    height: min(100cqw, 100cqh);
    object-fit: cover;
    border-radius: 12px;
    background: var(--secondary-background-color);
  }
  .now .queue-box { display: none; flex: 1; min-height: 0; align-self: stretch; flex-direction: column; max-width: 640px; width: 100%; margin: 0 auto 20px; }
  dialog.now.queue-open .queue-box { display: flex; }
  dialog.now.queue-open .art-box { display: none; }
  .now .queue-list { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
  .now .queue-box .actions { margin: 0 0 8px; flex: none; display: grid; grid-template-columns: 1fr 1fr; }
  .now .queue-box .actions button { width: 100%; justify-content: flex-start; padding: 6px 14px; }
  dialog.now { --vol-fill: var(--primary-color); }
  dialog.now.has-art { --vol-fill: #fff; }
  .now .vol-ring, .now .vol-ring:hover:not(:disabled) { background: none; }
  .now .vol-ring::before {
    inset: 0;
    background: conic-gradient(var(--vol-fill) calc(var(--level, 0) * 1%), var(--divider-color) 0);
    -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 3px));
    mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 3px));
  }
  /* The volume is a ring in the bottom row, a tap opens the slider in its place */
  .now .line.volume-row { display: none; order: 20; }
  .now .line.bottom { order: 10; }
  .now .line.bottom .vol-ring { margin-right: auto; }
  dialog.now.vol-open .line.volume-row { display: flex; }
  dialog.now.vol-open .line.bottom { display: none; }
  .now .line.bottom button.on { background: rgba(127, 127, 127, 0.3); }
  .now .line.bottom { justify-content: flex-end; }
  dialog.now.has-art .qrow { background: rgba(255, 255, 255, 0.12); border-color: transparent; }
  dialog.now.has-art .qrow.current { background: rgba(255, 255, 255, 0.28); }
  dialog.now.has-art .actions button { background: rgba(255, 255, 255, 0.12); border-color: transparent; }
  dialog.now.has-art .actions button.on { background: rgba(255, 255, 255, 0.3); }
  .now .meta { display: flex; align-items: center; gap: 4px; max-width: 640px; width: 100%; }
  .now .meta .text { flex: 1; min-width: 0; }
  .now .title { font-size: 24px; font-weight: 500; }
  .now .sub { color: var(--secondary-text-color); }
  .now .line { align-self: stretch; display: flex; align-items: center; justify-content: center; gap: 8px; max-width: 640px; width: 100%; margin: 0 auto; }
  .now .line input[type="range"] { flex: 1; min-width: 0; }
  .now .time { min-width: 3.2em; font-variant-numeric: tabular-nums; }
  .now .time:last-child { text-align: right; }
  .now .big { --mdc-icon-size: 40px; }
  .now select { font: inherit; padding: 8px; border-radius: 8px; max-width: 45%; }
  dialog .group-row { display: flex; flex-direction: column; gap: 4px; }
  dialog .group-row .line { display: flex; align-items: center; gap: 8px; }
  dialog .group-row input[type="range"] { flex: 1; min-width: 0; }
  dialog .group-volume { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
  dialog .group-volume .label { flex: 1; }
  dialog .player-row .cover { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; --mdc-icon-size: 28px; }
  dialog .player-row .text { flex: 1; min-width: 0; }
  dialog .player-row .text div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  dialog .player-row .name { font-weight: 500; }
  dialog .player-row .sub { font-size: 12px; color: var(--secondary-text-color); }
  main { flex: 1; min-height: 0; overflow-y: auto; padding: 16px; }
  /* The way back stays at the top while one scrolls up, and gives the room back while one scrolls down */
  .crumbs {
    position: sticky;
    top: 0;
    z-index: 4;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: -16px -16px 8px;
    padding: 16px 16px 8px;
    background: var(--primary-background-color);
    transition: transform 0.2s;
  }
  .crumbs:empty { display: none; }
  .crumbs.away { transform: translateY(-100%); }
  .tile { scroll-margin-top: 72px; }
  .rows { border-top: 1px solid var(--divider-color); margin-bottom: 16px; }
  .lrow {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 4px 0 8px;
    height: 56px;
    box-sizing: border-box;
    border-bottom: 1px solid var(--divider-color);
    cursor: pointer;
    content-visibility: auto;
    contain-intrinsic-size: auto 56px;
  }
  .lrow:hover { background: rgba(127, 127, 127, 0.1); }
  .lrow .num { width: 28px; text-align: right; color: var(--secondary-text-color); flex: none; font-variant-numeric: tabular-nums; }
  .lrow .cover {
    width: 44px;
    height: 44px;
    border-radius: 6px;
    object-fit: cover;
    flex: none;
    background: var(--secondary-background-color);
    display: flex;
    align-items: center;
    justify-content: center;
    --mdc-icon-size: 22px;
  }
  .lrow .text { flex: 1; min-width: 0; }
  .lrow .text div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .lrow .sub { font-size: 12px; color: var(--secondary-text-color); }
  .lrow .time { color: var(--secondary-text-color); font-size: 13px; font-variant-numeric: tabular-nums; }
  .lrow button { --mdc-icon-size: 24px; padding: 6px; }
  .lrow .chev { color: var(--secondary-text-color); --mdc-icon-size: 22px; padding-right: 4px; display: inline-flex; }
  .album-head { position: relative; overflow: hidden; border-radius: var(--ha-card-border-radius, 12px); margin-bottom: 12px; background: #3a3a3a; color: #fff; }
  .ah-bg { position: absolute; inset: 0; background-size: cover; background-position: center; filter: blur(32px) saturate(1.3); transform: scale(1.5); }
  .ah-veil { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.5); }
  .ah-body { position: relative; display: flex; gap: 16px; padding: 16px; align-items: flex-end; }
  .ah-cover {
    width: min(160px, 34vw);
    aspect-ratio: 1;
    border-radius: 8px;
    object-fit: cover;
    flex: none;
    background: rgba(255, 255, 255, 0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    --mdc-icon-size: 48px;
  }
  .ah-text { min-width: 0; flex: 1; }
  .ah-text h2 { margin: 0 0 4px; font-size: 22px; font-weight: 500; overflow-wrap: anywhere; }
  .ah-artist, .ah-meta { opacity: 0.8; }
  .ah-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
  .ah-actions button { border-radius: 20px; padding: 8px 16px; gap: 8px; font: inherit; background: rgba(255, 255, 255, 0.18); color: #fff; }
  .ah-actions button.primary { background: var(--primary-color); }
  .ah-actions button.round { padding: 8px; }
  .browse { position: relative; flex: 1; min-height: 0; display: flex; flex-direction: column; }
  main.with-az { padding-right: 38px; }
  .az {
    position: absolute;
    right: calc(var(--scrollbar, 0px) + 4px);
    top: 8px;
    bottom: 8px;
    width: 26px;
    z-index: 5;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
    box-sizing: border-box;
    border-radius: 13px;
    background: rgba(127, 127, 127, 0.18);
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
    font-size: 11px;
    line-height: 1;
    color: var(--secondary-text-color);
  }
  .az div { padding: 1px 0; cursor: pointer; }
  .az div.current { color: var(--primary-color); font-weight: 700; }
  .sec-head { margin: 8px 0 4px; padding: 0 8px; font-size: 20px; font-weight: 500; height: 40px; line-height: 40px; box-sizing: border-box; }
  .sec-body .rows { margin-bottom: 0; border-top: none; }
  .sec-body .grid { margin-bottom: 8px; }
  .sec-loading { padding: 16px; color: var(--secondary-text-color); }
  .landing { display: flex; flex-direction: column; gap: 16px; }
  .lsec {
    background: var(--card-background-color);
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: var(--ha-card-box-shadow, none);
    border: 1px solid var(--divider-color);
    padding: 8px 16px 12px;
  }
  .lsec-head { display: flex; align-items: center; gap: 8px; min-height: 48px; margin-bottom: 12px; }
  .lsec-head h3 { margin: 0; flex: 1; font-size: 18px; font-weight: 500; cursor: pointer; }
  .lsec-head button.viewall { border-radius: 16px; padding: 6px 14px; font: inherit; font-size: 13px; text-transform: uppercase; background: rgba(127, 127, 127, 0.15); }
  .lsec-head button.arrow { padding: 4px; min-width: 40px; min-height: 40px; --mdc-icon-size: 22px; background: rgba(127, 127, 127, 0.15); }
  .lsec .rows { margin-bottom: 0; border-top: none; }
  .lsec .lrow.link { height: 48px; }
  .lsec .lrow:last-child { border-bottom: none; }
  .hscroll { display: flex; gap: 16px; overflow-x: auto; scroll-snap-type: x proximity; padding: 4px 2px 8px; }
  .hscroll .tile { flex: 0 0 150px; scroll-snap-align: start; }
  /* The albums of a wide screen flow in one grid, the letter (or year, artist...) being a cell of it */
  .grid.flow { margin-bottom: 16px; }
  .grid.flow .tile .title, .grid.flow .tile .subtitle { line-height: 1.25; }
  .grid.flow .tile .title { min-height: 2.5em; }
  .grid.flow .tile .subtitle { min-height: 1.25em; -webkit-line-clamp: 1; line-clamp: 1; }
  .grid.flow .tile .text { padding-top: 8px; }
  .tile.ph { visibility: hidden; pointer-events: none; }
  /* The letter, the year, the artist: a card of the grid, lighter than the albums */
  .tile.hcell {
    cursor: default;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 8px;
    background: var(--secondary-background-color);
  }
  .tile.hcell:hover { background: var(--secondary-background-color); }
  .hlabel {
    font-size: 18px;
    font-weight: 500;
    line-height: 1.3;
    overflow-wrap: break-word;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 4;
    line-clamp: 4;
    overflow: hidden;
  }
  .list-controls { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
  .list-controls button { border-radius: 20px; padding: 6px 14px; gap: 8px; font: inherit; border: 1px solid var(--divider-color); background: var(--card-background-color); }
  .list-controls select { font: inherit; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
  .info-rows { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
  .info-row { display: flex; justify-content: space-between; gap: 16px; }
  .info-row span:first-child { color: var(--secondary-text-color); }
  .info-row span:last-child { text-align: right; overflow-wrap: anywhere; }
  .crumb-cover { width: 56px; height: 56px; border-radius: 8px; object-fit: cover; flex: none; }
  .crumbs h2 { margin: 0; font-size: 20px; font-weight: 500; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 16px;
  }
  .tile {
    position: relative;
    cursor: pointer;
    box-sizing: border-box;
    padding: 8px 8px 12px;
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--card-background-color);
    overflow: hidden;
  }
  .tile:hover { background: var(--secondary-background-color); }
  .tile .art {
    aspect-ratio: 1;
    width: 100%;
    display: block;
    object-fit: cover;
    border-radius: 8px;
    background: var(--secondary-background-color);
  }
  .tile .art.icon { border-radius: 0; background: none; }
  .tile .art.logo { object-fit: contain; padding: 16px; box-sizing: border-box; }
  .tile .art.empty {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--secondary-text-color);
    --mdc-icon-size: 48px;
  }
  .tile .text { padding: 12px 8px 0; }
  .tile .title, .tile .subtitle {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    overflow: hidden;
    overflow-wrap: anywhere;
  }
  .tile .subtitle { font-size: 12px; color: var(--secondary-text-color); }
  .tile .play {
    position: absolute;
    right: 6px;
    bottom: 6px;
    background: rgba(0, 0, 0, 0.6);
    color: #fff;
    --mdc-icon-size: 24px;
  }
  .actions { display: flex; flex-wrap: wrap; gap: 8px; margin: -4px 0 16px; }
  .actions button, dialog button.action {
    border: 1px solid var(--divider-color);
    border-radius: 20px;
    padding: 8px 16px;
    gap: 8px;
    font: inherit;
    background: var(--card-background-color);
  }
  .tile .artwrap { position: relative; }
  .tile .more { position: absolute; right: 6px; top: 6px; background: rgba(0, 0, 0, 0.6); color: #fff; --mdc-icon-size: 22px; padding: 6px; }
  dialog {
    border: none;
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    padding: 16px;
    min-width: 260px;
    max-width: 90vw;
  }
  dialog::backdrop { background: rgba(0, 0, 0, 0.5); }
  dialog h2 { margin: 0 0 4px; font-size: 18px; font-weight: 500; }
  dialog p { margin: 0 0 12px; color: var(--secondary-text-color); font-size: 13px; }
  dialog .list { display: flex; flex-direction: column; gap: 8px; }
  dialog button.action { justify-content: flex-start; border-radius: 12px; width: 100%; }
  .qrow {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 8px 8px 12px;
    margin-bottom: 8px;
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--card-background-color);
    cursor: pointer;
  }
  .qrow.current { border-color: var(--primary-color); }
  .qrow .pos { width: 28px; text-align: right; color: var(--secondary-text-color); flex: none; }
  .qrow .cover { width: 48px; height: 48px; border-radius: 8px; object-fit: cover; flex: none; background: var(--secondary-background-color); display: flex; align-items: center; justify-content: center; --mdc-icon-size: 24px; }
  .qrow .text { flex: 1; min-width: 0; }
  .qrow .text div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .qrow .sub { font-size: 12px; color: var(--secondary-text-color); }
  .qrow button { --mdc-icon-size: 24px; padding: 6px; }
  dialog input[type="text"] {
    width: 100%;
    box-sizing: border-box;
    font: inherit;
    padding: 10px 14px;
    margin-bottom: 12px;
    border: 1px solid var(--divider-color);
    border-radius: 12px;
    background: var(--card-background-color);
    color: var(--primary-text-color);
  }
  form.search { display: flex; gap: 8px; margin-bottom: 16px; }
  form.search input {
    flex: 1;
    min-width: 0;
    font: inherit;
    padding: 10px 14px;
    border: 1px solid var(--divider-color);
    border-radius: 24px;
    background: var(--card-background-color);
    color: var(--primary-text-color);
  }
  h3 { margin: 24px 0 12px; font-size: 16px; font-weight: 500; }
  .message { color: var(--secondary-text-color); text-align: center; margin-top: 48px; }
  footer {
    flex: none;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 16px;
    background: var(--card-background-color);
    border-top: 1px solid var(--divider-color);
    flex-wrap: wrap;
    padding-bottom: max(8px, env(safe-area-inset-bottom));
  }
  footer img, footer .cover {
    width: 64px;
    height: 64px;
    border-radius: 8px;
    object-fit: cover;
    background: var(--secondary-background-color);
    flex: none;
  }
  .info { flex: 1 1 160px; min-width: 0; cursor: pointer; }
  .info div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .info .track { font-weight: 500; }
  .info .artist { font-size: 13px; color: var(--secondary-text-color); }
  .controls { display: flex; align-items: center; }
  .progress { display: flex; align-items: center; gap: 8px; flex: 1 1 100%; font-size: 12px; }
  .progress input { flex: 1; }
  .progress .time { min-width: 3.2em; font-variant-numeric: tabular-nums; }
  .progress .time:last-child { text-align: right; }
  .volume { display: flex; align-items: center; gap: 4px; }
  input[type="range"] { accent-color: var(--primary-color); }
  .phone-only { display: none; }
  .mini-bar { display: none; }
  footer .volume { display: none; }
  footer.vol-open > *:not(.volume) { display: none; }
  footer.vol-open .volume { display: flex; flex: 1; gap: 8px; }
  footer .volume input { flex: 1; min-width: 0; }
  .vol-ring, .vol-ring:hover:not(:disabled) {
    position: relative;
    flex: none;
    width: 48px;
    height: 48px;
    padding: 0;
    background: conic-gradient(var(--primary-color) calc(var(--level, 0) * 1%), var(--divider-color) 0);
  }
  .vol-ring::before {
    content: "";
    position: absolute;
    inset: 3px;
    border-radius: 50%;
    background: var(--card-background-color);
  }
  .vol-ring ha-icon { position: relative; --mdc-icon-size: 22px; }
  dialog .more-list select {
    font: inherit;
    padding: 10px;
    border-radius: 8px;
    width: 100%;
    box-sizing: border-box;
  }
  dialog .more-list label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--secondary-text-color); }
  /* Phone: a compact bar (cover, title, play, volume, more) and a strip for the volume */
  @media (max-width: 600px) {
    .phone-only { display: inline-flex; }
    footer {
      position: relative;
      flex-wrap: nowrap;
      gap: 8px;
      padding: 10px 12px max(10px, env(safe-area-inset-bottom));
    }
    footer img, footer .cover { width: 48px; height: 48px; }
    .info { flex: 1 1 0; }
    .controls button { display: none; }
    .controls button.keep { display: inline-flex; }
    footer .progress { display: none; }
    .mini-bar { display: block; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--divider-color); }
    .mini-bar div { height: 100%; width: 0; background: var(--primary-color); }
    footer.vol-open .mini-bar { display: none; }
    .now .settings-button { display: none; }
    .now .top button.phone-only { display: inline-flex; }
  }
`;

const ROW_TYPES = ["track", "artist", "composer", "genre"];
const LANDING_TYPES = ["artist", "composer", "genre"]; // their page shows a few albums, songs...
const FAR = 4000; // letters this far (in pixels) from what shows are given back
const ROW_HEIGHT = 56; // a row of a list has a fixed height, so that the length of a list of letters is known
const REPEAT_CYCLE = { 2: 0, 0: 1, 1: 2 }; // off -> queue -> track -> off
const ACTIVE_STATES = ["play", "stream"];
const INITIALS_FROM = 40; // a list this long gets a bar of first letters
const STORAGE_KEY = "bluos_companion_player";
const DISPLAY_KEY = "bluos_companion_display"; // the lists of albums: list or grid
const ALBUM_SORT_KEY = "bluos_companion_album_sort";
const ALBUMS_KEY = "LocalMusic:bySection:Album/%2Flibrary%2Fv1%2FAlbums%3Fservice=LocalMusic"; // all the albums
const ALBUM_SORTS = ["az", "recent", "year", "decade", "artist", "artist_year"];
const DEFAULT_SEARCH_KEY = "LocalMusic:Search"; // the library, used at the root

// The signed URL of an image changes with every state update: compare what it points to
function imageKey(url) {
  return url ? url.replace(/[?&]authSig=[^&]*/, "") : "";
}

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null) node.setAttribute(key, value);
  }
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}

function icon(name) {
  return el("ha-icon", { icon: name });
}

const ACTION_ICONS = {
  "add-now": "mdi:play",
  "add-shuffle": "mdi:shuffle",
  "addAll-shuffle": "mdi:shuffle",
  "add-next": "mdi:playlist-play",
  "addAll-next": "mdi:playlist-play",
  "add-last": "mdi:playlist-plus",
  "addAll-last": "mdi:playlist-plus",
  add: "mdi:playlist-plus",
};

function formatTime(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  return `${minutes}:${String(total % 60).padStart(2, "0")}`;
}

class BluOSCompanionPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._players = [];
    this._playerId = localStorage.getItem(STORAGE_KEY);
    this._stack = []; // [{ title, key }], the root is implicit
    this._groups = null; // [{ title, items }]
    this._nextKey = null; // where a list cut after a few pages continues
    this._levelActions = [];
    this._queue = null; // [{ position, title, artist, image }]
    this._queueKey = null;
    this._searchKey = DEFAULT_SEARCH_KEY;
    this._receivedAt = 0;
    this._browseToken = 0;
    this._unsubscribe = null;
    this._ticker = null;
    this._built = false;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._loadStrings().then(() => {
        this._build();
        this._subscribe();
      });
    }
  }

  // The texts come from the integration, in the language of the user (English if unknown).
  async _loadStrings() {
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "bluos_companion/translations",
        language: this._hass.language,
      });
      this._strings = result.strings;
    } catch (err) {
      this._strings = {};
    }
  }

  _t(key, vars = {}) {
    let text = (this._strings || {})[key] ?? key;
    for (const [name, value] of Object.entries(vars)) text = text.replace(`{${name}}`, value);
    return text;
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menuButton) this._menuButton.hidden = !narrow;
  }

  set panel(panel) {
    this._panel = panel;
  }

  connectedCallback() {
    if (this._hass && !this._unsubscribe) this._subscribe();
    this._ticker = setInterval(() => this._tick(), 1000);
    this._fit = () => this._fitHeight();
    window.addEventListener("resize", this._fit);
    requestAnimationFrame(this._fit);
  }

  // The panel may start below the top of the window (a phone's status bar, a toolbar of the
  // app): take that off the viewport height so the footer is never pushed out of sight.
  _fitHeight() {
    const top = Math.max(0, this.getBoundingClientRect().top);
    this.style.height = top ? `calc(100dvh - ${top}px)` : "";
  }

  disconnectedCallback() {
    window.removeEventListener("resize", this._fit);
    clearInterval(this._ticker);
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = null;
    }
  }

  get _player() {
    return this._players.find((player) => player.entry_id === this._playerId);
  }

  async _subscribe() {
    this._unsubscribe = await this._hass.connection.subscribeMessage(
      (event) => this._onPlayers(event.players),
      { type: "bluos_companion/subscribe" },
    );
  }

  _onPlayers(players) {
    this._players = players;
    this._receivedAt = Date.now();
    const previous = this._playerId;
    if (!this._player && players.length) this._playerId = players[0].entry_id;
    if (this._playerId !== previous) {
      localStorage.setItem(STORAGE_KEY, this._playerId);
      this._stack = [];
      this._browse();
    } else if (this._groups === null) {
      this._browse();
    }
    this._renderPlayers();
    this._renderNowPlaying();
    this._renderNow();
    this._refreshQueue();
  }

  _call(message) {
    return this._hass.connection
      .sendMessagePromise(message)
      .catch((err) => this._notify(err.message || String(err)));
  }

  _notify(message) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
    );
  }

  async _actions(contextKey) {
    const result = await this._call({
      type: "bluos_companion/actions",
      entry_id: this._playerId,
      key: contextKey,
    });
    return result ? result.actions : [];
  }

  async _runAction(action, label) {
    if (action.favourite) {
      const done = await this._call({
        type: "bluos_companion/favourite",
        entry_id: this._playerId,
        on: !action.on,
        ...action.favourite,
      });
      if (done === undefined) return;
      this._notify(`${this._t(action.on ? "favourite_removed" : "favourite_added")}: ${label}`);
      this._refreshLevelActions();
      return;
    }
    await this._call({ type: "bluos_companion/play", entry_id: this._playerId, path: action.path });
    this._notify(`${action.title}: ${label}`);
  }

  // The actions of the page on display, after one of them changed (a favourite).
  async _refreshLevelActions() {
    const level = this._stack[this._stack.length - 1];
    if (!level || !level.contextKey) return;
    const token = this._browseToken;
    const actions = await this._actions(level.contextKey);
    if (token !== this._browseToken) return;
    this._levelActions = actions;
    this._renderCrumbs();
  }

  _showPlaying() {
    const player = this._player;
    if (!player || !player.title) return;
    if (player.service !== "LocalMusic") {
      this._notify(this._t("library_only"));
      return;
    }
    const options = {
      title: player.title,
      subtitle: [player.artist, player.album].filter(Boolean).join(" - "),
      names: { album: player.album, artist: player.artist },
      info: { type: "track", artist: player.artist, album: player.album, duration: player.duration },
    };
    this._itemMenu(options);
    // Whether the track is a favourite takes a request: the button comes when it is known
    this._call({ type: "bluos_companion/playing_favourite", entry_id: this._playerId }).then((result) => {
      if (!result || !this._dialog.open) return;
      this._itemMenu({ ...options, actions: [{ favourite: result.favourite, on: result.on }] });
    });
  }

  async _jump(kind, names) {
    if (this._nowDialog.open) this._nowDialog.close();
    // The album is found with the artist of the album, which is not always the one of the track
    const artist = kind === "album" ? names.albumArtist || names.artist : names.artist;
    const found = await this._call({
      type: "bluos_companion/locate",
      entry_id: this._playerId,
      ...(names.album ? { album: names.album } : {}),
      ...(artist ? { artist } : {}),
    });
    if (!found) return;
    const level = (page) => ({ title: page.title, key: page.browse_key, contextKey: page.context_key });
    const stack = found.artist ? [{ ...level(found.artist), type: "artist" }] : [];
    if (kind === "album") {
      if (!found.album) {
        this._notify(this._t("album_not_found"));
        return;
      }
      stack.push({
        ...level(found.album),
        type: "album",
        subtitle: found.album.subtitle,
        image: found.album.image,
        tracks: found.album.tracks,
      });
    } else if (!found.artist) {
      return;
    }
    this._stack = stack;
    this._browse();
  }

  // The artist of a song and the artist of its album can be two: one button for each
  _gotoButtons(names) {
    const button = (kind, iconName, label, target) =>
      el(
        "button",
        {
          class: "action",
          onclick: () => {
            this._dialog.close();
            this._jump(kind, target);
          },
        },
        icon(iconName),
        label,
      );
    const artists = names.artists || (names.artist ? [names.artist] : []);
    return [
      names.album ? button("album", "mdi:album", this._t("album_label", { name: names.album }), names) : null,
      ...artists.map((name) => button("artist", "mdi:account-music", this._t("artist_label", { name }), { artist: name })),
    ].filter(Boolean);
  }

  _menuRow(iconName, label, run) {
    return el(
      "button",
      {
        class: "action",
        onclick: () => {
          this._dialog.close();
          run();
        },
      },
      icon(iconName),
      label,
    );
  }

  // The menu of an item, the same everywhere: favourite, what the player offers, what the place adds
  // (moving in the queue...), go to the album and the artist, info. `info` says what is known of it.
  _itemMenu({ title, subtitle, actions = [], extra = [], names = {}, info = null }) {
    const options = { title, subtitle, actions, extra, names, info };
    const close = () => this._dialog.close();
    const ordered = [...actions.filter((action) => action.favourite), ...actions.filter((action) => !action.favourite)];
    const list = el(
      "div",
      { class: "list" },
      ...ordered.map((action) => this._actionButton(action, title, close)),
      ...extra,
      ...this._gotoButtons(names),
      info && this._infoRows(info).length
        ? el("button", { class: "action", onclick: () => this._showInfo(options) }, icon("mdi:information-outline"), this._t("info"))
        : null,
    );
    this._dialog.replaceChildren(el("h2", {}, title), el("p", {}, subtitle || "\u00a0"), list);
    if (!this._dialog.open) this._dialog.showModal();
    return list;
  }

  _infoRows(info) {
    return [
      [this._t("info_artist"), info.artist],
      [this._t("info_album"), info.album],
      [this._t("info_duration"), info.duration ? formatTime(info.duration) : null],
      [this._t("info_tracks"), info.tracks ? String(info.tracks) : null],
    ].filter(([, value]) => value);
  }

  // What the panel knows of an item, from the lists
  _showInfo(options) {
    const rows = this._infoRows(options.info);
    this._dialog.replaceChildren(
      el("h2", {}, options.title),
      el(
        "div",
        { class: "info-rows" },
        ...rows.map(([label, value]) => el("div", { class: "info-row" }, el("span", {}, label), el("span", {}, value))),
      ),
      el(
        "div",
        { class: "list", style: "margin-top: 12px" },
        el("button", { class: "action", onclick: () => this._itemMenu(options) }, icon("mdi:arrow-left"), this._t("back")),
      ),
    );
  }


  _actionButton(action, label, after) {
    return el(
      "button",
      {
        class: "action",
        onclick: () => {
          this._runAction(action, label);
          if (after) after();
        },
      },
      icon(
        action.favourite
          ? action.on
            ? "mdi:heart-off"
            : "mdi:heart"
          : ACTION_ICONS[action.type] || "mdi:playlist-plus",
      ),
      action.favourite ? this._t(action.on ? "favourite_remove" : "favourite_add") : action.title,
    );
  }

  async _showActions(item) {
    const actions = item.context_key ? await this._actions(item.context_key) : [];
    const level = this._stack[this._stack.length - 1];
    // A song of a list reads "Artist \u2022 Album", or "Artist \u2022 Album artist \u2022 Album" in the results of a
    // search; the key of its menu has the album and the artist of the album, which find the album page
    const parts = item.type === "track" ? (item.subtitle || "").split(" \u2022 ") : [];
    const keyed = new URLSearchParams((item.context_key || "").split("?")[1] || "");
    let artist = parts.length ? parts[0] : null;
    let album = parts.length > 1 ? parts[parts.length - 1] : null;
    let albumArtist = keyed.get("album") ? keyed.get("artist") : null;
    if (keyed.get("album")) album = keyed.get("album");
    if (item.type === "track" && !album && level && level.type === "album") [artist, album, albumArtist] = [level.subtitle, level.title, level.subtitle];
    if (item.type === "album") artist = item.subtitle;
    const names = {};
    if (item.type === "track" && album) names.album = album;
    if (albumArtist) names.albumArtist = albumArtist;
    if (artist) names.artist = artist;
    names.artists = [...new Set([artist, albumArtist].filter(Boolean))];
    const onAlbum = Boolean(level && level.type === "album");
    this._itemMenu({
      title: onAlbum ? item.title.replace(/^\d+\.\s+/, "") : item.title,
      subtitle: item.subtitle || (level && level.type === "album" && item.type === "track" ? level.title : ""),
      actions,
      names,
      info: { type: item.type, artist, album, duration: item.duration, tracks: item.tracks },
    });
  }


  _control(action, value, entryId, extra = {}) {
    const id = entryId || (this._player && this._player.entry_id);
    if (!id) return;
    return this._call({
      type: "bluos_companion/control",
      entry_id: id,
      action,
      ...(value === undefined ? {} : { value }),
      ...extra,
    });
  }

  async _browse() {
    const player = this._player;
    if (!player) return;
    const token = ++this._browseToken;
    this._groups = null;
    this._nextKey = null;
    this._levelActions = []; // those of the previous page must not be drawn on this one
    this._renderBrowse();
    const level = this._stack[this._stack.length - 1];
    if (level && level.contextKey) {
      this._actions(level.contextKey).then((actions) => {
        if (token !== this._browseToken) return;
        this._levelActions = actions;
        this._renderCrumbs();
      });
    }
    let groups;
    if (level && level.queue) {
      await this._loadQueue();
      return;
    }
    if (level && level.search) {
      const result = await this._call({
        type: "bluos_companion/search",
        entry_id: player.entry_id,
        key: level.search.key,
        query: level.search.query,
      });
      groups = result ? result.groups : [];
    } else if (!level) {
      const result = await this._call({ type: "bluos_companion/home", entry_id: player.entry_id });
      this._searchKey = (result && result.search_key) || DEFAULT_SEARCH_KEY;
      groups = result ? result.groups : [];
    } else {
      const result = await this._call({
        type: "bluos_companion/browse",
        entry_id: player.entry_id,
        ...(level.key ? { key: level.key } : {}),
      });
      if (result && result.search_key) this._searchKey = result.search_key;
      this._nextKey = result ? result.next_key : null;
      groups = [{ title: null, items: result ? result.items : [] }];
    }
    if (token !== this._browseToken) return;
    this._groups = groups;
    this._landing = null;
    if (level && level.key === ALBUMS_KEY) this._albumsData = null; // the library may have changed
    this._renderBrowse();
    this._main.scrollTop = 0;
    this._loadPlaylistCovers();
    if (this._isLandingLevel(level)) this._loadLanding(level, token);
  }

  // Saved playlists have no cover of their own: use the one of their first track, which
  // can take a few requests on the player, so it is fetched after the list is shown.
  async _loadPlaylistCovers() {
    const token = this._browseToken;
    const items = (this._groups || [])
      .flatMap((group) => group.items)
      .filter((item) => item.type === "playlist" && !item.image && (item.browse_key || "").startsWith("BluOS:"));
    if (!items.length || !this._player) return;
    const result = await this._call({
      type: "bluos_companion/playlist_covers",
      entry_id: this._player.entry_id,
      keys: items.map((item) => item.browse_key),
    });
    if (token !== this._browseToken || !result) return;
    for (const item of items) item.image = result.covers[item.browse_key] || null;
    this._renderBrowse();
  }

  async _loadMore() {
    const key = this._nextKey;
    const token = this._browseToken;
    if (!key || !this._player) return;
    this._nextKey = null;
    this._renderBrowse();
    const result = await this._call({ type: "bluos_companion/browse", entry_id: this._player.entry_id, key });
    if (token !== this._browseToken || !result) return;
    this._groups[0].items.push(...result.items);
    this._nextKey = result.next_key;
    this._renderBrowse();
  }

  _search(query) {
    query = query.trim();
    if (!query) return;
    if (this._stack.length && this._stack[this._stack.length - 1].search) this._stack.pop();
    this._stack.push({ title: `\u201c${query}\u201d`, search: { key: this._searchKey, query } });
    this._browse();
  }

  get _inQueue() {
    const level = this._stack[this._stack.length - 1];
    return Boolean(level && level.queue);
  }

  _toggleQueue() {
    if (this._inQueue) {
      this._up();
      return;
    }
    this._stack.push({ title: this._t("queue"), queue: true });
    this._browse();
  }

  async _loadQueue() {
    const player = this._player;
    if (!player) return;
    const token = ++this._browseToken;
    const result = await this._call({ type: "bluos_companion/queue", entry_id: player.entry_id });
    if (token !== this._browseToken) return;
    this._queue = result ? result.items : [];
    this._queueKey = `${player.queue_id}/${player.queue_position}`;
    this._groups = [];
    this._renderBrowse();
  }

  _refreshQueue() {
    const player = this._player;
    if (!player || `${player.queue_id}/${player.queue_position}` === this._queueKey) return;
    if (this._nowQueueOpen) this._loadNowQueue();
    else if (this._inQueue) this._loadQueue();
  }

  async _queueAction(action, extra = {}) {
    await this._call({ type: "bluos_companion/queue_action", entry_id: this._playerId, action, ...extra });
    await (this._nowQueueOpen ? this._loadNowQueue() : this._loadQueue());
  }

  // The queue inside the full screen view
  // Whether a swipe (dy: the finger moved down when positive) scrolls the list, not the page behind it
  _queueCanScroll(list, dy) {
    if (list.scrollHeight <= list.clientHeight) return false;
    if (dy > 0) return list.scrollTop > 0;
    return list.scrollTop + list.clientHeight < list.scrollHeight - 1;
  }

  _setNowQueue(open) {
    this._nowQueueOpen = open;
    this._nowDialog.classList.toggle("queue-open", open);
    this._now.queueButton.classList.toggle("on", open);
    if (open) {
      this._nowQueueScroll = true;
      this._loadNowQueue();
    }
  }

  async _loadNowQueue() {
    const player = this._player;
    if (!player) return;
    const token = (this._nowQueueToken = (this._nowQueueToken || 0) + 1);
    const result = await this._call({ type: "bluos_companion/queue", entry_id: player.entry_id });
    if (token !== this._nowQueueToken || !this._nowQueueOpen) return;
    this._queue = result ? result.items : [];
    this._queueKey = `${player.queue_id}/${player.queue_position}`;
    this._renderNowQueue();
  }

  _renderNowQueue() {
    const now = this._now;
    const queue = this._queue || [];
    const current = this._player ? this._player.queue_position : null;
    now.queueActions.hidden = !queue.length;
    now.queueList.replaceChildren(
      ...(queue.length
        ? queue.map((item, index) => this._queueRow(item, index, queue.length, current))
        : [el("div", { class: "message" }, this._t("queue_empty"))]),
    );
    if (this._nowQueueScroll) {
      this._nowQueueScroll = false;
      const row = now.queueList.querySelector(".current");
      if (row) row.scrollIntoView({ block: "center" });
    }
  }

  _confirmClear() {
    this._dialog.replaceChildren(
      el("h2", {}, this._t("clear_queue_title")),
      el("p", {}, this._t("clear_queue_text")),
      el(
        "div",
        { class: "list" },
        el(
          "button",
          {
            class: "action",
            onclick: () => {
              this._dialog.close();
              this._queueAction("clear");
            },
          },
          icon("mdi:delete-sweep"),
          this._t("clear"),
        ),
      ),
    );
    this._dialog.showModal();
  }

  _askSaveName() {
    const input = el("input", { type: "text", placeholder: this._t("playlist_name"), maxlength: 100 });
    const save = async () => {
      const name = input.value.trim();
      if (!name) return;
      this._dialog.close();
      await this._call({ type: "bluos_companion/queue_action", entry_id: this._playerId, action: "save", name });
      this._notify(this._t("saved", { name }));
    };
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") save();
    });
    this._dialog.replaceChildren(
      el("h2", {}, this._t("save_queue_title")),
      input,
      el("div", { class: "list" }, el("button", { class: "action", onclick: save }, icon("mdi:content-save"), this._t("save"))),
    );
    this._dialog.showModal();
    input.focus();
  }

  _queueRow(item, index, count, current) {
    const stop = (fn) => (event) => {
      event.stopPropagation();
      fn();
    };
    const move = (to) => this._queueAction("move", { position: item.position, to });
    const moves = [
      item.position > 0 ? this._menuRow("mdi:chevron-up", this._t("move_up"), () => move(item.position - 1)) : null,
      index < count - 1 ? this._menuRow("mdi:chevron-down", this._t("move_down"), () => move(item.position + 1)) : null,
    ].filter(Boolean);
    const more = el(
      "button",
      {
        onclick: stop(() =>
          this._itemMenu({
            title: item.title,
            subtitle: [item.artist, item.album].filter(Boolean).join(" - "),
            extra: moves,
            names: item,
            info: { type: "track", artist: item.artist, album: item.album },
          }),
        ),
      },
      icon("mdi:dots-vertical"),
    );
    return el(
      "div",
      {
        class: `qrow${item.position === current ? " current" : ""}`,
        onclick: () => this._queueAction("play", { position: item.position }),
      },
      el("div", { class: "pos" }, item.position === current ? icon("mdi:volume-high") : String(item.position + 1)),
      item.image
        ? el("img", { class: "cover", src: item.image, alt: "", loading: "lazy" })
        : el("div", { class: "cover" }, icon("mdi:music")),
      el(
        "div",
        { class: "text" },
        el("div", { title: item.title }, item.title),
        el("div", { class: "sub" }, [item.artist, item.album].filter(Boolean).join(" - ") || "\u00a0"),
      ),
      more,
      el("button", { onclick: stop(() => this._queueAction("remove", { position: item.position })) }, icon("mdi:close")),
    );
  }

  _queueModeButtons() {
    return {
      shuffle: el("button", { class: "action", onclick: () => this._control("shuffle", !this._player.shuffle) }, icon("mdi:shuffle"), this._t("shuffle")),
      repeat: el("button", { class: "action", onclick: () => this._control("repeat", REPEAT_CYCLE[this._player.repeat]) }, icon("mdi:repeat"), this._t("repeat")),
    };
  }

  // The buttons above the queue, in the page of the queue and in the full screen view
  _queueActionButtons(modes) {
    return [
      modes.shuffle,
      modes.repeat,
      el("button", { class: "action", onclick: () => this._confirmClear() }, icon("mdi:delete-sweep"), this._t("clear")),
      el("button", { class: "action", onclick: () => this._askSaveName() }, icon("mdi:content-save"), this._t("save_as_playlist")),
    ];
  }

  _renderQueue() {
    const player = this._player;
    const current = player ? player.queue_position : null;
    this._grid.replaceChildren(
      ...(this._queue || []).map((item, index) => this._queueRow(item, index, this._queue.length, current)),
    );
    this._message.textContent = this._queue && !this._queue.length ? this._t("queue_empty") : "";
    this._actionRow.replaceChildren(...this._queueActionButtons(this._queueModes));
    this._actionRow.hidden = !(this._queue && this._queue.length);
  }

  // The letters of a long list: the player gives one entry per letter, with the count and the key of its entries
  _sectionItems() {
    const items = this._groups && this._groups.length === 1 ? this._groups[0].items : [];
    return items.length && items.every((item) => item.type === "section") ? items : null;
  }

  _open(item) {
    this._stack.push({
      title: item.title,
      key: item.browse_key,
      contextKey: item.context_key,
      image: item.image,
      type: item.type,
      subtitle: item.subtitle,
      tracks: item.tracks,
    });
    this._browse();
  }

  _up() {
    this._stack.pop();
    this._browse();
  }

  _home() {
    this._stack = [];
    this._browse();
    this._main.scrollTop = 0;
  }

  _play(item) {
    return this._call({
      type: "bluos_companion/play",
      entry_id: this._playerId,
      path: item.play_path,
    });
  }

  _build() {
    this._menuButton = el("button", { onclick: () => this._toggleMenu() }, icon("mdi:menu"));
    this._menuButton.hidden = !this._narrow;
    this._playerName = el("span");
    this._playerButton = el(
      "button",
      { class: "player-pill", onclick: () => this._showPlayers() },
      icon("mdi:speaker-multiple"),
      this._playerName,
    );
    this._searchInput = el("input", { type: "search", placeholder: this._t("search"), enterkeyhint: "search" });
    this._searchForm = el(
      "form",
      {
        class: "search",
        onsubmit: (event) => {
          event.preventDefault();
          this._search(this._searchInput.value);
          this._searchInput.blur();
        },
      },
      this._searchInput,
    );
    this._crumbs = el("div", { class: "crumbs" });
    this._actionRow = el("div", { class: "actions" });
    this._actionRow.hidden = true;
    this._queueModes = this._queueModeButtons();
    this._buildNow();
    this._dialogMode = null;
    this._dialog = el("dialog", {
      onclose: () => {
        this._dialogMode = null;
        clearInterval(this._groupTimer);
      },
      onclick: (event) => {
        if (event.target === this._dialog) this._dialog.close();
      },
    });
    this._grid = el("div");
    this._message = el("div", { class: "message" });
    this._main = el("main", {}, this._searchForm, this._crumbs, this._actionRow, this._grid, this._message);
    this._main.addEventListener("scroll", () => this._onBrowseScroll(), { passive: true });
    this._azStrip = el("div", { class: "az" });
    this._azStrip.hidden = true;
    this._azStrip.addEventListener("pointerdown", (event) => {
      this._azStrip.setPointerCapture(event.pointerId);
      this._azDrag = true;
      this._pickLetter(event, true);
    });
    this._azStrip.addEventListener("pointermove", (event) => {
      if (this._azDrag) this._pickLetter(event, false);
    });
    for (const name of ["pointerup", "pointercancel"]) {
      this._azStrip.addEventListener(name, () => (this._azDrag = false));
    }
    this._browseBox = el("div", { class: "browse" }, this._main, this._azStrip);

    this._cover = el("div", { class: "cover" });
    this._track = el("div", { class: "track" });
    this._artist = el("div", { class: "artist" });
    this._buttons = {
      previous: el("button", { onclick: () => this._control("previous") }, icon("mdi:skip-previous")),
      toggle: el("button", { class: "keep", onclick: () => this._togglePlayback() }, icon("mdi:play")),
      next: el("button", { onclick: () => this._control("next") }, icon("mdi:skip-next")),
      queue: el("button", { onclick: () => this._toggleQueue() }, icon("mdi:playlist-music")),
      mute: el("button", { onclick: () => this._control("mute", !this._player.muted) }, icon("mdi:volume-high")),
    };
    this._volume = el("input", {
      type: "range",
      min: 0,
      max: 100,
      oninput: () => this._armVolumeTimer(),
      onchange: (event) => this._control("volume", Number(event.target.value)),
    });
    this._volButton = el("button", { class: "vol-ring", title: this._t("volume"), onclick: () => this._openVolume() }, icon("mdi:volume-high"));
    this._moreButton = el("button", { title: this._t("more"), onclick: () => this._showMore() }, icon("mdi:dots-vertical"));
    this._miniFill = el("div");
    this._miniBar = el("div", { class: "mini-bar" }, this._miniFill);
    this._seek = el("input", {
      type: "range",
      min: 0,
      max: 0,
      step: 1,
      value: 0,
      onchange: (event) => this._control("seek", Number(event.target.value)),
      oninput: (event) => {
        this._seeking = true;
        this._showTimes(Number(event.target.value));
      },
    });
    this._elapsed = el("span", { class: "time" });
    this._total = el("span", { class: "time" });
    this._progress = el("div", { class: "progress" }, this._elapsed, this._seek, this._total);

    const footer = el(
      "footer",
      {},
      this._cover,
      this._miniBar,
      el("div", { class: "info", onclick: () => this._showNow() }, this._track, this._artist),
      el(
        "div",
        { class: "controls" },
        this._buttons.previous,
        this._buttons.toggle,
        this._buttons.next,
        this._buttons.queue,
      ),
      this._volButton,
      el(
        "div",
        { class: "volume" },
        this._buttons.mute,
        this._volume,
        this._stepButton(-1),
        this._stepButton(1),
        el("button", { title: this._t("close"), onclick: () => this._closeVolume() }, icon("mdi:close")),
      ),
      this._moreButton,
      this._progress,
    );
    this._footer = footer;

    this.shadowRoot.append(
      el("style", {}, STYLE),
      el("header", {}, this._menuButton, el("h1", { onclick: () => this._home() }, this._t("title"))),
      this._browseBox,
      footer,
      this._dialog,
      this._nowDialog,
    );
    this._built = true;
    this._fitHeight();
    this._renderPlayers();
    this._renderNowPlaying();
  }

  _toggleMenu() {
    this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
  }

  _togglePlayback() {
    const player = this._player;
    if (!player) return;
    this._control(ACTIVE_STATES.includes(player.state) ? "pause" : "play");
  }

  _renderPlayers() {
    if (!this._built) return;
    const player = this._player;
    const group = player ? this._groupName(player) : "";
    this._playerName.textContent = group || (player ? player.name : "");
    this._playerButton.firstChild.setAttribute("icon", group ? "mdi:link-variant" : "mdi:speaker-multiple");
    this._playerButton.hidden = !player;
    if (this._dialogMode === "players") this._renderPlayerList();
    if (this._dialogMode === "group") this._renderGroup();
  }

  _select(entryId) {
    if (entryId === this._playerId) return;
    this._playerId = entryId;
    localStorage.setItem(STORAGE_KEY, entryId);
    this._stack = [];
    this._browse();
    this._renderPlayers();
    this._renderNowPlaying();
  }

  // Names of the players playing together, the primary first ("" when alone).
  _groupName(player) {
    const primary = this._primaryOf(player);
    if (!primary) return "";
    const names = [primary, ...primary.group.slaves.map((id) => this._players.find((other) => other.entry_id === id))]
      .filter(Boolean)
      .map((member) => member.name);
    return names.join(" + ");
  }

  _groupLabel(player) {
    const name = (id) => (this._players.find((other) => other.entry_id === id) || {}).name;
    if (player.group.master) return this._t("grouped_with", { name: name(player.group.master) || this._t("another_player") });
    const slaves = player.group.slaves.map(name).filter(Boolean);
    return slaves.length ? this._t("group_of", { names: [player.name, ...slaves].join(" + ") }) : "";
  }

  _buildNow() {
    const now = {};
    this._now = now;
    now.player = el("span");
    now.art = el("div", { class: "art" });
    now.title = el("div", { class: "title" });
    now.sub = el("div", { class: "sub" });
    now.elapsed = el("span", { class: "time" });
    now.total = el("span", { class: "time" });
    now.seek = el("input", {
      type: "range",
      min: 0,
      max: 0,
      step: 1,
      value: 0,
      onchange: (event) => this._control("seek", Number(event.target.value)),
      oninput: (event) => {
        this._nowSeeking = true;
        this._showNowTimes(Number(event.target.value));
      },
    });
    now.progress = el("div", { class: "line" }, now.elapsed, now.seek, now.total);
    const control = (name, iconName, run, big) =>
      (now[name] = el("button", { class: big ? "big" : "", onclick: run }, icon(iconName)));
    now.controls = el(
      "div",
      { class: "line" },
      control("previous", "mdi:skip-previous", () => this._control("previous"), true),
      control("toggle", "mdi:play", () => this._togglePlayback(), true),
      control("next", "mdi:skip-next", () => this._control("next"), true),
    );
    now.mute = el("button", { onclick: () => this._control("mute", !this._player.muted) }, icon("mdi:volume-high"));
    now.volume = el("input", {
      type: "range",
      min: 0,
      max: 100,
      oninput: () => this._armVolumeTimer(),
      onchange: (event) => this._control("volume", Number(event.target.value)),
    });
    now.favourite = el(
      "button",
      { title: this._t("favourite_add"), onclick: () => this._toggleNowFavourite() },
      icon("mdi:heart-outline"),
    );
    now.dots = el(
      "button",
      { title: this._t("more"), onclick: () => this._showPlaying() },
      icon("mdi:dots-horizontal"),
    );
    now.volumeRow = el(
      "div",
      { class: "line volume-row" },
      now.mute,
      now.volume,
      this._stepButton(-1),
      this._stepButton(1),
      el("button", { title: this._t("close"), onclick: () => this._closeVolume() }, icon("mdi:close")),
    );
    now.volRing = el(
      "button",
      { class: "vol-ring", title: this._t("volume"), onclick: () => this._openNowVolume() },
      icon("mdi:volume-high"),
    );
    now.queueButton = el("button", { title: this._t("queue"), onclick: () => this._setNowQueue(!this._nowQueueOpen) }, icon("mdi:playlist-music"));
    now.bottom = el(
      "div",
      { class: "line bottom" },
      now.volRing,
      el("button", { class: "settings-button", title: this._t("more"), onclick: () => this._showMore() }, icon("mdi:tune-variant")),
      now.queueButton,
    );
    now.queueModes = this._queueModeButtons();
    now.queueActions = el("div", { class: "actions" }, ...this._queueActionButtons(now.queueModes));
    now.queueList = el("div", { class: "queue-list" });
    now.queueBox = el("div", { class: "queue-box" }, now.queueActions, now.queueList);
    this._nowDialog = el(
      "dialog",
      {
        class: "now",
        tabindex: "-1",
        autofocus: "",
        // A swipe on the full screen view must not scroll the page behind it (the queue and the sliders can)
        ontouchstart: (event) => (this._touchY = event.touches[0].clientY),
        ontouchmove: (event) => {
          if (event.target.tagName === "INPUT") return;
          const list = event.target.closest(".queue-list");
          if (list && this._queueCanScroll(list, event.touches[0].clientY - this._touchY)) return;
          event.preventDefault();
        },
        onclose: () => {
          this._nowOpen = false;
          this._closeVolume();
          this._main.style.overflowY = "";
          this._setNowQueue(false);
        },
      },
      (now.bg = el("div", { class: "bg" })),
      el("div", { class: "veil" }),
      el(
        "div",
        { class: "top" },
        el("button", { onclick: () => this._nowDialog.close() }, icon("mdi:close")),
        now.player,
        el("button", { class: "phone-only", title: this._t("more"), onclick: () => this._showMore() }, icon("mdi:dots-vertical")),
      ),
      (now.artBox = el("div", { class: "art-box" }, now.art)),
      now.queueBox,
      (now.meta = el(
        "div",
        { class: "meta" },
        el("div", { class: "text" }, now.title, now.sub),
        now.favourite,
        now.dots,
      )),
      now.progress,
      now.controls,
      now.volumeRow,
      now.bottom,
    );
  }

  _showNow() {
    if (!this._player) return;
    this._nowOpen = true;
    // Nothing of the page behind scrolls (and shows its scrollbar) under the full screen view
    this._main.style.overflowY = "hidden";
    this._renderNow();
    if (!this._nowDialog.open) this._nowDialog.showModal();
  }

  _renderNow() {
    const player = this._player;
    const now = this._now;
    if (!this._nowOpen || !player) return;
    const playing = ACTIVE_STATES.includes(player.state);
    now.player.textContent = this._groupName(player) || player.name;
    if (imageKey(player.image) !== now.imageKey) {
      now.imageKey = imageKey(player.image);
      now.bg.style.backgroundImage = player.image ? `url("${player.image}")` : "";
      now.art.replaceWith(
        (now.art = player.image ? el("img", { class: "art", src: player.image, alt: "" }) : el("div", { class: "art" })),
      );
    }
    this._nowDialog.classList.toggle("has-art", Boolean(player.image));
    this._refreshNowFavourite(player);
    now.title.textContent = player.title || player.name;
    now.sub.textContent = [player.artist, player.album].filter(Boolean).join(" - ");
    now.toggle.firstChild.setAttribute("icon", playing ? "mdi:pause" : "mdi:play");
    now.mute.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    now.volRing.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    now.volRing.style.setProperty("--level", player.max_volume ? Math.round((Math.max(player.volume, 0) / player.max_volume) * 100) : 0);
    now.volRing.disabled = player.volume < 0;
    now.volume.disabled = player.volume < 0;
    now.volume.max = player.max_volume;
    now.volume.value = Math.max(player.volume, 0);
    now.progress.hidden = !(player.duration > 0);
    now.seek.disabled = !player.can_seek;
    now.seek.max = player.duration || 0;
    this._nowSeeking = false;
    this._tickNow();
  }

  // Whether the playing track is a favourite takes a request, made when the track changes
  _refreshNowFavourite(player) {
    const key = [player.entry_id, player.service, player.title, player.artist, player.album].join("|");
    if (this._nowFavouriteKey !== key) {
      this._nowFavouriteKey = key;
      this._nowFavourite = null;
      this._renderNowFavourite();
      if (player.service === "LocalMusic" && player.title) {
        this._call({ type: "bluos_companion/playing_favourite", entry_id: this._playerId }).then((result) => {
          if (this._nowFavouriteKey !== key) return;
          this._nowFavourite = result || null;
          this._renderNowFavourite();
        });
      }
    }
  }

  _renderNowFavourite() {
    const button = this._now.favourite;
    const favourite = this._nowFavourite;
    button.disabled = !favourite;
    button.classList.toggle("on", Boolean(favourite && favourite.on));
    button.title = this._t(favourite && favourite.on ? "favourite_remove" : "favourite_add");
    button.firstChild.setAttribute("icon", favourite && favourite.on ? "mdi:heart" : "mdi:heart-outline");
  }

  async _toggleNowFavourite() {
    const favourite = this._nowFavourite;
    const player = this._player;
    if (!favourite || !player) return;
    await this._runAction({ favourite: favourite.favourite, on: favourite.on }, player.title);
    this._nowFavourite = { ...favourite, on: !favourite.on };
    this._renderNowFavourite();
  }

  _tickNow() {
    const player = this._player;
    const now = this._now;
    if (!this._nowOpen || !player || !(player.duration > 0) || this._nowSeeking) return;
    let position = player.position || 0;
    if (ACTIVE_STATES.includes(player.state)) position += (Date.now() - this._receivedAt) / 1000;
    position = Math.min(position, player.duration);
    now.seek.value = position;
    this._showNowTimes(position);
  }

  // The time played and the time left of the track
  _showNowTimes(position) {
    const player = this._player;
    if (!player || !(player.duration > 0)) return;
    this._now.elapsed.textContent = formatTime(position);
    this._now.total.textContent = `\u2212${formatTime(player.duration - position)}`;
  }

  _isPhone() {
    return window.matchMedia("(max-width: 600px)").matches;
  }

  _stepButton(direction, className) {
    return el(
      "button",
      { class: className || "", title: this._t("volume"), onclick: () => this._stepVolume(direction) },
      icon(direction < 0 ? "mdi:minus" : "mdi:plus"),
    );
  }

  _stepVolume(direction) {
    const player = this._player;
    if (!player || player.volume < 0) return;
    this._armVolumeTimer();
    this._control("volume", Math.min(player.max_volume, Math.max(0, Math.round(player.volume) + direction * 2)));
  }

  _openVolume() {
    this._footer.classList.add("vol-open");
    this._armVolumeTimer();
  }

  _openNowVolume() {
    this._nowDialog.classList.add("vol-open");
    this._armVolumeTimer();
  }

  _closeVolume() {
    clearTimeout(this._volumeTimer);
    this._footer.classList.remove("vol-open");
    this._nowDialog.classList.remove("vol-open");
  }

  // The volume strip goes back to the bar after a few seconds without a touch
  _armVolumeTimer() {
    clearTimeout(this._volumeTimer);
    this._volumeTimer = setTimeout(() => this._closeVolume(), 5000);
  }

  _sourceOptions(player) {
    return [
      el("option", { value: "", disabled: "" }, this._t("input")),
      ...player.sources.map((name) => el("option", { value: name }, name)),
    ];
  }

  _sleepOptions(player) {
    return [0, ...player.sleep_options].map((minutes) =>
      el("option", { value: minutes }, minutes ? this._t("minutes", { minutes }) : this._t("sleep_off")),
    );
  }

  // The input and the sleep timer, as the fields of a popup
  _settingRows(player) {
    const rows = [];
    if (player.sources.length) {
      const source = el("select", { onchange: (event) => this._control("source", event.target.value) }, ...this._sourceOptions(player));
      source.value = player.source || "";
      rows.push(el("label", {}, this._t("input"), source));
    }
    const sleep = el("select", { onchange: (event) => this._control("sleep", Number(event.target.value)) }, ...this._sleepOptions(player));
    sleep.value = player.sleep;
    rows.push(el("label", {}, this._t("sleep_timer"), sleep));
    return rows;
  }

  // What the bars leave out: the queue, the player, moving the playback, the input and the sleep timer
  _showMore() {
    const player = this._player;
    if (!player) return;
    const row = (name, iconName, onclick, on = false) =>
      el("button", { class: `action${on ? " on" : ""}`, onclick }, icon(iconName), name);
    const list = el(
      "div",
      { class: "list more-list" },
      row(this._groupName(player) || player.name, "mdi:speaker-multiple", () => this._showPlayers()),
    );
    // The queue has its own button in the bar (tablet, desktop) and in the full screen view
    if (!this._nowDialog.open && this._isPhone()) {
      list.prepend(
        row(this._t("queue"), "mdi:playlist-music", () => {
          this._dialog.close();
          if (!this._inQueue) this._toggleQueue();
        }),
      );
    }
    if (this._canMove(player)) list.append(row(this._t("move_playback"), "mdi:transfer-right", () => this._showMove()));
    list.append(...this._settingRows(player));
    this._dialogMode = "more";
    this._dialog.replaceChildren(el("h2", {}, this._t("more")), list);
    if (!this._dialog.open) this._dialog.showModal();
  }

  _showPlayers() {
    this._dialogMode = "players";
    this._renderPlayerList();
    if (!this._dialog.open) this._dialog.showModal();
  }

  _primaryOf(player) {
    if (player.group.master) return this._players.find((other) => other.entry_id === player.group.master);
    return player.group.slaves.length ? player : null;
  }

  // Moving replaces what the target plays, so only offer it for a player that plays.
  _canMove(player) {
    return player.can_move && ACTIVE_STATES.includes(player.state) && this._players.length > 1;
  }

  _showMove() {
    const source = this._player;
    if (!source) return;
    this._dialogMode = "move";
    this._dialog.replaceChildren(
      el("h2", {}, this._t("move_playback_to")),
      el("p", {}, `${source.name}: ${[source.title, source.artist].filter(Boolean).join(" - ")}`),
      el(
        "div",
        { class: "list" },
        ...this._players
          .filter((target) => target.entry_id !== source.entry_id)
          .map((target) =>
            el(
              "button",
              {
                class: "action player-row",
                onclick: async () => {
                  this._dialog.close();
                  await this._call({ type: "bluos_companion/move", entry_id: source.entry_id, target: target.entry_id });
                  this._select(target.entry_id);
                },
              },
              target.image
                ? el("img", { class: "cover", src: target.image, alt: "" })
                : el("div", { class: "cover" }, icon("mdi:speaker")),
              el(
                "div",
                { class: "text" },
                el("div", { class: "name" }, target.name),
                el("div", { class: "sub" }, [target.title, target.artist].filter(Boolean).join(" - ") || "\u00a0"),
              ),
              icon("mdi:transfer-right"),
            ),
          ),
      ),
    );
    this._dialog.showModal();
  }

  _showGroup() {
    this._dialogMode = "group";
    this._groupVolumes = {};
    this._renderGroup();
    if (!this._dialog.open) this._dialog.showModal();
    this._refreshGroupVolumes();
    clearInterval(this._groupTimer);
    this._groupTimer = setInterval(() => this._refreshGroupVolumes(), 3000);
  }

  // /Status of a secondary player shows the volume of the group, so ask each player.
  async _refreshGroupVolumes() {
    if (this._dialogMode !== "group" || !this._player) return;
    const result = await this._call({ type: "bluos_companion/group_volumes", entry_id: this._player.entry_id });
    if (this._dialogMode !== "group" || !result) return;
    this._groupVolumes = Object.fromEntries(result.volumes.map((volume) => [volume.entry_id, volume]));
    this._renderGroup();
  }

  _renderGroup() {
    // Do not rebuild the dialog while a slider is being dragged.
    const active = this.shadowRoot.activeElement;
    if (active && active.tagName === "INPUT" && this._dialog.contains(active)) return;
    const current = this._player;
    const primary = current ? this._primaryOf(current) : null;
    const members = primary
      ? [primary, ...primary.group.slaves.map((id) => this._players.find((other) => other.entry_id === id)).filter(Boolean)]
      : current
        ? [current]
        : [];
    const inGroup = (player) => members.some((member) => member.entry_id === player.entry_id);
    const toggle = (player) =>
      this._call(
        inGroup(player)
          ? { type: "bluos_companion/group", entry_id: player.entry_id, action: "leave" }
          : { type: "bluos_companion/group", entry_id: player.entry_id, action: "join", target: current.entry_id },
      );
    const row = (player) => {
      const member = inGroup(player);
      const line = el(
        "div",
        { class: "line" },
        el(
          "button",
          { class: "action", style: "flex: 1", onclick: () => toggle(player) },
          icon(member ? "mdi:checkbox-marked-circle" : "mdi:checkbox-blank-circle-outline"),
          player.name,
        ),
      );
      if (!member) return el("div", { class: "group-row" }, line);
      const own = this._groupVolumes[player.entry_id];
      const level = own ? own.volume : player.volume;
      const change = (action, value) =>
        Promise.resolve(this._control(action, value, player.entry_id)).then(() => this._refreshGroupVolumes());
      const slider = el("input", {
        type: "range",
        min: 0,
        max: own ? own.max_volume : player.max_volume,
        value: Math.max(level, 0),
        onchange: (event) => change("volume", Number(event.target.value)),
      });
      slider.disabled = level < 0;
      return el(
        "div",
        { class: "group-row" },
        line,
        el(
          "div",
          { class: "line" },
          icon(own && own.muted ? "mdi:volume-off" : "mdi:volume-medium"),
          slider,
          el("button", { onclick: () => change("volume_step", -2) }, icon("mdi:minus")),
          el("button", { onclick: () => change("volume_step", 2) }, icon("mdi:plus")),
        ),
      );
    };
    const rows = [el("h2", {}, this._t("group_players")), el("p", {}, this._t("group_hint"))];
    rows.push(el("div", { class: "list" }, ...this._players.map(row)));
    if (members.length > 1 && primary) {
      const step = (delta) =>
        Promise.resolve(this._control("volume_step", delta, primary.entry_id, { group: true })).then(() =>
          this._refreshGroupVolumes(),
        );
      rows.push(
        el(
          "div",
          { class: "group-volume" },
          el("span", { class: "label" }, this._t("group_volume")),
          el("button", { onclick: () => this._control("mute", !primary.muted, primary.entry_id, { group: true }) }, icon("mdi:volume-off")),
          el("button", { onclick: () => step(-2) }, icon("mdi:minus")),
          el("button", { onclick: () => step(2) }, icon("mdi:plus")),
        ),
      );
    }
    const footer = [];
    if (members.length > 1 && primary) {
      footer.push(
        el(
          "button",
          {
            class: "action",
            onclick: () => this._call({ type: "bluos_companion/group", entry_id: primary.entry_id, action: "leave" }),
          },
          icon("mdi:link-variant-off"),
          this._t("ungroup_all"),
        ),
      );
    }
    footer.push(el("button", { class: "action", onclick: () => this._showPlayers() }, icon("mdi:arrow-left"), this._t("back")));
    rows.push(el("div", { class: "list", style: "margin-top: 12px" }, ...footer));
    this._dialog.replaceChildren(...rows);
  }

  _renderPlayerList() {
    this._dialog.replaceChildren(
      el("h2", {}, this._t("play_on")),
      el(
        "div",
        { class: "list" },
        ...this._players.map((player) => {
          const playing = ACTIVE_STATES.includes(player.state);
          const what = player.available
            ? [player.title, player.artist].filter(Boolean).join(" - ")
            : this._t("unavailable");
          return el(
            "button",
            {
              class: `action player-row${player.entry_id === this._playerId ? " selected" : ""}`,
              onclick: () => {
                this._select(player.entry_id);
                this._dialog.close();
              },
            },
            player.image
              ? el("img", { class: "cover", src: player.image, alt: "" })
              : el("div", { class: "cover" }, icon("mdi:speaker")),
            el(
              "div",
              { class: "text" },
              el("div", { class: "name" }, player.name),
              el("div", { class: "sub" }, what || "\u00a0"),
              this._groupLabel(player) ? el("div", { class: "sub" }, this._groupLabel(player)) : null,
            ),
            icon(playing ? "mdi:play-circle" : player.state === "pause" ? "mdi:pause-circle" : "mdi:stop-circle-outline"),
          );
        }),
      ),
      ...(this._players.length > 1
        ? [
            el(
              "div",
              { class: "list", style: "margin-top: 12px" },
              el("button", { class: "action", onclick: () => this._showGroup() }, icon("mdi:speaker-multiple"), this._t("group_players")),
            ),
          ]
        : []),
    );
  }

  // Artists, composers, genres and tracks are flat rows, the rest (albums, playlists...) tiles
  _appendItems(items, level, target = this._grid) {
    const album = Boolean(level && level.type === "album");
    let rows = null;
    let grid = null;
    for (const item of items) {
      if (ROW_TYPES.includes(item.type) || (item.type === "album" && this._albumRows)) {
        grid = null;
        if (!rows) target.append((rows = el("div", { class: "rows" })));
        rows.append(this._row(item, album));
      } else {
        rows = null;
        if (!grid) target.append((grid = el("div", { class: "grid" })));
        grid.append(this._tile(item));
      }
    }
  }

  // The number of a track of an album is part of its title ("3. Title")
  _row(item, album) {
    let title = item.title;
    let number = null;
    if (album) {
      const found = /^(\d+)\.\s+(.*)$/.exec(title);
      if (found) [, number, title] = found;
    }
    // An album also says how many tracks it has
    const subtitle =
      item.type === "album" && item.tracks
        ? [item.subtitle, this._t("tracks_count", { count: item.tracks })].filter(Boolean).join(" \u2022 ")
        : item.subtitle;
    const withCover = !album && (item.type === "track" || item.type === "album");
    return el(
      "div",
      { class: "lrow", onclick: () => (item.browse_key ? this._open(item) : this._play(item)) },
      album ? el("div", { class: "num" }, number || "") : null,
      withCover
        ? item.image
          ? el("img", { class: "cover", src: item.image, loading: "lazy", alt: "" })
          : el("div", { class: "cover" }, icon("mdi:music"))
        : null,
      el(
        "div",
        { class: "text" },
        el("div", { class: "title", title }, title),
        subtitle ? el("div", { class: "sub" }, subtitle) : null,
      ),
      item.duration ? el("div", { class: "time" }, formatTime(item.duration)) : null,
      item.context_key
        ? el(
            "button",
            {
              title: this._t("more"),
              onclick: (event) => {
                event.stopPropagation();
                this._showActions(item);
              },
            },
            icon("mdi:dots-vertical"),
          )
        : null,
      item.browse_key ? el("span", { class: "chev" }, icon("mdi:chevron-right")) : null,
    );
  }

  // The header of the page of an album: its cover, what it is, and what to do with it
  _albumHead(level) {
    const tracks = level.tracks || (this._groups || []).reduce((sum, group) => sum + group.items.filter((item) => item.type === "track").length, 0);
    this._albumActions = el("div", { class: "ah-actions" });
    const head = el(
      "div",
      { class: "album-head" },
      level.image ? el("div", { class: "ah-bg", style: `background-image: url("${level.image}")` }) : null,
      el("div", { class: "ah-veil" }),
      el(
        "div",
        { class: "ah-body" },
        level.image
          ? el("img", { class: "ah-cover", src: level.image, alt: "" })
          : el("div", { class: "ah-cover" }, icon("mdi:music")),
        el(
          "div",
          { class: "ah-text" },
          el("h2", {}, level.title),
          level.subtitle ? el("div", { class: "ah-artist" }, level.subtitle) : null,
          tracks ? el("div", { class: "ah-meta" }, this._t("tracks_count", { count: tracks })) : null,
          this._albumActions,
        ),
      ),
    );
    this._renderAlbumActions();
    return head;
  }

  _renderAlbumActions() {
    const level = this._stack[this._stack.length - 1];
    const box = this._albumActions;
    if (!box || !level || level.type !== "album") return;
    const actions = this._levelActions || [];
    const play = actions.find((action) => action.type === "add-now");
    const shuffle = actions.find((action) => action.type.endsWith("-shuffle"));
    const rest = actions.filter((action) => action !== play && action !== shuffle);
    box.replaceChildren(
      ...[
        play
          ? el("button", { class: "primary", onclick: () => this._runAction(play, level.title) }, icon("mdi:play"), this._t("play_all"))
          : null,
        shuffle
          ? el("button", { onclick: () => this._runAction(shuffle, level.title) }, icon("mdi:shuffle"), this._t("shuffle"))
          : null,
        rest.length
          ? el(
              "button",
              { class: "round", title: this._t("more"), onclick: () => this._showLevelActions(level, rest) },
              icon("mdi:dots-vertical"),
            )
          : null,
      ].filter(Boolean),
    );
  }

  _showLevelActions(level, actions) {
    this._itemMenu({
      title: level.title,
      subtitle: level.subtitle,
      actions,
      names: level.subtitle ? { artist: level.subtitle } : {},
      info: { type: level.type, artist: level.subtitle, tracks: level.tracks },
    });
  }


  // The page of an artist, a composer or a genre is a menu of lists (albums, songs...)
  _isLandingLevel(level) {
    if (!level || !LANDING_TYPES.includes(level.type) || !this._groups || this._groups.length !== 1) return false;
    const items = this._groups[0].items;
    return items.length > 0 && items.every((item) => item.type === "link");
  }

  async _loadLanding(level, token) {
    const result = await this._call({ type: "bluos_companion/landing", entry_id: this._player.entry_id, key: level.key });
    if (token !== this._browseToken) return;
    this._landing = result ? result.sections : false;
    this._renderBrowse();
  }

  // A few albums (a row to scroll), a few songs or artists, and View all for the whole lists
  _renderLanding(level) {
    if (this._landing === null) {
      this._message.textContent = "\u2026";
      return;
    }
    if (this._landing === false) {
      this._appendItems(this._groups[0].items, level);
      return;
    }
    const root = el("div", { class: "landing" });
    for (const section of this._landing) {
      const open = () => this._open({ title: section.title, browse_key: section.browse_key, type: "link" });
      // Nothing in a list: no card for it (and composers, if there are some, are one row to open)
      if (!section.items.length) continue;
      const card = el("section", { class: "lsec" });
      if (section.kind === "composers") {
        card.append(
          el("div", { class: "lrow link", onclick: open }, el("div", { class: "text" }, el("div", { class: "title" }, section.title)), el("span", { class: "chev" }, icon("mdi:chevron-right"))),
        );
        root.append(card);
        continue;
      }
      const head = el("div", { class: "lsec-head" }, el("h3", { onclick: open }, section.title));
      if (section.kind === "albums") {
        const scroller = el("div", { class: "hscroll" });
        this._appendItems(section.items, level, scroller);
        const grid = scroller.querySelector(".grid");
        if (grid) scroller.replaceChildren(...grid.children);
        const scrollBy = (direction) => scroller.scrollBy({ left: direction * scroller.clientWidth * 0.8, behavior: "smooth" });
        head.append(
          el("button", { class: "arrow", onclick: () => scrollBy(-1) }, icon("mdi:chevron-left")),
          el("button", { class: "arrow", onclick: () => scrollBy(1) }, icon("mdi:chevron-right")),
        );
        head.append(el("button", { class: "viewall", onclick: open }, this._t("view_all")));
        card.append(head, scroller);
      } else {
        head.append(el("button", { class: "viewall", onclick: open }, this._t("view_all")));
        card.append(head);
        this._appendItems(section.items, level, card);
      }
      root.append(card);
    }
    this._grid.append(root);
  }

  // The first letter of a title as the player sorts it: `#` for what does not start with a letter
  _initial(title) {
    const letter = title.normalize("NFD").replace(/[\u0300-\u036f]/g, "").charAt(0).toUpperCase();
    return /[A-Z]/.test(letter) ? letter : "#";
  }

  // A long list given in alphabetical order gets its letters too
  _preference(key, allowed, fallback) {
    let value = null;
    try {
      value = localStorage.getItem(key);
    } catch (err) {
      // a browser that refuses storage keeps the default
    }
    return allowed.includes(value) ? value : fallback;
  }

  _remember(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (err) {
      // not kept, that is all
    }
  }

  // Whether the page lists albums to browse (and so offers the display and the sort), not the albums of a search
  _isAlbumList(level) {
    if (!level || level.search || level.queue || level.type === "album" || !this._groups) return false;
    const letters = this._sectionItems();
    if (letters) return letters.some((item) => item.browse_key && item.browse_key.startsWith("LocalMusic:S:Album/"));
    return this._groups.length === 1 && !this._isLandingLevel(level) && this._groups[0].items.some((item) => item.type === "album");
  }

  // Display (list or grid) and, for the whole library, the sort of a list of albums
  _listControls(level) {
    const display = this._preference(DISPLAY_KEY, ["list", "grid"], "list");
    const controls = el(
      "div",
      { class: "list-controls" },
      el(
        "button",
        {
          onclick: () => {
            this._remember(DISPLAY_KEY, display === "list" ? "grid" : "list");
            this._redraw();
          },
        },
        icon(display === "list" ? "mdi:view-list" : "mdi:view-grid"),
        this._t("display_label", { mode: this._t(display === "list" ? "display_list" : "display_grid") }),
      ),
    );
    if (level.key === ALBUMS_KEY) {
      const sort = this._preference(ALBUM_SORT_KEY, ALBUM_SORTS, "az");
      const select = el(
        "select",
        {
          onchange: (event) => {
            this._remember(ALBUM_SORT_KEY, event.target.value);
            this._redraw();
          },
        },
        ...ALBUM_SORTS.map((name) => el("option", { value: name }, this._t(`sort_${name}`))),
      );
      select.value = sort;
      controls.append(select);
    }
    return controls;
  }

  _redraw() {
    this._clearSectioned();
    this._renderBrowse();
  }

  // The albums of the library sorted and grouped: by year, decade, artist...
  _albumSections(sort, data) {
    const plain = (text) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const byTitle = (a, b) => plain(a.title).localeCompare(plain(b.title));
    const byYear = (a, b) => (a.year || 9999) - (b.year || 9999) || byTitle(a, b);
    const decade = (year) => (year ? `${Math.floor(year / 10) * 10}s` : this._t("unknown_year"));
    const groups = new Map();
    const add = (title, strip, item) => {
      if (!groups.has(title)) groups.set(title, { title, strip, items: [] });
      groups.get(title).items.push(item);
    };
    if (sort === "recent") {
      const known = new Map(data.albums.map((album) => [`${album.title}\u0000${album.subtitle}`, album]));
      for (const [title, artist] of data.recent) {
        const album = known.get(`${title}\u0000${artist}`);
        if (album) add(this._t("sort_recent"), this._t("sort_recent"), album);
      }
    } else if (sort === "year" || sort === "decade") {
      for (const album of [...data.albums].sort(byYear)) {
        const label = decade(album.year);
        add(sort === "year" ? String(album.year || this._t("unknown_year")) : label, label, album);
      }
    } else {
      const artists = [...data.albums].sort((a, b) => plain(a.subtitle).localeCompare(plain(b.subtitle)) || (sort === "artist_year" ? byYear(a, b) : byTitle(a, b)));
      for (const album of artists) add(album.subtitle || "?", this._initial(album.subtitle || "?"), album);
    }
    return [...groups.values()].map((group) => ({ ...group, count: group.items.length }));
  }

  async _loadAlbumsData() {
    if (this._albumsLoading || !this._player) return;
    this._albumsLoading = true;
    const result = await this._call({ type: "bluos_companion/albums", entry_id: this._player.entry_id });
    this._albumsLoading = false;
    this._albumsData = result ? { entry: this._player.entry_id, ...result } : false;
    this._redraw();
  }

  _isLettered() {
    if (!this._groups || this._groups.length !== 1) return false;
    const items = this._groups[0].items;
    if (items.length < INITIALS_FROM || !items.every((item) => ROW_TYPES.includes(item.type) && item.type !== "track")) return false;
    const rank = (item) => {
      const letter = this._initial(item.title);
      return letter === "#" ? "" : letter;
    };
    return items.every((item, index) => index === 0 || rank(items[index - 1]) <= rank(item));
  }

  _localSections(items) {
    const sections = [];
    for (const item of items) {
      const letter = this._initial(item.title);
      const last = sections[sections.length - 1];
      if (last && last.title === letter) last.items.push(item);
      else sections.push({ title: letter, items: [item] });
    }
    return sections.map((section) => ({ ...section, count: section.items.length }));
  }

  // The estimated height of the entries of a letter that is not loaded yet, so that the page has its final length
  _estimate(view, section) {
    if (section.key && section.key.startsWith("LocalMusic:S:Album/") && !this._albumRows) {
      const width = Math.max(150, this._main.clientWidth - 70);
      const columns = Math.max(1, Math.floor((width + 16) / 166));
      const tile = view.itemHeight || (width - (columns - 1) * 16) / columns + 70;
      return Math.ceil(section.count / columns) * (tile + 16);
    }
    return section.count * ROW_HEIGHT;
  }

  // A list drawn letter by letter: the headers at once, the entries of a letter when it is near or jumped to
  _buildSectioned(kind, specs, level) {
    // The albums as a grid on a wide screen flow in one grid, the letters being cells of it
    if (this._albumGrid && window.matchMedia("(min-width: 601px)").matches) {
      this._buildFlow(kind, specs, level);
      return;
    }
    const root = el("div", { class: "sectioned" });
    const view = { kind, groups: this._groups, root, sections: [], level, itemHeight: 0, timer: null, observer: null };
    for (const spec of specs) {
      const head = el("h3", { class: "sec-head" }, spec.title);
      head.hidden = specs.length === 1 && kind === "local";
      const body = el("div", { class: "sec-body" });
      const wrap = el("div", { class: "sec" }, head, body);
      const section = { ...spec, wrap, head, body, state: spec.items ? "done" : "idle", seen: new Set(), targets: [wrap] };
      view.sections.push(section);
      root.append(wrap);
      if (section.state === "done") this._fillSection(view, section);
      else body.style.minHeight = `${this._estimate(view, section)}px`;
    }
    this._grid.append(root);
    this._finishSectioned(view);
  }

  // One grid for all the letters: a cell with the letter, then the albums of the letter (empty cells of the same
  // size stand for those not loaded yet, so that the grid has its final size and nothing moves when they come)
  _buildFlow(kind, specs, level) {
    const root = el("div", { class: "grid flow" });
    const view = { kind, groups: this._groups, root, sections: [], level, timer: null, observer: null, flow: true };
    const blank = (view.blank = el(
      "div",
      { class: "tile ph" },
      el("div", { class: "artwrap" }, el("div", { class: "art empty" })),
      el("div", { class: "text" }, el("div", { class: "title" }, "\u00a0"), el("div", { class: "subtitle" }, "\u00a0")),
    ));
    for (const spec of specs) {
      // A list of one group (the recent albums) needs no card to name it
      const head = el("div", { class: "tile hcell" }, el("span", { class: "hlabel" }, spec.title));
      head.hidden = specs.length === 1;
      const section = { ...spec, wrap: head, state: spec.items ? "done" : "idle", seen: new Set(), targets: [], cells: [] };
      view.sections.push(section);
      root.append(head);
      if (section.items) {
        section.tiles = section.items.map((item) => this._tile(item));
        root.append(...section.tiles);
      } else {
        for (let index = 0; index < section.count; index++) {
          const cell = blank.cloneNode(true);
          section.cells.push(cell);
          section.targets.push(cell);
        }
        root.append(...section.cells);
      }
    }
    this._grid.append(root);
    this._finishSectioned(view);
  }

  // The letters that are near are loaded, the others wait; then the strip with the letters
  _finishSectioned(view) {
    this._sectionedView = view;
    if (view.kind === "server") {
      view.observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            const section = entry.target._section;
            if (entry.isIntersecting) section.seen.add(entry.target);
            else section.seen.delete(entry.target);
          }
          clearTimeout(view.timer);
          view.timer = setTimeout(() => {
            for (const section of view.sections) if (section.seen.size) this._loadSection(view, section);
            this._unloadFar(view);
          }, 120);
        },
        { root: this._main, rootMargin: "600px 0px" },
      );
      for (const section of view.sections) {
        for (const target of section.targets) {
          target._section = section;
          view.observer.observe(target);
        }
      }
    }
    // The strip has one entry for the sections that share a label (the albums of a decade, the artists of a letter)
    view.strips = [];
    view.sections.forEach((section, index) => {
      const label = section.strip || section.title;
      if (!view.strips.length || view.strips[view.strips.length - 1].label !== label) view.strips.push({ label, index });
    });
    this._azStrip.replaceChildren(...view.strips.map((entry) => el("div", {}, entry.label)));
    this._azStrip.hidden = view.strips.length < 2;
    this._main.classList.add("with-az");
    // A scrollbar that takes room (a mouse) must not lie under the strip
    this._browseBox.style.setProperty("--scrollbar", `${this._main.offsetWidth - this._main.clientWidth}px`);
    this._onBrowseScroll();
  }

  _fillSection(view, section) {
    if (view.flow) {
      this._fillFlow(section);
      return;
    }
    section.body.replaceChildren();
    this._appendItems(section.items, view.level, section.body);
    section.body.style.minHeight = "";
    this._loadFirstCovers(section.body);
    // A grid has no fixed height: what a loaded one measures serves for the estimate of the others
    if (section.key && section.key.startsWith("LocalMusic:S:Album/") && section.items.length && !this._albumRows) {
      const grid = section.body.querySelector(".grid");
      const rows = grid ? getComputedStyle(grid).gridTemplateColumns.split(" ").length : 1;
      if (grid) view.itemHeight = grid.offsetHeight / Math.ceil(section.items.length / rows) - 16;
    }
  }

  // The letters far from what shows are given back (their entries, their covers), as empty space of the same size
  _unloadFar(view) {
    const box = this._main.getBoundingClientRect();
    for (const section of view.sections) {
      if (section.state !== "done") continue;
      const first = section.wrap.getBoundingClientRect();
      const tiles = section.tiles || [];
      const last = (tiles.length ? tiles[tiles.length - 1] : section.wrap).getBoundingClientRect();
      if (last.bottom >= box.top - FAR && first.top <= box.bottom + FAR) continue;
      if (view.flow) {
        const cells = tiles.map((tile) => {
          const cell = view.blank.cloneNode(true);
          tile.replaceWith(cell);
          cell._section = section;
          view.observer.observe(cell);
          return cell;
        });
        section.cells = cells;
        section.targets = cells;
        section.tiles = [];
      } else {
        section.body.style.minHeight = `${section.body.offsetHeight}px`;
        section.body.replaceChildren();
      }
      section.items = null;
      section.seen = new Set();
      section.state = "idle";
    }
  }

  // The albums replace the empty cells that stand for them
  _fillFlow(section) {
    const tiles = section.items.map((item) => this._tile(item));
    let last = section.wrap;
    tiles.forEach((tile, index) => {
      const cell = section.cells[index];
      if (cell) cell.replaceWith(tile);
      else last.after(tile);
      last = tile;
    });
    section.cells.slice(tiles.length).forEach((cell) => cell.remove());
    section.cells = [];
    section.tiles = tiles;
    this._loadFirstCovers(section.wrap.parentElement, tiles.slice(0, 30));
  }

  // The first covers of a letter are those that show after a jump: they are not left to the lazy loading
  _loadFirstCovers(root, tiles) {
    const images = tiles ? tiles.flatMap((tile) => [...tile.querySelectorAll("img")]) : [...root.querySelectorAll("img")];
    for (const image of images.slice(0, 30)) image.loading = "eager";
  }

  async _loadSection(view, section) {
    if (section.state !== "idle" || !this._player) return;
    section.state = "loading";
    if (!view.flow) section.body.replaceChildren(el("div", { class: "sec-loading" }, "\u2026"));
    // The whole letter in one request
    const key = section.key.replace(/limit=\d+/, `limit=${section.count + 50}`);
    const result = await this._call({ type: "bluos_companion/browse", entry_id: this._player.entry_id, key });
    if (this._sectionedView !== view) return;
    if (!result) {
      section.state = "idle";
      if (!view.flow) section.body.replaceChildren();
      return;
    }
    section.items = result.items;
    section.state = "done";
    this._fillSection(view, section);
  }

  _clearSectioned() {
    const view = this._sectionedView;
    if (view) {
      if (view.observer) view.observer.disconnect();
      clearTimeout(view.timer);
    }
    this._sectionedView = null;
    this._azStrip.hidden = true;
    this._azStrip.replaceChildren();
    this._main.classList.remove("with-az");
  }

  // A letter of the strip, touched or dragged on: the list jumps to its entries
  _pickLetter(event, load) {
    const view = this._sectionedView;
    if (!view) return;
    const rect = this._azStrip.getBoundingClientRect();
    const entry = Math.min(view.strips.length - 1, Math.max(0, Math.floor(((event.clientY - rect.top) / rect.height) * view.strips.length)));
    const section = view.sections[view.strips[entry].index];
    const delta = section.wrap.getBoundingClientRect().top - this._main.getBoundingClientRect().top;
    this._main.scrollTop += delta - 8;
    // The way back would hide the letter that was jumped to: it comes back with the next scroll up
    this._lastScroll = this._main.scrollTop;
    this._crumbs.classList.toggle("away", this._lastScroll >= 80);
    if (load && view.kind === "server") this._loadSection(view, section);
  }

  // Scrolling down hides the way back, scrolling up (or being near the top) shows it
  _hideCrumbs() {
    const top = this._main.scrollTop;
    const delta = top - (this._lastScroll || 0);
    if (top < 80 || delta < -6) this._crumbs.classList.remove("away");
    else if (delta > 6) this._crumbs.classList.add("away");
    this._lastScroll = top;
  }

  // The letter at the top of the list is the one of the strip that is lit
  _onBrowseScroll() {
    if (this._scrollFrame) return;
    this._scrollFrame = requestAnimationFrame(() => {
      this._scrollFrame = null;
      this._hideCrumbs();
      const view = this._sectionedView;
      if (!view) return;
      const top = this._main.getBoundingClientRect().top + 24;
      let current = 0;
      view.sections.forEach((section, index) => {
        if (section.wrap.getBoundingClientRect().top <= top) current = index;
      });
      const lit = view.strips.reduce((found, entry, position) => (entry.index <= current ? position : found), 0);
      [...this._azStrip.children].forEach((node, index) => node.classList.toggle("current", index === lit));
    });
  }

  _renderBrowse() {
    if (!this._built) return;
    this._albumActions = null;
    this._albumRows = false;
    this._albumGrid = false;
    this._renderCrumbs();
    this._buttons.queue.classList.toggle("on", this._inQueue);
    // A list of letters already on screen stays, with what it has loaded
    const view = this._sectionedView;
    if (view && view.kind === "server" && view.groups === this._groups && !this._inQueue && this._grid.contains(view.root)) return;
    this._clearSectioned();
    this._grid.replaceChildren();
    this._message.textContent = "";
    this._searchForm.hidden = !this._player || this._inQueue;
    if (this._inQueue) {
      this._renderQueue();
      return;
    }
    if (!this._player) {
      this._message.textContent = this._t("no_player");
    } else if (this._groups === null) {
      this._message.textContent = "\u2026";
    } else if (!this._groups.some((group) => group.items.length)) {
      this._message.textContent = this._t("nothing_here");
    } else {
      const level = this._stack[this._stack.length - 1];
      if (level && level.type === "album") this._grid.append(this._albumHead(level));
      const letters = this._sectionItems();
      const albums = this._isAlbumList(level);
      this._albumRows = albums && this._preference(DISPLAY_KEY, ["list", "grid"], "list") === "list";
      this._albumGrid = albums && !this._albumRows;
      if (albums) this._grid.append(this._listControls(level));
      // The other sorts need the albums of the whole library (if the player does not give them, the letters stay)
      const sort = level && level.key === ALBUMS_KEY && this._albumsData !== false ? this._preference(ALBUM_SORT_KEY, ALBUM_SORTS, "az") : "az";
      if (this._isLandingLevel(level)) {
        this._renderLanding(level);
      } else if (letters && sort !== "az") {
        const data = this._albumsData;
        if (data && data.entry === this._player.entry_id) this._buildSectioned("local", this._albumSections(sort, data), level);
        else {
          this._message.textContent = "\u2026";
          this._loadAlbumsData();
        }
      } else if (letters) {
        this._buildSectioned(
          "server",
          letters.map((item) => ({ title: item.title, count: Number(item.subtitle) || 0, key: item.browse_key })),
          level,
        );
      } else if (this._isLettered()) {
        this._buildSectioned("local", this._localSections(this._groups[0].items), level);
      } else {
        for (const group of this._groups) {
          if (!group.items.length) continue;
          if (group.title) this._grid.append(el("h3", {}, group.title));
          this._appendItems(group.items, level);
        }
      }
      if (this._nextKey) {
        this._grid.append(
          el(
            "div",
            { class: "actions", style: "justify-content: center; margin: 16px 0" },
            el("button", { class: "action", onclick: () => this._loadMore() }, icon("mdi:chevron-down"), this._t("show_more")),
          ),
        );
      }
    }
  }

  _renderCrumbs() {
    const level = this._stack[this._stack.length - 1];
    this._crumbs.replaceChildren(
      ...(level
        ? [
            el("button", { title: this._t("back"), onclick: () => this._up() }, icon("mdi:arrow-left")),
            // From the second level on, a quick way back to the home page
            this._stack.length > 1
              ? el("button", { title: this._t("home"), onclick: () => this._home() }, icon("mdi:home"))
              : null,
            // The page of an album has its own header
            level.type !== "album" && level.image && !level.image.includes("/bluos_companion/icons/")
              ? el("img", { class: "crumb-cover", src: level.image, alt: "" })
              : null,
            level.type !== "album" ? el("h2", {}, level.title) : null,
          ].filter(Boolean)
        : []),
    );
    if (level && level.queue) return;
    if (level && level.type === "album") {
      this._actionRow.hidden = true;
      this._renderAlbumActions();
      return;
    }
    const actions = level ? this._levelActions : [];
    this._actionRow.replaceChildren(...actions.map((action) => this._actionButton(action, level.title)));
    this._actionRow.hidden = !actions.length;
  }

  _tile(item) {
    const own = item.image && item.image.includes("/bluos_companion/icons/");
    const art = item.image
      ? el("img", { class: own ? "art icon" : item.type === "link" ? "art logo" : "art", src: item.image, loading: "lazy", alt: "" })
      : el("div", { class: "art empty" }, icon("mdi:music"));
    const tile = el(
      "div",
      { class: "tile", onclick: () => (item.browse_key ? this._open(item) : this._play(item)) },
      el("div", { class: "artwrap" }, art),
      el(
        "div",
        { class: "text" },
        el("div", { class: "title", title: item.title }, item.title),
        el("div", { class: "subtitle" }, item.subtitle || " "),
      ),
    );
    if (item.browse_key && item.play_path) {
      tile.firstChild.append(
        el(
          "button",
          {
            class: "play",
            onclick: (event) => {
              event.stopPropagation();
              this._play(item);
            },
          },
          icon("mdi:play"),
        ),
      );
    }
    if (item.context_key) {
      tile.firstChild.append(
        el(
          "button",
          {
            class: "more",
            onclick: (event) => {
              event.stopPropagation();
              this._showActions(item);
            },
          },
          icon("mdi:dots-vertical"),
        ),
      );
    }
    return tile;
  }

  _renderNowPlaying() {
    if (!this._built) return;
    const player = this._player;
    this._footer.hidden = !player;
    if (!player) return;
    const playing = ACTIVE_STATES.includes(player.state);
    this._track.textContent = player.title || player.name;
    this._artist.textContent = [player.artist, player.album].filter(Boolean).join(" - ");
    if (imageKey(player.image) !== this._coverKey) {
      this._coverKey = imageKey(player.image);
      this._cover.replaceWith(
        (this._cover = player.image ? el("img", { class: "cover", src: player.image, alt: "" }) : el("div", { class: "cover" })),
      );
    }
    this._buttons.toggle.firstChild.setAttribute("icon", playing ? "mdi:pause" : "mdi:play");
    for (const modes of [this._queueModes, this._now.queueModes]) {
      modes.shuffle.classList.toggle("on", player.shuffle);
      modes.repeat.classList.toggle("on", player.repeat !== 2);
      modes.repeat.firstChild.setAttribute("icon", player.repeat === 1 ? "mdi:repeat-once" : "mdi:repeat");
    }
    this._buttons.mute.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    this._volButton.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    this._volButton.style.setProperty("--level", player.max_volume ? Math.round((Math.max(player.volume, 0) / player.max_volume) * 100) : 0);
    this._volButton.disabled = player.volume < 0;
    this._volume.disabled = player.volume < 0;
    this._volume.max = player.max_volume;
    this._volume.value = Math.max(player.volume, 0);
    this._buttons.next.disabled = this._buttons.previous.disabled = !player.available;
    this._progress.hidden = !(player.duration > 0);
    if (!(player.duration > 0)) this._miniFill.style.width = "0";
    this._seek.disabled = !player.can_seek;
    this._seek.max = player.duration || 0;
    this._seeking = false;
    this._tick();
  }

  _tick() {
    this._tickNow();
    const player = this._player;
    if (!this._built || !player || !(player.duration > 0) || this._seeking) return;
    let position = player.position || 0;
    if (ACTIVE_STATES.includes(player.state)) position += (Date.now() - this._receivedAt) / 1000;
    position = Math.min(position, player.duration);
    this._seek.value = position;
    this._miniFill.style.width = `${(position / player.duration) * 100}%`;
    this._showTimes(position);
  }

  // The time played and the time left of the track
  _showTimes(position) {
    const player = this._player;
    if (!player || !(player.duration > 0)) return;
    this._elapsed.textContent = formatTime(position);
    this._total.textContent = `\u2212${formatTime(player.duration - position)}`;
  }
}

if (!customElements.get("bluos-companion-panel")) customElements.define("bluos-companion-panel", BluOSCompanionPanel);
