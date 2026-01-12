"""
Plotting helpers for bolt connections.

All save outputs are forced to `.svg` when `save_path` is provided.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal
import math

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Circle, Rectangle
from matplotlib.lines import Line2D
from matplotlib.legend import Legend

from .load import Load
from .bolt import BoltGroup
from .plate import Plate

if TYPE_CHECKING:
    from .analysis import LoadedBoltConnection


def plot_shear_distribution(
    result: "LoadedBoltConnection",
    *,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | Path | None = None,
    colorbar: bool = True,
    cmap: str = "Reds",
    force_unit: str = "N",
    length_unit: str = "mm",
) -> plt.Axes:
    """Plot plate, bolts, and in-plane shear forces (Fx, Fy)."""
    return _plot_distribution(
        result=result,
        mode="shear",
        ax=ax,
        show=show,
        save_path=save_path,
        colorbar=colorbar,
        cmap=cmap,
        force_unit=force_unit,
        length_unit=length_unit,
    )


def plot_tension_distribution(
    result: "LoadedBoltConnection",
    *,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | Path | None = None,
    colorbar: bool = True,
    cmap: str = "Reds",
    force_unit: str = "N",
    length_unit: str = "mm",
) -> plt.Axes:
    """Plot plate, bolts, and out-of-plane tension forces (Fz)."""
    return _plot_distribution(
        result=result,
        mode="tension",
        ax=ax,
        show=show,
        save_path=save_path,
        colorbar=colorbar,
        cmap=cmap,
        force_unit=force_unit,
        length_unit=length_unit,
    )


def _plot_distribution(
    result: "LoadedBoltConnection",
    mode: Literal["shear", "tension"],
    *,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | Path | None = None,
    colorbar: bool = True,
    cmap: str = "viridis",
    force_unit: str = "N",
    length_unit: str = "mm",
) -> plt.Axes:
    """Internal helper to plot bolt distribution."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure

    bolt_group = result.bolt_connection.bolt_group
    bolts = bolt_group.bolts
    plate = result.bolt_connection.plate

    if plate is None:
        raise ValueError("Plate is required to plot a bolt result.")

    _plot_plate(ax, plate)

    # Determine scaling
    force_scale = 0.001  # Convert to kN as requested for both modes
    display_force_unit = "kN"

    # Extract values
    vals = []
    for b in bolts:
        fx, fy, fz = b.forces
        if mode == "shear":
            # Shear magnitude
            vals.append(np.sqrt(fx**2 + fy**2) * force_scale)
        else:
            # Axial (tension) force
            vals.append(fz * force_scale)

    if mode == "shear":
        color_label = f"Bolt Shear ({display_force_unit})"
        title_metric = "Max Shear"
        draw_arrows = True
    else:
        color_label = f"Bolt Tension ({display_force_unit})"
        title_metric = "Max Tension"
        draw_arrows = False

    force_min = min(vals) if vals else 0.0
    force_max = max(vals) if vals else 0.0

    if force_max - force_min > 1e-12:
        norm = mcolors.Normalize(vmin=force_min, vmax=force_max)
    else:
        norm = mcolors.Normalize(vmin=0.0, vmax=max(force_max, 1.0))

    colormap = plt.get_cmap(cmap)

    # Assume all bolts have same diameter for visualization
    bolt_diameter = bolts[0].params.diameter if bolts else 10.0
    visual_radius = bolt_diameter / 2.0

    x_coords = [b.position[0] for b in bolts]
    y_coords = [b.position[1] for b in bolts]

    extent = max(
        (max(x_coords) - min(x_coords)) if x_coords else 1.0,
        (max(y_coords) - min(y_coords)) if y_coords else 1.0,
        bolt_diameter * 4.0,
    )

    # Arrow scaling (shear only)
    #
    # IMPORTANT: keep arrow math in the same units as `b.forces` (N).
    # The color values above are converted to kN, but the arrow vectors are not.
    arrow_scale = 1.0
    if mode == "shear":
        shear_mags_n = [float(np.hypot(b.forces[0], b.forces[1])) for b in bolts]
        shear_max_n = max(shear_mags_n) if shear_mags_n else 0.0
        # Make the *longest* arrow about 25% of the plot extent.
        arrow_target_len = 0.25 * extent
        arrow_scale = arrow_target_len / shear_max_n if shear_max_n > 1e-12 else 1.0

    for i, b in enumerate(bolts):
        value = vals[i]
        color = colormap(norm(value))

        # position is (x, y)
        bx, by = b.position

        circle = Circle(
            (bx, by),
            radius=visual_radius,
            facecolor=color,
            edgecolor="black",
            linewidth=1.5,
            zorder=3,
        )
        ax.add_patch(circle)

        ax.text(
            bx,
            by - visual_radius * 1.2,
            str(i + 1),
            ha="center",
            va="top",
            fontsize=8,
            fontweight="bold",
            zorder=4,
        )

        if draw_arrows and value > 1e-12:
            fx, fy, _ = b.forces
            arrow_length_x = fx * arrow_scale
            arrow_length_y = fy * arrow_scale
            ax.arrow(
                bx,
                by,
                arrow_length_x,
                arrow_length_y,
                head_width=visual_radius * 0.8,
                head_length=visual_radius * 0.5,
                fc="black",
                ec="black",
                linewidth=1.5,
                zorder=4,
                alpha=0.8,
            )

    if colorbar and bolts:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
        cbar.set_label(color_label, fontsize=10)

    if mode == "tension":
        _plot_neutral_axes(ax=ax, result=result, bolt_group=bolt_group)
        
        if result.plate_pressure is not None and result.plate_pressure_extent is not None:
            # Plot pressure heatmap
            pressure_max = np.max(result.plate_pressure)
            if pressure_max > 1e-6:
                im = ax.imshow(
                    result.plate_pressure,
                    origin="lower",
                    extent=result.plate_pressure_extent,
                    cmap="Blues",
                    alpha=0.6,
                    zorder=2,
                    interpolation="bilinear",
                )
                
                # Add colorbar for pressure on the left
                # Note: 'location' parameter requires Matplotlib 3.4+
                try:
                    cbar_p = fig.colorbar(im, ax=ax, location="left", shrink=0.8)
                    cbar_p.set_label("Plate Pressure (MPa)", fontsize=10)
                except TypeError:
                    # Fallback for older matplotlib versions if 'location' is not supported
                    # We simply don't plot it on the left to avoid crashing, 
                    # or could try manual placement, but let's assume recent matplotlib.
                    pass

    if mode == "shear" and result.icr_point is not None:
        icr_x, icr_y = result.icr_point
        ax.plot(
            icr_x,
            icr_y,
            "ko",
            markersize=10,
            markerfacecolor="none",
            markeredgewidth=2,
            label="ICR",
            zorder=5,
        )

    ax.set_aspect("equal")
    ax.set_xlabel(f"x ({length_unit})", fontsize=11)
    ax.set_ylabel(f"y ({length_unit})", fontsize=11)
    ax.grid(True, alpha=0.3, linestyle="--")

    margin = extent * 0.15
    ax.set_xlim(plate.x_min - margin, plate.x_max + margin)
    ax.set_ylim(plate.y_min - margin, plate.y_max + margin)

    applied_legend = _plot_applied_force(
        ax=ax,
        load=result.load,
        bolt_group=bolt_group,
        force_unit=display_force_unit,
        length_unit=length_unit,
        mode=mode,
        force_scale=force_scale,
    )

    if mode == "shear" and result.icr_point is not None:
        icr_x, icr_y = result.icr_point
        icr_handle = Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markerfacecolor="none",
            markeredgecolor="black",
            markeredgewidth=2,
            color="black",
        )
        icr_text = f"x={icr_x:.2f}, y={icr_y:.2f} {length_unit}"

        # Keep Applied Load legend (top-left) and add ICR legend (top-right).
        if applied_legend is not None:
            ax.add_artist(applied_legend)
        ax.legend([icr_handle], [icr_text], loc="upper right", title="ICR", framealpha=0.9)

    title = f"Bolt Connection Analysis ({mode.title()})\n"
    title += f"{bolt_group.n} × {bolt_diameter:.1f}{length_unit} bolts"
    if bolts:
        title += f" | {title_metric}: {force_max:.2f} {force_unit}"
    ax.set_title(title, fontsize=12)

    plt.tight_layout()

    if save_path is not None:
        out = Path(save_path)
        if out.suffix.lower() != ".svg":
            out = out.with_suffix(".svg")
        fig.savefig(str(out), format="svg", bbox_inches="tight")

    if show:
        plt.show()

    return ax


