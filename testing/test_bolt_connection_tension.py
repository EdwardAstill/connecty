import pytest

from connecty import BoltGroup, Force, Plate
from connecty.bolt import BoltConnection


def test_tension_conservative_vs_accurate_changes_na_and_forces():
    # 2 rows (y), 3 cols (z)
    bg = BoltGroup.from_pattern(rows=2, cols=3, spacing_y=100.0, spacing_z=50.0, diameter=20.0)

    plate = Plate(corner_a=(-60.0, -60.0), corner_b=(60.0, 60.0), thickness=10.0, fu=450.0, fy=350.0)  # y,z
    conn = BoltConnection(bolt_group=bg, plate=plate, n_shear_planes=1)

    # Apply pure My (causes gradient across z)
    f = Force(My=1.0e6, location=(0.0, 0.0, 0.0))

    r_cons = conn.analyze(f, shear_method="elastic", tension_method="conservative")
    r_acc = conn.analyze(f, shear_method="elastic", tension_method="accurate")

    fx_cons = [bf.Fx for bf in r_cons.to_bolt_results()]
    fx_acc = [bf.Fx for bf in r_acc.to_bolt_results()]

    # Must produce some tension on at least one bolt
    assert max(fx_cons) > 0
    assert max(fx_acc) > 0

    # Different NA assumption should generally change tension distribution
    assert fx_cons != fx_acc


def test_tension_sums_my_and_mz_contributions():
    bg = BoltGroup.from_pattern(rows=2, cols=2, spacing_y=100.0, spacing_z=100.0, diameter=20.0)
    plate = Plate(corner_a=(-60.0, -60.0), corner_b=(60.0, 60.0), thickness=10.0, fu=450.0, fy=350.0)
    conn = BoltConnection(bolt_group=bg, plate=plate, n_shear_planes=1)

    f_my = Force(My=1.0e6, location=(0.0, 0.0, 0.0))
    f_mz = Force(Mz=1.0e6, location=(0.0, 0.0, 0.0))
    f_both = Force(My=1.0e6, Mz=1.0e6, location=(0.0, 0.0, 0.0))

    r_my = conn.analyze(f_my, shear_method="elastic", tension_method="conservative")
    r_mz = conn.analyze(f_mz, shear_method="elastic", tension_method="conservative")
    r_both = conn.analyze(f_both, shear_method="elastic", tension_method="conservative")

    for i in range(bg.n):
        both = r_both.to_bolt_results()[i].Fx
        my = r_my.to_bolt_results()[i].Fx
        mz = r_mz.to_bolt_results()[i].Fx
        assert pytest.approx(both, rel=1e-9, abs=1e-9) == (
            my + mz
        )


def test_shear_planes_reduce_shear_stress():
    bg = BoltGroup.from_pattern(rows=1, cols=1, spacing_y=100.0, spacing_z=100.0, diameter=20.0)
    plate = Plate(corner_a=(-10.0, -10.0), corner_b=(10.0, 10.0), thickness=10.0, fu=450.0, fy=350.0)

    f = Force(Fy=10000.0, location=(0.0, 0.0, 0.0))

    conn_1 = BoltConnection(bolt_group=bg, plate=plate, n_shear_planes=1)
    conn_2 = BoltConnection(bolt_group=bg, plate=plate, n_shear_planes=2)

    r1 = conn_1.analyze(f, shear_method="elastic", tension_method="conservative")
    r2 = conn_2.analyze(f, shear_method="elastic", tension_method="conservative")

    b1 = r1.to_bolt_results()[0]
    b2 = r2.to_bolt_results()[0]
    assert b1.shear_stress == pytest.approx(b2.shear_stress * 2.0)
