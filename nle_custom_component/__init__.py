"""NLE Custom Component."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .config import get_config

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Setup via configuration.yaml."""
    hass.data[DOMAIN] = get_config(hass, config)
    return True
