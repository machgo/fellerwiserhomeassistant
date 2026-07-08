"""Config flow for Feller Wiser integration."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_APIKEY = "apikey"
CONF_HOST = "host"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_APIKEY): str,
    }
)


def _normalize_host(host: str) -> str:
    """Normalize user-entered host values to the host[:port] form."""
    host = host.strip().rstrip("/")
    parsed = urlparse(host if "://" in host else f"http://{host}")

    if not parsed.netloc:
        raise CannotConnect

    return parsed.netloc


def _validate_api(host: str, apikey: str) -> dict[str, Any]:
    """Validate credentials against the Feller Wiser API."""
    try:
        response = requests.get(
            f"http://{host}/api/loads",
            headers={"authorization": f"Bearer {apikey}"},
            timeout=10,
        )
    except requests.RequestException as err:
        raise CannotConnect from err

    if response.status_code in (401, 403):
        raise InvalidAuth

    try:
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as err:
        raise CannotConnect from err

    if payload.get("status") not in (None, "success") or "data" not in payload:
        raise CannotConnect

    return payload


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = _normalize_host(data[CONF_HOST])
    await hass.async_add_executor_job(_validate_api, host, data[CONF_APIKEY].strip())

    return {"host": host, "title": f"Feller Wiser ({host})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Feller Wiser."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            user_input[CONF_HOST] = _normalize_host(user_input[CONF_HOST])
        except CannotConnect:
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        await self.async_set_unique_id(user_input[CONF_HOST])
        self._abort_if_unique_id_configured()

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            user_input[CONF_HOST] = info["host"]
            user_input[CONF_APIKEY] = user_input[CONF_APIKEY].strip()
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
