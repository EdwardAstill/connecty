"""AISC 360-22 weld checks (fillet welds, LRFD)."""

from __future__ import annotations

import math

from .models import WeldCheckDetail, WeldCheckResult, get_governing


def _auto_compute_governing_theta(result) -> float | None:
    """
    Compute theta corresponding to the governing (maximum utilization) point.
    
    This function scans all discretized points and finds the one that maximizes
    the ratio (stress / k_ds), which corresponds to the highest utilization.
    
    Args:
        result: LoadedWeldConnection result object
        
    Returns:
        Angle in degrees that corresponds to the governing limit state, or None.
    """
    # Check if result has analysis attribute (real LoadedWeldConnection vs test dummy)
    if not hasattr(result, 'analysis'):
        return None
    
    analysis = result.analysis
    if not analysis.point_stresses:
        return None
    
    # Get tangents at discretized points
    weld = result.connection.weld
    points_ds = weld._discretize(result.discretization)
    
    # Ensure lists are aligned (sanity check)
    if len(analysis.point_stresses) != len(points_ds):
        # Fallback: if lengths mismatch, we cannot reliably map stresses to tangents.
        # Return None -> k_ds=1.0 (conservative)
        return None
        
    best_util_proxy = -1.0
    governing_theta = None
    
    for ps, (pt_ds, _, (tan_y, tan_z), _) in zip(analysis.point_stresses, points_ds):
        stress = ps.stress
        if stress < 1e-6:
            continue
            
        # Local in-plane resultant direction
        fy = float(ps.components.total_y)
        fz = float(ps.components.total_z)
        mag = math.hypot(fy, fz)
        
        if mag < 1e-12:
            # Pure axial/moment with no shear? unlikely for general case but possible.
            # If no shear direction, assume worst case for k_ds benefit (min benefit).
            theta = 0.0
            k_ds = 1.0
        else:
            dir_y = fy / mag
            dir_z = fz / mag
            
            # Angle between force and tangent
            # Tangent is unit vector (tan_y, tan_z)
            cos_theta = abs(dir_y * float(tan_y) + dir_z * float(tan_z))
            cos_theta = min(max(cos_theta, 0.0), 1.0)
            theta = math.degrees(math.acos(cos_theta))
            k_ds = _aisc_kds(theta)
            
        # Utilization proxy = stress / k_ds
        # (Capacity R_n proportional to k_ds)
        util_proxy = stress / k_ds
        
        if util_proxy > best_util_proxy:
            best_util_proxy = util_proxy
            governing_theta = theta
            
    return governing_theta


def _aisc_kds(theta_deg: float) -> float:
    theta = abs(float(theta_deg))
    sin_val = abs(math.sin(math.radians(theta)))
    return 1.0 + 0.50 * (sin_val**1.5)


def _aisc_max_fillet_size_metric(t: float) -> float:
    """
    Maximum fillet size detailing limit (metric), for fillets along a part edge.

    weld.md definition:
      w_max = t              for t < 6 mm
      w_max = t - 2 mm       for t >= 6 mm
    """
    thickness = float(t)
    if thickness < 6.0:
        return thickness
    return thickness - 2.0


