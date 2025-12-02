"""
Example 6: Circular hollow section

Demonstrates weld stress on a circular section with torsional loading.
"""
from sectiony.library import chs
from weldy import WeldedSection, WeldParameters, Force

# Create CHS: 200mm diameter, 10mm wall thickness
section = chs(d=200, t=10)

welded = WeldedSection(section=section)

weld_params = WeldParameters(
    weld_type="butt",
    throat_thickness=10.0,  # Full penetration butt weld
    strength=250.0
)

welded.weld_all_segments(weld_params)

# Primarily torsional loading
force = Force(
    Fy=-50000,   # 50kN vertical
    Mx=3e6,      # 3kNm torsion
    location=(0, 0)
)

result = welded.calculate_weld_stress(force)
print(f"Max stress: {result.max_stress:.2f} MPa")
if weld_params.strength:
    util = result.utilization(weld_params.strength)
    print(f"Utilization: {util*100:.1f}%")

from pathlib import Path

# ... (imports)

# ... (code)

gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example6_chs.svg"

welded.plot_weld_stress(
    force,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"Saved: {save_path}")

