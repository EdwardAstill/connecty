"""End-to-end bolt example: setup, analyze, plot, and check.

Outputs (created under `gallery/bolt/`):
- 01_setup.txt
- 02_plot.txt
- 03_analysis.txt
- 04_check_aisc.txt
- 05_check_as4100.txt
- bolt_plot_shear.svg
- bolt_plot_axial.svg
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for scripts/CI

from connecty import BoltConnection, BoltGroup, Load, Plate


@dataclass(frozen=True)
class BoltCase:
    name: str
    connection: BoltConnection
    load: Load


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _out_dir() -> Path:
    out_dir = _project_root() / "gallery" / "bolt"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(f"Saved: {path}")


def _format_setup(case: BoltCase) -> str:
    bg = case.connection.bolt_group
    plate = case.connection.plate
    load = case.load

    lines: list[str] = []
    lines.append("BOLT EXAMPLE - SETUP")
    lines.append("=" * 80)
    lines.append(f"Case: {case.name}")
    lines.append("")
    lines.append("Units: choose any consistent system (this example uses mm, N, N*mm)")
    lines.append("")
    lines.append(f"Bolt group: n={bg.n}, d={bg.diameter:.2f}, grade={bg.grade}")
    lines.append("Positions (y, z):")
    for i, (y, z) in enumerate(bg.positions, start=1):
        lines.append(f"  {i:>2}: y={y:>8.2f}, z={z:>8.2f}")
    lines.append("")
    lines.append(
        "Plate (axis-aligned rectangle in y-z): "
        f"corner_a={plate.corner_a}, corner_b={plate.corner_b}, "
        f"t={plate.thickness:.2f}, fu={plate.fu:.1f}, fy={plate.fy}"
    )
    lines.append("")
    lines.append(
        "Applied load (forces + moments at a location): "
        f"Fx={load.Fx:.2f}, Fy={load.Fy:.2f}, Fz={load.Fz:.2f}, "
        f"Mx={load.Mx:.2f}, My={load.My:.2f}, Mz={load.Mz:.2f}, "
        f"location={load.location}"
    )
    return "\n".join(lines)


def _format_analysis(title: str, result) -> str:
    lines: list[str] = []
    lines.append(title)
    lines.append("=" * 80)
    lines.append(f"shear_method={result.shear_method}, tension_method={result.tension_method}")
    if result.icr_point is not None:
        lines.append(f"icr_point=(y={result.icr_point[0]:.3f}, z={result.icr_point[1]:.3f})")
    lines.append(
        "Summary: "
        f"max_shear={result.max_shear_force:.3f}, "
        f"max_axial={result.max_axial_force:.3f}, "
        f"max_combined_stress={result.max_combined_stress:.3f}"
    )
    lines.append("")
    lines.append("Per-bolt forces/stresses:")
    lines.append("  #    y        z        Fy        Fz        Fx        R      tau    sigma    comb")
    for i, br in enumerate(result.to_bolt_results(), start=1):
        lines.append(
            f"  {i:>2}  {br.y:>7.2f}  {br.z:>7.2f}  "
            f"{br.Fy:>8.2f}  {br.Fz:>8.2f}  {br.Fx:>8.2f}  {br.resultant:>8.2f}  "
            f"{br.shear_stress:>6.2f}  {br.axial_stress:>6.2f}  {br.combined_stress:>6.2f}"
        )
    return "\n".join(lines)


def _render_formula_trace(standard: str, calc: dict[str, Any], meta: dict[str, Any]) -> list[str]:
    """Render explicit calculation traces based on the standard and available calc data."""
    lines = []
    
    if standard == "aisc":
        # Inputs
        phi = calc.get("phi", 0.75)
        area_b = calc.get("area_b", 0.0)
        
        # --- Shear (Vn) ---
        Fnv = calc.get("Fnv", 0.0)
        n_s = calc.get("n_s", 1)
        # Simplified trace for typical case (no fillers)
        vn_nom = n_s * Fnv * area_b / 1000.0  # kN
        lines.append(f"      Vn = phi * Fnv * Ab * ns = {phi} * {Fnv:.1f} * {area_b:.1f} * {n_s} / 1000 = {phi * vn_nom:.3f} kN")

        # --- Tension (Tn) ---
        Fnt_prime = calc.get("Fnt_prime", 0.0)
        tn_nom = Fnt_prime * area_b / 1000.0 # kN
        lines.append(f"      Tn = phi * Fnt' * Ab     = {phi} * {Fnt_prime:.1f} * {area_b:.1f} / 1000 = {phi * tn_nom:.3f} kN")
        
        # --- Bearing (Bn) ---
        # min of bearing and tearout
        br_nom = calc.get("bearing_nom_kN", 0.0)
        tr_nom = calc.get("tear_nom_kN", 0.0)
        lines.append(f"      Bn = phi * min(R_bearing, R_tearout)")
        lines.append(f"         = {phi} * min({br_nom:.1f}, {tr_nom:.1f}) = {phi * min(br_nom, tr_nom):.3f} kN")

    elif standard == "as4100":
        # Resistance factors per the implemented AS 4100 checks:
        # - shear/tension: ϕ = 0.8
        # - bearing/tearout: ϕ = 0.9
        phi_st = 0.8
        phi_b = 0.9
        fuf = meta.get("fuf", 0.0)
        kr = meta.get("reduction_factor_kr", 1.0)
        
        # --- Shear (Vn) ---
        # Vf = phi * 0.62 * fuf * kr * (nn*Ac + nx*Ao)
        Ac = meta.get("Ac", 0.0)
        Ao = meta.get("Ao", 0.0)
        nn = meta.get("nn_shear_planes", 0)
        nx = meta.get("nx_shear_planes", 0)
        
        area_term = nn * Ac + nx * Ao
        vn_nom = 0.62 * fuf * kr * area_term / 1000.0  # kN
        
        lines.append(f"      Vn (Shear)   = phi * 0.62 * fuf * kr * (nn*Ac + nx*Ao)")
        lines.append(f"                   = {phi_st} * 0.62 * {fuf:.0f} * {kr} * ({nn}*{Ac:.1f} + {nx}*{Ao:.1f})")
        lines.append(f"                   = {phi_st} * 0.62 * {fuf:.0f} * {kr} * {area_term:.1f} / 1000")
        lines.append(f"                   = {phi_st * vn_nom:.3f} kN")

        # --- Tension (Tn) ---
        # Ntf = phi * As * fuf
        As = meta.get("As", 0.0)
        ntf_nom = As * fuf / 1000.0  # kN
        lines.append(f"      Tn (Tension) = phi * As * fuf")
        lines.append(f"                   = {phi_st} * {As:.1f} * {fuf:.0f} / 1000")
        lines.append(f"                   = {phi_st * ntf_nom:.3f} kN")
        
        # --- Bearing (Bn) ---
        # Design bearing/tearout capacity: 0.9 * min(Vb, Vp)
        # Vb = 3.2 * tp * df * fup
        # Vp = ae * tp * fup, where connecty uses ae := edge_clear (bolt center to nearest plate edge)
        df = meta.get("bolt_diameter", 0.0)
        tp = meta.get("plate_thickness", 0.0)
        fup = meta.get("plate_fu", 0.0)
        br_cap = calc.get("bearing_capacity_kN", 0.0)
        ae = calc.get("edge_clear", None)
        
        vb = 3.2 * df * tp * fup / 1000.0
        vp = None if ae is None else (float(ae) * tp * fup / 1000.0)
        governing = vb if vp is None else min(vb, vp)
        
        lines.append(f"      Bn (Bearing) = phi * min(Vb, Vp)")
        lines.append(f"                   Vb = 3.2 * tp * df * fup = 3.2 * {tp:.1f} * {df:.1f} * {fup:.0f} / 1000 = {vb:.3f} kN")
        if vp is not None:
            lines.append(f"                   Vp = ae * tp * fup       = {float(ae):.1f} * {tp:.1f} * {fup:.0f} / 1000 = {vp:.3f} kN")
        lines.append(f"                   = {phi_b} * {governing:.3f} = {phi_b * governing:.3f} kN")
        if abs(br_cap - phi_b * governing) > 0.05:
            lines.append(f"                   → {br_cap:.3f} kN (implemented)")

    return lines


def _format_check(title: str, check) -> str:
    lines: list[str] = []
    lines.append(title)
    lines.append("=" * 80)
    lines.append(f"connection_type={check.connection_type}, method={check.method}")
    lines.append(f"governing_bolt_index={check.governing_bolt_index}")
    lines.append(f"governing_limit_state={check.governing_limit_state}")
    lines.append(f"governing_utilization={check.governing_utilization:.4f}")

    # Method-wide inputs/constants
    meta = getattr(check, "meta", {})
    standard = meta.get("standard", "")

    if meta:
        lines.append("")
        lines.append("Meta:")
        for key in sorted(meta.keys()):
            value = meta[key]
            lines.append(f"  {key}: {value}")

    lines.append("")
    lines.append("Per-bolt:")
    for d in check.details:
        slip_util = d.slip_util
        slip_part = ""
        if slip_util is not None:
            slip_part = f", slip_util={slip_util:.4f}"
        lines.append(f"  bolt #{d.bolt_index + 1} @ (y={d.point[0]:.2f}, z={d.point[1]:.2f})")
        lines.append(
            f"    Demand: V={d.shear_demand:.3f} kN, T={d.tension_demand:.3f} kN"
        )
        lines.append(
            f"    Capacity: Vn={d.shear_capacity:.3f} kN, Tn={d.tension_capacity:.3f} kN, "
            f"Bn={d.bearing_capacity:.3f} kN"
            + ("" if d.slip_capacity is None else f", Sn={d.slip_capacity:.3f} kN")
        )
        lines.append(
            f"    Util: shear={d.shear_util:.4f}, tension={d.tension_util:.4f}, "
            f"bearing={d.bearing_util:.4f}{slip_part} "
            f"-> {d.governing_limit_state} ({d.governing_util:.4f})"
        )

        calc = getattr(d, "calc", {})
        if calc:
            lines.append("    Trace:")
            trace_lines = _render_formula_trace(standard, calc, meta)
            for line in trace_lines:
                lines.append(line)

            lines.append("    Calc (Raw):")
            for key in sorted(calc.keys()):
                value = calc[key]
                if value is None:
                    continue
                lines.append(f"      {key}: {value}")

    return "\n".join(lines)


def _make_case(*, grade: str, name: str) -> BoltCase:
    # Geometry (same for all cases, only grade changes for check standard defaults)
    bolt_group = BoltGroup.from_pattern(
        rows=3,
        cols=2,
        spacing_y=75.0,
        spacing_z=60.0,
        diameter=20.0,
        grade=grade,
        origin=(0.0, 0.0),
    )

    plate = Plate(
        corner_a=(-125.0, -80.0),
        corner_b=(125.0, 80.0),
        thickness=12.0,
        fu=450.0,
        fy=350.0,
    )

    connection = BoltConnection(bolt_group=bolt_group, plate=plate, n_shear_planes=1)

    load = Load(
        Fx=30_000.0,
        Fy=-120_000.0,
        Fz=45_000.0,
        My=6_000_000.0,
        Mz=-4_000_000.0,
        # Apply the load at a point ON the plate (x is out-of-plane; y/z lie on the plate rectangle).
        # Plate bounds are y∈[-125,125], z∈[-80,80] for this example.
        location=(0.0, 50.0, 40.0),
    )

    return BoltCase(name=name, connection=connection, load=load)


def run() -> None:
    out_dir = _out_dir()

    # Two grades so we can demonstrate both standards cleanly.
    case_aisc = _make_case(grade="A325", name="AISC_360_22_A325")
    case_as4100 = _make_case(grade="8.8", name="AS4100_8p8")

    # --- Setup docs ---
    _write_text(out_dir / "01_setup.txt", _format_setup(case_aisc))

    # --- Analysis ---
    result_aisc = case_aisc.connection.analyze(case_aisc.load, shear_method="elastic", tension_method="accurate")
    result_as4100 = case_as4100.connection.analyze(case_as4100.load, shear_method="elastic", tension_method="accurate")

    _write_text(out_dir / "03_analysis.txt", _format_analysis("BOLT ANALYSIS (ELASTIC + ACCURATE)", result_aisc))

    # --- Plot ---
    plot_path_shear = out_dir / "bolt_plot_shear.svg"
    result_aisc.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        cmap="coolwarm",
        show=False,
        save_path=str(plot_path_shear),
        mode="shear",
        force_unit="N",
        length_unit="mm",
    )

    plot_path_axial = out_dir / "bolt_plot_axial.svg"
    result_aisc.plot(
        force=True,
        bolt_forces=False,
        colorbar=True,
        cmap="RdBu_r",
        show=False,
        save_path=str(plot_path_axial),
        mode="axial",
        force_unit="N",
        length_unit="mm",
    )
    _write_text(
        out_dir / "02_plot.txt",
        "\n".join(
            [
                "BOLT PLOT",
                "=" * 80,
                f"Saved image (shear): {plot_path_shear}",
                f"Saved image (axial): {plot_path_axial}",
                "Shear plot: plate outline + bolt layout + per-bolt shear magnitudes (color) + shear arrows.",
                "Axial plot: plate outline + bolt layout + per-bolt axial force (color, +tension/-compression).",
            ]
        ),
    )

    # --- Checks ---
    check_aisc = result_aisc.check(
        standard="aisc",
        connection_type="bearing",
        hole_type="standard",
        threads_in_shear_plane=True,
    )
    _write_text(out_dir / "04_check_aisc.txt", _format_check("AISC 360-22 CHECK (bearing)", check_aisc))

    check_as4100 = result_as4100.check(
        standard="as4100",
        connection_type="bearing",
        hole_type="standard",
    )
    _write_text(out_dir / "05_check_as4100.txt", _format_check("AS 4100 CHECK (bearing)", check_as4100))

    print("")
    print("Done. Outputs written to:")
    print(f"  {out_dir}")


if __name__ == "__main__":
    run()
