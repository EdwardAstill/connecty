# Bolt Group Theory

## Overview
This note documents the theory used by `connecty` to compute **forces in each bolt**.

- **In-plane shear**: distributes $F_y$, $F_z$ and torsion $M_x$ across the bolt group using either:
  - the **elastic** method (linear), or
  - the **ICR** method (nonlinear Crawford–Kulak model).
- **Out-of-plane tension**: distributes axial demand $F_x$ and bending $M_y$, $M_z$ into per-bolt axial tension using a plate **neutral-axis** model.

## Coordinate system
- $x$: out-of-plane (axial), $+F_x$ = tension
- $y$: vertical in plane, $+F_y$ = up
- $z$: horizontal in plane, $+F_z$ = right
- $+M_x$: CCW when viewed from $+x$
- $+M_y$: causes tension on the $+z$ side
- $+M_z$: causes tension on the $+y$ side

## In-plane (shear: $F_y/F_z$ + $M_x$) methods

### Elastic method
Assumes bolt shear force is proportional to deformation (linear springs), and superposition applies.

**Given**
- $n$ bolts at $(y_i, z_i)$
- bolt-group centroid $(C_y, C_z)$

Define:

$$
\Delta y_i = y_i - C_y,\qquad \Delta z_i = z_i - C_z
$$

$$
I_p=\sum_{i=1}^{n}\left(\Delta y_i^2+\Delta z_i^2\right)
$$

Transfer the applied load to the centroid to obtain $M_{x,\text{total}}$ (this is the $M_x$ value returned by `Load.get_moments_about(0, Cy, Cz)`):

$$
M_{x,\text{total}} = M_x - F_z(y_\text{loc}-C_y) + F_y(z_\text{loc}-C_z)
$$

Direct shear per bolt:

$$
F_{y,p}=\frac{F_y}{n},\qquad F_{z,p}=\frac{F_z}{n}
$$

Moment-induced shear at bolt $i$:

$$
F_{y,m,i}=-\frac{M_{x,\text{total}}\Delta z_i}{I_p},\qquad
F_{z,m,i}= -\frac{M_{x,\text{total}}\Delta y_i}{I_p}
$$

Resultant per-bolt shear:

$$
F_{y,i}=F_{y,p}+F_{y,m,i},\qquad F_{z,i}=F_{z,p}+F_{z,m,i}
$$

$$
V_i=\sqrt{F_{y,i}^2+F_{z,i}^2}
$$

#### Code

```python
from math import sqrt
from typing import List, Dict


def elastic_in_plane_bolt_shear(
    bolts: List[Dict[str, float]],
    Fy: float,
    Fz: float,
    Mx: float,
    y_loc: float,
    z_loc: float,
):
    """
    Elastic in-plane bolt-group analysis (Fy/Fz + Mx).

    Parameters
    ----------
    bolts : list of dicts
        Each dict must contain {'y': float, 'z': float}
    Fy, Fz : float
        Applied in-plane shear forces
    Mx : float
        Applied moment about x-axis (about y_loc, z_loc)
    y_loc, z_loc : float
        Location where Fy and Fz act

    Returns
    -------
    results : dict
        Contains centroid, Ip, Mx_total, and per-bolt forces
    """

    n = len(bolts)
    if n == 0:
        raise ValueError("At least one bolt is required")

    # 1) Bolt-group centroid
    Cy = sum(b["y"] for b in bolts) / n
    Cz = sum(b["z"] for b in bolts) / n

    # 2) Offsets and polar second moment (Ip)
    Ip = 0.0
    for b in bolts:
        b["dy"] = b["y"] - Cy
        b["dz"] = b["z"] - Cz
        Ip += b["dy"] ** 2 + b["dz"] ** 2

    if Ip == 0.0:
        raise ValueError("Ip = 0 (all bolts coincident)")

    # 3) Transfer loads to centroid
    Mx_total = Mx - Fz * (y_loc - Cy) + Fy * (z_loc - Cz)

    # 4) Direct shear per bolt
    Fy_p = Fy / n
    Fz_p = Fz / n

    # 5) Moment-induced shear and resultants
    for b in bolts:
        Fy_m = -Mx_total * b["dz"] / Ip
        Fz_m = -Mx_total * b["dy"] / Ip

        b["Fy"] = Fy_p + Fy_m
        b["Fz"] = Fz_p + Fz_m
        b["V"] = sqrt(b["Fy"] ** 2 + b["Fz"] ** 2)

    return {
        "Cy": Cy,
        "Cz": Cz,
        "Ip": Ip,
        "Mx_total": Mx_total,
        "bolts": bolts,
    }

```
Below is a cleaner, more compact rewrite that keeps the full technical content but presents it in a more direct, engineering-focused way. Terminology is tightened, repetition removed, and the logic is made more linear.

