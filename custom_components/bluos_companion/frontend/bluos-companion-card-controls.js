/* Shared by the dashboard cards: a row with the volume ring, the input popup and the power button.
 * Each control drives the BluOS player of the card or, when the card is set up that way, another
 * entity of Home Assistant (an amplifier, for instance). Plain JavaScript, no build step. */

export const CONTROLS_STYLE = `
  .ctl-row { display: flex; align-items: center; gap: 4px; min-height: 48px; }
  .ctl-spacer { flex: 1; }
  .ctl {
    border: none;
    background: none;
    color: var(--primary-text-color);
    cursor: pointer;
    padding: 6px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    --mdc-icon-size: 24px;
  }
  .ctl:disabled { opacity: 0.4; cursor: default; }
  .ctl.on { color: var(--primary-color); }
  .ctl.main { --mdc-icon-size: 32px; }
  .ctl-ring, .ctl-ring:hover:not(:disabled) {
    position: relative;
    flex: none;
    width: 44px;
    height: 44px;
    padding: 0;
    background: conic-gradient(var(--primary-color) calc(var(--level, 0) * 1%), var(--divider-color) 0);
  }
  .ctl-ring::before {
    content: "";
    position: absolute;
    inset: 3px;
    border-radius: 50%;
    background: var(--card-background-color);
  }
  .ctl-ring ha-icon { position: relative; --mdc-icon-size: 20px; }
  .ctl-strip { display: none; align-items: center; gap: 4px; }
  .ctl-strip input[type="range"] { flex: 1; min-width: 0; accent-color: var(--primary-color); }
  .ctl-row.open > :not(.ctl-strip) { display: none; }
  .ctl-row.open > .ctl-strip { display: flex; flex: 1; }
  dialog.ctl-dialog {
    border: none;
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    padding: 16px;
    min-width: 260px;
    max-width: 90vw;
  }
  dialog.ctl-dialog::backdrop { background: rgba(0, 0, 0, 0.5); }
  dialog.ctl-dialog h2 { margin: 0 0 12px; font-size: 18px; font-weight: 500; }
  dialog.ctl-dialog .list { display: flex; flex-direction: column; gap: 8px; }
  dialog.ctl-dialog button.choice {
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
    --mdc-icon-size: 22px;
  }
  dialog.ctl-dialog button.choice.current { border-color: var(--primary-color); color: var(--primary-color); }
`;

const VOLUME_STEP = 2;
const STRIP_SECONDS = 5;

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

const icon = (name) => el("ha-icon", { icon: name });

function notify(card, err) {
  card.dispatchEvent(
    new CustomEvent("hass-notification", {
      detail: { message: err.message || String(err) },
      bubbles: true,
      composed: true,
    }),
  );
}

function entity(card, id) {
  return id ? card._hass.states[id] : undefined;
}

function call(card, domain, service, data) {
  return card._hass.callService(domain, service, data).catch((err) => notify(card, err));
}

// The volume of the BluOS player, or of another media player
const volume = {
  read(card) {
    const id = card._config.other_entities?.volume_entity;
    if (id) {
      const state = entity(card, id);
      const level = state && state.attributes.volume_level;
      if (typeof level !== "number") return null;
      return { level: Math.round(level * 100), max: 100, muted: state.attributes.is_volume_muted === true, fixed: false };
    }
    const player = card._player;
    if (!player) return null;
    return { level: Math.max(player.volume, 0), max: player.max_volume, muted: player.muted, fixed: player.volume < 0 };
  },
  set(card, value) {
    const id = card._config.other_entities?.volume_entity;
    if (id) return call(card, "media_player", "volume_set", { entity_id: id, volume_level: value / 100 });
    return card._control("volume", value);
  },
  mute(card, muted) {
    const id = card._config.other_entities?.volume_entity;
    if (id) return call(card, "media_player", "volume_mute", { entity_id: id, is_volume_muted: muted });
    return card._control("mute", muted);
  },
};

// The inputs of the BluOS player, or of another media player
const sources = {
  read(card) {
    const id = card._config.other_entities?.source_entity;
    if (id) {
      const state = entity(card, id);
      const list = state && state.attributes.source_list;
      return Array.isArray(list) && list.length ? { names: list, current: state.attributes.source } : null;
    }
    const player = card._player;
    return player && player.sources.length ? { names: player.sources, current: player.source } : null;
  },
  select(card, name) {
    const id = card._config.other_entities?.source_entity;
    if (id) return call(card, "media_player", "select_source", { entity_id: id, source: name });
    return card._control("source", name);
  },
};

