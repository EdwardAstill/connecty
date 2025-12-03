# Physics of Connection Analysis: Welds & Bolts

This document explains the physical principles and mathematical formulations used in the structural analysis library. It covers both welded and bolted connections, detailing the coordinate systems, load resolution, and analysis methods (Elastic and Instantaneous Center of Rotation).

---

## 1. Coordinate System

The analysis uses a consistent right-handed coordinate system for all connections:

-   **x-axis**: Along the member length (perpendicular to the cross-section plane).
-   **y-axis**: Vertical direction in the cross-section plane.
-   **z-axis**: Horizontal direction in the cross-section plane.

The connection (weld group or bolt pattern) lies in the **y-z plane**, and the member extends along the **x-axis**.

---

## 2. Force and Moment Resolution

Loads are applied using a `Force` object. All loads are ultimately resolved into forces and moments acting at the **centroid** of the connection (weld group or bolt group) before stress analysis begins.

### 2.1 Applied Loads
-   **Forces**: $F_x$ (Axial), $F_y$ (Vertical Shear), $F_z$ (Horizontal Shear).
-   **Moments**: $M_x$ (Torsion), $M_y$ (Bending), $M_z$ (Bending).

### 2.2 Resolution to Centroid
Loads applied at an arbitrary location $(y_{force}, z_{force})$ are transferred to the connection centroid $(C_y, C_z)$. The design moments used for analysis are:

$$
Mx_{total} = Mx_{applied} + Fz \cdot dy - Fy \cdot dz \\
My_{total} = My_{applied} + Fx \cdot dz \\
Mz_{total} = Mz_{applied} - Fx \cdot dy
$$

Where:
-   $dy = y_{force} - C_y$ (Vertical offset)
-   $dz = z_{force} - C_z$ (Horizontal offset)

---

## 3. Weld Analysis

Weld analysis treats the connection as a collection of line elements. Stresses are calculated per unit area of the effective throat.

### 3.1 Geometric Properties (Weld Group)
Properties are calculated by integrating over the discretized weld elements.

**Centroid:**
$$
Cy = \frac{\sum(y_i \cdot dA_i)}{A}, \quad Cz = \frac{\sum(z_i \cdot dA_i)}{A}
$$
Where $dA_i = \text{throat} \times ds_i$.

**Moments of Inertia:**
Calculated using the parallel axis theorem, integrating $d^2 dA$:
$$
Iz = \sum[(y_i - Cy)^2 \cdot dA_i] \quad (\text{Axis: } z) \\
Iy = \sum[(z_i - Cz)^2 \cdot dA_i] \quad (\text{Axis: } y) \\
Ip = Iz + Iy \quad (\text{Polar Moment})
$$
*Note: The calculation includes the element's own moment of inertia, providing higher accuracy than simple line approximations.*

### 3.2 Elastic Vector Method (Welds)
This conservative method superimposes stresses from direct loads and moments vectorially.

**In-Plane Shear (y-z plane):**
Combines direct shear ($F/A$) and torsional shear ($Tr/Ip$).
-   **Direct**: $\tau_{dir, y} = F_y/A$, $\tau_{dir, z} = F_z/A$
-   **Torsional**: Acts perpendicular to the radius $r$.
    $$
    \tau_{tor, y} = -\frac{M_x \cdot dz}{Ip}, \quad \tau_{tor, z} = \frac{M_x \cdot dy}{Ip}
    $$
-   **Resultant**: $\tau_{res} = \sqrt{(\tau_{dir, y} + \tau_{tor, y})^2 + (\tau_{dir, z} + \tau_{tor, z})^2}$

**Out-of-Plane Stress (x-direction):**
Combines axial load and bending.
$$
\sigma_{total} = \frac{F_x}{A} + \frac{M_y \cdot dz}{Iy} + \frac{M_z \cdot dy}{Iz}
$$

**Final Resultant:**
$$
\sigma_{vm} = \sqrt{\sigma_{total}^2 + \tau_{res}^2}
$$

