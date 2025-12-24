"""Bolt group plotting: elastic vs ICR shear, and axial tension.

Plots the shared 3×2 rectangular bolt group from bolt_demo.py with:
    - Elastic shear distribution
    - ICR (instantaneous center of rotation) shear distribution
    - Axial tension (from plate method)

Output: gallery/bolt plotting/
"""

from __future__ import annotations

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless plotting

from pathlib import Path

from connecty import ConnectionResult

from common.bolt_demo import make_demo_case


def run() -> None:
    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / "gallery" / "bolt plotting"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    case = make_demo_case(grade="A325")

    # Elastic shear analysis
    elastic_result = ConnectionResult(
        connection=case.connection,
        load=case.load,
        shear_method="elastic",
        tension_method="accurate",
    )

    # ICR shear analysis
    icr_result = ConnectionResult(
        connection=case.connection,
        load=case.load,
        shear_method="icr",
        tension_method="accurate",
    )

    # === Shear force plots ===
    elastic_result.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        cmap="coolwarm",
        show=False,
        save_path=str(out_dir / "elastic_shear_forces.svg"),
        mode="shear",
        force_unit="N",
        length_unit="mm",
    )

    icr_result.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        cmap="viridis",
        show=False,
        save_path=str(out_dir / "icr_shear_forces.svg"),
        mode="shear",
        force_unit="N",
        length_unit="mm",
    )

    # === Axial tension plot (using elastic for reference) ===
    elastic_result.plot(
        force=True,
        bolt_forces=False,
        colorbar=True,
        cmap="RdBu_r",
        show=False,
        save_path=str(out_dir / "axial_tension_forces.svg"),
        mode="axial",
        force_unit="N",
        length_unit="mm",
    )

    print(f"Saved 3 bolt plots to: {out_dir}")
    print(f"  - elastic_shear_forces.svg")
    print(f"  - icr_shear_forces.svg")
    print(f"  - axial_tension_forces.svg")


if __name__ == "__main__":
    run()
