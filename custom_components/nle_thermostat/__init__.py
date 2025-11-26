"""NLE Custom Component."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import discovery

from .const import DOMAIN
from .config import get_config

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Chargement via configuration.yaml uniquement."""
    hass.data[DOMAIN] = get_config(hass, config)

    await discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    _LOGGER.info("NLE Thermostat custom component loaded")

    return True
