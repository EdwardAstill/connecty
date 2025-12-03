# Connecty - Weld Stress Analysis

## Overview

Connecty calculates stress distribution along welded connections per AISC 360. It integrates with **sectiony** for section geometry and follows the **beamy** pattern for result access.

---

## Weld Types & Analysis Methods

| Weld Type | Analysis Methods | Key Variable | Strength Limit |
|-----------|------------------|--------------|----------------|
| **Fillet** | Elastic, ICR | Leg size ($w$) or throat ($a$) | $\phi R_n = \phi(0.60 F_{EXX}) A_w$ |
| **PJP** | Elastic | Effective throat ($E$) | $\phi R_n = \phi(0.60 F_{EXX}) A_w$ |
| **CJP** | Base metal check | Plate thickness ($t$) | Base metal governs ($F_y$, $F_u$) |
| **Plug/Slot** | Elastic (shear only) | Hole/slot area ($A_w$) | $\phi R_n = \phi(0.60 F_{EXX}) A_w$ |

### Analysis Method Summary

**Elastic Method** (all weld types)
- Conservative, closed-form solution
- Full **3D analysis** (handles $F_x, F_y, F_z, M_x, M_y, M_z$)
- Stress = vector sum of components (direct + moment)
- $f_{resultant} = \sqrt{f_{axial}^2 + f_{shear,y}^2 + f_{shear,z}^2}$
- Check: $f_{resultant} \leq \phi(0.60 F_{EXX})$

**ICR Method** (fillet welds only)
- Iterative, accounts for load angle benefit
- **2D analysis only** (in-plane loads $F_y, F_z, M_x$)
- Assumes instantaneous center of rotation lies in the plane of the connection
- Strength increase factor: $(1.0 + 0.50 \sin^{1.5}\theta)$
- More economical than elastic method for in-plane eccentricity

**Base Metal Analysis** (CJP welds)
- CJP weld strength exceeds base metal
- Check base metal capacity instead
- Weld effectively "disappears" from analysis

---

## Core Classes

### 1. `Weld`

A weld path defined by geometry and weld parameters. The geometry can be provided directly or derived from a section's contour.

```python
from connecty import Weld, WeldParameters
from sectiony import Geometry, Contour, Line, Arc
from sectiony.library import rhs

# Option A: Explicit geometry (the core way)
# Geometry built exactly like sectiony, but Contours need not be closed
path = Contour(segments=[
    Line(start=(0, -50), end=(0, 50)),
    Arc(center=(0, 50), radius=10, start_angle=math.pi, end_angle=0)
])
weld = Weld(
    geometry=Geometry(contours=[path]),
    parameters=WeldParameters(weld_type="fillet", throat=5.0)
)

# Option B: Derive geometry from section (convenience)
# Extracts the outer contour as the weld path
section = rhs(b=100, h=200, t=10, r=15)
weld = Weld.from_section(
    section=section,
    parameters=WeldParameters(weld_type="fillet", throat=4.2, leg=6.0)
)
# The section is stored for plotting but NOT required for analysis
```

#### Constructor

```python
Weld(geometry: Geometry, parameters: WeldParameters)
```

**Required:**
- `geometry`: Weld path as a sectiony `Geometry` (contours need not be closed)
- `parameters`: `WeldParameters` (throat, type, etc.)

#### Class Methods

| Method | Description |
|--------|-------------|
| `Weld.from_section(section, parameters, contour_index=0)` | Create weld from section's contour. Stores section for plotting. |

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `geometry` | `Geometry` | Weld path geometry (required) |
| `parameters` | `WeldParameters` | Weld configuration |
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

### 2. `WeldParameters`

```python
@dataclass
class WeldParameters:
    weld_type: Literal["fillet", "pjp", "cjp", "plug", "slot"]
    
    # Geometry (provide what's relevant for weld type)
    leg: float | None = None         # Fillet leg size (w)
    throat: float | None = None      # Effective throat (a or E)
    area: float | None = None        # Plug/slot: hole or slot area
    
    # Material
    electrode: str = "E70"           # Electrode classification (E60, E70, E80, etc.)
    F_EXX: float | None = None       # Override: electrode tensile strength (MPa)
    
    # Base metal (for CJP and capacity checks)
    F_y: float | None = None         # Base metal yield strength
    F_u: float | None = None         # Base metal ultimate strength
    t_base: float | None = None      # Base metal thickness
    
    # Resistance factor
    phi: float = 0.75                # AISC default for welds
```

