"""Synthetic StarCCM+ Design Manager run folder generator.

Produces ./sample_data/design_sweep_01/ with 55 cases covering six case types:
  - 25 clean iteration-based
  - 15 clean time-based
  -  8 extra monitor columns
  -  3 missing data CSV
  -  2 missing params CSV
  -  2 very short runs (10–20 iterations)

Run once: python generate_sample_data.py
Idempotent — safe to re-run; overwrites existing output.
"""

import shutil
from pathlib import Path

import numpy as np

np.random.seed(42)

OUTPUT_ROOT = Path(__file__).parent / "sample_data" / "design_sweep_01"


# ── Convergence curve ─────────────────────────────────────────────────────────

def make_convergence(
    n_steps: int,
    final: float,
    initial: float,
    k: float,
    noise: float,
) -> np.ndarray:
    """Generate a single exponential-convergence curve with Gaussian noise."""
    steps = np.arange(n_steps)
    return final + (initial - final) * np.exp(-k * steps) + noise * np.random.randn(n_steps)


# ── CSV writers ───────────────────────────────────────────────────────────────

def write_params_csv(
    path: Path,
    aoa: float,
    mach: float,
    altitude: float,
    rpm: float,
    pitch: float,
    flap: float,
    v_inf: float,
    re: float,
    q_dyn: float,
) -> None:
    """Write simulation_parameters.csv for one case."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ("Angle_of_Attack",     aoa,     "deg"),
        ("Mach_Number",         mach,    "--"),
        ("Altitude",            altitude,"ft"),
        ("Rotor_RPM",           rpm,     "RPM"),
        ("Blade_Pitch",         pitch,   "deg"),
        ("Flap_Deflection",     flap,    "deg"),
        ("Freestream_Velocity", v_inf,   "m/s"),
        ("Reynolds_Number",     re,      "--"),
        ("Dynamic_Pressure",    q_dyn,   "Pa"),
    ]
    with path.open("w", newline="") as f:
        f.write("Name,Data,Units\n")
        for name, val, unit in rows:
            f.write(f"{name},{val:.6g},{unit}\n")


def write_data_csv(
    path: Path,
    n_iter: int,
    aoa: float,
    mach: float,
    rpm: float,
    extra_monitors: bool = False,
    time_based: bool = False,
    dt: float = 0.005,
) -> None:
    """Write iteration_history.csv for one case."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # Physically motivated final values
    cl_final  = 0.3 + 0.08 * aoa - 0.002 * aoa ** 2
    cd0       = 0.025
    k_polar   = 0.05
    cd_final  = cd0 + k_polar * cl_final ** 2
    cm_final  = -0.05 - 0.002 * aoa
    thrust_final = 0.001 * rpm ** 2 * (1.0 + 0.1 * mach)
    cp_final  = -0.4 * (1.0 + 0.5 * mach)
    vel_final = mach * 340.0

    # Convergence parameters per quantity (varied slightly to look realistic)
    k_val  = np.random.uniform(0.003, 0.012)
    noise  = np.random.uniform(0.001, 0.005)

    cols = {
        "CL":                   make_convergence(n_iter, cl_final,     cl_final * 2.5,   k_val,       noise * 0.5),
        "CD":                   make_convergence(n_iter, cd_final,     cd_final * 3.0,   k_val * 0.8, noise * 0.2),
        "CM":                   make_convergence(n_iter, cm_final,     cm_final * 0.3,   k_val * 1.1, noise * 0.1),
        "Rotor_Thrust":         make_convergence(n_iter, thrust_final, thrust_final * 4, k_val * 0.6, noise * thrust_final * 0.1),
        "Pressure_Coefficient": make_convergence(n_iter, cp_final,     cp_final * 0.2,   k_val * 1.2, noise * 0.3),
        "Velocity_Magnitude":   make_convergence(n_iter, vel_final,    vel_final * 0.5,  k_val * 0.9, noise * vel_final * 0.02),
    }

    if extra_monitors:
        base_tap = -0.8 * (1 + 0.2 * mach)
        for i in range(1, 4):
            cols[f"Pressure_Tap_{i}"] = make_convergence(
                n_iter,
                base_tap * (1 + 0.05 * i),
                base_tap * 0.1,
                k_val * (0.9 + 0.05 * i),
                noise * 0.15,
            )

    with path.open("w", newline="") as f:
        if time_based:
            times = np.arange(n_iter) * dt
            header = "Physical_Time," + ",".join(cols.keys())
            f.write(header + "\n")
            for j in range(n_iter):
                row = f"{times[j]:.6f}," + ",".join(f"{v[j]:.8g}" for v in cols.values())
                f.write(row + "\n")
        else:
            header = "Iteration," + ",".join(cols.keys())
            f.write(header + "\n")
            for j in range(n_iter):
                row = f"{j + 1}," + ",".join(f"{v[j]:.8g}" for v in cols.values())
                f.write(row + "\n")


# ── Parameter helpers ─────────────────────────────────────────────────────────

