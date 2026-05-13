# DM Post-Processor

![Version](https://img.shields.io/badge/version-v0.4.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-gray)

A post-processing dashboard for StarCCM+ Design Manager simulation runs.
Reads case output folders, averages convergence data over a configurable window,
and provides an interactive visualization dashboard.

## Current Version
**v0.4.0** — Phase 3: SSE Streaming & Mode A UI

## Phase History
| Phase | Version | Description | Status |
|-------|---------|-------------|--------|
| 0 | v0.1.0 | Repository setup & scaffold | ✅ Complete |
| 1 | v0.2.0 | Sample data generator | ✅ Complete |
| 2 | v0.3.0 | Backend core (reader, processor, Flask) | ✅ Complete |
| 3 | v0.4.0 | SSE streaming & Mode A UI | ✅ Complete |
| 4 | v1.0.0 | Visualization — Mode B (first stable release) | ⏳ Planned |
| 5 | v1.1.0 | Polish & robustness | ⏳ Planned |

## Installation
```bash
git clone https://github.com/kalkisharma/dm-postproc.git
cd dm-postproc
pip install -r requirements.txt
python generate_sample_data.py   # generate test data (run once)
python app.py                    # launch app — opens browser automatically
```

## Usage

### Mode A — Process raw data
1. Enter the path to your Design Manager run folder
2. Configure filenames (params CSV, data CSV, subfolder name) — saved automatically
3. Set averaging window: absolute (last N iterations or seconds) or fractional (last X%)
4. Set number of parallel workers (1 to cpu_count)
5. Click Run — monitor live per-case progress in the log
6. Download output CSV when complete

### Mode B — Visualize
1. Load a post-processed CSV output from Mode A
2. Select plot type: Scatter, Pair Matrix, or Custom
3. Configure axes and optional color-by parameter
4. Click Generate Plot

## Configuration
Settings are saved automatically to `config.json` (gitignored, never committed).
Includes: filenames, last used paths, window settings, worker count, theme preference.
If `config.json` is missing or corrupted it is recreated automatically with safe defaults.

## Planned Features
- String/label parameter support in params CSV (`# TODO` stub in `reader.py`)
- Data cleaning and outlier detection hooks (`# TODO` stub in `processor.py`)
- Multi-CSV comparison in Mode B

## License
MIT
