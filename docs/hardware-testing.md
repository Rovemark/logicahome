# Hardware testing checklist

Tests in CI prove the code parses and the helpers translate. They do not prove a lamp turns on. This page is the gap between green CI and "it works".

Run through this checklist any time you cut a release that touches an adapter.

## Tuya / SmartLife

- [ ] `logicahome connect tuya` completes without errors and creates `devices.json`.
- [ ] `logicahome discover` registers at least one device.
- [ ] `logicahome device list` shows the device with sensible capabilities.
- [ ] `logicahome device on <slug>` — physical confirmation: lamp lights up.
- [ ] `logicahome device brightness <slug> 30` — physical confirmation: visibly dimmer.
- [ ] `logicahome device off <slug>` — physical confirmation: lamp turns off.
- [ ] If color: `logicahome device on <slug>` then via Claude Desktop ask for blue / red / green and confirm.
- [ ] Re-run after rebooting the device — adapter recovers without re-pairing.

## Home Assistant

- [ ] `logicahome connect home-assistant` validates against `/api/`.
- [ ] `logicahome discover` lists entities matching `include_domains`.
- [ ] One entity per supported domain controlled successfully:
  - [ ] `light` (on/off, brightness, color)
  - [ ] `switch` (on/off)
  - [ ] `climate` (`set_temperature`)
  - [ ] `lock` (lock/unlock)
  - [ ] `cover` (open/close, set position)
  - [ ] `media_player` (play/pause, volume)

## Hue

- [ ] `logicahome connect hue` succeeds after pressing the link button.
- [ ] `logicahome discover` lists every bulb.
- [ ] On/off, brightness, color (RGB), color temperature all work end-to-end.

## Shelly

- [ ] Manual config entry produces a valid device.
- [ ] Gen1 device: `/relay/<n>?turn=on` works.
- [ ] Gen2 device: `Switch.Set` RPC works.
- [ ] Power readings appear in `get_state` for plugs that support it.

## ESPHome

- [ ] Connect to a device with a switch entity, toggle works.
- [ ] Connect to a device with a light entity, brightness works.

## Scenes (cross-adapter)

- [ ] Save a scene with devices from at least two adapters.
- [ ] `run_scene` reports `ok: true` for each device.
- [ ] Verified physically — every device matches the snapshot.
- [ ] One device intentionally offline — others still apply, error reported for the offline one only.

## MCP integration

- [ ] Claude Desktop sees the 10 tools after `mcp install --client claude` + restart.
- [ ] `logicahome mcp serve --http --port 8765` boots and accepts SSE on `/sse`.
- [ ] Asking the AI client "list my devices" returns clean JSON, not a traceback.
- [ ] Triggering a scene by name from the AI works end-to-end.
