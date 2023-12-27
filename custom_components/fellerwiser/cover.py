from __future__ import annotations

import logging

import requests
import websockets
import asyncio
import json
import socket



# Import the device class from the component that you want to support
from homeassistant.components.cover import (ATTR_POSITION, CoverEntity)

_LOGGER = logging.getLogger(__name__)

async def hello(covers, hass, host, apikey):
    ip = host

    while True:
    # outer loop restarted every time the connection fails
        _LOGGER.info('Creating new connection...')
        try:
            async with websockets.connect("ws://"+ip+"/api", extra_headers={'authorization':'Bearer ' + apikey}, ping_timeout=None) as ws:
                while True:
                # listener loop
                    try:
                        result = await asyncio.wait_for(ws.recv(), timeout=None)
                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                        try:
                            pong = await ws.ping()
                            await asyncio.wait_for(pong, timeout=None)
                            _LOGGER.info('Ping OK, keeping connection alive...')
                            continue
                        except:
                            _LOGGER.info(
                                f'Ping error - retrying connection in {10} sec (Ctrl-C to quit)')
                            await asyncio.sleep(10)
                            break
                    _LOGGER.info(f'Server said > {result}')
                    data = json.loads(result)
                    for l in covers:
                        if l.unique_id == "cover-"+str(data["load"]["id"]):
                            _LOGGER.info("found entity to update")
                            l.updateExternal(data["load"]["state"]["level"], data["load"]["state"]["moving"])
        except socket.gaierror:
            _LOGGER.info(
                f'Socket error - retrying connection in {10} sec (Ctrl-C to quit)')
            await asyncio.sleep(10)
            continue
        except ConnectionRefusedError:
            _LOGGER.info('Nobody seems to listen to this endpoint. Please check the URL.')
            _LOGGER.info(f'Retrying connection in {10} sec (Ctrl-C to quit)')
            await asyncio.sleep(10)
            continue
        except KeyError:
            _LOGGER.info("KeyError")
            continue

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

    covers= []
    for value in loads["data"]:
        if value["type"] == "motor":
            covers.append(FellerCover(value, host, apikey))

    asyncio.get_event_loop().create_task(hello(covers, hass, host, apikey))
    async_add_entities(covers, True)


class FellerCover(CoverEntity):

    def __init__(self, data, host, apikey) -> None:
        self._data = data
        self._name = data["name"]
        self._id = str(data["id"])
        self._is_opening = False
        self._is_closing = False
        self._is_closed = False
        self._position = None
        self._host = host
        self._apikey = apikey

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self):
        return "cover-" + self._id

    @property
    def current_cover_position(self):
        return self._position

    @property
    def is_opening(self) -> bool | None:
        return self._is_opening

    @property
    def is_closing(self) -> bool | None:
        return self._is_closing

    @property
    def is_closed(self) -> bool | None:
        return self._is_closed

    @property
    def should_poll(self) -> bool | None:
        return False

    def open_cover(self, **kwargs: Any) -> None:
        self._position = kwargs.get(ATTR_POSITION, 100)
        ip = self._host
        response = requests.put("http://"+ip+"/api/loads/"+self._id+"/target_state", headers= {'authorization':'Bearer ' + self._apikey}, json={'level': 0})
        _LOGGER.info(response.json())
        self._state = True
        self._position = 100-(response.json()["data"]["target_state"]["level"]/100)

    def close_cover(self, **kwargs: Any) -> None:
        self._position = kwargs.get(ATTR_POSITION, 100)
        ip = self._host
        response = requests.put("http://"+ip+"/api/loads/"+self._id+"/target_state", headers= {'authorization':'Bearer ' + self._apikey}, json={'level': 10000})
        _LOGGER.info(response.json())
        self._state = True
        self._position = 100-(response.json()["data"]["target_state"]["level"]/100)

    def set_cover_position(self, **kwargs: Any) -> None:
        self._position = kwargs.get(ATTR_POSITION, 100)
        ip = self._host
        response = requests.put("http://"+ip+"/api/loads/"+self._id+"/target_state", headers= {'authorization':'Bearer ' + self._apikey}, json={'level': (100-self._position)*100})
        _LOGGER.info(response.json())
        self._state = True
        self._position = 100-(response.json()["data"]["target_state"]["level"]/100)

    def stop_cover(self, **kwargs: Any) -> None:
        ip = self._host
        response = requests.put("http://"+ip+"/api/loads/"+self._id+"/ctrl", headers= {'authorization':'Bearer ' + self._apikey}, json={'button': "stop", 'event': 'click'})
        _LOGGER.info(response.json())


    def updatestate(self):
        ip = self._host
        # _LOGGER.info("requesting http://"+ip+"/api/loads/"+self._id)
        return requests.get("http://"+ip+"/api/loads/"+self._id, headers= {'authorization':'Bearer ' + self._apikey})


    def update(self) -> None:
        response = self.updatestate()
        load = response.json()
        _LOGGER.info(load)

        #ha: 100 = open, 0 = closed
        #feller: 10000 = closed, 0 = open
        self._position = 100-(load["data"]["state"]["level"]/100)

        if load["data"]["state"]["moving"] == "stop":
            self._is_closing = False
            self._is_opening = False
        if load["data"]["state"]["moving"]  == "up":
            self._is_closing = False
            self._is_opening = True
        if load["data"]["state"]["moving"] == "down":
            self._is_closing = True
            self._is_opening = False

        if self._position >= 100:
            self._is_closed = True
        else:
            self._is_closed = False

    def updateExternal(self, position, moving):
        self._position = 100-(position/100)

        if moving == "stop":
            self._is_closing = False
            self._is_opening = False
        if moving == "up":
            self._is_closing = False
            self._is_opening = True
        if moving == "down":
            self._is_closing = True
            self._is_opening = False

        if self._position >= 100:
            self._is_closed = True
        else:
            self._is_closed = False

        self.schedule_update_ha_state()
