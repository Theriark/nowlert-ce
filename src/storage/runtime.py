"""Opt-in runtime initialization for persistent v2 platform state."""

from __future__ import annotations

import sys

from pathlib import Path

from environment import compatible_environment
from storage.database import Database


DEFAULT_STATE_DIRECTORY = "/nowlert/config/platform-state"


def state_directory(configuration) -> Path:
    configured = compatible_environment(
        "NOWLERT_STATE_DIR",
    ) or configuration.get(
        "platform",
        "state_dir",
        default=DEFAULT_STATE_DIRECTORY,
    )
    path = Path(str(configured or "")).expanduser()
    if not path.is_absolute():
        raise ValueError("platform.state_dir must be an absolute path")
    if path == Path("/"):
        raise ValueError("platform.state_dir must not be the filesystem root")
    return path


def initialize_state(configuration) -> Database | None:
    """Initialize platform state unless an operator explicitly disables it."""

    enabled = configuration.get("platform", "enabled", default=None)
    if enabled is False:
        return None
    database = Database(state_directory(configuration) / "nowlert.db")
    try:
        database.migrate()
    except OSError as error:
        if enabled is True:
            raise
        print(
            "WARNING: automatic WebUI state could not be initialized; "
            "the legacy notification pipeline will continue. Configure a "
            f"writable platform.state_dir to enable the WebUI ({error}).",
            file=sys.stderr,
            flush=True,
        )
        return None
    return database
