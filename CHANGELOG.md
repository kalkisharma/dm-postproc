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
