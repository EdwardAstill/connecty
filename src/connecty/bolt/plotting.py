"""
Plotting helpers for bolt connections.

All save outputs are forced to `.svg` when `save_path` is provided.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import math

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Circle
from matplotlib.lines import Line2D

from ..common.load import Load
from .geometry import BoltLayout, Plate

if TYPE_CHECKING:
    from .analysis import BoltResult


def plot_bolt_result(
    result: "BoltResult",
    *,
    force: bool = True,
    bolt_forces: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | Path | None = None,
    mode: str = "shear",
    force_unit: str = "N",
    length_unit: str = "mm",
) -> plt.Axes:
    """Plot plate + bolts + per-bolt forces (shear or axial)."""
    if mode not in {"shear", "axial"}:
        raise ValueError("mode must be 'shear' or 'axial'")
    if mode == "axial" and result.shear_method == "icr":
        raise ValueError("Axial plotting is not supported for ICR results.")

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure

    layout = result.connection.layout
    bolt_results_list = result.to_bolt_forces()
    plate = result.connection.plate
    if plate is None:
        raise ValueError("Plate is required to plot a bolt result (needs plate outline/limits).")

    _plot_plate(ax, plate)

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

    force_min = min(values) if values else 0.0
    force_max = max(values) if values else 0.0

    if force_max - force_min > 1e-12:
        norm = mcolors.Normalize(vmin=force_min, vmax=force_max)
    else:
        norm = mcolors.Normalize(vmin=0.0, vmax=max(force_max, 1.0))

    colormap = plt.get_cmap(cmap)

    bolt_diameter = float(result.connection.bolt.diameter)
    visual_radius = bolt_diameter / 2.0

    y_coords = [bf.y for bf in bolt_results_list]
    z_coords = [bf.z for bf in bolt_results_list]
    extent = max(
        (max(y_coords) - min(y_coords)) if y_coords else 1.0,
        (max(z_coords) - min(z_coords)) if z_coords else 1.0,
        bolt_diameter * 4.0,
    )

    arrow_scale = 1.0
    if mode == "shear":
        arrow_scale = 0.3 * extent / force_max if force_max > 1e-12 else 1.0

    for i, bf in enumerate(bolt_results_list):
        value = bf.shear if mode == "shear" else bf.axial
        color = colormap(norm(value))

        circle = Circle(
            (bf.z, bf.y),
            radius=visual_radius,
            facecolor=color,
            edgecolor="black",
            linewidth=1.5,
            zorder=3,
        )
        ax.add_patch(circle)

        ax.text(
            bf.z,
            bf.y - visual_radius * 1.2,
            str(i + 1),
            ha="center",
            va="top",
            fontsize=8,
            fontweight="bold",
            zorder=4,
        )

        if draw_arrows and bolt_forces and value > 1e-12:
            arrow_length_y = bf.Fy * arrow_scale
            arrow_length_z = bf.Fz * arrow_scale
            ax.arrow(
                bf.z,
                bf.y,
                arrow_length_z,
                arrow_length_y,
                head_width=visual_radius * 0.8,
                head_length=visual_radius * 0.5,
                fc="darkred",
                ec="darkred",
                linewidth=1.5,
                zorder=4,
                alpha=0.8,
            )

    if colorbar and bolt_results_list:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
        cbar.set_label(color_label, fontsize=10)

    if force:
        _plot_applied_force(
            ax=ax,
            load=result.load,
            bolt_group=layout,
            force_unit=force_unit,
            length_unit=length_unit,
        )

    if mode == "axial":
        _plot_neutral_axes(ax=ax, result=result, bolt_group=layout)

    if result.icr_point is not None:
        ax.plot(
            result.icr_point[1],
            result.icr_point[0],
            "ko",
            markersize=10,
            markerfacecolor="none",
            markeredgewidth=2,
            label="ICR",
            zorder=5,
        )

    ax.set_aspect("equal")
    ax.set_xlabel(f"z ({length_unit})", fontsize=11)
    ax.set_ylabel(f"y ({length_unit})", fontsize=11)
    ax.grid(True, alpha=0.3, linestyle="--")

    margin = extent * 0.15
    ax.set_xlim(plate.z_min - margin, plate.z_max + margin)
    ax.set_ylim(plate.y_min - margin, plate.y_max + margin)

    title = f"Bolt Connection Analysis ({result.shear_method.upper()} method)"
    title += f"\n{layout.n} × {bolt_diameter:.1f}{length_unit} bolts"
    if bolt_results_list:
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
    bolt_group: BoltLayout,
    *,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | Path | None = None,
    length_unit: str = "mm",
    bolt_diameter: float = 1.0,
) -> plt.Axes:
    """Plot bolt group pattern without analysis results."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.figure

    visual_radius = float(bolt_diameter) / 2.0

    for i, (y, z) in enumerate(bolt_group.points):
        circle = Circle(
            (z, y),
            radius=visual_radius,
            facecolor="steelblue",
            edgecolor="black",
            linewidth=1.5,
            zorder=3,
        )
        ax.add_patch(circle)
        ax.text(
            z,
            y,
            str(i + 1),
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="white",
            zorder=4,
        )

    ax.plot(bolt_group.Cz, bolt_group.Cy, "k+", markersize=12, markeredgewidth=2, label="Centroid")

    ax.set_aspect("equal")
    ax.set_xlabel(f"z ({length_unit})", fontsize=11)
    ax.set_ylabel(f"y ({length_unit})", fontsize=11)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper right")

    y_coords = [p[0] for p in bolt_group.points]
    z_coords = [p[1] for p in bolt_group.points]
    margin = max(
        max(y_coords) - min(y_coords),
        max(z_coords) - min(z_coords),
        bolt_diameter * 4.0,
    ) * 0.3

    ax.set_xlim(min(z_coords) - margin, max(z_coords) + margin)
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
    bolt_group: BoltLayout,
    force_unit: str,
    length_unit: str,
) -> None:
    """Plot applied load location and annotate key components."""
    _x_loc, y_loc, z_loc = load.location
    ax.plot(z_loc, y_loc, "rx", markersize=12, markeredgewidth=3, label="Load Location", zorder=5)

    labels: list[str] = []
    if abs(load.Fy) > 1e-6:
        labels.append(f"Fy = {load.Fy:.2f} {force_unit}")
    if abs(load.Fz) > 1e-6:
        labels.append(f"Fz = {load.Fz:.2f} {force_unit}")

    Cy, Cz = bolt_group.Cy, bolt_group.Cz
    load_at_centroid = load.equivalent_at((0.0, Cy, Cz))

    if abs(load_at_centroid.Mx) > 1e-6:
        labels.append(f"Mx = {load_at_centroid.Mx:.2f} {force_unit}·{length_unit}")

    if labels:
        text = "\n".join(labels)
        dummy_lines = [Line2D([0], [0], color="red", linestyle="None", marker="x")]
        ax.legend(dummy_lines, [text], loc="upper left", title="Applied Load", framealpha=0.9)


