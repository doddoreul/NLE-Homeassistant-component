import logging
import aiohttp
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    _LOGGER.info("NLE Thermostat async_setup_platform called")

    api_base = hass.data[DOMAIN].get(CONF_API_URL)
    api_key = hass.data[DOMAIN].get(CONF_API_KEY)
    device_id = hass.data[DOMAIN].get(CONF_DEVICE_ID)

    if not api_base or not api_key or not device_id:
        _LOGGER.error("Configuration incomplète pour nle_thermostat")
        return

    api_url = f"{api_base}thermostat/{device_id}/status"

    coordinator = NLECoordinator(hass, api_url, api_key)
    await coordinator.async_refresh()

    # On crée 4 entités séparées
    sensors = [
        NLEFieldSensor(coordinator, device_id, "nle_target_temp", "target_temperature"),
        NLEFieldSensor(coordinator, device_id, "nle_current_temp", "current_temperature"),
        NLEFieldSensor(coordinator, device_id, "nle_mode", "target_temperature_type"),
        NLEFieldSensor(coordinator, device_id, "nle_heating", "hvac_heater_state"),
    ]

    async_add_entities(sensors)


class NLECoordinator(DataUpdateCoordinator):
    """Coordonne l'appel API."""

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


class NLEFieldSensor(SensorEntity):
    """Un champ individuel du thermostat devient une entité."""

    def __init__(self, coordinator, device_id, sensor_name, field_name):
        self.coordinator = coordinator
        self.device_id = device_id
        self._attr_name = sensor_name.replace("_", " ").title()
        self._attr_unique_id = f"{DOMAIN}_{sensor_name}"
        self.field_name = field_name

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        """Retourne uniquement la valeur du champ souhaité."""
        data = self.coordinator.data or {}
        state = data.get("state", {})
        shared_key = next((k for k in state if k.startswith("shared.")), None)

        if not shared_key:
            return None

        val = state.get(shared_key, {}).get("value", {})
        return val.get(self.field_name)

    async def async_update(self):
        await self.coordinator.async_request_refresh()
