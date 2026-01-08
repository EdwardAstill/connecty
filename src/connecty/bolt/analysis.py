from dataclasses import dataclass
from .bolt import BoltConnection
from ..common.load import Load
from typing import Literal, Any
import numpy as np
from .solvers.elastic import solve_elastic_shear
from .solvers.icr import solve_icr_shear
from .solvers.tension import solve_tension

@dataclass(slots=True)
class LoadedBoltConnection:
    bolt_connection: BoltConnection
    load: Load
    shear_method: Literal["elastic", "icr"]
    tension_method: Literal["conservative", "accurate"]

    def __post_init__(self) -> None:
        """Calculate and distribute forces to all bolts in the connection."""
        # Reset forces first
        for bolt in self.bolt_connection.bolt_group.bolts:
            bolt.forces.fill(0.0)

        diameter = self.bolt_connection.bolt_group.bolts[0].params.diameter

        # 1. Shear Distribution
        if self.shear_method == "elastic":
            fys, fzs = solve_elastic_shear(
                layout=self.bolt_connection.bolt_group,
                bolt_diameter=diameter,
                load=self.load
            )
        elif self.shear_method == "icr":
            fys, fzs, _ = solve_icr_shear(
                layout=self.bolt_connection.bolt_group,
                bolt_diameter=diameter,
                load=self.load
            )
        else:
            raise ValueError(f"Unknown shear method: {self.shear_method}")

        # 2. Tension Distribution
        fxs = solve_tension(
            layout=self.bolt_connection.bolt_group,
            plate=self.bolt_connection.plate,
            load=self.load,
            tension_method=self.tension_method
        )

        # 3. Apply forces to bolts
        # Assuming list order is preserved (which it is for list implementations)
        for i, bolt in enumerate(self.bolt_connection.bolt_group.bolts):
            bolt.apply_force(fx=float(fxs[i]), fy=float(fys[i]), fz=float(fzs[i]))

    def check(self, standard: str, **kwargs) -> dict[str, Any]:
        if standard.lower() == "aisc":
            from .checks.aisc import check_aisc
            return check_aisc(self, **kwargs)
        raise ValueError(f"Unknown standard: {standard}")
