"""Weld design checks (AISC 360-22)."""

from __future__ import annotations

from .models import WeldCheckDetail, WeldCheckResult
from .aisc import check_aisc


def check_weld_group(
    result,
    *,
    standard: str = "aisc",
    theta_deg: float | None = None,
    F_EXX: float | None = None,
    enforce_max_fillet_size: bool = True,
) -> WeldCheckResult:
    """
    Check a weld group result per AISC 360-22.

    Notes:
    - Easy mode supports fillet welds with conservative defaults.
    - Other weld types require advanced inputs and are not auto-checked here.
    """
    standard_norm = standard.lower()
    if standard_norm != "aisc":
        raise ValueError("standard must be 'aisc'")

    if F_EXX is None:
        # Matching electrode assumption (conservative): use weaker/thinner base metal Fu.
        F_EXX_value = float(result.connection.base_metal.fu)
    else:
        F_EXX_value = float(F_EXX)

    return check_aisc(
        result=result,
        theta_deg=theta_deg,
        F_EXX=F_EXX_value,
        enforce_max_fillet_size=bool(enforce_max_fillet_size),
    )


__all__ = [
    "WeldCheckDetail",
    "WeldCheckResult",
    "check_weld_group",
    "check_aisc",
]


