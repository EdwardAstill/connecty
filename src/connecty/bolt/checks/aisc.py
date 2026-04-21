"""AISC 360-22 bolt group checks."""

from __future__ import annotations

import numpy as np
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..analysis import LoadedBoltConnection


AISC_HOLE_DIAMETERS: dict[int, dict[str, float]] = {
    12: {"standard": 14.0, "oversize": 16.0, "short_slotted": 14.0, "long_slotted": 14.0},
    16: {"standard": 18.0, "oversize": 20.0, "short_slotted": 18.0, "long_slotted": 18.0},
    20: {"standard": 22.0, "oversize": 24.0, "short_slotted": 22.0, "long_slotted": 22.0},
    22: {"standard": 24.0, "oversize": 28.0, "short_slotted": 24.0, "long_slotted": 24.0},
    24: {"standard": 27.0, "oversize": 30.0, "short_slotted": 27.0, "long_slotted": 27.0},
    27: {"standard": 30.0, "oversize": 35.0, "short_slotted": 30.0, "long_slotted": 30.0},
    30: {"standard": 33.0, "oversize": 38.0, "short_slotted": 33.0, "long_slotted": 33.0},
}

AISC_SLIP_COEFFICIENT: dict[str, float] = {"A": 0.30, "B": 0.50}


def check_aisc(
    connection: LoadedBoltConnection,
    *,
    connection_type: str,
    fillers: int = 0,  # for slip critical connection
) -> dict[str, Any]:

    n_s = connection.bolt_connection.n_shear_planes
    plate = connection.bolt_connection.plate
    bolts = connection.bolt_connection.bolt_group.bolts

    fxs = list(connection._fxs)
    fys = list(connection._fys)
    fzs = list(connection._fzs)

    results: dict[str, Any] = {}

    T_u = fxs  # tension is out-of-plane (x direction)
    V_u = [float(np.sqrt(y**2 + z**2)) for y, z in zip(fys, fzs)]
    V_u_total = float(np.sqrt(sum(fys) ** 2 + sum(fzs) ** 2))

    U_tension: list[float] = []
    U_shear: list[float] = []
    U_combined: list[float] = []
    U_bearing: list[float] = []
    U_tearout: list[float] = []
    f_rv: list[float] = []
    fp_nt: list[float] = []
    l_c: list[float] = []
    R_bear: list[float] = []
    R_tear: list[float] = []

    phi_tension = 0.75
    phi_shear = 0.75
    phi_bearing = 0.75
    strength = plate.fu  # AISC J3.10

    for i, bolt in enumerate(bolts):
        R_n_T = bolt.params.Fnt * bolt.params.area
        R_d_T = phi_tension * R_n_T
        U_tension.append(T_u[i] / R_d_T if R_d_T > 0 else 0.0)

        R_n_V = bolt.params.Fnv * bolt.params.area * n_s
        R_d_V = phi_shear * R_n_V
        U_shear.append(V_u[i] / R_d_V if R_d_V > 0 else 0.0)

        frv_i = V_u[i] / (bolt.params.area * n_s) if bolt.params.area > 0 else 0.0
        f_rv.append(frv_i)
        term = (bolt.params.Fnt / (phi_shear * bolt.params.Fnv)) * frv_i
        F_nt_prime = min(bolt.params.Fnt, max(0.0, 1.3 * bolt.params.Fnt - term))
        fp_nt.append(F_nt_prime)
        R_d_combined = phi_tension * F_nt_prime * bolt.params.area
        U_combined.append(T_u[i] / R_d_combined if R_d_combined > 0 else 0.0)

        R_n_bearing = 2.4 * bolt.params.diameter * plate.thickness * strength
        R_bear.append(R_n_bearing)
        U_bearing.append(V_u[i] / (phi_bearing * R_n_bearing) if R_n_bearing > 0 else 0.0)

        # clear distance from bolt shank edge to nearest plate edge
        lc = max(0.0, min(
            abs(bolt.position[0] - plate.y_min),
            abs(bolt.position[0] - plate.y_max),
            abs(bolt.position[1] - plate.z_min),
            abs(bolt.position[1] - plate.z_max),
        ) - bolt.params.diameter / 2)
        l_c.append(lc)
        R_n_tearout = 1.2 * lc * plate.thickness * strength
        R_tear.append(R_n_tearout)
        U_tearout.append(V_u[i] / (phi_bearing * R_n_tearout) if R_n_tearout > 0 else 0.0)

    results["tension"] = U_tension
    results["shear"] = U_shear
    results["combined"] = U_combined
    results["bearing"] = U_bearing
    results["tearout"] = U_tearout
    results["f_rv"] = f_rv
    results["fp_nt"] = fp_nt
    results["l_c"] = l_c
    results["R_bear"] = R_bear
    results["R_tear"] = R_tear

    U_slip: list[float] = []
    if connection_type == "slip_critical":
        slip_phi = 1.00  # LRFD standard holes
        D_u = 1.13
        h_f = 1.0 if fillers == 1 else 0.85
        mu = plate.slip_coefficient if plate.slip_coefficient is not None else 0.30

        R_n_slip_total = 0.0
        for i, bolt in enumerate(bolts):
            k_sc_i = max(0.0, 1.0 - T_u[i] / (D_u * bolt.params.T_b))
            R_n_slip_total += mu * D_u * h_f * bolt.params.T_b * n_s * k_sc_i

        R_d_slip = slip_phi * R_n_slip_total
        U_slip.append(V_u_total / R_d_slip if R_d_slip > 0 else 0.0)

    results["slip"] = U_slip

    u_slip_group = U_slip[0] if U_slip else 0.0
    if connection_type == "slip_critical":
        results["governing"] = [
            max(
                [("Tension", U_tension[i]), ("Shear", U_shear[i]), ("Combined", U_combined[i]),
                 ("Bearing", U_bearing[i]), ("Tearout", U_tearout[i]), ("Slip", u_slip_group)],
                key=lambda x: x[1],
            )[0]
            for i in range(len(bolts))
        ]
    else:
        results["governing"] = [
            max(
                [("Tension", U_tension[i]), ("Shear", U_shear[i]), ("Combined", U_combined[i]),
                 ("Bearing", U_bearing[i]), ("Tearout", U_tearout[i])],
                key=lambda x: x[1],
            )[0]
            for i in range(len(bolts))
        ]
    return results
