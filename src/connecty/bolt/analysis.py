from dataclasses import dataclass
from .bolt import BoltConnection
from .load import Load
from typing import Literal, Any
import numpy as np
from .solvers.elastic import solve_bolt_elastic
from .solvers.icr import solve_bolt_icr
from .solvers.tension import solve_bolt_tension

@dataclass(slots=True)
class LoadedBoltConnection:
    bolt_connection: BoltConnection
    load: Load
    shear_method: Literal["elastic", "icr"]
    tension_method: Literal["conservative", "accurate"]
    icr_point: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        """Calculate and distribute forces to all bolts in the connection."""
        # Reset forces first
        for bolt in self.bolt_connection.bolt_group.bolts:
            bolt.forces.fill(0.0)

        # Prepare data for solvers
        # Bolts are in x-y plane
        bolt_coords = np.array(self.bolt_connection.bolt_group.points)
        
        # 1. Shear Distribution (In-Plane: x, y)
        if self.shear_method == "elastic":
            fxs, fys = solve_bolt_elastic(
                bolt_coords=bolt_coords,
                Fx=self.load.Fx,
                Fy=self.load.Fy,
                Mz=self.load.Mz,
                x_loc=self.load.x_loc,
                y_loc=self.load.y_loc
            )
        elif self.shear_method == "icr":
            fxs, fys, icr = solve_bolt_icr(
                bolt_coords=bolt_coords,
                Fx=self.load.Fx,
                Fy=self.load.Fy,
                Mz=self.load.Mz,
                x_loc=self.load.x_loc,
                y_loc=self.load.y_loc
            )
            self.icr_point = (float(icr[0]), float(icr[1]))
        else:
            raise ValueError(f"Unknown shear method: {self.shear_method}")

        # 2. Tension Distribution (Out-of-Plane: z)
        fzs = solve_bolt_tension(
            bolt_coords=bolt_coords,
            plate=self.bolt_connection.plate,
            Fz=self.load.Fz,
            Mx=self.load.Mx,
            My=self.load.My,
            tension_method=self.tension_method
        )

        # 3. Apply forces to bolts
        # Assuming list order is preserved (which it is for list implementations)
        for i, bolt in enumerate(self.bolt_connection.bolt_group.bolts):
            bolt.apply_force(fx=float(fxs[i]), fy=float(fys[i]), fz=float(fzs[i]))
    
    def equivalent_load(self, position: tuple[float, float]) -> Load:
        """
        Calculate the equivalent load exerted BY the bolts at a given (x, y) position.
        This represents the total reaction force provided by the bolt group.
        
        Args:
            position: (x, y) coordinates of the point to calculate moments about.
            
        Returns:
            Load object containing total forces and moments.
        """
        px, py = position
        pz = 0.0 # Bolts are in z=0 plane
        
        Fx_tot = 0.0
        Fy_tot = 0.0
        Fz_tot = 0.0
        Mx_tot = 0.0
        My_tot = 0.0
        Mz_tot = 0.0
        
        for bolt in self.bolt_connection.bolt_group.bolts:
            fx, fy, fz = bolt.forces
            bx, by = bolt.position
            bz = 0.0
            
            dx = bx - px
            dy = by - py
            dz = bz - pz
            
            Fx_tot += fx
            Fy_tot += fy
            Fz_tot += fz
            
            # Moments (M = r x F)
            # Mx: dy*fz - dz*fy
            Mx_tot += dy * fz - dz * fy
            
            # My: dz*fx - dx*fz
            My_tot += dz * fx - dx * fz
            
            # Mz: dx*fy - dy*fx
            Mz_tot += dx * fy - dy * fx
            
        return Load(
            Fx=Fx_tot,
            Fy=Fy_tot,
            Fz=Fz_tot,
            Mx=Mx_tot,
            My=My_tot,
            Mz=Mz_tot,
            location=(px, py, 0.0)
        )

    def check(self, standard: str, **kwargs) -> dict[str, Any]:
        if standard.lower() == "aisc":
            from .checks.aisc import check_aisc
            return check_aisc(self, **kwargs)
        raise ValueError(f"Unknown standard: {standard}")
