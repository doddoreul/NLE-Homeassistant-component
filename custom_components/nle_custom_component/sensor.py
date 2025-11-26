import logging
import aiohttp
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configuration via YAML."""

    api_url = hass.data[DOMAIN][CONF_API_URL]
    api_key = hass.data[DOMAIN][CONF_API_KEY]

    coordinator = NLECoordinator(hass, api_url, api_key)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        NLESensor(coordinator, "example_value", "NLE Example Sensor")
    ]

    async_add_entities(sensors)


class NLECoordinator(DataUpdateCoordinator):
    """Gestion des appels API."""

    def __init__(self, hass, api_url, api_key):
        super().__init__(
            hass,
            _LOGGER,
            name="nle_custom_component_coordinator",
            update_interval=SCAN_INTERVAL,
        )
        self.api_url = api_url
        self.api_key = api_key

    async def _async_update_data(self):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Erreur API : {resp.status}")
                    return await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Erreur API NLE : {err}") from err


class NLESensor(Entity):
    """Capteur basé sur la NLE API."""

    def __init__(self, coordinator, key, name):
        self.coordinator = coordinator
        self._key = key
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"nle_custom_component_{self._key}"

    @property
    def state(self):
        data = self.coordinator.data
        return None if not data else data.get(self._key)

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_update(self):
        await self.coordinator.async_request_refresh()
