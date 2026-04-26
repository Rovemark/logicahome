# Writing an adapter

An adapter teaches LogicaHome how to talk to one ecosystem (Tuya, Home Assistant, Matter, Hue, Shelly, ...). Writing one is the smallest unit of contribution.

## The contract

Implement `logicahome.core.adapter.Adapter`. Four async methods:

```python
class MyAdapter(Adapter):
    name = "my_ecosystem"

    async def discover(self) -> list[Device]: ...
    async def get_state(self, device: Device) -> DeviceState: ...
    async def set_state(self, device: Device, **changes) -> DeviceState: ...
    async def close(self) -> None: ...
```

That's it. No callbacks, no events, no decorators.

## Step by step

### 1. Create the file

`src/logicahome/adapters/my_ecosystem.py`

### 2. Write the constructor

Validate config up front. If a required field is missing, raise `AdapterError` — LogicaHome will surface it cleanly.

```python
def __init__(self, config: dict[str, Any] | None = None) -> None:
    super().__init__(config)
    if not self.config.get("api_key"):
        raise AdapterError("my_ecosystem requires `api_key` in config")
```

### 3. Implement `discover`

Query the vendor's API or scan the LAN. Return a list of `Device` objects. Each device must have:

- `slug` — stable, lowercase, hyphenated (`bedroom-fan`)
- `native_id` — whatever the vendor uses to address the device
- `adapter` — your adapter `name`
- `capabilities` — list of `DeviceCapability` values
- `name` — human-readable

### 4. Implement `get_state` and `set_state`

`get_state` returns a `DeviceState` with whatever fields you can fill (it's all optional).

`set_state` accepts kwargs corresponding to `DeviceState` fields. Translate them to the vendor's API. Return the new state (refetch if needed — accuracy beats latency).

### 5. Implement `close`

Release HTTP sessions, sockets, threads. LogicaHome calls this on shutdown.

### 6. Register the adapter

Add an entry to `ADAPTERS` in [`src/logicahome/adapters/base.py`](../src/logicahome/adapters/base.py):

```python
ADAPTERS = {
    ...
    "my_ecosystem": "logicahome.adapters.my_ecosystem:MyAdapter",
}
```

### 7. Document config

Add a config example to your adapter module's docstring. Users will paste it into `config.yaml`.

### 8. Tests

`tests/adapters/test_my_ecosystem.py`. Mock the vendor API at the HTTP/socket level using `aiohttp` test utilities or `respx`. Don't mock at the adapter method level — that defeats the test.

### 9. Optional dependencies

If your adapter needs a heavyweight library (`paho-mqtt`, `python-matter-server`, etc), put it under an extras entry in `pyproject.toml`:

```toml
[project.optional-dependencies]
my_ecosystem = ["paho-mqtt>=2.0"]
```

Import it inside the constructor and raise `AdapterError` if missing — see the Tuya adapter for the pattern.

## Style

- Async everything. No `requests`, no blocking I/O.
- One file per adapter. Helpers go inline unless they cross adapters.
- Type hints required.
- Errors raise `AdapterError` with a message that points to the fix.

## Reference adapters

- [`tuya.py`](../src/logicahome/adapters/tuya.py) — local LAN, optional dep, config-driven
- [`home_assistant.py`](../src/logicahome/adapters/home_assistant.py) — REST, async HTTP session, dynamic discovery
