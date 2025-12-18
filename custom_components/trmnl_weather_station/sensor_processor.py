"""Sensor data processing and webhook communication."""

from __future__ import annotations

import pprint
import asyncio
import logging
from datetime import datetime

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CO2_NAME,
    CONF_CO2_SENSOR,
    CONF_DECIMAL_PLACES,
    CONF_INCLUDE_IDS,
    CONF_SENSOR_1,
    CONF_SENSOR_1_NAME,
    CONF_SENSOR_2,
    CONF_SENSOR_2_NAME,
    CONF_SENSOR_3,
    CONF_SENSOR_3_NAME,
    CONF_SENSOR_4,
    CONF_SENSOR_4_NAME,
    CONF_SENSOR_5,
    CONF_SENSOR_5_NAME,
    CONF_SENSOR_6,
    CONF_SENSOR_6_NAME,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_URL,
    CONF_WEATHER_PROVIDER,
    DEFAULT_DECIMAL_PLACES,
    MAX_PAYLOAD_SIZE,
)
from .payload_utils import create_entity_payload, estimate_payload_size, round_sensor_value

_LOGGER = logging.getLogger(__name__)


class SensorProcessor:
    """Handle sensor data processing and webhook communication."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor processor."""
        self.hass = hass
        self.entry = entry

    async def process_sensors(self, *_):
        """Process and send sensor data to TRMNL."""
        _LOGGER.debug("Starting sensor data processing")

        current_config = {**self.entry.data, **self.entry.options}
        current_url = current_config.get(CONF_URL)
        current_weather_provider = current_config.get(CONF_WEATHER_PROVIDER)
        current_sensor_1 = current_config.get(CONF_SENSOR_1)
        current_sensor_1_name = current_config.get(CONF_SENSOR_1_NAME)
        current_sensor_2 = current_config.get(CONF_SENSOR_2)
        current_sensor_2_name = current_config.get(CONF_SENSOR_2_NAME)
        current_sensor_3 = current_config.get(CONF_SENSOR_3)
        current_sensor_3_name = current_config.get(CONF_SENSOR_3_NAME)
        current_sensor_4 = current_config.get(CONF_SENSOR_4)
        current_sensor_4_name = current_config.get(CONF_SENSOR_4_NAME)
        current_sensor_5 = current_config.get(CONF_SENSOR_5)
        current_sensor_5_name = current_config.get(CONF_SENSOR_5_NAME)
        current_sensor_6 = current_config.get(CONF_SENSOR_6)
        current_sensor_6_name = current_config.get(CONF_SENSOR_6_NAME)
        include_ids = current_config.get(CONF_INCLUDE_IDS, False)
        decimal_places = current_config.get(CONF_DECIMAL_PLACES, DEFAULT_DECIMAL_PLACES)

        _LOGGER.debug("Using %d decimal places for sensor values", decimal_places)

        entities_payload = []

        weather_code = None
        if current_weather_provider:
            weather_state = self.hass.states.get(current_weather_provider)
            if weather_state:
                weather_code = weather_state.state
                _LOGGER.debug(
                    "Weather provider %s has condition: %s",
                    current_weather_provider,
                    weather_code,
                )
            else:
                _LOGGER.warning(
                    "Weather provider %s not found", current_weather_provider
                )

        weather_lang = None
        weather_lang_state = self.hass.states.get("sensor.current_weather")
        if weather_lang_state:
            weather_lang_code = weather_lang_state.state
            _LOGGER.debug(
                "Weather provider %s has condition: %s",
                "sensor.current_weather",
                weather_lang_code,
            )
        else:
            _LOGGER.warning(
                "Weather provider %s not found", "sensor.current_weather"
            )

        moon_code = None
        moon_state = self.hass.states.get("sensor.moon")
        if moon_state:
            moon_code = moon_state.state

        additional_sensors = [
            (current_sensor_1, current_sensor_1_name, "sensor_1"),
            (current_sensor_2, current_sensor_2_name, "sensor_2"),
            (current_sensor_3, current_sensor_3_name, "sensor_3"),
            (current_sensor_4, current_sensor_4_name, "sensor_4"),
            (current_sensor_5, current_sensor_5_name, "sensor_5"),
            (current_sensor_6, current_sensor_6_name, "sensor_6"),
        ]

        for sensor_id, custom_name, sensor_label in additional_sensors:
            if sensor_id and isinstance(sensor_id, str) and sensor_id.strip():
                sensor_state = self.hass.states.get(sensor_id.strip())
                _LOGGER.info("sensor state is %s", pprint.pformat(sensor_state))
                if sensor_state:
                    _LOGGER.info("sensor state id is %s", pprint.pformat(sensor_state.entity_id))
                _LOGGER.info("sensor label is %s", pprint.pformat(sensor_label))
                _LOGGER.info("sensor custom name is %s", pprint.pformat(custom_name))
                if sensor_state:
                    sensor_payload = create_entity_payload(
                        sensor_state,
                        sensor_type="r",
                        custom_name=custom_name,
                        include_id=include_ids,
                        decimal_places=decimal_places,
                    )
                    if sensor_payload:
                        entities_payload.append(sensor_payload)
                        _LOGGER.debug(
                            "Added %s: %s with name '%s' and value %s",
                            sensor_label,
                            sensor_id,
                            sensor_payload.get("n"),
                            sensor_payload.get("val"),
                        )
                else:
                    _LOGGER.warning("Sensor %s (%s) not found", sensor_label, sensor_id)

        if not entities_payload:
            _LOGGER.error("No valid sensor data to send")
            return

