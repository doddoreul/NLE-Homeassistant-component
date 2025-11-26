import logging
import aiohttp
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    _LOGGER.warning("NLE Thermostat async_setup_platform called")
    """Setup YAML sensors."""
    api_url = hass.data[DOMAIN][CONF_API_URL]
    api_key = hass.data[DOMAIN][CONF_API_KEY]

    coordinator = NLECoordinator(hass, api_url, api_key)
    await coordinator.async_request_refresh()

    if not coordinator.data:
        _LOGGER.error("Impossible de récupérer les données NLE. Vérifie l'API.")
        return

    device_info = coordinator.data.get("device", {})
    serial = device_info.get("serial")
    if not serial:
        _LOGGER.error("Impossible de récupérer le serial du device")
        return

    sensors = [
        NLEDeviceSensor(coordinator, serial, "Living Room Device")
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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Erreur API : status {resp.status}")
                    return await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Erreur API NLE : {err}") from err


class NLEDeviceSensor(Entity):
    """Entity représentant un device NLE avec plusieurs attributs."""

    def __init__(self, coordinator, serial, name):
        self.coordinator = coordinator
        self.serial = serial
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"nle_thermostat_{self.serial}"

    @property
    def state(self):
        """On prend current_temperature comme valeur principale du capteur."""
        data = self.coordinator.data
        shared = data.get("state", {}).get(f"shared.{self.serial}", {}).get("value", {})
        return shared.get("current_temperature")

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        """Toutes les données importantes."""
        data = self.coordinator.data
        attrs = {}

        # Ajout des données du device
        device = data.get("device", {})
        attrs.update({
            "device_id": device.get("id"),
            "serial": device.get("serial"),
            "device_name": device.get("name"),
        })

        # Ajout des champs de state.shared
        shared = data.get("state", {}).get(f"shared.{self.serial}", {}).get("value", {})
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
            if field in shared:
                attrs[field] = shared[field]

        return attrs

    async def async_update(self):
        await self.coordinator.async_request_refresh()
