"""
PJP Weld Analysis

Demonstrates analysis of a Partial Joint Penetration (PJP) weld.
PJP welds use the effective throat thickness (E) for calculation.
"""
from pathlib import Path
from sectiony.library import i
from connecty import Weld, WeldParams, Load, LoadedWeld


def run():
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)

    section = i(d=300, b=150, tf=12, tw=8, r=12)
    params = WeldParams(type="pjp", throat=8.0)
    weld = Weld.from_section(section=section, parameters=params)

    load = Load(Fy=-80000, Mx=2e6, Mz=15e6, location=(0, 0, 0))
    loaded = LoadedWeld(weld, load, method="elastic")

    print("=" * 60)
    print("PJP WELD ANALYSIS")
    print("=" * 60)
    print(f"Max Stress: {loaded.max:.1f} MPa")
    print(f"Min Stress: {loaded.min:.1f} MPa")

    F_EXX = 483.0
    phi = 0.75
    allowable = phi * 0.60 * F_EXX
    util = loaded.max / allowable
    print(f"Allowable stress: {allowable:.1f} MPa")
    print(f"Utilization: {util:.1%}")

    save_path = gallery_dir / "pjp_weld_analysis.svg"
    loaded.plot(section=True, force=True, save_path=str(save_path), show=False)
    print(f"Saved plot to: {save_path.name}")


if __name__ == "__main__":
    run()
