"""
Common loading conditions for examples.
"""
from connecty import Load


def get_vertical_shear(mag_kn: float = 100) -> Load:
    return Load(
        Fy=-mag_kn * 1000,
        location=(0, 0, 0)
    )


def get_eccentric_load(mag_kn: float = 150, ecc_z: float = 100, ecc_y: float = 0) -> Load:
    return Load(
        Fy=-mag_kn * 1000,
        location=(0, ecc_y, ecc_z)
    )


def get_combined_load() -> Load:
    return Load(
        Fy=-50000,
        Fz=20000,
        Mx=5e6,
        My=10e6,
        Mz=2e6,
        location=(0, 0, 0)
    )
