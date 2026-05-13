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

import numpy as np


np.random.seed(42)


def make_convergence(
    n_steps: int,
    final: float,
    initial: float,
    k: float,
    noise: float,
) -> np.ndarray:
    """Generate a single exponential-convergence curve with Gaussian noise."""
    pass


def write_params_csv(path, aoa, mach, altitude, rpm, pitch, flap, v_inf, re, q_dyn):
    """Write simulation_parameters.csv for one case."""
    pass


def write_data_csv(path, n_iter, params, extra_monitors=False, time_based=False):
    """Write iteration_history.csv for one case."""
    pass


def generate():
    """Entry point: generate all 55 cases into ./sample_data/design_sweep_01/."""
    pass


if __name__ == "__main__":
    generate()
