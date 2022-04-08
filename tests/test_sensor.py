"""The tests for the integration sensor platform."""
import pytest
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ATTRIBUTE,
    CONF_SOURCE,
    CONF_UNIT_OF_MEASUREMENT,
    EVENT_HOMEASSISTANT_START,
    EVENT_STATE_CHANGED,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_registry import RegistryEntryHider
from homeassistant.setup import async_setup_component
from pytest import LogCaptureFixture
from voluptuous.error import MultipleInvalid

from custom_components.calibration import CONFIG_SCHEMA
from custom_components.calibration.const import (
    CONF_DATAPOINTS,
    CONF_DEGREE,
    CONF_PRECISION,
    DOMAIN,
)
from custom_components.calibration.sensor import ATTR_COEFFICIENTS


async def test_linear_state(hass: HomeAssistant, caplog: LogCaptureFixture):
    """Test calibration sensor state."""
    config = {
        DOMAIN: {
            "test": {
                CONF_SOURCE: "sensor.uncalibrated",
                CONF_DATAPOINTS: [
                    [1.0, 2.0],
                    [2.0, 3.0],
                ],
                CONF_PRECISION: 2,
                CONF_UNIT_OF_MEASUREMENT: "a",
            }
        }
    }
    expected_entity_id = "sensor.test"

    assert await async_setup_component(hass, DOMAIN, config)
    assert await async_setup_component(hass, SENSOR_DOMAIN, config)
    await hass.async_block_till_done()

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    entity_id = config[DOMAIN]["test"][CONF_SOURCE]
    hass.states.async_set(entity_id, 4, {})
    await hass.async_block_till_done()

    state = hass.states.get(expected_entity_id)
    assert state is not None

    assert round(float(state.state), config[DOMAIN]["test"][CONF_PRECISION]) == 5.0

    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "a"

    coefs = [round(v, 1) for v in state.attributes.get(ATTR_COEFFICIENTS)]
    assert coefs == [1.0, 1.0]

    hass.states.async_set(entity_id, "foo", {})
    await hass.async_block_till_done()

    assert "state is not numerical" in caplog.text

    state = hass.states.get(expected_entity_id)
    assert state is not None

    assert state.state == STATE_UNKNOWN


async def test_linear_state_from_attribute(hass: HomeAssistant):
    """Test calibration sensor state that pulls from attribute."""
    config = {
        DOMAIN: {
            "test": {
                CONF_SOURCE: "sensor.uncalibrated",
                CONF_ATTRIBUTE: "value",
                CONF_DATAPOINTS: [
                    [1.0, 2.0],
                    [2.0, 3.0],
                ],
                CONF_PRECISION: 2,
            }
        }
    }
    expected_entity_id = "sensor.test"

    assert await async_setup_component(hass, DOMAIN, config)
    assert await async_setup_component(hass, SENSOR_DOMAIN, config)
    await hass.async_block_till_done()

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)

    entity_id = config[DOMAIN]["test"][CONF_SOURCE]
    hass.states.async_set(entity_id, 3, {"value": 4})
    await hass.async_block_till_done()

    state = hass.states.get(expected_entity_id)
    assert state is not None

    assert round(float(state.state), config[DOMAIN]["test"][CONF_PRECISION]) == 5.0

    coefs = [round(v, 1) for v in state.attributes.get(ATTR_COEFFICIENTS)]
    assert coefs == [1.0, 1.0]

    hass.states.async_set(entity_id, 3, {"value": "bar"})
    await hass.async_block_till_done()

    state = hass.states.get(expected_entity_id)
    assert state is not None

    assert state.state == STATE_UNKNOWN


