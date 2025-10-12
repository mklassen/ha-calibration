"""The Calibration integration."""

import logging

import voluptuous as vol
from homeassistant.components.sensor.const import (
    CONF_STATE_CLASS,
    DEVICE_CLASSES_SCHEMA,
)
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_DEVICE_CLASS,
    CONF_NAME,
    CONF_SOURCE,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType
from numpy.polynomial import Polynomial
from scipy.interpolate import CubicSpline

from .const import (
    CONF_CALIBRATION,
    CONF_DATAPOINTS,
    CONF_DEGREE,
    CONF_HIDE_SOURCE,
    CONF_POLYNOMIAL,
    CONF_PRECISION,
    DATA_CALIBRATION,
    DEFAULT_DEGREE,
    DEFAULT_PRECISION,
    CONF_METHOD,
    DEFAULT_METHOD,
    VALID_METHODS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def datapoints_greater_than_degree(value: dict) -> dict:
    """Validate data point list is greater than polynomial degrees."""
    if len(value[CONF_DATAPOINTS]) <= value[CONF_DEGREE]:
        raise vol.Invalid(
            f"{CONF_DATAPOINTS} must have at least {value[CONF_DEGREE]+1} {CONF_DATAPOINTS}"
        )

    return value


CALIBRATION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOURCE): cv.entity_id,
        vol.Exclusive(CONF_ATTRIBUTE, "attr_hide"): cv.string,
        vol.Exclusive(CONF_HIDE_SOURCE, "attr_hide"): cv.boolean,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(CONF_STATE_CLASS): cv.string,
        vol.Required(CONF_DATAPOINTS): [
            vol.ExactSequence([vol.Coerce(float), vol.Coerce(float)])
        ],
        vol.Optional(CONF_DEGREE, default=DEFAULT_DEGREE): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=7),
        ),
        vol.Optional(CONF_PRECISION, default=DEFAULT_PRECISION): cv.positive_int,
        vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.In(VALID_METHODS),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {cv.slug: vol.All(CALIBRATION_SCHEMA, datapoints_greater_than_degree)}
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Calibration sensor."""
    hass.data[DATA_CALIBRATION] = {}

    for calibration, conf in config.get(DOMAIN, {}).items():
        _LOGGER.debug("Setup %s.%s", DOMAIN, calibration)

        degree = conf[CONF_DEGREE]

        # Spline interpolation requires sorted x values
        x_values, y_values = zip(*sorted(conf[CONF_DATAPOINTS]))

        method = conf[CONF_METHOD]
        if method == "cubicspline":
            cs = CubicSpline(x_values, y_values, bc_type="natural")
            evaluator = lambda x: cs(x).item()
        else:
            # try to get valid coefficients for a polynomial
            evaluator = Polynomial.fit(x_values, y_values, degree, domain=[])  # type: ignore

        data = {
            k: v for k, v in conf.items() if k not in [CONF_DEGREE, CONF_DATAPOINTS, CONF_METHOD]
        }
        data[CONF_POLYNOMIAL] = evaluator

        hass.data[DATA_CALIBRATION][calibration] = data

        hass.async_create_task(
            async_load_platform(
                hass,
                SENSOR_DOMAIN,
                DOMAIN,
                {CONF_CALIBRATION: calibration},
                config,
            )
        )

    return True
