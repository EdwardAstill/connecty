"""Bolt group analysis demo (single geometry, four method combinations).

This example creates ONE 3×2 rectangular bolt pattern and runs all four
combinations of:
  - shear_method:  elastic | icr
  - tension_method: conservative | accurate

It prints a per-bolt table and writes the same text report to
gallery/bolt analysis/bolt_group_analysis.txt.
"""

from __future__ import annotations

from pathlib import Path

from connecty import ConnectionResult

from common.bolt_demo import make_demo_case


def _format_result(title: str, result: ConnectionResult) -> str:
    lines: list[str] = []
    lines.append(title)
    lines.append(f"  shear_method={result.shear_method}, tension_method={result.tension_method}")
    if result.icr_point is not None:
        lines.append(f"  icr_point=(y={result.icr_point[0]:.1f} mm, z={result.icr_point[1]:.1f} mm)")
    lines.append(
        "  Summary: "
        f"max_shear={result.max_shear_force/1000:.2f} kN, "
        f"max_axial={result.max_axial_force/1000:.2f} kN, "
        f"max_shear_stress={result.max_shear_stress:.1f} MPa, "
        f"max_axial_stress={result.max_axial_stress:.1f} MPa, "
        f"max_combined_stress={result.max_combined_stress:.1f} MPa"
    )
    lines.append("  Per-bolt forces/stresses (N, mm -> MPa):")
    lines.append("    #    y      z     Fy(kN)   Fz(kN)   Fx(kN)    R(kN)   tau(MPa)  sig(MPa)  comb(MPa)")
    for i, bf in enumerate(result.to_bolt_results(), start=1):
        lines.append(
            f"    {i:>1}  {bf.y:>6.1f} {bf.z:>6.1f}"
            f"  {bf.Fy/1000:>8.2f} {bf.Fz/1000:>8.2f} {bf.Fx/1000:>8.2f}"
            f"  {bf.resultant/1000:>8.2f}"
            f"  {bf.shear_stress:>8.1f}  {bf.axial_stress:>8.1f}  {bf.combined_stress:>8.1f}"
        )
    return "\n".join(lines)


def run() -> None:
    case = make_demo_case(grade="A325")

    combos = [
        ("elastic", "conservative"),
        ("elastic", "accurate"),
        ("icr", "conservative"),
        ("icr", "accurate"),
    ]

    reports: list[str] = []
    header = [
        "BOLT GROUP ANALYSIS (3x2 RECTANGULAR PATTERN)",
        "=" * 80,
        "Units: mm, N, N*mm (stresses in MPa = N/mm^2)",
        f"Bolts: n={case.bolt_group.n}, d={case.bolt_group.diameter:.0f} mm, grade={case.bolt_group.grade}",
        f"Plate: t={case.plate.thickness:.1f} mm, fu={case.plate.fu:.0f} MPa, fy={case.plate.fy:.0f} MPa",
        "Load:",
        f"  Fx={case.load.Fx/1000:.1f} kN, Fy={case.load.Fy/1000:.1f} kN, Fz={case.load.Fz/1000:.1f} kN",
        f"  My={case.load.My/1e6:.2f} kN*m, Mz={case.load.Mz/1e6:.2f} kN*m, at z={case.load.location[2]:.0f} mm",
        "=" * 80,
        "",
    ]
    reports.extend(header)

    for shear_method, tension_method in combos:
        result = ConnectionResult(
            connection=case.connection,
            load=case.load,
            shear_method=shear_method,
            tension_method=tension_method,
        )
        reports.append(_format_result(f"CASE: {shear_method.upper()} + {tension_method.upper()}", result))
        reports.append("")

    text = "\n".join(reports).rstrip() + "\n"
    print(text)

    out_dir = Path(__file__).resolve().parents[2] / "gallery" / "bolt analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "bolt_group_analysis.txt"
    out_path.write_text(text, encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    run()
