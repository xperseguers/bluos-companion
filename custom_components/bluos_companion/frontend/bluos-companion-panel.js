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
  select {
    font: inherit;
    padding: 6px 8px;
    border-radius: 8px;
    max-width: 50vw;
  }
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
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tile .subtitle { font-size: 12px; color: var(--secondary-text-color); }
  .tile .play {
    position: absolute;
    right: 14px;
    top: 14px;
    background: rgba(0, 0, 0, 0.6);
    color: #fff;
    --mdc-icon-size: 24px;
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
  .info { flex: 1 1 160px; min-width: 0; }
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
  }

  _call(message) {
    return this._hass.connection.sendMessagePromise(message).catch((err) => {
      this.dispatchEvent(
        new CustomEvent("hass-notification", {
          detail: { message: err.message || String(err) },
          bubbles: true,
          composed: true,
        }),
      );
    });
  }

  _control(action, value) {
    const player = this._player;
    if (!player) return;
    return this._call({
      type: "bluos_companion/control",
      entry_id: player.entry_id,
      action,
      ...(value === undefined ? {} : { value }),
    });
  }

  async _browse() {
    const player = this._player;
    if (!player) return;
    const token = ++this._browseToken;
    this._groups = null;
    this._renderBrowse();
    const level = this._stack[this._stack.length - 1];
    let groups;
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

  _open(item) {
    this._stack.push({ title: item.title, key: item.browse_key });
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
    this._select = el("select", {
      onchange: (event) => {
        this._playerId = event.target.value;
        localStorage.setItem(STORAGE_KEY, this._playerId);
        this._stack = [];
        this._browse();
        this._renderNowPlaying();
      },
    });
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
    this._grid = el("div");
    this._message = el("div", { class: "message" });
    this._main = el("main", {}, this._searchForm, this._crumbs, this._grid, this._message);

    this._cover = el("div", { class: "cover" });
    this._track = el("div", { class: "track" });
    this._artist = el("div", { class: "artist" });
    this._buttons = {
      shuffle: el("button", { onclick: () => this._control("shuffle", !this._player.shuffle) }, icon("mdi:shuffle")),
      previous: el("button", { onclick: () => this._control("previous") }, icon("mdi:skip-previous")),
      toggle: el("button", { onclick: () => this._togglePlayback() }, icon("mdi:play")),
      next: el("button", { onclick: () => this._control("next") }, icon("mdi:skip-next")),
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
      el("div", { class: "info" }, this._track, this._artist),
      el(
        "div",
        { class: "controls" },
        this._buttons.shuffle,
        this._buttons.previous,
        this._buttons.toggle,
        this._buttons.next,
        this._buttons.repeat,
      ),
      el("div", { class: "volume" }, this._buttons.mute, this._volume),
      this._progress,
    );
    this._footer = footer;

    this.shadowRoot.append(
      el("style", {}, STYLE),
      el("header", {}, this._menuButton, el("h1", {}, "BluOS Companion"), this._select),
      this._main,
      footer,
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
    this._select.replaceChildren(
      ...this._players.map((player) => {
        const option = el("option", { value: player.entry_id }, player.name);
        option.selected = player.entry_id === this._playerId;
        return option;
      }),
    );
    this._select.hidden = this._players.length < 2;
  }

  _renderBrowse() {
    if (!this._built) return;
    const crumbs = [];
    if (this._stack.length) {
      crumbs.push(
        el("button", { onclick: () => this._up() }, icon("mdi:arrow-left")),
        el("h2", {}, this._stack[this._stack.length - 1].title),
      );
    }
    this._crumbs.replaceChildren(...crumbs);
    this._grid.replaceChildren();
    this._message.textContent = "";
    this._searchForm.hidden = !this._player;
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

  _tile(item) {
    const own = item.image && item.image.includes("/bluos_companion/icons/");
    const art = item.image
      ? el("img", { class: own ? "art icon" : item.type === "link" ? "art logo" : "art", src: item.image, loading: "lazy", alt: "" })
      : el("div", { class: "art empty" }, icon("mdi:music"));
    const tile = el(
      "div",
      { class: "tile", onclick: () => (item.browse_key ? this._open(item) : this._play(item)) },
      art,
      el(
        "div",
        { class: "text" },
        el("div", { class: "title", title: item.title }, item.title),
        el("div", { class: "subtitle" }, item.subtitle || " "),
      ),
    );
    if (item.browse_key && item.play_path) {
      tile.append(
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

customElements.define("bluos-companion-panel", BluOSCompanionPanel);
