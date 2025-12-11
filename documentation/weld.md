# Connecty - Weld Stress Analysis

## Overview

Connecty calculates **stress distribution** along welded connections per AISC 360. It integrates with **sectiony** for section geometry and focuses on force/stress output—design checks are your responsibility.

---

## Analysis Methods

Connecty provides two methods for calculating stress at each point along a weld:

**Elastic Method** (all weld types)
- Conservative, closed-form solution
- Full **3D analysis** (handles $F_x, F_y, F_z, M_x, M_y, M_z$)
- Stress = vector sum of components (direct + moment)
- $f_{resultant} = \sqrt{f_{axial}^2 + f_{shear,y}^2 + f_{shear,z}^2}$
- Output: Stress at each discretized point

**ICR Method** (fillet welds only)
- Iterative Instantaneous Center of Rotation
- Accounts for load angle benefit (directional strength increase)
- **2D analysis only** (in-plane loads $F_y, F_z, M_x$)
- Assumes instantaneous center of rotation lies in the plane of the connection
- Strength increase factor: $(1.0 + 0.50 \sin^{1.5}\theta)$
- More accurate stress distribution for in-plane eccentric loading
- Output: Equivalent stress at each discretized point

---

## Core Classes

### 1. `Weld`

A weld path defined by geometry and weld parameters. The geometry can be provided directly or derived from a section's contour.

```python
from connecty import Weld, WeldParams
from sectiony import Geometry, Contour, Line, Arc
from sectiony.library import rhs

# Option A: Explicit geometry
path = Contour(segments=[
    Line(start=(0, -50), end=(0, 50)),
    Arc(center=(0, 50), radius=10, start_angle=math.pi, end_angle=0)
])
weld = Weld(
    geometry=Geometry(contours=[path]),
    parameters=WeldParams(type="fillet", throat=5.0)
)

# Option B: Derive geometry from section (convenience)
section = rhs(b=100, h=200, t=10, r=15)
weld = Weld.from_section(
    section=section,
    parameters=WeldParams(type="fillet", leg=6.0)
)
# The section is stored for plotting but NOT required for analysis
```

#### Constructor

```python
Weld(geometry: Geometry, parameters: WeldParams)
```

**Required:**
- `geometry`: Weld path as a sectiony `Geometry` (contours need not be closed)
- `parameters`: `WeldParams` (geometry only: type, leg, throat, area)

#### Class Methods

| Method | Description |
|--------|-------------|
| `Weld.from_section(section, parameters, contour_index=0)` | Create weld from section's contour. Stores section for plotting. |

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `geometry` | `Geometry` | Weld path geometry (required) |
| `parameters` | `WeldParams` | Weld geometry configuration |
| `section` | `Section \| None` | Optional, only for plotting context |

#### Properties (calculated automatically)

| Property | Type | Description |
|----------|------|-------------|
| `A` | `float` | Total weld area (throat × length) |
| `L` | `float` | Total weld length |
| `Cy`, `Cz` | `float` | Centroid coordinates |
| `Iy`, `Iz` | `float` | Second moments of area about centroid |
| `Ip` | `float` | Polar moment (Iy + Iz) |

---

### 2. `WeldParams`

Geometry-only configuration. No electrode or capacity properties.

```python
from connecty import WeldParams

@dataclass
class WeldParams:
    type: Literal["fillet", "pjp", "cjp", "plug", "slot"]
    
    # Geometry (provide what's relevant for weld type)
    leg: float | None = None         # Fillet leg size (w)
    throat: float | None = None      # Effective throat (a or E)
    area: float | None = None        # Plug/slot: hole or slot area
```

**Notes:**
- For fillet welds, if only `leg` is provided, `throat` is calculated automatically: $a = w \times 0.707$
- For PJP welds, provide `throat` (effective throat per AISC Table J2.1)
- For plug/slot welds, provide `area` (hole or slot area in mm²)

---

