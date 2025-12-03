"""
Example 6: Circular Hollow Section (CHS)

Demonstrates weld stress analysis on a circular hollow section.
"""
from sectiony.library import chs
from connecty import Weld, WeldParameters, Force
from pathlib import Path

# Create CHS: 150mm diameter, 6mm wall
section = chs(d=150, t=6)

# 5mm fillet weld
params = WeldParameters(
    weld_type="fillet",
    leg=5.0,
    electrode="E70"
)

weld = Weld.from_section(section=section, parameters=params)

# Combined loading
force = Force(
    Fy=-50000,    # 50kN shear
    Mx=2e6,       # 2kNm torsion
    location=(0, 0)
)

# Calculate stress
result = weld.stress(force, method="elastic")

# Print results
print("CHS WELD ANALYSIS")
print("=" * 50)
print(f"\nSection: CHS 150×6")
print(f"Weld: 5mm fillet")
print(f"\nLoading:")
print(f"  Fy = -50 kN (shear)")
print(f"  Mx = 2 kNm (torsion)")
print()

print(f"Weld Properties:")
print(f"  Length: {weld.L:.1f} mm")
print(f"  Area: {weld.A:.1f} mm²")
print(f"  Centroid: ({weld.Cy:.1f}, {weld.Cz:.1f})")
print(f"  Ip: {weld.Ip:.0f} mm⁴")
print()

print(f"Results:")
print(f"  Max stress: {result.max:.1f} MPa")
print(f"  Min stress: {result.min:.1f} MPa")
print(f"  Capacity: {result.capacity:.1f} MPa")
print(f"  Utilization: {result.utilization():.1%}")
print(f"  Adequate: {'✓' if result.is_adequate() else '✗'}")

# Plot
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example6_chs.svg"

result.plot(
    section=True,
    force=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"\nSaved: {save_path}")
