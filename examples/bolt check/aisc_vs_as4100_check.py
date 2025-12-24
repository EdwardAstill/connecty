"""Bolt check comparison: AISC 360-22 vs AS 4100 (elastic analysis).

Uses the shared 3×2 rectangular bolt connection and applies:
    - AISC 360-22 check (A325 grade)
    - AS 4100 / Steel Designers Handbook check (8.8 grade)

Both use ELASTIC shear analysis with accurate plate tension method.
"""

from __future__ import annotations

from pathlib import Path

from connecty import ConnectionResult

from common.bolt_demo import make_demo_case


def format_check(title: str, result) -> str:
    """Format check result for display."""
    lines = [title, "  Governing bolt index: " + str(result.governing_bolt_index)]
    lines.append(f"  Governing limit state: {result.governing_limit_state}")
    lines.append(f"  Governing utilization: {result.governing_utilization:.3f}")
    lines.append("  Per-bolt checks:")
    for d in result.details:
        slip_util = getattr(d, "slip_util", None)
        interaction_util = getattr(d, "interaction_util", None)
        slip_part = f", slip={slip_util:.3f}" if slip_util is not None else ""
        interaction_part = f", interaction={interaction_util:.3f}" if interaction_util is not None else ""
        lines.append(
            f"    #{d.bolt_index + 1} @ (y={d.point[0]:.1f}, z={d.point[1]:.1f})"
            f"  V={d.shear_demand:.2f} kN, T={d.tension_demand:.2f} kN"
        )
        lines.append(
            f"      shear_util={d.shear_util:.3f}, tension_util={d.tension_util:.3f},"
            f" bearing_util={d.bearing_util:.3f}{interaction_part}{slip_part} -> {d.governing_limit_state}"
        )
    return "\n".join(lines)


def run() -> None:
    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / "gallery" / "bolt check"
    out_dir.mkdir(parents=True, exist_ok=True)

    # === Shared geometry + shared load ===
    case_us = make_demo_case(grade="A325")
    case_au = make_demo_case(grade="8.8")

    # Analyze demands with ELASTIC shear distribution (requested)
    result_aisc = ConnectionResult(
        connection=case_us.connection,
        load=case_us.load,
        shear_method="elastic",
        tension_method="accurate",
    )
    result_as4100 = ConnectionResult(
        connection=case_au.connection,
        load=case_au.load,
        shear_method="elastic",
        tension_method="accurate",
    )

    # === AISC 360-22 check ===
    aisc_result = result_aisc.check(
        standard="aisc",
        connection_type="bearing",
        hole_type="standard",
        slot_orientation="perpendicular",
        threads_in_shear_plane=True,
    )

    # === AS 4100 (Steel Designers Handbook) check ===
    as4100_result = result_as4100.check(
        standard="as4100",
        connection_type="bearing",
        hole_type="standard",
        hole_type_factor=1.0,
        nn_shear_planes=1,
        nx_shear_planes=0,
        prying_allowance=0.25,
    )

    # === Format Output ===
    lines = [
        "BOLT CHECK COMPARISON: AISC 360-22 vs AS 4100 (Steel Designers Handbook)",
        "=" * 80,
        "",
        "Test Case: 3×2 bolt pattern (M20)",
        f"  Applied loads (analysis units): Fx={case_us.load.Fx/1000:.1f} kN, Fy={case_us.load.Fy/1000:.1f} kN, Fz={case_us.load.Fz/1000:.1f} kN",
        f"  Plate: t={case_us.plate.thickness:.1f} mm, fu={case_us.plate.fu:.0f} MPa, fy={case_us.plate.fy:.0f} MPa",
        f"  Analysis method: Elastic shear + plate tension (accurate)",
        "",
        "=" * 80,
        "",
        format_check("AISC 360-22 (A325)", aisc_result),
        "",
        "=" * 80,
        "",
        format_check("AS 4100 / SDHB (8.8)", as4100_result),
        "",
        "=" * 80,
        "",
        "Summary:",
        f"  AISC governing util:   {aisc_result.governing_utilization:.3f}",
        f"  AS4100 governing util: {as4100_result.governing_utilization:.3f}",
        f"  Difference: {abs(aisc_result.governing_utilization - as4100_result.governing_utilization):.3f}",
        "",
        "Note: Different resistance factors and capacity equations may result in",
        "different governing utilizations for the same connection.",
    ]

    out_path = out_dir / "aisc_vs_as4100_check.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved check summary to: {out_path}")


if __name__ == "__main__":
    run()
