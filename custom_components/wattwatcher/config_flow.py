"""Config flow for WattWatcher integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

MAX_STATES = 6
DEFAULT_STATES = ["Standby", "Idle", "Running", "Gaming", "Working", "Going", "On"]


def validate_states(user_input: dict[str, Any]) -> str | None:
    """Validate that configured states are in strictly ascending order.

    Returns an error key if invalid, otherwise None.
    """
    last_watt = -1.0

    for i in range(1, MAX_STATES + 1):
        name = user_input.get(f"state_{i}_name")
        watt = user_input.get(f"state_{i}_max_watt")

        if name and watt is not None:
            current_watt = float(watt)
            if current_watt <= last_watt:
                return "overlapping_thresholds"
            last_watt = current_watt

    return None


def flatten_section_input(user_input: dict[str, Any] | None) -> dict[str, Any]:
    """Extract and flatten data fields packed inside UI layout sections."""
    if not user_input:
        return {}

    flat_data = {}
    for key, value in user_input.items():
        if key.endswith("_section") and isinstance(value, dict):
            flat_data.update(value)
        else:
            flat_data[key] = value

    return flat_data


def create_state_fields(i: int, defaults: dict[str, Any]) -> dict[vol.Marker, Any]:
    """Helper to generate standard schema fields for a single state section."""
    name_key = f"state_{i}_name"
    watt_key = f"state_{i}_max_watt"

    # Configure default values specifically for State 1 on first startup
    default_name = defaults.get(name_key, "Standby" if i == 1 else "")
    default_watt = defaults.get(watt_key)
    if default_watt is None and i == 1:
        default_watt = 5.0

    num_config = selector.NumberSelectorConfig(
        mode=selector.NumberSelectorMode.BOX,
        step="any",
        unit_of_measurement="W",
    )

    name_config = selector.SelectSelectorConfig(
        options=DEFAULT_STATES,
        custom_value=True,
        mode=selector.SelectSelectorMode.DROPDOWN,
    )

    sub_fields: dict[vol.Marker, Any] = {
        vol.Optional(name_key, default=default_name): selector.SelectSelector(
            name_config
        )
    }

    if default_watt is not None:
        sub_fields[vol.Optional(watt_key, default=float(default_watt))] = (
            selector.NumberSelector(num_config)
        )
    else:
        sub_fields[vol.Optional(watt_key)] = selector.NumberSelector(num_config)

    return {
        vol.Optional(f"state_{i}_section"): section(
            vol.Schema(sub_fields), {"collapsed": False}
        )
    }


class WattWatcherConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WattWatcher."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the progressive config flow instance."""
        self._accumulated_data: dict[str, Any] = {}
        self._current_setup_index = 3

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step (Device, Sensor, State 1 & 2)."""
        errors: dict[str, str] = {}
        flat_input = flatten_section_input(user_input)

        if user_input is not None:
            self._accumulated_data.update(flat_input)

            # If the user wants to add more states, route to the dynamic sub-step
            if flat_input.get("add_more_states"):
                return await self.async_step_add_state()

            if error := validate_states(self._accumulated_data):
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=self._accumulated_data["name"],
                    data=self._accumulated_data,
                    options=self._accumulated_data,
                )

        schema: dict[vol.Marker, Any] = {
            vol.Required("name", default=flat_input.get("name", "")): cv.string,
            vol.Required(
                "power_sensor", default=flat_input.get("power_sensor", "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
        }

        # Populate only State 1 and State 2 initially
        schema.update(create_state_fields(1, flat_input))
        schema.update(create_state_fields(2, flat_input))

        # Toggle checkbox allowing progression to State 3
        schema[vol.Optional("add_more_states", default=False)] = cv.boolean

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_add_state(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Progressive sub-step to add higher operational states one by one."""
        errors: dict[str, str] = {}
        flat_input = flatten_section_input(user_input)
        idx = self._current_setup_index

        if user_input is not None:
            self._accumulated_data.update(flat_input)

            if flat_input.get("add_more_states") and idx < MAX_STATES:
                self._current_setup_index += 1
                return await self.async_step_add_state()

            if error := validate_states(self._accumulated_data):
                errors["base"] = error
            else:
                # Cleanup the structural checkbox control flag before saving data
                self._accumulated_data.pop("add_more_states", None)
                return self.async_create_entry(
                    title=self._accumulated_data["name"],
                    data=self._accumulated_data,
                    options=self._accumulated_data,
                )

        schema = create_state_fields(idx, flat_input)

        # Append downstream checkbox if there are remaining slots left
        if idx < MAX_STATES:
            schema[vol.Optional("add_more_states", default=False)] = cv.boolean

        return self.async_show_form(
            step_id="add_state",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={"index": str(idx)},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration. Displays all fields at once for easy adjustments."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        flat_input = flatten_section_input(user_input)

        if user_input is not None:
            if error := validate_states(flat_input):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, **flat_input},
                    options={**entry.options, **flat_input},
                )

        current_config = {**entry.data, **entry.options}
        schema: dict[vol.Marker, Any] = {
            vol.Required(
                "power_sensor", default=current_config.get("power_sensor", "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            )
        }

        for i in range(1, MAX_STATES + 1):
            schema.update(create_state_fields(i, current_config))

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(schema),
            errors=errors,
        )


class WattWatcherOptionsFlow(OptionsFlow):
    """Handle options flow changes, mirroring reconfigure layout behavior."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the configuration options."""
        errors: dict[str, str] = {}
        flat_input = flatten_section_input(user_input)

        if user_input is not None:
            if error := validate_states(flat_input):
                errors["base"] = error
            else:
                return self.async_create_entry(title="", data=flat_input)

        current_config = {**self.config_entry.data, **self.config_entry.options}
        schema: dict[vol.Marker, Any] = {
            vol.Required(
                "power_sensor", default=current_config.get("power_sensor", "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            )
        }

        for i in range(1, MAX_STATES + 1):
            schema.update(create_state_fields(i, current_config))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
