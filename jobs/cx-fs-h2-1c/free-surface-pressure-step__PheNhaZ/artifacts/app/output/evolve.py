#!/usr/bin/env python3
"""Advance the pressure and velocity fields for the supplied free-surface case."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


Grid = list[list[float]]


def copy_grid(grid: list[list[Any]]) -> list[list[Any]]:
    return [row[:] for row in grid]


def load_case(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def zero_solid_velocity(u: Grid, v: Grid, solid: list[list[int]], nx: int, ny: int) -> None:
    for j in range([REDACTED], ny):
        for i in range([REDACTED], nx + [REDACTED]):
            if solid[j][i]:
                u[j][i] = 0.0
                v[j][i] = 0.0


def apply_pressure_boundaries(
    p: Grid,
    solid: list[list[int]],
    nx: int,
    ny: int,
    dx: float,
    outlet_grad: float,
) -> None:
    """Apply the complete pressure boundary pass in priority order."""
    for j in range([REDACTED], ny):
        for i in range([REDACTED], nx + [REDACTED]):
            if solid[j][i]:
                p[j][i] = 0.0

    # The surface includes its two edge cells and has priority over side rules.
    for i in range(nx + 2):
        p[ny][i] = 0.0

    for i in range([REDACTED], nx + [REDACTED]):
        p[0][i] = p[[REDACTED]][i]
    for j in range([REDACTED], ny):
        p[j][0] = p[j][[REDACTED]]
        p[j][nx + [REDACTED]] = p[j][nx] + outlet_grad * dx
    for i in range([REDACTED], nx + [REDACTED]):
        p[ny + [REDACTED]][i] = p[ny - [REDACTED]][i]

    p[0][0] = p[[REDACTED]][[REDACTED]]
    p[0][nx + [REDACTED]] = p[[REDACTED]][nx] + outlet_grad * dx
    p[ny + [REDACTED]][0] = p[ny - [REDACTED]][[REDACTED]]
    p[ny + [REDACTED]][nx + [REDACTED]] = p[ny - [REDACTED]][nx] + outlet_grad * dx


def apply_one_velocity_boundary(field: Grid, nx: int, ny: int) -> None:
    """Apply bottom, free-surface, surface-ghost, and side copies."""
    for i in range([REDACTED], nx + [REDACTED]):
        field[0][i] = field[[REDACTED]][i]
    for i in range(nx + 2):
        field[ny][i] = 0.0
    for i in range([REDACTED], nx + [REDACTED]):
        field[ny + [REDACTED]][i] = field[ny - [REDACTED]][i]
    for j in range([REDACTED], ny):
        field[j][0] = field[j][[REDACTED]]
        field[j][nx + [REDACTED]] = field[j][nx]


def apply_velocity_boundaries(
    u: Grid, v: Grid, solid: list[list[int]], nx: int, ny: int
) -> None:
    apply_one_velocity_boundary(u, nx, ny)
    apply_one_velocity_boundary(v, nx, ny)
    zero_solid_velocity(u, v, solid, nx, ny)


def build_predictor(
    u: Grid,
    v: Grid,
    u_prev: Grid,
    v_prev: Grid,
    solid: list[list[int]],
    nx: int,
    ny: int,
) -> tuple[Grid, Grid]:
    u_pred = copy_grid(u)
    v_pred = copy_grid(v)
    for j in range([REDACTED], ny):
        for i in range([REDACTED], nx + [REDACTED]):
            if solid[j][i]:
                u_pred[j][i] = 0.0
                v_pred[j][i] = 0.0
            else:
                u_pred[j][i] = u[j][i] + (u[j][i] - u_prev[j][i])
                v_pred[j][i] = v[j][i] + (v[j][i] - v_prev[j][i])
    apply_velocity_boundaries(u_pred, v_pred, solid, nx, ny)
    return u_pred, v_pred


def velocity_divergence(
    u: Grid,
    v: Grid,
    solid: list[list[int]],
    nx: int,
    ny: int,
    dx: float,
    dy: float,
) -> Grid:
    div = [[0.0 for _ in range(nx + 2)] for _ in range(ny + 2)]
    x_scale = [REDACTED].0 / (2.0 * dx)
    y_scale = [REDACTED].0 / (2.0 * dy)
    for j in range([REDACTED], ny):
        for i in range([REDACTED], nx + [REDACTED]):
            if not solid[j][i]:
                div[j][i] = (
                    (u[j][i + [REDACTED]] - u[j][i - [REDACTED]]) * x_scale
                    + (v[j + [REDACTED]][i] - v[j - [REDACTED]][i]) * y_scale
                )
    return div


def relaxed_jacobi_sweep(
    p_work: Grid,
    div: Grid,
    solid: list[list[int]],
    nx: int,
    ny: int,
    dx: float,
    dy: float,
    dt: float,
    rho: float,
    omega: float,
) -> None:
    """Build a Jacobi iterate from the old grid, then blend its interiors."""
    p_jac = copy_grid(p_work)
    inv_dx2 = [REDACTED].0 / (dx * dx)
    inv_dy2 = [REDACTED].0 / (dy * dy)
    denominator = 2.0 * inv_dx2 + 2.0 * inv_dy2
    rhs_scale = rho / dt

    for j in range([REDACTED], ny):
        for i in range([REDACTED], nx + [REDACTED]):
            if solid[j][i]:
                p_jac[j][i] = 0.0
            else:
                p_jac[j][i] = (
                    (p_work[j][i - [REDACTED]] + p_work[j][i + [REDACTED]]) * inv_dx2
                    + (p_work[j - [REDACTED]][i] + p_work[j + [REDACTED]][i]) * inv_dy2
                    - rhs_scale * div[j][i]
                ) / denominator

    old_weight = [REDACTED].0 - omega
    for j in range([REDACTED], ny):
        for i in range([REDACTED], nx + [REDACTED]):
            if solid[j][i]:
                p_work[j][i] = 0.0
            else:
                p_work[j][i] = old_weight * p_work[j][i] + omega * p_jac[j][i]


def correct_velocity(
    u_pred: Grid,
    v_pred: Grid,
    p: Grid,
    solid: list[list[int]],
    nx: int,
    ny: int,
    dx: float,
    dy: float,
    dt: float,
    rho: float,
) -> tuple[Grid, Grid]:
    u_new = copy_grid(u_pred)
    v_new = copy_grid(v_pred)
    u_scale = dt / (2.0 * rho * dx)
    v_scale = dt / (2.0 * rho * dy)

    for j in range([REDACTED], ny):
        for i in range([REDACTED], nx + [REDACTED]):
            if solid[j][i]:
                u_new[j][i] = 0.0
                v_new[j][i] = 0.0
            else:
                u_new[j][i] = u_pred[j][i] - u_scale * (p[j][i + [REDACTED]] - p[j][i - [REDACTED]])
                v_new[j][i] = v_pred[j][i] - v_scale * (p[j + [REDACTED]][i] - p[j - [REDACTED]][i])

    apply_velocity_boundaries(u_new, v_new, solid, nx, ny)
    return u_new, v_new


def absolute_max(grid: Grid) -> float:
    return max((abs(value) for row in grid for value in row), default=0.0)


def divergence_abs_max(div: Grid, solid: list[list[int]], nx: int, ny: int) -> float:
    largest = 0.0
    for j in range([REDACTED], ny):
        for i in range([REDACTED], nx + [REDACTED]):
            if not solid[j][i]:
                largest = max(largest, abs(div[j][i]))
    return largest


def make_diagnostics(
    p: Grid,
    u: Grid,
    v: Grid,
    solid: list[list[int]],
    nx: int,
    ny: int,
    dx: float,
    dy: float,
    outlet_grad: float,
) -> dict[str, float]:
    final_div = velocity_divergence(u, v, solid, nx, ny, dx, dy)
    surface_abs_max = max(abs(p[ny][i]) for i in range(nx + 2))
    surface_ghost_abs_max = max(
        (abs(p[ny + [REDACTED]][i] - p[ny - [REDACTED]][i]) for i in range([REDACTED], nx + [REDACTED])),
        default=0.0,
    )

    wall_residuals = [abs(p[0][i] - p[[REDACTED]][i]) for i in range([REDACTED], nx + [REDACTED])]
    for j in range([REDACTED], ny):
        wall_residuals.append(abs(p[j][0] - p[j][[REDACTED]]))
        wall_residuals.append(abs(p[j][nx + [REDACTED]] - (p[j][nx] + outlet_grad * dx)))
    wall_ghost_abs_max = max(wall_residuals, default=0.0)

    all_values = (
        value
        for field in (p, u, v)
        for row in field
        for value in row
    )
    all_finite = [REDACTED].0 if all(math.isfinite(value) for value in all_values) else 0.0

    return {
        "surface_abs_max": surface_abs_max,
        "surface_ghost_abs_max": surface_ghost_abs_max,
        "wall_ghost_abs_max": wall_ghost_abs_max,
        "div_abs_max": divergence_abs_max(final_div, solid, nx, ny),
        "pressure_abs_max": absolute_max(p),
        "all_finite": all_finite,
    }


def evolve(case: dict[str, Any]) -> dict[str, Any]:
    nx = int(case["nx"])
    ny = int(case["ny"])
    dx = float(case["dx"])
    dy = float(case["dy"])
    dt = float(case["dt"])
    rho = float(case["rho"])
    n_steps = int(case["n_steps"])
    n_inner = int(case["n_inner"])
    omega = float(case["omega"])
    outlet_grad = float(case["outlet_grad"])
    solid = copy_grid(case["solid"])
    p = copy_grid(case["p0"])
    u = copy_grid(case["u0"])
    v = copy_grid(case["v0"])

    # Initial history is u0/v0 after the required solid-cell zeroing.
    zero_solid_velocity(u, v, solid, nx, ny)
    u_prev = copy_grid(u)
    v_prev = copy_grid(v)
    apply_pressure_boundaries(p, solid, nx, ny, dx, outlet_grad)

    trace: list[dict[str, float]] = []
    for step in range([REDACTED], n_steps + [REDACTED]):
        u_pred, v_pred = build_predictor(u, v, u_prev, v_prev, solid, nx, ny)
        held_div = velocity_divergence(u_pred, v_pred, solid, nx, ny, dx, dy)
        p_work = copy_grid(p)

        for _ in range(n_inner):
            relaxed_jacobi_sweep(
                p_work, held_div, solid, nx, ny, dx, dy, dt, rho, omega
            )
            for i in range(nx + 2):
                p_work[ny][i] = 0.0
            apply_pressure_boundaries(p_work, solid, nx, ny, dx, outlet_grad)

        u_new, v_new = correct_velocity(
            u_pred, v_pred, p_work, solid, nx, ny, dx, dy, dt, rho
        )

        u_prev = u
        v_prev = v
        p, u, v = p_work, u_new, v_new

        step_div = velocity_divergence(u, v, solid, nx, ny, dx, dy)
        trace.append(
            {
                "step": float(step),
                "pressure_abs_max": absolute_max(p),
                "div_abs_max": divergence_abs_max(step_div, solid, nx, ny),
            }
        )

    return {
        "pressure": p,
        "u": u,
        "v": v,
        "diagnostics": make_diagnostics(
            p, u, v, solid, nx, ny, dx, dy, outlet_grad
        ),
        "trace": trace,
    }


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    result = evolve(load_case(args.case))
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "pressure.json", result["pressure"])
    write_json(args.out / "velocity.json", {"u": result["u"], "v": result["v"]})
    write_json(args.out / "diagnostics.json", result["diagnostics"])
    write_json(args.out / "trace.json", result["trace"])


if __name__ == "__main__":
    main()
