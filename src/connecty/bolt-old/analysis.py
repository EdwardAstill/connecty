"""BoltResult: a BoltConnection subjected to a Load, with calculated bolt forces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..common.load import Load
from .group import BoltConnection, BoltLayout
from .types import Point2D, ShearMethod, TensionMethod


@dataclass
class BoltForce:
    """Forces on a single bolt."""
    y: float
    z: float
    shear: float
    axial: float
    Fy: float
    Fz: float
    Fx: float

    @property
    def point(self) -> Point2D:
        return (self.y, self.z)


class BoltResult:
    """A `BoltConnection` subjected to a `Load`, with calculated per-bolt forces."""

    connection: BoltConnection
    load: Load
    shear_method: ShearMethod
    tension_method: TensionMethod
    layout: BoltLayout
    method: str
    icr_point: Point2D | None
    bolt_forces: dict[str, list[float]]

    def __init__(
        self,
        connection: BoltConnection,
        load: Load,
        shear_method: ShearMethod = "elastic",
        tension_method: TensionMethod = "conservative",
    ) -> None:
        self.connection = connection
        self.load = load
        self.shear_method = shear_method
        self.tension_method = tension_method
        self.layout = self.connection.layout
        self.method = str(self.shear_method)
        self.bolt_forces = {"Fx": [], "Fy": [], "Fz": []}
        self.icr_point = None

        self._solve()

    def _solve(self) -> None:
        from .solvers.elastic import solve_elastic_shear
        from .solvers.icr import solve_icr_shear
        from .solvers.tension import calculate_plate_bolt_tensions

        # solve for shear forces
        if self.shear_method == "elastic":
            Fys, Fzs = solve_elastic_shear(
                layout=self.connection.layout,
                bolt_diameter=float(self.connection.bolt.diameter),
                load=self.load,
            )
            self.bolt_forces["Fy"] = Fys
            self.bolt_forces["Fz"] = Fzs
            self.icr_point = None
        elif self.shear_method == "icr":
            Fys, Fzs, icr_point = solve_icr_shear(
                layout=self.connection.layout,
                load=self.load,
            )
            self.bolt_forces["Fy"] = Fys
            self.bolt_forces["Fz"] = Fzs
            self.icr_point = icr_point
        else:
            raise ValueError("shear_method must be 'elastic' or 'icr'")

        # solve for tension forces
        if self.connection.plate is None:
            if abs(self.load.Fx) > 1e-12 or abs(self.load.My) > 1e-12 or abs(self.load.Mz) > 1e-12:
                raise ValueError("Plate is required for out-of-plane bolt effects (Fx/My/Mz).")
            self.bolt_forces["Fx"] = [0.0] * self.connection.layout.n
        else:
            Fxs = calculate_plate_bolt_tensions(
                layout=self.connection.layout,
                plate=self.connection.plate,
                load=self.load,
                tension_method=self.tension_method,
            )
        
        #add results to bolt_forces dict
        self.bolt_forces["Fx"] = Fxs
        # Fy and Fz are already set above

    def to_bolt_forces(self) -> list[BoltForce]:
        """Convert struct-of-arrays results to list of BoltForce objects."""
        results = []
        import numpy as np
        
        for i, (y, z) in enumerate(self.layout.points):
            fx = self.bolt_forces["Fx"][i]
            fy = self.bolt_forces["Fy"][i]
            fz = self.bolt_forces["Fz"][i]
            shear = float(np.sqrt(fy**2 + fz**2))
            
            results.append(BoltForce(
                y=y,
                z=z,
                shear=shear,
                axial=fx,
                Fy=fy,
                Fz=fz,
                Fx=fx
            ))
        return results

    def plot(
        self,
        *,
        force: bool = True,
        bolt_forces: bool = True,
        colorbar: bool = True,
        cmap: str = "coolwarm",
        ax: Any | None = None,
        show: bool = True,
        save_path: str | None = None,
        mode: str = "shear",
        force_unit: str = "N",
        length_unit: str = "mm",
    ) -> Any:
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
