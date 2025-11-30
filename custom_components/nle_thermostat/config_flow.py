import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_API_URL, CONF_API_KEY, CONF_DEVICE_ID

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_API_URL): str,
    vol.Required(CONF_API_KEY): str,
    vol.Required(CONF_DEVICE_ID): str,
})

class NLEThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="NLE Thermostat", data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)
