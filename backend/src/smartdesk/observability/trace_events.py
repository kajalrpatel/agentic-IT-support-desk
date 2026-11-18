"""Structured operational events in server logs and the active LangSmith span."""

from datetime import UTC, datetime

import structlog
from langsmith import get_current_run_tree


def record_event(name: str, **attributes: str | int | float | bool | None) -> None:
    # Callers provide diagnostic categories/counts, never message bodies or credentials.
    structlog.get_logger().info(name, **attributes)
    run = get_current_run_tree()
    if run is not None:
        run.add_event({"name": name, "time": datetime.now(UTC).isoformat(), "kwargs": attributes})
