# Connecty - Bolt Analysis

## Overview

The bolt analysis module calculates **force distribution** on bolt groups using elastic and ICR methods per AISC 360. It focuses on geometry and force calculation—leave design checks and capacity comparisons to your application.

---

## Analysis Methods

Connecty provides two methods for calculating force at each bolt location:

**Elastic Method**
- Conservative vector analysis
- Superimposes direct shear ($P/n$) and torsional shear ($Tr/I_p$)
- Assumes rigid connection behavior
- Output: Force vector at each bolt

**ICR Method**
- Iterative Instantaneous Center of Rotation method
- Accounts for non-linear load-deformation behavior
- Uses Crawford-Kulak load-deformation curves: $R = R_{ult}(1 - e^{-\mu \Delta})^\lambda$
- More accurate force distribution for eccentrically loaded bolt groups
- Output: Force vector at each bolt

---

## Core Classes

### 1. `BoltGroup`

A collection of bolts defined by coordinates or a pattern.

```python
from connecty import BoltGroup, BoltParameters

# Option A: Explicit coordinates
bolts = BoltGroup(
    positions=[(0, 0), (0, 75), (0, 150)],
    parameters=BoltParameters(diameter=20)
)

# Option B: Pattern generation (rectangular)
bolts = BoltGroup.from_pattern(
    rows=3, 
    cols=2, 
    spacing_y=75, 
    spacing_z=60,
    diameter=20,
    origin=(0, 0)
)

# Option C: Circular pattern
bolts = BoltGroup.from_circle(
    n=8,
    radius=100,
    diameter=20,
    center=(0, 0),
    start_angle=0
)
```

### 2. `BoltParameters`

Configuration for bolt geometry (for visualization and ICR calculations).

```python
from connecty import BoltParameters

params = BoltParameters(
    diameter=20  # Bolt diameter in mm
)
```

That's it! Only diameter is needed. Material properties are outside the scope of force calculation.

### 3. `Force` (Shared)

Uses the existing `Force` class for consistent load definition.

```python
from connecty import Force

force = Force(
    Fy=-100000,           # 100 kN downward (N)
    Fz=50000,             # 50 kN horizontal (N)
    location=(100, 150)   # (y, z) application point
)
```

---

## Analysis Workflow

The API is straightforward:

```python
from connecty import BoltGroup, BoltParameters, Force

# Setup
params = BoltParameters(diameter=20)
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)
force = Force(Fy=-100000, location=(75, 150))

# Elastic analysis
result = bolts.analyze(force, method="elastic")
print(f"Max bolt force: {result.max_force:.1f} kN")

# ICR analysis (more accurate for eccentric loads)
result_icr = bolts.analyze(force, method="icr")
print(f"ICR Max force: {result_icr.max_force:.1f} kN")
```

### Elastic Method Details

1. **Centroid**: Calculated from bolt coordinates
   - $C_y = \frac{\sum y_i}{n}$, $C_z = \frac{\sum z_i}{n}$

2. **Polar Moment**: $I_p = \sum (dy_i^2 + dz_i^2)$ about centroid

3. **Direct Shear**: $R_{direct} = P / n$ (uniform distribution)

4. **Torsional Shear**: $R_{torsion} = \frac{M \cdot r}{I_p}$ (perpendicular to radius)

5. **Superposition**: Vector sum of direct and torsional components

### ICR Method Details

1. **Iterative Solver**: Finds instantaneous center of rotation satisfying equilibrium

2. **Load-Deformation**: Crawford-Kulak model
   - $R = R_{ult}(1 - e^{-\mu\Delta/\Delta_{max}})^\lambda$
   - $\mu = 10$, $\lambda = 0.55$, $\Delta_{max} = 8.64$ mm

3. **Benefit**: Accounts for ductile redistribution; typically yields more realistic force distribution than elastic method

---

## Result Access

`BoltResult` provides force data at each bolt:

```python
result = bolts.analyze(force, method="elastic")

# Properties
result.max_force       # Maximum resultant force on any bolt (kN)
result.min_force       # Minimum resultant force on any bolt (kN)
result.mean            # Average bolt force (kN)
result.critical_bolt   # BoltForce object at max location
result.critical_index  # Index of most stressed bolt
result.bolt_forces     # List of all BoltForce objects

# ICR-specific
result.icr_point       # (y, z) location of instantaneous center
result.method          # "elastic" or "icr"
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
- Title shows bolt count, size, and max force

### Pattern Visualization

```python
from connecty.bolt_plotter import plot_bolt_pattern

# Visualize bolt layout before analysis
plot_bolt_pattern(bolts, save_path="pattern.svg")
```

---

## Design Checks

Connecty outputs forces only. To check adequacy:

```python
result = bolts.analyze(force, method="elastic")

# Get your bolt capacity from tables or calculation
bolt_capacity_kN = 150  # Example: A325 M20 bearing-type

# Check utilization
max_force = result.max_force
utilization = max_force / bolt_capacity_kN

if utilization <= 1.0:
    print(f"OK: Utilization {utilization:.1%}")
else:
    print(f"NOT OK: Utilization {utilization:.1%}")
```

This approach gives you full control over capacity definitions, phi factors, and design philosophy.
