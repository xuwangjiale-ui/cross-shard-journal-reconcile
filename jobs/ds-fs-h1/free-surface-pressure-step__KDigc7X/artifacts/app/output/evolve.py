#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def load_case(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def copy_field(field):
    return [row[:] for row in field]


def boundary_pass(p, solid, nx, ny, dx, outlet_grad):
    for i in range(nx + 2):
        p[ny][i] = 0.0
    for j in range(1, ny):
        for i in range(1, nx + 1):
            if solid[j][i]:
                p[j][i] = 0.0
    for i in range(1, nx + 1):
        p[ny + 1][i] = p[ny - 1][i]
    for i in range(1, nx + 1):
        p[0][i] = p[1][i]
    for j in range(1, ny):
        p[j][0] = p[j][1]
        p[j][nx + 1] = p[j][nx] + outlet_grad * dx
    p[0][0] = p[1][1]
    p[0][nx + 1] = p[1][nx] + outlet_grad * dx
    p[ny + 1][0] = p[ny - 1][1]
    p[ny + 1][nx + 1] = p[ny - 1][nx] + outlet_grad * dx


def jacobi(p, div, solid, nx, ny, dx, dy, rho, dt):
    p_new = copy_field(p)
    dx2 = dx * dx
    dy2 = dy * dy
    denom = 2.0 / dx2 + 2.0 / dy2
    rhs_factor = rho / dt
    for j in range(1, ny):
        row = p[j]
        row_m = p[j - 1]
        row_p = p[j + 1]
        row_new = p_new[j]
        row_div = div[j]
        row_solid = solid[j]
        for i in range(1, nx + 1):
            if row_solid[i]:
                row_new[i] = 0.0
            else:
                rhs = rhs_factor * row_div[i]
                row_new[i] = (
                    (row[i - 1] + row[i + 1]) / dx2
                    + (row_m[i] + row_p[i]) / dy2
                    - rhs
                ) / denom
    return p_new


def compute_div(u, v, solid, nx, ny, dx, dy):
    div = [[0.0] * (nx + 2) for _ in range(ny + 2)]
    inv2dx = 1.0 / (2.0 * dx)
    inv2dy = 1.0 / (2.0 * dy)
    for j in range(1, ny):
        row_u = u[j]
        row_v = v[j]
        row_vm = v[j - 1]
        row_vp = v[j + 1]
        row_solid = solid[j]
        row_div = div[j]
        for i in range(1, nx + 1):
            if not row_solid[i]:
                row_div[i] = (
                    (row_u[i + 1] - row_u[i - 1]) * inv2dx
                    + (row_vp[i] - row_vm[i]) * inv2dy
                )
    return div


def correct_velocity(u, v, p_work, solid, nx, ny, dx, dy, dt, rho):
    u_new = copy_field(u)
    v_new = copy_field(v)
    cu = dt / (2.0 * rho * dx)
    cv = dt / (2.0 * rho * dy)
    for j in range(1, ny):
        row_u = u[j]
        row_v = v[j]
        row_p = p_work[j]
        row_pm = p_work[j - 1]
        row_pp = p_work[j + 1]
        row_un = u_new[j]
        row_vn = v_new[j]
        row_solid = solid[j]
        for i in range(1, nx + 1):
            if row_solid[i]:
                row_un[i] = 0.0
                row_vn[i] = 0.0
            else:
                row_un[i] = row_u[i] - cu * (row_p[i + 1] - row_p[i - 1])
                row_vn[i] = row_v[i] - cv * (row_pp[i] - row_pm[i])
    for i in range(1, nx + 1):
        u_new[0][i] = u_new[1][i]
        v_new[0][i] = v_new[1][i]
        u_new[ny][i] = 0.0
        v_new[ny][i] = 0.0
        u_new[ny + 1][i] = u_new[ny - 1][i]
        v_new[ny + 1][i] = v_new[ny - 1][i]
    for j in range(ny + 2):
        u_new[j][0] = u_new[j][1]
        u_new[j][nx + 1] = u_new[j][nx]
        v_new[j][0] = v_new[j][1]
        v_new[j][nx + 1] = v_new[j][nx]
    for j in range(ny + 2):
        for i in range(nx + 2):
            if solid[j][i]:
                u_new[j][i] = 0.0
                v_new[j][i] = 0.0
    return u_new, v_new


def evolve(case):
    nx = int(case['nx'])
    ny = int(case['ny'])
    dx = float(case['dx'])
    dy = float(case['dy'])
    dt = float(case['dt'])
    rho = float(case['rho'])
    n_steps = int(case['n_steps'])
    n_inner = int(case['n_inner'])
    outlet_grad = float(case['outlet_grad'])
    p = copy_field(case['p0'])
    u = copy_field(case['u0'])
    v = copy_field(case['v0'])
    solid = case['solid']
    boundary_pass(p, solid, nx, ny, dx, outlet_grad)
    for _ in range(n_steps):
        div = compute_div(u, v, solid, nx, ny, dx, dy)
        p_work = copy_field(p)
        for _ in range(n_inner):
            p_work = jacobi(p_work, div, solid, nx, ny, dx, dy, rho, dt)
            for i in range(nx + 2):
                p_work[ny][i] = 0.0
            boundary_pass(p_work, solid, nx, ny, dx, outlet_grad)
        u, v = correct_velocity(u, v, p_work, solid, nx, ny, dx, dy, dt, rho)
        p = p_work
    return p, u, v


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
                val = abs(div[j][i])
                if val > div_abs_max:
                    div_abs_max = val
    pressure_abs_max = max(abs(x) for row in p for x in row)
    finite = True
    for field in (p, u, v):
        for row in field:
            for x in row:
                if not math.isfinite(x):
                    finite = False
    return {
        'surface_abs_max': float(surface_abs_max),
        'surface_ghost_abs_max': float(surface_ghost_abs_max),
        'wall_ghost_abs_max': float(wall_ghost_abs_max),
        'div_abs_max': float(div_abs_max),
        'pressure_abs_max': float(pressure_abs_max),
        'all_finite': 1.0 if finite else 0.0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('/app/output'))
    args = parser.parse_args()
    case = load_case(args.case)
    p, u, v = evolve(case)
    diag = diagnostics(
        p, u, v, case['solid'],
        int(case['nx']), int(case['ny']),
        float(case['dx']), float(case['dy']), float(case['outlet_grad'])
    )
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / 'pressure.json', 'w', encoding='utf-8') as f:
        json.dump(p, f)
    with open(args.out / 'velocity.json', 'w', encoding='utf-8') as f:
        json.dump({'u': u, 'v': v}, f)
    with open(args.out / 'diagnostics.json', 'w', encoding='utf-8') as f:
        json.dump(diag, f, sort_keys=True)


if __name__ == '__main__':
    main()
