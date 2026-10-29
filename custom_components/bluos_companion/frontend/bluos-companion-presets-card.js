/* BluOS Companion presets card: the presets of a player as a grid of artworks, with
 * input selection, volume and play / pause. Plain JavaScript, no build step. */

const CARD_STYLE = `
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
  footer { padding: 4px 12px 12px; display: flex; flex-direction: column; gap: 4px; }
  .row { display: flex; align-items: center; gap: 8px; min-height: 40px; }
  .row .name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  select {
    font: inherit;
    max-width: 45%;
    border: none;
    background: none;
    color: var(--primary-text-color);
  }
  button.icon {
    border: none;
    background: none;
    color: var(--primary-text-color);
    cursor: pointer;
    padding: 6px;
    border-radius: 50%;
    display: inline-flex;
    --mdc-icon-size: 24px;
  }
  button.icon:disabled { opacity: 0.4; cursor: default; }
  input[type="range"] { flex: 1; accent-color: var(--primary-color); min-width: 0; }
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
    if (first && this.isConnected) this._subscribe();
  }

  connectedCallback() {
    if (this._hass && !this._unsubscribe) this._subscribe();
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
    this._name = el("span", { class: "name" });
    this._source = el("select", { onchange: (event) => this._control("source", event.target.value) });
    this._mute = el("button", { class: "icon", onclick: () => this._control("mute", !this._player.muted) }, icon("mdi:volume-high"));
    this._volume = el("input", {
      type: "range",
      min: 0,
      max: 100,
      onchange: (event) => this._control("volume", Number(event.target.value)),
    });
    this._toggle = el(
      "button",
      {
        class: "icon",
        onclick: () => this._control(ACTIVE_STATES.includes(this._player.state) ? "pause" : "play"),
      },
      icon("mdi:play"),
    );
    this._footer = el(
      "footer",
      {},
      el("div", { class: "row" }, icon("mdi:speaker"), this._name, this._source),
      el("div", { class: "row" }, this._mute, this._volume, this._toggle),
    );
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
      ? "Player not found. Check the entity of the card."
      : this._presets && !this._presets.length
        ? "This player has no presets."
        : "";
    this._message.hidden = !this._message.textContent;

    this._footer.hidden = !player || this._config.show_footer === false;
    if (!player) return;
    this._name.textContent = player.name;
    this._source.hidden = !player.sources.length;
    this._source.replaceChildren(
      el("option", { value: "" }, "…"),
      ...player.sources.map((name) => {
        const option = el("option", { value: name }, name);
        option.selected = name === player.source;
        return option;
      }),
    );
    this._source.firstChild.disabled = true;
    this._source.firstChild.hidden = true;
    this._source.value = player.source || "";
    this._mute.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    this._volume.disabled = player.volume < 0;
    this._volume.max = player.max_volume;
    this._volume.value = Math.max(player.volume, 0);
    this._toggle.firstChild.setAttribute("icon", ACTIVE_STATES.includes(player.state) ? "mdi:pause" : "mdi:play");
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
    this._hass = hass;
    if (this._form) this._form.hass = hass;
  }

  _render() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.schema = [
        { name: "entity", required: true, selector: { entity: { domain: "media_player", integration: "bluos_companion" } } },
        { name: "columns", selector: { number: { min: 1, max: 8, mode: "box" } } },
        { name: "show_footer", selector: { boolean: {} } },
      ];
      this._form.computeLabel = (schema) =>
        ({ entity: "Player", columns: "Columns", show_footer: "Show volume and input" })[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (event) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: event.detail.value }, bubbles: true, composed: true }),
        );
      });
      this.append(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { columns: 3, show_footer: true, ...this._config };
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
