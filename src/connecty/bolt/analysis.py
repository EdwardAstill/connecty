"""User-facing bolt analysis object (result + convenience methods)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..common.load import Load
from .geometry import BoltConnection, BoltGroup, Point2D, ShearMethod, TensionMethod
from .results import BoltResult


@dataclass
class LoadedBoltConnection:
    """A `BoltConnection` subjected to a `Load`, with calculated bolt forces/stresses."""

    connection: BoltConnection
    load: Load
    shear_method: ShearMethod = "elastic"
    tension_method: TensionMethod = "conservative"

    bolt_results: list[BoltResult] = field(default_factory=list, init=False, repr=False)
    icr_point: Point2D | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        from .solvers.elastic import solve_elastic_shear
        from .solvers.icr import solve_icr_shear
        from .solvers.tension import calculate_plate_bolt_tensions

        if self.shear_method == "elastic":
            self.bolt_results = solve_elastic_shear(bolt_group=self.connection.bolt_group, load=self.load)
            self.icr_point = None
        elif self.shear_method == "icr":
            results, icr_point = solve_icr_shear(bolt_group=self.connection.bolt_group, load=self.load)
            self.bolt_results = results
            self.icr_point = icr_point
        else:
            raise ValueError("shear_method must be 'elastic' or 'icr'")

        tensions = calculate_plate_bolt_tensions(
            bolt_group=self.connection.bolt_group,
            plate=self.connection.plate,
            load=self.load,
            tension_method=self.tension_method,
        )

        for idx, br in enumerate(self.bolt_results):
            br.Fx = float(tensions[idx])
            br.n_shear_planes = int(self.connection.n_shear_planes)

    @property
    def bolt_group(self) -> BoltGroup:
        return self.connection.bolt_group

    @property
    def method(self) -> str:
        """Alias used by checks/legacy code paths."""
        return self.shear_method

    def to_bolt_results(self) -> list[BoltResult]:
        return list(self.bolt_results)

    @property
    def max_shear_force(self) -> float:
        if not self.bolt_results:
            return 0.0
        return float(np.max([br.shear for br in self.bolt_results]))

    @property
    def max_axial_force(self) -> float:
        if not self.bolt_results:
            return 0.0
        return float(np.max([br.axial for br in self.bolt_results]))

    @property
    def max_resultant_force(self) -> float:
        if not self.bolt_results:
            return 0.0
        return float(np.max([br.resultant for br in self.bolt_results]))

    @property
    def max_shear_stress(self) -> float:
        if not self.bolt_results:
            return 0.0
        return float(np.max([br.shear_stress for br in self.bolt_results]))

    @property
    def max_axial_stress(self) -> float:
        if not self.bolt_results:
            return 0.0
        return float(np.max([br.axial_stress for br in self.bolt_results]))

    @property
    def max_combined_stress(self) -> float:
        if not self.bolt_results:
            return 0.0
        return float(np.max([br.combined_stress for br in self.bolt_results]))

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