### 3. `Load` (or `Force`)

Load definition with 6 components and application location.

```python
from connecty import Load

# Direct components
load = Load(Fx=0, Fy=-100e3, Fz=0, Mx=0, My=0, Mz=0, location=(0, 50))
```

#### Attributes

| Attribute | Description | Sign Convention |
|-----------|-------------|-----------------|
| `Fx` | Axial force (out-of-plane) | + = tension |
| `Fy` | Vertical shear (in-plane) | + = up |
| `Fz` | Horizontal shear (in-plane) | + = right |
| `Mx` | Torsion about x-axis | + = CCW from +x |
| `My` | Bending about y-axis | + = tension on +z |
| `Mz` | Bending about z-axis | + = tension on +y |
| `location` | Application point `(y, z)` | — |

**Note:** Forces applied away from the weld centroid automatically generate additional moments due to eccentricity.

---

## Stress Calculation

### Basic Usage

```python
from connecty import LoadedWeld

# Create LoadedWeld (calculates stress automatically)
loaded = LoadedWeld(weld, load, method="elastic", discretization=200)

# Access results
print(f"Max stress: {loaded.max:.1f} MPa")
print(f"Mean stress: {loaded.mean:.1f} MPa")
```

### Available Methods

| Weld Type | `method=` | Description |
|-----------|-----------|-------------|
| **Fillet** | `"elastic"` | Conservative vector sum (default) |
| **Fillet** | `"icr"` | ICR method with angle benefit |
| **PJP** | `"elastic"` | Vector analysis (only option) |
| **CJP** | `"elastic"` | Vector analysis (only option) |
| **Plug/Slot** | `"elastic"` | Shear-only analysis (only option) |

### Elastic Method Details

Calculates stress at each discretized point along the weld:

1. **Direct stresses** (uniform):
   - $f_{direct,y} = F_y / A_w$
   - $f_{direct,z} = F_z / A_w$
   - $f_{axial} = F_x / A_w$

2. **Moment stresses** (linear with distance from centroid):
   - In-plane torsion: $f_{moment} = M_x \cdot r / I_p$ (perpendicular to radius)
   - Out-of-plane bending: $f_{bending} = M_y \cdot z / I_y + M_z \cdot y / I_z$

3. **Resultant**:
   - $f_{resultant} = \sqrt{f_{axial,total}^2 + f_{shear,y}^2 + f_{shear,z}^2}$

### ICR Method Details (Fillet Welds)

The Instantaneous Center of Rotation method:

1. Iterates to find the rotation center that satisfies equilibrium
2. Applies directional strength increase: $(1.0 + 0.50 \sin^{1.5}\theta)$
3. Where $\theta$ = angle between resultant force and weld longitudinal axis
4. More accurate for eccentrically loaded connections

**Important:** ICR is a **2D analysis**. It considers only in-plane loads ($F_y, F_z$) and torsion ($M_x$). Out-of-plane loads ($F_x, M_y, M_z$) are **ignored** by the ICR solver. For combined 3D loading, use the **Elastic Method**.

```python
# ICR method for fillet welds
loaded = LoadedWeld(weld, load, method="icr")

# Access ICR-specific results
print(f"ICR location: {loaded.icr_point}")
print(f"Rotation angle: {loaded.rotation}")
```

---

## Result Access

`LoadedWeld` provides stress data:

```python
loaded = LoadedWeld(weld, load, method="elastic")

# Properties
loaded.max              # Maximum resultant stress (MPa)
loaded.min              # Minimum resultant stress (MPa)
loaded.mean             # Average stress (MPa)
loaded.range            # Stress range (max - min) (MPa)
loaded.max_point        # PointStress object at max location
loaded.point_stresses   # List of all PointStress objects
loaded.method           # "elastic" or "icr"

# ICR-specific
loaded.icr_point        # (y, z) location of instantaneous center
loaded.rotation         # Rotation angle about ICR (radians)
```

### PointStress Object

