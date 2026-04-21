### Goals
- **Consistent model**: `Connection` + `Load` → `Result` → `CheckResult`
- **Unit-agnostic**: Connecty never assumes a unit system. Outputs are in the same derived units as inputs.
  - If inputs are force + length, then stresses are in (force / length²).
  - If you input stresses, you get forces back in (stress · length²).
- **Bolts are 2D** (planar bolt layouts only).
- **Plate is bolt-only** and is used for:
  - Out-of-plane effects (tension with neutral axis analysis)
  - Bearing and tear-out checks
  - Slip checks (for pretensioned connections)

---

## Shared

### `Load`
Single load object used by both bolts and welds.

- **Fields**: `Fx, Fy, Fz, Mx, My, Mz: float`, `location: tuple[float, float, float]`
- **Coordinate system**:
  - Bolts work in x-y plane (local coordinates):
    - `Fx` = axial force (out-of-plane, + = tension)
    - `Fy` = shear in y-direction (vertical)
    - `Fz` = shear in z-direction (horizontal)
    - `Mx` = torsional moment about x-axis (+ = CCW from +x)
    - `My` = bending moment about y-axis (+ = tension on +z side)
    - `Mz` = bending moment about z-axis (+ = tension on +y side)
- **Methods**:
  - `equivalent_at(location) -> Load`: Returns equivalent load at new location (forces unchanged; moments transferred).
  - `at(x, y, z) -> tuple`: Calculate equivalent forces and moments at point (x, y, z).
  - `get_moments_about(x, y, z) -> tuple`: Calculate total moments about point (x, y, z).
  - `from_components(axial, shear_y, shear_z, torsion, moment_y, moment_z, at) -> Load`: Alternative constructor with descriptive names.
- **Properties**:
  - `x_loc`, `y_loc`, `z_loc`: Load application point coordinates.
  - `shear_magnitude`: Magnitude of in-plane shear (√(Fy² + Fz²)).
  - `total_force_magnitude`: Magnitude of total force vector (√(Fx² + Fy² + Fz²)).

---

## Bolts

### `BoltLayout`
Bolt positions in the y-z cross-section plane. **2D only**.

- **Fields**: `points: list[tuple[float, float]]` — (y, z) coordinates
- **Classmethods**:
  - `from_pattern(*, rows, cols, spacing_y, spacing_z, offset_y=0, offset_z=0) -> BoltLayout`: Rectangular grid, centred at offset.
  - `from_circular(*, radius, n=6, center=(0,0), start_angle=0) -> BoltLayout`: Circular bolt pattern.
- **Properties**: `n: int`, `Cy: float`, `Cz: float`

### `BoltGroup`
Internal grouping of `Bolt` objects created by `BoltConnection`. Accessible via `connection.bolt_group`.

- **Fields**:
  - `bolts: list[Bolt]` - Individual bolt objects.
- **Properties**:
  - `n: int` - Number of bolts.
  - `points: list[tuple[float, float]]` - Bolt positions (y, z).
  - `centroid: tuple[float, float]` - Group centroid (Cy, Cz).
  - `Cy, Cz: float` - Centroid coordinates.
  - `Ip: float` - Polar moment of inertia about centroid.
- **Classmethods**:
  - `create(layout, params) -> BoltGroup`: Create from a `BoltLayout` and `BoltParams`.

### `Bolt`
Individual bolt in the group. Normally accessed via `connection.bolt_group.bolts`.

- **Fields**:
  - `params: BoltParams` - Bolt material and size.
  - `position: tuple[float, float]` - Bolt location (y, z).
  - `index: int | None` - Bolt index.
  - `k: float` - Axial stiffness (set by `BoltConnection` from grip length).
- **Properties**: `y: float`, `z: float`

### `BoltParams`
Bolt material properties and size.

- **Fields**:
  - `diameter: float` - Bolt diameter.
  - `grade: str | None` - Bolt grade (e.g., "A325", "A490", "8.8", "10.9"). **Required**.
  - `threaded_in_shear_plane: bool` (default `True`) - Whether threads are in shear plane.
  - `E: float` (default 210000.0) - Modulus of elasticity (user units, e.g., N/mm² for steel).
- **Calculated fields** (set in `__post_init__`):
  - `fy: float` - Yield strength (from grade lookup).
  - `fu: float` - Ultimate strength (from grade lookup).
  - `area: float` - Bolt cross-section area.
  - `Fnt: float` - AISC nominal tension stress.
  - `Fnv: float` - AISC nominal shear stress (depends on `threaded_in_shear_plane`).
  - `Fnv_N: float` - AISC shear stress (threads not excluded from shear).
  - `Fnv_X: float` - AISC shear stress (threads excluded from shear).
  - `T_b: float` - AISC pretension force.
  - `stiffness: float` - Bolt axial stiffness (set by `BoltConnection` based on grip length).
- **Methods**:
  - `recalculate() -> None`: Recalculate all derived properties (called after grade/thread changes).
  - `update_shear_plane_threads(included: bool) -> None`: Update thread status and recalculate properties.

### `Plate` (bolt-only)

- **Constructor**: Two options:
  1. Direct: `Plate(corner_a, corner_b, thickness, fu, ...)`
  2. Convenience: `Plate.from_dimensions(width, height, thickness, fu, center=...)`
