"""The Feller Wiser integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


from datetime import timedelta

import logging
_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.COVER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Feller Wiser from a config entry."""
    # TODO Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    # hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    for platform in PLATFORMS:
      hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, platform)
      )
    _LOGGER.info("----------------------blubb-------------------------")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    for platform in PLATFORMS:
      await hass.config_entries.async_forward_entry_unload(entry, platform)

    return True
