/* BluOS Companion play button card: one button that plays a genre, a preset or a saved
 * playlist on a player. It calls the same services as an automation does.
 * Plain JavaScript, no build step. */

const CARD_STYLE = `
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; height: 100%; }
  button.play {
    display: flex;
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    background: none;
    color: var(--primary-text-color);
    font: inherit;
    text-align: left;
    cursor: pointer;
    box-sizing: border-box;
  }
  button.play:active { opacity: 0.7; }
  .art {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .art img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .art ha-icon { --mdc-icon-size: 40%; width: 40%; height: 40%; }
  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 500;
    overflow-wrap: anywhere;
  }
  .message { padding: 16px; color: var(--secondary-text-color); text-align: center; }

  /* A cover and the name beside it */
  .row button.play { align-items: center; gap: 12px; padding: 8px 12px; min-height: 56px; }
  .row .art { flex: none; width: 48px; height: 48px; border-radius: 8px; }
  .row .name { white-space: nowrap; }
  .row .art ha-icon { --mdc-icon-size: 28px; width: 28px; height: 28px; }
  .row.noart .name { white-space: normal; }

  /* A square cover with the name below it */
  .tile button.play { flex-direction: column; }
  .tile .art { width: 100%; aspect-ratio: 1; }
  .tile .name { padding: 8px 12px; text-align: center; }

  /* A square cover with the name over it */
  .cover button.play { position: relative; flex-direction: column; }
  .cover .art { width: 100%; aspect-ratio: 1; }
  .cover .name {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 24px 12px 10px;
    color: #fff;
    text-align: center;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.6);
    background: linear-gradient(transparent, rgba(0, 0, 0, 0.65));
  }
  .cover.noart .name { position: static; color: var(--primary-text-color); text-shadow: none; background: none; padding: 8px 12px; }
  .noart.tile .name, .noart.row .name { text-align: center; }
  .noart.row .name { text-align: left; }
`;

const DEFAULT_ICONS = { genre: "mdi:music-box-multiple", preset: "mdi:radio", playlist: "mdi:playlist-music" };
const SERVICES = { genre: "play_genre", preset: "play_preset", playlist: "play_playlist" };

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

class BluOSCompanionPlayButtonCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._item = null; // what the player says of the item: { value, name, image }
    this._loadedFor = "";
  }

  static getConfigElement() {
    return document.createElement("bluos-companion-play-button-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find((id) => id.startsWith("media_player."));
    return { entity: entity || "", mode: "genre", item: "", layout: "tile", show_image: true, show_name: true };
  }

  setConfig(config) {
    if (!config.entity) throw new Error("Choose the BluOS Companion player (entity)");
    if (!SERVICES[config.mode || "genre"]) throw new Error("The mode must be genre, preset or playlist");
    this._config = { mode: "genre", layout: "tile", show_image: true, show_name: true, ...config };
    this._loadedFor = "";
    this._item = null;
    this._render();
    if (this._hass) this._load();
  }

  getCardSize() {
    return this._config && this._config.layout === "row" ? 1 : 3;
  }

  getGridOptions() {
    return this._config && this._config.layout === "row"
      ? { columns: 6, rows: 1, min_columns: 3, min_rows: 1 }
      : { columns: 6, min_columns: 2 };
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._loadStrings().then(() => {
        this._render();
        this._load();
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
    // A card put back on the page asks again, the presets or the playlists may have changed
    if (this._hass && this._config) {
      this._loadedFor = "";
      this._load();
    }
  }

  // The name and the artwork of the item
  async _load() {
    const { entity, mode, item } = this._config;
    const key = `${entity}|${mode}|${item}`;
    if (!item || key === this._loadedFor) return;
    this._loadedFor = key;
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "bluos_companion/play_button_items",
        entity_id: entity,
        mode,
        item: String(item),
      });
      if (this._loadedFor !== key) return; // the configuration changed meanwhile
      this._item = result.items[0] || null;
      this._missing = !this._item;
    } catch (err) {
      if (this._loadedFor !== key) return;
      this._item = null;
      this._missing = false;
    }
    this._render();
  }

  _notify(message) {
    this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
  }

  // The same services as an automation: nothing here that a script could not do
  _play() {
    const { entity, mode, item, shuffle, clear_queue: clear } = this._config;
    const data = { entity_id: entity, [mode]: String(item) };
    if (mode !== "preset") {
      if (shuffle) data.shuffle = true;
      if (clear) data.clear_queue = true;
    }
    return this._hass.callService("bluos_companion", SERVICES[mode], data).catch((err) => {
      this._notify((err && err.message) || String(err));
    });
  }

  _render() {
    if (!this._config) return;
    const { mode, item, layout, show_image: showImage, show_name: showName } = this._config;
    // An item that the player does not have (any more) says so instead of staying blank
    const unknown = this._missing ? this._t("play_button_unknown", { item: String(item) }) : "";
    const name = this._config.name || (this._item && this._item.name) || unknown || (mode === "preset" ? "" : item) || "";
    const image = this._item && this._item.image;
    const artwork = showImage !== false;
    const layoutName = ["row", "tile", "cover"].includes(layout) ? layout : "tile";

    let body;
    if (!item) {
      body = el("div", { class: "message" }, this._t("play_button_choose"));
    } else {
      const label = showName === false ? null : el("div", { class: "name", title: name }, name);
      const art = artwork
        ? el(
            "div",
            { class: "art" },
            image
              ? el("img", { src: image, alt: name, loading: "lazy" })
              : icon(this._config.icon || DEFAULT_ICONS[mode]),
          )
        : null;
      body = el(
        "button",
        { class: "play", title: name, "aria-label": name || this._t("play_button_play"), onclick: () => this._play() },
        art,
        label,
      );
    }
    const classes = [layoutName, artwork ? "" : "noart"].filter(Boolean);
    const card = el("ha-card", { class: classes.join(" ") }, body);
    this.shadowRoot.replaceChildren(el("style", {}, CARD_STYLE), card);
  }
}

