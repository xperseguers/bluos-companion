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
      this._build();
      this._subscribe();
    }
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
    await this._call({ type: "bluos_companion/play", entry_id: this._playerId, path: action.path });
    this._notify(`${action.title}: ${label}`);
  }

  _showPlaying() {
    const player = this._player;
    if (!player || !player.title) return;
    if (player.service !== "LocalMusic") {
      this._notify("Only tracks of the library have an album and an artist page");
      return;
    }
    this._showGoTo(player.title, [player.artist, player.album].filter(Boolean).join(" - "), {
      album: player.album,
      artist: player.artist,
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
        this._notify("Album not found in the library");
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
    const button = (kind, iconName, label, name) =>
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
        `${label}: ${name}`,
      );
    return [
      names.album ? button("album", "mdi:album", "Album", names.album) : null,
      names.artist ? button("artist", "mdi:account-music", "Artist", names.artist) : null,
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
    this._dialog.replaceChildren(
      el("h2", {}, title),
      el("p", {}, subtitle || "\u00a0"),
      el("div", { class: "list" }, ...this._gotoButtons(names), ...extra),
    );
    this._dialog.showModal();
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
      icon(ACTION_ICONS[action.type] || "mdi:playlist-plus"),
      action.title,
    );
  }

  async _showActions(item) {
    const actions = await this._actions(item.context_key);
    // Songs read "Artist \u2022 Album": offer to jump to them.
    const [artist, album] = item.type === "track" ? (item.subtitle || "").split(" \u2022 ") : [];
    const names = artist && album ? { artist, album } : {};
    if (!actions.length && !names.album) {
      this._notify("No action available");
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
    this._renderBrowse();
    const level = this._stack[this._stack.length - 1];
    this._levelActions = [];
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
    } else {
      const result = await this._call({
        type: "bluos_companion/browse",
        entry_id: player.entry_id,
        ...(level && level.key ? { key: level.key } : {}),
      });
      if (result && (result.search_key || !level)) {
        this._searchKey = result.search_key || DEFAULT_SEARCH_KEY;
      }
      groups = [{ title: null, items: result ? result.items : [] }];
    }
    if (token !== this._browseToken) return;
    this._groups = groups;
    this._renderBrowse();
    this._main.scrollTop = 0;
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
    this._stack.push({ title: "Queue", queue: true });
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
      el("h2", {}, "Clear the queue?"),
      el("p", {}, "All the tracks are removed from the queue."),
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
          "Clear",
        ),
      ),
    );
    this._dialog.showModal();
  }

  _askSaveName() {
    const input = el("input", { type: "text", placeholder: "Playlist name", maxlength: 100 });
    const save = async () => {
      const name = input.value.trim();
      if (!name) return;
      this._dialog.close();
      await this._call({ type: "bluos_companion/queue_action", entry_id: this._playerId, action: "save", name });
      this._notify(`Saved: ${name}`);
    };
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") save();
    });
    this._dialog.replaceChildren(
      el("h2", {}, "Save the queue as a playlist"),
      input,
      el("div", { class: "list" }, el("button", { class: "action", onclick: save }, icon("mdi:content-save"), "Save")),
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
      item.position > 0 ? this._menuButton("mdi:chevron-up", "Move up", () => move(item.position - 1)) : null,
      index < count - 1 ? this._menuButton("mdi:chevron-down", "Move down", () => move(item.position + 1)) : null,
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
    this._message.textContent = this._queue && !this._queue.length ? "The queue is empty." : "";
    this._actionRow.replaceChildren(
      el("button", { class: "action", onclick: () => this._confirmClear() }, icon("mdi:delete-sweep"), "Clear"),
      el("button", { class: "action", onclick: () => this._askSaveName() }, icon("mdi:content-save"), "Save as playlist"),
    );
    this._actionRow.hidden = !(this._queue && this._queue.length);
  }

  _open(item) {
    this._stack.push({ title: item.title, key: item.browse_key, contextKey: item.context_key });
    this._browse();
  }

  _up() {
    this._stack.pop();
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
    this._searchInput = el("input", { type: "search", placeholder: "Search", enterkeyhint: "search" });
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
    this._dialogMode = null;
    this._dialog = el("dialog", {
      onclose: () => {
        this._dialogMode = null;
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
      ),
      el("div", { class: "volume" }, this._buttons.mute, this._volume),
      this._playerButton,
      this._progress,
    );
    this._footer = footer;

    this.shadowRoot.append(
      el("style", {}, STYLE),
      el("header", {}, this._menuButton, el("h1", {}, "BluOS Companion")),
      this._main,
      footer,
      this._dialog,
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
    this._playerName.textContent = player ? player.name : "";
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

  _groupLabel(player) {
    const name = (id) => (this._players.find((other) => other.entry_id === id) || {}).name;
    if (player.group.master) return `Grouped with ${name(player.group.master) || "another player"}`;
    const slaves = player.group.slaves.map(name).filter(Boolean);
    return slaves.length ? `Group: ${[player.name, ...slaves].join(" + ")}` : "";
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

  _showGroup() {
    this._dialogMode = "group";
    this._renderGroup();
    if (!this._dialog.open) this._dialog.showModal();
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
      const slider = el("input", {
        type: "range",
        min: 0,
        max: player.max_volume,
        value: Math.max(player.volume, 0),
        onchange: (event) => this._control("volume", Number(event.target.value), player.entry_id),
      });
      slider.disabled = player.volume < 0;
      return el("div", { class: "group-row" }, line, el("div", { class: "line" }, icon("mdi:volume-medium"), slider));
    };
    const rows = [el("h2", {}, "Group players"), el("p", {}, "Players that play the same music together.")];
    rows.push(el("div", { class: "list" }, ...this._players.map(row)));
    if (members.length > 1 && primary) {
      const step = (delta) => this._control("volume_step", delta, primary.entry_id, { group: true });
      rows.push(
        el(
          "div",
          { class: "group-volume" },
          el("span", { class: "label" }, "Group volume"),
          el("button", { onclick: () => this._control("mute", !primary.muted, primary.entry_id, { group: true }) }, icon("mdi:volume-off")),
          el("button", { onclick: () => step(-2) }, icon("mdi:minus")),
          el("button", { onclick: () => step(2) }, icon("mdi:plus")),
        ),
      );
    }
    rows.push(
      el(
        "div",
        { class: "list", style: "margin-top: 12px" },
        el("button", { class: "action", onclick: () => this._showPlayers() }, icon("mdi:arrow-left"), "Back"),
      ),
    );
    this._dialog.replaceChildren(...rows);
  }

  _renderPlayerList() {
    this._dialog.replaceChildren(
      el("h2", {}, "Play on"),
      el(
        "div",
        { class: "list" },
        ...this._players.map((player) => {
          const playing = ACTIVE_STATES.includes(player.state);
          const what = player.available
            ? [player.title, player.artist].filter(Boolean).join(" - ")
            : "Unavailable";
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
      this._players.length > 1
        ? el(
            "div",
            { class: "list", style: "margin-top: 12px" },
            el("button", { class: "action", onclick: () => this._showGroup() }, icon("mdi:speaker-multiple"), "Group players"),
          )
        : null,
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
      this._message.textContent = "No BluOS player configured.";
    } else if (this._groups === null) {
      this._message.textContent = "\u2026";
    } else if (!this._groups.some((group) => group.items.length)) {
      this._message.textContent = "Nothing here.";
    } else {
      for (const group of this._groups) {
        if (!group.items.length) continue;
        if (group.title) this._grid.append(el("h3", {}, group.title));
        this._grid.append(el("div", { class: "grid" }, ...group.items.map((item) => this._tile(item))));
      }
    }
  }

  _renderCrumbs() {
    const level = this._stack[this._stack.length - 1];
    this._crumbs.replaceChildren(
      ...(level
        ? [
            el("button", { onclick: () => this._up() }, icon("mdi:arrow-left")),
            el("h2", {}, level.title),
          ]
        : []),
    );
    if (level && level.queue) return;
    this._actionRow.replaceChildren(
      ...this._levelActions.map((action) => this._actionButton(action, level.title)),
    );
    this._actionRow.hidden = !this._levelActions.length;
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
    this._progress.hidden = !(player.duration > 0);
    this._seek.disabled = !player.can_seek;
    this._seek.max = player.duration || 0;
    this._seeking = false;
    this._tick();
  }

  _tick() {
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
