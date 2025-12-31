"""BoltResult: a BoltConnection subjected to a Load, with calculated bolt forces."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..common.load import Load
from .geometry import BoltConnection, BoltLayout, Point2D, ShearMethod, TensionMethod
from .results import BoltForce


@dataclass
class BoltResult:
    """A `BoltConnection` subjected to a `Load`, with calculated per-bolt forces."""

    connection: BoltConnection
    load: Load
    shear_method: ShearMethod = "elastic"
    tension_method: TensionMethod = "conservative"

    bolt_forces: list[BoltForce] = field(default_factory=list, init=False, repr=False)
    icr_point: Point2D | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        from .solvers.elastic import solve_elastic_shear
        from .solvers.icr import solve_icr_shear
        from .solvers.tension import calculate_plate_bolt_tensions

        if self.shear_method == "elastic":
            self.bolt_forces = solve_elastic_shear(
                layout=self.connection.layout,
                bolt_diameter=float(self.connection.bolt.diameter),
                load=self.load,
            )
            self.icr_point = None
        elif self.shear_method == "icr":
            results, icr_point = solve_icr_shear(
                layout=self.connection.layout,
                bolt_diameter=float(self.connection.bolt.diameter),
                load=self.load,
            )
            self.bolt_forces = results
            self.icr_point = icr_point
        else:
            raise ValueError("shear_method must be 'elastic' or 'icr'")

        if self.connection.plate is None:
            if abs(self.load.Fx) > 1e-12 or abs(self.load.My) > 1e-12 or abs(self.load.Mz) > 1e-12:
                raise ValueError("Plate is required for out-of-plane bolt effects (Fx/My/Mz).")
            tensions = [0.0 for _ in range(self.connection.layout.n)]
        else:
            tensions = calculate_plate_bolt_tensions(
                layout=self.connection.layout,
                plate=self.connection.plate,
                load=self.load,
                tension_method=self.tension_method,
            )

        for idx, bf in enumerate(self.bolt_forces):
            bf.Fx = float(tensions[idx])
            bf.n_shear_planes = int(self.connection.n_shear_planes)

    @property
    def layout(self) -> BoltLayout:
        return self.connection.layout

    @property
    def method(self) -> str:
        """Convenience alias used by checks."""
        return self.shear_method

    def to_bolt_forces(self) -> list[BoltForce]:
        return list(self.bolt_forces)

    @property
    def max_shear_force(self) -> float:
        if not self.bolt_forces:
            return 0.0
        return float(np.max([bf.shear for bf in self.bolt_forces]))

    @property
    def max_axial_force(self) -> float:
        if not self.bolt_forces:
            return 0.0
        return float(np.max([bf.axial for bf in self.bolt_forces]))

    @property
    def max_resultant_force(self) -> float:
        if not self.bolt_forces:
            return 0.0
        return float(np.max([bf.resultant for bf in self.bolt_forces]))

    @property
    def max_shear_stress(self) -> float:
        if not self.bolt_forces:
            return 0.0
        return float(np.max([bf.shear_stress for bf in self.bolt_forces]))

    @property
    def max_axial_stress(self) -> float:
        if not self.bolt_forces:
            return 0.0
        return float(np.max([bf.axial_stress for bf in self.bolt_forces]))

    @property
    def max_combined_stress(self) -> float:
        if not self.bolt_forces:
            return 0.0
        return float(np.max([bf.combined_stress for bf in self.bolt_forces]))

    def plot(
        self,
        *,
        force: bool = True,
        bolt_forces: bool = True,
        colorbar: bool = True,
        cmap: str = "coolwarm",
        ax=None,
        show: bool = True,
        save_path: str | None = None,
        mode: str = "shear",
        force_unit: str = "N",
        length_unit: str = "mm",
    ):
        from .plotting import plot_bolt_result

        return plot_bolt_result(
            self,
            force=force,
            bolt_forces=bolt_forces,
            colorbar=colorbar,
            cmap=cmap,
            ax=ax,
            show=show,
            save_path=save_path,
            mode=mode,
            force_unit=force_unit,
            length_unit=length_unit,
        )

    def check(self, **kwargs):
        from .checks import check_bolt_group

        return check_bolt_group(self, **kwargs)


