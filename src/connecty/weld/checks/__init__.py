"""Weld design checks (AISC 360-22)."""

from __future__ import annotations

from .models import WeldCheckDetail, WeldCheckResult
from .aisc import check_aisc


def check_weld_group(
    result,
    *,
    standard: str = "aisc",
    F_EXX: float | None = None,
    enforce_max_fillet_size: bool = True,
    conservative_k_ds: bool = False,
) -> WeldCheckResult:
    """
    Check a weld group result per AISC 360-22.

    Notes:
    - Easy mode supports fillet welds with conservative defaults.
    - Other weld types require advanced inputs and are not auto-checked here.
    - By default, automatically computes theta at the governing location (max utilization)
      to claim the AISC k_ds directional strength benefit safely.
    - Set conservative_k_ds=True to force k_ds=1.0 (ignores directional benefit).
    """
    standard_norm = standard.lower()
    if standard_norm != "aisc":
        raise ValueError("standard must be 'aisc'")

    if getattr(result.connection, "base_metal", None) is None:
        raise ValueError("WeldConnection.base_metal is required for weld checks.")

    if F_EXX is None:
        # Prefer explicit weld params strength; else matching-electrode assumption: F_EXX = base metal Fu.
        params_F_EXX = getattr(result.connection.params, "F_EXX", None)
        if params_F_EXX is not None:
            F_EXX_value = float(params_F_EXX)
        else:
            F_EXX_value = float(result.connection.base_metal.fu)
    else:
        F_EXX_value = float(F_EXX)

    return check_aisc(
        result=result,
        F_EXX=F_EXX_value,
        enforce_max_fillet_size=bool(enforce_max_fillet_size),
        conservative_k_ds=bool(conservative_k_ds),
    )


__all__ = [
    "WeldCheckDetail",
    "WeldCheckResult",
    "check_weld_group",
    "check_aisc",
]