---

### Instantaneous Center of Rotation (ICR) Method — In-Plane Bolt Groups

#### Purpose

The ICR method determines the force distribution in a bolt group subjected to general in-plane loading ((F_y, F_z, M_x)) **without assuming linear elastic bolt behavior**.

Unlike the elastic method—which assumes bolt force is proportional to distance from the centroid—the ICR method:

* assumes the connected plate undergoes a small rigid-body rotation,
* locates an **instantaneous center of rotation (ICR)** for that motion,
* assigns bolt forces using a **nonlinear load–deformation model**, and
* finds the ICR position that satisfies global equilibrium.

The method captures redistribution and concentration of force that occur beyond the elastic range.

---

#### Kinematic Assumption

* The bolt group rotates rigidly about the ICR.
* Bolt deformation is proportional to distance from the ICR.

For bolt $i$ at $(y_i, z_i)$ and ICR at $(y_{IC}, z_{IC})$:

$$c_i = \sqrt{(y_i - y_{IC})^2 + (z_i - z_{IC})^2}$$

Relative slip governs the force distribution; the absolute rotation magnitude is not required.

---

#### Bolt Force–Slip Relationship (Crawford–Kulak)

Each bolt's force magnitude is derived from a normalized slip:

$$\rho_i = \frac{\Delta_i}{\Delta_{\max}} \propto \frac{c_i}{c_{\max}}$$

$$R_i = R_\text{ult}\left(1 - e^{-\mu \rho_i}\right)^\lambda$$

Typical parameters:

* $\mu = 10$
* $\lambda = 0.55$
* $\Delta_{\max} = 8.64$

**Implementation note**

$R_\text{ult}$ is used only to define the *shape* of the force distribution (meaning the forces relative to one another).
After computing all $R_i$, forces are rescaled so that:

$$\sum F_{y,i} = F_y, \qquad \sum F_{z,i} = F_z$$

Thus, the nonlinear model controls *relative* bolt forces, not their absolute magnitude.

---

#### Force Direction at Each Bolt

Bolt forces act **tangentially** to the circle centered at the ICR.

For counter-clockwise rotation:

$$\hat{t}_i = \left( -\frac{z_i - z_{IC}}{c_i}, \frac{y_i - y_{IC}}{c_i} \right)$$

Force components:

$$F_{y,i} = R_i \hat{t}_{y,i}, \qquad F_{z,i} = R_i \hat{t}_{z,i}$$

Each bolt force is perpendicular to its radius from the ICR.

---

#### Equilibrium Conditions

The correct ICR location satisfies:

**Force equilibrium**

$$\sum_i F_{y,i} = F_y, \qquad \sum_i F_{z,i} = F_z$$

(enforced by rescaling)

**Moment equilibrium**

$$\sum_i \left(F_{y,i} z_i - F_{z,i} y_i\right) = M_x$$

Moment equilibrium is used to determine the ICR position.

---

#### Numerical Solution Strategy

The ICR location $(y_{IC}, z_{IC})$ is unknown and solved iteratively.

Define the residual:

$$r(y_{IC}, z_{IC}) = \sum_i \left(F_{y,i} z_i - F_{z,i} y_i\right) - M_x$$

A root-finding algorithm adjusts the ICR until $r \approx 0$.

---

#### Algorithm Overview

1. Assume an ICR location.
2. Compute bolt distances from the ICR.
3. Evaluate relative slips and bolt force magnitudes.
4. Assign tangential force directions.
5. Rescale forces to satisfy applied shear.
6. Compute resisting moment.
7. Update the ICR location to reduce moment error.
8. Iterate until convergence.

---