Each point's stress is stored as a `PointStress`:

```python
for ps in loaded.point_stresses:
    print(f"Point at ({ps.y}, {ps.z})")
    print(f"  Components: {ps.components}")
    print(f"  Resultant: {ps.stress:.1f} MPa")
```

### StressComponents Object

Access individual stress components at any point:

```python
stress = loaded.at(y=50, z=100)  # Get stress at or near point
print(f"Direct Y: {stress.f_direct_y:.1f} MPa")
print(f"Direct Z: {stress.f_direct_z:.1f} MPa")
print(f"Moment Y: {stress.f_moment_y:.1f} MPa")
print(f"Moment Z: {stress.f_moment_z:.1f} MPa")
print(f"Axial: {stress.f_axial:.1f} MPa")
print(f"Bending: {stress.f_bending:.1f} MPa")
print(f"Resultant: {stress.resultant:.1f} MPa")
```

---

## Visualization

```python
# Plot stress distribution
loaded.plot(
    section=True,        # Show section geometry
    force=True,          # Show applied load
    colorbar=True,       # Show stress magnitude colorbar
    cmap="coolwarm",     # Matplotlib colormap
    weld_linewidth=5.0,  # Width of weld path
    show=True,           # Display immediately
    save_path="weld_analysis.svg"  # Save to file
)
```

Features:
- Weld path colored by stress magnitude
- Section geometry shown in background (if available)
- Applied load location marked
- ICR point shown (if ICR method used)
- Title shows method and max stress

### Comparison Plots

```python
from connecty.weld_plotter import plot_loaded_weld_comparison

# Compare multiple analyses side-by-side
loaded_elastic = LoadedWeld(weld, load, method="elastic")
loaded_icr = LoadedWeld(weld, load, method="icr")

plot_loaded_weld_comparison(
    [loaded_elastic, loaded_icr],
    section=True,
    save_path="comparison.svg"
)
```

---

## Design Checks

Connecty outputs stress only. To check adequacy, you provide the allowable stress:

```python
loaded = LoadedWeld(weld, load, method="elastic")

# Get your allowable stress from design standards or materials
# AISC 360: φ(0.60 F_EXX) for welds
# Example: E70 electrode
F_EXX = 483  # MPa
allowable = 0.75 * 0.60 * F_EXX  # ~218 MPa

# Check utilization
max_stress = loaded.max
utilization = max_stress / allowable

if utilization <= 1.0:
    print(f"OK: Utilization {utilization:.1%}")
else:
    print(f"NOT OK: Utilization {utilization:.1%}")
```

This approach gives you complete control over:
- Electrode selection and strength
- Resistance factors (phi)
- Design methodology (elastic vs. ICR vs. other)
- Safety margins and project requirements

---

## Advanced Topics

### 3D vs. 2D Analysis

**Elastic Method (3D):** Handles all 6 load components. Conservative for eccentric loading.

**ICR Method (2D):** More accurate for in-plane eccentric loading, but ignores out-of-plane effects. Use Elastic for 3D cases.

### Discretization

The `discretization` parameter controls how finely the weld is divided for stress calculation:

```python
# Coarse (faster)
loaded = LoadedWeld(weld, load, discretization=50)

# Fine (more accurate)
loaded = LoadedWeld(weld, load, discretization=500)
```

Higher values give smoother stress plots and are more accurate for visualization. For design, 200-300 is typically sufficient.

### CJP Weld Example

For CJP welds (which are governed by base metal, not weld):

```python
params = WeldParams(type="cjp")
weld = Weld(geometry=geom, parameters=params)

# Analyze with elastic method (CJP doesn't have special strength)
loaded = LoadedWeld(weld, load, method="elastic")

# Check against base metal yield/ultimate, not weld strength
F_y_base = 345  # MPa (e.g., A36)
allowable = 0.9 * F_y_base  # AISC tension allowable

utilization = loaded.max / allowable
```