// The amplifier of the BluOS player, or another media player, switch...
const power = {
  read(card) {
    const id = card._config.other_entities?.power_entity;
    if (id) {
      const state = entity(card, id);
      if (!state || ["unavailable", "unknown"].includes(state.state)) return null;
      return { on: !["off", "standby"].includes(state.state) };
    }
    const player = card._player;
    return player && typeof player.power === "boolean" ? { on: player.power } : null;
  },
  toggle(card, on) {
    const id = card._config.other_entities?.power_entity;
    if (id) {
      const domain = id.split(".")[0];
      const service = on ? "turn_off" : "turn_on";
      return call(card, domain === "media_player" ? "media_player" : "homeassistant", service, { entity_id: id });
    }
    return card._control("power", !on);
  },
};

/* The row of a card: the volume ring on the left (a tap turns the row into a slider with - and +),
 * then the buttons of the card (`extras`), the input and the power. The card needs `_hass`,
 * `_config`, `_player`, `_t(key)` and `_control(action, value)`. Call `update()` after every change
 * of the player or of the states; it tells whether the row has something to show. */
export function createControls(card, extras = []) {
  let timer = null;
  const arm = () => {
    clearTimeout(timer);
    timer = setTimeout(close, STRIP_SECONDS * 1000);
  };
  const close = () => {
    clearTimeout(timer);
    row.classList.remove("open");
  };
  const step = (direction) => {
    const current = volume.read(card);
    if (!current || current.fixed) return;
    arm();
    volume.set(card, Math.min(current.max, Math.max(0, Math.round(current.level) + direction * VOLUME_STEP)));
  };
  const button = (iconName, onclick) => el("button", { class: "ctl", onclick }, icon(iconName));

  const ring = el(
    "button",
    {
      class: "ctl ctl-ring",
      onclick: () => {
        row.classList.add("open");
        arm();
      },
    },
    icon("mdi:volume-high"),
  );
  const mute = button("mdi:volume-high", () => {
    arm();
    const current = volume.read(card);
    if (current) volume.mute(card, !current.muted);
  });
  const slider = el("input", {
    type: "range",
    min: 0,
    max: 100,
    oninput: arm,
    onchange: (event) => volume.set(card, Number(event.target.value)),
  });
  const down = button("mdi:minus", () => step(-1));
  const up = button("mdi:plus", () => step(1));
  const strip = el("div", { class: "ctl-strip" }, mute, slider, down, up, button("mdi:close", close));

  const dialog = el("dialog", {
    class: "ctl-dialog",
    onclick: (event) => {
      if (event.target === dialog) dialog.close();
    },
  });
  const input = button("mdi:import", () => {
    const available = sources.read(card);
    if (!available) return;
    dialog.replaceChildren(
      el("h2", {}, card._t("input")),
      el(
        "div",
        { class: "list" },
        ...available.names.map((name) =>
          el(
            "button",
            {
              class: `choice${name === available.current ? " current" : ""}`,
              onclick: () => {
                dialog.close();
                sources.select(card, name);
              },
            },
            icon("mdi:import"),
            name,
          ),
        ),
      ),
    );
    dialog.showModal();
  });
  // Switching an amplifier on takes a few seconds: the button waits for the answer
  const switchPower = button("mdi:power", async () => {
    const current = power.read(card);
    if (!current) return;
    switchPower.disabled = true;
    try {
      await power.toggle(card, current.on);
    } finally {
      switchPower.disabled = false;
    }
  });
  const row = el("div", { class: "ctl-row" }, ring, strip, el("span", { class: "ctl-spacer" }), ...extras, input, switchPower);

  const update = () => {
    const config = card._config;
    const level = volume.read(card);
    ring.hidden = config.show_volume === false || !level;
    if (level) {
      const icons = level.muted ? "mdi:volume-off" : "mdi:volume-high";
      ring.firstChild.setAttribute("icon", icons);
      mute.firstChild.setAttribute("icon", icons);
      ring.style.setProperty("--level", level.max ? Math.round((level.level / level.max) * 100) : 0);
      ring.disabled = down.disabled = up.disabled = slider.disabled = level.fixed;
      slider.max = level.max;
      slider.value = level.level;
    }
    if (ring.hidden) close();
    input.hidden = config.show_input === false || !sources.read(card);
    input.title = card._t("input");
    const state = power.read(card);
    switchPower.hidden = !(config.show_power === true && state);
    switchPower.title = card._t("power");
    switchPower.classList.toggle("on", Boolean(state && state.on));
    ring.title = card._t("volume");
    return ![ring, input, switchPower, ...extras].every((node) => node.hidden);
  };

  return { row, dialog, update };
}
