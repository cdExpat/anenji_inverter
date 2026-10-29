import logging
import threading
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_STICK_IP,
    CONF_STICK_PORT,
    CONF_SERVER_IP,
    CONF_SERVER_PORT,
    CONF_MQTT_HOST,
    CONF_MQTT_PORT,
    CONF_MQTT_USER,
    CONF_MQTT_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)

def _setup_mqtt_client(config):
    """Synchronous helper run in executor thread to prevent blocking event loop."""
    import paho.mqtt.client as mqtt

    mqtt_host = config.get(CONF_MQTT_HOST)
    mqtt_port = config.get(CONF_MQTT_PORT)
    mqtt_user = config.get(CONF_MQTT_USER)
    mqtt_pass = config.get(CONF_MQTT_PASSWORD)

    client = mqtt.Client(client_id="anenji_hacs_bridge")
    if mqtt_user and mqtt_pass:
        client.username_pw_set(mqtt_user, mqtt_pass)

    try:
        client.connect(mqtt_host, mqtt_port, 60)
        client.loop_start()
    except Exception as e:
        _LOGGER.error("Failed to connect paho-mqtt client: %s", e)

    return client


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Anenji Inverter from UI config entry."""
    config = entry.data

    # Offload blocking MQTT client initialization to executor thread pool
    client = await hass.async_add_executor_job(_setup_mqtt_client, config)

    # Import thread starter dynamically inside async_setup_entry
    from .inverter_bridge import start_inverter_bridge_thread

    hass.data.setdefault(DOMAIN, {})

    stop_event = threading.Event()
    bridge_thread = threading.Thread(
        target=start_inverter_bridge_thread,
        args=(config, client, stop_event),
        daemon=True,
    )
    bridge_thread.start()

    hass.data[DOMAIN][entry.entry_id] = {
        "mqtt_client": client,
        "stop_event": stop_event,
        "thread": bridge_thread,
    }

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration and stop background bridge thread."""
    data = hass.data[DOMAIN].pop(entry.entry_id)
    data["stop_event"].set()

    # Stop MQTT loop safely in executor
    def _stop_mqtt():
        data["mqtt_client"].loop_stop()
        data["mqtt_client"].disconnect()

    await hass.async_add_executor_job(_stop_mqtt)
    return True
