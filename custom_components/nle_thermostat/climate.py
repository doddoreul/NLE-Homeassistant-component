import logging
import aiohttp
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup YAML sensors."""
    _LOGGER.info("NLE Thermostat async_setup_platform called")

    device_id = hass.data[DOMAIN][CONF_DEVICE_ID]
    api_url = f"{hass.data[DOMAIN][CONF_API_URL]}thermostat/{device_id}/status"
    api_key = hass.data[DOMAIN][CONF_API_KEY]

    coordinator = NLECoordinator(hass, api_url, api_key)
    await coordinator.async_refresh()

    if not coordinator.data:
        _LOGGER.error("Impossible de récupérer les données du device NLE")
        return

    sensors = [
        NLESensor(coordinator, device_id, "current_temperature", "Current Temperature"),
        NLESensor(coordinator, device_id, "target_temperature", "Target Temperature"),
        NLESensor(coordinator, device_id, "target_temperature_type", "Mode"),
        NLESensor(coordinator, device_id, "hvac_heater_state", "Heating"),
    ]

    async_add_entities(sensors)


class NLECoordinator(DataUpdateCoordinator):
    """Centralise les appels API."""

    def __init__(self, hass, api_url, api_key):
        super().__init__(
            hass,
            _LOGGER,
            name="nle_thermostat_coordinator",
            update_interval=SCAN_INTERVAL,
        )
        self.api_url = api_url
        self.api_key = api_key

    async def _async_update_data(self):
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Erreur API : HTTP {resp.status}")
                    return await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Erreur API NLE : {err}") from err


class NLESensor(Entity):
    """Un capteur générique pour NLE Thermostat."""

    def __init__(self, coordinator, device_id, field_key, name):
        self.coordinator = coordinator
        self.device_id = device_id
        self.field_key = field_key
        self._attr_name = f"NLE {name}"
        self._attr_unique_id = f"nle_{device_id[:8]}_{field_key}"

    @property
    def name(self):
        return self._attr_name

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def state(self):
        data = self.coordinator.data or {}
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})
        value = shared.get(self.field_key)
        if isinstance(value, bool):
            return "ON" if value else "OFF"
        return value

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        """Renvoie toutes les données de state.shared."""
        data = self.coordinator.data or {}
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})
        return shared

    async def async_update(self):
        await self.coordinator.async_request_refresh()