class BluOSCompanionPlayButtonCardEditor extends HTMLElement {
  constructor() {
    super();
    this._options = []; // the items of the player for the chosen mode: [{ value, label }]
    this._optionsFor = "";
  }

  setConfig(config) {
    this._config = config;
    this._render();
    this._loadOptions();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    if (first) {
      this._loadStrings().then(() => {
        this._render();
        this._loadOptions();
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

  // The genres, presets or playlists of the player, to choose from
  async _loadOptions() {
    if (!this._hass || !this._config || !this._config.entity) return;
    const mode = this._config.mode || "genre";
    const key = `${this._config.entity}|${mode}`;
    if (key === this._optionsFor) return;
    this._optionsFor = key;
    let options = [];
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "bluos_companion/play_button_items",
        entity_id: this._config.entity,
        mode,
      });
      options = result.items.map((entry) => ({
        value: entry.value,
        // A preset is told apart by its number
        label: mode === "preset" ? `${entry.value}. ${entry.name}` : entry.name,
      }));
    } catch (err) {
      options = [];
    }
    if (this._optionsFor !== key) return;
    this._options = options;
    this._render();
  }

  _schema(data) {
    const mode = data.mode;
    const options = [...this._options];
    // An item that the player does not list any more stays visible, so that it can be seen and replaced
    if (data.item && !options.some((option) => option.value === String(data.item))) {
      options.unshift({ value: String(data.item), label: String(data.item) });
    }
    return [
      { name: "entity", required: true, selector: { entity: { domain: "media_player", integration: "bluos_companion" } } },
      {
        name: "mode",
        required: true,
        selector: {
          select: {
            mode: "list",
            options: ["genre", "preset", "playlist"].map((value) => ({ value, label: this._t(`editor_mode_${value}`) })),
          },
        },
      },
      { name: "item", required: true, selector: { select: { mode: "dropdown", options } } },
      ...(mode === "preset"
        ? []
        : [
            { name: "shuffle", selector: { boolean: {} } },
            { name: "clear_queue", selector: { boolean: {} } },
          ]),
      {
        name: "layout",
        selector: {
          select: {
            mode: "dropdown",
            options: ["tile", "row", "cover"].map((value) => ({ value, label: this._t(`editor_layout_${value}`) })),
          },
        },
      },
      { name: "show_image", selector: { boolean: {} } },
      { name: "show_name", selector: { boolean: {} } },
      { name: "name", selector: { text: {} } },
      { name: "icon", selector: { icon: {} } },
    ];
  }

  _render() {
    if (!this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (event) => this._changed(event.detail.value));
      this.append(this._form);
    }
    const labels = {
      entity: "editor_player",
      mode: "editor_mode",
      item: "editor_item",
      shuffle: "editor_shuffle",
      clear_queue: "editor_clear_queue",
      layout: "editor_layout",
      show_image: "editor_show_image",
      show_name: "editor_show_name",
      name: "editor_name",
      icon: "editor_icon",
    };
    const data = {
      mode: "genre",
      layout: "tile",
      show_image: true,
      show_name: true,
      shuffle: false,
      clear_queue: false,
      ...this._config,
    };
    this._form.computeLabel = (schema) => this._t(labels[schema.name] || schema.name);
    this._form.schema = this._schema(data);
    this._form.hass = this._hass;
    this._form.data = data;
  }

  _changed(value) {
    const config = { ...value };
    // What was chosen belongs to the player and to the mode: start again when one of them changes
    if (config.mode !== (this._config.mode || "genre") || config.entity !== this._config.entity) config.item = "";
    this._config = config;
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
    this._loadOptions();
    this._render();
  }
}

if (!customElements.get("bluos-companion-play-button-card")) customElements.define("bluos-companion-play-button-card", BluOSCompanionPlayButtonCard);
if (!customElements.get("bluos-companion-play-button-card-editor")) customElements.define("bluos-companion-play-button-card-editor", BluOSCompanionPlayButtonCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "bluos-companion-play-button-card",
  name: "BluOS Companion play button",
  description: "A button that plays a genre, a preset or a saved playlist of a BluOS player.",
});
