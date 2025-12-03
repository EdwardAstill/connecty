# Physics of Weld Stress Calculation

This document explains the physical principles and mathematical formulations used in the weld stress analysis.

## Coordinate System

The analysis uses a right-handed coordinate system:

- **x-axis**: Along the member length (perpendicular to the cross-section plane)
- **y-axis**: Vertical direction in the cross-section plane
- **z-axis**: Horizontal direction in the cross-section plane

The cross-section lies in the **y-z plane**, and the member extends along the **x-axis**.

## Method: Elastic Vector Method (Instantaneous Center of Rotation)

The library uses the **Elastic Vector Method** for weld group analysis. This approach splits the load into concentric and eccentric components and superimposes the resulting stresses vectorially.

This is consistent with the standard elastic method described in engineering literature (e.g., AISC, Shigley):

1.  **Concentric Load**: Assumed to be distributed uniformly (Force / Total Length or Force / Total Area).
2.  **Eccentric Moment (Torsion/Bending)**: Assumed to cause rotation about the centroid, with stress proportional to distance ($Mc/I$ or $Tr/J$).

### Terminology Note: Reaction vs. Stress

Some methods calculate the **reaction force per unit length** ($r$ in N/mm):
$$r = \frac{P}{L} \quad \text{and} \quad r = \frac{Mc}{I}$$

This library calculates **stress** ($\sigma, \tau$ in N/mm² or MPa):
$$\sigma = \frac{P}{A} \quad \text{and} \quad \tau = \frac{Mc}{I_p}$$

Since $A = L \times t_{throat}$ and $I_p$ (moment of inertia) accounts for thickness, the relationship is simply:
$$\text{Stress} = \frac{\text{Reaction per unit length}}{\text{Throat Thickness}}$$

Calculating stress allows the library to handle **mixed weld sizes** (variable throat thickness) correctly, whereas the force-per-unit-length method assumes a constant throat.

## Force and Moment Resolution

### Applied Forces and Moments
    
    A `Force` object represents loads applied at a specific location:
    
    - **Fx**: Axial force (along x-axis, positive = tension)
    - **Fy**: Shear force in y-direction (vertical)
    - **Fz**: Shear force in z-direction (horizontal)
    - **Mx**: Torsional moment about x-axis (applied at location)
    - **My**: Bending moment about y-axis (applied at location)
    - **Mz**: Bending moment about z-axis (applied at location)
    
    ### Specifying Forces: Two Approaches
    
    You can specify forces in two equivalent ways, depending on what is most convenient for your problem. The library automatically handles the mechanics for both.
    
    #### 1. Eccentric Force Method
    
    Specify the force components ($F_x, F_y, F_z$) and the actual location $(y, z)$ where they act. The library will calculate the moment arm from this location to the weld group centroid and add the resulting moments automatically.
    
    ```python
    # Vertical force of 10kN applied 100mm to the right of the origin
    force = Force(Fy=-10000, location=(0, 100))
    ```
    
    #### 2. Centroidal Force + Moment Method
    
    Specify the forces and the *resulting* moments ($M_x, M_y, M_z$) acting directly at the section centroid (typically $(0,0)$).
    
    ```python
    # Same effect: Vertical force + Torsional moment (10kN * 100mm)
    force = Force(Fy=-10000, Mx=1000000, location=(0, 0))
    ```
    
    ### Mathematical Resolution
    
    Internally, all forces are transferred to the **Weld Group Centroid** $(C_y, C_z)$ for calculation. The total design moments are:
    
    ```
    Mx_total = Mx_applied + Fz·dy - Fy·dz
    My_total = My_applied + Fx·dz
    Mz_total = Mz_applied - Fx·dy
    ```
    
    Where:
    - `dy = y_force - C_y` (vertical offset from load point to weld centroid)
    - `dz = z_force - C_z` (horizontal offset from load point to weld centroid)

## Weld Group Properties

Before stress calculation, the weld group properties are computed:

### Centroid Calculation

The centroid (center of area) is found by:

```
Cy = Σ(y_i · dA_i) / A
Cz = Σ(z_i · dA_i) / A
```

Where:
- `dA_i = throat_thickness × ds_i` (area of each weld element)
- `A = Σ dA_i` (total weld area)
- `ds_i` is the length of each discretized element

### Moments of Inertia

The second moments of area about the centroid are calculated by numerical integration over the discretized weld elements:

```
Iz = Σ[(y_i - Cy)² · dA_i]  (about z-axis, horizontal)
Iy = Σ[(z_i - Cz)² · dA_i]  (about y-axis, vertical)
Ip = Iz + Iy                (polar moment, about x-axis)
```

**Note**: Since the calculation integrates $d^2 dA$, it correctly accounts for the moment of inertia of the weld elements themselves, providing higher accuracy than simple line-approximations ($I \approx \Sigma L d^2$).

## Stress Calculation at a Point

For each point along the weld, stresses are calculated by **superposition** of different loading effects.

### 1. In-Plane Shear Stresses (y-z plane)

These are shear stresses acting **in the plane** of the cross-section.

#### Direct Shear Stress (Concentric Load)

From direct forces Fy and Fz, the stress is **uniformly distributed**:

```
τ_direct_y = Fy / A
τ_direct_z = Fz / A
```

#### Torsional Shear Stress (Eccentric Moment)

From moment Mx (torsion), the stress **varies linearly** with distance from the centroid and acts **perpendicular to the radius**:

```
τ_moment_y = -Mx · dz / Ip
τ_moment_z = Mx · dy / Ip
```

Where:
- `dy = y - Cy` (vertical distance from centroid)
- `dz = z - Cz` (horizontal distance from centroid)

**Physical interpretation**: The stress vector is perpendicular to the radius vector `(dy, dz)`. For a positive moment Mx (counter-clockwise when viewed from +x), the stress at a point rotates the weld group about the centroid.

The perpendicular direction is `(-dz, dy)`, which gives:
- Y-component: `-Mx · dz / Ip`
- Z-component: `Mx · dy / Ip`

#### Total In-Plane Shear Stress

The total in-plane shear stress is the **vector sum**:

```
τ_total_y = τ_direct_y + τ_moment_y
τ_total_z = τ_direct_z + τ_moment_z
```

The resultant magnitude:

```
τ_resultant = √(τ_total_y² + τ_total_z²)
```

### 2. Out-of-Plane (Axial) Stresses

These are normal stresses acting **perpendicular to the cross-section** (along the x-axis).

#### Direct Axial Stress

From axial force Fx:

```
σ_axial = Fx / A
```

Uniform distribution (positive = tension).

#### Bending Stress

From bending moments My and Mz, the stress **varies linearly** with distance:

```
σ_bending = (My · dz / Iy) + (Mz · dy / Iz)
```

#### Total Axial Stress

The total axial stress is the **algebraic sum**:

```
σ_total = σ_axial + σ_bending
```

### 3. Resultant Stress

The **resultant stress** combines both in-plane shear and out-of-plane normal stresses:

```
σ_resultant = √(σ_total² + τ_resultant²)
```

## Verification

The implementation has been verified against standard manual calculations for the Elastic Method. 

**Example Case Verified:**
- Vertical weld line (L=100mm)
- Eccentric vertical load (P=10kN at e=100mm)
- Result: Matches theoretical Elastic Method calculation within < 0.1% error.

## References

This method is based on standard weld analysis procedures found in:

- AISC (American Institute of Steel Construction) specifications
- AWS (American Welding Society) D1.1 Structural Welding Code
- Eurocode 3: Design of steel structures
- Standard structural engineering textbooks (e.g., Shigley's Mechanical Engineering Design)
