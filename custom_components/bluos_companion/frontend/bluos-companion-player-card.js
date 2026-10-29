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
  progress { display: block; width: calc(100% - 24px); height: 4px; margin: 4px 12px; accent-color: var(--primary-color); }
  .controls { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 0 12px; }
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
    if (first && this.isConnected) this._subscribe();
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

  async _subscribe() {
    this._unsubscribe = await this._hass.connection.subscribeMessage(
      (event) => {
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
    this._mute = pel("button", { class: "icon", onclick: () => this._control("mute", !this._player.muted) }, picon("mdi:volume-high"));
    this._volume = pel("input", {
      type: "range",
      min: 0,
      max: 100,
      onchange: (event) => this._control("volume", Number(event.target.value)),
    });
    this._volumeRow = pel("div", { class: "volume" }, this._mute, this._volume);
    this._message = pel("div", { class: "sub", style: "padding: 16px; text-align: center" });
    this._content = pel(
      "div",
      {},
      pel("div", { class: "top" }, this._cover, pel("div", { class: "info" }, this._title, this._sub, this._where)),
      this._progress,
      pel("div", { class: "controls" }, this._prev, this._toggle, this._next),
      this._volumeRow,
    );
    this.shadowRoot.replaceChildren(
      pel("style", {}, PLAYER_CARD_STYLE),
      pel("ha-card", {}, this._message, this._content),
    );
  }

  _render() {
    if (!this._content) return;
    const player = this._player;
    this._content.hidden = !player;
    this._message.hidden = Boolean(player);
    if (!player) {
      this._message.textContent = "Player not found. Check the entity of the card.";
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
    this._volumeRow.hidden = this._config.show_volume === false;
    this._volume.disabled = player.volume < 0;
    this._volume.value = Math.max(player.volume, 0);
    this._mute.firstChild.setAttribute("icon", player.muted ? "mdi:volume-off" : "mdi:volume-high");
    this._progress.hidden = !(player.duration > 0);
    this._tick();
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
    this._hass = hass;
    if (this._form) this._form.hass = hass;
  }

  _render() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.schema = [
        { name: "entity", required: true, selector: { entity: { domain: "media_player", integration: "bluos_companion" } } },
        { name: "show_volume", selector: { boolean: {} } },
      ];
      this._form.computeLabel = (schema) => ({ entity: "Player", show_volume: "Show the volume" })[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (event) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: event.detail.value }, bubbles: true, composed: true }),
        );
      });
      this.append(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { show_volume: true, ...this._config };
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
