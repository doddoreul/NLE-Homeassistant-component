"""NLE Thermostat climate platform."""
import logging
from datetime import timedelta
import aiohttp

from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)

# Définition des constantes locales pour HA 2025+
HVAC_MODE_HEAT = "heat"
HVAC_MODE_OFF = "off"
SUPPORT_TARGET_TEMPERATURE = 1
TEMP_CELSIUS = "°C"

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Setup YAML-based climate platform."""
    _LOGGER.info("NLE Thermostat climate async_setup_platform called")

    api_url = hass.data[DOMAIN][CONF_API_URL]
    api_key = hass.data[DOMAIN][CONF_API_KEY]
    device_id = hass.data[DOMAIN][CONF_DEVICE_ID]

    coordinator = NLECoordinator(hass, api_url, api_key, device_id)
    await coordinator.async_refresh()

    async_add_entities([NLEClimate(coordinator, device_id, "NLE Thermostat")])


class NLECoordinator(DataUpdateCoordinator):
    """Central coordinator to fetch NLE API data."""

    def __init__(self, hass, api_url, api_key, device_id):
        super().__init__(
            hass,
            _LOGGER,
            name="nle_thermostat_coordinator",
            update_interval=SCAN_INTERVAL,
        )
        self.api_url = f"{api_url}thermostat/{device_id}/status"
        self.api_key = api_key

    async def _async_update_data(self):
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Erreur API NLE : HTTP %s sur %s", resp.status, self.api_url)
                        return {}
                    return await resp.json()
        except Exception as err:
            _LOGGER.error("Erreur API NLE : %s", err)
            return {}


class NLEClimate(ClimateEntity):
    """Climate entity for NLE Thermostat."""

    def __init__(self, coordinator, device_id, name):
        self.coordinator = coordinator
        self.device_id = device_id
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        # Tronquer le device_id pour un ID plus lisible
        return f"nle_{self.device_id[:8]}"

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        data = self.coordinator.data or {}
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})
        return shared.get("current_temperature")

    @property
    def target_temperature(self):
        data = self.coordinator.data or {}
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})
        return shared.get("target_temperature")

    @property
    def hvac_mode(self):
        data = self.coordinator.data or {}
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})
        if shared.get("hvac_heater_state"):
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

    async def async_set_temperature(self, **kwargs):
        """Set target temperature via API."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        url = f"{self.coordinator.api_url.replace('/status', '/temperature')}"
        headers = {"Authorization": f"Bearer {self.coordinator.api_key}"}
        json_data = {"value": temperature, "mode": HVAC_MODE_HEAT, "scale": "C"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    _LOGGER.error("Erreur API NLE set_temperature: HTTP %s", resp.status)
                await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode via API."""
        url = f"{self.coordinator.api_url.replace('/status', '/mode')}"
        headers = {"Authorization": f"Bearer {self.coordinator.api_key}"}
        json_data = {"mode": hvac_mode}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    _LOGGER.error("Erreur API NLE set_hvac_mode: HTTP %s", resp.status)
                await self.coordinator.async_request_refresh()

    async def async_update(self):
        """Request coordinator to update data."""
        await self.coordinator.async_request_refresh()
