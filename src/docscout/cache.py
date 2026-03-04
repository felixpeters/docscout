"""SQLite cache layer for docscout."""

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from docscout.models import FileResult

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS file_cache (
    file_path     TEXT PRIMARY KEY,
    file_size     INTEGER NOT NULL,
    file_mtime    REAL NOT NULL,
    result_json   TEXT NOT NULL,
    cached_at     TEXT NOT NULL
);
"""


def _default_cache_dir() -> Path:
    """Return the default cache directory using XDG_CACHE_HOME."""
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "docscout"
    return Path.home() / ".cache" / "docscout"


class Cache:
    """SQLite-backed file result cache."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or _default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self._connect()

    def _connect(self) -> None:
        try:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute(_SCHEMA)
            self._conn.commit()
        except sqlite3.DatabaseError:
            print("Warning: cache corrupted, recreating.", file=sys.stderr)
            self.db_path.unlink(missing_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute(_SCHEMA)
            self._conn.commit()

    def get(self, path: Path) -> FileResult | None:
        """Look up a cached result. Returns None if missing or stale."""
        abs_path = str(path.resolve())
        try:
            stat = path.stat()
        except OSError:
            return None

        row = self._conn.execute(
            "SELECT file_size, file_mtime, result_json FROM file_cache WHERE file_path = ?",
            (abs_path,),
        ).fetchone()

        if row is None:
            return None

        cached_size, cached_mtime, result_json = row
        if cached_size != stat.st_size or cached_mtime != stat.st_mtime:
            return None

        return FileResult.model_validate_json(result_json)

    def put(self, path: Path, result: FileResult) -> None:
        """Upsert a cache entry."""
        abs_path = str(path.resolve())
        stat = path.stat()
        self._conn.execute(
            "INSERT OR REPLACE INTO file_cache (file_path, file_size, file_mtime, result_json, cached_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                abs_path,
                stat.st_size,
                stat.st_mtime,
                result.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def invalidate(self, path: Path) -> None:
        """Delete a cache entry."""
        abs_path = str(path.resolve())
        self._conn.execute("DELETE FROM file_cache WHERE file_path = ?", (abs_path,))
        self._conn.commit()

    def clear(self) -> None:
        """Drop all cache entries."""
        self._conn.execute("DELETE FROM file_cache")
        self._conn.commit()
