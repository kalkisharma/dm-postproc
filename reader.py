"""Folder scanning, CSV parsing, and case file detection."""

from dataclasses import dataclass, field
from pathlib import Path
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
    pass


def parse_params_csv(path: Path) -> tuple[dict[str, float], list[str]]:
    """Read params CSV; coerce Data column to float, warn on non-numeric values."""
    pass


def parse_data_csv(path: Path) -> tuple[pd.DataFrame, str]:
    """Read data CSV; detect iteration vs time mode from column headers."""
    pass
