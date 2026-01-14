from dataclasses import dataclass
from .bolt import BoltConnection
from .load import Load
from typing import Literal, Any
import numpy as np
from .solvers.elastic import solve_bolt_elastic
from .solvers.icr import solve_bolt_icr
from .solvers.tension import solve_neutral_axis, cells_from_rectangle

@dataclass(slots=True)
class LoadedBoltConnection:
    bolt_connection: BoltConnection
    load: Load
    shear_method: Literal["elastic", "icr"] = "icr"
    icr_point: tuple[float, float] | None = None
    neutral_axis: tuple[float, float] | None = None
    plate_pressure: np.ndarray | None = None
    plate_pressure_extent: tuple[float, float, float, float] | None = None

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
        # Prepare inputs
        bolt_ks = np.array([bolt.k for bolt in self.bolt_connection.bolt_group.bolts], dtype=float)
        
        # Combine coordinates and stiffness: (x, y, k)
        bolts_data = np.column_stack([bolt_coords, bolt_ks])
        
        plate = self.bolt_connection.plate
        
        # Create compression cells for the plate contact
        # Using default grid resolution
        cells, A_cell = cells_from_rectangle(
            x_min=plate.x_min,
            x_max=plate.x_max,
            y_min=plate.y_min,
            y_max=plate.y_max,
            n_cells_x=50,
            n_cells_y=50,
            total_thickness=self.bolt_connection.total_thickness,
        )
        
        # Handle pure axial tension optimization (if desired for speed/stability)
        # If Fz > 0 and no moments, assume uniform lift-off if symmetric, 
        # or at least no compression zone (NA undefined or far away).
        if abs(self.load.Mx) < 1e-6 and abs(self.load.My) < 1e-6 and self.load.Fz > 0:
            # Pure tension: distribute by stiffness
            w = bolt_ks / np.sum(bolt_ks)
            fzs = np.maximum(0.0, self.load.Fz * w)
            self.neutral_axis = None
            self.plate_pressure = None
            self.plate_pressure_extent = None
        else:
            # General case: solve for NA
            theta, c, s, b_f1, c_f1 = solve_neutral_axis(
                bolts=bolts_data,
                cells=cells,
                Fz=self.load.Fz,
                Mx=self.load.Mx,
                My=self.load.My,
                theta_steps=720,
                c_steps=400,
            )
            self.neutral_axis = (theta, c)
            # Calculate final bolt forces (s * unit_forces)
            fzs = np.maximum(0.0, s * b_f1)
            
            # Calculate pressure (s * c_f1 / Area)
            # c_f1 is negative for compression, so we take abs/negative to get positive pressure magnitude
            # or keep negative to signify compression? Usually pressure is > 0.
            # Let's store positive pressure magnitude.
            pressures = np.abs(s * c_f1) / A_cell
            
            # Reshape (n_x, n_y) then transpose to (n_y, n_x) for plotting
            self.plate_pressure = pressures.reshape((50, 50)).T
            self.plate_pressure_extent = (plate.x_min, plate.x_max, plate.y_min, plate.y_max)

        # 3. Apply forces to bolts
        # Assuming list order is preserved (which it is for list implementations)
        for i, bolt in enumerate(self.bolt_connection.bolt_group.bolts):
            bolt.apply_force(fx=float(fxs[i]), fy=float(fys[i]), fz=float(fzs[i]))
    


    def check(self, standard: str, **kwargs) -> dict[str, Any]:
        if standard.lower() == "aisc":
            from .checks.aisc import check_aisc
            return check_aisc(self, **kwargs)
        raise ValueError(f"Unknown standard: {standard}")

    def plot_shear(self, **kwargs) -> Any:
        """Plot shear force distribution."""
        from .plotting import plot_shear_distribution
        return plot_shear_distribution(self, **kwargs)

    def plot_tension(self, **kwargs) -> Any:
        """Plot tension force distribution."""
        from .plotting import plot_tension_distribution
        return plot_tension_distribution(self, **kwargs)
