import math

def circular_layout(radius: float, center: tuple[float, float] = (0, 0), n: int = 6, start_angle: float = 0.0) -> list[tuple[float, float]]:
    """Create a circular layout of bolts.

    Args:
        radius (float): The radius of the bolt circle.
        center (tuple[float, float], optional): The (y, z) coordinates of the center. Defaults to (0, 0).
        n (int, optional): The number of bolts. Defaults to 6.
        start_angle (float, optional): The starting angle in degrees (counter-clockwise from positive y-axis). Defaults to 0.0.

    Returns:
        list[tuple[float, float]]: A list of (y, z) coordinates for the bolts.
    """
    bolts = []
    cy, cz = center
    start_rad = math.radians(start_angle)
    step = 2 * math.pi / n
    
    for i in range(n):
        angle = start_rad + i * step
        # y corresponds to x in standard trig, z corresponds to y in standard trig
        y = cy + radius * math.cos(angle)
        z = cz + radius * math.sin(angle)
        bolts.append((y, z))
    
    return bolts

def grid_layout(rows: int, cols: int, spacing_y: float, spacing_z: float, center: tuple[float, float] = (0, 0), rotate: float = 0.0) -> list[tuple[float, float]]:
    """Create a grid layout of bolts.

    Args:
        rows (int): The number of rows of bolts.
        cols (int): The number of columns of bolts.
        spacing_y (float): The spacing between bolts in the y-direction.
        spacing_z (float): The spacing between bolts in the z-direction.
        center (tuple[float, float], optional): The (y, z) coordinates of the center of the grid. Defaults to (0, 0).
        rotate (float, optional): Rotation angle of the grid in degrees (counter-clockwise). Defaults to 0.0.

    Returns:
        list[tuple[float, float]]: A list of (y, z) coordinates for the bolts.
    """
    bolts = []
    cy_center, cz_center = center
    rot_rad = math.radians(rotate)
    cos_r = math.cos(rot_rad)
    sin_r = math.sin(rot_rad)

    # Calculate grid dimensions to center it
    width = (cols - 1) * spacing_y if cols > 1 else 0.0
    height = (rows - 1) * spacing_z if rows > 1 else 0.0
    
    start_y = -width / 2.0
    start_z = -height / 2.0
    
    for r in range(rows):
        for c in range(cols):
            # Local coordinates in unrotated grid, centered at (0,0) relative to grid center
            local_y = start_y + c * spacing_y
            local_z = start_z + r * spacing_z
            
            # Rotate
            # y' = y cos - z sin
            # z' = y sin + z cos
            rot_y = local_y * cos_r - local_z * sin_r
            rot_z = local_y * sin_r + local_z * cos_r
            
            # Translate
            final_y = cy_center + rot_y
            final_z = cz_center + rot_z
            
            bolts.append((final_y, final_z))
            
    return bolts

def main():
    print("Circular Layout with 6 bolts at radius 10 centered at (0, 0) starting at 0 degrees:")
    print(circular_layout(radius=10, center=(0, 0), n=6, start_angle=0.0))
    print("Grid Layout with 6 bolts in a 2x3 grid spaced 10 units apart centered at (0, 0) rotated 45 degrees:")
    print(grid_layout(rows=2, cols=3, spacing_y=10, spacing_z=10, center=(0, 0), rotate=45.0))

if __name__ == "__main__":
    main()
