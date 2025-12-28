"""Shared result models for bolt design checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BoltCheckDetail:
    bolt_index: int
    point: tuple[float, float]
    shear_demand: float
    tension_demand: float
    shear_capacity: float
    tension_capacity: float
    bearing_capacity: float
    slip_capacity: float | None
    shear_util: float
    tension_util: float
    bearing_util: float
    slip_util: float | None
    governing_util: float
    governing_limit_state: str
    interaction_util: float = 0.0
    calc: dict[str, Any] = field(default_factory=dict)

    @property
    def info(self) -> dict[str, Any]:
        return {
            "bolt_index": self.bolt_index,
            "point": self.point,
            "shear_demand_kN": self.shear_demand,
            "tension_demand_kN": self.tension_demand,
            "shear_capacity_kN": self.shear_capacity,
            "tension_capacity_kN": self.tension_capacity,
            "bearing_capacity_kN": self.bearing_capacity,
            "slip_capacity_kN": self.slip_capacity,
            "shear_util": self.shear_util,
            "tension_util": self.tension_util,
            "bearing_util": self.bearing_util,
            "slip_util": self.slip_util,
            "interaction_util": self.interaction_util,
            "governing_util": self.governing_util,
            "governing_limit_state": self.governing_limit_state,
            "calc": dict(self.calc),
        }


@dataclass
class BoltCheckResult:
    connection_type: str
    method: str
    details: list[BoltCheckDetail] = field(default_factory=list)
    governing_bolt_index: int | None = None
    governing_limit_state: str | None = None
    governing_utilization: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def info(self) -> dict[str, Any]:
        return {
            "connection_type": self.connection_type,
            "method": self.method,
            "governing_bolt_index": self.governing_bolt_index,
            "governing_limit_state": self.governing_limit_state,
            "governing_utilization": self.governing_utilization,
            "meta": dict(self.meta),
            "details": [d.info for d in self.details],
        }


def get_governing(details: list[BoltCheckDetail]) -> tuple[int | None, str | None, float]:
    """Return (index, limit_state, utilization) for the governing bolt."""
    if not details:
        return None, None, 0.0
    idx, detail = max(enumerate(details), key=lambda item: item[1].governing_util)
    return idx, detail.governing_limit_state, detail.governing_util


__all__ = ["BoltCheckDetail", "BoltCheckResult", "get_governing"]


