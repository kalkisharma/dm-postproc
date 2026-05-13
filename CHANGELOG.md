## [v1.0.0] — 2026-05-12 — Phase 4: Visualization Mode B

### Added
- Mode B fully operational: `/api/load_csv` returns columns + row data for any post-processed CSV
- Scatter plot: markers, continuous Viridis color scale, hover shows all param values, error bars from `_std` columns when present
- Pair matrix: Plotly splom across selected columns, first param column as color dimension
- Custom plot: multiple Y series on shared X axis, legend with column names, distinct color per series
- Stats summary table rendered below every plot showing case-by-case values
- Version badge in UI header populated live from `/api/version`
- Plotly layout uses CSS variable colors; re-renders on light/dark theme toggle
- `/api/load_csv` path accessible via file browser modal (mode="csv")

### Changed
- None

### Fixed
- None

### Breaking Changes
- None

---

## [v0.4.0] — 2026-05-12 — Phase 3: SSE Streaming & Mode A UI

### Added
- Full `index.html` single-page dashboard: Mode A + Mode B panels, path browser modal, progress bar, summary chips, download button
- Full `style.css`: complete design system with IBM Plex fonts, dark/light CSS variable themes, collapsible sidebar sections, animated case log rows, Plotly wrapper, stats table
- Full `main.js`: config round-trip (debounced 800ms), mode switch, theme toggle with Plotly re-render, window type radio, worker slider, SSE event consumer, animated log rows, path browser modal, Mode B scatter/pair/custom plot generators

### Changed
- None

### Fixed
- None

### Breaking Changes
- None

---

## [v0.3.0] — 2026-05-12 — Phase 2: Backend Core

### Added
- `reader.py`: `scan_run_folder` (detects ok/missing_data/missing_params), `parse_params_csv` (NaN on non-numeric with warning), `parse_data_csv` (time vs iteration auto-detection)
- `processor.py`: `compute_case_stats` with absolute (iteration + time) and fractional window modes; warns when window exceeds data; `merge_cases` union outer-join with param-first/alphabetical column order; `build_summary`; `process_run_folder` with `ProcessPoolExecutor` + `multiprocessing.Manager().Queue()` bridge
- `app.py`: full Flask factory — all 8 routes implemented; config auto-created/repaired on startup; browser opens automatically; `if __name__ == "__main__"` guard for Windows multiprocessing

### Changed
- None

### Fixed
- None

### Breaking Changes
- None

---

## [v0.2.0] — 2026-05-12 — Phase 1: Sample Data Generator

### Added
- `generate_sample_data.py` fully implemented — generates 55 synthetic cases
- Exponential convergence model: `final + (initial - final)*exp(-k*i) + noise`
- Physically plausible CL/CD polar, CM, Rotor_Thrust, Pressure_Coefficient, Velocity_Magnitude
- All 6 case types in correct counts (25 iteration, 15 time, 8 extra monitors, 3 missing data, 2 missing params, 2 short-run)
- Random seed fixed at 42 for reproducibility
- Built-in verification printout showing case type breakdown on every run

### Changed
- None

### Fixed
- None

### Breaking Changes
- None

---

## [v0.1.0] — 2026-05-12 — Phase 0: Repository Setup

### Added
- Full project file tree scaffolded as stub files with module docstrings
- `version.py` as single source of truth for version string (`v0.1.0`)
- `README.md` with installation instructions, usage guide, and phase history table
- `.gitignore` covering Python artefacts, `config.json`, and `sample_data/`
- `requirements.txt` with date-stamped header comment
- `reader.py` stub: `scan_run_folder`, `parse_params_csv`, `parse_data_csv`
- `processor.py` stub: `compute_case_stats`, `merge_cases`, `build_summary`, `process_run_folder`
- `app.py` stub: Flask app factory, config load/save, route placeholders
- `generate_sample_data.py` stub: convergence model helpers, case generators
- `templates/index.html` placeholder page with correct font and Plotly CDN links
- `static/style.css` stub: full CSS variable palette for dark and light themes
- `static/main.js` stub: DOMContentLoaded scaffold

### Changed
- None

### Fixed
- None

### Breaking Changes
- None
