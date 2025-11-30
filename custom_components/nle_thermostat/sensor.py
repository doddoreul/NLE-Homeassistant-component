import logging
import aiohttp
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)

async def async_setup_entry(hass, entry, async_add_entities):
    api_url = entry.data[CONF_API_URL].rstrip("/") + f"/thermostat/{entry.data[CONF_DEVICE_ID]}/status"
    api_key = entry.data[CONF_API_KEY]
    device_id = entry.data[CONF_DEVICE_ID]

    coordinator = NLECoordinator(hass, api_url, api_key)
    await coordinator.async_refresh()

    entities = [
        NLEFieldSensor(coordinator, device_id, "Current Temperature", "current_temperature"),
        NLEFieldSensor(coordinator, device_id, "Target Temperature", "target_temperature"),
        NLEFieldSensor(coordinator, device_id, "Mode", "target_temperature_type"),
        NLEFieldSensor(coordinator, device_id, "Heating", "hvac_heater_state"),
    ]

    async_add_entities(entities)


class NLECoordinator(DataUpdateCoordinator):
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
                async with session.get(self.api_url, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"API HTTP {resp.status}")
                    return await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Erreur API NLE : {err}") from err


class NLEFieldSensor(Entity):
    def __init__(self, coordinator, device_id, name, field):
        self.coordinator = coordinator
        self.device_id = device_id
        self._name = name
        self._field = field

    @property
    def name(self):
        return f"NLE {self._name}"

    @property
    def unique_id(self):
        short_id = self.device_id[:8]
        return f"nle_{short_id}_{self._field}"

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def state(self):
        data = self.coordinator.data or {}
        state_dict = data.get("state", {})
        shared_key = next((k for k in state_dict if k.startswith("shared.")), None)
        if not shared_key:
            return None
        val = state_dict.get(shared_key, {}).get("value", {})
        return val.get(self._field)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        device = data.get("device", {})
        return {
            "device_id": device.get("id"),
            "serial": device.get("serial"),
            "device_name": device.get("name"),
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()
