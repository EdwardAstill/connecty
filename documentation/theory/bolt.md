# Bolt Group Theory

## 1. Global Coordinate System

To ensure consistency between shear and tension solvers, `connecty` uses a standard 3D member coordinate system where the -axis is the longitudinal axis of the member.

* ** (Axial):** Out-of-plane.  indicates tension;  indicates compression.
* ** (Vertical):** In-plane vertical.  is upward.
* ** (Horizontal):** In-plane horizontal.  is to the right.
* ** (Torsion):** Counter-clockwise (CCW) when looking toward the origin from .
* ** (Bending):** Causes tension on the  side of the plate.
* ** (Bending):** Causes tension on the  side of the plate.

---

## 2. In-Plane Shear ()

### 2.1 Elastic Method (Linear)

The elastic method assumes bolts behave as linear springs and that shear force is proportional to the distance from the bolt group centroid .

**1. Load Transfer to Centroid:**
Before analysis, all applied loads  and the eccentric moment  acting at  must be transferred to the bolt group centroid:


**2. Force Components:**

* **Direct Shear:**  and .
* **Torsional Shear:**  and .
* **Resultant:** .

### 2.2 Instantaneous Center of Rotation (ICR) Method (Nonlinear)

The ICR method uses the **Crawford–Kulak** nonlinear load-deformation relationship to account for force redistribution as bolts yield.

**Kinematics and Force Calculation:**

* **Assumption:** The plate rotates rigidly about a point .
* **Deformation:** Bolt slip  is proportional to its radius  from the ICR.
* **Nonlinear Relationship:**  (where ).
* **Equilibrium:** The solver iteratively finds the  where the sum of internal bolt moments equals the applied .

---

## 3. Out-of-Plane Tension ()

### 3.1 Plate Neutral-Axis Method

Tension is calculated by assuming the plate rotates about a **Neutral Axis (NA)**, creating a linear strain distribution.

**1. NA Selection:**

* **Conservative:** The NA is fixed at the bolt group centroid.
* **Accurate:** The NA is shifted to  from the compression edge (the "Kern" limit), simulating the presence of a compression block.

**2. Axis Mapping:**

*  is resisted by the -coordinates of the bolts.
*  is resisted by the -coordinates of the bolts.

**3. Peak Row Force ():**
The peak tension  in the furthest row is solved using the following equilibrium equation, where  is the lever arm to the compression resultant:


---

## 4. Design Adjustments: Prying Action

The demand  calculated above represents only the static equilibrium force. However, if the plate is flexible, the interaction between the plate edge and the support creates an additional "prying" force () on the bolt. The total design demand is defined as .

### 4.1 Geometric Prying (Simplified AISC Model)

The prying calculation in `connecty` follows a simplified procedure based on the AISC Manual (Part 9) mechanics to determine the increase in bolt tension due to plate flexibility.

#### Parameters
* **$p$ (Effective Width):** The tributary length of plate per bolt. In this implementation, simplified to $p = 2 \cdot d_{bolt}$.
* **$a$:** Distance from the bolt centerline to the edge of the plate.
* **$b$:** Distance from the bolt centerline to the face of the support (web/flange toe).
* **$\rho$:** The geometric ratio $b/a$.
* **$\delta$:** The net area ratio at the bolt line, $\delta = 1 - d_{bolt}/p$.

#### Calculation Procedure

**1. Determine Thickness Required to Eliminate Prying ($t_{req}$)**
First, the solver calculates the plate thickness theoretically required to keep the prying force at zero (where the plate is stiff enough to act rigidly).

$$
t_{req} = \sqrt{\frac{4.44 \cdot T_{static} \cdot b}{p \cdot F_y \cdot (1 + \delta)}}
$$

**2. Calculate Prying Ratio**
If the actual plate thickness $t_{plate} < t_{req}$, the plate will deform and generate prying forces. The prying ratio ($Q/T$) is approximated as:

$$
\text{Ratio} = \frac{1}{\delta} \left[ \left(\frac{t_{req}}{t_{plate}}\right)^2 - 1 \right] \left( \frac{\rho}{1 + \rho} \right)
$$

This ratio is clamped between 0.0 and 1.0.

**3. Total Tension ($T_{design}$)**
The final design tension includes the amplification factor:

$$
T_{design} = T_{static} \cdot (1 + \text{Ratio})
$$

---

