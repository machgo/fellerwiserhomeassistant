# Feller Wiser for Home Assistant

Custom Home Assistant integration for local control of a Feller Wiser installation.

The integration connects directly to the Feller Wiser gateway over the local network, discovers supported loads and scenes, and exposes them as Home Assistant entities.

## Features

- Light entities for Feller Wiser `dim`, `dali`, and `onoff` loads
- Cover entities for Feller Wiser `motor` loads
- Button entities for Feller Wiser scenes
- Live state updates for lights and covers through the gateway websocket
- Local push integration type, no cloud service required

## Supported Entities

### Lights

Feller Wiser loads with type `dim`, `dali`, or `onoff` are exposed as Home Assistant lights.

Supported actions:

- Turn on
- Turn off
- Set brightness for dimmable loads
- Receive live brightness and on/off state updates

### Covers

Feller Wiser loads with type `motor` are exposed as Home Assistant covers.

Supported actions:

- Open
- Close
- Stop
- Set position
- Receive live position and movement state updates

### Scenes

Feller Wiser scenes are exposed as Home Assistant buttons.

Pressing a scene button triggers the matching Feller Wiser job.

## Requirements

- Home Assistant `2025.1` or newer
- A Feller Wiser gateway reachable from Home Assistant on the local network
- A Feller Wiser API key

The integration currently uses the gateway HTTP API and websocket endpoint at:

- `http://<host>/api/loads`
- `http://<host>/api/scenes`
- `ws://<host>/api`

## Installation

### HACS

1. Add this repository as a custom repository in HACS.
2. Select the integration category.
3. Install **Feller Wiser**.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/fellerwiser` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration

1. In Home Assistant, go to **Settings** > **Devices & services**.
2. Select **Add integration**.
3. Search for **Feller Wiser**.
4. Enter the gateway host and API key.

The host can be entered as an IP address, hostname, or URL. It is normalized and stored as `host[:port]`.

During setup, the integration calls `/api/loads` with the provided bearer token. Invalid credentials are rejected before the config entry is created.

## Getting an API Key

The Feller Wiser REST API must be unlocked by claiming an API user.
The gateway flashes its physical buttons for 30 seconds after the claim request.
Press one of the physical buttons during that window to approve the request.

Create a token:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"user":"homeassistant"}' \
  http://<host>/api/account/claim
```

If the claim succeeds, the response contains a `secret`. Use that `secret` as the API key in this integration.

You can verify the key before adding the integration:

```bash
curl -H "authorization: Bearer <api-key>" http://<host>/api/loads
```

Official authentication documentation:

https://github.com/Feller-AG/wiser-tutorial/blob/main/doc/authentication.md

## Current Limitations

- Discovery is based on the load and scene data returned by the Feller Wiser gateway.
- Lights and covers each maintain their own websocket listener.
- Scene entities are exposed as buttons, not as native Home Assistant scene entities.

## Issues

Report bugs and feature requests at:

https://github.com/machgo/fellerwiserhomeassistant/issues
