"""Dev/demo provisioning: share a new sensor's token with the local simulator.

Only used when SIMULATOR_AUTO_PROVISION is enabled. Writes are atomic so the
simulator, which reloads the file periodically, never reads a partial file.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)
_lock = threading.Lock()


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def provision_simulator_token(tokens_file: str, sensor_id: str, token: str) -> bool:
    """Add sensor_id -> token to the simulator tokens file. Returns True on success."""
    path = Path(tokens_file)
    with _lock:
        try:
            tokens = json.loads(path.read_text()) if path.exists() else {}
            tokens[sensor_id] = token
            write_json_atomic(path, tokens)
        except (OSError, ValueError) as exc:
            logger.warning("Could not provision simulator token for %s: %s", sensor_id, exc)
            return False
    logger.info("Provisioned simulator token for %s", sensor_id)
    return True
