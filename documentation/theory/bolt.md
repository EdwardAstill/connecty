## Overview
The icr and elastic methods can be used to determine the forces at each bolt (unlike in whelds where the stress in the weld is determined). 


Here are an outline of the methods discussed for calculating the forces in bolts.

### Determining shear forces:
For in plane shear loading (no tension) we can use a 2D elastic or icr method as outlined below.

### Determining axial/tension forces:
For the out of plane loading we need to consider the geometry of the plate and bolt together to determine the tension in the bolt. Becase there is a prying effect that the plate exerts on the bolt due to bending of the plate.

Once the force in the bolt is determined then using the properties of the bolt the stress and utilistaion can be found.

# In plane (shear loading) methods

## Elastic Method (Bolts)

By assuming the force in each bolt is proportional to its deformation, we can use the principle of superposition to calculate the forces in the bolt group. This allows us to split the load into a concentric load and an eccentric load (moment).

### Assumptions

* The deformation of each bolt is proportional to the force in that bolt (bolt group is elastic).
* The connected plate is assumed rigid (no prying in this step).
* Superposition is valid (concentric + eccentric effects can be added linearly).

### Method

Split the load into:

* A **concentric load** through the centroid of the bolt group, and
* A **bending moment** about the centroid due to eccentricity.

Let the bolt group have $n$ bolts at coordinates $(y_i, z_i)$ measured from the centroid, and let:

$$
r_i = \sqrt{y_i^2 + z_i^2}
$$

$$
\sum r^2 = \sum_{i=1}^{n} (y_i^2 + z_i^2)
$$

---

#### Concentric Load

For a concentric shear load $V$ acting through the centroid, the average shear per bolt is:

$$
V_{p} = \frac{V}{n}
$$

* ($V_{p}$): Shear force per bolt due to concentric load (N)
* ($V$): Applied shear load (N)
* ($n$): Number of bolts in the group

If there is an axial tension $P$ acting through the centroid, the uniform tension per bolt is:

$$
T_{p} = \frac{P}{n}
$$

* ($T_{p}$): Tension per bolt due to concentric axial load (N)
* ($P$): Applied axial tension (N)

---

#### Bending Moment (Eccentric Shear / Axial)

If the line of action of the load does not pass through the centroid, an additional **moment** is introduced:

$$
M = V e_V + P e_P
$$

where $e_V$ and $e_P$ are the eccentricities of shear and axial loads relative to the centroid.

The bolts resist this moment by developing forces proportional to their distance from the centroid.

For a **shear-type moment** (rotation in the plane of the bolt group), the additional force in bolt $i$ due to moment $M$ is:

$$
F_{m,i} = \frac{M r_i}{\sum r^2}
$$

* ($F_{m,i}$): Resultant force in bolt $i$ due to moment (N)
* ($M$): Moment about the centroid (N·mm)
* ($r_i$): Distance from centroid to bolt $i$ (mm)
* ($\sum r^2$): Polar “second moment” of the bolt pattern (mm²)

The direction of $F_{m,i}$ is tangential to the circle about the centroid (perpendicular to the radius). Its components are:

$$
F_{my,i} = -F_{m,i} \frac{z_i}{r_i}
$$
$$
F_{mz,i} = F_{m,i} \frac{y_i}{r_i}
$$

* ($F_{my,i}$): y-component of force in bolt $i$ due to moment (N)
* ($F_{mz,i}$): z-component of force in bolt $i$ due to moment (N)

If the moment produces tension (e.g. flange in bending), we can similarly distribute **tension** from moment:

$$
T_{m,i} = \frac{M_t r_i}{\sum r^2}
$$

* ($T_{m,i}$): Tension in bolt $i$ due to tensile moment $M_t$ (N)

Only bolts on the tension side are considered effective in resisting $M_t$; compression-side bolts may be ignored for tension.

---

#### Resultant Bolt Forces

For each bolt $i$:

