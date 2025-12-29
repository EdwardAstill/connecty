# Connecty

Weld and bolt connection analysis for structural engineering. Calculates and visualizes stress/force distribution and performs AISC-style checks.

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
from connecty import Load, WeldBaseMetal, WeldConnection, WeldParams

# 1) Create a weld connection from DXF geometry
connection = WeldConnection.from_dxf(
    "examples/base1.dxf",
    parameters=WeldParams(type="fillet", leg=6.0),
    base_metal=WeldBaseMetal(t=10.0, fy=350.0, fu=450.0),
)

# 2) Define applied load (forces + moments at a location)
load = Load(Fy=-120_000.0, Fz=45_000.0, location=(0.0, 0.0, 0.0))

# 3) Analyze (elastic or icr for fillet welds)
result = connection.analyze(load, method="icr")
print(f"Max stress: {result.max_stress:.2f} MPa")

# 4) Check (AISC 360-22, fillet welds)
check = result.check(standard="aisc")
print(f"Governing utilisation: {check.governing_utilization:.3f} ({check.governing_limit_state})")

# 5) Plot (saved as .svg)
result.plot(show=False, save_path="weld_stress.svg")
```

## Examples & Gallery

Check the `examples/` directory for more usage scenarios. You can generate the example gallery by running:

```bash
uv run python examples/generate_gallery.py
```

The generated images will be saved to the `gallery/` directory.

## API Reference

### WeldParams

```python
WeldParams(
    type: "fillet" | "pjp" | "cjp" | "plug" | "slot",
    leg: float | None = None,     # Fillet weld leg size (mm)
    throat: float | None = None,  # Effective throat (mm)
    area: float | None = None,    # Plug/slot effective area (mm^2)
)
```

### Load

```python
Load(
    Fx: float = 0,  # Axial force
    Fy: float = 0,  # Vertical shear
    Fz: float = 0,  # Horizontal shear
    Mx: float = 0,  # Torsion
    My: float = 0,  # Bending about y
    Mz: float = 0,  # Bending about z
    location: tuple = (0, 0, 0)  # Point of application (x, y, z)
)
```

### WeldedSection

```python
from sectiony.library import rhs
from connecty import Load, WeldParams, WeldedSection

section = rhs(b=100, h=200, t=10, r=15)
welded = WeldedSection(section=section)

# Add welds
params = WeldParams(type="fillet", leg=6.0)
welded.weld_all_segments(params)

# Optional: inspect available segments
welded.get_segment_info()

# Calculate stress
load = Load(Fy=-50_000.0, Fz=10_000.0, Mx=1_000_000.0, location=(0.0, 0.0, 0.0))
result = welded.calculate_weld_stress(load, method="elastic")
print(result.max_stress)

# Plot
welded.plot_weld_stress(load, cmap="coolwarm", save_path="output.svg")
```

## Stress Calculation Method

The elastic method calculates stress at each point along the weld:

1. **Direct stress** - Uniform distribution: `f = F / A_weld`
2. **Torsional stress** - Varies with distance from centroid: `f = M Ã— r / Ip`
3. **Bending stress** - Linear distribution: `f = M Ã— d / I`

The resultant stress is the vector sum of all components.

## License

MIT


