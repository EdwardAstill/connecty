"""
ICR method for an eccentrically loaded RHS.

Highlights how the ICR method locates the instantaneous center and
delivers better stress distribution when the load is offset from the weld
centroid in both shear directions.
"""
from pathlib import Path

from sectiony.library import rhs

from connecty import Load, Weld, WeldParams, LoadedWeld

# Build section and weld
section = rhs(b=150, h=75, t=10, r=12)

Fy = -140000  # N
Fz = 45000    # N
location = (0, 20, -55)  # (x, y, z) mm

weld_leg = 8.0  # mm

params = WeldParams(
    type="fillet",
    leg=weld_leg
)
weld = Weld.from_section(section=section, parameters=params)

weld_throat = weld.parameters.throat

# Define an eccentrically applied shear that introduces torsion
load = Load(
    Fy=Fy,
    Fz=Fz,
    location=location
)

# Get the torsional moment about weld centroid
Mx, _, _ = load.get_moments_about(0, weld.Cy, weld.Cz)

print("=" * 60)
print("Eccentrically Loaded RHS Weld - ICR vs Elastic")
print("=" * 60)

print("\nWeld Properties:")
print(f"  Type: {weld.parameters.type.capitalize()}")
print(f"  Leg size: {weld.parameters.leg:.2f} mm")
print(f"  Effective Throat: {weld.parameters.throat:.2f} mm")
print(f"  Weld length: {weld.L:.1f} mm")
print(f"  Weld area: {weld.A:.1f} mm²")
print(f"  Centroid: ({weld.Cy:.1f}, {weld.Cz:.1f})")

print("\nApplied Load:")
print(f"  Vertical shear Fy = {Fy/1000:.0f} kN")
print(f"  Horizontal shear Fz = {Fz/1000:.0f} kN")
print(f"  Location: ({location[1]:.0f} mm y, {location[2]:.0f} mm z)")
print(f"  Eccentricity-induced moment Mx = {Mx/1e6:.1f} kN·m")

print("\n" + "=" * 60)

# Elastic Method
print("\nELASTIC METHOD:")
print("-" * 60)

loaded_elastic = LoadedWeld(weld, load, method="elastic")
print(f"  Max stress: {loaded_elastic.max:.1f} MPa")
print(f"  Min stress: {loaded_elastic.min:.1f} MPa")
print(f"  Mean stress: {loaded_elastic.mean:.1f} MPa")
print(f"  Stress range: {loaded_elastic.range:.1f} MPa")

# ICR Method
print("\nICR METHOD:")
print("-" * 60)

loaded_icr = LoadedWeld(weld, load, method="icr")
print(f"  Max stress: {loaded_icr.max:.1f} MPa")
print(f"  Min stress: {loaded_icr.min:.1f} MPa")
print(f"  Mean stress: {loaded_icr.mean:.1f} MPa")
print(f"  Stress range: {loaded_icr.range:.1f} MPa")

if loaded_icr.icr_point is not None:
    print(f"  Instantaneous center: ({loaded_icr.icr_point[0]:.1f}, {loaded_icr.icr_point[1]:.1f}) mm")
    print(f"  Rotation distance: {loaded_icr.rotation:.1f} mm")

# Comparison
print("\n" + "=" * 60)
print("COMPARISON:")
print("-" * 60)

stress_reduction = (1 - loaded_icr.max / loaded_elastic.max) * 100
print(f"  ICR reduces max stress by: {stress_reduction:.1f}%")

# Design check example
print("\n" + "=" * 60)
print("DESIGN CHECK EXAMPLE:")
print("-" * 60)

# AISC 360: φ(0.60 × F_EXX) for fillet welds
F_EXX = 483.0  # E70 electrode (MPa)
phi = 0.75
allowable_stress = phi * 0.60 * F_EXX

print(f"  Allowable stress (E70, φ=0.75): {allowable_stress:.1f} MPa")

# Check elastic
elastic_util = loaded_elastic.max / allowable_stress
print(f"\n  Elastic method:")
print(f"    Max stress / Allowable: {elastic_util:.1%}")
print(f"    Status: {'✓ PASS' if elastic_util <= 1.0 else '✗ FAIL'}")

# Check ICR
icr_util = loaded_icr.max / allowable_stress
print(f"\n  ICR method:")
print(f"    Max stress / Allowable: {icr_util:.1%}")
print(f"    Status: {'✓ PASS' if icr_util <= 1.0 else '✗ FAIL'}")

# Visualize
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)

save_path_icr = gallery_dir / "icr_rhs_eccentric_load.svg"
loaded_icr.plot(
    section=True,
    force=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    info=True,
    show=False,
    save_path=str(save_path_icr)
)

print(f"\nSaved: {save_path_icr}")
