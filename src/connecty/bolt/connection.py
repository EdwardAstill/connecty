"""Bolt connection analysis.

A BoltConnection combines a bolt group with a backing plate to define
the complete connection geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .bolt import BoltGroup
from .load import ConnectionLoad
from .plate import Plate

TensionMethod = Literal["conservative", "accurate"]
ShearMethod = Literal["elastic", "icr"]


@dataclass(frozen=True)
class BoltConnection:
    """Bolt group + plate definition for connection geometry.
    
    Attributes:
        bolt_group: BoltGroup defining bolt pattern
        plate: Plate defining backing plate geometry
        n_shear_planes: Number of shear planes (default 1)
    """

    bolt_group: BoltGroup
    plate: Plate
    n_shear_planes: int = 1

    def __post_init__(self) -> None:
        if self.n_shear_planes < 1:
            raise ValueError("n_shear_planes must be at least 1")
        
        # Check if any bolt is too close to plate boundary
        radius = self.bolt_group.diameter / 2
        for y, z in self.bolt_group.positions:
            # Distance from each plate boundary
            dist_to_y_min = y - self.plate.y_min
            dist_to_y_max = self.plate.y_max - y
            dist_to_z_min = z - self.plate.z_min
            dist_to_z_max = self.plate.z_max - z
            
            # Check if within radius of any boundary
            if (dist_to_y_min < radius or dist_to_y_max < radius or 
                dist_to_z_min < radius or dist_to_z_max < radius):
                raise ValueError(
                    f"Bolt at ({y}, {z}) is within diameter/2 ({radius}) of plate boundary"
                )

    def analyze(
        self,
        load,
        *,
        shear_method: ShearMethod = "elastic",
        tension_method: TensionMethod = "conservative",
    ):
        """Analyze this connection and return a ConnectionResult.

        This is the only supported public analysis entry point.

        Parameters
        ----------
        load:
            Either a bolt `ConnectionLoad` (preferred) or a common `Force`.
        shear_method:
            "elastic" or "icr" for in-plane shear distribution.
        tension_method:
            "conservative" or "accurate" for plate-based bolt tension distribution.
        """

        from ..common.force import Force
        from .bolt import ConnectionResult

        if isinstance(load, ConnectionLoad):
            conn_load = load
        elif isinstance(load, Force):
            conn_load = ConnectionLoad(
                Fx=float(load.Fx),
                Fy=float(load.Fy),
                Fz=float(load.Fz),
                Mx=float(load.Mx),
                My=float(load.My),
                Mz=float(load.Mz),
                location=tuple(load.location),
            )
        else:
            raise TypeError("load must be a ConnectionLoad or Force")

        return ConnectionResult(
            connection=self,
            load=conn_load,
            shear_method=shear_method,
            tension_method=tension_method,
        )
