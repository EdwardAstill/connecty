from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Any, TYPE_CHECKING

import numpy as np

from .bolt import BoltConnection

if TYPE_CHECKING:
    from ..common.load import Load


@dataclass(frozen=True)
class BoltForceResult:
    """Force result for a single bolt."""

    Fx: float  # tension (out-of-plane)
    Fy: float  # shear in y
    Fz: float  # shear in z
    area: float
    n_shear_planes: int

    @property
    def shear(self) -> float:
        return float(np.sqrt(self.Fy**2 + self.Fz**2))

    @property
    def shear_stress(self) -> float:
        return self.shear / (self.area * self.n_shear_planes)

    @property
    def tension_stress(self) -> float:
        return self.Fx / self.area


def _solve_tension_conservative(
    bolt_coords: np.ndarray,
    bolt_ks: np.ndarray,
    Fx: float,
    My: float,
    Mz: float,
) -> np.ndarray:
    """Distribute tension with NA at bolt-group centroid.

    Linear elastic superposition; negative bolt forces zeroed.
    """
    n = len(bolt_ks)
    ys = bolt_coords[:, 0]
    zs = bolt_coords[:, 1]
    Cy = float(np.mean(ys))
    Cz = float(np.mean(zs))

    k_total = float(np.sum(bolt_ks))

    dy = ys - Cy
    dz = zs - Cz
    Iy = float(np.sum(bolt_ks * dz**2))  # for My (gradient in z)
    Iz = float(np.sum(bolt_ks * dy**2))  # for Mz (gradient in y)

    fx = Fx * bolt_ks / k_total  # direct tension

    if Iy > 1e-12:
        fx = fx + My * bolt_ks * dz / Iy
    if Iz > 1e-12:
        fx = fx + Mz * bolt_ks * dy / Iz

    return np.maximum(0.0, fx)


def _solve_tension_accurate(
    bolt_coords: np.ndarray,
    bolt_ks: np.ndarray,
    plate_y_min: float,
    plate_y_max: float,
    plate_z_min: float,
    plate_z_max: float,
    Fx: float,
    My: float,
    Mz: float,
) -> np.ndarray:
    """Distribute tension using the d/6 neutral-axis approximation.

    The NA is placed at plate_edge + depth/6 from the compression face,
    which accounts for the plate compression zone. Linear superposition
    of direct tension and moment contributions, with negative (compression)
    values zeroed.
    """
    n = len(bolt_ks)
    ys = bolt_coords[:, 0]
    zs = bolt_coords[:, 1]
    k_total = float(np.sum(bolt_ks))

    # Direct tension
    fx = Fx * bolt_ks / k_total

    # My contribution (gradient in z)
    if abs(My) > 1e-12:
        depth_z = plate_z_max - plate_z_min
        if My > 0:
            NA_z = plate_z_min + depth_z / 6.0
        else:
            NA_z = plate_z_max - depth_z / 6.0

        dz = zs - NA_z
        Iy = float(np.sum(bolt_ks * dz**2))
        if Iy > 1e-12:
            fx = fx + My * bolt_ks * dz / Iy

    # Mz contribution (gradient in y)
    if abs(Mz) > 1e-12:
        depth_y = plate_y_max - plate_y_min
        if Mz > 0:
            NA_y = plate_y_min + depth_y / 6.0
        else:
            NA_y = plate_y_max - depth_y / 6.0

        dy = ys - NA_y
        Iz = float(np.sum(bolt_ks * dy**2))
        if Iz > 1e-12:
            fx = fx + Mz * bolt_ks * dy / Iz

    return np.maximum(0.0, fx)


