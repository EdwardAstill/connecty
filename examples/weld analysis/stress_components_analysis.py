"""
Detailed stress component breakdown.
"""
from pathlib import Path
from sectiony.library import rhs
from connecty import Weld, WeldParams, Load, LoadedWeld


def run():
    section = rhs(b=100, h=150, t=8, r=10)
    params = WeldParams(type="fillet", leg=6.0)
    weld = Weld.from_section(section=section, parameters=params)

    load = Load(
        Fx=20000,
        Fy=-60000,
        Fz=30000,
        Mx=3e6,
        My=2e6,
        Mz=5e6,
        location=(0, 50, 25),
    )

    loaded = LoadedWeld(weld, load, method="elastic")

    print("STRESS COMPONENT BREAKDOWN")
    print("=" * 60)
    print(f"Max stress: {loaded.max:.1f} MPa | Min: {loaded.min:.1f} MPa | Range: {loaded.range:.1f} MPa")

    pt = loaded.max_point
    if pt:
        c = pt.components
        print(f"Max point at ({pt.y:.1f}, {pt.z:.1f})")
        print(f"  Shear resultant: {c.shear_resultant:.1f} MPa | Axial: {c.total_axial:.1f} MPa | Resultant: {c.resultant:.1f} MPa")

    F_EXX = 483.0
    phi = 0.75
    allowable = phi * 0.60 * F_EXX
    util = loaded.max / allowable
    print(f"Design check util (E70): {util:.1%}")

    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)
    save_path = gallery_dir / "stress_components_breakdown.svg"
    loaded.plot(section=True, force=True, cmap="coolwarm", weld_linewidth=5.0, show=False, save_path=str(save_path))
    print(f"Saved: {save_path}")


if __name__ == "__main__":
    run()
