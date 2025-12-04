"""
Example 2: RHS with eccentric load (Elastic vs ICR)

Demonstrates comparison between Elastic and ICR methods for an
eccentrically loaded weld group on an RHS section.
"""
from sectiony.library import rhs
from connecty import Weld, WeldParameters, Force
from pathlib import Path

# Create RHS section
section = rhs(b=100, h=200, t=10, r=15)

# Create weld with 6mm fillet
params = WeldParameters(
    weld_type="fillet",
    leg=6.0,
    electrode="E70"
)

weld = Weld.from_section(section=section, parameters=params)

# Eccentric load - applied 50mm to the right of centroid
# This creates torsion in addition to direct shear
force = Force(
    Fy=-100000,        # 100kN downward
    location=(0, 50)   # 50mm right of centroid (z-direction) → creates Mx
)

# Calculate stress - Elastic method
result_elastic = weld.stress(force, method="elastic")

# Calculate stress - ICR method
result_icr = weld.stress(force, method="icr")

# Print comparison
print("=" * 60)
print("ELASTIC VS ICR METHOD COMPARISON")
print("=" * 60)
print(f"\nLoad: 100 kN vertical, 50mm horizontal eccentricity")
print(f"Weld: 6mm fillet around RHS 100×200×10")
print()

print("ELASTIC METHOD:")
print(f"  Max stress: {result_elastic.max:.1f} MPa")
print(f"  Utilization: {result_elastic.utilization():.1%}")
print(f"  Adequate: {'✓' if result_elastic.is_adequate() else '✗'}")

pt = result_elastic.max_point
if pt:
    print(f"  Max location: ({pt.y:.1f}, {pt.z:.1f})")

print()
print("ICR METHOD:")
print(f"  Max stress: {result_icr.max:.1f} MPa")
print(f"  Utilization: {result_icr.utilization():.1%}")
print(f"  Adequate: {'✓' if result_icr.is_adequate() else '✗'}")

if result_icr.icr_point:
    print(f"  ICR location: ({result_icr.icr_point[0]:.1f}, {result_icr.icr_point[1]:.1f})")

print()
print(f"ICR gives {(1 - result_icr.utilization()/result_elastic.utilization())*100:.0f}% "
      f"more capacity than Elastic method")

# Plot elastic result
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example2_rhs_eccentric.svg"

weld.plot(
    stress=result_elastic,
    info=True,
    cmap="coolwarm",
    section=True,
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"\nSaved: {save_path}")
