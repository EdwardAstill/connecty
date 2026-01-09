
Your refined plan is very close. The key to making it work is realizing that you don't scale the forces until the *very* end. During the iteration, you are simply moving the "line" (Neutral Axis) until the internal physics balances out.

Here are the corrected, simple steps for the **Strain Compatibility Method**:
Basically:
Your targets are the ratio and magnitude of the moments about the origin.

Assume a theta

find c (a neutral axis for a given angle) that balances the forces (that is applied force = -1 * sum of forces),
 he relative forces are proportional to the distance from the neutral axis and so can be determined.
see if the forces balance if they aren't then move it.

once you have a neutral axis determine the moments about the origin, compare the ratio of these to your target, if they are not then you need to chagne theta

once the ratio matches scale up the forces so that the moments about the origin match your target.

In depth:

### 1. Setup the Geometry

* **Plate Grid:** Create a grid of points  representing the plate. Each point has an area .
* **Bolts:** Define bolt locations  and their areas .
* **Coordinate System:** Ensure all coordinates are relative to the plate center (or your load application point).

### 2. Set Initial Neutral Axis (NA)

* **The Angle ():** Start with an angle **perpendicular** to the resultant moment vector. (If the moment is purely about the X-axis, the NA is a horizontal line).
* **The Depth ():** Pick an initial distance from the origin to the NA.

### 3. Calculate Relative Strains

For every point (grid cells and bolts), calculate the perpendicular distance  to the NA:

* Points on one side of the NA are **Compression** (negative).
* Points on the other side are **Tension** (positive).
* **The Physics:** Only grid cells in the compression zone provide force. Only bolts in the tension zone provide force. (Standard assumption: concrete/grout doesn't take tension).

### 4. Check Axial Equilibrium (The First "Match")

* Calculate the total Force: .
* *Note: Use  for cells and  for bolts.*


* **The Goal:** The total sum of forces must equal your applied axial load  (usually  for pure bending).
* **Iterate:** Adjust the distance  (move the line back and forth) until this balance is met.

### 5. Check Moment Direction (The Second "Match")

Now that your axial forces balance, calculate the internal moments:

* 
* 
* **The Goal:** The ratio  must match the ratio of your applied moments .
* **Iterate:** If the ratios don't match, **rotate the angle ** and go back to Step 4.

### 6. Final Scaling

Once you have found the  that satisfies both the axial balance and the moment ratio:

* Calculate the magnitude of your internal moment.
* **Scale all forces** by the ratio: .
* This gives you the final, real-world forces in every bolt and every compression cell.

---

### Important Corrections to your Draft:

1. **Angle:** The Neutral Axis is **perpendicular** to the direction you want the plate to lean.
2. **No Error for "No Bolts":** If no bolts are above the NA, it doesn't always mean an error—it might mean the entire plate is in compression (if you have a high axial load ). However, for pure bending, you are correct: you need bolts in tension to balance the system.
3. **The "Origin":** You don't match the "moment of the below cells" to the "moment of the above cells" directly. You match the **sum of all forces to the applied axial load**. The moments are a byproduct of that balanced state.


```text
# INPUTS: 
# bolts = list of (x, y, area)
# plate_cells = list of (x, y, area) 
# M_target = (Mx, My)
# P_target = applied axial load (usually 0)

# 1. SETUP
target_ratio = My / Mx
target_magnitude = sqrt(Mx^2 + My^2)

# 2. OUTER LOOP: Iterate through possible Neutral Axis angles (theta)
for theta in range(0, 360, step=1):
    
    # 3. INNER LOOP: Find the depth 'c' that satisfies Axial Equilibrium (Sum of F = P)
    # We use a binary search or linear scan for 'c'
    for c in search_range_across_plate:
        total_force = 0
        
        # Calculate forces in Bolts (Tension side)
        for b in bolts:
            dist = distance_from_line(b.x, b.y, theta, c)
            if dist > 0: # Tension
                force = dist * b.area * E_steel
                total_force += force
        
        # Calculate forces in Plate Cells (Compression side)
        for cell in plate_cells:
            dist = distance_from_line(cell.x, cell.y, theta, c)
            if dist < 0: # Compression
                force = dist * cell.area * E_steel
                total_force += force # (dist is negative, so this subtracts)
        
        # Check if axial forces are balanced
        if abs(total_force - P_target) < tolerance:
            # We found the correct 'c' for this 'theta'
            break 

    # 4. CALCULATE INTERNAL MOMENTS for this balanced (theta, c)
    Mx_int = sum(all_forces * y_coordinates)
    My_int = sum(all_forces * x_coordinates)
    current_ratio = My_int / Mx_int
    
    # 5. CHECK MOMENT DIRECTION
    if abs(current_ratio - target_ratio) < tolerance:
        # SUCCESS: We found the actual Neutral Axis!
        found_theta = theta
        found_c = c
        break

# 6. FINAL SCALING
# At this point, the NA is in the right place, but magnitudes are relative
current_magnitude = sqrt(Mx_int^2 + My_int^2)
scale_factor = target_magnitude / current_magnitude

final_bolt_forces = relative_bolt_forces * scale_factor
final_plate_pressure = relative_plate_forces * scale_factor
```




