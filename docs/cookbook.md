# Cookbook

Practical prompts and CLI recipes for getting the most out of LogicaHome with any MCP-speaking AI.

These examples assume you've already run `logicahome init`, `logicahome connect <adapter>`, `logicahome discover`, and installed the MCP server in your client (`logicahome mcp install --client claude`).

---

## Talking to your AI

You don't need to memorize tool names. The AI picks the right tool from the schema. Phrase commands the way you'd talk to a person.

### Direct control

| What you say | What the AI does |
|---|---|
| *"Turn the living room lamp on."* | `turn_on(slug="living-room-lamp")` |
| *"Dim the bedroom to 30%."* | `set_brightness(slug="bedroom-lamp", brightness=30)` |
| *"Make the kitchen light warm white."* | `set_color(slug="kitchen-lamp", r=255, g=180, b=120)` |
| *"What's the temperature in the office?"* | `get_state(slug="office-thermostat")` |
| *"Turn everything off."* | `list_devices` then `turn_off` for each |

### Discovery and naming

| What you say | What happens |
|---|---|
| *"What devices do I have?"* | `list_devices` returns the registry |
| *"I just added a new bulb in the hall."* | `discover` re-scans every adapter |
| *"What's on right now?"* | `list_devices` then `get_state` for each |

### Scenes

Scenes are how you make a single phrase trigger many devices at once.

| What you say | What happens |
|---|---|
| *"Save the current state as 'movie night'."* | `snapshot_scene(slug="movie-night", name="Movie night")` |
| *"Activate movie night."* | `run_scene(slug="movie-night")` |
| *"What scenes do I have?"* | `list_scenes` |

You can also save scenes manually from the CLI for finer control — see below.

---

## CLI recipes

### Bootstrapping a fresh install

```bash
logicahome init
logicahome connect home-assistant   # if you run HA
logicahome connect tuya             # if you have SmartLife/Tuya
logicahome discover
logicahome device list              # confirm
logicahome mcp install --client claude
```

### Building a scene by hand

```bash
# 1. Set the room exactly how you want it
logicahome device on living-room-lamp
logicahome device brightness living-room-lamp 25
logicahome device on kitchen-lamp
logicahome device brightness kitchen-lamp 10

# 2. Capture it
logicahome scene snapshot dinner --name "Dinner" --description "Warm low light, kitchen dim"

# 3. Use it any time
logicahome scene run dinner
```

### Inspecting one device

```bash
logicahome device state bedroom-lamp
# {"on": true, "brightness": 60, "color_rgb": null, ...}
```

### Cleaning up

```bash
logicahome scene remove dinner            # forget a scene
logicahome scene list                     # confirm
```

---

## Common scene patterns

These are starting points. Adjust device slugs to match yours, then `snapshot` after you set the room manually.

### Bedtime

- All lights: off, except a hall night-light at 5%
- Smart plugs: TV off, fans on
- Thermostat: 19°C

```bash
# After arranging the room manually:
logicahome scene snapshot bedtime --name "Bedtime"
```

### Movie night

- Living room ceiling: off
- Backlight LED strip: 40%, warm
- Smart plug for popcorn: on (use `device on`, then snapshot)

### Welcome home

- Hall + living room: 80%
- Kitchen: 60%
- Music speaker plug: on

### Away

- Everything off
- Optional: a single hall light at 30% on a timer (configure on the device side; LogicaHome only flips it)

---

## When something goes wrong

### "No devices yet"

You configured an adapter but didn't run `discover`. Run it.

### "Adapter X is not configured"

The device exists in the registry, but the adapter that owns it isn't set up. Run `logicahome connect <adapter>` again.

### "Tuya status() failed"

Common causes:

- Device IP changed (DHCP). Re-run the wizard or update the IP in `config.yaml`.
- `local_key` rotated (rare). Re-run the wizard.
- Device unreachable on the LAN (Wi-Fi issue, device unplugged).

### "HA token invalid"

Long-lived access tokens never expire on Home Assistant *unless* the user explicitly revokes them. If you regenerated, re-run `logicahome connect home-assistant`.

### MCP client doesn't see the tools

- Restart the client (Claude Desktop, Cursor) after `logicahome mcp install`.
- Check that `which logicahome` returns a path the client can run (the install snippet uses the bare command).
- Verify by running `logicahome mcp serve` in a terminal — it should print nothing and wait. That's correct.

---

## Want to add something here?

Open a PR — `docs/cookbook.md` is the most user-facing file in the repo and benefits from real-world recipes. Include the prompt, the expected tool calls, and what a good AI response looks like.
