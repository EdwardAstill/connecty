"""Shared result models for weld design checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WeldCheckDetail:
    weld_type: str
    leg: float
    throat: float
    L_weld: float
    theta_deg: float | None
    k_ds: float
    F_EXX: float
    stress_demand: float
    Ru_equiv: float
    weld_capacity: float
    base_capacity: float | None
    detailing_w_max: float | None
    weld_util: float
    base_util: float | None
    detailing_max_util: float | None
    governing_util: float
    governing_limit_state: str
    calc: dict[str, Any] = field(default_factory=dict)

    @property
    def info(self) -> dict[str, Any]:
        return {
            "weld_type": self.weld_type,
            "leg": self.leg,
            "throat": self.throat,
            "L_weld": self.L_weld,
            "theta_deg": self.theta_deg,
            "k_ds": self.k_ds,
            "F_EXX": self.F_EXX,
            "stress_demand_MPa": self.stress_demand,
            "Ru_equiv_N": self.Ru_equiv,
            "weld_capacity_N": self.weld_capacity,
            "base_capacity_N": self.base_capacity,
            "detailing_w_max": self.detailing_w_max,
            "weld_util": self.weld_util,
            "base_util": self.base_util,
            "detailing_max_util": self.detailing_max_util,
            "governing_util": self.governing_util,
            "governing_limit_state": self.governing_limit_state,
            "calc": dict(self.calc),
        }


@dataclass
class WeldCheckResult:
    method: str
    details: list[WeldCheckDetail] = field(default_factory=list)
    governing_limit_state: str | None = None
    governing_utilization: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "governing_limit_state": self.governing_limit_state,
            "governing_utilization": self.governing_utilization,
            "meta": dict(self.meta),
            "details": [d.info for d in self.details],
        }

    @property
    def info(self) -> dict[str, Any]:
        return self.to_dict()


def get_governing(details: list[WeldCheckDetail]) -> tuple[str | None, float]:
    """Return (limit_state, utilization) for the governing weld group."""
    if not details:
        return None, 0.0
    _, detail = max(enumerate(details), key=lambda item: item[1].governing_util)
    return detail.governing_limit_state, float(detail.governing_util)


__all__ = ["WeldCheckDetail", "WeldCheckResult", "get_governing"]


