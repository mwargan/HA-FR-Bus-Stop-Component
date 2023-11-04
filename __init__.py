# __init__.py

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'bus_stop'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required('bus_stop_ids'): vol.All(cv.ensure_list, [cv.positive_int]),
    }),
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the bus stop component from configuration.yaml."""
    bus_stop_config = config[DOMAIN]
    hass.data[DOMAIN] = bus_stop_config

    # Forward the setup to the sensor platform
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform('sensor', DOMAIN, {}, config)
    )

    return True