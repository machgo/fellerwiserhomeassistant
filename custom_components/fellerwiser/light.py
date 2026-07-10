"""Platform for light integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import requests
import websockets

# Import the device class from the component that you want to support
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    LightEntity,
)

_LOGGER = logging.getLogger(__name__)

HTTP_TIMEOUT = 10
RECONCILE_INTERVAL = 60
RECONNECT_DELAY = 10
WEBSOCKET_OPEN_TIMEOUT = 10
WEBSOCKET_PING_INTERVAL = 20
WEBSOCKET_PING_TIMEOUT = 10


def _apply_gateway_load(lights_by_id, load):
    """Apply one gateway load state to the matching Home Assistant entity."""
    light = lights_by_id.get(str(load.get("id")))
    state = load.get("state")
    if light is None or not isinstance(state, dict) or "bri" not in state:
        return

    brightness = state["bri"]
    if not isinstance(brightness, (int, float)):
        return

    light.update_external(brightness)


async def _reconcile_lights(lights_by_id, hass, host, apikey):
    """Refresh all light states from the authoritative HTTP endpoint."""
    try:
        response = await hass.async_add_executor_job(updatedata, host, apikey)
        response.raise_for_status()
        loads = response.json()["data"]
    except (requests.RequestException, ValueError, KeyError, TypeError) as err:
        _LOGGER.warning("Unable to reconcile light states from gateway: %s", err)
        return

    for load in loads:
        if isinstance(load, dict):
            _apply_gateway_load(lights_by_id, load)


async def hello(lights, hass, host, apikey):
    """Listen for gateway events and periodically reconcile missed state."""
    lights_by_id = {light._id: light for light in lights}

    while True:
        _LOGGER.info("Creating new light websocket connection")
        try:
            async with websockets.connect(
                "ws://" + host + "/api",
                additional_headers={"authorization": "Bearer " + apikey},
                open_timeout=WEBSOCKET_OPEN_TIMEOUT,
                ping_interval=WEBSOCKET_PING_INTERVAL,
                ping_timeout=WEBSOCKET_PING_TIMEOUT,
            ) as ws:
                # Events can be lost while disconnected, so every new connection
                # starts with a snapshot from the gateway.
                await _reconcile_lights(lights_by_id, hass, host, apikey)
                next_reconcile = (
                    asyncio.get_running_loop().time() + RECONCILE_INTERVAL
                )

                while True:
                    try:
                        timeout = max(
                            0,
                            next_reconcile - asyncio.get_running_loop().time(),
                        )
                        result = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    except asyncio.TimeoutError:
                        await _reconcile_lights(
                            lights_by_id, hass, host, apikey
                        )
                        next_reconcile = (
                            asyncio.get_running_loop().time()
                            + RECONCILE_INTERVAL
                        )
                        continue

                    try:
                        data = json.loads(result)
                        load = data["load"]
                        state = load["state"]
                    except (json.JSONDecodeError, KeyError, TypeError) as err:
                        _LOGGER.debug(
                            "Ignoring unsupported websocket message: %s", err
                        )
                        continue

                    if not isinstance(load, dict) or not isinstance(state, dict):
                        _LOGGER.debug(
                            "Ignoring websocket message with invalid load state"
                        )
                        continue

                    flags = state.get("flags")
                    if not isinstance(flags, dict) or flags.get("fading", 0) == 0:
                        _apply_gateway_load(lights_by_id, load)

                    if asyncio.get_running_loop().time() >= next_reconcile:
                        await _reconcile_lights(
                            lights_by_id, hass, host, apikey
                        )
                        next_reconcile = (
                            asyncio.get_running_loop().time()
                            + RECONCILE_INTERVAL
                        )
        except asyncio.CancelledError:
            raise
        except (
            OSError,
            TimeoutError,
            websockets.exceptions.WebSocketException,
        ) as err:
            _LOGGER.warning(
                "Light websocket disconnected (%s); retrying in %s seconds",
                err,
                RECONNECT_DELAY,
            )
            await asyncio.sleep(RECONNECT_DELAY)


def updatedata(host, apikey):
    #ip = "192.168.0.18"
    ip = host
    key = apikey
    return requests.get(
        "http://" + ip + "/api/loads",
        headers={"authorization": "Bearer " + key},
        timeout=HTTP_TIMEOUT,
    )


async def async_setup_entry(hass, entry, async_add_entities):
    host = entry.data['host']
    apikey = entry.data['apikey']

    _LOGGER.info("Setting up lights for Feller Wiser gateway %s", host)

    response = await hass.async_add_executor_job(updatedata, host, apikey)
    response.raise_for_status()

    loads = response.json()

    lights= []
    for value in loads["data"]:
        if value["type"] in ["dim", "dali", "onoff"]:
            lights.append(FellerLight(value, host, apikey))

    async_add_entities(lights, True)
    task = hass.async_create_task(hello(lights, hass, host, apikey))
    entry.async_on_unload(task.cancel)


class FellerLight(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(self, data, host, apikey) -> None:
        """Initialize an AwesomeLight."""
        # Phasecut Dimmer {'name': '00005341_0', 'device': '00005341', 'channel': 0, 'type': 'dim', 'id': 14, 'unused': False}
        # DALI Dimmer {'name': '00005341_0', 'device': '00005341', 'channel': 0, 'type': 'dali', 'id': 14, 'unused': False}

        self._data = data
        self._name = data["name"]
        self._id = str(data["id"])
        self._state = None
        self._brightness = None
        self._host = host
        self._apikey = apikey
        self._type = data["type"]


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


    @property
    def color_mode(self) -> str | None:
        if self._type == "onoff":
            return "onoff"
        return "brightness"


    @property
    def supported_color_modes(self) -> set | None:
        if self._type == "onoff":
            return {"onoff"}
        return {"brightness"}

    
    def turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """
        
        if not kwargs: 
            ip = self._host
            response = requests.put("http://"+ip+"/api/loads/"+self._id+"/ctrl", headers= {'authorization':'Bearer ' + self._apikey}, json={'button': 'on', 'event': 'click'})
            _LOGGER.info(response.json())
            self._state = True
            response = requests.get("http://"+ip+"/api/loads/"+self._id, headers= {'authorization':'Bearer ' + self._apikey})
            self._brightness = response.json()["data"]["state"]["bri"]/39.22
        
        else:
            self._brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            convertedBrightness = round(self._brightness*39.22)
            if convertedBrightness > 10000:
                convertedBrightness = 10000

            ip = self._host
            response = requests.put("http://"+ip+"/api/loads/"+self._id+"/target_state", headers= {'authorization':'Bearer ' + self._apikey}, json={'bri': convertedBrightness})
            _LOGGER.info(response.json())
            self._state = True
            self._brightness = response.json()["data"]["target_state"]["bri"]/39.22


    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        ip = self._host
        self._oldbrightness = self._brightness
        response = requests.put("http://"+ip+"/api/loads/"+self._id+"/ctrl", headers= {'authorization':'Bearer ' + self._apikey}, json={'button': 'off', 'event': 'click'})
        _LOGGER.info(response.json())
        # {'data': {'id': 6, 'target_state': {'bri': 0}}, 'status': 'success'}
        self._state = False
        response = requests.get("http://"+ip+"/api/loads/"+self._id, headers= {'authorization':'Bearer ' + self._apikey})
        self._brightness = response.json()["data"]["state"]["bri"]/39.22


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
        self._brightness = load["data"]["state"]["bri"]/39.22


    def update_external(self, brightness):
        """Apply a brightness update received from the gateway."""
        self._brightness = brightness/39.22
        if self._brightness > 0:
            self._state = True
        else:
            self._state = False
        self.schedule_update_ha_state()

    def updateExternal(self, brightness):
        """Apply a gateway update using the legacy method name."""
        self.update_external(brightness)
