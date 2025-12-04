"""
Example 8: Explore how the ICR rotation changes with eccentricity.

Runs the same shear combination at three different offsets from the centroid
and prints how the instantaneous center shifts while tracking utilization.
"""
from pathlib import Path
from typing import Sequence

from sectiony.library import rhs

from connecty import Force, StressResult, Weld, WeldParameters

section = rhs(b=120, h=120, t=10, r=10)

params = WeldParameters(
    weld_type="fillet",
    leg=6.0,
    electrode="E70"
)

weld = Weld.from_section(section=section, parameters=params)

OFFSETS: Sequence[float] = [15.0, 35.0, 70.0]


def summarize_icr(offset: float) -> StressResult:
    """
    Calculate ICR stress for a given horizontal location offset.
    """
    force = Force(
        Fy=-130000,
        Fz=28000,
        location=(0.0, offset)
    )
    result = weld.stress(force, method="icr")

    rotation_label = f"{result.rotation:.1f} mm" if result.rotation is not None else "n/a"
    icr_point = result.icr_point
    icr_label = (
        f"({icr_point[0]:.1f}, {icr_point[1]:.1f})"
        if icr_point is not None else "n/a"
    )

    print(f"Offset {offset:5.0f} mm | Rotation {rotation_label:>8} | "
          f"Util {result.utilization():.1%} | ICR {icr_label}")

    return result


print("=" * 60)
print("EXAMPLE 8: ICR ROTATION TREND WITH ECCENTRICITY")
print("=" * 60)
print("Each row shows the instantaneous center for the same shear combination")
print("applied at increasing horizontal offsets.")
print()

last_result: StressResult | None = None
for off in OFFSETS:
    last_result = summarize_icr(off)

if last_result is not None:
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)
    save_path = gallery_dir / "example8_icr_rotation_trend.svg"

    last_result.plot(
        section=True,
        force=True,
        cmap="coolwarm",
        weld_linewidth=5.0,
        show=False,
        save_path=str(save_path)
    )

    print(f"\nSaved: {save_path}")

