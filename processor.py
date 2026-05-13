"""Averaging, statistics computation, and cross-case merging."""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from reader import CaseResult, parse_data_csv, parse_params_csv, scan_run_folder


# ── Core statistics ────────────────────────────────────────────────────────────

def compute_case_stats(
    df: pd.DataFrame,
    mode: str,
    window_type: str,
    window_value: float,
) -> tuple[dict, list[str]]:
    """Compute mean/min/max/std/n for each data column over the specified window.

    # TODO: data cleaning hook — stub for future outlier detection / NaN handling
    """
    warnings: list[str] = []

    # Identify the index column (Iteration or Physical_Time)
    index_col = None
    for col in df.columns:
        if col.lower() == "iteration" or "time" in col.lower():
            index_col = col
            break

    value_cols = [c for c in df.columns if c != index_col]

    # ── Select window rows ────────────────────────────────────────────────────
    if window_type == "fractional":
        frac = float(window_value)
        if frac <= 0 or frac > 1:
            frac = min(max(frac / 100.0, 0.01), 1.0)  # allow 1–100% input too
        n_rows = max(1, int(len(df) * frac))
        window_df = df.iloc[-n_rows:]
        if len(df) < 2:
            warnings.append(
                f"Very short run ({len(df)} rows) — used all available rows for statistics"
            )

    elif window_type == "absolute":
        if mode == "iteration":
            n_rows = int(window_value)
            if n_rows >= len(df):
                warnings.append(
                    f"Absolute window ({n_rows}) exceeds available data ({len(df)} rows) "
                    "— used all rows"
                )
                n_rows = len(df)
            window_df = df.iloc[-n_rows:]
        else:
            # time-based: filter rows where time >= max(time) - window_value
            time_col = index_col
            t_max = df[time_col].max()
            t_min_window = t_max - float(window_value)
            window_df = df[df[time_col] >= t_min_window]
            if len(window_df) == 0:
                warnings.append(
                    f"Absolute time window ({window_value}s) produced no rows — used all rows"
                )
                window_df = df
    else:
        window_df = df
        warnings.append(f"Unknown window_type '{window_type}' — used all rows")

    # ── Compute stats for each value column ───────────────────────────────────
    stats: dict = {}
    n_rows_used = len(window_df)

    for col in value_cols:
        series = window_df[col].dropna()
        if len(series) == 0:
            for suffix in ("mean", "min", "max", "std", "n"):
                stats[f"{col}_{suffix}"] = float("nan")
            continue
        stats[f"{col}_mean"] = float(series.mean())
        stats[f"{col}_min"]  = float(series.min())
        stats[f"{col}_max"]  = float(series.max())
        stats[f"{col}_std"]  = float(series.std())
        stats[f"{col}_n"]    = int(len(series))

    return stats, warnings


# ── Merging ────────────────────────────────────────────────────────────────────

def merge_cases(results_list: list[dict]) -> pd.DataFrame:
    """Union-merge per-case stat dicts into a single DataFrame (one row per case)."""
    rows = []
    for r in results_list:
        row: dict = {"case_name": r["case"]}
        row.update(r.get("params", {}))
        row.update(r.get("stats", {}))
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).set_index("case_name")

    # Separate param and stat columns; sort params alphabetically
    stat_suffixes = ("_mean", "_min", "_max", "_std", "_n")
    param_cols = sorted([c for c in df.columns if not any(c.endswith(s) for s in stat_suffixes)])
    stat_cols_raw = [c for c in df.columns if any(c.endswith(s) for s in stat_suffixes)]

    # Group stat columns by quantity name (preserving quantity order, stats ordered _mean/_min/_max/_std/_n)
    quantity_order: list[str] = []
    for col in stat_cols_raw:
        for suf in stat_suffixes:
            if col.endswith(suf):
                qty = col[: -len(suf)]
                if qty not in quantity_order:
                    quantity_order.append(qty)
                break

    stat_cols_ordered: list[str] = []
    for qty in quantity_order:
        for suf in stat_suffixes:
            c = f"{qty}{suf}"
            if c in df.columns:
                stat_cols_ordered.append(c)

    return df[param_cols + stat_cols_ordered]


def build_summary(cases: list[CaseResult], results: list[dict]) -> dict:
    """Aggregate per-case results into a run-level summary dict."""
    total = len(cases)
    ok = sum(1 for r in results if r["status"] in ("ok", "warning"))
    warnings_count = sum(1 for r in results if r["status"] == "warning")
    missing_data   = sum(1 for c in cases if c.status == "missing_data")
    missing_params = sum(1 for c in cases if c.status == "missing_params")
    all_warnings: list[str] = []
    for r in results:
        for w in r.get("warnings", []):
            all_warnings.append(f"[{r['case']}] {w}")
    return {
        "total":            total,
        "ok":               ok,
        "warnings":         warnings_count,
        "missing_data":     missing_data,
        "missing_params":   missing_params,
        "all_warnings":     all_warnings,
    }


# ── Worker (runs in subprocess) ────────────────────────────────────────────────

def _process_case_worker(
    case_result: CaseResult,
    config: dict,
    window_type: str,
    window_value: float,
    queue_proxy,
) -> None:
    """Run in worker process; put result dict into shared queue."""
    try:
        params, param_warnings = parse_params_csv(case_result.params_path)
        df, mode = parse_data_csv(case_result.data_path)
        stats, stat_warnings = compute_case_stats(df, mode, window_type, window_value)
        all_warnings = param_warnings + stat_warnings
        status = "warning" if all_warnings else "ok"
        queue_proxy.put({
            "case":     case_result.case_name,
            "status":   status,
            "warnings": all_warnings,
            "stats":    stats,
            "params":   params,
        })
    except Exception as exc:
        queue_proxy.put({
            "case":     case_result.case_name,
            "status":   "error",
            "warnings": [str(exc)],
            "stats":    {},
            "params":   {},
        })


# ── Orchestrator ───────────────────────────────────────────────────────────────

def process_run_folder(
    root_path: Path,
    config: dict,
    window_type: str,
    window_value: float,
    n_workers: int,
    progress_callback,
) -> tuple[pd.DataFrame, dict]:
    """Scan and process all cases in root_path using a multiprocessing pool."""
    cases    = scan_run_folder(root_path, config)
    ok_cases = [c for c in cases if c.status == "ok"]
    skip_cases = [c for c in cases if c.status != "ok"]

    for c in skip_cases:
        progress_callback(c.case_name, c.status, c.warnings)

    results: list[dict] = []

    if ok_cases:
        manager = multiprocessing.Manager()
        q = manager.Queue()

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            for c in ok_cases:
                executor.submit(_process_case_worker, c, config, window_type, window_value, q)

            received = 0
            while received < len(ok_cases):
                result = q.get()
                received += 1
                progress_callback(result["case"], result["status"], result["warnings"])
                results.append(result)

    merged_df = merge_cases(results)
    summary   = build_summary(cases, results)
    return merged_df, summary
