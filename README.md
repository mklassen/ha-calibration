# [Calibration](https://github.com/lymanepp/ha-calibration)

The Calibration integration consumes the state from other sensors. It exports the calibrated value as state and the following values as attributes: `source_value`, `source`, `source_attribute` and `coefficients`.  A single polynomial, linear by default, is fit to the data points provided.

This is a fork of the Home Assistant Core [compensation](https://www.home-assistant.io/integrations/compensation/) integration created by [@petro31](https://github.com/petro31). It was forked to add these enhancements:
1. Provide sane defaults for `unique_id` and `name`.
2. Allow `device_class` and `unit_of_measurement` to be configured. This is especially useful when `attribute` is specified.
3. Add auto-configuration of `device_class` when `attribute` is not specified. The `compensation` integration already partially supported that for `unit_of_measurement`.
4. Allow hiding the `source` entity from Home Assistant.

#2-4 have been submitted for integration in Home Assistant Core, but backward-compatibility constraints will prevent sane defaults from being integrated upstream.

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

This integration can be installed using HACS. To do it search for Calibration in the integrations section.

### Manual

To install this integration manually you can either:

* Use git:

```sh
git clone https://github.com/lymanepp/ha-calibration.git
cd ha-calibration
# if you want a specific version checkout its tag
# e.g. git checkout 1.0.0

# replace $hacs_config_folder with your home assistant config folder path
cp -r custom_components $hacs_config_folder
```

* Download the source release and extract the custom_components folder into your home assistant config folder.

Finally, you need to restart Home Assistant before you can use it.

## Configuration

To enable the calibration integration, add the following lines to your `configuration.yaml`:

```yaml
# Example configuration.yaml entry
calibration:
  garage_humidity:
    source: sensor.garage_humidity_uncalibrated
    degree: 1
    hide_source: true
    data_points:
      - [38.68, 32.0]
      - [79.89, 75.0]
```

## Options

***source** `string` `(required)`*
> The entity to monitor.

***attribute** `string` `(optional)`*
> The source attribute to monitor.

***hide_source** `boolean` `(optional, default: false)`*
> Hide the source entity in Home Assistant. If specified with `attribute`, it will hide the `source` entity as attributes cannot be hidden individually.

***name** `string` `(optional)`*
> Set the name for the new sensor. By default, a human-readable version of the configuration section name will be used (**Garage Humidity** in the example).

***device_class** `string` `(optional, default: from source)`*
> Set the device class for the new sensor. By default, the device class from the monitored entity will be used (except when `attribute` is specified). A list of device classes is available [here](https://www.home-assistant.io/integrations/sensor).

***unit_of_measurement** `string` `(optional, default: from source)`*
> Defines the units of measurement of the sensor, if any. By default, the unit of measurement from the source will be used (except when `attribute` is specified).

***state_class** `string` `(optional, default: from source)`*
> Set the state class for the new sensor. By default, the state class from the monitored entity will be used (except when `attribute` is specified). The typical state class will be 'measurement'.

***data_points** `list` `(required)`*
> The collection of data point conversions with the format `[uncalibrated_value, calibrated_value]`. e.g., `[38.68, 32.0]`. The number of required data points is equal to the polynomial `degree` + 1. For example, a linear calibration (with `degree: 1`) requires at least 2 data points.

***degree** `integer` `(optional, default=1)`*
> The degree of a polynomial. e.g., Linear calibration (y = x + 3) has 1 degree, Quadratic calibration (y = x2 + x + 3) has 2 degrees, etc.

***precision** `integer` `(optional, default=2)`*
> Defines the precision of the calculated values.