#### Electrode Strengths (auto-lookup if `F_EXX` not provided)

| Electrode | $F_{EXX}$ (MPa) | $F_{EXX}$ (ksi) |
|-----------|-----------------|-----------------|
| E60 | 414 | 60 |
| E70 | 483 | 70 |
| E80 | 552 | 80 |
| E90 | 621 | 90 |
| E100 | 690 | 100 |
| E110 | 759 | 110 |

#### Throat Calculation (fillet welds)

If only `leg` is provided, throat is calculated automatically:
- **Equal leg fillet (45°):** $a = w \times 0.707$
- For unequal leg or other angles, provide `throat` directly.

#### Effective Throat for PJP

For PJP welds, `throat` is the effective throat $E$ per AISC Table J2.1, which depends on:
- Groove angle
- Welding process (SMAW, GMAW, FCAW, SAW)
- Welding position

---

### 3. `Force`

Load definition with 6 components and application location.

```python
from connecty import Force

# Option A: Direct components
force = Force(Fx=0, Fy=-100e3, Fz=0, Mx=0, My=0, Mz=0, location=(0, 50))

# Option B: Named constructor
force = Force.from_components(
    axial=0,
    shear_y=-100e3,
    shear_z=0,
    torsion=0,
    moment_y=0,
    moment_z=0,
    at=(0, 50)  # (y, z) point of application
)
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

### Method

```python
result = weld.stress(force, method="elastic", discretization=100)
```

**Parameters:**
- `force`: `Force` object
- `method`: Analysis method (see below)
- `discretization`: Points per segment (default 100)

**Returns:** `StressResult` object

### Available Methods by Weld Type

| Weld Type | `method=` | Description |
|-----------|-----------|-------------|
| **Fillet** | `"elastic"` | Conservative vector sum (default) |
| **Fillet** | `"icr"` | ICR method with angle benefit |
| **PJP** | `"elastic"` | Vector analysis (only option) |
| **CJP** | `"base_metal"` | Returns base metal capacity check |
| **Plug/Slot** | `"elastic"` | Shear-only analysis |

### Elastic Method Details

Calculates stress at each discretized point:

1. **Direct stresses** (uniform):
   - $f_{direct,y} = F_y / A_w$
   - $f_{direct,z} = F_z / A_w$
   - $f_{axial} = F_x / A_w$

2. **Moment stresses** (linear with distance from centroid):
   - In-plane torsion: $f_{moment} = M_x \cdot r / I_p$
   - Out-of-plane bending: $f_{bending} = M_y \cdot z / I_y + M_z \cdot y / I_z$

3. **Resultant**:
   - $f_{resultant} = \sqrt{f_{axial,total}^2 + f_{shear,y}^2 + f_{shear,z}^2}$

4. **Capacity check**:
   - $f_{resultant} \leq \phi (0.60 \cdot F_{EXX})$

### ICR Method Details (Fillet Welds)

The Instantaneous Center of Rotation method:

1. Iterates to find the rotation center that satisfies equilibrium
2. Applies directional strength increase: $(1.0 + 0.50 \sin^{1.5}\theta)$
3. Where $\theta$ = angle between resultant force and weld longitudinal axis
4. More economical for eccentrically loaded connections

**Note on 2D vs 3D Analysis:**
The ICR implementation in this package is a **2D analysis**. It considers only in-plane loads ($F_y, F_z$) and torsion ($M_x$). Out-of-plane loads ($F_x, M_y, M_z$) are **ignored** by the ICR solver.

*Justification:* The primary benefit of the ICR method comes from the non-linear redistribution of shear forces in eccentrically loaded groups (e.g., lap joints, bracket plates). Extending the non-linear instantaneous axis of rotation to 3D (6 degrees of freedom) significantly increases computational complexity and stability risks. For combined 3D loading, use the **Elastic Method**, which conservatively superimposes all 6 load components.

```python
# ICR method for fillet welds
result = weld.stress(force, method="icr")

