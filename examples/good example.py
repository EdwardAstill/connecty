"""
ICR method for an eccentrically loaded RHS.

Highlights how the ICR method locates the instantaneous center and
delivers additional strength when the load is offset from the weld
centroid in both shear directions.
"""
from pathlib import Path

from sectiony.library import rhs

from connecty import Load, Weld, WeldParams, LoadedWeld

# Build section and weld
section = rhs(b=150, h=75, t=10, r=12)

Fy = -140000
Fz = 45000
location = (0, 20, -55)

weld_type = "fillet"

weld_leg = 8.0

weld_electrode = "E70"

params = WeldParams(
    type=weld_type,
    leg=weld_leg,
    electrode=weld_electrode
)
weld = Weld.from_section(section=section, parameters=params)

weld_throat = weld.parameters.throat


# Define an eccentrically applied shear that introduces torsion
load = Load(
    Fy=-140000,
    Fz=45000,
    location=(0, 20, -55)
)
EMx, _, _ = load.get_moments_about(0, weld.Cy, weld.Cz)

# Analysis will be done when plotting with method="both"

method = {"elastic": True, "icr": True}


print("Weld Properties:")
print(f"  Type: {weld.parameters.type.capitalize()}")
print(f"  Effective Throat: {weld.parameters.throat:.2f} mm")
print(f"  Electrode Strength: {weld.parameters.F_EXX:.0f} MPa")
print(f"  Weld Capacity: {weld.parameters.capacity:.1f} MPa")
print(f"  Centroid: ({weld.Cy:.1f}, {weld.Cz:.1f})")
print()

# Analyze with both methods to compare


print("=" * 60)
print("Good example")
print("=" * 60)
print("Loading:")
print(f"  Vertical shear Fy = {Fy}")
print(f"  Horizontal shear Fz = {Fz}")
print(f"  Location offset: ({location[0]} mm up, {location[1]} mm left)")
if location[0] != 0 or location[1] != 0:
    print(f"  Effective torsion moment: {load.Mx:.0f} N·mm")
print()
if method["icr"]:
    loaded_icr = LoadedWeld(weld, load, method="icr")
    print("ICR METHOD:")
    print(f"  Max stress: {loaded_icr.max:.1f} MPa")
    print(f"  Utilization: {loaded_icr.utilization():.1%}")
    rotation_text = f"{loaded_icr.rotation:.1f} mm" if loaded_icr.rotation is not None else "n/a"
    print(f"  Instantaneous center distance along shear perp: {rotation_text}")
    if loaded_icr.icr_point is not None:
        print(f"  ICR location: ({loaded_icr.icr_point[0]:.1f}, {loaded_icr.icr_point[1]:.1f})")
print()
if method["elastic"]:
    loaded_elastic = LoadedWeld(weld, load, method="elastic")
    print("ELASTIC METHOD:")
    print(f"  Max stress: {loaded_elastic.max:.1f} MPa")
    print(f"  Utilization: {loaded_elastic.utilization():.1%}")
    if method["icr"]:
        print(f"  Capacity gain from ICR: "
            f"{(1 - loaded_icr.utilization() / loaded_elastic.utilization()) * 100:.0f}%")

# Save visualization of the ICR result
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "icr_rhs_eccentric_load.svg"

loaded_both = LoadedWeld(weld, load, method="both")
loaded_both.plot(
    section=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)

print(f"\nSaved: {save_path}")

