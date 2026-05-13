"""Averaging, statistics computation, and cross-case merging."""

from pathlib import Path
import pandas as pd


def compute_case_stats(
    df: pd.DataFrame,
    mode: str,
    window_type: str,
    window_value: float,
) -> tuple[dict, list[str]]:
    """Compute mean/min/max/std/n for each data column over the specified window.

    # TODO: data cleaning hook — stub for future outlier detection / NaN handling
    """
    pass


def merge_cases(results_list: list[dict]) -> pd.DataFrame:
    """Union-merge per-case stat dicts into a single DataFrame (one row per case)."""
    pass


def build_summary(cases: list, results: list[dict]) -> dict:
    """Aggregate per-case results into a run-level summary dict."""
    pass


def process_run_folder(
    root_path: Path,
    config: dict,
    window_type: str,
    window_value: float,
    n_workers: int,
    progress_callback,
) -> tuple[pd.DataFrame, dict]:
    """Scan and process all cases in root_path using a multiprocessing pool."""
    pass
