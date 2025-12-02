"""
Example 3: I-beam with selective welding

Demonstrates welding only specific segments (e.g., flanges only).
"""
from sectiony.library import i
from weldy import WeldedSection, WeldParameters, Force

# Create I-beam: 400mm deep, 200mm wide, 20mm flanges, 10mm web, 15mm root radius
section = i(d=400, b=200, tf=20, tw=10, r=15)

welded = WeldedSection(section=section)

# Check available segments
print("Available segments:")
for info in welded.get_segment_info():
    print(f"  Segment {info['index']}: {info['type']}")

# Weld only top and bottom flanges (typically segments 0-3 and 8-11 for I-beam)
# Top flange: segments 0, 1, 2, 3
# Bottom flange: segments 8, 9, 10, 11
weld_params = WeldParameters(
    weld_type="fillet",
    throat_thickness=6.0,
    leg_size=8.5
)

# Weld top flange
welded.add_welds([0, 1, 2, 3], weld_params)
# Weld bottom flange  
welded.add_welds([8, 9, 10, 11], weld_params)

# Calculate properties
welded.calculate_properties()

# Apply bending moment
force = Force(
    My=5e6,  # 5kNm bending moment
    location=(0, 0)
)

from pathlib import Path

# ... (imports)

# ... (code)

gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example3_i_beam.svg"

welded.plot_weld_stress(
    force,
    cmap="RdBu_r",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"Saved: {save_path}")

