from __future__ import annotations

from pathlib import Path

from connecty import Load, WeldBaseMetal, WeldConnection, WeldParams


def test_weld_connection_from_dxf_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    dxf_path = root / "examples" / "base1.dxf"

    conn = WeldConnection.from_dxf(
        dxf_path,
        parameters=WeldParams(type="fillet", leg=6.0),
        base_metal=WeldBaseMetal(t=10.0, fy=350.0, fu=450.0),
        is_double_fillet=False,
        is_rect_hss_end_connection=False,
    )

    result = conn.analyze(Load(Fy=-10_000.0, Fz=5_000.0, location=(0.0, 0.0, 0.0)), method="elastic")
    check = result.check(standard="aisc")

    # Basic sanity: should produce a finite, non-negative governing utilization.
    assert check.governing_utilization >= 0.0


