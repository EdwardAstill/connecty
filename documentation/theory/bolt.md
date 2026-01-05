# Bolt Group Theory

## Overview
This note documents the theory used by `connecty` to compute **forces in each bolt**.

- **In-plane shear**: distributes $F_y$, $F_z$ and torsion $M_x$ across the bolt group using either:
  - the **elastic** method (linear), or
  - the **ICR** method (nonlinear Crawford–Kulak model).
- **Out-of-plane tension**: distributes axial demand $F_x$ and bending $M_y$, $M_z$ into per-bolt axial tension using a plate **neutral-axis** model.

## Coordinate system (matches `connecty.common.load.Load`)
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

### Instantaneous center of rotation (ICR) method (Crawford–Kulak)
Replaces the elastic spring assumption with a nonlinear load–deformation curve per bolt, and finds the **ICR** that satisfies equilibrium under $(F_y,F_z,M_x)$.

#### Crawford–Kulak curve (as implemented)
`connecty` uses:

$$
R = R_\text{ult}\left(1-e^{-\mu\rho}\right)^{\lambda},\qquad \rho=\frac{\Delta}{\Delta_\text{max}}
$$

Default parameters: $\mu=10$, $\lambda=0.55$, $\Delta_\text{max}=8.64$ (see `connecty.common.icr_solver.CrawfordKulakParams`).

> In the current implementation, $R_\text{ult}$ is used only as an internal scale and the final bolt forces are rescaled to match the applied shear resultant.

#### Geometry and force direction
For a trial ICR at $(y_{IC}, z_{IC})$:

$$
c_i=\sqrt{(y_i-y_{IC})^2+(z_i-z_{IC})^2}
$$

Tangential direction (CCW):

$$
\hat{t}_i=\left(-\frac{(z_i-z_{IC})}{c_i},\ \frac{(y_i-y_{IC})}{c_i}\right)
$$

$$
F_{y,i}=R_i\,\hat{t}_{y,i},\qquad F_{z,i}=R_i\,\hat{t}_{z,i}
$$

#### ICR search (as implemented)
- Let $P=\sqrt{F_y^2+F_z^2}$. If $P\approx0$ or $|M_x|\approx0$, the solver falls back to the elastic method.
- The ICR is searched along a line through the centroid perpendicular to the applied shear resultant.
- For each trial ICR, the solver:
  - assigns a **normalized** deformation $\Delta_i=c_i/c_{\max}$, where $c_{\max}=\max(c_i)$. This normalized deformation is used to get the *shape* of the force distribution; the final forces are scaled to satisfy equilibrium.
  - computes $R_i$ from the Crawford–Kulak curve,
  - forms a base ratio:

$$
P_\text{base}=\sqrt{\left(\sum F_{y,i}\right)^2+\left(\sum F_{z,i}\right)^2}
$$

$$
M_\text{base}=\sum\left[(y_i-y_{IC})F_{z,i}-(z_i-z_{IC})F_{y,i}\right]
$$

  - adjusts ICR distance until $M_\text{base}/P_\text{base}$ matches the applied target ratio $M_{x,\text{total}}/P$,
  - then scales all $(F_{y,i},F_{z,i})$ by $P/P_\text{base}$.

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

- In `connecty`'s AS 4100 check, prying is modeled by:

$$
T_u^\prime=T_u(1+\texttt{prying\_allowance})
$$

  where the default `prying_allowance` is `0.25` (+25%).
- **Important**: The 25% allowance is a user-defined default and serves as a rule-of-thumb preliminary estimate. AISC and AS 4100 have specific prying force equations based on plate geometry ($t_p$, $a$, $b$). For accurate design, verify that the applied prying allowance matches the corresponding yield-line or plastic hinge model equations based on your specific plate thickness and bolt gauge.
- Adjust this allowance as required for your detailing/handbook assumptions.

## Next step: bolt checks
Use the relevant design check (AISC / AS 4100) to convert bolt force demand into utilization and governing limit state.


