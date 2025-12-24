"""
Bolt check examples (bearing vs slip-critical) writing text outputs.

Runs AISC 360-22 checks for A325 bolts in bearing and slip-critical
configurations and saves summaries to gallery/bolt check.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from connecty import BoltConnection, BoltGroup, ConnectionLoad, ConnectionResult, Plate


@dataclass(frozen=True)
class DemoBoltCase:
    bolt_group: BoltGroup
    plate: Plate
    connection: BoltConnection
    load: ConnectionLoad


def make_demo_case(*, grade: str = "A325") -> DemoBoltCase:
    """Create the shared 3x2 rectangular bolt connection used by examples."""

    bolt_group = BoltGroup.from_pattern(
        rows=3,
        cols=2,
        spacing_y=75.0,
        spacing_z=60.0,
        diameter=20.0,
        grade=grade,
        origin=(0.0, 0.0),
    )

    # With the pattern centered at (0, 0):
    # y = [-75, 0, +75], z = [-30, +30]
    plate = Plate(
        corner_a=(-125.0, -80.0),
        corner_b=(125.0, 80.0),
        thickness=12.0,
        fu=450.0,
        fy=350.0,
    )

    connection = BoltConnection(bolt_group=bolt_group, plate=plate)

    # Load chosen to exercise:
    # - in-plane shear + torsion (via eccentricity)
    # - out-of-plane tension + bending (My/Mz)
    load = ConnectionLoad(
        Fx=30_000.0,   # N
        Fy=-120_000.0, # N
        Fz=45_000.0,   # N
        My=6_000_000.0,  # N*mm
        Mz=-4_000_000.0, # N*mm
        location=(0.0, 0.0, 150.0),
    )

    return DemoBoltCase(
        bolt_group=bolt_group,
        plate=plate,
        connection=connection,
        load=load,
    )


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
