# DM Post-Processor

![Version](https://img.shields.io/badge/version-v1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-gray)

A post-processing dashboard for StarCCM+ Design Manager simulation runs.
Reads case output folders, averages convergence data over a configurable window,
and provides an interactive visualization dashboard.

## Current Version
**v1.1.0** — Phase 5: Polish & Robustness

## Phase History
| Phase | Version | Description | Status |
|-------|---------|-------------|--------|
| 0 | v0.1.0 | Repository setup & scaffold | ✅ Complete |
| 1 | v0.2.0 | Sample data generator | ✅ Complete |
| 2 | v0.3.0 | Backend core (reader, processor, Flask) | ✅ Complete |
| 3 | v0.4.0 | SSE streaming & Mode A UI | ✅ Complete |
| 4 | v1.0.0 | Visualization — Mode B (first stable release) | ✅ Complete |
| 5 | v1.1.0 | Polish & robustness | ✅ Complete |

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
3. Set averaging window:
   - **Fractional**: last X% of all rows (e.g. 20 = last 20%)
   - **Absolute**: last N iterations, or last N seconds for time-based cases
4. Set number of parallel workers (1 to cpu_count)
5. Click **Run** — monitor live per-case progress in the log
   - ✓ green: converged successfully
   - ⚠ yellow: processed with warnings (click row to expand details)
   - ✗ red: missing data or params CSV — case skipped
6. Download output CSV when processing is complete

### Mode B — Visualize
1. Switch to **Visualize** tab
2. Enter or browse to a post-processed CSV from Mode A and click **Load CSV**
3. Select plot type:
   - **Scatter**: one X vs one Y, optional continuous color axis, std error bars
   - **Pair Matrix**: Plotly splom across selected columns
   - **Custom**: multiple Y series on a shared X axis
4. Click **Generate Plot**

### Keyboard / UI shortcuts
- **Theme toggle** (header) — switch between dark and light mode; Plotly chart re-renders automatically
- **Browse** buttons (📁) — navigate the filesystem to select paths without typing
- **Collapsible** "File Settings" section — click the header to collapse/expand

## Configuration
Settings are saved automatically to `config.json` (gitignored, never committed).
Persisted fields:

| Key | Default | Description |
|-----|---------|-------------|
| `params_filename` | `simulation_parameters.csv` | Name of the parameters CSV inside each case folder |
| `data_filename` | `iteration_history.csv` | Name of the convergence data CSV |
| `subfolder_name` | `monitors` | Subfolder containing the data CSV (leave blank if same level as params) |
| `last_run_folder` | `""` | Most recently used run folder path |
| `last_output_folder` | `""` | Most recently used output folder path |
| `last_window_type` | `fractional` | `fractional` or `absolute` |
| `last_window_value` | `0.2` | Window size (fraction 0–1 or absolute row/second count) |
| `last_n_workers` | `1` | Number of parallel worker processes |
| `theme` | `dark` | `dark` or `light` |

If `config.json` is missing or JSON-invalid it is recreated automatically with safe defaults.

## Data format

### Run folder structure
```
design_sweep_01/
└── case_001/
    ├── simulation_parameters.csv    # params_filename
    └── monitors/                   # subfolder_name
        └── iteration_history.csv   # data_filename
```

### simulation_parameters.csv
```
Name,Data,Units
Angle_of_Attack,5.0,deg
Mach_Number,0.3,--
```

### iteration_history.csv (iteration-based)
```
Iteration,CL,CD,CM,...
1,0.12,0.031,...
2,0.19,0.029,...
```

### iteration_history.csv (time-based)
Column header containing "time" (case-insensitive) triggers time mode.
```
Physical_Time,CL,CD,...
0.001,0.12,...
```

### Output CSV schema
Param columns first (alphabetical), then stat columns grouped by quantity:
```
case_name, Altitude, Angle_of_Attack, ..., CL_mean, CL_min, CL_max, CL_std, CL_n, CD_mean, ...
```

## Planned Features
The following stubs are in place for future development:

- **String/label parameter support** — `# TODO: string param support` stub in `reader.py:scan_run_folder`.
  Currently non-numeric parameter values are stored as NaN with a warning. Future work: preserve the
  string value as a separate label column in the output CSV.

- **Data cleaning / outlier detection** — `# TODO: data cleaning hook` stub in
  `processor.py:compute_case_stats`. Future work: pluggable hook to filter outliers or NaN rows
  before averaging.

- **Multi-CSV comparison in Mode B** — load two or more post-processed CSVs and overlay traces on the
  same Plotly chart for direct before/after or parameter-sweep comparison.

## License
MIT
