import numpy as np
import math
from connecty.bolt.solvers.icr import _calculate_final_state

def main():
    # 3x3 grid, 80mm spacing
    rows, cols = 3, 3
    spacing = 80
    coords = []
    for i in range(rows):
        y = (i - (rows-1)/2) * spacing
        for j in range(cols):
            x = (j - (cols-1)/2) * spacing
            coords.append([x, y])
    
    bolt_coords = np.array(coords, dtype=float)
    
    Fx = 10000.0
    Fy = 0.0
    Mz = 200000.0
    x_loc = 0.0
    y_loc = 0.0
    
    # Defaults
    mu = 10.0
    lam = 0.55
    delta_max = 8.64
    
    centroid = np.mean(bolt_coords, axis=0)
    Cx, Cy = float(centroid[0]), float(centroid[1])
    Mz_centroid = Mz + (x_loc - Cx) * Fy - (y_loc - Cy) * Fx
    P = math.hypot(Fx, Fy)
    L_char = float(np.max(np.linalg.norm(bolt_coords - np.array([Cx, Cy]), axis=1)))
    force_scale = max(P, 1.0)
    moment_scale = max(abs(Mz_centroid), 1.0)

    def moment_about_centroid(bfx, bfy):
        r = bolt_coords - np.array([Cx, Cy], dtype=float)
        return float(np.sum(r[:, 0] * bfy - r[:, 1] * bfx))
    
    def objective_xy(xy):
        x_ic, y_ic = float(xy[0]), float(xy[1])
        bfx, bfy, _ = _calculate_final_state(
            bolt_coords, x_ic, y_ic, Fx, Fy, Mz_centroid, mu, lam, delta_max
        )
        dFx = float(np.sum(bfx) - Fx)
        dFy = float(np.sum(bfy) - Fy)
        dMz = float(moment_about_centroid(bfx, bfy) - Mz_centroid)
        
        return (dFx / force_scale) ** 2 + (dFy / force_scale) ** 2 + (dMz / (moment_scale / max(L_char, 1e-9))) ** 2

    # Elastic estimate
    J = np.sum(bolt_coords[:,0]**2 + bolt_coords[:,1]**2)
    N = len(bolt_coords)
    e = abs(Mz_centroid) / P
    r_est = J / (N * e)
    print(f"Estimated ICR radius: {r_est}")
    
    print(f"Objective at (0, {r_est}): {objective_xy([0, r_est])}")
    print(f"Objective at (0, -{r_est}): {objective_xy([0, -r_est])}")

if __name__ == "__main__":
    main()
