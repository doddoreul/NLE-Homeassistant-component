from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_API_URL, CONF_API_KEY

def get_config(hass: HomeAssistant, config: ConfigType):
    """Lecture des paramètres du configuration.yaml."""
    domain_config = config.get(DOMAIN, {})

    return {
        CONF_API_URL: domain_config.get(CONF_API_URL),
        CONF_API_KEY: domain_config.get(CONF_API_KEY),
    }
