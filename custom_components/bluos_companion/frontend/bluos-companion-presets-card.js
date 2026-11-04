/* BluOS Companion presets card: the presets of a player as a grid of artworks, with
 * volume, input selection, power and play / pause. Plain JavaScript, no build step. */

// The shared controls come with the version of this file, so that a changed file is not cached
const { createControls, CONTROLS_STYLE } = await import(
  new URL(`./bluos-companion-card-controls.js${new URL(import.meta.url).search}`, import.meta.url)
);

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
    this._presets = null;
    this._presetsId = undefined;
    this._unsubscribe = null;
  }

  static getConfigElement() {
    return document.createElement("bluos-companion-presets-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find((id) => id.startsWith("media_player."));
    return { entity: entity || "", columns: 3, show_footer: true };
  }

  setConfig(config) {
    if (!config.entity) throw new Error("Choose the BluOS Companion player (entity)");
    this._config = { columns: 3, show_footer: true, ...config };
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
    } else if (this._controls && this._usesOtherEntities()) {
      this._renderFooter();
    }
  }

  // The volume, the input or the power can be those of another entity: follow its states
  _usesOtherEntities() {
    const { volume_entity: volume, source_entity: source, power_entity: power } = this._config.other_entities || {};
    return Boolean(volume || source || power);
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
    if (this._hass && this._strings && !this._unsubscribe) this._subscribe();
  }

  disconnectedCallback() {
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = null;
    }
  }

  async _subscribe() {
    this._unsubscribe = await this._hass.connection.subscribeMessage(
      (event) => this._onPlayers(event.players),
      { type: "bluos_companion/subscribe" },
    );
  }

  _onPlayers(players) {
    const player = players.find((candidate) => candidate.entity_id === this._config.entity) || null;
    this._player = player;
    if (player && player.presets_id !== this._presetsId) {
      this._presetsId = player.presets_id;
      this._loadPresets(player.entry_id);
    }
    this._render();
  }

  async _loadPresets(entryId) {
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "bluos_companion/presets",
        entry_id: entryId,
      });
      this._presets = result.presets;
    } catch (err) {
      this._presets = [];
    }
    this._render();
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
      el("ha-card", {}, this._grid, this._message, this._footer),
    );
  }

  _render() {
    if (!this._grid) return;
    const player = this._player;
    this._grid.style.gridTemplateColumns = `repeat(${Math.max(1, Number(this._config.columns) || 3)}, 1fr)`;
    this._grid.replaceChildren(
      ...(player && this._presets ? this._presets.map((preset) => this._tile(preset)) : []),
    );
    this._grid.hidden = !this._grid.childNodes.length;
    this._message.textContent = !player
      ? this._t("card_not_found")
      : this._presets && !this._presets.length
        ? this._t("no_presets")
        : "";
    this._message.hidden = !this._message.textContent;

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

  _tile(preset) {
    return el(
      "button",
      {
        class: this._isPlaying(preset) ? "preset playing" : "preset",
        title: preset.name,
        "aria-label": preset.name,
        onclick: () =>
          this._call({ type: "bluos_companion/play", path: `/Preset?id=${preset.id}` }),
      },
      preset.image
        ? el("img", { src: preset.image, alt: preset.name, loading: "lazy" })
        : el("span", {}, preset.name),
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
      { name: "columns", selector: { number: { min: 1, max: 8, mode: "box" } } },
      { name: "show_footer", selector: { boolean: {} } },
      { name: "show_volume", selector: { boolean: {} } },
      { name: "show_playback", selector: { boolean: {} } },
      { name: "show_input", selector: { boolean: {} } },
      { name: "show_power", selector: { boolean: {} } },
      {
        type: "expandable",
        name: "other_entities",
        title: this._t("editor_other_entities"),
        schema: [
          { name: "volume_entity", selector: { entity: { domain: "media_player" } } },
          { name: "source_entity", selector: { entity: { domain: "media_player" } } },
          { name: "power_entity", selector: { entity: { domain: ["media_player", "switch", "input_boolean"] } } },
        ],
      },
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
      columns: "editor_columns",
      show_footer: "editor_show_footer",
      show_volume: "editor_show_volume",
      show_playback: "editor_show_playback",
      show_input: "editor_show_input",
      show_power: "editor_show_power",
      volume_entity: "editor_volume_entity",
      source_entity: "editor_source_entity",
      power_entity: "editor_power_entity",
    };
    this._form.computeLabel = (schema) => this._t(labels[schema.name] || schema.name);
    this._form.schema = this._schema();
    this._form.hass = this._hass;
    this._form.data = {
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
  name: "BluOS Companion presets",
  description: "The presets of a BluOS player as a grid, with input selection and volume.",
});