####  Pseudocode

```text
given:
    bolt coordinates (y[i], z[i])
    applied loads Fy, Fz, Mx
    Crawford–Kulak parameters (mu, lambda, Delta_max)

initialize:
    guess yIC, zIC

while not converged:

    # --- kinematics ---
    for each bolt i:
        c[i] = sqrt((y[i] - yIC)^2 + (z[i] - zIC)^2)

    c_max = max(c[i])

    # --- nonlinear bolt forces ---
    for each bolt i:
        rho[i] = (c[i] / c_max) * (c_max / Delta_max)
        R[i] = (1 - exp(-mu * rho[i]))^lambda

    # --- tangential directions ---
    for each bolt i:
        ty[i] = -(z[i] - zIC) / c[i]
        tz[i] =  (y[i] - yIC) / c[i]

        Fy_i[i] = R[i] * ty[i]
        Fz_i[i] = R[i] * tz[i]

    # --- rescale forces to match applied shear ---
    scale = sqrt(Fy^2 + Fz^2) / sqrt(sum(Fy_i)^2 + sum(Fz_i)^2)

    for each bolt i:
        Fy_i[i] *= scale
        Fz_i[i] *= scale

    # --- moment equilibrium ---
    M_resisting = sum(Fy_i[i] * z[i] - Fz_i[i] * y[i])

    residual = M_resisting - Mx

    update (yIC, zIC) to reduce residual
        (e.g. Newton, secant, or 2D search)

return:
    yIC, zIC
    bolt forces Fy_i, Fz_i
```

---




## Out-of-plane (bolt axial: $F_x$ + $M_y/M_z$) method

### Plate neutral-axis method
This method estimates per-bolt axial tension demand $F_x$ from direct axial force and out-of-plane bending of the plate (implemented in `connecty.bolt.solvers.tension.calculate_plate_bolt_tensions`).

#### 1) Transfer loads to the bolt-group centroid
Compute $(C_y,C_z)$, then evaluate:

$$
(M_{x,\text{total}}, M_{y,\text{total}}, M_{z,\text{total}})=\texttt{Load.get\_moments\_about}(0,C_y,C_z)
$$

#### 2) Direct axial tension
If $F_x>0$, distribute uniformly:

$$
F_{x,\text{direct}}=\frac{F_x}{n}
$$

#### 3) Apply moment distribution about each axis
The method is applied independently to $M_y$ and $M_z$ using a linear distribution about a neutral axis (NA).

Axis mapping (matches code):
- For $M_y$: distribution varies with bolt **$z$** over $[z_{\min}, z_{\max}]$
- For $M_z$: distribution varies with bolt **$y$** over $[y_{\min}, y_{\max}]$

Compression edge selection (matches `Load` sign convention and the solver):
- If $M_y>0$: compression edge is $z_{\min}$; if $M_y<0$: compression edge is $z_{\max}$
- If $M_z>0$: compression edge is $y_{\min}$; if $M_z<0$: compression edge is $y_{\max}$

Neutral axis location options (matches `tension_method`):
- **conservative**: NA at the bolt-group centroid coordinate in that axis
- **accurate**: NA at $d/6$ from the compression edge, where $d=u_{\max}-u_{\min}$ along that axis

Group bolts by rows of constant coordinate $u$ (where $u=z$ for $M_y$, $u=y$ for $M_z$). For row $i$:
- $y_i=\left|u_i-u_{NA}\right|$
- $y_1=\max(y_i)$ over tension-side rows
- $n_i$ = number of bolts in the row

Define the signed compression-resultant lever arm (negative toward compression):

$$
y_c=-\left|u_{\text{comp}}-u_{NA}\right|
$$

Solve for peak **row** force $T_1$ (sum over tension-side rows only):

$$
T_1=\frac{|M|}{\sum\left[y_i\left(\frac{y_i}{y_1}-\frac{y_c}{y_1}\right)\right]}
$$

Distribute to row $i$:

$$
T_i=T_1\frac{y_i}{y_1},\qquad T_{\text{bolt},i}=\frac{T_i}{n_i}
$$

Compression-side rows are assigned the same linear distribution with **negative** sign so biaxial effects can cancel.

