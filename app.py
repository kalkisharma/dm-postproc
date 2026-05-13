"""Flask application: routes, SSE streaming, config management, browser launch."""

import json
import logging
import os
import threading
import webbrowser
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

from version import __phase__, __release_date__, __version__

log = logging.getLogger(__name__)

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


# ── Config helpers ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load config.json, recreating it with defaults if missing or corrupted."""
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge in any missing default keys
            merged = {**CONFIG_DEFAULTS, **data}
            return merged
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("config.json is corrupted (%s) — recreating with defaults", exc)
            CONFIG_PATH.unlink(missing_ok=True)

    cfg = dict(CONFIG_DEFAULTS)
    save_config(cfg)
    return cfg


def save_config(data: dict) -> None:
    """Persist a config dict to config.json."""
    try:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        log.error("Failed to save config.json: %s", exc)


# ── App factory ────────────────────────────────────────────────────────────────

def create_app() -> Flask:
    """Construct and configure the Flask application instance."""
    app = Flask(__name__)
    config_state: dict = load_config()

    # ── Static routes ──────────────────────────────────────────────────────────

    @app.get("/")
    def index():
        """Serve the single-page dashboard."""
        return render_template("index.html")

    @app.get("/api/version")
    def api_version():
        """Return version metadata from version.py."""
        return jsonify({
            "version":      __version__,
            "phase":        __phase__,
            "release_date": __release_date__,
        })

    @app.get("/api/system_info")
    def api_system_info():
        """Return host system information."""
        return jsonify({"cpu_count": os.cpu_count() or 1})

    @app.get("/api/config")
    def api_config_get():
        """Return the current config as JSON."""
        return jsonify(config_state)

    @app.post("/api/config")
    def api_config_post():
        """Merge request body into config and persist."""
        updates = request.get_json(silent=True) or {}
        config_state.update(updates)
        save_config(config_state)
        return jsonify({"ok": True})

    # ── File browser ───────────────────────────────────────────────────────────

    @app.get("/api/browse")
    def api_browse():
        """List directories (and optionally .csv files) at the requested path."""
        raw_path = request.args.get("path", "").strip()
        mode     = request.args.get("mode", "folder")  # "folder" | "csv"

        # Default to filesystem root(s) if no path given
        if not raw_path:
            import string
            if os.name == "nt":
                drives = [f"{d}:\\" for d in string.ascii_uppercase
                          if Path(f"{d}:\\").exists()]
                return jsonify({"dirs": drives, "files": [], "parent": "", "current": ""})
            raw_path = "/"

        try:
            current = Path(raw_path).resolve()
        except (OSError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

        if not current.exists():
            return jsonify({"error": f"Path does not exist: {current}"}), 404

        if not current.is_dir():
            current = current.parent

        try:
            entries = list(current.iterdir())
        except PermissionError:
            return jsonify({"error": "Permission denied"}), 403

        dirs  = sorted(str(e) for e in entries if e.is_dir())
        files = sorted(str(e) for e in entries if e.is_file() and e.suffix.lower() == ".csv") \
                if mode == "csv" else []
        parent = str(current.parent) if current.parent != current else ""

        return jsonify({
            "dirs":    dirs,
            "files":   files,
            "parent":  parent,
            "current": str(current),
        })

    # ── SSE processing stream ──────────────────────────────────────────────────

    @app.get("/api/stream_process")
    def api_stream_process():
        """Stream per-case processing progress as Server-Sent Events."""
        from processor import process_run_folder

        root_path    = request.args.get("root_path", "").strip()
        window_type  = request.args.get("window_type", "fractional")
        window_value = float(request.args.get("window_value", 0.2))
        n_workers    = int(request.args.get("n_workers", 1))
        output_path  = request.args.get("output_path", "").strip()

        if not root_path:
            return jsonify({"error": "root_path is required"}), 400

        root = Path(root_path)
        if not root.is_dir():
            return jsonify({"error": f"Not a directory: {root_path}"}), 400

        # Determine output CSV path
        if output_path:
            out_dir = Path(output_path)
        else:
            out_dir = root.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / f"{root.name}_postprocessed.csv"

        def event_stream():
            import json as _json
            total_cases: list[int] = [0]
            done_cases:  list[int] = [0]

            # First scan to know total
            from reader import scan_run_folder as _scan
            all_cases = _scan(root, config_state)
            total_cases[0] = len(all_cases)

            if total_cases[0] == 0:
                yield f"data: {_json.dumps({'done': True, 'output_path': '', 'summary': {'total': 0, 'ok': 0, 'warnings': 0, 'missing_data': 0, 'missing_params': 0, 'all_warnings': ['Run folder contains no case subdirectories']}, 'empty_run': True})}\n\n"
                return

            def callback(case_name: str, status: str, warnings: list):
                done_cases[0] += 1
                pct = round(done_cases[0] / max(total_cases[0], 1) * 100, 1)
                payload = _json.dumps({
                    "case":         case_name,
                    "status":       status,
                    "warnings":     warnings,
                    "progress_pct": pct,
                })
                yield f"data: {payload}\n\n"

            # We need to collect yields from callback — use a queue-based approach
            import queue
            q: queue.Queue = queue.Queue()

            def cb(case_name, status, warnings):
                done_cases[0] += 1
                pct = round(done_cases[0] / max(total_cases[0], 1) * 100, 1)
                q.put({"case": case_name, "status": status,
                       "warnings": warnings, "progress_pct": pct})

            results_holder: list = []
            summary_holder:  list = []
            exc_holder:      list = []

            def run():
                try:
                    merged_df, summary = process_run_folder(
                        root, config_state, window_type, window_value, n_workers, cb
                    )
                    results_holder.append(merged_df)
                    summary_holder.append(summary)
                except Exception as exc:
                    exc_holder.append(exc)
                finally:
                    q.put(None)  # sentinel

            t = threading.Thread(target=run, daemon=True)
            t.start()

            while True:
                item = q.get()
                if item is None:
                    break
                yield f"data: {_json.dumps(item)}\n\n"

            if exc_holder:
                yield f"data: {_json.dumps({'error': str(exc_holder[0])})}\n\n"
                return

            # Save CSV
            merged_df = results_holder[0] if results_holder else None
            summary   = summary_holder[0] if summary_holder else {}
            saved_path = ""
            if merged_df is not None and not merged_df.empty:
                try:
                    merged_df.to_csv(out_csv)
                    saved_path = str(out_csv)
                except OSError as exc:
                    yield f"data: {_json.dumps({'error': f'Failed to save CSV: {exc}'})}\n\n"
                    return

            yield f"data: {_json.dumps({'done': True, 'output_path': saved_path, 'summary': summary})}\n\n"

        return Response(event_stream(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ── CSV loading for Mode B ─────────────────────────────────────────────────

    @app.post("/api/load_csv")
    def api_load_csv():
        """Load a post-processed CSV and return columns and row data."""
        body = request.get_json(silent=True) or {}
        file_path = body.get("file_path", "").strip()
        if not file_path:
            return jsonify({"error": "file_path is required"}), 400

        p = Path(file_path)
        if not p.is_file():
            return jsonify({"error": f"File not found: {file_path}"}), 404

        try:
            import pandas as pd
            df = pd.read_csv(p, index_col=0)
            columns = list(df.columns)

            # Warn about all-NaN columns so frontend can inform user
            all_nan_cols = [c for c in df.columns if df[c].isna().all()]

            # Use pandas to_json → parse back so NaN becomes null (not the invalid JS NaN literal)
            df_with_index = df.copy()
            df_with_index.insert(0, "case_name", df.index)
            data = json.loads(df_with_index.to_json(orient="records"))
            columns = ["case_name"] + columns
            return jsonify({"columns": columns, "data": data,
                            "all_nan_columns": all_nan_cols})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Download ───────────────────────────────────────────────────────────────

    @app.get("/api/download")
    def api_download():
        """Serve a file as a downloadable attachment."""
        file_path = request.args.get("file_path", "").strip()
        if not file_path:
            return jsonify({"error": "file_path is required"}), 400
        p = Path(file_path)
        if not p.is_file():
            return jsonify({"error": f"File not found: {file_path}"}), 404
        try:
            return send_file(p.resolve(), as_attachment=True)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return app


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    threading.Timer(1.0, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(debug=False, use_reloader=False)
