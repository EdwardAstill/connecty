"""
Bolt analysis examples (elastic vs ICR) with saved text outputs.

Produces force distribution summaries for two bolt groups and writes
results to gallery/bolt analysis/*.txt.
"""
from __future__ import annotations

from pathlib import Path
from connecty import BoltGroup, Load


def summarize(result_name: str, result, load_label: str) -> str:
    lines = [
        f"Case: {result_name}",
        f"  Method: {result.method}",
        f"  Load: {load_label}",
        f"  Max bolt force: {result.max_force:.2f} kN",
        f"  Min bolt force: {result.min_force:.2f} kN",
        f"  Mean bolt force: {result.mean:.2f} kN",
        f"  Max shear stress: {result.max_stress:.1f} MPa",
        f"  Min shear stress: {result.min_stress:.1f} MPa",
        f"  Mean shear stress: {result.mean_stress:.1f} MPa",
    ]
    if result.critical_index is not None and result.critical_bolt is not None:
        bf = result.critical_bolt
        lines.append(
            f"  Critical bolt #{result.critical_index + 1} at (y={bf.y:.1f}, z={bf.z:.1f}) -> R={bf.resultant:.2f} kN, stress={bf.shear_stress:.1f} MPa"
        )
    lines.append("  Per-bolt forces and stresses:")
    for i, bf in enumerate(result.bolt_forces, start=1):
        lines.append(
            f"    {i:>2}: Fy={bf.Fy:.2f} kN, Fz={bf.Fz:.2f} kN, R={bf.resultant:.2f} kN, stress={bf.shear_stress:.1f} MPa, angle={bf.angle:.1f} deg"
        )
    return "\n".join(lines)


def run() -> None:
    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / "gallery" / "bolt analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Rectangular group, eccentric vertical shear (torsion)
    rect = BoltGroup.from_pattern(rows=3, cols=3, spacing_y=70, spacing_z=60, diameter=20)
    load_rect = Load(Fy=-120000, Mx=5000000, location=(0, 90, 140))  # 120 kN down + 5 kN·m torsion, eccentric in z

    rect_elastic = rect.analyze(load_rect, method="elastic")
    rect_icr = rect.analyze(load_rect, method="icr")

    # Circular group, combined shear
    circle = BoltGroup.from_circle(n=8, radius=110, diameter=24, center=(0, 0))
    load_circ = Load(Fy=-90000, Fz=45000, Mx=3000000, location=(0, 0, 80))

    circ_elastic = circle.analyze(load_circ, method="elastic")
    circ_icr = circle.analyze(load_circ, method="icr")

    report_lines = [
        "BOLT ANALYSIS SUMMARY (ELASTIC VS ICR)",
        "=" * 60,
        summarize("Rectangular – Elastic", rect_elastic, "Fy=120 kN, Mx=5 kN·m @ z=140 mm"),
        "",
        summarize("Rectangular – ICR", rect_icr, "Fy=120 kN, Mx=5 kN·m @ z=140 mm"),
        "",
        summarize("Circular – Elastic", circ_elastic, "Fy=90 kN, Fz=45 kN, Mx=3 kN·m @ z=80 mm"),
        "",
        summarize("Circular – ICR", circ_icr, "Fy=90 kN, Fz=45 kN, Mx=3 kN·m @ z=80 mm"),
    ]

    out_path = out_dir / "elastic_vs_icr_analysis.txt"
    out_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Saved analysis summary to: {out_path}")


if __name__ == "__main__":
    run()