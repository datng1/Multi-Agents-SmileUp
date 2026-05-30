from __future__ import annotations

import threading
from typing import Callable


ProgressCallback = Callable[[str, str], None]

_LOCAL = threading.local()


def set_workflow_progress_callback(callback: ProgressCallback | None) -> None:
    _LOCAL.callback = callback


def emit_workflow_progress(agent_name: str, status: str) -> None:
    callback = getattr(_LOCAL, "callback", None)
    if not callback:
        return
    try:
        callback(agent_name, status)
    except Exception:
        return