def _plot_plate(ax: plt.Axes, plate: Plate) -> None:
    """Plot plate boundary as a prominent rectangle."""
    from matplotlib.patches import Rectangle

    rect = Rectangle(
        (plate.z_min, plate.y_min),
        plate.depth_z,
        plate.depth_y,
        linewidth=3,
        edgecolor="darkgray",
        facecolor="lightgray",
        alpha=0.3,
        zorder=1,
        label="Plate",
    )
    ax.add_patch(rect)


def _plot_neutral_axes(*, ax: plt.Axes, result: "BoltResult", bolt_group: BoltLayout) -> None:
    """Plot neutral axis lines used by the plate tension method."""
    plate = result.connection.plate
    if plate is None:
        return

    Cy, Cz = bolt_group.Cy, bolt_group.Cz
    load_at_centroid = result.load.equivalent_at((0.0, Cy, Cz))
    My = load_at_centroid.My
    Mz = load_at_centroid.Mz

    if abs(My) > 1e-6:
        d_z = plate.depth_z
        if result.tension_method == "conservative":
            na_z = float(bolt_group.Cz)
        else:
            comp_edge_z = plate.z_min if My > 0.0 else plate.z_max
            na_z = comp_edge_z + d_z / 6.0 if My > 0.0 else comp_edge_z - d_z / 6.0
        ax.axvline(na_z, color="blue", linestyle="--", linewidth=1.5, alpha=0.7, label="NA (My)", zorder=2)

    if abs(Mz) > 1e-6:
        d_y = plate.depth_y
        if result.tension_method == "conservative":
            na_y = float(bolt_group.Cy)
        else:
            comp_edge_y = plate.y_min if Mz > 0.0 else plate.y_max
            na_y = comp_edge_y + d_y / 6.0 if Mz > 0.0 else comp_edge_y - d_y / 6.0
        ax.axhline(na_y, color="green", linestyle="--", linewidth=1.5, alpha=0.7, label="NA (Mz)", zorder=2)


