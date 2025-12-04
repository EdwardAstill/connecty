"""
Example 7: ICR method for an eccentrically loaded RHS.

Highlights how the ICR method locates the instantaneous center and
delivers additional strength when the load is offset from the weld
centroid in both shear directions.
"""
from pathlib import Path

from sectiony.library import rhs

from connecty import Force, Weld, WeldParameters

# Build section and weld
section = rhs(b=150, h=75, t=10, r=12)

params = WeldParameters(
    weld_type="fillet",
    leg=8.0,
    electrode="E70"
)

weld = Weld.from_section(section=section, parameters=params)

# Define an eccentrically applied shear that introduces torsion
force = Force(
    Fy=-140000,
    Fz=45000,
    location=(20, -55)
)

# Analyze with both methods to compare
elastic_result = weld.stress(force, method="elastic")
icr_result = weld.stress(force, method="icr")

print("=" * 60)
print("EXAMPLE 7: ICR METHOD WITHOUT-MOMENT SCREENING")
print("=" * 60)
print("Loading:")
print("  Vertical shear Fy = -140 kN | Horizontal shear Fz = 45 kN")
print("  Location offset: (20 mm up, 55 mm left)")
print()
print("ICR METHOD:")
print(f"  Max stress: {icr_result.max:.1f} MPa")
print(f"  Utilization: {icr_result.utilization():.1%}")
rotation_text = f"{icr_result.rotation:.1f} mm" if icr_result.rotation is not None else "n/a"
print(f"  Instantaneous center distance along shear perp: {rotation_text}")
if icr_result.icr_point is not None:
    print(f"  ICR location: ({icr_result.icr_point[0]:.1f}, {icr_result.icr_point[1]:.1f})")
print()
print("ELASTIC METHOD (for reference):")
print(f"  Max stress: {elastic_result.max:.1f} MPa")
print(f"  Utilization: {elastic_result.utilization():.1%}")
print(f"  Capacity gain from ICR: "
      f"{(1 - icr_result.utilization() / elastic_result.utilization()) * 100:.0f}%")

# Save visualization of the ICR result
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example7_icr_rhs_eccentric.svg"

icr_result.plot(
    section=True,
    force=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)

print(f"\nSaved: {save_path}")

