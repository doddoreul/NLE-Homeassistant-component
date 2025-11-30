from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

def get_config(hass: HomeAssistant, config: ConfigType):
    """Charge la config YAML."""
    domain_cfg = config.get(DOMAIN, {})
    return {
        CONF_API_URL: domain_cfg.get(CONF_API_URL),
        CONF_API_KEY: domain_cfg.get(CONF_API_KEY),
        CONF_DEVICE_ID: domain_cfg.get(CONF_DEVICE_ID),
    }
