"""NLE Thermostat climate platform (YAML-based)."""
import logging
from datetime import timedelta
import aiohttp

from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)

# Constantes maison pour le thermostat
HVAC_MODE_HEAT = "heat"
HVAC_MODE_OFF = "off"
SUPPORT_TARGET_TEMPERATURE = 1  # bitmask
TEMP_CELSIUS = "°C"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup YAML-based NLE climate platform."""
    _LOGGER.info("NLE Thermostat climate async_setup_platform called")

    cfg = hass.data.get(DOMAIN, {})
    api_base = cfg.get(CONF_API_URL)
    api_key = cfg.get(CONF_API_KEY)
    device_id = cfg.get(CONF_DEVICE_ID)

    if not api_base or not api_key or not device_id:
        _LOGGER.error("nle_thermostat: configuration incomplète, climate non chargé")
        return

    # Construire l'URL status
    api_url = api_base.rstrip("/") + f"/thermostat/{device_id}/status"

    coordinator = NLECoordinator(hass, api_url, api_key, device_id)
    await coordinator.async_refresh()

    async_add_entities([NLEClimate(coordinator, device_id)], True)


class NLECoordinator(DataUpdateCoordinator):
    """Coordinator pour appels API NLE."""

    def __init__(self, hass, api_url, api_key, device_id):
        super().__init__(
            hass,
            _LOGGER,
            name="nle_thermostat_coordinator",
            update_interval=SCAN_INTERVAL,
        )
        self.api_url = api_url
        self.api_key = api_key
        self.device_id = device_id

    async def _async_update_data(self):
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"API NLE HTTP {resp.status}")
                    return await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Erreur réseau/API NLE : {err}") from err

    async def async_set_temperature(self, temperature, mode="heat"):
        url = self.api_url.replace("/status", "/temperature")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        json_data = {"value": temperature, "mode": mode, "scale": "C"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    _LOGGER.error("Erreur set_temperature: HTTP %s", resp.status)
                return await resp.json()

    async def async_set_mode(self, mode: str):
        url = self.api_url.replace("/status", "/mode")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        json_data = {"mode": mode}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    _LOGGER.error("Erreur set_mode: HTTP %s", resp.status)
                return await resp.json()


class NLEClimate(ClimateEntity):
    """Entité climate pour le thermostat NLE."""

    def __init__(self, coordinator: NLECoordinator, device_id: str):
        self.coordinator = coordinator
        self.device_id = device_id
        self._attr_hvac_modes = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
        self._attr_supported_features = SUPPORT_TARGET_TEMPERATURE

    @property
    def name(self) -> str:
        return f"NLE {self.device_id[:8]}"

    @property
    def unique_id(self) -> str:
        return f"nle_{self.device_id[:8]}_climate"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def temperature_unit(self) -> str:
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
    def hvac_modes(self):
        return self._attr_hvac_modes

    @property
    def hvac_mode(self):
        data = self.coordinator.data or {}
        shared = data.get("state", {}).get(f"shared.{self.device_id}", {}).get("value", {})
        if shared.get("hvac_heater_state"):
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def supported_features(self):
        return self._attr_supported_features

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get("temperature")
        if temp is None:
            return
        await self.coordinator.async_set_temperature(temp, HVAC_MODE_HEAT)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: str):
        mode = HVAC_MODE_HEAT if hvac_mode == HVAC_MODE_HEAT else "off"
        await self.coordinator.async_set_mode(mode)
        await self.coordinator.async_request_refresh()

    async def async_update(self):
        await self.coordinator.async_request_refresh()
