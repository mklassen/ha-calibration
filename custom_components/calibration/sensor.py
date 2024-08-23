"""Support for calibration sensor."""
from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.sensor.const import ATTR_STATE_CLASS, CONF_STATE_CLASS
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ICON,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ATTRIBUTE,
    CONF_DEVICE_CLASS,
    CONF_NAME,
    CONF_SOURCE,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import (
    get_capability,
    get_device_class,
    get_unit_of_measurement,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import RegistryEntry, RegistryEntryHider
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    ATTR_COEFFICIENTS,
    ATTR_SOURCE,
    ATTR_SOURCE_ATTRIBUTE,
    ATTR_SOURCE_VALUE,
    CONF_CALIBRATION,
    CONF_HIDE_SOURCE,
    CONF_POLYNOMIAL,
    CONF_PRECISION,
    DATA_CALIBRATION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(  # pylint: disable=too-many-locals
    hass: HomeAssistant,
    config: ConfigType,  # pylint: disable=unused-argument
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Calibration sensor."""
    if discovery_info is None:
        return

    calibration = discovery_info[CONF_CALIBRATION]
    conf = hass.data[DATA_CALIBRATION][calibration]

    unique_id = f"{DOMAIN}.{calibration}"
    name = conf.get(CONF_NAME) or calibration.replace("_", " ").title()
    source = conf[CONF_SOURCE]

    units = conf.get(CONF_UNIT_OF_MEASUREMENT)
    device_class = conf.get(CONF_DEVICE_CLASS)
    state_class = conf.get(CONF_STATE_CLASS)

    ent_reg = entity_registry.async_get(hass)
    source_entity: RegistryEntry | None = ent_reg.async_get(source)

    if not (attribute := conf.get(CONF_ATTRIBUTE)):
        units = units or get_unit_of_measurement(hass, source)
        device_class = device_class or get_device_class(hass, source)
        state_class = get_capability(hass, source, ATTR_STATE_CLASS)

    if conf.get(CONF_HIDE_SOURCE) and source_entity and not source_entity.hidden:
        ent_reg.async_update_entity(source, hidden_by=RegistryEntryHider.INTEGRATION)

    async_add_entities(
        [
            CalibrationSensor(
                unique_id,
                name,
                source,
                attribute,
                conf[CONF_PRECISION],
                conf[CONF_POLYNOMIAL],
                units,
                device_class,
                state_class,
            )
        ]
    )


class CalibrationSensor(SensorEntity):  # pylint: disable=too-many-instance-attributes
    """Representation of a Calibration sensor."""

    def __init__(
        self,
        unique_id: str,
        name: str,
        source: str,
        attribute: str | None,
        precision: int,
        polynomial,
        unit_of_measurement: str | None,
        device_class: str | None,
        state_class: str | None,
    ) -> None:
        """Initialize the Calibration sensor."""
        self._source_entity_id = source
        self._source_attribute = attribute
        self._precision = precision
        self._poly = polynomial

        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_class = cast(SensorDeviceClass, device_class)
        self._attr_icon = None
        self._attr_should_poll = False

        attrs = {
            ATTR_SOURCE_VALUE: None,
            ATTR_SOURCE: source,
            ATTR_SOURCE_ATTRIBUTE: attribute,
            ATTR_COEFFICIENTS: polynomial.coef.tolist(),
            ATTR_STATE_CLASS: state_class,
        }
        self._attr_extra_state_attributes = {
            k: v for k, v in attrs.items() if v or k == ATTR_SOURCE_VALUE
        }

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        if (state := self.hass.states.get(self._source_entity_id)) is not None:
            self._update_state(state)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._async_calibration_sensor_state_listener,
            )
        )

    @callback
    def _async_calibration_sensor_state_listener(self, event: Event) -> None:
        """Handle sensor state changes."""
        if (new_state := event.data.get("new_state")) is not None:
            self._update_state(new_state)

    def _update_state(self, state: State) -> None:
        source_value = (
            state.attributes.get(self._source_attribute)
            if self._source_attribute
            else state.state
            if state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
            else None
        )

        _LOGGER.debug(
            "CalibrationSensor(%s) received update: %s", self.name, source_value
        )

        if not self._source_attribute:
            if self._attr_native_unit_of_measurement is None:
                self._attr_native_unit_of_measurement = state.attributes.get(
                    ATTR_UNIT_OF_MEASUREMENT
                )

            if self._attr_device_class is None and (
                device_class := state.attributes.get(ATTR_DEVICE_CLASS)
            ):
                self._attr_device_class = cast(SensorDeviceClass, device_class)

            if self._attr_icon is None:
                self._attr_icon = state.attributes.get(ATTR_ICON)

        try:
            source_value = float(source_value)
            native_value = round(self._poly(source_value), self._precision)
        except (ValueError, TypeError):
            source_value = native_value = None
            if self._source_attribute:
                _LOGGER.warning(
                    "%s attribute %s is not numerical",
                    self._source_entity_id,
                    self._source_attribute,
                )
            else:
                _LOGGER.warning("%s state is not numerical", self._source_entity_id)

        self._attr_extra_state_attributes[ATTR_SOURCE_VALUE] = source_value
        self._attr_native_value = native_value

        self.async_write_ha_state()
