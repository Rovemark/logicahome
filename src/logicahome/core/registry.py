"""Device registry — single source of truth for known devices.

Persists to SQLite under the user config dir. Adapters register devices
on discovery; CLI and MCP server query through here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite
from platformdirs import user_config_dir

from logicahome.core.device import Device, DeviceCapability
from logicahome.core.scene import Scene, SceneAction


def _config_dir() -> Path:
    path = Path(user_config_dir("logicahome", appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_db_path() -> Path:
    return _config_dir() / "registry.db"


SCHEMA_VERSION = 2

MIGRATIONS: list[str] = [
    # v1 — initial schema (devices + scenes)
    """
    CREATE TABLE IF NOT EXISTS devices (
        slug TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        adapter TEXT NOT NULL,
        native_id TEXT NOT NULL,
        capabilities TEXT NOT NULL,
        room TEXT,
        manufacturer TEXT,
        model TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        UNIQUE(adapter, native_id)
    );

    CREATE INDEX IF NOT EXISTS idx_devices_adapter ON devices(adapter);
    CREATE INDEX IF NOT EXISTS idx_devices_room ON devices(room);

    CREATE TABLE IF NOT EXISTS scenes (
        slug TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        actions TEXT NOT NULL
    );
    """,
    # v2 — schema versioning table
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
]


class Registry:
    """Persistent device registry backed by SQLite."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            current = await self._current_version(db)
            for i, migration_sql in enumerate(MIGRATIONS, start=1):
                if i > current:
                    await db.executescript(migration_sql)
            await db.execute(
                "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', ?)",
                (str(SCHEMA_VERSION),),
            )
            await db.commit()

    @staticmethod
    async def _current_version(db: Any) -> int:
        try:
            row = await (
                await db.execute("SELECT value FROM schema_meta WHERE key='version'")
            ).fetchone()
            return int(row["value"]) if row else 0
        except Exception:
            return 0

    async def upsert(self, device: Device) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO devices (slug, name, adapter, native_id, capabilities,
                                     room, manufacturer, model, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(adapter, native_id) DO UPDATE SET
                    slug=excluded.slug,
                    name=excluded.name,
                    capabilities=excluded.capabilities,
                    room=excluded.room,
                    manufacturer=excluded.manufacturer,
                    model=excluded.model,
                    metadata=excluded.metadata
                """,
                (
                    device.slug,
                    device.name,
                    device.adapter,
                    device.native_id,
                    json.dumps([c.value for c in device.capabilities]),
                    device.room,
                    device.manufacturer,
                    device.model,
                    json.dumps(device.metadata),
                ),
            )
            await db.commit()

    async def list_all(self) -> list[Device]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            rows = await (await db.execute("SELECT * FROM devices ORDER BY name")).fetchall()
            return [self._row_to_device(r) for r in rows]

    async def get(self, slug: str) -> Device | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await (
                await db.execute("SELECT * FROM devices WHERE slug = ?", (slug,))
            ).fetchone()
            return self._row_to_device(row) if row else None

    async def remove(self, slug: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM devices WHERE slug = ?", (slug,))
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_device(row: Any) -> Device:
        return Device(
            slug=row["slug"],
            name=row["name"],
            adapter=row["adapter"],
            native_id=row["native_id"],
            capabilities=[DeviceCapability(c) for c in json.loads(row["capabilities"])],
            room=row["room"],
            manufacturer=row["manufacturer"],
            model=row["model"],
            metadata=json.loads(row["metadata"]),
        )

    # --- scenes ------------------------------------------------------------

    async def upsert_scene(self, scene: Scene) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO scenes (slug, name, description, actions)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    actions=excluded.actions
                """,
                (
                    scene.slug,
                    scene.name,
                    scene.description,
                    json.dumps([a.model_dump() for a in scene.actions]),
                ),
            )
            await db.commit()

    async def list_scenes(self) -> list[Scene]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            rows = await (await db.execute("SELECT * FROM scenes ORDER BY name")).fetchall()
            return [self._row_to_scene(r) for r in rows]

    async def get_scene(self, slug: str) -> Scene | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await (
                await db.execute("SELECT * FROM scenes WHERE slug = ?", (slug,))
            ).fetchone()
            return self._row_to_scene(row) if row else None

    async def remove_scene(self, slug: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM scenes WHERE slug = ?", (slug,))
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_scene(row: Any) -> Scene:
        return Scene(
            slug=row["slug"],
            name=row["name"],
            description=row["description"],
            actions=[SceneAction(**a) for a in json.loads(row["actions"])],
        )
