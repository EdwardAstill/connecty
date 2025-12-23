"""
Bolt check examples (bearing vs slip-critical) writing text outputs.

Runs AISC 360-22 checks for A325 bolts in bearing and slip-critical
configurations and saves summaries to gallery/bolt check.
"""
from __future__ import annotations

from pathlib import Path

from connecty import BoltGroup, BoltDesignParams, Load


def format_check(title: str, result) -> str:
    lines = [title, "  Governing bolt index: " + str(result.governing_bolt_index)]
    lines.append(f"  Governing limit state: {result.governing_limit_state}")
    lines.append(f"  Governing utilization: {result.governing_utilization:.3f}")
    lines.append("  Per-bolt utilizations:")
    for d in result.details:
        slip_part = f", slip={d.slip_util:.3f}" if d.slip_util is not None else ""
        lines.append(
            f"    #{d.bolt_index + 1} @ (y={d.point[0]:.1f}, z={d.point[1]:.1f})"
            f"  V={d.shear_demand:.2f} kN, T={d.tension_demand:.2f} kN"
        )
        lines.append(
            f"      shear={d.shear_util:.3f}, tension={d.tension_util:.3f},"
            f" bearing={d.bearing_util:.3f}{slip_part} -> {d.governing_limit_state}"
        )
    return "\n".join(lines)


def run() -> None:
    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / "gallery" / "bolt check"
    out_dir.mkdir(parents=True, exist_ok=True)

    bolts = BoltGroup.from_pattern(rows=2, cols=3, spacing_y=80, spacing_z=70, diameter=20)

    # Factored loads
    load_bearing = Load(Fy=-110000, Fz=25000, Fx=30000, location=(0, 40, 120))
    load_slip = Load(Fy=-90000, Fz=45000, Fx=50000, location=(0, 30, 90))

    common_geom = dict(
        plate_fu=450.0,
        plate_thickness=14.0,
        edge_distance_y=55.0,
        edge_distance_z=60.0,
    )

    # Bearing-type check (threads in shear plane)
    design_bearing = BoltDesignParams(
        grade="A325",
        hole_type="standard",
        slot_orientation="perpendicular",
        threads_in_shear_plane=True,
        slip_class="A",
        n_s=1,
        fillers=0,
        **common_geom,
    )

    bearing_result = bolts.check_aisc(
        force=load_bearing,
        design=design_bearing,
        method="elastic",
        connection_type="bearing",
    )

    # Slip-critical check (Class B, slots perpendicular)
    design_slip = BoltDesignParams(
        grade="A325",
        hole_type="short_slotted",
        slot_orientation="perpendicular",
        threads_in_shear_plane=False,
        slip_class="B",
        n_s=2,
        fillers=0,
        n_b_tension=bolts.n,
        **common_geom,
    )

    slip_result = bolts.check_aisc(
        force=load_slip,
        design=design_slip,
        method="elastic",
        connection_type="slip-critical",
    )

    lines = [
        "BOLT CHECK SUMMARY (BEARING VS SLIP-CRITICAL)",
        "=" * 60,
        format_check("Bearing connection (A325, standard holes)", bearing_result),
        "",
        format_check("Slip-critical (A325, Class B, short slots perpendicular to load)", slip_result),
    ]

    out_path = out_dir / "bearing_vs_slip_check.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved check summary to: {out_path}")


if __name__ == "__main__":
    run()