# Access ICR-specific results
print(f"ICR location: {result.icr_point}")
print(f"Rotation angle: {result.rotation}")
```

### CJP Weld Analysis

CJP welds match or exceed base metal strength. Analysis shifts to base metal:

```python
params = WeldParameters(
    weld_type="cjp",
    t_base=12.0,    # Plate thickness
    F_y=345,        # Base metal yield (MPa)
    F_u=450         # Base metal ultimate (MPa)
)

weld = Weld(geometry=geom, parameters=params)
result = weld.stress(force, method="base_metal")

# Returns base metal capacity, not weld stress
print(f"Base metal utilization: {result.utilization():.1%}")
```

### Plug/Slot Weld Analysis

Resists shear only (no moment capacity):

```python
params = WeldParameters(
    weld_type="plug",
    area=500,       # Plug hole area (mm²)
    electrode="E70"
)

# Only in-plane forces (Fy, Fz) are valid
# Fx, Mx, My, Mz should be zero or will raise warning
force = Force(Fy=-20e3, Fz=10e3)
result = weld.stress(force)
```

---

## Result Access (beamy pattern)

The `StressResult` class follows beamy's `Result` pattern for convenient access to stress values.

### Properties

| Property | Returns | Description |
|----------|---------|-------------|
| `max` | `float` | Maximum resultant stress |
| `min` | `float` | Minimum resultant stress |
| `mean` | `float` | Average stress |
| `range` | `float` | max - min |
| `capacity` | `float` | $\phi (0.60 \cdot F_{EXX})$ from parameters |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `at(y, z)` | `StressComponents` | Stress components at nearest point |
| `max_point` | `PointStress` | Location and components of max stress |
| `all` | `List[PointStress]` | All stress points |
| `utilization(allowable=None)` | `float` | max / allowable (uses capacity if None) |
| `is_adequate()` | `bool` | True if utilization ≤ 1.0 |

### Capacity & Utilization

```python
result = weld.stress(force)

# Capacity auto-calculated from electrode
print(f"Weld capacity: {result.capacity:.1f} MPa")  # φ(0.60 × F_EXX)

# Utilization uses capacity by default
print(f"Utilization: {result.utilization():.1%}")

# Or provide custom allowable
print(f"Custom check: {result.utilization(allowable=150):.1%}")

# Quick pass/fail
if result.is_adequate():
    print("✓ Weld is adequate")
```

### Stress Components Access

```python
result = weld.stress(force)

# Quick access
print(f"Max stress: {result.max:.1f} MPa")
print(f"Utilization: {result.utilization(200):.2%}")

# Detailed access at max location
pt = result.max_point
print(f"Location: ({pt.y:.1f}, {pt.z:.1f})")
print(f"Direct shear: {pt.components.shear_resultant:.1f}")
print(f"Axial: {pt.components.total_axial:.1f}")
print(f"Resultant: {pt.components.resultant:.1f}")

# Access specific components
components = result.at(y=100, z=0)
print(f"f_direct_y: {components.f_direct_y}")
print(f"f_moment_z: {components.f_moment_z}")
```

### `StressComponents` Breakdown

| Component | Description |
|-----------|-------------|
| `f_direct_y` | In-plane shear from Fy (uniform) |
| `f_direct_z` | In-plane shear from Fz (uniform) |
| `f_moment_y` | In-plane shear from Mx (y-component) |
| `f_moment_z` | In-plane shear from Mx (z-component) |
| `f_axial` | Out-of-plane from Fx (uniform) |
| `f_bending` | Out-of-plane from My, Mz (linear) |
| **Computed** | |
| `total_y` | f_direct_y + f_moment_y |
| `total_z` | f_direct_z + f_moment_z |
| `total_axial` | f_axial + f_bending |
| `shear_resultant` | √(total_y² + total_z²) |
| `resultant` | √(total_axial² + shear_resultant²) |

---

## Visualization

### `result.plot(...)`

```python
result.plot(
    section=True,       # Show section outline (only if weld has section reference)
    force=True,         # Show force arrow at application point
    colorbar=True,      # Show stress colorbar
    cmap="coolwarm",    # Matplotlib colormap
    weld_linewidth=5.0, # Weld line thickness
    ax=None,            # Matplotlib axes (creates new if None)
    show=True,          # Display plot
    save_path=None      # Save to file (use .svg extension)
)
```

**Note:** `section=True` only has an effect if the `Weld` was created via `Weld.from_section()`. Otherwise, only the weld path is shown.

### `result.plot_components(...)`

Plot individual stress components for detailed analysis.

```python
result.plot_components(
    components=["direct", "moment", "axial", "bending"],  # Which to show
    layout="grid",  # "grid" or "row"
    ...
)
```

---

## Complete Examples

### Example 1: Fillet Weld - Elastic Method

```python
from sectiony.library import rhs
from connecty import Weld, WeldParameters, Force

