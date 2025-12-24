# Unified Bolt Check API Refactor

## Overview
Refactored the bolt check modules to use a **single unified `check_bolt_group()` function** that automatically routes to either AISC 360-22 or AS 4100 based on the bolt grade, eliminating the need for separate check methods.

## Changes

### 1. Unified `BoltDesignParams` Class
Both `aisc.py` and `as4100.py` now share a single `BoltDesignParams` class that contains all parameters for both standards.

**Key additions:**
- `grade: str` - Required field: "A325", "A490", "8.8", or "10.9"
- `is_aisc()` method - Returns True if AISC standard (A325/A490)
- `is_as4100()` method - Returns True if AS 4100 standard (8.8/10.9)
- All AISC-specific parameters (e.g., `slot_orientation`, `slip_class`, `fillers`)
- All AS 4100-specific parameters (e.g., `nn_shear_planes`, `nx_shear_planes`, `prying_allowance`)
- Common parameters used by both standards (`plate_fu`, `plate_thickness`, `tension_per_bolt`)

### 2. Single Public `check_bolt_group()` Function

**Location:** Both `aisc.py` and `as4100.py` (in `aisc.py` it's the primary entry point)

**Signature:**
```python
def check_bolt_group(
    result,
    design: BoltDesignParams,
    connection_type: str | None = None,
) -> BoltCheckResult
```

**Behavior:**
- Examines `design.grade` to determine the standard
- Automatically routes to the appropriate internal check function
- Routes to `_check_bolt_group_aisc()` for AISC grades
- Routes to `check_bolt_group_sd_handbook()` for AS 4100 grades
- Defaults `connection_type` to "bearing" if not specified

### 3. Internal Functions Renamed
- `check_bolt_group_aisc()` → `_check_bolt_group_aisc()` (private, for AISC implementation)
- `check_bolt_group_sd_handbook()` → Kept public but called internally by unified function

## Usage Example

### Before (Separate Methods)
```python
from connecty.bolt.checks.aisc import check_bolt_group_aisc, BoltDesignParams as AISCParams
from connecty.bolt.checks.as4100 import check_bolt_group_sd_handbook, BoltDesignParams as AS4100Params

# AISC check
aisc_design = AISCParams(
    grade="A325",
    plate_fu=450.0,
    plate_thickness=10.0,
    edge_distance_y=45.0,
)
aisc_result = check_bolt_group_aisc(connection, aisc_design)

# AS 4100 check
as4100_design = AS4100Params(
    grade="8.8",
    plate_fu=430.0,
    edge_distance=45.0,
)
as4100_result = check_bolt_group_sd_handbook(connection, as4100_design)
```

### After (Unified Method)
```python
from connecty.bolt.checks.aisc import check_bolt_group, BoltDesignParams

# AISC check - same unified function
aisc_design = BoltDesignParams(
    grade="A325",
    plate_fu=450.0,
    plate_thickness=10.0,
    edge_distance_y=45.0,
)
aisc_result = check_bolt_group(connection, aisc_design)

# AS 4100 check - same unified function
as4100_design = BoltDesignParams(
    grade="8.8",
    plate_fu=430.0,
    edge_distance=45.0,
)
as4100_result = check_bolt_group(connection, as4100_design)
```

## Benefits

1. **Single API Entry Point** - Users only need to import and use one function
2. **Automatic Standard Selection** - No need to remember which method to call for each standard
3. **Unified Parameter Class** - Consistent interface regardless of standard
4. **Backwards Compatible** - Internal functions still available if needed
5. **Reduced Cognitive Load** - Grade parameter drives behavior automatically

## Parameter Organization

### Always Required
- `grade`: "A325", "A490", "8.8", or "10.9"
- `plate_fu`: Material ultimate strength (MPa)
- `plate_thickness`: Material thickness (mm)

### AISC-Specific (if `grade` is A325 or A490)
- `edge_distance_y`, `edge_distance_z`: Clear distances to edges
- `threads_in_shear_plane`: Whether threads are in shear plane
- `hole_type`: "standard", "oversize", "short_slotted", "long_slotted"
- `slip_class`, `n_s`, `fillers`: For slip-critical connections

### AS 4100-Specific (if `grade` is 8.8 or 10.9)
- `edge_distance`: Clear distance to plate edge
- `plate_fy`: Material yield strength (MPa)
- `nn_shear_planes`, `nx_shear_planes`: Threaded and unthreaded shear planes
- `slip_coefficient`, `n_e`: For friction-type connections
- `prying_allowance`, `reduction_factor_kr`: AS 4100-specific factors

## Files Modified

1. **aisc.py**
   - Unified `BoltDesignParams` class
   - New `check_bolt_group()` function (router)
   - Renamed original function to `_check_bolt_group_aisc()`

2. **as4100.py**
   - Unified `BoltDesignParams` class (same as aisc.py)
   - New `check_bolt_group()` function (router)
   - Kept `check_bolt_group_sd_handbook()` as internal implementation
