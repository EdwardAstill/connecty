"""
Explore how the ICR rotation changes with eccentricity.
"""
from pathlib import Path
from typing import Sequence
from sectiony.library import rhs
from connecty import Load, Weld, WeldParams, LoadedWeld

section = rhs(b=120, h=120, t=10, r=10)
params = WeldParams(type="fillet", leg=6.0)
weld = Weld.from_section(section=section, parameters=params)
OFFSETS: Sequence[float] = [15.0, 35.0, 70.0]


def analyze_at_offset(offset: float) -> LoadedWeld:
    load = Load(Fy=-130000, Fz=28000, location=(0.0, 0.0, offset))
    loaded = LoadedWeld(weld, load, method="icr")

    F_EXX = 483.0
    phi = 0.75
    allowable = phi * 0.60 * F_EXX
    util = loaded.max / allowable

    icr_label = "n/a"
    if loaded.icr_point is not None:
        icr_label = f"({loaded.icr_point[0]:.1f}, {loaded.icr_point[1]:.1f})"

    print(
        f"Offset {offset:5.0f} mm | Rotation {loaded.rotation or 0:.1f} mm | "
        f"Max stress {loaded.max:6.1f} MPa | Util {util:.1%} | ICR {icr_label}"
    )
    return loaded


def run() -> None:
    print("=" * 60)
    print("ICR ROTATION TREND WITH ECCENTRICITY")
    print("=" * 60)
    print()

    last_result = None
    for off in OFFSETS:
        last_result = analyze_at_offset(off)

    if last_result is not None:
        gallery_dir = Path(__file__).parent.parent / "gallery"
        gallery_dir.mkdir(exist_ok=True)
        save_path = gallery_dir / "icr_rotation_eccentricity_trend.svg"
        last_result.plot(section=True, force=True, cmap="coolwarm", weld_linewidth=5.0, info=True, show=False, save_path=str(save_path))
        print(f"\nSaved: {save_path}")


if __name__ == "__main__":
    run()
