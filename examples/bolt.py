#Test the bolt check
from connecty import BoltConnection, BoltGroup, Plate, Load, BoltParams

bg = BoltGroup.create(layout=[(0, 0), (0, 100), (100, 0), (100, 100)], params=BoltParams(diameter=12, grade="A325"))
plate = Plate.from_dimensions(width=100, height=100, thickness=10, fu=450, fy=350)
conn = BoltConnection(bolt_group=bg, plate=plate, n_shear_planes=1)
load = Load(Fx=30_000, Fy=-120_000, Fz=45_000, My=6_000_000, Mz=-4_000_000, location=(0, 50, 40))
res = conn.analyze(load, shear_method="elastic", tension_method="accurate")
check_dict = res.check(standard="aisc", connection_type="bearing")
print(check_dict)
