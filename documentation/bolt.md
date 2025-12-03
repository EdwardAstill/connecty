# Weldy - Bolt Analysis

## Overview

The bolt analysis module follows the same architectural patterns as the weld module, providing elastic and ICR analysis methods for bolted connections. It uses the same `Force` class for loading and follows the AISC 360 design provisions.

---

## Bolt Types & Analysis Methods

| Bolt Type | Analysis Methods | Key Variable | Strength Limit |
|-----------|------------------|--------------|----------------|
| **Bearing** | Elastic, ICR | Diameter ($d_b$) | Shear/Bearing capacity ($\phi R_n$) |
| **Slip-Critical** | Elastic, ICR | Diameter ($d_b$) | Slip resistance ($\phi R_n$) |

### Analysis Method Summary

**Elastic Method**
- Conservative vector analysis
- Superimposes direct shear ($P/n$) and torsional shear ($Tr/J$)
- Assumes rigid plate behavior
- Check: $f_{resultant} \leq \phi R_n$

**ICR Method**
- Iterative Instantaneous Center of Rotation method
- Accounts for non-linear load-deformation behavior of bolts
- Uses Crawford-Kulak or similar load-deformation curves: $R = R_{ult}(1 - e^{-\mu \Delta})^\lambda$
- More economical for eccentrically loaded bolt groups

---

## Core Classes

### 1. `BoltGroup`

A collection of bolts defined by coordinates or a pattern.

```python
from weldy import BoltGroup, BoltParameters

# Option A: Explicit coordinates
bolts = BoltGroup(
    positions=[(0, 0), (0, 75), (0, 150)],
    parameters=BoltParameters(diameter=20, grade="A325")
)

# Option B: Pattern generation (rectangular)
bolts = BoltGroup.from_pattern(
    rows=3, 
    cols=2, 
    spacing_y=75, 
    spacing_z=60,
    parameters=params,
    origin=(0, 0)
)

# Option C: Circular pattern
bolts = BoltGroup.from_circle(
    n=8,
    radius=100,
    parameters=params,
    center=(0, 0),
    start_angle=0
)
```

### 2. `BoltParameters`

Configuration for bolt properties.

```python
from weldy import BoltParameters

params = BoltParameters(
    diameter=20,              # Bolt diameter (mm)
    grade="A325",             # Grade (A325, A490, 8.8, 10.9)
    threads_excluded=False,   # Threads condition (X or N)
    hole_type="STD",          # Standard, Oversized, Slotted
    shear_planes=1,           # Single or double shear
    slip_critical=False,      # Use slip resistance instead of shear
    slip_class="B",           # Surface class (A, B, C)
    phi=0.75                  # Resistance factor
)
```

### 3. `Force` (Shared)

Uses the existing `Force` class for consistent load definition.

```python
from weldy import Force

force = Force(
    Fy=-100000,           # 100 kN downward (N)
    Fz=50000,             # 50 kN horizontal (N)
    location=(100, 150)   # (y, z) application point
)
```

---

## Analysis Methods

The API mirrors the weld workflow:

```python
from weldy import BoltGroup, BoltParameters, Force

# Setup
params = BoltParameters(diameter=20, grade="A325")
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, parameters=params)
force = Force(Fy=-100000, location=(75, 150))

# Elastic analysis
result = bolts.analyze(force, method="elastic")
print(f"Max bolt force: {result.max_force:.1f} kN")
print(f"Utilization: {result.utilization():.1%}")

# ICR analysis (more economical for eccentric loads)
result_icr = bolts.analyze(force, method="icr")
print(f"ICR Max force: {result_icr.max_force:.1f} kN")
```

### Elastic Method Details
1. **Centroid**: Calculated from bolt coordinates: $C_y = \frac{\sum y_i}{n}$, $C_z = \frac{\sum z_i}{n}$
2. **Polar Moment**: $I_p = \sum (y_i^2 + z_i^2)$ about centroid
3. **Direct Shear**: $R_{direct} = P / n$ (uniform distribution)
4. **Torsional Shear**: $R_{torsion} = \frac{M \cdot r}{I_p}$ (perpendicular to radius, linear with distance)
5. **Superposition**: Vector sum of direct and torsional components

### ICR Method Details
1. **Iterative Solver**: Finds instantaneous center of rotation satisfying equilibrium
2. **Load-Deformation**: Crawford-Kulak model: $R = R_{ult}(1 - e^{-\mu\Delta/\Delta_{max}})^\lambda$
3. **Parameters**: $\mu = 10$, $\lambda = 0.55$, $\Delta_{max} = 8.64$ mm
4. **Benefit**: Accounts for ductile redistribution, typically 15-30% more economical

---

## Result Access

`BoltResult` class (similar to `StressResult`):

```python
result = bolts.analyze(force, method="elastic")

# Key properties
result.max_force       # Maximum resultant force on any bolt (kN)
result.min_force       # Minimum resultant force on any bolt (kN)
result.mean            # Average bolt force (kN)
result.critical_bolt   # BoltForce object at max location
result.critical_index  # Index of most stressed bolt
result.capacity        # Design capacity per bolt φRn (kN)
result.bolt_forces     # List of BoltForce objects

# Methods
result.utilization()   # max_force / capacity
result.is_adequate()   # True if utilization ≤ 1.0

# ICR-specific
result.icr_point       # (y, z) location of ICR (if ICR method used)
```

### BoltForce Object

Each bolt's force is stored as a `BoltForce`:

```python
for bf in result.bolt_forces:
    print(f"Bolt at ({bf.y}, {bf.z})")
    print(f"  Fy = {bf.Fy:.2f} kN")
    print(f"  Fz = {bf.Fz:.2f} kN")
    print(f"  Resultant = {bf.resultant:.2f} kN")
    print(f"  Angle = {bf.angle:.1f}°")
```

---

## Visualization

```python
# Plot analysis results
result.plot(
    force=True,          # Show applied load location
    bolt_forces=True,    # Show reaction vectors at each bolt
    colorbar=True,       # Show force magnitude colorbar
    cmap="coolwarm",     # Matplotlib colormap
    show=True,           # Display immediately
    save_path="bolt_analysis.svg"  # Save to file
)
```

Features:
- Bolts shown as circles colored by force magnitude
- Reaction forces shown as arrows at each bolt
- Applied load location marked with red ×
- ICR point shown (if ICR method used)
- Title includes bolt count, size, grade, max force, and utilization

### Pattern Visualization

```python
from weldy.bolt_plotter import plot_bolt_pattern

# Visualize bolt layout before analysis
plot_bolt_pattern(bolts, save_path="pattern.svg")
```

