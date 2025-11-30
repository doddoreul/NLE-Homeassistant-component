import logging
from datetime import timedelta
import aiohttp

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)

HVAC_MODE_HEAT = "heat"
HVAC_MODE_OFF = "off"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup YAML-based NLE climate."""
    _LOGGER.info("NLE Thermostat climate async_setup_platform called")

    cfg = hass.data.get(DOMAIN, {})
    device_id = cfg.get(CONF_DEVICE_ID)
    api_url = cfg.get(CONF_API_URL).rstrip("/") + f"/thermostat/{device_id}/status"
    api_key = cfg.get(CONF_API_KEY)

    coordinator = NLECoordinator(hass, api_url, api_key)
    await coordinator.async_refresh()

    async_add_entities([NLEClimate(coordinator, device_id, "Living Room")])


class NLECoordinator(DataUpdateCoordinator):
    """Coordinator for NLE API calls."""

    def __init__(self, hass, api_url, api_key):
        super().__init__(
            hass,
            _LOGGER,
            name="nle_thermostat_climate_coordinator",
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
                        raise UpdateFailed(f"API HTTP {resp.status}")
                    return await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Erreur API NLE : {err}") from err

    async def async_set_temperature(self, device_id, temperature, mode="heat"):
        url = self.api_url.rsplit("/status", 1)[0] + "/temperature"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        json_data = {"value": temperature, "mode": mode, "scale": "C"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    _LOGGER.error("Erreur API NLE set_temperature: HTTP %s", resp.status)
                return await resp.json()

    async def async_set_mode(self, device_id, mode):
        url = self.api_url.rsplit("/status", 1)[0] + "/mode"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        json_data = {"mode": mode}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    _LOGGER.error("Erreur API NLE set_mode: HTTP %s", resp.status)
                return await resp.json()


class NLEClimate(ClimateEntity):
    """Representation of a NLE thermostat."""

    def __init__(self, coordinator, device_id, name):
        self.coordinator = coordinator
        self.device_id = device_id
        self._name = name
        self._hvac_mode = HVAC_MODE_HEAT
        self._target_temperature = None
        self._current_temperature = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        short_id = self.device_id[:8]
        return f"nle_{short_id}_climate"

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return [HVAC_MODE_HEAT, HVAC_MODE_OFF]

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

    async def async_update(self):
        data = self.coordinator.data or {}
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})
        self._current_temperature = shared.get("current_temperature")
        self._target_temperature = shared.get("target_temperature")
        self._hvac_mode = HVAC_MODE_HEAT if shared.get("hvac_heater_state") else HVAC_MODE_OFF

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        await self.coordinator.async_set_temperature(self.device_id, temperature, "heat")
        await self.coordinator.async_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        mode = "heat" if hvac_mode == HVAC_MODE_HEAT else "off"
        await self.coordinator.async_set_mode(self.device_id, mode)
        await self.coordinator.async_refresh()
