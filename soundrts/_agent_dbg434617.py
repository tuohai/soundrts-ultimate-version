"""Session 434617 perf-debug counters (NDJSON → debug-434617.log)."""
from __future__ import annotations

import json
import time
from pathlib import Path

_LOG = Path(__file__).resolve().parents[1] / "debug-434617.log"
_C: dict[str, int] = {}


def inc(key: str, n: int = 1) -> None:
    _C[key] = _C.get(key, 0) + n


def dump(message: str = "counters", hypothesis_id: str = "summary", run_id: str = "pre") -> None:
    # #region agent log
    payload = {
        "sessionId": "434617",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": "soundrts/_agent_dbg434617.py:dump",
        "message": message,
        "data": dict(_C),
        "timestamp": int(time.time() * 1000),
    }
    with _LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    # #endregion


def reset() -> None:
    _C.clear()