* Shear components:
  $$
  V_{iy} = V_{p,y} + F_{my,i}
  $$
  $$
  V_{iz} = V_{p,z} + F_{mz,i}
  $$

  where $V_{p,y}$ and $V_{p,z}$ are the components of the uniform shear per bolt.

* Total shear magnitude:
  $$
  V_i = \sqrt{V_{iy}^2 + V_{iz}^2}
  $$

* Total tension:
  $$
  T_i = T_{p} + T_{m,i}
  $$



---

## Instantaneous Center of Rotation Method (Bolts)

For bolts, the ICR method uses **curved load–deformation relationships** for each bolt, instead of assuming a linear elastic spring. It accounts for **nonlinear bearing and slip behavior** and allows **plastic redistribution** of forces in the bolt group.

### Assumptions

* Bolt forces are related to deformation via a **nonlinear** curve (based on tests, as in Crawford–Kulak).
* The bolt group rotates about an **instantaneous center of rotation (ICR)** under the applied load.
* One bolt reaches its deformation capacity first and thus governs the rotation.
* The connected plate is treated as rigid at bolt locations (prying is handled separately if needed).

### Curved Load–Deformation Relationship

For each bolt, the reaction force $F_b$ is a nonlinear function of its deformation $\Delta$:

* The curve starts with low stiffness (slip / clearance),
* Then increases as the bolt bears against the hole,
* Then approaches a maximum / ultimate reaction at a deformation $\Delta_u$.

A generic normalized form (analogous in spirit to the weld case) is:

$$
F_b = F_{u} \cdot \phi(p)
$$

where:

* ($F_{u}$): Ultimate force capacity of the bolt (shear or combined shear/bearing)
* ($p = \dfrac{\Delta}{\Delta_m}$): Normalized deformation
* ($\Delta_m$): Deformation at which the bolt reaches its peak effective stiffness / maximum design load (model parameter)
* ($\phi(p)$): Empirical function capturing the nonlinear stiffness (e.g. increasing up to $p \approx 1$, then plateauing/softening)

$\Delta_m$ and $\Delta_u$ (ultimate deformation) depend on bolt diameter, plate thickness, edge distance, and hole geometry and are obtained from the adopted bolt model (e.g. Crawford–Kulak).

---

### Rotation and Bolt Deformation

If the group rotates about a trial ICR with a small rotation $\omega$, the deformation at bolt $i$ is:

$$
\Delta_i = \omega \cdot c_i
$$

where:

* $(x_i, y_i)$: Coordinates of bolt $i$
* $(x_{IC}, y_{IC})$: Coordinates of the trial ICR
* $c_i$: Distance from ICR to bolt $i$:
  $$
  c_i = \sqrt{(x_i - x_{IC})^2 + (y_i - y_{IC})^2}
  $$

Each bolt also has an ultimate deformation capacity $\Delta_{u,i}$ (from the bolt–plate bearing model).

---

### Governing Deformation Ratio

For each bolt, the rotation at which that bolt reaches its ultimate deformation is:

$$
\omega_i = \frac{\Delta_{u,i}}{c_i}
$$

The bolt with the **smallest** $\omega_i$ reaches its deformation capacity first and therefore **governs the rotation** of the group.

Define:

$$
\omega_{\min} = \min_i \left( \frac{\Delta_{u,i}}{c_i} \right)
$$

This governs the deformation pattern in the group at ultimate.

---

### Steps

1. **Initialize (Choose ICR):**
   Start with a guess for the instantaneous center of rotation (e.g., on a line perpendicular to the applied load through the centroid of the bolt group).

2. **Geometry for Each Bolt:**
  For each bolt $i$, compute:

   * Distance from ICR:
     $$
     c_i = \sqrt{(x_i - x_{IC})^2 + (y_i - y_{IC})^2}
     $$
   * Direction from ICR to bolt:
     $$
     \hat{e}_{ri} = \left( \frac{x_i - x_{IC}}{c_i}, \frac{y_i - y_{IC}}{c_i} \right)
     $$

