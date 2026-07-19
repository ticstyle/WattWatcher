# WattWatcher

<p align="center">
  <img src="https://raw.githubusercontent.com/ticstyle/WattWatcher/main/custom_components/wattwatcher/brand/logo.png" alt="WattWatcher Logo" width="800" />
</p>

![Latest Release](https://img.shields.io/github/release/ticstyle/WattWatcher?color=blue&label=Release)
![Last Updated](https://img.shields.io/github/last-commit/ticstyle/WattWatcher?path=hacs.json&label=Maintained)
![Issues](https://img.shields.io/github/issues/ticstyle/WattWatcher?color=orange&label=Issues)
![Custom Integration](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-blue?logo=home-assistant)
![Home Assistant Required Version](https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/ticstyle/WattWatcher/main/hacs.json&query=%24.homeassistant&suffix=%2B&label=Home%20Assistant&logo=homeassistant)

![License](https://img.shields.io/github/license/ticstyle/WattWatcher?label=License)
[![Hassfest](https://img.shields.io/github/actions/workflow/status/ticstyle/WattWatcher/pipeline.yml?branch=main&label=Hassfest)](https://github.com/ticstyle/WattWatcher/actions/workflows/pipeline.yml)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/ticstyle/WattWatcher/pipeline.yml?branch=main&label=HACS)](https://github.com/ticstyle/WattWatcher/actions/workflows/pipeline.yml)
[![Ruff / Format](https://img.shields.io/github/actions/workflow/status/ticstyle/WattWatcher/pipeline.yml?branch=main&label=Ruff%20%2F%20Format)](https://github.com/ticstyle/WattWatcher/actions/workflows/pipeline.yml)
[![Mypy](https://img.shields.io/github/actions/workflow/status/ticstyle/WattWatcher/pipeline.yml?branch=main&label=Mypy)](https://github.com/ticstyle/WattWatcher/actions/workflows/pipeline.yml)
![Installs](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=Known%20installs&url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.wattwatcher.total)


An asynchronous Home Assistant custom integration that tracks the real-time power consumption of a device and cleanly translates raw watt data into distinct operational states. It dynamically monitors power signatures—allowing you to easily identify when a system transitions between custom states like Standby, Idle, or Gaming.

To add this integration, please add the custom repository `https://github.com/ticstyle/WattWatcher/` to HACS in your Home Assistant setup.

## 🌐 Supported Languages
This integration is written and maintained exclusively in **English**. All entity states, attributes, configuration dialogues, and logging diagnostic files use English standards.

## ✨ Features
* **6 Fixed Operational State Slots:** Tweak and define up to 6 custom states inside the User Interface, instantly dividing your device's power footprint into easily readable operational zones.
* **Time-Windowed Moving Average:** Utilizes a robust 30-second sliding time-window algorithm to calculate power draw. This entirely neutralizes brief, temporary power spikes or drops—even if a fluctuation includes consecutive updates—preventing rapid, flickering state changes.
* **Safety Lock Fallback Architecture:** Built-in safeguards gracefully handle periods of perfectly constant consumption. If the source entity doesn't report any new data over a 30-second period, the logic locks onto the last known baseline rather than wiping the moving window.
* **Automatic Multi-Sensor Provisioning:** Spins up a complete, uniform diagnostic package under a single device registry layer—instantly spawning your main state classifier, an explicit real-time power monitor entity, and read-only limits for each configured threshold.
* **Seamless Restart State Persistence:** Fully backs up active structural states and numerical baseline histories via native state restoration. Your entities remain completely stable through Home Assistant reboots or integration reloads without dropping to an "unknown" or "Off" state for a single second.
* **Strict Validation Guardrails:** Protects state evaluation logic by checking structural constraints. The configuration flow automatically enforces a strict, ascending watt threshold order to guarantee boundaries never overlap or misfire.
* **Full Reconfigure & Options Support:** Swap out the underlying source power sensor or fine-tune your target watt limits instantly through the native Home Assistant user interface without touching YAML files.
* **Clean Native UI Attribute Layouts:** Maps your configured thresholds using structural dictionary envelopes rather than raw list brackets, yielding highly legible, clutter-free telemetry details in the front end.

## 🚀 Installation

[![](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ticstyle&repository=WattWatcher&category=Integration)

Via [HACS](https://hacs.xyz/) or manually copy the `wattwatcher` folder from the [latest release](https://github.com/ticstyle/WattWatcher/releases/latest) to the `custom_components` folder inside your Home Assistant configuration directory.

## ⚙️ Configuration

[![](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wattwatcher)

Add and adjust the integration via the Home Assistant User Interface. The setup step can be run multiple times to spin up separate mirrored entity layers for different appliances, and existing entries can be fully tweaked on the fly using the native **Reconfigure** and **Options** flow.

During setup or reconfiguration, you will be prompted to provide:
1. **Device Name:** A descriptive name used to build the parent device structure and object ID (e.g., `Stoffe-PC`).
2. **Source Power Sensor:** An existing `sensor` entity monitoring power consumption in pure Watts (`W`).
3. **States 1 to 6 (Optional):** Pairs of custom names and their corresponding maximum watt boundaries configured in strictly ascending order (e.g., State 1: `Standby` up to `5W`, State 2: `Idle` up to `200W`, State 3: `Gaming` up to `Infinite`).

---

## 📊 Available Entities
When parsing your selected source power entity, the integration registers a unified device map containing distinct diagnostic tracking viewpoints:

| Entity ID | Name in UI | State Example | Description |
| :--- | :--- | :--- | :--- |
| `sensor.wattwatcher_stoffe_pc` | Stoffe-PC | `Gaming` | The current matching operational state based on the 30-second moving average. |
| `sensor.wattwatcher_stoffe_pc_current_power` | Stoffe-PC Current Power | `311.75 W` | The smoothed, time-windowed numerical watt level currently being calculated. |
| `sensor.wattwatcher_stoffe_pc_standby_limit` | Stoffe-PC State Limit Standby | `5.0 W` | Static, read-only entity showing the upper watt boundary configured for this state. |

> **Note:** Dynamic boundary threshold sensors are automatically provisioned for all values except for the final trailing catch-all threshold (which behaves as an infinite fallback boundary).

### Entity Attributes
The core state sensor entity exposes advanced telemetry parameters for historical tracking and effortless debugging:

* `current_power`: The smoothed, time-windowed moving average wattage currently applied to evaluate states.
* `source_power`: The raw, un-smoothed numerical watt reading last broadcasted by the source monitor hardware.
* `power_unit`: The uniform unit of validation deployed across entities (`W`).
* `source_entity`: The underlying tracking entity target assigned during configuration.
* `configured_states`: A clean Nyckel-Värde object structure displaying user-defined thresholds natively.

---

## 💡 Lovelace Dashboard Example

Because calculated parameters are exposed cleanly to the event bus, you can easily design contextual dashboards using native Markdown tools without complicated layout configurations.

```yaml
type: markdown
title: WattWatcher Devices
content: >-
  {% set sensors = states.sensor 
     | selectattr('entity_id', 'search', '^sensor\\.wattwatcher_') 
     | rejectattr('entity_id', 'search', '_(current_power|limit)$')
     | list %}
  {% if sensors | length > 0 %}
    {% for sensor in sensors %}
      ### 🔌 {{ device_attr(sensor.entity_id, 'name') }}
      * **Current State:** `{{ sensor.state }}`
      * **Smoothed Power Draw:** `{{ state_attr(sensor.entity_id, 'current_power') }} W`
      * **Source Entity Link:** `{{ state_attr(sensor.entity_id, 'source_entity') }}`
      
      ---
    {% endfor %}
  {% else %}
    No active WattWatcher sensor mirrors detected in the system entity registry.
  {% endif %}
```
