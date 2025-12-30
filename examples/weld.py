"""End-to-end weld example: setup, analyze, plot, and check (AISC 360-22).

Outputs (created under `gallery/weld/`):
- 01_setup.txt
- 02_plot.txt
- 03_analysis_elastic.txt
- 04_analysis_icr.txt
- 05_check_aisc.txt
- 06_full_check_aisc.txt
- weld_plot_elastic.svg
- weld_plot_icr.svg
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for scripts/CI

from connecty import Load, WeldBaseMetal, WeldConnection, WeldParams


@dataclass(frozen=True)
class WeldCase:
    name: str
    connection: WeldConnection
    load: Load
    theta_deg: float | None = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _out_dir() -> Path:
    out_dir = _project_root() / "gallery" / "weld"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(f"Saved: {path}")


def _format_setup(case: WeldCase, dxf_path: Path) -> str:
    conn = case.connection
    weld = conn.weld

    lines: list[str] = []
    lines.append("WELD EXAMPLE - SETUP")
    lines.append("=" * 80)
    lines.append(f"Case: {case.name}")
    lines.append("")
    lines.append("Units: choose any consistent system (this example uses mm, N, N*mm, MPa)")
    lines.append("")
    lines.append(f"DXF geometry: {dxf_path}")
    lines.append("")
    lines.append("Weld definition:")
    lines.append(f"  type={weld.parameters.type}")
    lines.append(f"  leg w={weld.parameters.leg:.3f} mm")
    lines.append(f"  throat t_e={weld.parameters.throat:.3f} mm")
    lines.append("")
    lines.append("Weld group geometry:")
    lines.append(f"  L_weld={weld.L:.3f} mm")
    lines.append(f"  A_we={weld.A:.3f} mm^2 (throat * length)")
    lines.append(f"  centroid=(y={weld.Cy:.3f}, z={weld.Cz:.3f}) mm")
    lines.append(f"  Ip={weld.Ip:.3f} mm^4")
    lines.append("")
    lines.append("Base metal (conservative, for fusion-face check):")
    lines.append(f"  t={conn.base_metal.t:.3f} mm, Fy={conn.base_metal.fy:.1f} MPa, Fu={conn.base_metal.fu:.1f} MPa")
    lines.append(f"  is_double_fillet={conn.is_double_fillet}")
    lines.append(f"  is_rect_hss_end_connection={conn.is_rect_hss_end_connection}")
    lines.append("")
    lines.append("Applied load (forces + moments at a location):")
    load = case.load
    lines.append(
        f"  Fx={load.Fx:.2f} N, Fy={load.Fy:.2f} N, Fz={load.Fz:.2f} N, "
        f"Mx={load.Mx:.2f} N·mm, My={load.My:.2f} N·mm, Mz={load.Mz:.2f} N·mm, "
        f"location={load.location}"
    )
    if case.theta_deg is not None:
        lines.append(f"  theta_deg (for k_ds) = {case.theta_deg:.1f}°")
    else:
        lines.append("  theta_deg (for k_ds) = None (auto-computed at governing location)")
    return "\n".join(lines)


def _format_analysis(title: str, result) -> str:
    lines: list[str] = []
    lines.append(title)
    lines.append("=" * 80)
    lines.append(f"method={result.method}")
    if result.analysis.icr_point is not None:
        y_icr, z_icr = result.analysis.icr_point
        lines.append(f"icr_point=(y={y_icr:.3f}, z={z_icr:.3f})")
    lines.append(f"max_stress={result.max_stress:.3f} MPa")
    lines.append(f"mean_stress={result.mean_stress:.3f} MPa")
    return "\n".join(lines)


def _render_equations_once() -> list[str]:
    lines: list[str] = []
    lines.append("Capacity Equations (AISC 360-22, fillet welds):")
    lines.append("  Weld metal:   φRn_w = 0.75 * 0.60 * FEXX * Awe * kds")
    lines.append("  Base metal:   φRn_b = min(1.00*0.60*Fy*ABM, 0.75*0.60*Fu*ABM)")
    lines.append("               where ABM = nf * t * Lweld")
    lines.append("  Detailing:    w <= w_max(t) (metric max fillet size rule)")
    return lines


def _format_check(title: str, result, check) -> str:
    lines: list[str] = []
    lines.append(title)
    lines.append("=" * 80)
    lines.append(f"method={check.method}")
    lines.append(f"governing_limit_state={check.governing_limit_state}")
    lines.append(f"governing_utilization={check.governing_utilization:.4f}")
    lines.append("")
    for eq in _render_equations_once():
        lines.append(eq)

    lines.append("")
    if not check.details:
        lines.append("No check details.")
        return "\n".join(lines)

    d = check.details[0]
    lines.append("Weld group:")
    lines.append(f"  type={d.weld_type}, w={d.leg:.3f} mm, t_e={d.throat:.3f} mm, L_weld={d.L_weld:.3f} mm")
    lines.append(f"  stress_demand={d.stress_demand:.3f} MPa")
    lines.append(f"  F_EXX={d.F_EXX:.1f} MPa, k_ds={d.k_ds:.3f}, theta_deg={d.theta_deg}")
    lines.append("")
    lines.append("Utilizations:")
    lines.append(f"  weld_metal: {d.weld_util:.4f}")
    if d.base_util is not None:
        lines.append(f"  base_metal_fusion_face: {d.base_util:.4f}")
    if d.detailing_max_util is not None:
        lines.append(f"  detailing_max_fillet: {d.detailing_max_util:.4f} (w_max={d.detailing_w_max})")
    lines.append("")
    lines.append(f"Governing: {d.governing_limit_state} ({d.governing_util:.4f})")
    return "\n".join(lines)


def _format_full_check(title: str, case: WeldCase, elastic_result, icr_result, check) -> str:
    conn = case.connection
    weld = conn.weld

    lines: list[str] = []
    lines.append(title)
    lines.append("=" * 80)
    lines.append("")

    lines.append("1. WELD GROUP CONFIGURATION")
    lines.append("-" * 80)
    lines.append(f"DXF: {(_project_root() / 'examples' / 'base1.dxf')}")
    lines.append(f"Weld type: {weld.parameters.type}")
    lines.append(f"Weld size: w={weld.parameters.leg:.3f} mm, throat={weld.parameters.throat:.3f} mm")
    lines.append(f"Total weld length L_weld={weld.L:.3f} mm")
    lines.append(f"Effective area Awe={weld.A:.3f} mm^2")
    lines.append(f"Centroid: (y={weld.Cy:.3f}, z={weld.Cz:.3f}) mm")
    lines.append("")

    lines.append("2. MATERIAL / DETAILING INPUTS (CONSERVATIVE)")
    lines.append("-" * 80)
    lines.append(f"Base metal: t={conn.base_metal.t:.3f} mm, Fy={conn.base_metal.fy:.1f} MPa, Fu={conn.base_metal.fu:.1f} MPa")
    lines.append(f"is_double_fillet={conn.is_double_fillet}")
    lines.append(f"is_rect_hss_end_connection={conn.is_rect_hss_end_connection}")
    if case.theta_deg is not None:
        lines.append(f"theta_deg={case.theta_deg:.1f}° (k_ds enabled)")
    else:
        lines.append("theta_deg=None (auto-computed at governing location)")
    lines.append("")

    lines.append("3. LOAD INFORMATION")
    lines.append("-" * 80)
    load = case.load
    lines.append(f"Forces:  Fx={load.Fx:.2f} N, Fy={load.Fy:.2f} N, Fz={load.Fz:.2f} N")
    lines.append(f"Moments: Mx={load.Mx:.2f} N·mm, My={load.My:.2f} N·mm, Mz={load.Mz:.2f} N·mm")
    lines.append(f"Location: {load.location}")
    lines.append("")

    lines.append("4. ANALYSIS RESULTS")
    lines.append("-" * 80)
    lines.append(f"Elastic max stress: {elastic_result.max_stress:.3f} MPa")
    if icr_result.analysis.icr_point is not None:
        y_icr, z_icr = icr_result.analysis.icr_point
        lines.append(f"ICR max stress:     {icr_result.max_stress:.3f} MPa (icr_point=(y={y_icr:.3f}, z={z_icr:.3f}))")
    else:
        lines.append(f"ICR max stress:     {icr_result.max_stress:.3f} MPa")
    lines.append("")

    lines.append("5. CHECK RESULTS (AISC 360-22)")
    lines.append("-" * 80)
    lines.append(f"Governing limit state: {check.governing_limit_state}")
    lines.append(f"Governing utilization: {check.governing_utilization:.4f}")
    if check.details:
        d = check.details[0]
        lines.append("")
        lines.append("Per-limit-state utilization:")
        lines.append(f"  weld_metal: {d.weld_util:.4f}")
        if d.base_util is not None:
            lines.append(f"  base_metal_fusion_face: {d.base_util:.4f}")
        if d.detailing_max_util is not None:
            lines.append(f"  detailing_max_fillet: {d.detailing_max_util:.4f}")
    lines.append("")
    lines.append("Equations:")
    for eq in _render_equations_once():
        lines.append(f"  {eq}")

    return "\n".join(lines)


def _make_case(name: str) -> WeldCase:
    root = _project_root()
    dxf_path = root / "examples" / "base1.dxf"

    base_metal = WeldBaseMetal(t=10.0, fy=350.0, fu=450.0)
    params = WeldParams(type="fillet", leg=6.0)
    connection = WeldConnection.from_dxf(
        dxf_path,
        parameters=params,
        base_metal=base_metal,
        is_double_fillet=False,
        is_rect_hss_end_connection=False,
    )

    # In-plane shear applied at an eccentric location to generate torsion about x (Mx via Load.at()).
    load = Load(
        Fy=-120_000.0,
        Fz=45_000.0,
        location=(0.0, 0.0, 0.0),
    )

    # Optional angle between force direction and weld axis for k_ds.
    theta_deg = None

    return WeldCase(name=name, connection=connection, load=load, theta_deg=theta_deg)


def run() -> None:
    out_dir = _out_dir()
    case = _make_case(name="AISC_360_22_FILLET_DXF")

    root = _project_root()
    dxf_path = root / "examples" / "base1.dxf"

    # --- Setup docs ---
    _write_text(out_dir / "01_setup.txt", _format_setup(case, dxf_path))

    # --- Analysis ---
    result_elastic = case.connection.analyze(case.load, method="elastic")
    result_icr = case.connection.analyze(case.load, method="icr")

    _write_text(out_dir / "03_analysis_elastic.txt", _format_analysis("WELD ANALYSIS (ELASTIC)", result_elastic))
    _write_text(out_dir / "04_analysis_icr.txt", _format_analysis("WELD ANALYSIS (ICR)", result_icr))

    # --- Plot ---
    plot_path_elastic = out_dir / "weld_plot_elastic.svg"
    result_elastic.plot(
        section=False,
        show=False,
        save_path=str(plot_path_elastic),
        legend=True,
        info=True,
    )

    plot_path_icr = out_dir / "weld_plot_icr.svg"
    result_icr.plot(
        section=False,
        show=False,
        save_path=str(plot_path_icr),
        legend=True,
        info=True,
    )

    plot_path_util_elastic = out_dir / "weld_util_elastic.svg"
    result_elastic.plot_utilization(
        section=False,
        show=False,
        save_path=str(plot_path_util_elastic),
        legend=True,
        info=True,
    )

    plot_path_util_icr = out_dir / "weld_util_icr.svg"
    result_icr.plot_utilization(
        section=False,
        show=False,
        save_path=str(plot_path_util_icr),
        legend=True,
        info=True,
    )

    _write_text(
        out_dir / "02_plot.txt",
        "\n".join(
            [
                "WELD PLOT",
                "=" * 80,
                f"Saved image (elastic): {plot_path_elastic}",
                f"Saved image (icr):     {plot_path_icr}",
                f"Saved image (elastic util): {plot_path_util_elastic}",
                f"Saved image (icr util):     {plot_path_util_icr}",
                "Plots show weld path colored by stress magnitude, with applied load arrow.",
            ]
        ),
    )

    # --- Checks (AISC) ---
    check_aisc = result_icr.check(
        standard="aisc",
        conservative_k_ds=False,  # Enable auto-angle computation (default)
    )
    _write_text(out_dir / "05_check_aisc.txt", _format_check("AISC 360-22 CHECK (fillet)", result_icr, check_aisc))

    # --- Full comprehensive report ---
    _write_text(
        out_dir / "06_full_check_aisc.txt",
        _format_full_check("AISC 360-22 FULL WELD CHECK REPORT", case, result_elastic, result_icr, check_aisc),
    )

    print("")
    print("Done. Outputs written to:")
    print(f"  {out_dir}")


if __name__ == "__main__":
    run()


