/* BluOS Companion presets card: the presets of a player as a grid of artworks, with
 * volume, input selection, power and play / pause. Plain JavaScript, no build step. */

// The shared controls come with the version of this file, so that a changed file is not cached
const { createControls, CONTROLS_STYLE } = await import(
  new URL(`./bluos-companion-card-controls.js${new URL(import.meta.url).search}`, import.meta.url)
);

const CONTENTS = ["presets", "playlists", "favourites"];

const CARD_STYLE = CONTROLS_STYLE + `
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; }
  .grid { display: grid; gap: 8px; padding: 12px; }
  .preset {
    position: relative;
    aspect-ratio: 1;
    padding: 0;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: var(--card-background-color);
    color: var(--primary-text-color);
    cursor: pointer;
    overflow: hidden;
    font: inherit;
  }
  .preset:hover { border-color: var(--primary-color); }
  .preset.playing { border-color: var(--primary-color); box-shadow: 0 0 0 2px var(--primary-color); }
  .preset img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .preset span {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 4px;
    text-align: center;
    font-size: 13px;
    overflow-wrap: anywhere;
  }
  .message { padding: 16px; color: var(--secondary-text-color); text-align: center; }
  footer { padding: 4px 12px 12px; }
`;

const ACTIVE_STATES = ["play", "stream"];

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

class BluOSCompanionPresetsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._player = null;
    this._items = null;
    this._loadedKey = undefined;
    this._unsubscribe = null;
  }

  static getConfigElement() {
    return document.createElement("bluos-companion-presets-card-editor");
  }

  static getStubConfig(hass) {
    // A player of this integration, so that the preview of the card picker shows something
    const players = Object.keys(hass.states).filter((id) => id.startsWith("media_player."));
    const entity = players.find((id) => hass.entities?.[id]?.platform === "bluos_companion") || players[0];
    return { entity: entity || "", content: "presets", columns: 3, show_footer: true };
  }

  setConfig(config) {
    if (!config.entity) throw new Error("Choose the BluOS Companion player (entity)");
    this._config = { content: "presets", columns: 3, show_footer: true, ...config };
    if (!CONTENTS.includes(this._config.content)) throw new Error("The content must be presets, playlists or favourites");
    // What the grid shows may have changed (the editor): load it again
    this._loadedKey = undefined;
    this._items = null;
    if (this._player) this._loadItems();
    this._build();
    this._render();
  }

  getCardSize() {
    return 4;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._loadStrings().then(() => {
        this._render();
        if (this.isConnected) this._subscribe();
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

  connectedCallback() {
    this._watchSubscription();
    if (this._hass && this._strings && !this._unsubscribe) this._subscribe();
  }

  disconnectedCallback() {
    this._unwatchSubscription();
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = null;
    }
  }

  // A tablet puts a page to sleep and its connection with it, and nothing tells the page it missed
  // anything: subscribe again when the page is back (the answer is the current state) and now and then
  async _resubscribe() {
    if (!this._hass || !this.isConnected || document.hidden) return;
    const previous = this._unsubscribe;
    this._unsubscribe = null;
    try {
      await this._subscribe();
    } catch (err) {
      this._unsubscribe = previous;
      return;
    }
    if (previous) Promise.resolve().then(previous).catch(() => {});
  }

  _watchSubscription() {
    this._wake = () => this._resubscribe();
    document.addEventListener("visibilitychange", this._wake);
    window.addEventListener("pageshow", this._wake);
    window.addEventListener("online", this._wake);
    this._watchdog = setInterval(this._wake, 60000);
  }

  _unwatchSubscription() {
    document.removeEventListener("visibilitychange", this._wake);
    window.removeEventListener("pageshow", this._wake);
    window.removeEventListener("online", this._wake);
    clearInterval(this._watchdog);
  }

  async _subscribe() {
    this._unsubscribe = await this._hass.connection.subscribeMessage(
      (event) => this._onPlayers(event.players),
      { type: "bluos_companion/subscribe" },
    );
  }

  _onPlayers(players) {
    this._player = players.find((candidate) => candidate.entity_id === this._config.entity) || null;
    this._loadItems();
    this._render();
  }

  // The presets follow the player (it tells when they change); playlists and favourites are read
  // again when the card is set up differently, and every time the card is loaded.
  async _loadItems() {
    const player = this._player;
    if (!player) return;
    const { content, max_items: limit } = this._config;
    const key = content === "presets" ? `presets:${player.presets_id}` : `${content}:${limit}`;
    if (key === this._loadedKey) return;
    this._loadedKey = key;
    try {
      this._items =
        content === "presets"
          ? await this._loadPresets(player.entry_id)
          : (
              await this._hass.connection.sendMessagePromise({
                type: "bluos_companion/card_items",
                entry_id: player.entry_id,
                content,
                ...(limit ? { limit: Number(limit) } : {}),
              })
            ).items;
    } catch (err) {
      this._items = [];
    }
    // The card may have been set up differently while the player answered
    if (key === this._loadedKey) this._render();
  }

  async _loadPresets(entryId) {
    const result = await this._hass.connection.sendMessagePromise({
      type: "bluos_companion/presets",
      entry_id: entryId,
    });
    const limit = Number(this._config.max_items) || result.presets.length;
    return result.presets.slice(0, limit).map((preset) => ({
      name: preset.name,
      image: preset.image,
      path: `/Preset?id=${preset.id}`,
      url: preset.url,
    }));
  }

  _notify(message) {
    this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
  }

  _call(message) {
    return this._hass.connection.sendMessagePromise({ entry_id: this._player.entry_id, ...message }).catch((err) => {
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
    return this._call({
      type: "bluos_companion/control",
      action,
      ...(value === undefined ? {} : { value }),
    });
  }

  _build() {
    this._grid = el("div", { class: "grid" });
    this._message = el("div", { class: "message" });
    // Cards written before the options of the integration had the entities in their own settings
    this._hint = el("div", { class: "message" });
    this._toggle = el(
      "button",
      {
        class: "ctl",
        onclick: () => this._control(ACTIVE_STATES.includes(this._player.state) ? "pause" : "play"),
      },
      icon("mdi:play"),
    );
    this._controls = createControls(this, [this._toggle]);
    this._footer = el("footer", {}, this._controls.row, this._controls.dialog);
    this.shadowRoot.replaceChildren(
      el("style", {}, CARD_STYLE),
      el("ha-card", {}, this._hint, this._grid, this._message, this._footer),
    );
  }

  _render() {
    if (!this._grid) return;
    const player = this._player;
    this._grid.style.gridTemplateColumns = `repeat(${Math.max(1, Number(this._config.columns) || 3)}, 1fr)`;
    this._grid.replaceChildren(
      ...(player && this._items ? this._items.map((item) => this._tile(item)) : []),
    );
    this._grid.hidden = !this._grid.childNodes.length;
    this._message.textContent = !player
      ? this._t("card_not_found")
      : this._items && !this._items.length
        ? this._t(`no_${this._config.content}`)
        : "";
    this._message.hidden = !this._message.textContent;
    this._hint.textContent = this._config.other_entities ? this._t("card_other_entities_moved") : "";
    this._hint.hidden = !this._hint.textContent;

    this._renderFooter();
  }

  _renderFooter() {
    const player = this._player;
    if (!player) {
      this._footer.hidden = true;
      return;
    }
    this._toggle.hidden = this._config.show_playback === false;
    this._toggle.firstChild.setAttribute("icon", ACTIVE_STATES.includes(player.state) ? "mdi:pause" : "mdi:play");
    const visible = this._controls.update();
    this._footer.hidden = this._config.show_footer === false || !visible;
  }

  // The stream URL of a station is the URL of its preset (or its start); the name is the
  // fallback for services whose URLs differ.
  _isPlaying(preset) {
    const player = this._player;
    if (!player || player.state === "stop") return false;
    const stream = player.stream_url;
    if (stream && preset.url && (preset.url === stream || preset.url.startsWith(`${stream}/`))) return true;
    return Boolean(player.preset_name) && preset.name === player.preset_name;
  }

  _tile(item) {
    const label = item.subtitle ? `${item.name} - ${item.subtitle}` : item.name;
    return el(
      "button",
      {
        class: this._config.content === "presets" && this._isPlaying(item) ? "preset playing" : "preset",
        title: label,
        "aria-label": label,
        onclick: () => this._call({ type: "bluos_companion/play", path: item.path }),
      },
      item.image
        ? el("img", { src: item.image, alt: item.name, loading: "lazy" })
        : el("span", {}, item.name),
    );
  }
}

class BluOSCompanionPresetsCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    if (first) this._loadStrings().then(() => this._render());
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

  _schema() {
    return [
      { name: "entity", required: true, selector: { entity: { domain: "media_player", integration: "bluos_companion" } } },
      {
        name: "content",
        selector: {
          select: {
            mode: "dropdown",
            options: CONTENTS.map((value) => ({ value, label: this._t(`editor_content_${value}`) })),
          },
        },
      },
      { name: "max_items", selector: { number: { min: 1, max: 200, mode: "box" } } },
      { name: "columns", selector: { number: { min: 1, max: 8, mode: "box" } } },
      { name: "show_footer", selector: { boolean: {} } },
      { name: "show_volume", selector: { boolean: {} } },
      { name: "show_playback", selector: { boolean: {} } },
      { name: "show_input", selector: { boolean: {} } },
      { name: "show_power", selector: { boolean: {} } },
    ];
  }

  _render() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (event) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: event.detail.value }, bubbles: true, composed: true }),
        );
      });
      this.append(this._form);
    }
    const labels = {
      entity: "editor_player",
      content: "editor_content",
      max_items: "editor_max_items",
      columns: "editor_columns",
      show_footer: "editor_show_footer",
      show_volume: "editor_show_volume",
      show_playback: "editor_show_playback",
      show_input: "editor_show_input",
      show_power: "editor_show_power",
    };
    this._form.computeLabel = (schema) => this._t(labels[schema.name] || schema.name);
    this._form.schema = this._schema();
    this._form.hass = this._hass;
    this._form.data = {
      content: "presets",
      columns: 3,
      show_footer: true,
      show_volume: true,
      show_playback: true,
      show_input: true,
      show_power: false,
      ...this._config,
    };
  }
}

if (!customElements.get("bluos-companion-presets-card")) customElements.define("bluos-companion-presets-card", BluOSCompanionPresetsCard);
if (!customElements.get("bluos-companion-presets-card-editor")) customElements.define("bluos-companion-presets-card-editor", BluOSCompanionPresetsCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "bluos-companion-presets-card",
  name: "BluOS Companion grid",
  description: "The presets, playlists or favourites of a BluOS player as a grid of covers, with input selection and volume.",
  preview: true,
});
