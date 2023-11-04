# sensor.py
# @see docs for API at https://api.rla2.cityway.fr/

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_RESOURCES
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import asyncio
import logging
from . import DOMAIN

from datetime import timedelta, datetime

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)  # Polling interval

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""

    # Not needed, as we're not using discovery but configuration.yaml
    # if discovery_info is None:
    #     return

    bus_stop_ids = hass.data[DOMAIN]['bus_stop_ids']
    coordinator = BusStopDataUpdateCoordinator(hass, bus_stop_ids)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise UpdateFailed

    sensors = []
    for stop_id in bus_stop_ids:
        # sensors.append(BusStopSensor(coordinator, stop_id))

        # Then, get each line for each bus stop and create a sensor for each line
        lines_info = coordinator.data[stop_id]['lines'][0]['Lines']
        for line in lines_info:
            # Note that each line may have multiple directions, so we need to create a sensor for each direction
            for direction in line['LineDirections']:
                # We will use the line code and direction code as the unique ID for the sensor
                sensor_id = f"{stop_id}_{line['Code']}_{direction['Direction']}"
                sensors.append(BusLineSensor(coordinator, stop_id, line['Code'], direction['Direction']))

    async_add_entities(sensors, True)

class BusStopDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""
    def __init__(self, hass, bus_stop_ids):
        """Initialize."""
        self.bus_stop_ids = bus_stop_ids
        self.api = BusStopAPI(async_get_clientsession(hass))

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            # First, we gather data for all bus stops
            next_departure_for_bus_stop_data = await self.api.get_next_departure_for_bus_stop_data(self.bus_stop_ids)

            # Check if next_departure_for_bus_stop_data is a dictionary before proceeding
            if not isinstance(next_departure_for_bus_stop_data, dict):
                _LOGGER.error("next_departure_for_bus_stop_data is not a dictionary: %s", next_departure_for_bus_stop_data)
                return {}

            # Now, we get the lines available at each bus stop
            lines_tasks = [self.api.get_lines_by_stop(stop_id) for stop_id in self.bus_stop_ids]
            lines_data = await asyncio.gather(*lines_tasks)

            # Combine bus stop data with line data using stop_id as a key
            combined_data = {}
            for stop_id, lines in zip(self.bus_stop_ids, lines_data):
                combined_data[stop_id] = {
                    'next_departure_for_bus_stop_data': next_departure_for_bus_stop_data.get(stop_id),
                    'lines': lines
                }
            return combined_data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

class BusStopSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, coordinator, stop_id):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.stop_id = stop_id
        self._attr_name = f"Bus Stop {stop_id}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data.get(self.stop_id)
        # Here you extract the required data. For demonstration, let's say we want the number of lines
        return len(data['lines'][0]['Lines']) if data and 'lines' in data else 0

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = self.coordinator.data.get(self.stop_id)
        if data and 'lines' in data:
            # Extract and return the bus lines information as attributes
            lines_info = data['lines'][0]['Lines']
            return {
                "lines": [
                    {
                        "line_code": line["Code"],
                        "line_name": line["Name"],
                        "color": line["Color"],
                        "text_color": line["TextColor"],
                        "disrupted": line["IsDisrupted"]
                    } for line in lines_info
                ]
            }
        return {}

    async def async_update(self):
        """Update Bus Stop sensor."""
        await self.coordinator.async_request_refresh()

class BusLineSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, coordinator, stop_id, line_code, line_direction_code):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.stop_id = stop_id
        self.line_code = line_code
        self.line_direction_code = line_direction_code
        self._attr_name = self.get_pretty_name()

    def get_pretty_name(self):
        """Return a pretty name for the sensor. It should be like: Line {} to {}"""
        data = self.coordinator.data.get(self.stop_id)
        if data and 'lines' in data:
            # Extract and return the bus lines information as attributes for the given line code and direction
            lines_info = data['lines'][0]['Lines']
            for line in lines_info:
                if line['Code'] == self.line_code:
                    for direction in line['LineDirections']:
                        if direction['Direction'] == self.line_direction_code:
                            return f"{line['Code']} to {direction['Destination']}"
    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data.get(self.stop_id)
        # Here we will extract the next departure time for the given line code and direction
        if data and 'next_departure_for_bus_stop_data' in data:
            next_departure_for_bus_stop_data = data['next_departure_for_bus_stop_data']
            if next_departure_for_bus_stop_data is not None:
                for line in next_departure_for_bus_stop_data['lines']:
                    # If the line['number'] matches the line code (note, first one is a string, second one is an int), then we return the next departure time
                    if line['line']['number'] == self.line_code:
                        # If the nexted object direction has an id key that matches the line direction code, then we return the next departure time, otherwise we continue
                        if line['direction']['id'] == self.line_direction_code:
                            # Now we can go into the "times" array and get the first item, which is the next departure time
                            date = line['times'][0]['dateTime']
                            return format_hour_minute(date)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = self.coordinator.data.get(self.stop_id)

        if data and 'lines' in data:
            # Extract and return the bus lines information as attributes for the given line code and direction
            lines_info = data['lines'][0]['Lines']
            for line in lines_info:
                if line['Code'] == self.line_code:
                    for direction in line['LineDirections']:
                        if direction['Direction'] == self.line_direction_code:
                            return {
                                "line_code": line["Code"],
                                "line_name": line["Name"],
                                "color": line["Color"],
                                "text_color": line["TextColor"],
                                "disrupted": line["IsDisrupted"],
                                "direction": direction["Direction"],
                                "destination": direction["Destination"]
                                # "next_departure": direction["NextDeparture"]
                            }
        return {}

    async def async_update(self):
        """Update Bus Stop sensor."""
        await self.coordinator.async_request_refresh()

class BusStopAPI:
    """Class for handling the data retrieval."""

    BASE_URL = 'https://api.rla2.cityway.fr/media/api/v1/en/Schedules/LogicalStop/{}/NextDeparture'

    LINES_BY_STOP_URL = 'https://api.rla2.cityway.fr/media/api/transport/linesByLogicalStops?StopId={}'

    def __init__(self, session):
        """Initialize the API."""
        self.session = session

    async def get_next_departure_for_bus_stop_data(self, stop_ids):
        """Pull data from the API for each bus stop."""
        next_departure_for_bus_stop_data = {}
        for stop_id in stop_ids:
            url = self.BASE_URL.format(stop_id)
            response = await self.session.get(url)
            try:
                response.raise_for_status()
                data = await response.json()
                _LOGGER.debug("API Response for stop ID %s: %s", stop_id, data)
                if data is not None and len(data) > 0:
                    # Get the first item in the lest where the "transportMode" is "Bus"
                    data_to_return = next((item for item in data if item["transportMode"] == "Bus"), None)
                    next_departure_for_bus_stop_data[stop_id] = data_to_return
                else:
                    next_departure_for_bus_stop_data[stop_id] = {}
            except Exception as e:
                _LOGGER.error("Error fetching data for stop ID %s: %s", stop_id, e)
        return next_departure_for_bus_stop_data


    async def get_lines_by_stop(self, stop_id):
        """Fetch lines available at a specific bus stop."""
        url = self.LINES_BY_STOP_URL.format(stop_id)
        response = await self.session.get(url)
        response.raise_for_status()
        return await response.json()

def format_hour_minute(date_str):
    # Parse the date string to a datetime object
    date_obj = datetime.fromisoformat(date_str)
    # Format the datetime object to only show the hour and minute
    return date_obj.strftime('%H:%M')
