"""Sensor platform for WattWatcher integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfPower
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_call_later

from .const import DOMAIN

MAX_STATES = 6
# 5 seconds delay stabilizes quick power oscillations perfectly
FLUCTUATION_DELAY = 5


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WattWatcher sensor platform."""
    config = {**config_entry.data, **config_entry.options}
    
    name: str = config["name"]
    power_sensor: str = config["power_sensor"]
    
    states = []
    for i in range(1, MAX_STATES + 1):
        state_name = config.get(f"state_{i}_name")
        state_watt = config.get(f"state_{i}_max_watt")
        
        if state_name:
            val_watt = float(state_watt) if state_watt is not None else float("inf")
            states.append({"name": state_name, "max_watt": val_watt})

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
    """Representation of a WattWatcher power state sensor with debouncing stabilization."""

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
        
        self.entity_id = f"sensor.{suggested_object_id}"
        self._attr_name = ""
        self._state_value: str | None = None
        self._pending_state_value: str | None = None
        self._current_power: float | None = None
        self._debounce_unsub: Any = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="ticstyle",
            model="WattWatcher",
        )
        self._attr_unique_id = f"{entry_id}_state_sensor"

    @property
    def native_value(self) -> str | None:
        """Return the current calculated operational state."""
        return self._state_value

    async def async_added_to_hass(self) -> None:
        """Handle entity registry lifecycle hooks."""
        await super().async_added_to_hass()

        if initial_state := self.hass.states.get(self._power_sensor):
            # Parse target layout immediately on startup without debounce delay
            self._update_power_state(initial_state.state, use_debounce=False)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._power_sensor], self._handle_state_change
            )
        )

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Process event updates broadcasted from the monitored sensor."""
        if (new_state := event.data.get("new_state")) is not None:
            self._update_power_state(new_state.state, use_debounce=True)

    def _update_power_state(self, raw_state: str, use_debounce: bool) -> None:
        """Evaluate the raw state value against thresholds with optional debouncing."""
        if raw_state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._cancel_debounce()
            self._state_value = None
            self._current_power = None
            self.async_write_ha_state()
            return

        try:
            power_val = float(raw_state)
            self._current_power = power_val
        except ValueError:
            self._cancel_debounce()
            self._state_value = None
            self._current_power = None
            self.async_write_ha_state()
            return

        # Determine target state matching the power signature
        target_state: str | None = None
        if power_val == 0.0:
            target_state = "Off"
        else:
            for state_item in self._states:
                if power_val <= state_item["max_watt"]:
                    target_state = state_item["name"]
                    break
            if target_state is None and self._states:
                target_state = self._states[-1]["name"]

        if not use_debounce:
            self._cancel_debounce()
            self._state_value = target_state
            self.async_write_ha_state()
            return

        # Debounce evaluation logic block
        if target_state == self._state_value:
            self._cancel_debounce()
            return

        if target_state == self._pending_state_value:
            # Already waiting for this specific state to commit
            return

        self._cancel_debounce()
        self._pending_state_value = target_state
        
        # Fire delayed state switch execution hook
        self._debounce_unsub = async_call_later(
            self.hass,
            timedelta(seconds=FLUCTUATION_DELAY),
            self._async_commit_state
        )

    async def _async_commit_state(self, _now: Any) -> None:
        """Commit the verified stable state update onto the entity platform."""
        self._state_value = self._pending_state_value
        self._pending_state_value = None
        self._debounce_unsub = None
        self.async_write_ha_state()

    def _cancel_debounce(self) -> None:
        """Safely clear outstanding state change timers."""
        if self._debounce_unsub:
            self._debounce_unsub()
            self._debounce_unsub = None
        self._pending_state_value = None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return optional telemetry data elements inside the state envelope."""
        return {
            "current_power": self._current_power,
            "power_unit": UnitOfPower.WATT,
            "configured_states": self._states,
        }