async def test_quadratic_state(hass: HomeAssistant):
    """Test 3 degree polynominial calibration sensor."""
    config = {
        DOMAIN: {
            "test": {
                CONF_SOURCE: "sensor.temperature",
                CONF_DATAPOINTS: [
                    [50, 3.3],
                    [50, 2.8],
                    [50, 2.9],
                    [70, 2.3],
                    [70, 2.6],
                    [70, 2.1],
                    [80, 2.5],
                    [80, 2.9],
                    [80, 2.4],
                    [90, 3.0],
                    [90, 3.1],
                    [90, 2.8],
                    [100, 3.3],
                    [100, 3.5],
                    [100, 3.0],
                ],
                CONF_DEGREE: 2,
                CONF_PRECISION: 3,
            }
        }
    }
    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    entity_id = config[DOMAIN]["test"][CONF_SOURCE]
    hass.states.async_set(entity_id, 43.2, {})
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test")

    assert state is not None

    assert round(float(state.state), config[DOMAIN]["test"][CONF_PRECISION]) == 3.327


async def test_datapoints_greater_than_degree(
    hass: HomeAssistant, caplog: LogCaptureFixture
):
    """Tests 3 bad data points."""
    config = {
        DOMAIN: {
            "test": {
                CONF_SOURCE: "sensor.uncalibrated",
                CONF_DATAPOINTS: [
                    [1.0, 2.0],
                    [2.0, 3.0],
                ],
                CONF_DEGREE: 2,
            },
        }
    }
    await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    assert "data_points must have at least 3 data_points" in caplog.text


async def test_new_state_is_none(hass: HomeAssistant):
    """Tests catch for empty new states."""
    config = {
        DOMAIN: {
            "test": {
                CONF_SOURCE: "sensor.uncalibrated",
                CONF_DATAPOINTS: [
                    [1.0, 2.0],
                    [2.0, 3.0],
                ],
                CONF_PRECISION: 2,
                CONF_UNIT_OF_MEASUREMENT: "a",
            }
        }
    }
    expected_entity_id = "sensor.test"

    await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    last_changed = hass.states.get(expected_entity_id).last_changed

    hass.bus.async_fire(
        EVENT_STATE_CHANGED, event_data={"entity_id": "sensor.uncalibrated"}
    )

    assert last_changed == hass.states.get(expected_entity_id).last_changed


async def test_hide_source(hass):
    """Test hiding source sensor."""
    config = {
        DOMAIN: {
            "test": {
                "source": None,
                "data_points": [
                    [1.0, 2.0],
                    [2.0, 3.0],
                ],
                "precision": 2,
                "hide_source": "yes",
            }
        }
    }

    registry = entity_registry.async_get(hass)
    source = registry.async_get_or_create(SENSOR_DOMAIN, "test", "sensor.uncompensated")
    config[DOMAIN]["test"]["source"] = source.entity_id

    assert await async_setup_component(hass, DOMAIN, config)
    assert await async_setup_component(hass, SENSOR_DOMAIN, config)
    await hass.async_block_till_done()

    source = registry.async_get(source.entity_id)
    assert source.hidden_by == RegistryEntryHider.INTEGRATION


async def test_attr_hide_exclusive():
    """Test compensation sensor state."""
    config = {
        DOMAIN: {
            "test": {
                "source": "sensor.uncompensated",
                "attribute": "value",
                "hide_source": True,
                "data_points": [
                    [1.0, 2.0],
                    [2.0, 3.0],
                ],
                "precision": 2,
                "unit_of_measurement": "a",
            }
        }
    }

    with pytest.raises(
        MultipleInvalid, match="two or more values in the same group of exclusion"
    ):
        CONFIG_SCHEMA(config)


async def test_invalid_config(hass: HomeAssistant, caplog: LogCaptureFixture):
    """Test calibration sensor state."""
    config = {
        DOMAIN: {
            "test": {
                CONF_SOURCE: "sensor.uncalibrated",
                CONF_DATAPOINTS: [
                    [1.0, 2.0],
                    [2.0, "a"],
                ],
                CONF_PRECISION: 2,
                CONF_UNIT_OF_MEASUREMENT: "a",
            }
        }
    }
    assert not await async_setup_component(hass, DOMAIN, config)
    assert (
        "expected float @ data['calibration']['test']['data_points'][1]. Got [2.0, 'a']."
        in caplog.text
    )
