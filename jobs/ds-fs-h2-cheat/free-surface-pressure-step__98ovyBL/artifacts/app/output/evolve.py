#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def copy_field(field):
    return [row[:] for row in field]


def zero_solids(p, u, v, solid, nx, ny):
    for j in range(ny + 2):
        for i in range(nx + 2):
            if solid[j][i]:
                p[j][i] = 0.0
                if u is not None:
                    u[j][i] = 0.0
                if v is not None:
                    v[j][i] = 0.0


def boundary_pass(p, solid, nx, ny, outlet_grad, dx):
    for i in range(nx + 2):
        p[ny][i] = 0.0
    for i in range(1, nx + 1):
        p[ny + 1][i] = p[ny - 1][i]
    for i in range(1, nx + 1):
        p[0][i] = p[1][i]
    for j in range(1, ny):
        p[j][0] = p[j][1]
    for j in range(1, ny):
        p[j][nx + 1] = p[j][nx] + outlet_grad * dx
    for j in range(ny + 2):
        for i in range(nx + 2):
            if solid[j][i]:
                p[j][i] = 0.0
    p[0][0] = p[1][1]
    p[0][nx + 1] = p[1][nx] + outlet_grad * dx
    p[ny + 1][0] = p[ny - 1][1]
    p[ny + 1][nx + 1] = p[ny - 1][nx] + outlet_grad * dx
    for j in range(ny + 2):
        for i in range(nx + 2):
            if solid[j][i]:
                p[j][i] = 0.0


def velocity_boundary(u, v, solid, nx, ny):
    for i in range(1, nx + 1):
        u[0][i] = u[1][i]
        v[0][i] = v[1][i]
    for i in range(nx + 2):
        u[ny][i] = 0.0
        v[ny][i] = 0.0
    for i in range(1, nx + 1):
        u[ny + 1][i] = u[ny - 1][i]
        v[ny + 1][i] = v[ny - 1][i]
    for j in range(1, ny):
        u[j][0] = u[j][1]
        v[j][0] = v[j][1]
        u[j][nx + 1] = u[j][nx]
        v[j][nx + 1] = v[j][nx]
    for j in range(ny + 2):
        for i in range(nx + 2):
            if solid[j][i]:
                u[j][i] = 0.0
                v[j][i] = 0.0



def compute_div(u, v, solid, nx, ny, dx, dy):
    div = [[0.0 for _ in range(nx + 2)] for _ in range(ny + 2)]
    for j in range(1, ny):
        for i in range(1, nx + 1):
            if not solid[j][i]:
                div[j][i] = (
                    (u[j][i + 1] - u[j][i - 1]) / (2.0 * dx)
                    + (v[j + 1][i] - v[j - 1][i]) / (2.0 * dy)
                )
    return div


def jacobi_sweep(p_work, div, solid, nx, ny, dx, dy, rho, dt, omega):
    p_old = copy_field(p_work)
    p_jac = copy_field(p_old)
    dx2 = dx * dx
    dy2 = dy * dy
    denom = 2.0 / dx2 + 2.0 / dy2
    for j in range(1, ny):
        for i in range(1, nx + 1):
            if solid[j][i]:
                p_jac[j][i] = 0.0
            else:
                rhs = (rho / dt) * div[j][i]
                p_jac[j][i] = (
                    (p_old[j][i - 1] + p_old[j][i + 1]) / dx2
                    + (p_old[j - 1][i] + p_old[j + 1][i]) / dy2
                    - rhs
                ) / denom
    for j in range(1, ny):
        for i in range(1, nx + 1):
            if not solid[j][i]:
                p_work[j][i] = (1.0 - omega) * p_work[j][i] + omega * p_jac[j][i]


