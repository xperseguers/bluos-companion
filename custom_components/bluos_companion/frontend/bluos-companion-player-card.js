/* BluOS Companion player card: what a player plays, with transport and volume.
 * Plain JavaScript, no build step. */

const PLAYER_CARD_STYLE = `
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; }
  .top { display: flex; align-items: center; gap: 12px; padding: 12px 12px 4px; }
  .cover {
    width: 72px;
    height: 72px;
    flex: none;
    border-radius: 8px;
    object-fit: cover;
    background: var(--secondary-background-color);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--secondary-text-color);
    --mdc-icon-size: 36px;
  }
  .info { flex: 1; min-width: 0; }
  .info div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .title { font-weight: 500; font-size: 16px; }
  .sub { color: var(--secondary-text-color); font-size: 13px; }
  .where { color: var(--secondary-text-color); font-size: 12px; display: flex; align-items: center; gap: 4px; --mdc-icon-size: 14px; }
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
  dialog h2 { margin: 0 0 12px; font-size: 18px; font-weight: 500; }
  dialog .list { display: flex; flex-direction: column; gap: 8px; }
  dialog button.target {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--divider-color);
    border-radius: 12px;
    background: var(--card-background-color);
    color: var(--primary-text-color);
    font: inherit;
    text-align: left;
    cursor: pointer;
    --mdc-icon-size: 24px;
  }
  dialog button.target .text { flex: 1; min-width: 0; }
  dialog button.target .text div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  dialog button.target .sub { font-size: 12px; color: var(--secondary-text-color); }
  progress { display: block; width: calc(100% - 24px); height: 4px; margin: 4px 12px; accent-color: var(--primary-color); }
  .controls { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 0 12px; }
  button.icon.on { color: var(--primary-color); }
  .link { display: flex; align-items: center; gap: 4px; padding: 0 16px 12px; font-size: 13px; color: var(--primary-color); text-decoration: none; --mdc-icon-size: 16px; }
  .volume { display: flex; align-items: center; gap: 8px; padding: 0 12px 8px; }
  button.icon {
    border: none;
    background: none;
    color: var(--primary-text-color);
    cursor: pointer;
    padding: 8px;
    border-radius: 50%;
    display: inline-flex;
    --mdc-icon-size: 28px;
  }
  button.icon.main { --mdc-icon-size: 36px; }
  button.icon.on { color: var(--primary-color); }
  button.icon:disabled { opacity: 0.4; cursor: default; }
  .volume button.icon { --mdc-icon-size: 24px; padding: 6px; }
  input[type="range"] { flex: 1; accent-color: var(--primary-color); min-width: 0; }
`;

const PLAYER_ACTIVE = ["play", "stream"];

function pel(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null) node.setAttribute(key, value);
  }
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}

const picon = (name) => pel("ha-icon", { icon: name });

class BluOSCompanionPlayerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._player = null;
    this._receivedAt = 0;
    this._unsubscribe = null;
    this._ticker = null;
  }

  static getConfigElement() {
    return document.createElement("bluos-companion-player-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find((id) => id.startsWith("media_player."));
    return { entity: entity || "", show_volume: true };
  }

  setConfig(config) {
    if (!config.entity) throw new Error("Choose the BluOS Companion player (entity)");
    this._config = { show_volume: true, ...config };
    this._build();
    this._render();
  }

  getCardSize() {
    return 3;
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
    if (this._hass && this._strings && !this._unsubscribe) this._subscribe();
    this._ticker = setInterval(() => this._tick(), 1000);
  }

  disconnectedCallback() {
    clearInterval(this._ticker);
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = null;
    }
  }

  async _subscribe() {
    this._unsubscribe = await this._hass.connection.subscribeMessage(
      (event) => {
        this._all = event.players;
        this._player = event.players.find((player) => player.entity_id === this._config.entity) || null;
        this._receivedAt = Date.now();
        this._render();
      },
      { type: "bluos_companion/subscribe" },
    );
  }

  _control(action, value) {
    if (!this._player) return;
    return this._hass.connection
      .sendMessagePromise({
        type: "bluos_companion/control",
        entry_id: this._player.entry_id,
        action,
        ...(value === undefined ? {} : { value }),
      })
      .catch((err) =>
        this.dispatchEvent(
          new CustomEvent("hass-notification", {
            detail: { message: err.message || String(err) },
            bubbles: true,
            composed: true,
          }),
        ),
      );
  }

  _build() {
    this._cover = pel("div", { class: "cover" }, picon("mdi:music"));
    this._title = pel("div", { class: "title" });
    this._sub = pel("div", { class: "sub" });
    this._where = pel("div", { class: "where" }, picon("mdi:speaker"), pel("span"));
    this._progress = pel("progress", { max: 1, value: 0 });
    this._prev = pel("button", { class: "icon", onclick: () => this._control("previous") }, picon("mdi:skip-previous"));
    this._toggle = pel(
      "button",
      {
        class: "icon main",
        onclick: () => this._control(PLAYER_ACTIVE.includes(this._player.state) ? "pause" : "play"),
      },
      picon("mdi:play"),
    );
    this._next = pel("button", { class: "icon", onclick: () => this._control("next") }, picon("mdi:skip-next"));
    this._move = pel("button", { class: "icon", title: this._t("move_playback"), onclick: () => this._showMove() }, picon("mdi:transfer-right"));
    // Switching an amplifier on takes a few seconds: the button waits for the answer
    this._power = pel(
      "button",
      {
        class: "icon",
        onclick: async () => {
          this._power.disabled = true;
          try {
            await this._control("power", !this._player.power);
          } finally {
            this._power.disabled = false;
          }
        },
      },
      picon("mdi:power"),
    );
    this._dialog = pel("dialog", {
      onclick: (event) => {
        if (event.target === this._dialog) this._dialog.close();
      },
    });
    this._mute = pel("button", { class: "icon", onclick: () => this._control("mute", !this._player.muted) }, picon("mdi:volume-high"));
    this._volume = pel("input", {
      type: "range",
      min: 0,
      max: 100,
      onchange: (event) => this._control("volume", Number(event.target.value)),
    });
    this._volumeRow = pel("div", { class: "volume" }, this._mute, this._volume);
    this._link = pel("a", { class: "link", target: "_blank", rel: "noopener" }, picon("mdi:open-in-new"), pel("span"));
    this._message = pel("div", { class: "sub", style: "padding: 16px; text-align: center" });
    this._content = pel(
      "div",
      {},
      pel("div", { class: "top" }, this._cover, pel("div", { class: "info" }, this._title, this._sub, this._where)),
      this._progress,
      pel("div", { class: "controls" }, this._prev, this._toggle, this._next, this._move, this._power),
      this._volumeRow,
      this._link,
    );
    this.shadowRoot.replaceChildren(
      pel("style", {}, PLAYER_CARD_STYLE),
      pel("ha-card", {}, this._message, this._content, this._dialog),
    );
  }

  _render() {
    if (!this._content) return;
    const player = this._player;
    this._content.hidden = !player;
    this._message.hidden = Boolean(player);
    if (!player) {
      this._message.textContent = this._t("card_not_found");
      return;
    }
    this._title.textContent = player.title || player.name;
    this._sub.textContent = [player.artist, player.album].filter(Boolean).join(" - ");
    this._sub.hidden = !this._sub.textContent;
    this._where.lastChild.textContent = player.name;
    if (player.image) {
      this._cover.replaceWith((this._cover = pel("img", { class: "cover", src: player.image, alt: "" })));
    } else if (this._cover.tagName === "IMG") {
      this._cover.replaceWith((this._cover = pel("div", { class: "cover" }, picon("mdi:music"))));
    }
    this._toggle.firstChild.setAttribute("icon", PLAYER_ACTIVE.includes(player.state) ? "mdi:pause" : "mdi:play");
    this._prev.disabled = this._next.disabled = !player.available;
    this._move.title = this._t("move_playback");
    this._move.hidden = !(player.can_move && PLAYER_ACTIVE.includes(player.state) && (this._all || []).length > 1);
    this._power.hidden = !(this._config.show_power === true && typeof player.power === "boolean");
    this._power.title = this._t("power");
    this._power.classList.toggle("on", player.power === true);
    this._volumeRow.hidden = this._config.show_volume === false;
    this._volume.disabled = player.volume < 0;
    this._volume.max = player.max_volume;
    this._volume.value = Math.max(player.volume, 0);
    this._mute.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    this._progress.hidden = !(player.duration > 0);
    this._link.hidden = !(this._config.show_control_panel === true && player.configuration_url);
    this._link.href = player.configuration_url || "";
    this._link.lastChild.textContent = this._t("open_control_panel");
    this._tick();
  }

  _showMove() {
    const source = this._player;
    if (!source) return;
    this._dialog.replaceChildren(
      pel("h2", {}, this._t("move_playback_to")),
      pel("div", { class: "sub", style: "margin: -8px 0 12px" }, `${source.name}: ${[source.title, source.artist].filter(Boolean).join(" - ")}`),
      pel(
        "div",
        { class: "list" },
        ...this._all
          .filter((target) => target.entry_id !== source.entry_id)
          .map((target) =>
            pel(
              "button",
              {
                class: "target",
                onclick: () => {
                  this._dialog.close();
                  this._hass.connection
                    .sendMessagePromise({ type: "bluos_companion/move", entry_id: source.entry_id, target: target.entry_id })
                    .catch((err) =>
                      this.dispatchEvent(
                        new CustomEvent("hass-notification", {
                          detail: { message: err.message || String(err) },
                          bubbles: true,
                          composed: true,
                        }),
                      ),
                    );
                },
              },
              picon("mdi:speaker"),
              pel(
                "div",
                { class: "text" },
                pel("div", {}, target.name),
                pel("div", { class: "sub" }, [target.title, target.artist].filter(Boolean).join(" - ") || "\u00a0"),
              ),
              picon("mdi:transfer-right"),
            ),
          ),
      ),
    );
    this._dialog.showModal();
  }

  _tick() {
    const player = this._player;
    if (!this._progress || !player || !(player.duration > 0)) return;
    let position = player.position || 0;
    if (PLAYER_ACTIVE.includes(player.state)) position += (Date.now() - this._receivedAt) / 1000;
    this._progress.max = player.duration;
    this._progress.value = Math.min(position, player.duration);
  }
}

