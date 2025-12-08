"""
Common loading conditions for examples.
"""
from connecty import Load

# 1. Simple Vertical Shear (Centroidal)
def get_vertical_shear(mag_kn: float = 100) -> Load:
    return Load(
        Fy=-mag_kn * 1000,
        location=(0, 0, 0)
    )

# 2. Eccentric Vertical Load (Generates Torsion/Bending)
def get_eccentric_load(mag_kn: float = 150, ecc_z: float = 100, ecc_y: float = 0) -> Load:
    return Load(
        Fy=-mag_kn * 1000,
        location=(0, ecc_y, ecc_z)
    )

# 3. Combined Multi-Axis Load
def get_combined_load() -> Load:
    return Load(
        Fy=-50000,      # 50kN vertical shear
        Fz=20000,       # 20kN lateral shear
        Mx=5e6,         # 5kNm torsion
        My=10e6,        # 10kNm bending (y-axis)
        Mz=2e6,         # 2kNm bending (z-axis)
        location=(0, 0, 0)
    )

