# Connecty

Weld stress analysis package for structural engineering. Calculates and visualizes stress distribution along welded connections using the elastic method.

## Features

- **Elastic stress analysis** - Calculates direct, torsional, and bending stress components
- **Multiple weld types** - Support for fillet and butt welds
- **Visual output** - Color-coded stress plots along weld lines
- **Integration with sectiony** - Works with any section from the sectiony package

## Documentation

For comprehensive documentation, including detailed weld and bolt analysis guides, see the [User Guide](documentation/user%20guide.md).

## Installation

```bash
uv add connecty
```

## Quick Start

```python
from sectiony.library import rhs
from connecty import WeldedSection, WeldParameters, Force

# Create a section
section = rhs(b=100, h=200, t=10, r=15)

# Create welded section
welded = WeldedSection(section=section)

# Define weld parameters (6mm fillet weld)
params = WeldParameters(
    weld_type="fillet",
    throat_thickness=4.2,
    leg_size=6.0
)

# Add welds to all outer edges
welded.weld_all_segments(params)

# Define applied force
force = Force(
    Fy=-50000,      # 50kN downward
    Fz=10000,       # 10kN horizontal  
    Mx=1e6,         # 1kNm torsion
    location=(100, 30)  # Point of application
)

# Calculate and plot stress
welded.plot_weld_stress(force, save_path="stress.svg")
```

## Examples & Gallery

Check the `examples/` directory for more usage scenarios. You can generate the example gallery by running:

```bash
uv run python examples/generate_gallery.py
```

The generated images will be saved to the `gallery/` directory.

## API Reference

### WeldParameters

```python
WeldParameters(
    weld_type: "fillet" | "butt",
    throat_thickness: float,  # Effective throat (mm)
    leg_size: float = None,   # For fillet welds (mm)
    strength: float = None    # Allowable stress (MPa)
)
```

### Force

```python
Force(
    Fx: float = 0,  # Axial force
    Fy: float = 0,  # Vertical shear
    Fz: float = 0,  # Horizontal shear
    Mx: float = 0,  # Torsion
    My: float = 0,  # Bending about y
    Mz: float = 0,  # Bending about z
    location: tuple = (0, 0)  # Point of application (y, z)
)
```

### WeldedSection

```python
welded = WeldedSection(section=section)

# Add welds
welded.add_weld(segment_index, params)
welded.add_welds([0, 1, 2], params)
welded.weld_all_segments(params)

# Get segment info to identify which edges to weld
welded.get_segment_info()

# Calculate stress
result = welded.calculate_weld_stress(force)
print(result.max_stress)
print(result.utilization(allowable=220))

# Plot
welded.plot_weld_stress(force, cmap="coolwarm", save_path="output.svg")
```

## Stress Calculation Method

The elastic method calculates stress at each point along the weld:

1. **Direct stress** - Uniform distribution: `f = F / A_weld`
2. **Torsional stress** - Varies with distance from centroid: `f = M Ã— r / Ip`
3. **Bending stress** - Linear distribution: `f = M Ã— d / I`

The resultant stress is the vector sum of all components.

## License

MIT


