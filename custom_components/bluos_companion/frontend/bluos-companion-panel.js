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
  header h1 { font-size: 20px; font-weight: 400; margin: 0; flex: 1; }
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
    padding: 12px 24px 24px;
    background: var(--primary-background-color);
  }
  dialog.now[open] { display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .now .top { align-self: stretch; display: flex; align-items: center; gap: 8px; }
  .now .top span { flex: 1; text-align: center; color: var(--secondary-text-color); }
  .now .art {
    flex: 1;
    min-height: 0;
    max-width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 12px;
    background: var(--secondary-background-color);
  }
  .now .title { font-size: 24px; font-weight: 500; text-align: center; }
  .now .sub { color: var(--secondary-text-color); text-align: center; }
  .now .line { align-self: stretch; display: flex; align-items: center; justify-content: center; gap: 8px; max-width: 640px; width: 100%; margin: 0 auto; }
  .now .line input[type="range"] { flex: 1; min-width: 0; }
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
  .crumbs { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
  .tile { scroll-margin-top: 72px; }
  .azbar {
    position: sticky;
    top: -16px;
    z-index: 2;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 0;
    margin-bottom: 8px;
    background: var(--primary-background-color);
  }
  .chip {
    border: 1px solid var(--divider-color);
    border-radius: 20px;
    min-width: 40px;
    height: 40px;
    padding: 0 10px;
    font: inherit;
    background: var(--card-background-color);
    color: var(--primary-text-color);
  }
  .chip.current {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
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
  .volume { display: flex; align-items: center; gap: 4px; }
  input[type="range"] { accent-color: var(--primary-color); }
  @media (max-width: 600px) {
    .volume input { width: 90px; }
  }
`;

const REPEAT_CYCLE = { 2: 0, 0: 1, 1: 2 }; // off -> queue -> track -> off
const ACTIVE_STATES = ["play", "stream"];
const INITIALS_FROM = 40; // a list this long gets a bar of first letters
const STORAGE_KEY = "bluos_companion_player";
const DEFAULT_SEARCH_KEY = "LocalMusic:Search"; // the library, used at the root

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
  }

  disconnectedCallback() {
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
    const list = this._showGoTo(player.title, [player.artist, player.album].filter(Boolean).join(" - "), {
      album: player.album,
      artist: player.artist,
    });
    // Whether the track is a favourite takes a request: the button comes when it is known
    this._call({ type: "bluos_companion/playing_favourite", entry_id: this._playerId }).then((result) => {
      if (!result || !this._dialog.open) return;
      list.append(
        this._actionButton({ favourite: result.favourite, on: result.on }, player.title, () => this._dialog.close()),
      );
    });
  }

  async _jump(kind, names) {
    const found = await this._call({
      type: "bluos_companion/locate",
      entry_id: this._playerId,
      ...(names.album ? { album: names.album } : {}),
      ...(names.artist ? { artist: names.artist } : {}),
    });
    if (!found) return;
    const level = (page) => ({ title: page.title, key: page.browse_key, contextKey: page.context_key });
    const stack = found.artist ? [level(found.artist)] : [];
    if (kind === "album") {
      if (!found.album) {
        this._notify(this._t("album_not_found"));
        return;
      }
      stack.push(level(found.album));
    } else if (!found.artist) {
      return;
    }
    this._stack = stack;
    this._browse();
  }

  _gotoButtons(names) {
    const button = (kind, iconName, label) =>
      el(
        "button",
        {
          class: "action",
          onclick: () => {
            this._dialog.close();
            this._jump(kind, names);
          },
        },
        icon(iconName),
        label,
      );
    return [
      names.album ? button("album", "mdi:album", this._t("album_label", { name: names.album })) : null,
      names.artist ? button("artist", "mdi:account-music", this._t("artist_label", { name: names.artist })) : null,
    ].filter(Boolean);
  }

  _menuButton(iconName, label, run) {
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

  _showGoTo(title, subtitle, names, extra = []) {
    const list = el("div", { class: "list" }, ...this._gotoButtons(names), ...extra);
    this._dialog.replaceChildren(el("h2", {}, title), el("p", {}, subtitle || "\u00a0"), list);
    this._dialog.showModal();
    return list;
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
    const actions = await this._actions(item.context_key);
    // Songs read "Artist \u2022 Album": offer to jump to them.
    const [artist, album] = item.type === "track" ? (item.subtitle || "").split(" \u2022 ") : [];
    const names = artist && album ? { artist, album } : {};
    if (!actions.length && !names.album) {
      this._notify(this._t("no_action"));
      return;
    }
    this._dialog.replaceChildren(
      el("h2", {}, item.title),
      el("p", {}, item.subtitle || "\u00a0"),
      el(
        "div",
        { class: "list" },
        ...this._gotoButtons(names),
        ...actions.map((action) => this._actionButton(action, item.title, () => this._dialog.close())),
      ),
    );
    this._dialog.showModal();
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
    this._renderBrowse();
    this._main.scrollTop = 0;
    this._loadPlaylistCovers();
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
    if (this._inQueue && player && `${player.queue_id}/${player.queue_position}` !== this._queueKey) {
      this._loadQueue();
    }
  }

  async _queueAction(action, extra = {}) {
    await this._call({ type: "bluos_companion/queue_action", entry_id: this._playerId, action, ...extra });
    await this._loadQueue();
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
      item.position > 0 ? this._menuButton("mdi:chevron-up", this._t("move_up"), () => move(item.position - 1)) : null,
      index < count - 1 ? this._menuButton("mdi:chevron-down", this._t("move_down"), () => move(item.position + 1)) : null,
    ].filter(Boolean);
    const more = el(
      "button",
      {
        onclick: stop(() =>
          this._showGoTo(item.title, [item.artist, item.album].filter(Boolean).join(" - "), item, moves),
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

  _renderQueue() {
    const player = this._player;
    const current = player ? player.queue_position : null;
    this._grid.replaceChildren(
      ...(this._queue || []).map((item, index) => this._queueRow(item, index, this._queue.length, current)),
    );
    this._message.textContent = this._queue && !this._queue.length ? this._t("queue_empty") : "";
    this._actionRow.replaceChildren(
      el("button", { class: "action", onclick: () => this._confirmClear() }, icon("mdi:delete-sweep"), this._t("clear")),
      el("button", { class: "action", onclick: () => this._askSaveName() }, icon("mdi:content-save"), this._t("save_as_playlist")),
    );
    this._actionRow.hidden = !(this._queue && this._queue.length);
  }

  // The letters (sections) of a long list: shown as a bar, kept above the entries of a letter.
  _sectionBar() {
    const level = this._stack[this._stack.length - 1];
    if (level && level.bar) return level.bar;
    const items = this._groups && this._groups.length === 1 ? this._groups[0].items : [];
    return items.length && items.every((item) => item.type === "section") ? items : null;
  }

  _open(item) {
    if (item.type === "section") {
      const bar = this._sectionBar();
      const top = this._stack[this._stack.length - 1];
      const base = top && top.bar ? top.base : top ? top.title : "";
      const level = { title: base ? `${base} \u00b7 ${item.title}` : item.title, base, key: item.browse_key, bar, letter: item.title };
      // Jumping from a letter to another one replaces it, so that back leaves the list.
      if (top && top.bar) this._stack[this._stack.length - 1] = level;
      else this._stack.push(level);
    } else {
      this._stack.push({ title: item.title, key: item.browse_key, contextKey: item.context_key, image: item.image });
    }
    this._browse();
  }

  _renderInitials(items) {
    const initial = (item) => {
      const letter = item.title.normalize("NFD").replace(/[\u0300-\u036f]/g, "").charAt(0).toUpperCase();
      return /[A-Z]/.test(letter) ? letter : "#";
    };
    const letters = [...new Set(items.map(initial))].sort((a, b) => (a === "#" ? -1 : b === "#" ? 1 : a < b ? -1 : 1));
    return el(
      "div",
      { class: "azbar" },
      ...letters.map((letter) =>
        el(
          "button",
          {
            class: "chip",
            onclick: () => {
              const index = items.findIndex((item) => initial(item) === letter);
              const tile = this._grid.querySelectorAll(".tile")[index];
              if (tile) tile.scrollIntoView({ block: "start", behavior: "smooth" });
            },
          },
          letter,
        ),
      ),
    );
  }

  _renderBar(bar, current) {
    return el(
      "div",
      { class: "azbar" },
      ...bar.map((item) =>
        el(
          "button",
          {
            class: item.title === current ? "chip current" : "chip",
            title: item.subtitle ? `${item.title} (${item.subtitle})` : item.title,
            onclick: () => this._open(item),
          },
          item.title,
        ),
      ),
    );
  }

  _up() {
    this._stack.pop();
    this._browse();
  }

  _home() {
    this._stack = [];
    this._browse();
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

    this._cover = el("div", { class: "cover" });
    this._track = el("div", { class: "track" });
    this._artist = el("div", { class: "artist" });
    this._buttons = {
      shuffle: el("button", { onclick: () => this._control("shuffle", !this._player.shuffle) }, icon("mdi:shuffle")),
      previous: el("button", { onclick: () => this._control("previous") }, icon("mdi:skip-previous")),
      toggle: el("button", { onclick: () => this._togglePlayback() }, icon("mdi:play")),
      next: el("button", { onclick: () => this._control("next") }, icon("mdi:skip-next")),
      queue: el("button", { onclick: () => this._toggleQueue() }, icon("mdi:playlist-music")),
      expand: el("button", { onclick: () => this._showNow() }, icon("mdi:fullscreen")),
      move: el("button", { title: this._t("move_playback"), onclick: () => this._showMove() }, icon("mdi:transfer-right")),
      repeat: el("button", { onclick: () => this._control("repeat", REPEAT_CYCLE[this._player.repeat]) }, icon("mdi:repeat")),
      mute: el("button", { onclick: () => this._control("mute", !this._player.muted) }, icon("mdi:volume-high")),
    };
    this._volume = el("input", {
      type: "range",
      min: 0,
      max: 100,
      onchange: (event) => this._control("volume", Number(event.target.value)),
    });
    this._seek = el("input", {
      type: "range",
      min: 0,
      max: 0,
      step: 1,
      value: 0,
      onchange: (event) => this._control("seek", Number(event.target.value)),
      oninput: () => {
        this._seeking = true;
      },
    });
    this._elapsed = el("span");
    this._total = el("span");
    this._progress = el("div", { class: "progress" }, this._elapsed, this._seek, this._total);

    const footer = el(
      "footer",
      {},
      this._cover,
      el("div", { class: "info", onclick: () => this._showPlaying() }, this._track, this._artist),
      el(
        "div",
        { class: "controls" },
        this._buttons.shuffle,
        this._buttons.previous,
        this._buttons.toggle,
        this._buttons.next,
        this._buttons.repeat,
        this._buttons.queue,
        this._buttons.expand,
        this._buttons.move,
      ),
      el("div", { class: "volume" }, this._buttons.mute, this._volume),
      this._playerButton,
      this._progress,
    );
    this._footer = footer;

    this.shadowRoot.append(
      el("style", {}, STYLE),
      el("header", {}, this._menuButton, el("h1", {}, this._t("title"))),
      this._main,
      footer,
      this._dialog,
      this._nowDialog,
    );
    this._built = true;
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
    now.elapsed = el("span");
    now.total = el("span");
    now.seek = el("input", {
      type: "range",
      min: 0,
      max: 0,
      step: 1,
      value: 0,
      onchange: (event) => this._control("seek", Number(event.target.value)),
      oninput: () => {
        this._nowSeeking = true;
      },
    });
    now.progress = el("div", { class: "line" }, now.elapsed, now.seek, now.total);
    const control = (name, iconName, run, big) =>
      (now[name] = el("button", { class: big ? "big" : "", onclick: run }, icon(iconName)));
    now.controls = el(
      "div",
      { class: "line" },
      control("shuffle", "mdi:shuffle", () => this._control("shuffle", !this._player.shuffle)),
      control("previous", "mdi:skip-previous", () => this._control("previous"), true),
      control("toggle", "mdi:play", () => this._togglePlayback(), true),
      control("next", "mdi:skip-next", () => this._control("next"), true),
      control("repeat", "mdi:repeat", () => this._control("repeat", REPEAT_CYCLE[this._player.repeat])),
    );
    now.mute = el("button", { onclick: () => this._control("mute", !this._player.muted) }, icon("mdi:volume-high"));
    now.volume = el("input", {
      type: "range",
      min: 0,
      max: 100,
      onchange: (event) => this._control("volume", Number(event.target.value)),
    });
    now.volumeRow = el("div", { class: "line" }, now.mute, now.volume);
    now.source = el("select", { onchange: (event) => this._control("source", event.target.value) });
    now.sleep = el("select", { onchange: (event) => this._control("sleep", Number(event.target.value)) });
    now.settings = el(
      "div",
      { class: "line" },
      icon("mdi:import"),
      now.source,
      icon("mdi:sleep"),
      now.sleep,
    );
    this._nowDialog = el(
      "dialog",
      { class: "now", onclose: () => (this._nowOpen = false) },
      el(
        "div",
        { class: "top" },
        el("button", { onclick: () => this._nowDialog.close() }, icon("mdi:close")),
        now.player,
        (now.move = el(
          "button",
          {
            onclick: () => {
              this._nowDialog.close();
              this._showMove();
            },
          },
          icon("mdi:transfer-right"),
        )),
      ),
      now.art,
      now.title,
      now.sub,
      now.progress,
      now.controls,
      now.volumeRow,
      now.settings,
    );
  }

  _showNow() {
    if (!this._player) return;
    this._nowOpen = true;
    this._renderNow();
    if (!this._nowDialog.open) this._nowDialog.showModal();
  }

  _renderNow() {
    const player = this._player;
    const now = this._now;
    if (!this._nowOpen || !player) return;
    const playing = ACTIVE_STATES.includes(player.state);
    now.player.textContent = this._groupName(player) || player.name;
    now.move.hidden = !this._canMove(player);
    now.title.textContent = player.title || player.name;
    now.sub.textContent = [player.artist, player.album].filter(Boolean).join(" - ");
    if (player.image) {
      now.art.replaceWith((now.art = el("img", { class: "art", src: player.image, alt: "" })));
    } else if (now.art.tagName === "IMG") {
      now.art.replaceWith((now.art = el("div", { class: "art" })));
    }
    now.toggle.firstChild.setAttribute("icon", playing ? "mdi:pause" : "mdi:play");
    now.shuffle.classList.toggle("on", player.shuffle);
    now.repeat.classList.toggle("on", player.repeat !== 2);
    now.repeat.firstChild.setAttribute("icon", player.repeat === 1 ? "mdi:repeat-once" : "mdi:repeat");
    now.mute.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    now.volume.disabled = player.volume < 0;
    now.volume.max = player.max_volume;
    now.volume.value = Math.max(player.volume, 0);
    now.progress.hidden = !(player.duration > 0);
    now.seek.disabled = !player.can_seek;
    now.seek.max = player.duration || 0;
    this._nowSeeking = false;
    if (document.activeElement !== now.source && this.shadowRoot.activeElement !== now.source) {
      now.source.replaceChildren(
        el("option", { value: "" }, this._t("input")),
        ...player.sources.map((name) => {
          const option = el("option", { value: name }, name);
          option.selected = name === player.source;
          return option;
        }),
      );
      now.source.firstChild.disabled = true;
      now.source.value = player.source || "";
    }
    now.source.hidden = !player.sources.length;
    now.sleep.replaceChildren(
      ...[0, ...player.sleep_options].map((minutes) => {
        const option = el("option", { value: minutes }, minutes ? this._t("minutes", { minutes }) : this._t("sleep_off"));
        option.selected = minutes === player.sleep;
        return option;
      }),
    );
    this._tickNow();
  }

  _tickNow() {
    const player = this._player;
    const now = this._now;
    if (!this._nowOpen || !player || !(player.duration > 0) || this._nowSeeking) return;
    let position = player.position || 0;
    if (ACTIVE_STATES.includes(player.state)) position += (Date.now() - this._receivedAt) / 1000;
    position = Math.min(position, player.duration);
    now.seek.value = position;
    now.elapsed.textContent = formatTime(position);
    now.total.textContent = formatTime(player.duration);
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

  _renderBrowse() {
    if (!this._built) return;
    this._renderCrumbs();
    this._buttons.queue.classList.toggle("on", this._inQueue);
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
      const bar = this._sectionBar();
      const level = this._stack[this._stack.length - 1];
      if (bar) this._grid.append(this._renderBar(bar, level && level.letter));
      else if (
        this._groups.length === 1 &&
        this._groups[0].items.length >= INITIALS_FROM &&
        this._groups[0].items.every((item) => item.type !== "track")
      ) {
        // A long list the player gives without letters (not tracks, they are in playing order).
        this._grid.append(this._renderInitials(this._groups[0].items));
      }
      for (const group of this._groups) {
        if (!group.items.length) continue;
        if (bar && !level.bar) continue; // the letters are the bar, not tiles
        if (group.title) this._grid.append(el("h3", {}, group.title));
        this._grid.append(el("div", { class: "grid" }, ...group.items.map((item) => this._tile(item))));
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
            level.image && !level.image.includes("/bluos_companion/icons/")
              ? el("img", { class: "crumb-cover", src: level.image, alt: "" })
              : null,
            el("h2", {}, level.title),
          ].filter(Boolean)
        : []),
    );
    if (level && level.queue) return;
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
    if (player.image) {
      this._cover.replaceWith((this._cover = el("img", { class: "cover", src: player.image, alt: "" })));
    } else if (this._cover.tagName === "IMG") {
      this._cover.replaceWith((this._cover = el("div", { class: "cover" })));
    }
    this._buttons.toggle.firstChild.setAttribute("icon", playing ? "mdi:pause" : "mdi:play");
    this._buttons.shuffle.classList.toggle("on", player.shuffle);
    this._buttons.repeat.classList.toggle("on", player.repeat !== 2);
    this._buttons.repeat.firstChild.setAttribute("icon", player.repeat === 1 ? "mdi:repeat-once" : "mdi:repeat");
    this._buttons.mute.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    this._volume.disabled = player.volume < 0;
    this._volume.max = player.max_volume;
    this._volume.value = Math.max(player.volume, 0);
    this._buttons.next.disabled = this._buttons.previous.disabled = !player.available;
    this._buttons.move.hidden = !this._canMove(player);
    this._progress.hidden = !(player.duration > 0);
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
    this._elapsed.textContent = formatTime(position);
    this._total.textContent = formatTime(player.duration);
  }
}

if (!customElements.get("bluos-companion-panel")) customElements.define("bluos-companion-panel", BluOSCompanionPanel);
