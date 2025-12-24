"""
Plotting functions for bolt group visualization.

Provides plotting methods called by BoltResult.plot().
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import math
import numpy as np

if TYPE_CHECKING:
    from .bolt import ConnectionResult

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Circle
from matplotlib.lines import Line2D


def plot_bolt_result(
    result: "ConnectionResult",
    force: bool = True,
    bolt_forces: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | None = None,
    mode: str = "shear",
    force_unit: str = "N",
    length_unit: str = "mm",
) -> plt.Axes:
    """
    Plot bolt connection with plate and force distribution.
    
    Args:
        result: ConnectionResult from analysis
        force: Show applied load arrow
        bolt_forces: Show reaction vectors at each bolt (shear mode only)
        colorbar: Show force colorbar
        cmap: Matplotlib colormap name
        ax: Matplotlib axes (creates new if None)
        show: Display the plot
        save_path: Path to save figure (.svg recommended)
        mode: Visualization mode: "shear" (default) or "axial"
        force_unit: Unit label for forces (e.g., 'N', 'kN', 'lbf')
        length_unit: Unit label for lengths (e.g., 'mm', 'm', 'in')
        
    Returns:
        Matplotlib axes
    """
    # Validate mode
    if mode not in {"shear", "axial"}:
        raise ValueError("mode must be 'shear' or 'axial'")
    if mode == "axial" and result.shear_method == "icr":
        raise ValueError("Axial plotting is not supported for ICR results.")

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure
    
    bolt_group = result.bolt_group
    bolt_results_list = result.to_bolt_results()
    plate = result.connection.plate
    
    # Plot plate first (background)
    _plot_plate(ax, plate)
    
    # Choose value source based on mode
    if mode == "shear":
        values = [bf.shear for bf in bolt_results_list]
        color_label = f"Bolt Shear ({force_unit})"
        title_metric = "Max Shear"
        draw_arrows = True
    else:
        values = [bf.axial for bf in bolt_results_list]
        color_label = f"Bolt Axial ({force_unit}) [+tension/-compression]"
        title_metric = "Max |Axial|"
        draw_arrows = False

    # Get range for coloring
    force_min = min(values) if values else 0.0
    force_max = max(values) if values else 0.0

    # Standard normalization for both modes
    if force_max - force_min > 1e-12:
        norm = mcolors.Normalize(vmin=force_min, vmax=force_max)
    else:
        norm = mcolors.Normalize(vmin=0, vmax=max(force_max, 1.0))

    colormap = plt.get_cmap(cmap)
    
    # Bolt radius for visualization (proportional to actual diameter)
    bolt_diameter = bolt_group.parameters.diameter
    visual_radius = bolt_diameter / 2
    
    # Calculate arrow scale based on extent
    y_coords = [bf.y for bf in bolt_results_list]
    z_coords = [bf.z for bf in bolt_results_list]
    extent = max(
        max(y_coords) - min(y_coords) if y_coords else 1,
        max(z_coords) - min(z_coords) if z_coords else 1,
        bolt_diameter * 4
    )
    
    # Arrow scale: max selected metric should be ~30% of extent
    if mode == "shear":
        arrow_scale = 0.3 * extent / force_max if force_max > 1e-12 else 1.0
    else:
        arrow_scale = 1.0  # Not used in axial mode
    
    # Plot bolt connections and forces
    for i, bf in enumerate(bolt_results_list):
        # Bolt location point colored by selected metric
        value = bf.shear if mode == "shear" else bf.axial
        color = colormap(norm(value))
        
        # Bolt circle with actual diameter
        circle = Circle(
            (bf.z, bf.y),
            radius=visual_radius,
            facecolor=color,
            edgecolor='black',
            linewidth=1.5,
            zorder=3
        )
        ax.add_patch(circle)
        
        # Add bolt index label
        ax.text(bf.z, bf.y - visual_radius * 1.2, str(i + 1), 
               ha='center', va='top', fontsize=8, fontweight='bold', zorder=4)
        
        # Force vector arrow (shear mode only)
        if draw_arrows and bolt_forces and value > 1e-12:
            arrow_length_y = bf.Fy * arrow_scale
            arrow_length_z = bf.Fz * arrow_scale
            
            ax.arrow(
                bf.z, bf.y,
                arrow_length_z, arrow_length_y,
                head_width=visual_radius * 0.8,
                head_length=visual_radius * 0.5,
                fc='darkred',
                ec='darkred',
                linewidth=1.5,
                zorder=4,
                alpha=0.8
            )
    
    # Add colorbar
    if colorbar and bolt_results_list:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        
        cbar = fig.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
        cbar.set_label(color_label, fontsize=10)
    
    # Plot applied force
    if force:
        _plot_applied_force(ax, result.load, bolt_group, extent, force_unit, length_unit)
    
    # Plot neutral axis lines (if tension analysis was performed)
    if mode == "axial":
        _plot_neutral_axes(ax, result, bolt_group)
    
    # Plot ICR point if available
    if result.icr_point is not None:
        ax.plot(result.icr_point[1], result.icr_point[0], 'ko',
                markersize=10, markerfacecolor='none', markeredgewidth=2,
                label='ICR', zorder=5)
    
    # Formatting
    ax.set_aspect('equal')
    ax.set_xlabel(f'z ({length_unit})', fontsize=11)
    ax.set_ylabel(f'y ({length_unit})', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Adjust limits with margin
    margin = extent * 0.15
    y_min, y_max = plate.y_min - margin, plate.y_max + margin
    z_min, z_max = plate.z_min - margin, plate.z_max + margin
    ax.set_xlim(z_min, z_max)
    ax.set_ylim(y_min, y_max)
    
    # Title with key info
    title = f"Bolt Connection Analysis ({result.shear_method.upper()} method)"
    title += f"\n{bolt_group.n} × {bolt_group.parameters.diameter:.1f}{length_unit} bolts"
    if bolt_results_list:
        title += f" | {title_metric}: {force_max:.2f} {force_unit}"
    ax.set_title(title, fontsize=12)
    
    plt.tight_layout()
    
    # Save if requested
    if save_path:
        if not save_path.endswith('.svg'):
            save_path += '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    
    return ax


def _plot_applied_force(
    ax: plt.Axes,
    load,
    bolt_group,
    extent: float,
    force_unit: str,
    length_unit: str
) -> None:
    """Plot applied force and add legend."""
    x_loc, y_loc, z_loc = load.location
    
    # Plot application point (red 'x')
    ax.plot(z_loc, y_loc, 'rx', markersize=12, markeredgewidth=3,
            label='Force Location', zorder=5)
    
    # Build legend text
    labels = []
    
    # Forces (display in same units as input)
    if abs(load.Fy) > 1e-6:
        labels.append(f"Fy = {load.Fy:.2f} {force_unit}")
    if abs(load.Fz) > 1e-6:
        labels.append(f"Fz = {load.Fz:.2f} {force_unit}")
    
    # Transfer moments to bolt group centroid for display
    Cy, Cz = bolt_group.Cy, bolt_group.Cz
    load_at_centroid = load.equivalent_load((0.0, Cy, Cz))
    
    if abs(load_at_centroid.Mx) > 1e-6:
        labels.append(f"Mx = {load_at_centroid.Mx:.2f} {force_unit}·{length_unit}")
    
    # Add a custom legend entry for the loads
    if labels:
        text = "\n".join(labels)
        dummy_lines = [Line2D([0], [0], color='red', linestyle='None', marker='x')]
        ax.legend(dummy_lines, [text], loc='upper left',
                 title="Applied Loads", framealpha=0.9)


def _plot_plate(ax: plt.Axes, plate) -> None:
    """Plot plate boundary as a prominent rectangle."""
    from matplotlib.patches import Rectangle
    
    # Plot plate as light gray rectangle (background)
    width = plate.depth_z
    height = plate.depth_y
    
    rect = Rectangle(
        (plate.z_min, plate.y_min),
        width,
        height,
        linewidth=3,
        edgecolor='darkgray',
        facecolor='lightgray',
        alpha=0.3,
        zorder=1,
        label='Plate'
    )
    ax.add_patch(rect)


def _draw_connection_line(ax: plt.Axes, bolt_result, plate, color: str) -> None:
    """Draw connection line from bolt to nearest plate edge."""
    # Find nearest point on plate edge to this bolt
    bolt_y, bolt_z = bolt_result.y, bolt_result.z
    
    # Calculate distances to each plate edge
    dist_to_bottom = abs(bolt_y - plate.y_min)
    dist_to_top = abs(bolt_y - plate.y_max)
    dist_to_left = abs(bolt_z - plate.z_min)
    dist_to_right = abs(bolt_z - plate.z_max)
    
    # Find which edge is closest
    min_dist = min(dist_to_bottom, dist_to_top, dist_to_left, dist_to_right)
    
    if min_dist == dist_to_bottom:
        edge_point = (plate.z_min + (plate.z_max - plate.z_min) / 2, plate.y_min)
    elif min_dist == dist_to_top:
        edge_point = (plate.z_min + (plate.z_max - plate.z_min) / 2, plate.y_max)
    elif min_dist == dist_to_left:
        edge_point = (plate.z_min, plate.y_min + (plate.y_max - plate.y_min) / 2)
    else:
        edge_point = (plate.z_max, plate.y_min + (plate.y_max - plate.y_min) / 2)
    
    # Draw line from bolt to nearest edge
    ax.plot(
        [bolt_z, edge_point[0]],
        [bolt_y, edge_point[1]],
        color=color,
        linewidth=2,
        alpha=0.6,
        zorder=2
    )


def _plot_neutral_axes(ax: plt.Axes, result, bolt_group) -> None:
    """Plot neutral axis lines for My and Mz bending."""
    plate = result.connection.plate
    
    # Get moments at bolt group centroid
    Cy, Cz = bolt_group.Cy, bolt_group.Cz
    load_at_centroid = result.load.equivalent_load((0.0, Cy, Cz))
    My = load_at_centroid.My
    Mz = load_at_centroid.Mz
    
    # Plot NA for My (bending about y-axis -> tension gradient across z)
    if abs(My) > 1e-6:
        # Determine neutral axis position
        d_z = plate.depth_z
        if result.tension_method == "conservative":
            na_z = 0.5 * (plate.z_min + plate.z_max)
        else:  # accurate
            comp_edge_z = plate.z_min if My > 0 else plate.z_max
            na_z = comp_edge_z + d_z / 6.0 if My > 0 else comp_edge_z - d_z / 6.0
        
        # Draw vertical dashed line at NA
        ax.axvline(na_z, color='blue', linestyle='--', linewidth=1.5, 
                   alpha=0.7, label='NA (My)', zorder=2)
    
    # Plot NA for Mz (bending about z-axis -> tension gradient across y)
    if abs(Mz) > 1e-6:
        # Determine neutral axis position
        d_y = plate.depth_y
        if result.tension_method == "conservative":
            na_y = 0.5 * (plate.y_min + plate.y_max)
        else:  # accurate
            comp_edge_y = plate.y_min if Mz > 0 else plate.y_max
            na_y = comp_edge_y + d_y / 6.0 if Mz > 0 else comp_edge_y - d_y / 6.0
        
        # Draw horizontal dashed line at NA
        ax.axhline(na_y, color='green', linestyle='--', linewidth=1.5,
                   alpha=0.7, label='NA (Mz)', zorder=2)


def _plot_applied_force_old(
    ax: plt.Axes,
    force,
    bolt_group,
    extent: float,
    force_unit: str,
    length_unit: str
) -> None:
    """Plot applied force and add legend (old Force object version - deprecated)."""
    x_loc, y_loc, z_loc = force.location
    
    # Plot application point (red 'x')
    ax.plot(z_loc, y_loc, 'rx', markersize=12, markeredgewidth=3,
            label='Force Location', zorder=5)
    
    # Build legend text
    labels = []
    
    # Forces (display in same units as input)
    if abs(force.Fy) > 1e-6:
        labels.append(f"Fy = {force.Fy:.2f} {force_unit}")
    if abs(force.Fz) > 1e-6:
        labels.append(f"Fz = {force.Fz:.2f} {force_unit}")
    
    # Moment (torsion)
    Cy, Cz = bolt_group.Cy, bolt_group.Cz
    Mx_total, _, _ = force.get_moments_about(Cy, Cz)
    if abs(Mx_total) > 1e-6:
        labels.append(f"Mx = {Mx_total:.2f} {force_unit}·{length_unit}")
    
    # Add a custom legend entry for the loads
    if labels:
        text = "\n".join(labels)
        dummy_lines = [Line2D([0], [0], color='red', linestyle='None', marker='x')]
        ax.legend(dummy_lines, [text], loc='upper left',
                 title="Applied Loads", framealpha=0.9)


def plot_bolt_pattern(
    bolt_group,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | None = None,
    length_unit: str = "mm"
) -> plt.Axes:
    """
    Plot bolt group pattern without analysis results.
    
    Useful for visualizing bolt layout before analysis.
    
    Args:
        bolt_group: BoltGroup object
        ax: Matplotlib axes (creates new if None)
        show: Display the plot
        save_path: Path to save figure
        length_unit: Unit label for lengths (e.g., 'mm', 'm', 'in')
        
    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.figure
    
    bolt_diameter = bolt_group.parameters.diameter
    visual_radius = bolt_diameter / 2
    
    # Plot each bolt
    for i, (y, z) in enumerate(bolt_group.positions):
        circle = Circle(
            (z, y),
            radius=visual_radius,
            facecolor='steelblue',
            edgecolor='black',
            linewidth=1.5,
            zorder=3
        )
        ax.add_patch(circle)
        
        # Label bolt number
        ax.text(z, y, str(i + 1), ha='center', va='center',
               fontsize=8, fontweight='bold', color='white', zorder=4)
    
    # Plot centroid
    ax.plot(bolt_group.Cz, bolt_group.Cy, 'k+',
            markersize=12, markeredgewidth=2, label='Centroid')
    
    # Formatting
    ax.set_aspect('equal')
    ax.set_xlabel(f'z ({length_unit})', fontsize=11)
    ax.set_ylabel(f'y ({length_unit})', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper right')
    
    # Adjust limits
    y_coords = [p[0] for p in bolt_group.positions]
    z_coords = [p[1] for p in bolt_group.positions]
    margin = max(
        max(y_coords) - min(y_coords),
        max(z_coords) - min(z_coords),
        bolt_diameter * 4
    ) * 0.3
    
    ax.set_xlim(min(z_coords) - margin, max(z_coords) + margin)
    ax.set_ylim(min(y_coords) - margin, max(y_coords) + margin)
    
    # Title
    title = f"Bolt Pattern: {bolt_group.n} × {bolt_diameter:.1f}{length_unit} bolts"
    ax.set_title(title, fontsize=12)
    
    plt.tight_layout()
    
    if save_path:
        if not save_path.endswith('.svg'):
            save_path += '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    
    return ax

