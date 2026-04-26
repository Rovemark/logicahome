# Contributing to LogicaHome

Thank you for considering a contribution. The shortest path to becoming a contributor is shipping a new adapter — see [docs/writing-adapters.md](docs/writing-adapters.md).

## Ground rules

- **Local-first.** No adapter may require an outbound cloud call when a local protocol exists. If the vendor has no local API, document the trade-off in the adapter's docstring.
- **No telemetry.** LogicaHome never reports back to anyone.
- **Apache 2.0 only.** All contributions are under the project license. By submitting a PR you agree to that.
- **Adapters must be optional.** Heavy/proprietary deps (e.g. `tinytuya`) live behind extras (`pip install logicahome[tuya]`).

## Dev setup

```bash
git clone https://github.com/Rovemark/logicahome.git
cd logicahome
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,all]"
ruff check src tests
pytest
```

## Pull requests

- One change per PR.
- Tests for new behavior. Stubs and mocks for vendor APIs are fine.
- Run `ruff check` and `ruff format` before pushing.
- Keep README + docs/ in sync if the surface changes.

## Adding an adapter

See [docs/writing-adapters.md](docs/writing-adapters.md). The four async methods you must implement: `discover`, `get_state`, `set_state`, `close`.

## Reporting a bug

Open an issue with: LogicaHome version, Python version, OS, the adapter involved, the exact command or MCP call, and the full traceback. Sanitize tokens and IPs before pasting.
