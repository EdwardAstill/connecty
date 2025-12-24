"""
Bolt check examples (bearing vs slip-critical) writing text outputs.

Runs AISC 360-22 checks for A325 bolts in bearing and slip-critical
configurations and saves summaries to gallery/bolt check.
"""
from __future__ import annotations

from pathlib import Path

from connecty import ConnectionResult

from common.bolt_demo import demo_edge_distances_mm, make_demo_case


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

    case = make_demo_case(grade="A325")
    edge_y, edge_z, _edge_clear = demo_edge_distances_mm(case)

    # Use the same load for both checks so only the connection type changes.
    load = case.load

    # Bearing-type check (threads in shear plane)
    result_bearing = ConnectionResult(
        connection=case.connection,
        load=load,
        shear_method="elastic",
        tension_method="accurate",
    )
    bearing_result = result_bearing.check(
        standard="aisc",
        connection_type="bearing",
        hole_type="standard",
        slot_orientation="perpendicular",
        threads_in_shear_plane=True,
        slip_class="A",
        n_s=1,
        fillers=0,
        edge_distance_y=edge_y,
        edge_distance_z=edge_z,
        use_analysis_bolt_tension_if_present=True,
    )

    # Slip-critical check (Class B, slots perpendicular)
    result_slip = ConnectionResult(
        connection=case.connection,
        load=load,
        shear_method="elastic",
        tension_method="accurate",
    )
    slip_result = result_slip.check(
        standard="aisc",
        connection_type="slip-critical",
        hole_type="short_slotted",
        slot_orientation="perpendicular",
        threads_in_shear_plane=False,
        slip_class="B",
        n_s=2,
        fillers=0,
        n_b_tension=case.bolt_group.n,
        edge_distance_y=edge_y,
        edge_distance_z=edge_z,
        use_analysis_bolt_tension_if_present=True,
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
