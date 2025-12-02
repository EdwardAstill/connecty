"""
Example 5: Stress component breakdown

Shows different stress components (resultant, shear, axial, torsion)
in a 2x2 grid plot.
"""
from sectiony.library import rhs
from weldy import WeldedSection, WeldParameters, Force
from weldy.plotter import plot_weld_stress_components

section = rhs(b=120, h=250, t=8, r=12)
welded = WeldedSection(section=section)

weld_params = WeldParameters(
    weld_type="fillet",
    throat_thickness=5.0,
    leg_size=7.0
)

welded.weld_all_segments(weld_params)

# Complex loading
force = Force(
    Fx=30000,    # 30kN axial
    Fy=-70000,   # 70kN vertical
    Fz=25000,    # 25kN horizontal
    Mx=2.5e6,    # 2.5kNm torsion
    My=4e6,      # 4kNm bending
    Mz=1.5e6,    # 1.5kNm bending
    location=(100, 40)
)

result = welded.calculate_weld_stress(force)

from pathlib import Path

# ... (imports)

# ... (code)

gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example5_stress_components.svg"

# Plot component breakdown
plot_weld_stress_components(
    welded,
    result,
    force,
    show=False,
    save_path=str(save_path)
)
print(f"Saved: {save_path}")

