"""
Example 4: U-Channel with torsional loading

Demonstrates weld stress analysis on a U-channel section
with torsional moment (Mx).
"""
from sectiony.library import u
from connecty import Weld, WeldParameters, Force
from pathlib import Path

# Create U-channel: 150mm high, 75mm wide, 8mm thickness
section = u(b=75, h=150, t=8, r=8)

# 5mm fillet weld
params = WeldParameters(
    weld_type="fillet",
    leg=5.0,
    electrode="E70"
)

weld = Weld.from_section(section=section, parameters=params)

# Torsional loading
force = Force(
    Fy=-30000,    # 30kN shear
    Mx=5e6,       # 5kNm torsion
    location=(0, 0)
)

# Calculate stress
result = weld.stress(force, method="elastic")

# Print results
print("U-CHANNEL WELD ANALYSIS (TORSION)")
print("=" * 50)
print(f"\nSection: U 150×75×8")
print(f"Weld: 5mm fillet")
print(f"\nLoading:")
print(f"  Fy = -30 kN (shear)")
print(f"  Mx = 5 kNm (torsion)")
print()

print(f"Weld Properties:")
print(f"  Length: {weld.L:.1f} mm")
print(f"  Centroid: ({weld.Cy:.1f}, {weld.Cz:.1f})")
print(f"  Ip: {weld.Ip:.0f} mm⁴")
print()

print(f"Results:")
print(f"  Max stress: {result.max:.1f} MPa")
print(f"  Capacity: {result.capacity:.1f} MPa")
print(f"  Utilization: {result.utilization():.1%}")
print(f"  Adequate: {'✓' if result.is_adequate() else '✗'}")

# Plot
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example4_u_channel.svg"

result.plot(
    section=True,
    force=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"\nSaved: {save_path}")
