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
    # Récupération de la config YAML
    hass.data[DOMAIN] = get_config(hass, config)

    # Forward setup pour sensor
    await discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    _LOGGER.info("NLE Thermostat sensors loaded")

    # Forward setup pour climate
    await discovery.async_load_platform(hass, "climate", DOMAIN, {}, config)
    _LOGGER.info("NLE Thermostat climate loaded")

    return True
