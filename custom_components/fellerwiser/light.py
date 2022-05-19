"""Platform for light integration."""
from __future__ import annotations

import logging
from modulefinder import LOAD_CONST

import requests
import websockets
import asyncio
import json



import voluptuous as vol
from .const import (
    DOMAIN,
)

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (ATTR_BRIGHTNESS, PLATFORM_SCHEMA,
                                            LightEntity)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required('host'): cv.string,
    vol.Required('apikey'): cv.string,
})



async def hello(lights, hass, host, apikey):
    ip = host
    async with websockets.connect("ws://"+ip+"/api", extra_headers={'authorization':'Bearer ' + apikey}, ping_timeout=None) as ws:
        while True:
            result =  await ws.recv()
            _LOGGER.info("Received '%s'" % result)
            data = json.loads(result)     
            # {"load":{"id":6,"state":{"bri":10000,"flags":{"over_current":0,"fading":0,"noise":0,"direction":0,"over_temperature":0}}}}

            if data["load"]["state"]["flags"]["fading"] == 0:
                for l in lights:
                    if l.unique_id == "light-"+str(data["load"]["id"]):
                        _LOGGER.info("found entity to update")
                        l.updateExternal(data["load"]["state"]["bri"])

        ws.close()

def updatedata(host, apikey):
    #ip = "192.168.0.18"
    ip = host
    key = apikey
    return requests.get("http://"+ip+"/api/loads", headers= {'authorization':'Bearer ' + key})


async def async_setup_entry(hass, entry, async_add_entities):
    host = entry.data['host']
    apikey = entry.data['apikey']

    _LOGGER.info("---------------------------------------------- %s %s", host, apikey)

    response = await hass.async_add_executor_job(updatedata, host, apikey)

    loads = response.json()

    lights= []
    for value in loads["data"]:
        if value["type"] == "dim":
            lights.append(FellerLight(value, host, apikey))

    asyncio.get_event_loop().create_task(hello(lights, hass, host, apikey))
    async_add_entities(lights, True)

   


class FellerLight(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(self, data, host, apikey) -> None:
        """Initialize an AwesomeLight."""
        # {'name': '00005341_0', 'device': '00005341', 'channel': 0, 'type': 'dim', 'id': 14, 'unused': False}

        self._data = data
        self._name = data["name"]
        self._id = str(data["id"])
        self._state = None
        self._brightness = None
        self._host = host
        self._apikey = apikey

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        return "light-" + self._id

    @property
    def brightness(self):
        """Return the brightness of the light.

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state
    
    @property
    def should_poll(self) -> bool | None:
        return False

    def turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """
        self._brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        ip = self._host
        response = requests.put("http://"+ip+"/api/loads/"+self._id+"/target_state", headers= {'authorization':'Bearer ' + self._apikey}, json={'bri': 10000})
        _LOGGER.info(response.json())
        self._state = True
        self._brightness = response.json()["data"]["target_state"]["bri"]


    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        ip = self._host
        response = requests.put("http://"+ip+"/api/loads/"+self._id+"/target_state", headers= {'authorization':'Bearer ' + self._apikey}, json={'bri': 0})
        _LOGGER.info(response.json())
        # {'data': {'id': 6, 'target_state': {'bri': 0}}, 'status': 'success'}
        self._state = False
        self._brightness = response.json()["data"]["target_state"]["bri"]

    def updatestate(self):
        ip = self._host
        # _LOGGER.info("requesting http://"+ip+"/api/loads/"+self._id)
        return requests.get("http://"+ip+"/api/loads/"+self._id, headers= {'authorization':'Bearer ' + self._apikey})


    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """

        response = self.updatestate()
        load = response.json()
        _LOGGER.info(load)
        # 'data': {'id': 7, 'unused': False, 'name': '000086dd_0', 'state': {'bri': 0, 'flags': {'over_current': 0, 'fading': 0, 'noise': 0, 'direction': 1, 'over_temperature': 0}}, 'device': '000086dd', 'channel': 0, 'type': 'dim'}, 'status': 'success'}

        self._data = load["data"]
        if (load["data"]["state"]["bri"] > 0):
            self._state = True
        else:
            self._state = False
        self._brightness = load["data"]["state"]["bri"]
    
    def updateExternal(self, brightness):
        self._brightness = brightness
        if self._brightness > 0:
            self._state = True
        else:
            self._state = False
        self.schedule_update_ha_state()


