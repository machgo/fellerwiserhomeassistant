"""Platform for Scene integration."""
from __future__ import annotations

import logging

import requests
import websockets
import asyncio
import json
import socket

from .const import (
    DOMAIN,
)

# Import the device class from the component that you want to support
from homeassistant.components.button import (
    ButtonEntity,
)

_LOGGER = logging.getLogger(__name__)

def updatedata(host, apikey):
    return requests.get(
        f"http://{host}/api/scenes", headers={"authorization": f"Bearer {apikey}"}
    )


async def async_setup_entry(hass, entry, async_add_entities):
    host = entry.data["host"]
    apikey = entry.data["apikey"]

    response = await hass.async_add_executor_job(updatedata, host, apikey)

    scene_resp = response.json()

    scenes = []
    for value in scene_resp["data"]:
        scenes.append(FellerScene(value, host, apikey))

    # asyncio.get_event_loop().create_task(hello(scenes, hass, host, apikey))
    async_add_entities(scenes, True)


class FellerScene(ButtonEntity):
    """Representation of an Awesome Scene."""

    def __init__(self, data, host, apikey) -> None:
        """Initialize an AwesomeScene."""
        # scene { "type": 20, "name": "Alle Storen auf", "sceneButtons": [], "kind": 24, "id": 211, "job": 210 }

        self._data = data
        self._name = data["name"]
        self._id = str(data["id"])
        self._type = data["type"]
        self._kind = data["kind"]
        self._job = data["job"]
        self._host = host
        self._apikey = apikey

    @property
    def name(self) -> str:
        """Return the display name of this scene."""
        return self._name

    @property
    def unique_id(self):
        return "scene-" + self._id

    def press(self) -> None:
        """Handle the button press."""
        requests.get(
            f"http://{self._host}/api/jobs/{self._job}/trigger",
            headers={"authorization": f"Bearer {self._apikey}"},
        )
        # _LOGGER.info(response.json())

    def updatestate(self):
        ip = self._host
        # _LOGGER.info("requesting http://"+ip+"/api/scenes/"+self._id)
        return requests.get(
            f"http://{self._host}/api/jobs/{self._id}",
            headers={"authorization": f"Bearer {self._apikey}"},
        )

    def update(self) -> None:
        """Fetch new state data for this scene.
        This is the only method that should fetch new data for Home Assistant.
        """
        response = self.updatestate()
        scene = response.json()
        _LOGGER.info(scene)