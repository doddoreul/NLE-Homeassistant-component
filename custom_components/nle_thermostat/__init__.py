"""NLE Custom Component."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .config import get_config

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Chargement via configuration.yaml uniquement."""
    hass.data[DOMAIN] = get_config(hass, config)

    # Charger la plateforme sensor
    hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)

    return True
