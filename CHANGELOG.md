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