3. **Determine Governing Rotation:**

  * From the chosen bolt deformation model, obtain $\Delta_{u,i}$ for each bolt.
   * Compute the deformation ratio:
     $$
     \frac{\Delta_{u,i}}{c_i}
     $$
   * Identify the bolt with the minimum value:
     $$
     \left( \frac{\Delta_u}{c} \right)_{\min} = \min_i \left( \frac{\Delta_{u,i}}{c_i} \right)
     $$
   * Set the group rotation at ultimate:
     $$
     \omega = \left( \frac{\Delta_u}{c} \right)_{\min}
     $$

4. **Calculate Forces in Each Bolt:**

  For each bolt $i$:

   1. **Deformation:**
      $$
      \Delta_i = \omega \cdot c_i
      $$

   2. **Normalized Deformation:**
      $$
      p_i = \frac{\Delta_i}{\Delta_{m,i}}
      $$
      where $\Delta_{m,i}$ is the deformation corresponding to maximum effective load for bolt $i$.

   3. **Bolt Force (from nonlinear curve):**
      $$
      F_{b,i} = F_{u,i} \cdot \phi(p_i)
      $$
      (specific form of $\phi(p)$ depends on the chosen model; analogous in role to $[p(1.9 - 0.9p)]^{0.3}$ in your weld expression, but calibrated for bolts).

      The crawford–Kulak model is: $$F_{b,i} = F_{u,i}(1-e^{-10 p_i})^{0.55}$$

   4. **Direction and Components:**
      The bolt force acts along the local deformation direction (tangential to rotation). For in-plane shear:
      $$
      F_{ix} = F_{b,i} \cdot \left(\frac{-(y_i - y_{IC})}{c_i}\right)
      $$
      $$
      F_{iy} = F_{b,i} \cdot \left(\frac{(x_i - x_{IC})}{c_i}\right)
      $$

      If the model includes bolt tension, the total bolt force may be resolved into shear and tension components depending on connection geometry.

   5. **Moment Contribution About the ICR:**
      $$
      M_{ic,i} = F_{ix}(y_i - y_{IC}) - F_{iy}(x_i - x_{IC})
      $$

5. **Check Equilibrium:**

   Sum forces and moments from all bolts and compare with applied loads:

   * Force equilibrium:
     $$
     \sum F_{ix} \approx V_x,\quad \sum F_{iy} \approx V_y
     $$
   * Moment equilibrium about the ICR:
     $$
     \sum M_{ic,i} \approx M_{\text{applied}}
     $$

   If the sums do **not** match within tolerance:

  * Adjust the location of the instantaneous center of rotation $(x_{IC}, y_{IC})$ along the search line (typically using a numerical method such as Newton–Raphson).
   * Repeat from Step 2.

6. **Strength Check:**
   Once equilibrium is achieved for a given ICR and deformation pattern:

   * For each bolt, compute:

     * Shear $V_i$ (from $F_{ix}, F_{iy}$)
     * Tension $T_i$ (if relevant)



# Out of Plane (Tension Loading) Methods


### 1) Define the action and geometry

* Determine the applied **out-of-plane design moment** $M_o^*$ (and **out-of-plane shear** $V_o^*$ if present).
* Identify bolt row coordinates (row distances measured normal to the support face).

### 2) Identify tension vs compression region

* Decide which side of the plate is in **compression (bearing/contact)** and which bolt rows are in **tension**.

**Important (matches code behavior):**
- The solver computes **signed** moment-induced axial contributions: bolts on the compression side of a moment receive **negative** axial contributions from that moment.
- After **summing** all axial contributions (direct $F_x$ + $M_y$ + $M_z$), the reported per-bolt axial force is **clamped** to tension-only:
  - If $F_{x,\text{bolt}} < 0$, it is set to $0$.

### 3) Assume a neutral axis (NA) location

Use a practical assumption per handbook guidance (because exact NA is hard to define): 

