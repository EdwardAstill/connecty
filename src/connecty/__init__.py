"""
Connecty - Weld and Bolt Connection Analysis Package

Calculate and visualize stress/force distribution along welded and bolted
connections per AISC 360 using Elastic and ICR methods.

Example usage (Welds):
    from sectiony.geometry import Geometry
    from connecty import Load, WeldBaseMetal, WeldConnection, WeldParams

    base_metal = WeldBaseMetal(t=10.0, fy=350.0, fu=450.0)
    params = WeldParams(type="fillet", leg=6.0)
    geometry = Geometry.from_dxf("weld_path.dxf")

    connection = WeldConnection.from_geometry(geometry=geometry, parameters=params, base_metal=base_metal)

    load = Load(Fy=-120_000.0, Fz=45_000.0, location=(0.0, 0.0, 0.0))
    result = connection.analyze(load, method="elastic")

    print(result.max_stress)
    result.plot(show=False, save_path="weld_stress.svg")
    check = result.check(standard="aisc")

Example usage (Bolts):
    from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate

    layout = BoltLayout.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, offset_y=10.0, offset_z=-5.0)
    bolt = BoltParams(diameter=20.0, grade="A325")
    plate = Plate.from_dimensions(width=200.0, height=300.0, center=(0.0, 0.0), thickness=12.0, fu=450.0, fy=350.0)

    connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
    load = Load(Fy=-100_000.0, location=(0.0, 0.0, 0.0))

    result = connection.analyze(load, shear_method="elastic", tension_method="conservative")
    print(result.max_shear_force)
    result.plot(show=False, save_path="bolt_forces.svg")
"""

from .common import Load
from .bolt import BoltConnection, BoltGroup, BoltParams, LoadedBoltConnection, Plate
# from .bolt.checks import BoltCheckDetail, BoltCheckResult
from .weld import WeldBaseMetal, WeldConnection, WeldParams, WeldResult
from .weld.checks import WeldCheckDetail, WeldCheckResult

__all__ = [
    "Load",
    # Bolts
    "BoltGroup",
    "BoltParams",
    "LoadedBoltConnection",
    "BoltConnection",
    "Plate",
    # "BoltCheckResult",
    # "BoltCheckDetail",
    # Welds
    "WeldParams",
    "WeldConnection",
    "WeldBaseMetal",
    "WeldResult",
    "WeldCheckResult",
    "WeldCheckDetail",
]

__version__ = "0.3.0"