def check_aisc(
    *,
    result,
    F_EXX: float,
    enforce_max_fillet_size: bool,
    conservative_k_ds: bool = False,
) -> WeldCheckResult:
    """
    Check a weld analysis result per AISC 360-22 (fillet welds, LRFD).

    This check is intentionally conservative and aligns with documentation/standards/weld.md.
    
    Args:
        result: LoadedWeldConnection result
        F_EXX: Electrode strength (MPa)
        enforce_max_fillet_size: Check maximum fillet size detailing limit
        conservative_k_ds: If True, force k_ds=1.0 (ignores directional benefit)
    """
    connection = result.connection
    weld = connection.weld
    params = weld.parameters

    if params.type != "fillet":
        raise ValueError("AISC weld checks are implemented for fillet welds only (easy mode).")

    if params.leg is None or params.throat is None:
        raise ValueError("Fillet weld checks require leg (w) and throat (t_e).")

    # Geometry
    w = float(params.leg)
    throat = float(params.throat)
    L_weld = float(weld.L)
    A_we = float(weld.A)  # throat * length

    # Demand from analysis (stress-based, method-aware)
    stress_demand = float(result.max_stress)  # MPa (N/mm^2) if using mm+N
    Ru_equiv = stress_demand * A_we  # N

    # k_ds: automatic by default, can be disabled
    if connection.is_rect_hss_end_connection or conservative_k_ds:
        # HSS end connection restriction OR user requests conservative approach
        k_ds = 1.0
        theta_used = None
    else:
        # Automatically compute theta at governing (max utilization) location
        theta_computed = _auto_compute_governing_theta(result)
        if theta_computed is None:
            k_ds = 1.0
            theta_used = None
        else:
            k_ds = _aisc_kds(theta_computed)
            theta_used = float(theta_computed)

    # Weld metal capacity (AISC J2.2, LRFD)
    phi_w = 0.75
    weld_capacity = phi_w * 0.60 * float(F_EXX) * A_we * k_ds  # N
    weld_util = Ru_equiv / weld_capacity if weld_capacity > 0.0 else math.inf

    # Base metal capacity at fusion face (J4 via Table J2.5)
    n_f = 2 if connection.is_double_fillet else 1
    t = float(connection.base_metal.t)
    Fy = float(connection.base_metal.fy)
    Fu = float(connection.base_metal.fu)

    A_BM = float(n_f) * t * L_weld
    base_phiRn_yield = 1.00 * 0.60 * Fy * A_BM
    base_phiRn_rupture = 0.75 * 0.60 * Fu * A_BM
    base_capacity = min(base_phiRn_yield, base_phiRn_rupture)
    base_util = Ru_equiv / base_capacity if base_capacity > 0.0 else math.inf

    # Detailing: max fillet size (flag by default)
    detailing_w_max: float | None
    detailing_max_util: float | None
    if enforce_max_fillet_size:
        detailing_w_max = _aisc_max_fillet_size_metric(t)
        detailing_max_util = w / detailing_w_max if detailing_w_max > 0.0 else math.inf
    else:
        detailing_w_max = None
        detailing_max_util = None

    utils: list[tuple[float, str]] = [(weld_util, "weld_metal"), (base_util, "base_metal_fusion_face")]
    if detailing_max_util is not None:
        utils.append((detailing_max_util, "detailing_max_fillet"))

    governing_util, governing_state = max(utils, key=lambda item: item[0])

    calc: dict[str, object] = {
        "w": w,
        "throat": throat,
        "L_weld": L_weld,
        "A_we": A_we,
        "stress_demand_MPa": stress_demand,
        "Ru_equiv_N": Ru_equiv,
        "phi_w": phi_w,
        "F_EXX": float(F_EXX),
        "k_ds": k_ds,
        "n_f": int(n_f),
        "t": t,
        "Fy": Fy,
        "Fu": Fu,
        "A_BM": A_BM,
        "base_phiRn_yield_N": base_phiRn_yield,
        "base_phiRn_rupture_N": base_phiRn_rupture,
        "weld_capacity_N": weld_capacity,
        "base_capacity_N": base_capacity,
        "detailing_w_max": detailing_w_max,
    }

    detail = WeldCheckDetail(
        weld_type=params.type,
        leg=w,
        throat=throat,
        L_weld=L_weld,
        theta_deg=theta_used,
        k_ds=float(k_ds),
        F_EXX=float(F_EXX),
        stress_demand=stress_demand,
        Ru_equiv=Ru_equiv,
        weld_capacity=weld_capacity,
        base_capacity=base_capacity,
        detailing_w_max=detailing_w_max,
        weld_util=weld_util,
        base_util=base_util,
        detailing_max_util=detailing_max_util,
        governing_util=float(governing_util),
        governing_limit_state=governing_state,
        calc=calc,
    )

    meta: dict[str, object] = {
        "standard": "aisc",
        "phi_w": float(phi_w),
        "enforce_max_fillet_size": bool(enforce_max_fillet_size),
        "is_double_fillet": bool(connection.is_double_fillet),
        "is_rect_hss_end_connection": bool(connection.is_rect_hss_end_connection),
    }

    details = [detail]
    gov_state, gov_util = get_governing(details)
    return WeldCheckResult(
        method=str(result.method),
        details=details,
        governing_limit_state=gov_state,
        governing_utilization=float(gov_util),
        meta=meta,
    )


__all__ = ["check_aisc"]


