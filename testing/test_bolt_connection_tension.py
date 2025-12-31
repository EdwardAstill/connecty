import pytest

from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate


def test_tension_conservative_vs_accurate_changes_na_and_forces():
    # 2 rows (y), 3 cols (z)
    layout = BoltLayout.from_pattern(rows=2, cols=3, spacing_y=100.0, spacing_z=50.0)
    bolt = BoltParams(diameter=20.0, grade="A325")

    plate = Plate(corner_a=(-60.0, -60.0), corner_b=(60.0, 60.0), thickness=10.0, fu=450.0, fy=350.0)  # y,z
    conn = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)

    # Apply pure My (causes gradient across z)
    f = Load(My=1.0e6, location=(0.0, 0.0, 0.0))

    r_cons = conn.analyze(f, shear_method="elastic", tension_method="conservative")
    r_acc = conn.analyze(f, shear_method="elastic", tension_method="accurate")

    fx_cons = [bf.Fx for bf in r_cons.to_bolt_forces()]
    fx_acc = [bf.Fx for bf in r_acc.to_bolt_forces()]

    # Must produce some tension on at least one bolt
    assert max(fx_cons) > 0
    assert max(fx_acc) > 0

    # Different NA assumption should generally change tension distribution
    assert fx_cons != fx_acc


def test_tension_sums_my_and_mz_contributions():
    """Test biaxial bending with proper compression interaction.
    
    Note: With the corrected implementation, compression from one axis can cancel
    tension from another. So Fx(My+Mz) != Fx(My) + Fx(Mz) in general, because
    negative contributions are now properly handled before the final zeroing.
    """
    layout = BoltLayout.from_pattern(rows=2, cols=2, spacing_y=100.0, spacing_z=100.0)
    bolt = BoltParams(diameter=20.0, grade="A325")
    plate = Plate(corner_a=(-60.0, -60.0), corner_b=(60.0, 60.0), thickness=10.0, fu=450.0, fy=350.0)
    conn = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)

    f_my = Load(My=1.0e6, location=(0.0, 0.0, 0.0))
    f_mz = Load(Mz=1.0e6, location=(0.0, 0.0, 0.0))
    f_both = Load(My=1.0e6, Mz=1.0e6, location=(0.0, 0.0, 0.0))

    r_my = conn.analyze(f_my, shear_method="elastic", tension_method="conservative")
    r_mz = conn.analyze(f_mz, shear_method="elastic", tension_method="conservative")
    r_both = conn.analyze(f_both, shear_method="elastic", tension_method="conservative")

    # Check that biaxial bending properly accounts for compression cancellation
    for i in range(layout.n):
        both = r_both.to_bolt_forces()[i].Fx
        my = r_my.to_bolt_forces()[i].Fx
        mz = r_mz.to_bolt_forces()[i].Fx
        
        # With proper compression handling:
        # - If both My and Mz create tension (both > 0 before zeroing), then both ≈ my + mz
        # - If one creates compression (< 0 before zeroing), it can cancel the other
        # - So both <= my + mz (with equality when no cancellation occurs)
        
        assert both >= 0.0, "Tension should never be negative"
        assert both <= my + mz + 1e-6, "Combined should not exceed simple sum"
        
        # For this specific geometry with conservative method:
        # Bolt positions: [(-50, -50), (-50, +50), (+50, -50), (+50, +50)]
        # Both moments create same pattern, so we expect some cancellation for opposing quadrants


def test_shear_planes_reduce_shear_stress():
    layout = BoltLayout.from_pattern(rows=1, cols=1, spacing_y=100.0, spacing_z=100.0)
    bolt = BoltParams(diameter=20.0, grade="A325")
    plate = Plate(corner_a=(-10.0, -10.0), corner_b=(10.0, 10.0), thickness=10.0, fu=450.0, fy=350.0)

    f = Load(Fy=10000.0, location=(0.0, 0.0, 0.0))

    conn_1 = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
    conn_2 = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=2)

    r1 = conn_1.analyze(f, shear_method="elastic", tension_method="conservative")
    r2 = conn_2.analyze(f, shear_method="elastic", tension_method="conservative")

    b1 = r1.to_bolt_forces()[0]
    b2 = r2.to_bolt_forces()[0]
    assert b1.shear_stress == pytest.approx(b2.shear_stress * 2.0)
