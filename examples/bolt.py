"""End-to-end bolt example: setup, analyze, plot, and check.

Outputs (created under `gallery/bolt/`):
- 01_setup.txt
- 02_plot.txt
- 03_analysis.txt
- 04_check_aisc.txt
- 05_check_as4100.txt
- 06_full_check_aisc.txt (comprehensive report)
- 07_full_check_as4100.txt (comprehensive report)
- bolt_plot_shear.svg
- bolt_plot_axial.svg
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for scripts/CI

from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate


@dataclass(frozen=True)
class BoltCase:
    name: str
    connection: BoltConnection
    load: Load


_PLATE_WIDTH_Z = 160.0  # width along z-axis
_PLATE_HEIGHT_Y = 250.0  # height along y-axis
_PLATE_CENTER = (0.0, 0.0)

# Small offset so the bolt group is not perfectly centered on the plate
_BOLT_OFFSET_Y = 10.0
_BOLT_OFFSET_Z = -5.0


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
    layout = case.connection.layout
    bolt = case.connection.bolt
    plate = case.connection.plate
    load = case.load
    if plate is None:
        raise ValueError("Bolt example requires a plate")

    plate_center_y, plate_center_z = plate.center
    bolt_centroid_y = layout.Cy
    bolt_centroid_z = layout.Cz
    offset_y = bolt_centroid_y - plate_center_y
    offset_z = bolt_centroid_z - plate_center_z

    lines: list[str] = []
    lines.append("BOLT EXAMPLE - SETUP")
    lines.append("=" * 80)
    lines.append(f"Case: {case.name}")
    lines.append("")
    lines.append("Units: choose any consistent system (this example uses mm, N, N*mm)")
    lines.append("")
    lines.append(f"Bolt layout: n={layout.n}, d={bolt.diameter:.2f}, grade={bolt.grade}")
    lines.append(
        f"Bolt group centroid: (y={bolt_centroid_y:.2f}, z={bolt_centroid_z:.2f}) mm "
        f"(offset from plate center: Δy={offset_y:.2f} mm, Δz={offset_z:.2f} mm)"
    )
    lines.append("Positions (y, z):")
    for i, (y, z) in enumerate(layout.points, start=1):
        lines.append(f"  {i:>2}: y={y:>8.2f}, z={z:>8.2f}")
    lines.append("")
    lines.append(
        "Plate (axis-aligned rectangle in y-z): "
        f"width={plate.width:.1f}, height={plate.height:.1f}, center={plate.center}, "
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
    for i, br in enumerate(result.to_bolt_forces(), start=1):
        lines.append(
            f"  {i:>2}  {br.y:>7.2f}  {br.z:>7.2f}  "
            f"{br.Fy:>8.2f}  {br.Fz:>8.2f}  {br.Fx:>8.2f}  {br.resultant:>8.2f}  "
            f"{br.shear_stress:>6.2f}  {br.axial_stress:>6.2f}  {br.combined_stress:>6.2f}"
        )
    return "\n".join(lines)


def _render_equations_once(standard: str, meta: dict[str, Any]) -> list[str]:
    """Render the capacity equations once (without specific values)."""
    lines = []
    
    if standard == "aisc":
        lines.append("Capacity Equations (AISC 360-22):")
        lines.append("  Shear:   Vn = φ * Fnv * Ab * ns")
        lines.append("  Tension: Tn = φ * Fnt' * Ab")
        lines.append("           where Fnt' = min(Fnt, 1.3*Fnt - (Fnt/(φ*Fnv))*f_rv), f_rv = Vu/(Ab*ns)")
        lines.append("  Bearing: Bn = φ * min(R_bearing, R_tearout)")
        lines.append("           R_bearing = 2.4 * d * t * Fu")
        lines.append("           R_tearout = 1.2 * lc * t * Fu")
        
    elif standard == "as4100":
        lines.append("Capacity Equations (AS 4100):")
        lines.append("  Shear:   Vn = φ * 0.62 * fuf * kr * (nn*Ac + nx*Ao)")
        lines.append("  Tension: Tn = φ * As * fuf")
        lines.append("  Bearing: Bn = φ * min(Vb, Vp)")
        lines.append("           Vb = 3.2 * tp * df * fup")
        lines.append("           Vp = a_e * tp * fup")
        lines.append("           where a_e = edge_clear - dh/2 (AS 4100:2020 Cl. 9.3.2.4)")
        prying = meta.get("prying_allowance", 0.0)
        if prying > 0:
            lines.append(f"  Note: Tension demand includes prying allowance ({prying*100:.0f}%): Tu_design = Tu * (1 + {prying})")
    
    return lines


def _format_full_check(title: str, case: BoltCase, result, check) -> str:
    """Comprehensive check report with all information in one document."""
    lines: list[str] = []
    lines.append(title)
    lines.append("=" * 80)
    lines.append("")
    
    # 1. BOLT GROUP CONFIGURATION
    lines.append("1. BOLT GROUP CONFIGURATION")
    lines.append("-" * 80)
    layout = case.connection.layout
    bolt = case.connection.bolt
    plate = case.connection.plate
    if plate is None:
        raise ValueError("Bolt example requires a plate")
    plate_center_y, plate_center_z = plate.center
    bolt_centroid_y = layout.Cy
    bolt_centroid_z = layout.Cz
    offset_y = bolt_centroid_y - plate_center_y
    offset_z = bolt_centroid_z - plate_center_z
    lines.append(f"Bolt grade: {bolt.grade}")
    lines.append(f"Bolt diameter: {bolt.diameter:.2f} mm")
    lines.append(f"Number of bolts: {layout.n}")
    lines.append(f"Number of shear planes: {case.connection.n_shear_planes}")
    lines.append(f"Bolt group centroid: (y={bolt_centroid_y:.2f}, z={bolt_centroid_z:.2f}) mm")
    lines.append(f"Plate center: (y={plate_center_y:.2f}, z={plate_center_z:.2f}) mm")
    lines.append(f"Bolt group offset from plate center: Δy={offset_y:.2f} mm, Δz={offset_z:.2f} mm")
    lines.append("")
    lines.append("Bolt positions (y, z) in mm:")
    lines.append("  #    y        z")
    for i, (y, z) in enumerate(layout.points, start=1):
        lines.append(f"  {i:>2}  {y:>7.2f}  {z:>7.2f}")
    lines.append("")
    lines.append(
        f"Plate: width={plate.width:.1f} mm, height={plate.height:.1f} mm, "
        f"t={plate.thickness:.1f} mm, fu={plate.fu:.0f} MPa, fy={plate.fy}"
    )
    lines.append(f"Plate bounds: y=[{plate.y_min:.1f}, {plate.y_max:.1f}], z=[{plate.z_min:.1f}, {plate.z_max:.1f}]")
    lines.append("")
    
    # 2. LOAD INFORMATION
    lines.append("2. LOAD INFORMATION")
    lines.append("-" * 80)
    load = case.load
    lines.append(f"Forces:  Fx={load.Fx:.2f} N, Fy={load.Fy:.2f} N, Fz={load.Fz:.2f} N")
    lines.append(f"Moments: Mx={load.Mx:.2f} N·mm, My={load.My:.2f} N·mm, Mz={load.Mz:.2f} N·mm")
    lines.append(f"Location: {load.location}")
    lines.append("")
    
    # 3. ANALYSIS RESULTS
    lines.append("3. ANALYSIS RESULTS")
    lines.append("-" * 80)
    lines.append(f"Method: shear={result.shear_method}, tension={result.tension_method}")
    lines.append("")
    lines.append("Per-bolt forces and stresses:")
    lines.append("  #    y        z        Fy        Fz        Fx        V         tau    sigma_x")
    lines.append("                        (N)       (N)       (N)       (N)      (MPa)    (MPa)")
    for i, br in enumerate(result.to_bolt_forces(), start=1):
        lines.append(
            f"  {i:>2}  {br.y:>7.2f}  {br.z:>7.2f}  "
            f"{br.Fy:>8.2f}  {br.Fz:>8.2f}  {br.Fx:>8.2f}  {br.shear:>8.2f}  "
            f"{br.shear_stress:>6.2f}  {br.axial_stress:>7.2f}"
        )
    lines.append("")
    
    # 4. CHECKING CRITERIA - GROUP LEVEL
    lines.append("4. CHECKING CRITERIA - GROUP LEVEL")
    lines.append("-" * 80)
    meta = check.get("meta", {})
    standard = meta.get("standard", "")
    
    if standard == "aisc":
        lines.append(f"Standard: AISC 360-22")
        lines.append(f"Grade: {meta.get('grade', 'N/A')}")
        lines.append(f"Threads in shear plane: {meta.get('threads_in_shear_plane', True)}")
        lines.append(f"Connection type: {meta.get('connection_type', 'N/A')}")
        lines.append(f"Hole type: {meta.get('hole_type', 'N/A')}")
        lines.append(f"Hole diameter: {meta.get('hole_dia', 0.0):.1f} mm")
        lines.append(f"Resistance factor (φ): {meta.get('phi', 0.75)}")
        lines.append(f"Nominal shear stress (Fnv): {meta.get('Fnv', 0.0):.0f} MPa")
        lines.append(f"Nominal tension stress (Fnt): {meta.get('Fnt', 0.0):.0f} MPa")
        lines.append(f"Bolt area (Ab): {meta.get('area_b', 0.0):.1f} mm²")
    elif standard == "as4100":
        lines.append(f"Standard: AS 4100")
        lines.append(f"Grade: {meta.get('grade', 'N/A')}")
        lines.append(f"Connection type: {meta.get('connection_type', 'N/A')}")
        lines.append(f"Hole type: {meta.get('hole_type', 'N/A')}")
        lines.append(f"Ultimate tensile strength (fuf): {meta.get('fuf', 0.0):.0f} MPa")
        lines.append(f"Tensile stress area (As): {meta.get('As', 0.0):.1f} mm²")
        lines.append(f"Core area (Ac): {meta.get('Ac', 0.0):.1f} mm²")
        lines.append(f"Prying allowance: {meta.get('prying_allowance', 0.0)*100:.0f}%")
    lines.append("")
    
    # 5. CHECKING CRITERIA - INDIVIDUAL BOLTS
    lines.append("5. CHECKING CRITERIA - INDIVIDUAL BOLT INPUTS")
    lines.append("-" * 80)
    
    if standard == "aisc":
        lines.append("  #    Vu      Tu      f_rv    Fnt'     lc    R_bear  R_tear")
        lines.append("       (kN)    (kN)    (MPa)   (MPa)   (mm)    (kN)    (kN)")
        for d in check["details"]:
            calc = d.get("calc", {})
            lines.append(
                f"  {d['bolt_index'] + 1:>2}  "
                f"{calc.get('Vu_kN', 0.0):>6.3f}  "
                f"{calc.get('Tu_kN', 0.0):>6.3f}  "
                f"{calc.get('f_rv', 0.0):>6.1f}  "
                f"{calc.get('Fnt_prime', 0.0):>6.1f}  "
                f"{calc.get('lc', 0.0):>5.1f}  "
                f"{calc.get('bearing_nom_kN', 0.0):>6.1f}  "
                f"{calc.get('tear_nom_kN', 0.0):>6.1f}"
            )
    elif standard == "as4100":
        lines.append("  #    Vu      Tu     Tu_pry   a_e     Vb      Vp")
        lines.append("       (kN)    (kN)    (kN)   (mm)    (kN)    (kN)")
        for d in check["details"]:
            calc = d.get("calc", {})
            lines.append(
                f"  {d['bolt_index'] + 1:>2}  "
                f"{calc.get('Vu_kN', 0.0):>6.3f}  "
                f"{calc.get('Tu_kN', 0.0):>6.3f}  "
                f"{calc.get('Tu_prying_kN', 0.0):>6.3f}  "
                f"{calc.get('a_e', 0.0):>5.1f}  "
                f"{calc.get('Vb_N', 0.0)/1000:>6.1f}  "
                f"{calc.get('Vp_N', 0.0)/1000:>6.1f}"
            )
    lines.append("")
    
    # 6. LIMIT STATE CHECKS
    lines.append("6. LIMIT STATE CHECKS")
    lines.append("-" * 80)
    
    # SHEAR CHECK
    lines.append("")
    lines.append("6.1 SHEAR RUPTURE")
    if standard == "aisc":
        lines.append("Equation: Vn = φ * Fnv * Ab * ns")
    elif standard == "as4100":
        lines.append("Equation: Vn = φ * 0.62 * fuf * kr * (nn*Ac + nx*Ao)")
    lines.append("")
    lines.append("  #    Applied   Capacity   Utilization")
    lines.append("        (kN)       (kN)")
    for d in check["details"]:
        lines.append(
            f"  {d['bolt_index'] + 1:>2}    {d['shear_demand_kN']:>6.3f}     {d['shear_capacity_kN']:>6.3f}      {d['shear_util']:>5.3f}"
        )
    lines.append("")
    
    # TENSION CHECK
    lines.append("6.2 TENSION RUPTURE")
    if standard == "aisc":
        lines.append("Equation: Tn = φ * Fnt' * Ab")
        lines.append("          where Fnt' = min(Fnt, 1.3*Fnt - (Fnt/(φ*Fnv))*f_rv)")
    elif standard == "as4100":
        lines.append("Equation: Tn = φ * As * fuf")
    lines.append("")
    lines.append("  #    Applied   Capacity   Utilization")
    lines.append("        (kN)       (kN)")
    for d in check["details"]:
        lines.append(
            f"  {d['bolt_index'] + 1:>2}    {d['tension_demand_kN']:>6.3f}     {d['tension_capacity_kN']:>6.3f}      {d['tension_util']:>5.3f}"
        )
    lines.append("")
    
    # BEARING CHECK
    lines.append("6.3 BEARING / TEAROUT")
    if standard == "aisc":
        lines.append("Equation: Bn = φ * min(R_bearing, R_tearout)")
        lines.append("          R_bearing = 2.4 * d * t * Fu")
        lines.append("          R_tearout = 1.2 * lc * t * Fu")
    elif standard == "as4100":
        lines.append("Equation: Bn = φ * min(Vb, Vp)")
        lines.append("          Vb = 3.2 * tp * df * fup")
        lines.append("          Vp = a_e * tp * fup")
    lines.append("")
    lines.append("  #    Applied   Capacity   Utilization")
    lines.append("        (kN)       (kN)")
    for d in check["details"]:
        lines.append(
            f"  {d['bolt_index'] + 1:>2}    {d['shear_demand_kN']:>6.3f}     {d['bearing_capacity_kN']:>6.3f}      {d['bearing_util']:>5.3f}"
        )
    lines.append("")
    
    # INTERACTION (AS 4100 only)
    if standard == "as4100":
        lines.append("6.4 SHEAR-TENSION INTERACTION")
        lines.append("Equation: U_int = (V*/φVn)² + (T*/φTn)²")
        lines.append("")
        lines.append("  #    Utilization")
        for d in check["details"]:
            lines.append(
                f"  {d['bolt_index'] + 1:>2}       {d.get('interaction_util', 0.0):>5.3f}"
            )
        lines.append("")
    
    # SUMMARY
    lines.append("7. SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Governing bolt: #{check['governing_bolt_index'] + 1}")
    lines.append(f"Governing limit state: {check['governing_limit_state']}")
    lines.append(f"Governing utilization: {check['governing_utilization']:.4f}")
    if check["governing_utilization"] <= 1.0:
        lines.append("Status: PASS")
    else:
        lines.append("Status: FAIL")
    
    return "\n".join(lines)


def _format_check(title: str, check) -> str:
    lines: list[str] = []
    lines.append(title)
    lines.append("=" * 80)
    lines.append(f"connection_type={check.get('connection_type')}, method={check.get('method')}")
    lines.append(f"governing_bolt_index={check.get('governing_bolt_index')}")
    lines.append(f"governing_limit_state={check.get('governing_limit_state')}")
    lines.append(f"governing_utilization={check.get('governing_utilization', 0.0):.4f}")

    # Method-wide inputs/constants
    meta = check.get("meta", {})
    standard = meta.get("standard", "")

    if meta:
        lines.append("")
        lines.append("Meta:")
        for key in sorted(meta.keys()):
            value = meta[key]
            lines.append(f"  {key}: {value}")

    # Show equations once
    lines.append("")
    equation_lines = _render_equations_once(standard, meta)
    for line in equation_lines:
        lines.append(line)

    lines.append("")
    lines.append("Per-bolt:")
    for d in check["details"]:
        slip_util = d.get("slip_util")
        slip_part = ""
        if slip_util is not None:
            slip_part = f", slip={slip_util:.4f}"
        lines.append(f"  bolt #{d['bolt_index'] + 1} @ (y={d['point'][0]:.2f}, z={d['point'][1]:.2f})")
        lines.append(
            f"    Demand: V={d.get('shear_demand_kN', 0.0):.3f} kN, T={d.get('tension_demand_kN', 0.0):.3f} kN"
        )
        lines.append(
            f"    Capacity: Vn={d.get('shear_capacity_kN', 0.0):.3f} kN, Tn={d.get('tension_capacity_kN', 0.0):.3f} kN, "
            f"Bn={d.get('bearing_capacity_kN', 0.0):.3f} kN"
            + ("" if d.get("slip_capacity_kN") is None else f", Sn={d.get('slip_capacity_kN'):.3f} kN")
        )
        lines.append(
            f"    Util: shear={d.get('shear_util', 0.0):.4f}, tension={d.get('tension_util', 0.0):.4f}, "
            f"bearing={d.get('bearing_util', 0.0):.4f}{slip_part} "
            f"-> {d.get('governing_limit_state')} ({d.get('governing_util', 0.0):.4f})"
        )

        # Show input values for this bolt
        calc = d.get("calc", {})
        if calc:
            lines.append("    Inputs:")
            
            if standard == "aisc":
                # Show key varying inputs
                lines.append(f"      Vu={calc.get('Vu_kN', 0.0):.3f} kN, Tu={calc.get('Tu_kN', 0.0):.3f} kN")
                lines.append(f"      f_rv={calc.get('f_rv', 0.0):.1f} MPa → Fnt'={calc.get('Fnt_prime', 0.0):.1f} MPa")
                lines.append(f"      lc={calc.get('lc', 0.0):.1f} mm → R_bearing={calc.get('bearing_nom_kN', 0.0):.1f} kN, R_tearout={calc.get('tear_nom_kN', 0.0):.1f} kN")
                
            elif standard == "as4100":
                # Show key varying inputs
                Tu = calc.get('Tu_kN', 0.0)
                Tu_prying = calc.get('Tu_prying_kN', 0.0)
                lines.append(f"      Vu={calc.get('Vu_kN', 0.0):.3f} kN, Tu={Tu:.3f} kN"
                           + (f" (with prying: {Tu_prying:.3f} kN)" if abs(Tu_prying - Tu) > 0.001 else ""))
                a_e = calc.get('a_e', 0.0)
                edge_clear = calc.get('edge_clear_center', 0.0)
                lines.append(f"      a_e={a_e:.1f} mm (from edge_clear={edge_clear:.1f} mm)")
                lines.append(f"      Vb={calc.get('Vb_N', 0.0)/1000:.1f} kN, Vp={calc.get('Vp_N', 0.0)/1000:.1f} kN")

    return "\n".join(lines)


def _make_case(*, grade: str, name: str) -> BoltCase:
    # Geometry (same for all cases, only grade changes for check standard defaults)
    layout = BoltLayout.from_pattern(
        rows=3,
        cols=2,
        spacing_y=75.0,
        spacing_z=60.0,
        offset_y=_BOLT_OFFSET_Y,
        offset_z=_BOLT_OFFSET_Z,
    )
    bolt = BoltParams(diameter=20.0, grade=grade)

    plate = Plate.from_dimensions(
        width=_PLATE_WIDTH_Z,
        height=_PLATE_HEIGHT_Y,
        center=_PLATE_CENTER,
        thickness=12.0,
        fu=450.0,
        fy=350.0,
    )

    connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)

    load = Load(
        Fx=30_000.0,
        Fy=-120_000.0,
        Fz=45_000.0,
        My=6_000_000.0,
        Mz=-4_000_000.0,
        # Apply the load at a point ON the plate (x is out-of-plane; y/z lie on the plate rectangle).
        # Plate bounds are y∈[-width/2,width/2], z∈[-height/2,height/2] (centered at (0,0)) for this example.
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

    # --- Full comprehensive checks ---
    _write_text(
        out_dir / "06_full_check_aisc.txt",
        _format_full_check("AISC 360-22 FULL CHECK REPORT", case_aisc, result_aisc, check_aisc)
    )
    _write_text(
        out_dir / "07_full_check_as4100.txt",
        _format_full_check("AS 4100 FULL CHECK REPORT", case_as4100, result_as4100, check_as4100)
    )

    print("")
    print("Done. Outputs written to:")
    print(f"  {out_dir}")


if __name__ == "__main__":
    run()
