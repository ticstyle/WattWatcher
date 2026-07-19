"""Sensor platform for WattWatcher integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfPower
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN

MAX_STATES = 6


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

    # Calculate active unique IDs to clean up orphaned entities
    active_unique_ids: set[str] = {
        f"{config_entry.entry_id}_state_sensor",
        f"{config_entry.entry_id}_current_power_diagnostic",
    }

    for state_item in states:
        if state_item["max_watt"] != float("inf"):
            active_unique_ids.add(
                f"{config_entry.entry_id}_limit_{state_item['name'].lower()}"
            )

    # Purge any obsolete entities left behind from a reconfiguration
    entity_reg = er.async_get(hass)
    existing_entries = er.async_entries_for_config_entry(
        entity_reg, config_entry.entry_id
    )
    for entity_entry in existing_entries:
        if entity_entry.unique_id not in active_unique_ids:
            entity_reg.async_remove(entity_entry.entity_id)

    main_sensor = WattWatcherSensor(
        config_entry.entry_id,
        name,
        power_sensor,
        states,
        suggested_object_id,
    )

    entities: list[SensorEntity] = [main_sensor]

    entities.append(
        WattWatcherPowerSensor(
            config_entry.entry_id, name, suggested_object_id, main_sensor
        )
    )

    for state_item in states:
        if state_item["max_watt"] != float("inf"):
            state_slug = state_item["name"].lower().replace(" ", "_").replace("-", "_")
            entities.append(
                WattWatcherStateLimitSensor(
                    config_entry.entry_id,
                    name,
                    state_item["name"],
                    state_item["max_watt"],
                    f"{suggested_object_id}_{state_slug}_limit",
                )
            )

    async_add_entities(entities)


class WattWatcherSensor(RestoreEntity, SensorEntity):
    """Representation of the main state classifier sensor."""

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
        self.current_power: float | None = None
        self.source_power: float | None = None
        self._power_history: list[tuple[float, float]] = []
        self._listeners: list[Any] = []

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
        """Handle entity registry lifecycle hooks and restore previous state."""
        await super().async_added_to_hass()

        if last_state := await self.async_get_last_state():
            self._state_value = last_state.state
            # Seed the tracking window with restored data to keep baseline history stable
            if "source_power" in last_state.attributes:
                saved_power = last_state.attributes["source_power"]
                if saved_power is not None:
                    self._power_history = [
                        (dt_util.utcnow().timestamp(), float(saved_power))
                    ]

        if initial_state := self.hass.states.get(self._power_sensor):
            self._update_power_state(initial_state.state, use_debounce=False)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._power_sensor], self._handle_state_change
            )
        )

    def register_power_listener(self, callback_func: Any) -> Any:
        """Register secondary entities to track moving average mutations."""
        self._listeners.append(callback_func)
        return lambda: self._listeners.remove(callback_func)

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Process event updates broadcasted from the monitored sensor."""
        if (new_state := event.data.get("new_state")) is not None:
            self._update_power_state(new_state.state, use_debounce=True)

    def _update_power_state(self, raw_state: str, use_debounce: bool) -> None:
        """Evaluate the raw state value against thresholds using a 30s rolling window."""
        if raw_state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self.current_power = None
            self.source_power = None
            self._power_history.clear()
            self._notify_listeners()
            self.async_write_ha_state()
            return

        try:
            power_val = float(raw_state)
            self.source_power = power_val
        except ValueError:
            self.current_power = None
            self.source_power = None
            self._power_history.clear()
            self._notify_listeners()
            self.async_write_ha_state()
            return

        now = dt_util.utcnow().timestamp()

        if not use_debounce:
            # Immediate baseline parsing during initial bootup setups
            mean_power = power_val
            self._power_history = [(now, power_val)]
        else:
            cutoff = now - 30
            # Split window data arrays into expired frames and valid active frames
            expired = [item for item in self._power_history if item[0] < cutoff]
            active = [item for item in self._power_history if item[0] >= cutoff]

            # Safety Lock: Retain the last known value if the active window is completely empty
            if not active and expired:
                active.append((cutoff, expired[-1][1]))

            active.append((now, power_val))
            self._power_history = active

            # Evaluate rolling average across the active time array explicitly
            mean_power = sum(w for _, w in self._power_history) / len(
                self._power_history
            )

        self.current_power = round(mean_power, 2)
        self._notify_listeners()

        target_state: str | None = None
        if mean_power == 0.0:
            target_state = "Off"
        else:
            for state_item in self._states:
                if mean_power <= state_item["max_watt"]:
                    target_state = state_item["name"]
                    break
            if target_state is None and self._states:
                target_state = self._states[-1]["name"]

        self._state_value = target_state
        self.async_write_ha_state()

    def _notify_listeners(self) -> None:
        """Trigger update updates across subordinate diagnostic entities."""
        for listener in self._listeners:
            listener()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return optional telemetry data elements inside the state envelope."""
        state_map: dict[str, str] = {}
        for state_item in self._states:
            max_watt_str = (
                "Infinite"
                if state_item["max_watt"] == float("inf")
                else f"{state_item['max_watt']} W"
            )
            state_map[state_item["name"]] = max_watt_str

        return {
            "current_power": self.current_power,
            "source_power": self.source_power,
            "power_unit": UnitOfPower.WATT,
            "source_entity": self._power_sensor,
            "configured_states": state_map,
        }


class WattWatcherPowerSensor(SensorEntity):
    """Subordinate entity rendering current smoothed numerical usage explicitly."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        entry_id: str,
        device_name: str,
        parent_slug: str,
        main_sensor: WattWatcherSensor,
    ) -> None:
        """Initialize the power diagnostic view."""
        self._main_sensor = main_sensor
        self.entity_id = f"sensor.{parent_slug}_current_power"
        self._attr_name = "Current Power"
        self._attr_unique_id = f"{entry_id}_current_power_diagnostic"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=device_name,
            manufacturer="ticstyle",
            model="WattWatcher",
        )

    @property
    def native_value(self) -> float | None:
        """Return raw native numerical data bound to upstream moving averages."""
        return self._main_sensor.current_power

    async def async_added_to_hass(self) -> None:
        """Bind hooks watching mutations occurring on master state containers."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._main_sensor.register_power_listener(self.async_write_ha_state)
        )


class WattWatcherStateLimitSensor(SensorEntity):
    """Static descriptive locked sensor showing thresholds for explicit configurations."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        entry_id: str,
        device_name: str,
        state_label: str,
        limit_watt: float,
        suggested_object_id: str,
    ) -> None:
        """Initialize fixed configuration tracker entities."""
        self.entity_id = f"sensor.{suggested_object_id}"
        self._attr_name = f"State Limit {state_label}"
        self._attr_native_value = limit_watt
        self._attr_unique_id = f"{entry_id}_limit_{state_label.lower()}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=device_name,
            manufacturer="ticstyle",
            model="WattWatcher",
        )
