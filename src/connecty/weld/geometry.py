"""
Bolt-like weld connection geometry + required design inputs.

This module introduces `WeldConnection`, analogous to `connecty.bolt.geometry.BoltConnection`,
so weld workflows can follow:

    connection -> analyze(load) -> result -> check() / plot()
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sectiony.geometry import Geometry

from ..common.load import Load
from .weld import Weld, WeldParams

WeldMethod = Literal["elastic", "icr", "both"]


@dataclass(frozen=True)
class WeldBaseMetal:
    """Conservative base metal properties for a weld group."""

    t: float
    fy: float
    fu: float

    def __post_init__(self) -> None:
        if self.t <= 0.0:
            raise ValueError("Base metal thickness t must be > 0")
        if self.fy <= 0.0:
            raise ValueError("Base metal yield strength fy must be > 0")
        if self.fu <= 0.0:
            raise ValueError("Base metal tensile strength fu must be > 0")


@dataclass(frozen=True)
class WeldConnection:
    """
    Weld group + base metal properties for design checking.

    Notes:
    - Geometry lives in the y-z plane (same convention as bolts).
    - The weld group is represented by a `Weld` (geometry + weld parameters).
    """

    weld: Weld
    base_metal: WeldBaseMetal
    is_double_fillet: bool = False
    is_rect_hss_end_connection: bool = False

    @classmethod
    def from_geometry(
        cls,
        *,
        geometry: Geometry,
        parameters: WeldParams,
        base_metal: WeldBaseMetal,
        is_double_fillet: bool = False,
        is_rect_hss_end_connection: bool = False,
    ) -> "WeldConnection":
        weld = Weld(geometry=geometry, parameters=parameters, section=None)
        return cls(
            weld=weld,
            base_metal=base_metal,
            is_double_fillet=bool(is_double_fillet),
            is_rect_hss_end_connection=bool(is_rect_hss_end_connection),
        )

    @classmethod
    def from_dxf(
        cls,
        dxf_path: str | Path,
        *,
        parameters: WeldParams,
        base_metal: WeldBaseMetal,
        is_double_fillet: bool = False,
        is_rect_hss_end_connection: bool = False,
    ) -> "WeldConnection":
        """
        Create a `WeldConnection` from a DXF file.

        Uses `sectiony.geometry.Geometry.from_dxf(...)` to produce the weld path geometry.
        """
        geometry = Geometry.from_dxf(str(dxf_path))
        return cls.from_geometry(
            geometry=geometry,
            parameters=parameters,
            base_metal=base_metal,
            is_double_fillet=is_double_fillet,
            is_rect_hss_end_connection=is_rect_hss_end_connection,
        )

    def analyze(
        self,
        load: Load,
        *,
        method: WeldMethod = "elastic",
        discretization: int = 200,
    ) -> "LoadedWeldConnection":
        """Analyze this weld connection and return a `LoadedWeldConnection`."""
        from .analysis import LoadedWeldConnection

        return LoadedWeldConnection(
            connection=self,
            load=load,
            method=method,
            discretization=discretization,
        )


