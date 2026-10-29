# Anenji Inverter Bridge

This custom Home Assistant integration connects a SmartESS Wi-Fi stick to a
local TCP bridge on Home Assistant, reads inverter values from Modbus registers,
and publishes them to an MQTT broker. It uses MQTT Discovery to create sensors
in Home Assistant.

The discovery metadata identifies the device as an Anenji ANJ-4200W. Other
inverters or stick firmware versions may use different register layouts and
have not been verified.

## Requirements

- Home Assistant with the MQTT integration configured.
- An MQTT broker reachable from Home Assistant.
- A SmartESS Wi-Fi stick reachable from the Home Assistant host over the
  network.
- The stick must be able to connect to the Home Assistant host at the
  configured TCP server port.

The integration creates its own MQTT client; configuring the Home Assistant
MQTT integration does not automatically supply this integration's broker
credentials.

## Installation with HACS

After this repository is public on GitHub:

1. In Home Assistant, open **HACS → Integrations**.
2. Open the HACS menu and choose **Custom repositories**.
3. Add `https://github.com/cdExpat/anenji_inverter` with category **Integration**.
4. Find **Anenji Inverter Bridge** in HACS and install it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration** and search for
   **Anenji Inverter Bridge**.

The integration manifest declares `paho-mqtt` as a requirement, which Home
Assistant installs for the integration.

### Manual installation

Copy the `custom_components/anenji_inverter` directory from this repository
into the `custom_components` directory in your Home Assistant configuration,
then restart Home Assistant and add the integration from **Settings →
Devices & services**.

## Configuration

Enter the following values in the setup form:

| Setting | Purpose | Default |
| --- | --- | --- |
| SmartESS Stick IP | IP address of the Wi-Fi stick receiving the UDP redirect | `192.168.138.2` |
| SmartESS UDP Port | Port used to send the redirect to the stick | `58899` |
| Local Bridge Server IP | IP address of the Home Assistant host that the stick should connect to | `192.168.1.69` |
| Local TCP Listen Port | Port on which the integration listens for the stick | `18899` |
| MQTT Broker Host | Hostname or IP address of the MQTT broker | `127.0.0.1` |
| MQTT Broker Port | MQTT broker port | `1883` |
| MQTT Username | Broker username; leave blank if not required | blank |
| MQTT Password | Broker password; leave blank if not required | blank |

Use an address for **Local Bridge Server IP** that the stick can reach. The
default MQTT host, `127.0.0.1`, refers to the Home Assistant host/container
itself; if the broker is elsewhere, enter its reachable hostname or IP.

When both MQTT username and password are provided, the integration uses them
for broker authentication.

## Sensors

The integration publishes these MQTT-discovered sensors:

| Sensor | Unit | Notes |
| --- | --- | --- |
| Anenji PV Power | W | Solar PV power |
| Anenji PV Voltage | V | Solar PV voltage |
| Anenji Battery Voltage | V | Battery voltage |
| Anenji Battery Capacity | % | Battery state of charge |
| Anenji Battery Power | W | Signed battery power |
| Anenji Battery Charge Power | W | Positive charge power; zero otherwise |
| Anenji Battery Discharge Power | W | Positive discharge power; zero otherwise |
| Anenji AC Load Power | W | AC load power; invalid register value `65535` is published as `0` |
| Anenji Grid Voltage | V | Grid voltage |

Charge and discharge sensors are calculated from the signed battery power
reading: positive battery power is treated as charging, and negative as
discharging.

The bridge publishes discovery configuration under
`homeassistant/sensor/anenji_modbus/<sensor_key>/config` and state under
`anenji_inverter/<sensor_key>/state`. Sensor values are published as readings
arrive; state messages are not retained, so a sensor may initially show
`unknown` until the stick sends data.

## Data flow

1. The integration starts an MQTT client and a background bridge thread.
2. The bridge publishes MQTT Discovery configuration for its sensors and
   listens for the stick on the configured TCP port.
3. While waiting for the stick, it sends a UDP redirect command to the stick
   with the configured server IP and port.
4. After the stick connects, the bridge performs its wake-up handshake and
   repeatedly requests 40 Modbus holding registers beginning at register 200.
5. Parsed readings are published to the sensor state topics.

## Troubleshooting

- **Sensors show `unknown`:** Check that the MQTT broker is reachable and the
  configured credentials are correct. Verify that the stick connects to the
  bridge and that state messages appear on `anenji_inverter/+/state`.
- **No MQTT-discovered entities:** Check that discovery configuration messages
  appear on `homeassistant/sensor/anenji_modbus/+/config` and that MQTT
  Discovery is enabled in Home Assistant.
- **Stick does not connect:** Confirm that the configured server IP is the
  Home Assistant host address reachable by the stick, the TCP port is
  available, and network/firewall rules permit the connection.
- **View bridge logs:** Home Assistant logs integration messages under
  `custom_components.anenji_inverter`. To show informational messages when
  the default log level is `warning`, add:

  ```yaml
  logger:
    default: warning
    logs:
      custom_components.anenji_inverter: info
  ```

  Restart Home Assistant after changing `configuration.yaml`.

Changes to the integration's Python files require a Home Assistant restart to
reliably load the updated code.
