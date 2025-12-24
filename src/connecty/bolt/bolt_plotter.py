"""
Plotting functions for bolt group visualization.

Provides plotting methods called by BoltResult.plot().
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import math
import numpy as np

if TYPE_CHECKING:
    from .bolt import BoltResult

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Circle
from matplotlib.lines import Line2D


def plot_bolt_result(
    result: BoltResult,
    force: bool = True,
    bolt_forces: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | None = None,
    mode: str = "shear",
) -> plt.Axes:
    """
    Plot bolt group with force distribution.
    
    Args:
        result: BoltResult from analysis
        force: Show applied load arrow
        bolt_forces: Show reaction vectors at each bolt (shear mode only)
        colorbar: Show force colorbar
        cmap: Matplotlib colormap name
        ax: Matplotlib axes (creates new if None)
        show: Display the plot
        save_path: Path to save figure (.svg recommended)
        mode: Visualization mode: "shear" (default) or "axial"
        
    Returns:
        Matplotlib axes
    """
    # Validate mode
    if mode not in {"shear", "axial"}:
        raise ValueError("mode must be 'shear' or 'axial'")
    if mode == "axial" and result.method == "icr":
        raise ValueError("Axial plotting is not supported for ICR results.")

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure
    
    bolt_group = result.bolt_group
    
    # Choose value source based on mode
    if mode == "shear":
        values = [bf.shear for bf in result.bolt_forces]
        color_label = "Bolt Shear (kN)"
        title_metric = "Max Shear"
        draw_arrows = True
    else:
        values = [bf.axial for bf in result.bolt_forces]
        color_label = "Bolt Axial (kN) [+tension/-compression]"
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
    y_coords = [bf.y for bf in result.bolt_forces]
    z_coords = [bf.z for bf in result.bolt_forces]
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
    
    # Plot each bolt
    for i, bf in enumerate(result.bolt_forces):
        # Bolt circle colored by selected metric
        value = bf.shear if mode == "shear" else bf.axial
        color = colormap(norm(value))
        circle = Circle(
            (bf.z, bf.y),  # (z, y) for plotting
            radius=visual_radius,
            facecolor=color,
            edgecolor='black',
            linewidth=1.5,
            zorder=3
        )
        ax.add_patch(circle)
        
        # Add bolt index label
        ax.text(bf.z, bf.y, str(i), ha='center', va='center',
               fontsize=8, fontweight='bold', color='white', zorder=4)
        
        # Force vector arrow (shear mode only)
        if draw_arrows and bolt_forces and value > 1e-12:
            arrow_length_y = bf.Fy * arrow_scale
            arrow_length_z = bf.Fz * arrow_scale
            
            ax.arrow(
                bf.z, bf.y,
                arrow_length_z, arrow_length_y,
                head_width=visual_radius * 0.5,
                head_length=visual_radius * 0.3,
                fc='black',
                ec='black',
                linewidth=1.0,
                zorder=4
            )
    
    # Add colorbar
    if colorbar and result.bolt_forces:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        
        cbar = fig.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
        cbar.set_label(color_label, fontsize=10)
    
    # Plot applied force
    if force:
        _plot_applied_force(ax, result.force, bolt_group, extent)
    
    # Plot ICR point if available
    if result.icr_point is not None:
        ax.plot(result.icr_point[1], result.icr_point[0], 'ko',
                markersize=10, markerfacecolor='none', markeredgewidth=2,
                label='ICR')
    
    # Formatting
    ax.set_aspect('equal')
    ax.set_xlabel('z (mm)', fontsize=11)
    ax.set_ylabel('y (mm)', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Adjust limits with margin
    margin = extent * 0.3
    y_min, y_max = min(y_coords) - margin, max(y_coords) + margin
    z_min, z_max = min(z_coords) - margin, max(z_coords) + margin
    ax.set_xlim(z_min, z_max)
    ax.set_ylim(y_min, y_max)
    
    # Title with key info
    title = f"Bolt Group Analysis ({result.method.upper()} method)"
    title += f"\n{bolt_group.n} × M{bolt_group.parameters.diameter:.0f} bolts"
    if result.bolt_forces:
        title += f" | {title_metric}: {force_max:.1f} kN"
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
    force,
    bolt_group,
    extent: float
) -> None:
    """Plot applied force and add legend."""
    x_loc, y_loc, z_loc = force.location
    
    # Plot application point (red 'x')
    ax.plot(z_loc, y_loc, 'rx', markersize=12, markeredgewidth=3,
            label='Force Location', zorder=5)
    
    # Build legend text
    labels = []
    
    # Forces (convert from N to kN)
    if abs(force.Fy) > 1e-3:
        labels.append(f"Fy = {force.Fy/1000:.1f} kN")
    if abs(force.Fz) > 1e-3:
        labels.append(f"Fz = {force.Fz/1000:.1f} kN")
    
    # Moment (torsion)
    Cy, Cz = bolt_group.Cy, bolt_group.Cz
    Mx_total, _, _ = force.get_moments_about(Cy, Cz)
    if abs(Mx_total) > 1e-3:
        labels.append(f"Mx = {Mx_total/1e6:.2f} kN·m")
    
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
    save_path: str | None = None
) -> plt.Axes:
    """
    Plot bolt group pattern without analysis results.
    
    Useful for visualizing bolt layout before analysis.
    
    Args:
        bolt_group: BoltGroup object
        ax: Matplotlib axes (creates new if None)
        show: Display the plot
        save_path: Path to save figure
        
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
    ax.set_xlabel('z (mm)', fontsize=11)
    ax.set_ylabel('y (mm)', fontsize=11)
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
    title = f"Bolt Pattern: {bolt_group.n} × M{bolt_diameter:.0f} bolts"
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

