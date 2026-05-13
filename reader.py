"""Folder scanning, CSV parsing, and case file detection."""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class CaseResult:
    """Holds the scan result for a single simulation case directory."""

    case_name: str
    status: str
    params_path: Path | None
    data_path: Path | None
    warnings: list[str] = field(default_factory=list)


def scan_run_folder(root_path: Path, config: dict) -> list[CaseResult]:
    """Walk root_path; treat each immediate subdirectory as a potential case.

    # TODO: string param support — stub for future non-numeric value handling
    """
    root = Path(root_path)
    results: list[CaseResult] = []

    for case_dir in sorted(root.iterdir()):
        if not case_dir.is_dir():
            continue

        params_path = case_dir / config["params_filename"]
        # Data CSV may be directly in case_dir or in a named subfolder
        data_direct    = case_dir / config["data_filename"]
        data_subfolder = case_dir / config["subfolder_name"] / config["data_filename"]

        found_params = params_path if params_path.is_file() else None
        if data_direct.is_file():
            found_data = data_direct
        elif data_subfolder.is_file():
            found_data = data_subfolder
        else:
            found_data = None

        if found_params is None and found_data is None:
            status = "missing_data"  # treat as skippable
        elif found_params is None:
            status = "missing_params"
        elif found_data is None:
            status = "missing_data"
        else:
            status = "ok"

        results.append(CaseResult(
            case_name=case_dir.name,
            status=status,
            params_path=found_params,
            data_path=found_data,
        ))

    return results


def parse_params_csv(path: Path) -> tuple[dict[str, float], list[str]]:
    """Read params CSV; coerce Data column to float, warn on non-numeric values."""
    warnings: list[str] = []
    params: dict[str, float] = {}

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return {}, [f"Could not read params CSV '{path.name}': {exc}"]

    for _, row in df.iterrows():
        name = str(row.get("Name", "")).strip()
        raw  = row.get("Data", "")
        try:
            params[name] = float(raw)
        except (ValueError, TypeError):
            params[name] = float("nan")
            warnings.append(
                f"Non-numeric value '{raw}' for parameter '{name}' in '{path.name}' — stored as NaN"
            )

    return params, warnings


def parse_data_csv(path: Path) -> tuple[pd.DataFrame, str]:
    """Read data CSV; detect iteration vs time mode from column headers."""
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise RuntimeError(f"Could not read data CSV '{path.name}': {exc}") from exc

    mode = "iteration"
    for col in df.columns:
        if "time" in col.lower():
            mode = "time"
            break

    return df, mode
