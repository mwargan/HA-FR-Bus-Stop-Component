# Example Sensor

This is a minimum implementation of an integration providing a sensor measurement.

### Installation

Copy this folder to `<config_dir>/custom_components/bus_stop/`.

Add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
bus_stop:
  bus_stop_ids:
    - 1000
```

### How to get the bus stop id

1. Go to https://www.lignesdazur.com/horaires-arret/1000
2. Write in a bus stop name you're interested in and make the request
3. Look at the network requests tab, you should see a request to LinesByLogicalStops (e.g. https://api.rla2.cityway.fr/media/api/transport/linesByLogicalStops?StopId=1000)
   1. The StopId parameter is the bus stop id you're looking for

# HA-FR-Bus-Stop-Component