class BluOSCompanionPlayerCardEditor extends HTMLElement {
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

  _render() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.schema = [
        { name: "entity", required: true, selector: { entity: { domain: "media_player", integration: "bluos_companion" } } },
        { name: "show_volume", selector: { boolean: {} } },
        { name: "show_power", selector: { boolean: {} } },
        { name: "show_control_panel", selector: { boolean: {} } },
      ];
      this._form.addEventListener("value-changed", (event) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: event.detail.value }, bubbles: true, composed: true }),
        );
      });
      this.append(this._form);
    }
    const labels = {
      entity: "editor_player",
      show_volume: "editor_show_volume",
      show_power: "editor_show_power",
      show_control_panel: "editor_show_control_panel",
    };
    this._form.computeLabel = (schema) => this._t(labels[schema.name] || schema.name);
    this._form.hass = this._hass;
    this._form.data = { show_volume: true, show_power: false, show_control_panel: false, ...this._config };
  }
}

if (!customElements.get("bluos-companion-player-card")) {
  customElements.define("bluos-companion-player-card", BluOSCompanionPlayerCard);
}
if (!customElements.get("bluos-companion-player-card-editor")) {
  customElements.define("bluos-companion-player-card-editor", BluOSCompanionPlayerCardEditor);
}
window.customCards = window.customCards || [];
window.customCards.push({
  type: "bluos-companion-player-card",
  name: "BluOS Companion player",
  description: "What a BluOS player plays, with transport buttons and volume.",
});