@dataclass(slots=True)
class LoadedBoltConnection:
    bolt_connection: BoltConnection
    load: "Load"
    shear_method: Literal["elastic", "icr"] = "elastic"
    tension_method: Literal["conservative", "accurate"] = "conservative"
    icr_point: tuple[float, float] | None = None
    neutral_axis: tuple[float, float] | None = None
    plate_pressure: np.ndarray | None = None
    plate_pressure_extent: tuple[float, float, float, float] | None = None
    _fxs: np.ndarray = field(init=False, repr=False)
    _fys: np.ndarray = field(init=False, repr=False)
    _fzs: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Calculate and distribute forces to all bolts in the connection."""
        bolt_coords = np.array(self.bolt_connection.bolt_group.points)  # (y, z)

        # --- Shear Distribution (in-plane: Fy, Fz) ---
        # Solvers use generic (coord1, coord2); we pass (y, z).
        if self.shear_method == "elastic":
            from .solvers.elastic import solve_bolt_elastic

            fys, fzs = solve_bolt_elastic(
                bolt_coords=bolt_coords,
                Fx=self.load.Fy,       # shear in y (solver's first coord)
                Fy=self.load.Fz,       # shear in z (solver's second coord)
                Mz=self.load.Mx,       # in-plane torsion about x (normal axis)
                x_loc=self.load.y_loc,
                y_loc=self.load.z_loc,
            )
        elif self.shear_method == "icr":
            from .solvers.icr import solve_bolt_icr

            fys, fzs, icr = solve_bolt_icr(
                bolt_coords=bolt_coords,
                Fx=self.load.Fy,
                Fy=self.load.Fz,
                Mz=self.load.Mx,
                x_loc=self.load.y_loc,
                y_loc=self.load.z_loc,
            )
            self.icr_point = (float(icr[0]), float(icr[1]))
        else:
            raise ValueError(f"Unknown shear method: {self.shear_method}")

        # --- Tension Distribution (out-of-plane: Fx) ---
        bolt_ks = np.array([b.k for b in self.bolt_connection.bolt_group.bolts], dtype=float)
        plate = self.bolt_connection.plate

        # Transfer moments to bolt group centroid to account for eccentric load
        bg = self.bolt_connection.bolt_group
        load_at_centroid = self.load.equivalent_at((0.0, bg.Cy, bg.Cz))

        if self.tension_method == "conservative":
            fxs = _solve_tension_conservative(
                bolt_coords=bolt_coords,
                bolt_ks=bolt_ks,
                Fx=load_at_centroid.Fx,
                My=load_at_centroid.My,
                Mz=load_at_centroid.Mz,
            )
        elif self.tension_method == "accurate":
            fxs = _solve_tension_accurate(
                bolt_coords=bolt_coords,
                bolt_ks=bolt_ks,
                plate_y_min=plate.y_min,
                plate_y_max=plate.y_max,
                plate_z_min=plate.z_min,
                plate_z_max=plate.z_max,
                Fx=load_at_centroid.Fx,
                My=load_at_centroid.My,
                Mz=load_at_centroid.Mz,
            )
        else:
            raise ValueError(f"Unknown tension method: {self.tension_method}")

        # Store forces locally (not on shared bolt objects)
        self._fxs = np.asarray(fxs, dtype=float)
        self._fys = np.asarray(fys, dtype=float)
        self._fzs = np.asarray(fzs, dtype=float)

    # --- Result accessors ---

    @property
    def bolt_forces(self) -> dict[str, list[float]]:
        """Bolt forces as a dict with keys 'Fx', 'Fy', 'Fz'."""
        return {
            "Fx": [float(v) for v in self._fxs],
            "Fy": [float(v) for v in self._fys],
            "Fz": [float(v) for v in self._fzs],
        }

    def to_bolt_forces(self) -> list[BoltForceResult]:
        """Per-bolt force results with derived quantities."""
        n_sp = self.bolt_connection.n_shear_planes
        bolts = self.bolt_connection.bolt_group.bolts
        return [
            BoltForceResult(
                Fx=float(self._fxs[i]),
                Fy=float(self._fys[i]),
                Fz=float(self._fzs[i]),
                area=bolts[i].params.area,
                n_shear_planes=n_sp,
            )
            for i in range(len(bolts))
        ]

    def check(self, standard: str, **kwargs: Any) -> dict[str, Any]:
        if standard.lower() == "aisc":
            from .checks.aisc import check_aisc
            return check_aisc(self, **kwargs)
        raise ValueError(f"Unknown standard: {standard}")

    def plot_shear(self, **kwargs: Any) -> Any:
        """Plot shear force distribution."""
        from .plotting import plot_shear_distribution
        return plot_shear_distribution(self, **kwargs)

    def plot_tension(self, **kwargs: Any) -> Any:
        """Plot tension force distribution."""
        from .plotting import plot_tension_distribution
        return plot_tension_distribution(self, **kwargs)
