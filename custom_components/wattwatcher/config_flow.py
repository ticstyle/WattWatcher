"""Config flow for WattWatcher integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

# Number of fixed mode slots in the GUI
MAX_MODES = 6


def validate_modes(user_input: dict[str, Any]) -> str | None:
    """Validate that configured modes are in strictly ascending order.

    Returns an error key if invalid, otherwise None.
    """
    last_watt = -1.0

    for i in range(1, MAX_MODES + 1):
        # Flattened check because section fields are unpacked into the root input dict
        name_key = f"mode_{i}_name"
        watt_key = f"mode_{i}_max_watt"

        name = user_input.get(name_key)
        watt = user_input.get(watt_key)

        # If both are filled, validate the threshold sequence
        if name and watt is not None:
            current_watt = float(watt)
            if current_watt <= last_watt:
                return "overlapping_thresholds"
            last_watt = current_watt

    return None


def create_schema(
    hass: HomeAssistant,
    defaults: dict[str, Any] | None = None,
    is_reconfigure: bool = False,
) -> vol.Schema:
    """Create the configuration schema with optional default values."""
    defaults = defaults or {}
    schema: dict[vol.Marker, Any] = {}

    # Device name is only needed during initial setup
    if not is_reconfigure:
        schema[vol.Required("name", default=defaults.get("name", ""))] = cv.string

    # Source power sensor selection
    schema[vol.Required("power_sensor", default=defaults.get("power_sensor", ""))] = (
        selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )
    )

    # Dynamic generation of the 6 fixed mode fields inside visual layout sections
    for i in range(1, MAX_MODES + 1):
        name_key = f"mode_{i}_name"
        watt_key = f"mode_{i}_max_watt"

        # Build number selector configuration for float input
        num_config = selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX,
            step="any",
            unit_of_measurement="W",
        )

        sub_fields: dict[vol.Marker, Any] = {
            vol.Optional(name_key, default=defaults.get(name_key, "")): cv.string
        }

        default_watt = defaults.get(watt_key)
        if default_watt is not None:
            sub_fields[vol.Optional(watt_key, default=float(default_watt))] = (
                selector.NumberSelector(num_config)
            )
        else:
            sub_fields[vol.Optional(watt_key)] = selector.NumberSelector(num_config)

        # Bind using the core framework section layout to handle grouping and collapse behaviors
        schema[vol.Optional(f"mode_{i}_section")] = section(
            vol.Schema(sub_fields),
            {
                "collapsed": i > 3
            },  # Expand the first 3 by default, keep higher entries clean
        )

    return vol.Schema(schema)


class WattWatcherConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WattWatcher."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate that thresholds do not overlap
            if error := validate_modes(user_input):
                errors["base"] = error
            else:
                title = user_input["name"]

                return self.async_create_entry(
                    title=title,
                    data=user_input,
                    options=user_input,  # Duplicate to options to make reconfigure seamless
                )

        return self.async_show_form(
            step_id="user",
            data_schema=create_schema(self.hass, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            # Validate that thresholds do not overlap
            if error := validate_modes(user_input):
                errors["base"] = error
            else:
                # Merge new configuration details into the existing entry
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, **user_input},
                    options={**entry.options, **user_input},
                )

        # Pre-populate the GUI with the current configurations
        current_config = {**entry.data, **entry.options}

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=create_schema(self.hass, current_config, is_reconfigure=True),
            errors=errors,
        )


class WattWatcherOptionsFlow(OptionsFlow):
    """Handle options flow changes, mirroring the reconfigure flow behavior."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the configuration options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if error := validate_modes(user_input):
                errors["base"] = error
            else:
                return self.async_create_entry(title="", data=user_input)

        current_config = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=create_schema(self.hass, current_config, is_reconfigure=True),
            errors=errors,
        )