* Conservative: NA at bolt-group centroid line, or
* Empirical: NA at (d/6) from the bottom edge of plate depth (d).

**Sign convention used in the code (per axis):**
- For $M_y$: the distribution varies with bolt **z** coordinate over the plate range $[z_{\min}, z_{\max}]$.
  - If $M_y > 0$, the compression edge is $z_{\min}$; if $M_y < 0$, the compression edge is $z_{\max}$.
- For $M_z$: the distribution varies with bolt **y** coordinate over the plate range $[y_{\min}, y_{\max}]$.
  - If $M_z > 0$, the compression edge is $y_{\min}$; if $M_z < 0$, the compression edge is $y_{\max}$.

Define:

* $y_i$ = distance from NA to each tension bolt row $i$
* $y_1$ = distance from NA to the **farthest** (critical) tension row

### 4) Set compression-resultant lever arm

Define $y_c$ = distance from NA to the resultant compression force $C$ (i.e., where the compression block acts). This is part of the handbook equilibrium form. 

### 5) Solve for the peak tension row force (T_1) by equilibrium

Using moment equilibrium about the NA (handbook form):
$$\sum T_i y_i + C y_c = M_o^*$$
$$\sum T_i = C$$

Eliminating $C$ gives:
$$T_1=\frac{M_o^*}{\sum\left[y_i\left(\frac{y_i}{y_1}-\frac{y_c}{y_1}\right)\right]}$$

(That denominator sum is taken over the **tension-side** bolt rows.) 

Convert to **per-bolt** maximum tension in the critical row:
$$T_{\text{bolt,max}}=\frac{T_1}{n_1}$$

where $n_1$ is the number of bolts in the critical row. 

### 6) Distribute tensions to the other rows (now that (T_1) is known)

Assume a linear (triangular) tension distribution from NA to the farthest row:
$$T_i = T_1\frac{y_i}{y_1}$$

Then per-bolt in row $i$: $T_{\text{bolt},i} = T_i/n_i$.


### 7) Biaxial Bending (Both My and Mz)

When both out-of-plane moments are present, the neutral-axis method is applied independently to each axis, and the **signed** contributions are summed before enforcing “no compression in bolts”:

1. Calculate tension contribution from $M_y$ using the above method (varies with bolt z-coordinate)
2. Calculate tension contribution from $M_z$ using the above method (varies with bolt y-coordinate)  
3. Add direct tension from $F_x$ (if present)
4. Sum all contributions: $F_{x,\text{bolt}} = F_{x,\text{direct}} + F_{x,M_y} + F_{x,M_z}$
5. Apply compression rule: if total is negative, set to zero

**How the code models “compression side” for a moment (per axis):**
- The handbook distribution is solved using **tension-side** bolt rows only (to get the peak row force $T_1$).
- The compression side is then assigned a **negative** linear extension with the same slope (triangular distribution mirrored about the NA), so that compression from one axis can cancel tension from the other axis during summation.

- A bolt below NA_y (compression zone for $M_z$) gets a negative contribution from $M_z$
- Same bolt above NA_z (tension zone for $M_y$) gets a positive contribution from $M_y$  
- The negative contribution can reduce or eliminate the positive contribution
- Only after summing all contributions is the final clamp applied (negative → 0)

This represents the true biaxial bending behavior where compression effects can counteract tension effects.




## Considering prying (from steel construction handbook 7th edition)

if these conditions apply then prying needs to be considered (conservatively this means increasing the tension by 33%):
- Bolt is in tension
- Medium and thick plates used


Prying can be ignored if
- Plates are stiffened by gussets
- Plates are thin
- Plates are relatively rigid

To minimise prying
- Space bolts at least 90mm
- Use an end plate thickness of at least 1.25 times the bolt diameter


# Weld comparison

That’s the bolt version of your weld text:

* Elastic method → bolt forces instead of weld stress per unit length.
* ICR method → nonlinear force–deformation per bolt instead of nonlinear stress–deformation per weld segment.

Becuse we have not determined the stress we need one final step

