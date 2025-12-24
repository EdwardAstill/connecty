"""
Bolt plotting demo saving images to gallery/bolt plotting.

Shows elastic vs ICR force plots for a rectangular group and a circular
ring to illustrate vector and color mapping.
"""
from __future__ import annotations

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless plotting

from pathlib import Path

from connecty import BoltGroup, Load


def run() -> None:
    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / "gallery" / "bolt plotting"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Rectangular pattern
    rect = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=80, spacing_z=70, diameter=22)
    load_rect = Load(Fx=50000, Fy=-140000, Fz=35000, location=(0, 60, 130))

    rect_elastic = rect.analyze(load_rect, method="elastic")
    rect_icr = rect.analyze(load_rect, method="icr")

    rect_elastic.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        cmap="coolwarm",
        show=False,
        save_path=str(out_dir / "rectangular_elastic_shear.svg"),
        mode="shear",
    )
    rect_icr.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        cmap="viridis",
        show=False,
        save_path=str(out_dir / "rectangular_icr_shear.svg"),
        mode="shear",
    )
    rect_elastic.plot(
        force=True,
        bolt_forces=False,
        colorbar=True,
        cmap="RdBu_r",
        show=False,
        save_path=str(out_dir / "rectangular_elastic_axial.svg"),
        mode="axial",
    )

    # Circular pattern
    ring = BoltGroup.from_circle(n=10, radius=120, diameter=20, center=(0, 0), start_angle=18)
    load_ring = Load(Fx=40000, Fy=-80000, Fz=60000, location=(0, 0, 90))

    ring_elastic = ring.analyze(load_ring, method="elastic")
    ring_icr = ring.analyze(load_ring, method="icr")
    
    ring_elastic.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        cmap="coolwarm",
        show=False,
        save_path=str(out_dir / "ring_elastic_shear.svg"),
        mode="shear",
    )
    ring_icr.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        cmap="viridis",
        show=False,
        save_path=str(out_dir / "ring_icr_shear.svg"),
        mode="shear",
    )
    ring_elastic.plot(
        force=True,
        bolt_forces=False,
        colorbar=True,
        cmap="RdBu_r",
        show=False,
        save_path=str(out_dir / "ring_elastic_axial.svg"),
        mode="axial",
    )

    print(f"Saved bolt plots to {out_dir}")


if __name__ == "__main__":
    run()
