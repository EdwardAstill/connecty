"""
Explore how the ICR rotation changes with eccentricity.

Runs the same shear combination at three different offsets from the centroid
and shows how the instantaneous center shifts with increasing eccentricity.
"""
from pathlib import Path
from typing import Sequence

from sectiony.library import rhs

from connecty import Load, Weld, WeldParams, LoadedWeld

section = rhs(b=120, h=120, t=10, r=10)

params = WeldParams(
    type="fillet",
    leg=6.0
)

weld = Weld.from_section(section=section, parameters=params)

OFFSETS: Sequence[float] = [15.0, 35.0, 70.0]


def analyze_at_offset(offset: float) -> LoadedWeld:
    """
    Calculate ICR stress for a given horizontal location offset.
    """
    load = Load(
        Fy=-130000,  # 130 kN downward
        Fz=28000,    # 28 kN horizontal
        location=(0.0, 0.0, offset)  # Increasing offset
    )
    loaded = LoadedWeld(weld, load, method="icr")

    rotation_label = f"{loaded.rotation:.1f} mm" if loaded.rotation is not None else "n/a"
    icr_point = loaded.icr_point
    icr_label = (
        f"({icr_point[0]:.1f}, {icr_point[1]:.1f})"
        if icr_point is not None else "n/a"
    )

    # Design check
    F_EXX = 483.0  # E70
    phi = 0.75
    allowable = phi * 0.60 * F_EXX
    util = loaded.max / allowable

    print(f"Offset {offset:5.0f} mm | Rotation {rotation_label:>8} | "
          f"Max stress {loaded.max:6.1f} MPa | Util {util:.1%} | ICR {icr_label}")

    return loaded


print("=" * 60)
print("ICR ROTATION TREND WITH ECCENTRICITY")
print("=" * 60)
print("Each row shows the instantaneous center for the same shear combination")
print("applied at increasing horizontal offsets.")
print()

last_result: LoadedWeld | None = None
for off in OFFSETS:
    last_result = analyze_at_offset(off)

print()
print("As eccentricity increases, the ICR point shifts to resist the additional")
print("moment, resulting in a more favorable stress distribution along the weld.")

if last_result is not None:
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)
    save_path = gallery_dir / "icr_rotation_eccentricity_trend.svg"

    last_result.plot(
        section=True,
        force=True,
        cmap="coolwarm",
        weld_linewidth=5.0,
        info=True,
        show=False,
        save_path=str(save_path)
    )

    print(f"\nSaved: {save_path}")