# 1. Create fillet weld from RHS section
section = rhs(b=100, h=200, t=10, r=15)
params = WeldParameters(
    weld_type="fillet",
    leg=6.0,              # 6mm leg → throat auto-calculated as 4.2mm
    electrode="E70"       # F_EXX = 483 MPa
)

weld = Weld.from_section(section=section, parameters=params)

# 2. Define eccentric load
force = Force(
    Fy=-100e3,           # 100 kN down
    location=(100, 0)    # Applied 100mm above centroid (creates torsion)
)

# 3. Calculate stress (elastic method is default)
result = weld.stress(force)

# 4. Check results
print(f"Max stress: {result.max:.1f} MPa")
print(f"Capacity: {result.capacity:.1f} MPa")  # φ(0.60 × 483) = 217 MPa
print(f"Utilization: {result.utilization():.1%}")

if result.is_adequate():
    print("✓ Weld OK")

# 5. Plot
result.plot(section=True, force=True, save_path="fillet_elastic.svg")
```

### Example 2: Fillet Weld - ICR Method

```python
from sectiony.library import rhs
from connecty import Weld, WeldParameters, Force

# Same setup as Example 1
section = rhs(b=100, h=200, t=10, r=15)
params = WeldParameters(weld_type="fillet", leg=6.0, electrode="E70")
weld = Weld.from_section(section=section, parameters=params)

force = Force(Fy=-100e3, location=(100, 0))

# Use ICR method - accounts for load angle benefit
result = weld.stress(force, method="icr")

print(f"Max stress (ICR): {result.max:.1f} MPa")
print(f"Utilization (ICR): {result.utilization():.1%}")

# ICR typically gives lower utilization than elastic
# due to (1.0 + 0.5 sin^1.5 θ) strength increase
```

### Example 3: PJP Groove Weld

```python
from connecty import Weld, WeldParameters, Force
from sectiony import Geometry, Contour, Line

# PJP weld at top of a beam flange connection
weld_path = Contour(segments=[Line(start=(0, -150), end=(0, 150))])

params = WeldParameters(
    weld_type="pjp",
    throat=8.0,           # Effective throat E = 8mm
    electrode="E70"
)

weld = Weld(
    geometry=Geometry(contours=[weld_path]),
    parameters=params
)

# Tension + bending
force = Force(Fx=200e3, Mz=50e6)
result = weld.stress(force)  # Elastic method only for PJP

print(f"Max stress: {result.max:.1f} MPa")
print(f"Utilization: {result.utilization():.1%}")
```

### Example 4: CJP Weld (Base Metal Check)

```python
from connecty import Weld, WeldParameters, Force
from sectiony import Geometry, Contour, Line

# CJP weld - strength exceeds base metal, so check base metal
weld_path = Contour(segments=[Line(start=(0, -100), end=(0, 100))])

params = WeldParameters(
    weld_type="cjp",
    t_base=12.0,          # 12mm plate
    F_y=345,              # Grade 345 steel yield
    F_u=450,              # Ultimate strength
    electrode="E70"       # Matching electrode
)

weld = Weld(
    geometry=Geometry(contours=[weld_path]),
    parameters=params
)

force = Force(Fx=500e3)  # Tension
result = weld.stress(force, method="base_metal")

# Result is base metal utilization, not weld stress
print(f"Base metal utilization: {result.utilization():.1%}")
```

### Example 5: Custom Geometry (No Section)

```python
from connecty import Weld, WeldParameters, Force
from sectiony import Geometry, Contour, Line

# Two vertical fillet welds for a simple lap joint
left = Contour(segments=[Line(start=(-50, -100), end=(-50, 100))])
right = Contour(segments=[Line(start=(50, -100), end=(50, 100))])

