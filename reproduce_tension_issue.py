import numpy as np
from connecty.bolt.solvers.tension import solve_bolt_tension
from connecty.bolt.plate import Plate

def test_my_direction():
    # Plate 10 wide (z), 10 high (y)
    # z from -5 to 5. y from -5 to 5.
    plate = Plate.from_dimensions(width=10.0, height=10.0, thickness=1.0, fu=400.0)
    
    # Bolts on Z axis: one at left (-4), one at right (+4)
    bolts = np.array([
        [0.0, -4.0], # Bolt 0 (Left)
        [0.0, 4.0]   # Bolt 1 (Right)
    ])
    
    print(f"Plate z range: {plate.z_min} to {plate.z_max}")
    print(f"Bolts: {bolts}")
    
    # Apply My > 0
    # Thumb up. Right side (+Z) should move Into Page (+X).
    # If +X is Tension, then Right bolt should be in Tension.
    My = 100.0
    print(f"Applying My = {My}")
    
    tensions = solve_bolt_tension(
        bolt_coords=bolts,
        plate=plate,
        Fx=0.0,
        My=My,
        Mz=0.0,
        tension_method="conservative" # Simple NA at center? No, look at code
    )
    
    print(f"Tensions: {tensions}")
    
    if tensions[1] > tensions[0]:
        print("RESULT: Right bolt (+Z) has HIGHER tension.")
        if tensions[0] == 0:
            print("RESULT: Left bolt (-Z) is in compression (0 tension).")
    else:
        print("RESULT: Left bolt (-Z) has HIGHER tension.")

    # Check u_comp logic trace by inference
    # if My > 0, code sets u_comp = z_min (-5).
    # In conservative method: u_na = (z_min + z_max) / 2 = 0.
    # _distribute_moment:
    # u_na = 0. u_comp = -5.
    # u_na > u_comp is True.
    # is_tension = (rel_dist > 0) -> (z - 0 > 0) -> z > 0.
    # So z > 0 (Right) is tension.
    
    # Let's try accurate method too
    tensions_acc = solve_bolt_tension(
        bolt_coords=bolts,
        plate=plate,
        Fx=0.0,
        My=My,
        Mz=0.0,
        tension_method="accurate"
    )
    print(f"Tensions (accurate): {tensions_acc}")

if __name__ == "__main__":
    test_my_direction()
