"""
Example 4: U-channel with combined loading

Shows stress distribution on a U-channel section with multiple load components.
"""
from sectiony.library import u
from weldy import WeldedSection, WeldParameters, Force

# Create U-channel: 200mm deep (height), 100mm wide, 10mm thick, 10mm root radius
section = u(h=200, b=100, t=10, r=10)

welded = WeldedSection(section=section)

weld_params = WeldParameters(
    weld_type="fillet",
    throat_thickness=4.2,
    leg_size=6.0,
    strength=220.0  # Allowable stress
)

welded.weld_all_segments(weld_params)

# Combined loading: shear + bending + torsion
force = Force(
    Fy=-60000,   # 60kN vertical shear
    Fz=-15000,   # 15kN horizontal shear
    Mx=1.5e6,    # 1.5kNm torsion
    My=3e6,      # 3kNm bending
    location=(80, 20)
)

result = welded.calculate_weld_stress(force)
print(f"Max stress: {result.max_stress:.2f} MPa")
print(f"Min stress: {result.min_stress:.2f} MPa")
if weld_params.strength:
    util = result.utilization(weld_params.strength)
    print(f"Utilization: {util*100:.1f}%")

from pathlib import Path

# ... (imports)

# ... (code)

gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example4_u_channel.svg"

welded.plot_weld_stress(
    force,
    cmap="viridis",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"Saved: {save_path}")