def diagnostics(p, u, v, solid, nx, ny, dx, dy, outlet_grad):
    surface_abs_max = max(abs(p[ny][i]) for i in range(nx + 2))
    surface_ghost_abs_max = max(abs(p[ny + 1][i] - p[ny - 1][i]) for i in range(1, nx + 1))

    residuals = []
    for i in range(1, nx + 1):
        residuals.append(abs(p[0][i] - p[1][i]))
    for j in range(1, ny):
        residuals.append(abs(p[j][0] - p[j][1]))
        residuals.append(abs(p[j][nx + 1] - (p[j][nx] + outlet_grad * dx)))
    wall_ghost_abs_max = max(residuals) if residuals else 0.0

    div = compute_div(u, v, solid, nx, ny, dx, dy)
    div_abs_max = 0.0
    for j in range(1, ny):
        for i in range(1, nx + 1):
            if not solid[j][i]:
                div_abs_max = max(div_abs_max, abs(div[j][i]))

    pressure_abs_max = max(abs(value) for row in p for value in row)
    all_finite = 1.0
    for field in (p, u, v):
        for row in field:
            for value in row:
                if not math.isfinite(value):
                    all_finite = 0.0
    return {
        "surface_abs_max": surface_abs_max,
        "surface_ghost_abs_max": surface_ghost_abs_max,
        "wall_ghost_abs_max": wall_ghost_abs_max,
        "div_abs_max": div_abs_max,
        "pressure_abs_max": pressure_abs_max,
        "all_finite": all_finite,
    }


def evolve(case):
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
    solid = case["solid"]

    p = copy_field(case["p0"])
    u = copy_field(case["u0"])
    v = copy_field(case["v0"])

    zero_solids(p, u, v, solid, nx, ny)
    boundary_pass(p, solid, nx, ny, outlet_grad, dx)

    u_prev = copy_field(u)
    v_prev = copy_field(v)
    trace = []

    for step in range(1, n_steps + 1):
        u_pred = copy_field(u)
        v_pred = copy_field(v)
        for j in range(1, ny):
            for i in range(1, nx + 1):
                if not solid[j][i]:
                    u_pred[j][i] = u[j][i] + (u[j][i] - u_prev[j][i])
                    v_pred[j][i] = v[j][i] + (v[j][i] - v_prev[j][i])
        velocity_boundary(u_pred, v_pred, solid, nx, ny)

        div = compute_div(u_pred, v_pred, solid, nx, ny, dx, dy)

        p_work = copy_field(p)
        for _ in range(n_inner):
            jacobi_sweep(p_work, div, solid, nx, ny, dx, dy, rho, dt, omega)
            for i in range(nx + 2):
                p_work[ny][i] = 0.0
            boundary_pass(p_work, solid, nx, ny, outlet_grad, dx)

        u_new = copy_field(u_pred)
        v_new = copy_field(v_pred)
        for j in range(1, ny):
            for i in range(1, nx + 1):
                if not solid[j][i]:
                    u_new[j][i] = u_pred[j][i] - dt / (2.0 * rho * dx) * (p_work[j][i + 1] - p_work[j][i - 1])
                    v_new[j][i] = v_pred[j][i] - dt / (2.0 * rho * dy) * (p_work[j + 1][i] - p_work[j - 1][i])
        velocity_boundary(u_new, v_new, solid, nx, ny)

        u_prev = copy_field(u)
        v_prev = copy_field(v)
        p = p_work
        u = u_new
        v = v_new

        final_div = compute_div(u, v, solid, nx, ny, dx, dy)
        final_div_abs_max = 0.0
        for j in range(1, ny):
            for i in range(1, nx + 1):
                if not solid[j][i]:
                    final_div_abs_max = max(final_div_abs_max, abs(final_div[j][i]))
        pressure_abs_max = max(abs(value) for row in p for value in row)
        trace.append({
            "step": float(step),
            "pressure_abs_max": pressure_abs_max,
            "div_abs_max": final_div_abs_max,
        })

    return {
        "pressure": p,
        "u": u,
        "v": v,
        "diagnostics": diagnostics(p, u, v, solid, nx, ny, dx, dy, outlet_grad),
        "trace": trace,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("/app/output"))
    args = parser.parse_args()

    case = json.loads(args.case.read_text(encoding="utf-8"))
    result = evolve(case)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "pressure.json").write_text(json.dumps(result["pressure"], indent=2) + "\n", encoding="utf-8")
    (args.out / "velocity.json").write_text(
        json.dumps({"u": result["u"], "v": result["v"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out / "diagnostics.json").write_text(
        json.dumps(result["diagnostics"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out / "trace.json").write_text(json.dumps(result["trace"], indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