def _make_params(case_idx: int) -> dict:
    """Derive a physically consistent parameter set from a case index."""
    aoa      = np.random.uniform(-5.0, 20.0)
    mach     = np.random.uniform(0.1, 0.9)
    altitude = np.random.uniform(0.0, 40000.0)
    rpm      = np.random.uniform(500.0, 3000.0)
    pitch    = np.random.uniform(0.0, 15.0)
    flap     = np.random.uniform(-5.0, 30.0)
    v_inf    = mach * 340.0
    rho      = 1.225 * np.exp(-altitude / 30000.0)  # rough ISA
    mu       = 1.81e-5
    chord    = 1.0
    re       = rho * v_inf * chord / mu
    q_dyn    = 0.5 * rho * v_inf ** 2
    return dict(aoa=aoa, mach=mach, altitude=altitude, rpm=rpm,
                pitch=pitch, flap=flap, v_inf=v_inf, re=re, q_dyn=q_dyn)


# ── Main generator ────────────────────────────────────────────────────────────

def generate() -> None:
    """Entry point: generate all 55 cases into ./sample_data/design_sweep_01/."""
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True)

    case_num = 1

    # ── 25 clean iteration-based ─────────────────────────────────────────────
    for _ in range(25):
        name = f"case_{case_num:03d}"
        p = _make_params(case_num)
        n_iter = int(np.random.randint(500, 2001))
        case_dir = OUTPUT_ROOT / name
        write_params_csv(case_dir / "simulation_parameters.csv", **p)
        write_data_csv(
            case_dir / "monitors" / "iteration_history.csv",
            n_iter, p["aoa"], p["mach"], p["rpm"],
        )
        case_num += 1

    # ── 15 clean time-based ───────────────────────────────────────────────────
    for _ in range(15):
        name = f"case_{case_num:03d}"
        p = _make_params(case_num)
        duration = np.random.uniform(5.0, 50.0)
        dt       = np.random.uniform(0.001, 0.01)
        n_iter   = int(duration / dt)
        case_dir = OUTPUT_ROOT / name
        write_params_csv(case_dir / "simulation_parameters.csv", **p)
        write_data_csv(
            case_dir / "monitors" / "iteration_history.csv",
            n_iter, p["aoa"], p["mach"], p["rpm"],
            time_based=True, dt=dt,
        )
        case_num += 1

    # ── 8 extra monitor cases ─────────────────────────────────────────────────
    for _ in range(8):
        name = f"case_{case_num:03d}"
        p = _make_params(case_num)
        n_iter = int(np.random.randint(500, 1501))
        case_dir = OUTPUT_ROOT / name
        write_params_csv(case_dir / "simulation_parameters.csv", **p)
        write_data_csv(
            case_dir / "monitors" / "iteration_history.csv",
            n_iter, p["aoa"], p["mach"], p["rpm"],
            extra_monitors=True,
        )
        case_num += 1

    # ── 3 missing data CSV ────────────────────────────────────────────────────
    for _ in range(3):
        name = f"case_{case_num:03d}"
        p = _make_params(case_num)
        case_dir = OUTPUT_ROOT / name
        write_params_csv(case_dir / "simulation_parameters.csv", **p)
        # intentionally omit data CSV and monitors subfolder
        case_num += 1

    # ── 2 missing params CSV ─────────────────────────────────────────────────
    for _ in range(2):
        name = f"case_{case_num:03d}"
        p = _make_params(case_num)
        n_iter = int(np.random.randint(500, 1001))
        case_dir = OUTPUT_ROOT / name
        write_data_csv(
            case_dir / "monitors" / "iteration_history.csv",
            n_iter, p["aoa"], p["mach"], p["rpm"],
        )
        # intentionally omit params CSV
        case_num += 1

    # ── 2 very short runs ────────────────────────────────────────────────────
    for _ in range(2):
        name = f"case_{case_num:03d}"
        p = _make_params(case_num)
        n_iter = int(np.random.randint(10, 21))
        case_dir = OUTPUT_ROOT / name
        write_params_csv(case_dir / "simulation_parameters.csv", **p)
        write_data_csv(
            case_dir / "monitors" / "iteration_history.csv",
            n_iter, p["aoa"], p["mach"], p["rpm"],
        )
        case_num += 1

    total = case_num - 1
    print(f"Generated {total} cases in {OUTPUT_ROOT}")

    # Quick verification
    types = {
        "iteration-based":  0,
        "time-based":       0,
        "extra-monitors":   0,
        "missing-data":     0,
        "missing-params":   0,
        "short-run":        0,
    }
    for case_dir in sorted(OUTPUT_ROOT.iterdir()):
        has_params = (case_dir / "simulation_parameters.csv").exists()
        data_path  = case_dir / "monitors" / "iteration_history.csv"
        has_data   = data_path.exists()
        if not has_data:
            types["missing-data"] += 1
        elif not has_params:
            types["missing-params"] += 1
        else:
            with data_path.open() as f:
                header = f.readline().strip().split(",")
                rows   = sum(1 for _ in f)
            if rows <= 20:
                types["short-run"] += 1
            elif any("pressure_tap" in c.lower() for c in header):
                types["extra-monitors"] += 1
            elif any("time" in c.lower() for c in header):
                types["time-based"] += 1
            else:
                types["iteration-based"] += 1

    print("\nCase type breakdown:")
    for t, n in types.items():
        print(f"  {t:20s}: {n}")


if __name__ == "__main__":
    generate()