#        _LOGGER.info("calling weather service")
#        service_data:dict = {
#                "entity_id": current_weather_provider,
#                'type': 'daily',
#                }
#        forecast_data:dict = await self.hass.services.async_call(domain='weather', service='get_forecasts', service_data=service_data, blocking=True, return_response=True)
#        _LOGGER.info("%s", pprint.pformat(forecast_data))
#        _LOGGER.info("calling weather service")
#        forecast_data_int = forecast_data[current_weather_provider]['forecast']
        for forecast_num in range(0,8):
            my_state = self.hass.states.get("sensor.weather_forecast_daily_"+str(forecast_num))
            my_date = my_state.attributes.get("datetime", "01.01.")
            _LOGGER.info("forecast sensor state is %s", pprint.pformat(my_state))
            _LOGGER.info("forecast sensor id is %s", pprint.pformat(my_state.entity_id))
            sensor_payload = create_entity_payload(
                    my_state,
                    sensor_type="f",
                    custom_name=my_date
            )
            if sensor_payload:
                entities_payload.append(sensor_payload)
                _LOGGER.info("added %s %s", my_state, forecast_num)
            else:
                _LOGGER.error("adding values %s failed", forecast_num)

        weather_sensors = [
            ("sensor.windrichtung", "Wind-Dir", "w"),
            ("sensor.zuhause_wind_speed", "Wind-Spd", "w"),
            ("sensor.zuhause_rain", "Regen", "w"),
            ("sensor.zuhause_humidity", "Luftf.", "w"),
            ("sensor.next_sunrise", "Sunrise", "x"),
            ("sensor.next_sunset", "Sunset", "x"),
            ("sensor.zuhause_pressure", "Luft", "x"),
            ("sensor.ruediger_s_trmnl_battery_percentage", "Batt", "x"),
            ("sensor.zuhause_temperature", "Temp", "y"),
            ("sensor.minhighweekly", "Min", "y"),
            ("sensor.maxhighweekly", "Max", "y"),
        ]

        for sensor_id, custom_name, sensor_label in weather_sensors:
            if sensor_id and isinstance(sensor_id, str) and sensor_id.strip():
                sensor_state = self.hass.states.get(sensor_id.strip())
                _LOGGER.info("sensor state is %s", pprint.pformat(sensor_state))
                _LOGGER.info("sensor label is %s", pprint.pformat(sensor_label))
                _LOGGER.info("sensor custom name is %s", pprint.pformat(custom_name))
                if sensor_state:
                    _LOGGER.info("sensor state id is %s", pprint.pformat(sensor_state.entity_id))
                    sensor_payload = create_entity_payload(
                        sensor_state,
                        sensor_type=sensor_label,
                        custom_name=custom_name,
                        include_id=include_ids,
                        decimal_places=decimal_places,
                    )
                    if sensor_payload:
                        entities_payload.append(sensor_payload)
                        _LOGGER.debug(
                            "Added %s: %s with name '%s' and value %s",
                            sensor_label,
                            sensor_id,
                            sensor_payload.get("n"),
                            sensor_payload.get("val"),
                        )
                else:
                    _LOGGER.warning("Sensor %s (%s) not found", sensor_label, sensor_id)

        timestamp = datetime.now().isoformat()

        payload = {
            "merge_variables": {
                "entities": entities_payload,
                "timestamp": timestamp,
                "count": len(entities_payload),
                "wc": weather_code,
                "wl": weather_lang_code,
                "ms": moon_code,
            }
        }

        final_size = estimate_payload_size(payload)
        _LOGGER.debug(
            "Payload size: %d bytes (%d entities)", final_size, len(entities_payload)
        )

        _LOGGER.info("payload data is %s", pprint.pformat(payload))

        if final_size > MAX_PAYLOAD_SIZE:
            _LOGGER.warning(
                "Payload exceeds 2KB limit (%d bytes). Trimming...", final_size
            )

            essential_payloads = [p for p in entities_payload if p.get("primary")]
            other_payloads = [p for p in entities_payload if not p.get("primary")]

            final_payloads = essential_payloads.copy()
            for sensor_payload in other_payloads:
                test_payload = {
                    "merge_variables": {
                        "entities": final_payloads + [sensor_payload],
                        "timestamp": timestamp,
                        "count": len(final_payloads) + 1,
                        "wc": weather_code,
                        "wl": weather_lang_code,
                    }
                }
                if estimate_payload_size(test_payload) <= MAX_PAYLOAD_SIZE:
                    final_payloads.append(sensor_payload)
                else:
                    break

            payload["merge_variables"]["entities"] = final_payloads
            payload["merge_variables"]["count"] = len(final_payloads)
            final_size = estimate_payload_size(payload)
            _LOGGER.info(
                "Trimmed payload size: %d bytes (%d entities)",
                final_size,
                len(final_payloads),
            )
            _LOGGER.info("final payload data is %s", pprint.pformat(final_payloads))

        try:
            async with aiohttp.ClientSession() as session:
                _LOGGER.debug("Sending data to TRMNL webhook")
                async with session.post(current_url, json=payload) as response:
                    if response.status == 200:
                        _LOGGER.info(
                            "Successfully sent %d sensors to TRMNL",
                            len(entities_payload)
                        )
                        _LOGGER.debug("Response: %s", await response.text())
                    else:
                        _LOGGER.error("Webhook error: %s", response.status)
                        _LOGGER.error("Response: %s", await response.text())
        except Exception as err:
            _LOGGER.error("Failed to send data to webhook: %s", err)
