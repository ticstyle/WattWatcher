class WattWatcherSensor(SensorEntity):
    """Representation of a WattWatcher power mode sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        name: str,
        power_sensor: str,
        modes: list[dict[str, Any]],
        suggested_object_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._power_sensor = power_sensor
        self._modes = modes
        self._attr_suggested_object_id = suggested_object_id
        
        self._attr_state: str | None = None
        self._current_power: float | None = None

        # Build the shared device identity block
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="ticstyle",
            model="WattWatcher",
        )
        
        # Unique ID based on the entry ID ensures uniqueness across multiple instances
        self._attr_unique_id = f"{entry_id}_mode_sensor"

    @property
    def name(self) -> str | None:
        """Return None to force the entity to inherit the Device name directly."""
        return None

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
        """Evaluate the raw state value against the sorted mode thresholds."""
        if state_value in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._attr_state = None
            self._current_power = None
            return

        try:
            power_val = float(state_value)
            self._current_power = power_val
        except ValueError:
            self._attr_state = None
            self._current_power = None
            return

        # Map the power signature to the appropriate target operational mode
        for mode in self._modes:
            if power_val <= mode["max_watt"]:
                self._attr_state = mode["name"]
                return

        # Default to the absolute highest configured mode if it exceeds all intermediate steps
        if self._modes:
            self._attr_state = self._modes[-1]["name"]
        else:
            self._attr_state = None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return optional telemetry data elements inside the state envelope."""
        return {
            "current_power": self._current_power,
            "power_unit": UnitOfPower.WATT,
        }