def plot_bolt_pattern(
    bolt_group: BoltGroup,
    *,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | Path | None = None,
    length_unit: str = "mm",
    bolt_diameter: float = 10.0,
) -> plt.Axes:
    """Plot bolt group pattern without analysis results."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.figure

    visual_radius = float(bolt_diameter) / 2.0

    # points are (x, y)
    for i, (x, y) in enumerate(bolt_group.points):
        circle = Circle(
            (x, y),
            radius=visual_radius,
            facecolor="steelblue",
            edgecolor="black",
            linewidth=1.5,
            zorder=3,
        )
        ax.add_patch(circle)
        ax.text(
            x,
            y,
            str(i + 1),
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="white",
            zorder=4,
        )

    ax.plot(bolt_group.Cx, bolt_group.Cy, "k+", markersize=12, markeredgewidth=2, label="Centroid")

    ax.set_aspect("equal")
    ax.set_xlabel(f"x ({length_unit})", fontsize=11)
    ax.set_ylabel(f"y ({length_unit})", fontsize=11)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper right")

    x_coords = [p[0] for p in bolt_group.points]
    y_coords = [p[1] for p in bolt_group.points]
    margin = max(
        (max(x_coords) - min(x_coords)) if x_coords else 0,
        (max(y_coords) - min(y_coords)) if y_coords else 0,
        bolt_diameter * 4.0,
    ) * 0.3

    if not x_coords:  # Handle empty group
        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)
    else:
        ax.set_xlim(min(x_coords) - margin, max(x_coords) + margin)
        ax.set_ylim(min(y_coords) - margin, max(y_coords) + margin)

    ax.set_title(f"Bolt Pattern: {bolt_group.n} bolts", fontsize=12)

    plt.tight_layout()

    if save_path is not None:
        out = Path(save_path)
        if out.suffix.lower() != ".svg":
            out = out.with_suffix(".svg")
        fig.savefig(str(out), format="svg", bbox_inches="tight")

    if show:
        plt.show()

    return ax


def _plot_applied_force(
    *,
    ax: plt.Axes,
    load: Load,
    bolt_group: BoltGroup,
    force_unit: str,
    length_unit: str,
    mode: Literal["shear", "tension"],
    extent: float | None = None, # kept for backward compatibility if needed, but unused in logic below if we use ax limits
    force_scale: float = 1.0,
) -> Legend | None:
    """Plot applied load location and annotate key components."""
    x_loc, y_loc, _ = load.location
    ax.plot(x_loc, y_loc, "kx", markersize=10, markeredgewidth=2, label="Load Location", zorder=5)

    # Intentionally do not draw Mx/My vectors on the tension plot.
    # The tension figure already contains NA/pressure visuals; adding moment arrows tends to clutter it.

    labels: list[str] = []
    
    if mode == "shear":
        if abs(load.Fx) > 1e-6:
            labels.append(f"Fx = {load.Fx * force_scale:.2f} {force_unit}")
        if abs(load.Fy) > 1e-6:
            labels.append(f"Fy = {load.Fy * force_scale:.2f} {force_unit}")
            
        Cx, Cy = bolt_group.Cx, bolt_group.Cy
        load_at_centroid = load.equivalent_at((Cx, Cy, 0.0))
        
        if abs(load_at_centroid.Mz) > 1e-6:
            labels.append(f"Mz = {load_at_centroid.Mz * force_scale:.2f} {force_unit}·{length_unit}")

    if mode == "tension":
        if abs(load.Fz) > 1e-6:
            labels.append(f"Fz (axial) = {load.Fz * force_scale:.2f} {force_unit}")

        # Keep Mx/My in the legend for reporting, but do not draw them graphically.
        Cx, Cy = bolt_group.Cx, bolt_group.Cy
        load_at_centroid = load.equivalent_at((Cx, Cy, 0.0))

        if abs(load_at_centroid.Mx) > 1e-6:
            labels.append(f"Mx = {load_at_centroid.Mx * force_scale:.2f} {force_unit}·{length_unit}")
        if abs(load_at_centroid.My) > 1e-6:
            labels.append(f"My = {load_at_centroid.My * force_scale:.2f} {force_unit}·{length_unit}")

    if labels:
        text = "\n".join(labels)
        dummy_lines = [Line2D([0], [0], color="black", linestyle="None", marker="x")]
        return ax.legend(dummy_lines, [text], loc="upper left", title="Applied Load", framealpha=0.9)

    return None


def _plot_plate(ax: plt.Axes, plate: Plate) -> None:
    """Plot plate boundary as a prominent rectangle."""
    rect = Rectangle(
        (plate.x_min, plate.y_min),
        plate.depth_x,
        plate.depth_y,
        linewidth=3,
        edgecolor="darkgray",
        facecolor="lightgray",
        alpha=0.3,
        zorder=1,
        label="Plate",
    )
    ax.add_patch(rect)


def _plot_neutral_axes(*, ax: plt.Axes, result: "LoadedBoltConnection", bolt_group: BoltGroup) -> None:
    """Plot neutral axis lines used by the plate tension method."""
    plate = result.bolt_connection.plate
    if plate is None:
        return

    Cx, Cy = bolt_group.Cx, bolt_group.Cy
    load_at_centroid = result.load.equivalent_at((Cx, Cy, 0.0))
    Mx = load_at_centroid.Mx
    My = load_at_centroid.My

    if abs(Mx) < 1e-6 and abs(My) < 1e-6:
        return

    # Neutral Axis logic:
    # This is a visualization approximation or result display.
    # The actual neutral axis is computed as a line in the plane.
    # If the solver provides an exact NA line equation (theta, c), we should plot that.
    
    if result.neutral_axis is not None:
        theta, c = result.neutral_axis
        # Line equation: x*cos(theta) + y*sin(theta) = c
        # We want to plot this line within the plate bounds.
        
        # Calculate intersections with plate bounding box for plotting
        points = []
        
        # Intersection with x_min
        if abs(np.sin(theta)) > 1e-6:
            y = (c - plate.x_min * np.cos(theta)) / np.sin(theta)
            if plate.y_min <= y <= plate.y_max:
                points.append((plate.x_min, y))
                
        # Intersection with x_max
        if abs(np.sin(theta)) > 1e-6:
            y = (c - plate.x_max * np.cos(theta)) / np.sin(theta)
            if plate.y_min <= y <= plate.y_max:
                points.append((plate.x_max, y))
                
        # Intersection with y_min
        if abs(np.cos(theta)) > 1e-6:
            x = (c - plate.y_min * np.sin(theta)) / np.cos(theta)
            if plate.x_min <= x <= plate.x_max:
                points.append((x, plate.y_min))

        # Intersection with y_max
        if abs(np.cos(theta)) > 1e-6:
            x = (c - plate.y_max * np.sin(theta)) / np.cos(theta)
            if plate.x_min <= x <= plate.x_max:
                points.append((x, plate.y_max))
                
        # Unique points
        points = list(set(points))
        if len(points) >= 2:
            p1, p2 = points[:2]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], "b--", linewidth=2, label="Neutral Axis")
            return

    # Fallback visualization if exact NA not available or logic simple
    if abs(My) > 1e-6:
        # Bending around Y axis -> varies with X (sigma = M*x/I)
        # Neutral axis is x = constant
        if result.tension_method == "conservative":
            na_x = float(bolt_group.Cx)
        else:
            # Simple approximation for visualization if solver didn't return NA
            comp_edge_x = plate.x_min if My > 0.0 else plate.x_max
            na_x = (float(bolt_group.Cx) + comp_edge_x) / 2.0 # Rough guess
        ax.axvline(na_x, color="blue", linestyle="--", linewidth=1.5, alpha=0.7, label="Neutral Axis (approx)", zorder=2)

    if abs(Mx) > 1e-6:
        # Bending around X axis -> varies with Y (sigma = M*y/I)
        # Neutral axis is y = constant
        if result.tension_method == "conservative":
            na_y = float(bolt_group.Cy)
        else:
            comp_edge_y = plate.y_min if Mx < 0.0 else plate.y_max # Check sign convention
            na_y = (float(bolt_group.Cy) + comp_edge_y) / 2.0
        ax.axhline(na_y, color="green", linestyle="--", linewidth=1.5, alpha=0.7, label="Neutral Axis (approx)", zorder=2)
