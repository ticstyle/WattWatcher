# WattWatcher

<p align="center">
  <img src="https://github.com/ticstyle/WattWatcher/blob/main/custom_components/wattwatcher/brand/logo.png" alt="WattWatcher Logo" width="800" />
</p>

![Latest Release](https://img.shields.io/github/v/release/ticstyle/WattWatcher?color=blue&label=Release)
![Last Updated](https://img.shields.io/github/last-commit/ticstyle/WattWatcher?path=hacs.json&label=Maintained)
![Issues](https://img.shields.io/github/issues/ticstyle/WattWatcher?color=orange&label=Issues)
![Custom Integration](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-blue?logo=home-assistant)
![Home Assistant Required Version](https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/ticstyle/WattWatcher/main/hacs.json&query=%24.homeassistant&suffix=%2B&label=Home%20Assistant&logo=homeassistant)

![License](https://img.shields.io/github/license/ticstyle/WattWatcher?label=License)
[![Hassfest](https://img.shields.io/github/actions/workflow/status/ticstyle/WattWatcher/pipeline.yml?branch=main&job=hassfest&label=Hassfest)](https://github.com/ticstyle/WattWatcher/actions/workflows/pipeline.yml)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/ticstyle/WattWatcher/pipeline.yml?branch=main&job=hacs&label=HACS)](https://github.com/ticstyle/WattWatcher/actions/workflows/pipeline.yml)
[![Ruff / Format](https://img.shields.io/github/actions/workflow/status/ticstyle/WattWatcher/pipeline.yml?branch=main&job=sync_and_format&label=Ruff%20%2F%20Format)](https://github.com/ticstyle/WattWatcher/actions/workflows/pipeline.yml)
[![Mypy](https://img.shields.io/github/actions/workflow/status/ticstyle/WattWatcher/pipeline.yml?branch=main&job=mypy&label=Mypy)](https://github.com/ticstyle/WattWatcher/actions/workflows/pipeline.yml)
![Installs](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=Known%20installs&url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.WattWatcher.total)


An asynchronous Home Assistant custom integration that tracks the real-time power consumption of a device and cleanly translates raw watt data into distinct operational states. It dynamically monitors power signatures—allowing you to easily identify when a system transitions between custom states like Standby, Idle, or Gaming.

To add this integration, please add the custom repository `https://github.com/ticstyle/WattWatcher/` to HACS in your Home Assistant setup.

## 🌐 Supported Languages
This integration is written and maintained exclusively in **English**. All entity states, attributes, configuration dialogues, and logging diagnostic files use English standards.

## ✨ Features
* **6 Fixed Operational Mode Slots:** Tweak and define up to 6 custom states inside the User Interface, instantly dividing your device's power footprint into easily readable operational zones.
* **Strict Validation Guardrails:** Protects state evaluation logic by checking structural constraints. The configuration flow automatically enforces a strict, ascending watt threshold order to guarantee boundaries never overlap or misfire.
* **Predictable & Clean Object Slugs:** Automatically generates dedicated entity IDs bound cleanly to your designated configuration name for a uniform and recognizable system registry layout.
* **State Event Subscriptions:** Listens natively to real-time state mutations broadcasted from your hardware smart plug or monitor entity without heavy polling loops or performance bottlenecks.
* **Full Reconfigure & Options Support:** Swap out the underlying source power sensor or fine-tune your target watt limits instantly through the native Home Assistant user interface without touching YAML files.
* **Rich Telemetry Attributes:** Exposes raw real-time tracking data alongside your processed operational mode directly inside the entity envelope for comprehensive historical analysis.

## 🚀 Installation

[![](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ticstyle&repository=WattWatcher&category=Integration)

Via [HACS](https://hacs.xyz/) or manually copy the `wattwatcher` folder from the [latest release](https://github.com/ticstyle/WattWatcher/releases/latest) to the `custom_components` folder inside your Home Assistant configuration directory.

## ⚙️ Configuration

[![](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wattwatcher)

Add and adjust the integration via the Home Assistant User Interface. The setup step can be run multiple times to spin up separate mirrored entity layers for different appliances, and existing entries can be fully tweaked on the fly using the native **Reconfigure** and **Options** flow.

During setup or reconfiguration, you will be prompted to provide:
1. **Device Name:** A descriptive name used to build the parent device structure and object ID (e.g., `PC`).
2. **Source Power Sensor:** An existing `sensor` entity monitoring power consumption in pure Watts (`W`).
3. **Modes 1 to 6 (Optional):** Pairs of custom names and their corresponding maximum watt boundaries configured in strictly ascending order (e.g., Mode 1: `Off` up to `2W`, Mode 2: `Standby` up to `20W`, Mode 3: `Idle` up to `130W`, Mode 4: `Gaming` up to `500W`).

---

## 📊 Available Entities
When parsing your selected source power entity, the integration registers a unified device map containing a custom identifier:

| Entity ID | Name in UI | State Example | Description |
| :--- | :--- | :--- | :--- |
| `sensor.wattwatcher_pc` | PC | `Gaming` | The current matching operational mode based on real-time watt metrics. |

### Entity Attributes
The generated sensor entity exposes core parameters to track real-time telemetry:

* `current_power`: The precise numerical watt level currently being drawn by the monitored source hardware.
* `power_unit`: The unit of measurement deployed for validation (`W`).

---

## 💡 Lovelace Dashboard Example

Because calculated parameters are exposed cleanly to the event bus, you can easily design contextual dashboards using native Markdown tools without complicated layout configurations.

```yaml
type: markdown
title: WattWatcher Devices
content: >-
  {% set sensors = states.sensor 
     | selectattr('entity_id', 'search', '^sensor\\.wattwatcher_') 
     | list %}
  {% if sensors | length > 0 %}
    {% for sensor in sensors %}
      ### 🔌 {{ device_attr(sensor.entity_id, 'name') }}
      * **Current Mode:** `{{ sensor.state }}`
      * **Power Draw:** `{{ state_attr(sensor.entity_id, 'current_power') }} W`
      
      ---
    {% endfor %}
  {% else %}
    No active WattWatcher sensor mirrors detected in the system entity registry.
  {% endif %}
```
