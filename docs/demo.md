# Recording the demo GIF

The README links to `docs/demo.gif` once it exists. This page is the recording script — follow it once, drop the resulting file into `docs/demo.gif`, and the README link starts working.

## Setup

1. Connect at least one real device via `logicahome connect <adapter>`.
2. Run `logicahome discover`.
3. Install in Claude Desktop: `logicahome mcp install --client claude` then restart Claude Desktop.
4. Make sure the device is in a known starting state (lamp off, full brightness).

## Recording

Use any screen recorder (macOS: built-in QuickTime, or `ffmpeg`/`asciinema`+`agg`). Aim for **20–30 seconds**, **800×500** or 16:10.

### Sequence

1. (2s) Show the LogicaHome README badge row centered on screen.
2. (2s) Cut to terminal: type `logicahome device list` — table appears.
3. (3s) Cut to Claude Desktop. Type: *"Turn the living room lamp to 30%."*
4. (4s) Show the AI calling `set_brightness` and the lamp dimming on a small picture-in-picture of the actual lamp.
5. (3s) Type: *"Save this as movie night."*
6. (3s) AI calls `snapshot_scene`. Confirm in terminal: `logicahome scene list` shows the new scene.
7. (3s) Type: *"Now turn everything off."*
8. (3s) AI calls `turn_off` for each device. Lamp goes dark.
9. (2s) End frame: `logicahome` ASCII title + GitHub URL.

### Export

- Format: GIF, optimized (target < 4 MB).
- Save as: `docs/demo.gif`.
- Update the README intro line to remove the "coming soon" wrapper.
