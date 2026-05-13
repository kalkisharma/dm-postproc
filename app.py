"""Flask application: routes, SSE streaming, config management, browser launch."""

from pathlib import Path
from version import __version__, __phase__, __release_date__

CONFIG_DEFAULTS: dict = {
    "params_filename":    "simulation_parameters.csv",
    "data_filename":      "iteration_history.csv",
    "subfolder_name":     "monitors",
    "last_run_folder":    "",
    "last_output_folder": "",
    "last_window_type":   "fractional",
    "last_window_value":  0.2,
    "last_n_workers":     1,
    "theme":              "dark",
}

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """Load config.json, recreating it with defaults if missing or corrupted."""
    pass


def save_config(data: dict) -> None:
    """Persist a config dict to config.json."""
    pass


def create_app():
    """Construct and configure the Flask application instance."""
    pass


if __name__ == "__main__":
    pass