#### 4) Sum and clamp to tension-only
The solver sums signed contributions and then clamps:

$$
F_{x,\text{bolt}}=F_{x,\text{direct}}+F_{x,M_y}+F_{x,M_z}
$$

$$
F_{x,\text{bolt}}=\max(F_{x,\text{bolt}},0)
$$

### Prying (design note)
The above methods return bolt axial demand. Prying can increase that demand depending on plate stiffness and detailing.

For now prying should be a true or false use input and applied in the design check.


$$
T_u^\prime=T_u(1+\text{prying allowance})
$$

  where the default `prying_allowance` is `0.25` (+25%).

- **Important**: The 25% allowance is a user-defined default and serves as a rule-of-thumb preliminary estimate. AISC and AS 4100 have specific prying force equations based on plate geometry ($t_p$, $a$, $b$). For accurate design, verify that the applied prying allowance matches the corresponding yield-line or plastic hinge model equations based on your specific plate thickness and bolt gauge.
- Adjust this allowance as required for your detailing/handbook assumptions.

In the future prying force should be calculated

#### Pseudocode

```text
FUNCTION plate_neutral_axis_bolt_tension(
    bolts,                  # list of bolts with fields: y, z
    Fx,                     # applied axial force (+ tension)
    Load,                   # load object with get_moments_about()
    tension_method          # "conservative" or "accurate"
):

    n = COUNT(bolts)
    REQUIRE n > 0

    # -------------------------------------------------
    # 1) Transfer loads to bolt-group centroid
    # -------------------------------------------------
    Cy = (SUM over bolts of bolt.y) / n
    Cz = (SUM over bolts of bolt.z) / n

    (Mx_tot, My_tot, Mz_tot) = Load.get_moments_about(0, Cy, Cz)

    # -------------------------------------------------
    # 2) Direct axial tension
    # -------------------------------------------------
    IF Fx > 0:
        Fx_direct = Fx / n
    ELSE:
        Fx_direct = 0

    # Initialize per-bolt axial force
    FOR each bolt IN bolts:
        bolt.Fx = Fx_direct

    # -------------------------------------------------
    # 3) Moment-induced axial forces (My and Mz)
    # -------------------------------------------------
    FOR each (M, axis) IN [(My_tot, "z"), (Mz_tot, "y")]:

        IF M == 0:
            CONTINUE

        # Coordinate selection
        IF axis == "z":
            u = [bolt.z for bolt in bolts]
        ELSE:  # axis == "y"
            u = [bolt.y for bolt in bolts]

        u_min = MIN(u)
        u_max = MAX(u)
        d = u_max - u_min

        # Compression edge (matches sign convention)
        IF (axis == "z" AND M > 0) OR (axis == "y" AND M > 0):
            u_comp = u_min
        ELSE:
            u_comp = u_max

        # Neutral axis location
        IF tension_method == "accurate":
            u_NA = u_comp + SIGN(M) * d / 6
        ELSE:  # "conservative"
            u_NA = (u_min + u_max) / 2

        # Group bolts by rows of constant u
        rows = GROUP bolts BY coordinate u

        # Distances from NA for tension-side rows only
        FOR each row IN rows:
            row.yi = ABS(row.u - u_NA)

        y1 = MAX(row.yi for row IN rows IF row.u is on tension side)

        # Signed compression lever arm
        y_c = -ABS(u_comp - u_NA)

        # Solve for peak row force
        denom = 0
        FOR each row IN rows IF row.u is on tension side:
            denom += row.yi * (row.yi / y1 - y_c / y1)

        T1 = ABS(M) / denom

        # Distribute to rows and bolts
        FOR each row IN rows:
            Ti = T1 * (row.yi / y1)

            # Compression side gets negative sign
            IF row.u is on compression side:
                Ti = -Ti

            FOR each bolt IN row:
                bolt.Fx += Ti / row.n_bolts

    # -------------------------------------------------
    # 4) Clamp to tension-only
    # -------------------------------------------------
    FOR each bolt IN bolts:
        bolt.Fx = MAX(bolt.Fx, 0)

    RETURN bolts
END FUNCTION

```

## Next step: bolt checks
Use the relevant design check (AISC / AS 4100) to convert bolt force demand into utilization and governing limit state.
