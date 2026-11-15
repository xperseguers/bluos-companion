"""Constants for the BluOS Companion integration."""

DOMAIN = "bluos_companion"

CONF_PORT = "port"
CONF_HIDDEN_SERVICES = "hidden_services"
CONF_MAX_VOLUME = "max_volume"
CONF_BACKUP_PLAYLISTS = "backup_playlists"
CONF_BEFORE_PLAYBACK = "before_playback_script"
# Entities that stand for the volume, the inputs and the power of a player (an amplifier the player feeds)
CONF_VOLUME_ENTITY = "volume_entity"
CONF_SOURCE_ENTITY = "source_entity"
CONF_POWER_ENTITY = "power_entity"
# How long the script run before a new playback may take (an amplifier takes a few seconds to wake up)
BEFORE_PLAYBACK_TIMEOUT = 60
DEFAULT_PORT = 11000

LONG_POLL_TIMEOUT = 100
MIN_POLL_INTERVAL = 1
RETRY_INTERVAL = 15
# A player that cannot be reached is looked at more often, to show it back as soon as it answers
UNREACHABLE_INTERVAL = 4
# After a command, the status is read again after these delays (seconds), whatever the long poll does
REFRESH_AFTER_COMMAND = (1, 4)
# How often a player that is not a secondary looks whether it became one
VOLUME_IDLE_INTERVAL = 5
# While the player reads its library: how often the scan is looked at, and how long to wait for it to start
INDEXING_POLL_INTERVAL = 1
INDEXING_START_TIMEOUT = 30

ICONS_URL = "/bluos_companion/icons"

CARD_ELEMENT = "bluos-companion-presets-card"
PANEL_PATH = "bluos-companion"
PANEL_ELEMENT = "bluos-companion-panel"
PANEL_URL = "/bluos_companion/panel"
EXTERNAL_SOURCE_URL = "Capture:External"

# The amplifier a BluOS module is built into, controlled on the same address
AMPLIFIER_PORT = 23
AMPLIFIER_SCAN_INTERVAL = 30
