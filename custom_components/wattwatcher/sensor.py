"""Sensor platform for WattWatcher integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfPower
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN

MAX_STATES = 6


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WattWatcher sensor platform."""
    # Combine data and options to support runtime adjustments seamlessly
    config = {**config_entry.data, **config_entry.options}
    
    name: str = config["name"]
    power_sensor: str = config["power_sensor"]
    
    # Extract and structure the configured states
    states = []
    for i in range(1, MAX_STATES + 1):
        state_name = config.get(f"state_{i}_name")
        state_watt = config.get(f"state_{i}_max_watt")
        
        if state_name:
            # If name is present but watt is omitted, default to infinity to catch all upper values
            val_watt = float(state_watt) if state_watt is not None else float("inf")
            states.append({"name": state_name, "max_watt": val_watt})

    # Generate a clean object ID slug for a predictable entity_id
    slug = name.lower().replace(" ", "_").replace("-", "_")
    suggested_object_id = f"wattwatcher_{slug}"

    async_add_entities(
        [
            WattWatcherSensor(
                config_entry.entry_id,
                name,
                power_sensor,
                states,
                suggested_object_id,
            )
        ]
    )


class WattWatcherSensor(SensorEntity):
    """Representation of a WattWatcher power state sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        name: str,
        power_sensor: str,
        states: list[dict[str, Any]],
        suggested_object_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._power_sensor = power_sensor
        self._states = states
        self._attr_suggested_object_id = suggested_object_id
        
        # Strictly force the exact entity_id layout required
        self.entity_id = f"sensor.{suggested_object_id}"
        
        # Setting a blank string forces the entity name to match the device name exactly
        self._attr_name = ""
        self._state_value: str | None = None
        self._current_power: float | None = None

        # Build the shared device identity block
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="ticstyle",
            model="WattWatcher",
        )
        
        # Unique ID based on the entry ID ensures uniqueness across multiple instances
        self._attr_unique_id = f"{entry_id}_state_sensor"

    @property
    def native_value(self) -> str | None:
        """Return the current calculated operational state."""
        return self._state_value

    async def async_added_to_hass(self) -> None:
        """Handle entity registry lifecycle hooks."""
        await super().async_added_to_hass()

        # Fetch the initial state of the source sensor right away if available
        if initial_state := self.hass.states.get(self._power_sensor):
            self._update_power_state(initial_state.state)

        # Start tracking real-time state mutations on the source power sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._power_sensor], self._handle_state_change
            )
        )

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Process event updates broadcasted from the monitored sensor."""
        if (new_state := event.data.get("new_state")) is not None:
            self._update_power_state(new_state.state)
            self.async_write_ha_state()

    def _update_power_state(self, state_value: str) -> None:
        """Evaluate the raw state value against the sorted state thresholds."""
        if state_value in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._state_value = None
            self._current_power = None
            return

        try:
            power_val = float(state_value)
            self._current_power = power_val
        except ValueError:
            self._state_value = None
            self._current_power = None
            return

        # Explicit requirement: hardcode "Off" state if consumption hits absolute zero
        if power_val == 0.0:
            self._state_value = "Off"
            return

        # Map the power signature to the appropriate target operational state
        for state_item in self._states:
            if power_val <= state_item["max_watt"]:
                self._state_value = state_item["name"]
                return

        # Default to the absolute highest configured state if it exceeds all intermediate steps
        if self._states:
            self._state_value = self._states[-1]["name"]
        else:
            self._state_value = None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return optional telemetry data elements inside the state envelope."""
        return {
            "current_power": self._current_power,
            "power_unit": UnitOfPower.WATT,
            "configured_states": self._states,
        }
