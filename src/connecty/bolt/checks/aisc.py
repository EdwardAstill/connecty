"""AISC 360-22 bolt group checks."""

from __future__ import annotations

import numpy as np
from typing import Any

from ..analysis import BoltResult as _BoltResult
from ..geometry import Plate


AISC_GRADE_STRESS: dict[str, dict[str, float]] = {
    "A325": {"Fnt": 620.0, "Fnv_N": 370.0, "Fnv_X": 470.0},
    "A490": {"Fnt": 780.0, "Fnv_N": 470.0, "Fnv_X": 580.0},
}

AISC_PRETENSION_KN: dict[int, dict[str, float]] = {
    12: {"A325": 49.0, "A490": 72.0},
    16: {"A325": 91.0, "A490": 114.0},
    20: {"A325": 142.0, "A490": 179.0},
    22: {"A325": 176.0, "A490": 221.0},
    24: {"A325": 205.0, "A490": 257.0},
    27: {"A325": 267.0, "A490": 334.0},
    30: {"A325": 326.0, "A490": 408.0},
    36: {"A325": 475.0, "A490": 595.0},
}

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

class BoltResult(_BoltResult):
    def check_aisc(
    self, *,
    n_s: int,
    threads_in_shear_plane: bool,
    bolt_diameter: float,
    connection_type: str,
    fillers: int, #for slip critical connection
    apply_prying_factor: bool,
    prying_factor: float,
    ) -> dict[str, Any]:

        # Raise errors for invalid inputs
        if connection_type not in ("bearing", "slip-critical"):
            raise ValueError("AISC connection_type must be 'bearing' or 'slip-critical'")
        if n_s < 1:
            raise ValueError("AISC n_s (number of shear/slip planes) must be at least 1")
        if self.connection.plate.hole_type != "standard":
            raise ValueError("AISC hole type must be 'standard' for now")

        # gather useful inputs
        # bolt properties from grade table
        stresses = AISC_GRADE_STRESS[grade]
        Fnv = stresses["Fnv_N" if threads_in_shear_plane else "Fnv_X"]
        Fnt = stresses["Fnt"]

        # plate object
        plate = self.connection.plate

        grade = self.connection.bolt.grade
        if grade is None:
            raise ValueError("BoltParams.grade is required for bolt code checks.")

        A_b = np.pi * (bolt_diameter**2) / 4.0
        # initialise results
        results = {}

        # apply prying factor if applicable to get tension force
        prying_factor = prying_factor if apply_prying_factor else 0.0
        T_u = [prying_factor * x for x in self.bolt_forces["Fx"]]

        # calculate shear force
        V_u = [np.sqrt(x**2 + y**2) for x, y in zip(self.bolt_forces["Fy"], self.bolt_forces["Fz"])]

        # Applied forces
        V_u_total = np.sqrt((sum(self.bolt_forces["Fy"]))**2 + (sum(self.bolt_forces["Fz"]))**2)

        # perform checks

        # tension check
        results["tension"] = check_tension(Fnt, A_b, T_u)

        # shear check
        results["shear"] = check_shear(Fnv, A_b, V_u, n_s)
        
        # shear + tension interaction check
        results["combined"] = check_combined(Fnt, Fnv, A_b, T_u, V_u, n_s)

        if connection_type == "slip-critical":
        # slip critical connection check
            T_b = AISC_PRETENSION_KN[int((bolt_diameter))][grade]
            results["slip"] = check_slip(fillers,T_b,plate,V_u_total, n_s, T_u)
        
        # bearing check
        results["bearing"] = check_bearing(plate,V_u_total, bolt_diameter, )

        # tearout check
        results["tearout"] = check_tearout(plate,V_u_total, bolt_diameter, self.connection.layout.points)

        return results


def check_tension(Fnt, A_b, T_u):
    phi = 0.75
    R_n_T = Fnt * A_b
    R_d_T = phi * R_n_T
    U_tension = [x / R_d_T for x in T_u]
    return U_tension


def check_shear(Fnv, A_b, V_u, n_s):
    phi = 0.75
    R_n_V = Fnv * A_b * n_s
    R_d_V = phi * R_n_V
    U_shear = [x / R_d_V for x in V_u]
    return U_shear

def check_combined(Fnt, Fnv, A_b, T_u, V_u, n_s):
    phi = 0.75
    F_nt_prime = min(Fnt, Fnt * (1.3 - Fnt / phi / Fnv * f_rv))
    R_n_T = F_nt_prime * A_b
    f_rv = [x / (A_b * n_s) for x in V_u]
    U_combined = [x / (phi * R_n_T) for x in T_u]
    return U_combined

def check_slip(fillers,T_b,plate:Plate,V_u_total, n_s, T_u):
    phi = 1.00# when other holes are supported conditions should be used to find phi
    D_u = 1.13
    h_f = 1.0 if fillers == 1 else 0.85
    mu = plate.slip_coefficient
    k_sc = R_n_slip_i = [0] * len(T_u)
    for i in range(len(T_u)):
        k_sc[i] = max(0, 1 - T_u[i] / (D_u * T_b))
        R_n_slip_i[i] = mu * D_u * h_f * T_b * n_s * k_sc[i]
    R_n_slip = sum(R_n_slip_i)
    R_d_slip = phi * R_n_slip
    U_slip = [x / R_d_slip for x in V_u_total]
    return U_slip
    

def check_bearing(plate:Plate,V_u_total, bolt_diameter, points):
    phi = 0.75
    R_n_bearing = 2.4 * bolt_diameter * plate.thickness * plate.material.yield_strength
    R_d_bearing = phi * R_n_bearing
    U_bearing = [x / R_d_bearing for x in V_u_total]
    return U_bearing

def check_tearout(plate:Plate,V_u_total, bolt_diameter, points):
    phi = 0.75
    R_n_tearout = 1.2 * bolt_diameter * plate.thickness * plate.material.yield_strength
    R_d_tearout = phi * R_n_tearout
    U_tearout = [x / R_d_tearout for x in V_u_total]
    return U_tearout
    pass
