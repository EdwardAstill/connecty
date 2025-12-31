"""Bolt design checks (AISC 360-22 and AS 4100)."""

from __future__ import annotations

from .models import BoltCheckDetail, BoltCheckResult, get_governing
from .aisc import check_aisc
from .as4100 import check_as4100


def check_bolt_group(
    result,
    *,
    standard: str | None = None,
    connection_type: str | None = None,
    hole_type: str = "standard",
    slot_orientation: str = "perpendicular",
    threads_in_shear_plane: bool = True,
    slip_class: str = "A",
    n_s: int | None = None,
    fillers: int = 0,
    n_b_tension: int | None = None,
    hole_type_factor: float = 1.0,
    slip_coefficient: float = 0.35,
    n_e: int = 1,
    nn_shear_planes: int = 1,
    nx_shear_planes: int = 0,
    prying_allowance: float = 0.25,
    reduction_factor_kr: float = 1.0,
    tension_per_bolt: float | None = None,
    pretension_override: float | None = None,
    require_explicit_tension: bool = False,
    assume_uniform_tension_if_missing: bool = True,
) -> BoltCheckResult:
    """Check a bolt group result per AISC 360-22 or AS 4100."""
    bolt = result.connection.bolt
    grade = bolt.grade
    bolt_diameter = float(bolt.diameter)
    plate = result.connection.plate

    if plate is None:
        raise ValueError("Plate is required for bolt checks (bearing/tear-out geometry).")
    if grade is None:
        raise ValueError("BoltParams.grade is required for bolt code checks (AISC/AS4100).")

    if standard is None:
        standard = "aisc" if grade in ("A325", "A490") else "as4100"

    standard_norm = standard.lower()
    connection_type_norm = connection_type or "bearing"

    if standard_norm == "aisc":
        # In AISC, `n_s` is used for:
        # - number of shear planes (shear strength)
        # - number of slip planes (slip-critical strength)
        # If not provided, default to the connection's configured number of shear planes.
        if n_s is None:
            n_s = int(getattr(result.connection, "n_shear_planes", 1))
        return check_aisc(
            result=result,
            grade=grade,
            bolt_diameter=bolt_diameter,
            plate=plate,
            connection_type=connection_type_norm,
            hole_type=hole_type,
            slot_orientation=slot_orientation,
            threads_in_shear_plane=threads_in_shear_plane,
            slip_class=slip_class,
            n_s=n_s,
            fillers=fillers,
            n_b_tension=n_b_tension,
            tension_per_bolt=tension_per_bolt,
            pretension_override=pretension_override,
        )

    if standard_norm == "as4100":
        return check_as4100(
            result=result,
            grade=grade,
            bolt_diameter=bolt_diameter,
            plate=plate,
            connection_type=connection_type_norm,
            hole_type=hole_type,
            hole_type_factor=hole_type_factor,
            slip_coefficient=slip_coefficient,
            n_e=n_e,
            nn_shear_planes=nn_shear_planes,
            nx_shear_planes=nx_shear_planes,
            prying_allowance=prying_allowance,
            reduction_factor_kr=reduction_factor_kr,
            tension_per_bolt=tension_per_bolt,
            pretension_override=pretension_override,
            require_explicit_tension=require_explicit_tension,
            assume_uniform_tension_if_missing=assume_uniform_tension_if_missing,
        )

    raise ValueError("standard must be 'aisc' or 'as4100'")


__all__ = [
    "BoltCheckDetail",
    "BoltCheckResult",
    "check_bolt_group",
    "check_aisc",
    "check_as4100",
]


