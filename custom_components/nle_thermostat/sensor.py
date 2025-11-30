import logging
import aiohttp
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    _LOGGER.info("NLE Thermostat async_setup_platform called")

    api_key = hass.data[DOMAIN][CONF_API_KEY]
    device_id = hass.data[DOMAIN][CONF_DEVICE_ID]
    api_url = hass.data[DOMAIN][CONF_API_URL]+"thermostat/"+device_id+"/status"

    coordinator = NLECoordinator(hass, api_url, api_key)
    await coordinator.async_refresh()

    data = coordinator.data or {}

    device_info = data.get("device", {})

    if not device_id:
        _LOGGER.error("Impossible de récupérer le device_id du device (device.device_id manquant). Données = %s", data)
        return

    sensors = [
        NLEDeviceSensor(coordinator, device_id, "Living Room Device")
    ]

    async_add_entities(sensors)


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
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Erreur API NLE : HTTP %s sur %s", resp.status, self.api_url)
                        return {}

                    return await resp.json()

        except Exception as err:
            _LOGGER.error("Erreur API NLE : %s", err)
            return {}  # <-- NE PAS PLANTER


class NLEDeviceSensor(Entity):
    def __init__(self, coordinator, device_id, name):
        self.coordinator = coordinator
        self.device_id = device_id
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"nle_thermostat_{self.device_id}"

    @property
    def state(self):
        data = self.coordinator.data or {}
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})
        return shared.get("current_temperature")

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}

        attrs = {}

        # device info
        device = data.get("device", {})
        attrs.update({
            "device_id": device.get("id"),
            "device_id": device.get("device_id"),
            "device_name": device.get("name"),
        })

        # shared state
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})

        fields = [
            "target_temperature",
            "target_temperature_type",
            "current_temperature",
            "hvac_heater_state",
            "hvac_ac_state",
            "fan_mode",
            "auto_away",
            "leaf",
            "can_cool",
            "can_heat",
        ]
        for field in fields:
            attrs[field] = shared.get(field)

        return attrs

    async def async_update(self):
        await self.coordinator.async_request_refresh()