### 3.3 ICR Method (Welds)
The **Instantaneous Center of Rotation (ICR)** method accounts for the non-linear load-deformation behavior of fillet welds.
-   **Assumption**: The connection rotates about an instantaneous center (IC).
-   **Deformation**: Varies linearly with distance from IC ($r$).
-   **Stress/Force**: Non-linear function of deformation angle and magnitude.
-   **Equilibrium**: The location of the IC is found iteratively such that $\sum F_x = 0, \sum F_y = 0, \sum M = 0$.

---

## 4. Bolt Analysis

Bolt analysis treats the connection as a set of discrete points (bolts). Analysis checks individual bolt forces against shear or slip capacity.

### 4.1 Geometric Properties (Bolt Group)
Properties are derived from the discrete bolt locations.

**Centroid:**
Assuming all bolts have equal area:
$$
Cy = \frac{\sum y_i}{n}, \quad Cz = \frac{\sum z_i}{n}
$$
Where $n$ is the number of bolts.

**Polar Moment of Inertia ($J$ or $I_p$):**
Sum of the squared distances from the centroid to each bolt:
$$
I_p = \sum (r_i^2) = \sum ((y_i - Cy)^2 + (z_i - Cz)^2)
$$
*Note: This simplifies the integral used in welds to a discrete summation.*

### 4.2 Elastic Vector Method (Bolts)
Similar to the weld method, but calculates **Force per Bolt** rather than stress.

**Direct Shear Force:**
Assumed to be shared equally among bolts:
$$
R_{dir, y} = \frac{F_y}{n}, \quad R_{dir, z} = \frac{F_z}{n}
$$

**Torsional Shear Force:**
Varies linearly with distance $r$ from the centroid. The force on bolt $i$ is:
$$
R_{tor, i} = \frac{M_x \cdot r_i}{I_p}
$$
Resolving into components (similar to welds, force opposes rotation):
$$
R_{tor, y} = -\frac{M_x \cdot dz}{I_p}, \quad R_{tor, z} = \frac{M_x \cdot dy}{I_p}
$$

**Resultant Bolt Force:**
The vector sum of direct and torsional forces:
$$
R_{total} = \sqrt{(R_{dir, y} + R_{tor, y})^2 + (R_{dir, z} + R_{tor, z})^2}
$$
*Check*: $R_{total} \leq \phi R_n$ (Bolt Capacity).

### 4.3 ICR Method (Bolts)
Used for eccentrically loaded bolt groups to utilize the post-elastic reserve strength.

**Concept:**
The group rotates about an Instantaneous Center (IC). The force in each bolt is determined by its deformation, which is proportional to its distance from the IC.

**Load-Deformation Relationship:**
Typically uses empirical curves (e.g., Crawford-Kulak for A325/A490 bolts):
$$
R = R_{ult} (1 - e^{-\mu \Delta})^\lambda
$$
Where:
-   $R$: Bolt force at deformation $\Delta$.
-   $R_{ult}$: Ultimate shear strength of the bolt.
-   $\Delta$: Deformation (proportional to distance $r$ from IC).
-   $\mu, \lambda$: Empirical coefficients determined by test data.

**Process:**
1.  Guess a location for the IC.
2.  Calculate deformation $\Delta_i$ for each bolt (max deformation $\Delta_{max} = 0.34$ inches typically).
3.  Calculate force $R_i$ using the curve.
4.  Check equilibrium equations ($\sum F = 0, \sum M = 0$).
5.  Iterate until convergence.

---

## 5. References

-   **AISC Specification for Structural Steel Buildings (AISC 360)**: Chapter J (Connections).
-   **AISC Steel Construction Manual**: Part 7 (Bolts) and Part 8 (Welds).
-   **Fisher, Kulak, and Struik**: "Guide to Design Criteria for Bolted and Riveted Joints".
-   **Shigley's Mechanical Engineering Design**: Analysis of bolted and welded joints.