- **Fields**:
  - `corner_a: tuple[float, float]` - First corner (y, z) in bolt-group plane.
  - `corner_b: tuple[float, float]` - Second corner (y, z) in bolt-group plane.
  - `thickness: float` - Plate thickness (in direction perpendicular to bolt plane).
  - `fu: float` - Ultimate tensile strength.
  - `fy: float | None` - Yield strength (optional).
  - `hole_type: Literal["standard", "oversize", "short_slotted", "long_slotted"]` (default "standard").
  - `hole_orientation: float | None` - Hole slot orientation angle in degrees (default None).
  - `surface_class: Literal["A", "B"] | None` (default None) - Surface preparation class (affects slip coefficient).
  - `slip_coefficient: float | None` - Slip coefficient (derived from `surface_class` if None: A→0.30, B→0.50).
- **Properties**:
  - `y_min, y_max, z_min, z_max: float` - Plate extent boundaries (plate is in the y-z plane).
  - `depth_y, depth_z: float` - Plate dimensions in each axis.
  - `width: float` - Size in z-direction (same as `depth_z`).
  - `height: float` - Size in y-direction (same as `depth_y`).
  - `center: tuple[float, float]` - Plate centre (y, z).



### `BoltConnection`
Combines bolt layout, bolt parameters, and plate geometry for analysis.

- **Fields**:
  - `layout: BoltLayout` - Bolt positions.
  - `bolt: BoltParams` - Bolt material and size.
  - `plate: Plate` - Connection plate.
  - `n_shear_planes: int` - Number of shear planes.
  - `threaded_in_shear_plane: bool | None` - Override thread status on all bolts (optional).
- **Computed field**: `bolt_group: BoltGroup` — created automatically from `layout` and `bolt`.
- **Methods**:
  - `analyze(load, shear_method="elastic", tension_method="conservative") -> LoadedBoltConnection`
    - `shear_method`: `"elastic"` or `"icr"`.
    - `tension_method`: `"conservative"` (NA at centroid) or `"accurate"` (d/6 NA approximation).
    - Returns `LoadedBoltConnection` with distributed forces.

### `LoadedBoltConnection`
Result of a bolt group analysis. Contains distributed forces and analysis metadata.

- **Fields**:
  - `bolt_connection: BoltConnection` - Reference to original connection.
  - `load: Load` - Applied load.
  - `shear_method: Literal["elastic", "icr"]` - Shear analysis method used.
  - `icr_point: tuple[float, float] | None` - Instantaneous center of rotation (only for ICR method).
  - `neutral_axis: tuple[float, float] | None` - Neutral axis (theta, c) from tension analysis.
  - `plate_pressure: np.ndarray | None` - Pressure distribution on plate (for out-of-plane).
  - `plate_pressure_extent: tuple[float, float, float, float] | None` - Pressure grid bounds (xmin, xmax, ymin, ymax).
- **Methods**:
  - `to_bolt_forces() -> list[BoltForceResult]`: Per-bolt force results.
  - `check(standard, connection_type, fillers=0) -> dict`: AISC 360-22 checks.
    - `standard`: `"aisc"`.
    - `connection_type`: `"bearing"` or `"slip_critical"`.
    - `fillers`: number of filler plates (slip-critical only, affects h_f factor).
    - Returns dict with per-bolt lists: `"tension"`, `"shear"`, `"combined"`, `"bearing"`, `"tearout"`, `"governing"`; and group-level `"slip"` (slip-critical only).
  - `plot_shear(**kwargs)`: Plot shear force distribution.
  - `plot_tension(**kwargs)`: Plot tension force distribution.

### Check Results (AISC 360-22)
Dictionary returned by `LoadedBoltConnection.check()`.

- **Keys** (all contain lists indexed by bolt number):
  - `"shear"`: Utilization for shear failure (V_u / φ·R_n_v).
  - `"tension"`: Utilization for tensile failure (T_u / φ·R_n_t).
  - `"combined"`: Utilization for combined shear + tension (T_u / φ·R_n_t').
  - `"bearing"`: Utilization for bearing failure (V_u / φ·R_n_bearing).
  - `"tearout"`: Utilization for block/tearout shear (V_u / φ·R_n_tearout).
  - `"slip"`: Group-level slip utilization [U_slip] (pretensioned connections only).
- **Notes**:
  - Tension method (conservative vs. accurate) affects tension force distribution but not check calculations.
  - Prying effects are not currently modeled; use neutral axis tension solver for approximate out-of-plane behavior.

---

## Welds

### `WeldParams`
Defines weld type/size and strength source.

- **Fields**:
  - `type: Literal["fillet","cjp","pjp","plug","slot"]`
  - `leg: float | None`
  - `throat: float | None`  # derived if needed/possible
  - `electrode: str | None`
  - `F_EXX: float | None`  # if not provided, derive from electrode (if given)

### `WeldConnection`
- **Fields**:
  - `params: WeldParams`
  - `path: Geometry/Path object` (contours need not be closed)
  - `base_metal: WeldBaseMetal | None` (only if checks require it)
  - flags like `is_double_fillet`, `is_rect_hss_end_connection` (as currently supported)
- **Method**:
  - `analyze(load: Load, *, method: Literal["elastic","icr"], discretization: int = 200) -> WeldResult`

### `WeldResult`
- **Fields**:
  - `connection: WeldConnection`
  - `load: Load`
  - `method: Literal["elastic","icr"]`
  - `discretization: int` (default 200)
- **Properties**: `max_stress`, `min_stress`, `mean_stress`, `analysis` (underlying `LoadedWeld`)
- **Methods**:
  - `check(standard="aisc", F_EXX=None, enforce_max_fillet_size=True, conservative_k_ds=False) -> WeldCheckResult`

---