weld = Weld(
    geometry=Geometry(contours=[left, right]),
    parameters=WeldParameters(weld_type="fillet", leg=5.0, electrode="E70")
)

force = Force(Fy=-50e3, location=(0, 0))
result = weld.stress(force)

print(f"Max stress: {result.max:.1f} MPa")

# Plot shows just weld paths (no section)
result.plot(force=True)
```

### Example 6: Plug Weld

```python
from connecty import Weld, WeldParameters, Force
from sectiony import Geometry, Contour, Arc
import math

# Circular plug weld (represented as a point with area)
# For plug welds, geometry defines location; area defines capacity
plug_center = Contour(segments=[
    Arc(center=(0, 0), radius=10, start_angle=0, end_angle=2*math.pi)
])

params = WeldParameters(
    weld_type="plug",
    area=math.pi * 10**2,  # πr² = 314 mm²
    electrode="E70"
)

weld = Weld(
    geometry=Geometry(contours=[plug_center]),
    parameters=params
)

# Plug welds resist shear only
force = Force(Fy=-15e3, Fz=10e3)
result = weld.stress(force)

print(f"Shear stress: {result.max:.1f} MPa")
```

---

## API Summary

```
Weld
├── geometry: Geometry              # Required - weld path
├── parameters: WeldParameters
├── section: Section | None         # Optional - only for plotting
├── A, L, Cy, Cz, Iy, Iz, Ip       (properties)
├── stress(force, method, discretization) → StressResult
└── from_section(section, parameters, contour_index) → Weld  (classmethod)

StressResult
├── max, min, mean, range, capacity  (properties)
├── max_point → PointStress
├── all → List[PointStress]
├── at(y, z) → StressComponents
├── utilization(allowable=None) → float
├── is_adequate() → bool
├── plot(section, force, ...) → Axes
└── plot_components(...) → Axes

PointStress
├── point: (y, z)
├── y, z  (properties)
├── stress → float (resultant)
└── components → StressComponents

StressComponents
├── f_direct_y, f_direct_z
├── f_moment_y, f_moment_z
├── f_axial, f_bending
├── total_y, total_z, total_axial  (properties)
├── shear_resultant  (property)
└── resultant  (property)

Force
├── Fx, Fy, Fz, Mx, My, Mz
├── location: (y, z)
└── from_components(...) → Force  (classmethod)

WeldParameters
├── weld_type: "fillet" | "pjp" | "cjp" | "plug" | "slot"
├── leg: float | None              # Fillet leg size
├── throat: float | None           # Effective throat
├── area: float | None             # Plug/slot area
├── electrode: str = "E70"         # Electrode classification
├── F_EXX: float | None            # Override electrode strength
├── F_y, F_u: float | None         # Base metal strengths (CJP)
├── t_base: float | None           # Base metal thickness (CJP)
└── phi: float = 0.75              # Resistance factor
```

---

## Coordinate System

Follows sectiony conventions:
- **y-axis**: Vertical (positive up)
- **z-axis**: Horizontal (positive right)  
- **x-axis**: Longitudinal (positive out of page)

Points are `(y, z)` tuples.

---

## Units

Unit-agnostic. Ensure consistency:
- Length: mm → Area: mm², Inertia: mm⁴
- Force: N, Moment: N·mm → Stress: MPa (N/mm²)
- Force: kN, Moment: kN·m, Length: m → Stress: kPa

---

## References & Standards

Based on **AISC 360-22** (Specification for Structural Steel Buildings):
- **Section J2**: Welds
- **Table J2.5**: Available Strength of Welded Joints

Key equations:
- Fillet/PJP/Plug nominal strength: $R_n = F_{nw} \times A_{we}$
- Where $F_{nw} = 0.60 \times F_{EXX}$ (filler metal classification strength)
- Design strength: $\phi R_n$ with $\phi = 0.75$

ICR method reference:
- AISC Design Guide 8: Column Base Plates
- AWS D1.1 Annex K

---

## Limitations

1. **Linear elastic analysis** - Does not model weld ductility or load redistribution
2. **2D weld groups** - All welds assumed in same plane (y-z)
3. **No fatigue** - Static loading only; use other tools for fatigue assessment
4. **Simplified shear lag** - Does not account for shear lag in long connections
5. **No weld defects** - Assumes full-strength welds without defects
