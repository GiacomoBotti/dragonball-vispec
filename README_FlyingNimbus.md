# Flying Nimbus

**Flying Nimbus** is a command-line Python tool for turning molecular dynamics trajectories into vibrational spectra.

It is designed for workflows where you already have:

- an equilibrium geometry in XYZ format,
- a Hessian or a previously exported hessian eigenvectors matrix (`cnorm.dat`),
- and a trajectory containing positions and **velocities**,

and you want to compute one or more of the following:

- **time-averaged (TA) spectra**,
- **correlation-function + Fourier-transform spectra**,
- **mode-resolved spectra** in **normal-mode space**,
- **Cartesian velocity autocorrelation spectra**,
- optional **CSV exports** for spreadsheet tools,
- and optional **PNG plots** for quick inspection.

The current implementation lives in a single script, `flying_nimbus.py`.

---

## Table of Contents

- [What Flying Nimbus does](#what-flying-nimbus-does)
- [Core workflow](#core-workflow)
- [Features at a glance](#features-at-a-glance)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [General command syntax](#general-command-syntax)
- [What the program expects as input](#what-the-program-expects-as-input)
  - [Equilibrium geometry (`--xyz`)](#equilibrium-geometry---xyz)
  - [Hessian (`--hess`)](#hessian---hess)
  - [Trajectory (`--traj`)](#trajectory---traj)
  - [`cnorm.dat` reuse (`--readcnorm 1`)](#cnormdat-reuse---readcnorm-1)
- [How Flying Nimbus works internally](#how-flying-nimbus-works-internally)
  - [Mass assignment](#mass-assignment)
  - [Building or loading the normal-mode basis](#building-or-loading-the-normal-mode-basis)
  - [Trajectory reading and unit handling](#trajectory-reading-and-unit-handling)
  - [Normal-mode projection](#normal-mode-projection)
  - [Correlation vs time-averaged spectra](#correlation-vs-time-averaged-spectra)
  - [Frequency grid construction](#frequency-grid-construction)
- [Coordinate systems](#coordinate-systems)
  - [Normal-mode mode (`--coord nm`)](#normal-mode-mode---coord-nm)
  - [Cartesian mode (`--coord cart`)](#cartesian-mode---coord-cart)
- [Detailed CLI reference](#detailed-cli-reference)
  - [System and structure options](#system-and-structure-options)
  - [Time and sampling options](#time-and-sampling-options)
  - [Spectral-grid options](#spectral-grid-options)
  - [Analysis mode options](#analysis-mode-options)
  - [Damping options](#damping-options)
  - [Selection options](#selection-options)
  - [Input/output options](#inputoutput-options)
  - [Plotting and spreadsheet export](#plotting-and-spreadsheet-export)
- [Outputs](#outputs)
  - [Normal-mode outputs](#normal-mode-outputs)
  - [Cartesian outputs](#cartesian-outputs)
  - [What is inside the `.dat` files](#what-is-inside-the-dat-files)
  - [CSV outputs](#csv-outputs)
  - [PNG outputs](#png-outputs)
  - [Atom-selection filename tags](#atom-selection-filename-tags)
- [Examples](#examples)
  - [1. Minimal normal-mode time-averaged spectrum](#1-minimal-normal-mode-time-averaged-spectrum)
  - [2. Correlation + FT instead of TA](#2-correlation--ft-instead-of-ta)
  - [3. Multiple vibrational modes at once](#3-multiple-vibrational-modes-at-once)
  - [4. Reuse an existing `cnorm.dat`](#4-reuse-an-existing-cnormdat)
  - [5. Cartesian VACF spectrum](#5-cartesian-spectrum)
  - [6. Analyze only selected atoms](#6-analyze-only-selected-atoms)
  - [7. Export CSV files for Excel or LibreOffice](#7-export-csv-files-for-excel-or-libreoffice)
  - [8. Merge multiple mode spectra into one CSV](#8-merge-multiple-mode-spectra-into-one-csv)
  - [9. Save PNG plots](#9-save-png-plots)
  - [10. Shift the printed frequency axis](#10-shift-the-printed-frequency-axis)
  - [11. Normalize spectra to a maximum of 1](#11-normalize-spectra-to-a-maximum-of-1)
  - [12. Overwrite an existing `cnorm.dat`](#12-overwrite-an-existing-cnormdat)
  - [13. Linear-molecule handling](#13-linear-molecule-handling)
  - [14. Start from a later MD step](#14-start-from-a-later-md-step)
- [Typical workflows](#typical-workflows)
  - [Workflow A: Hessian + trajectory → mode-resolved TA spectra](#workflow-a-hessian--trajectory--mode-resolved-ta-spectra)
  - [Workflow B: Precomputed `cnorm.dat` → fast repeat analyses](#workflow-b-precomputed-cnormdat--fast-repeat-analyses)
  - [Workflow C: Whole-system vs atom-projected comparison](#workflow-c-whole-system-vs-atom-projected-comparison)
- [Units and conventions](#units-and-conventions)
- [Supported atomic symbols and masses](#supported-atomic-symbols-and-masses)
- [Important implementation notes](#important-implementation-notes)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [License](#license)
- [Authors](#authors)

---

## What Flying Nimbus does

Flying Nimbus analyzes MD trajectories using either:

1. **normal-mode coordinates** derived from a Hessian, or
2. **Cartesian velocities** directly.

In normal-mode mode, the script projects the trajectory onto the normal-mode basis and can compute:

- `cpp` correlations and spectra from projected velocities,
- `cqq` correlations and spectra from projected coordinates,
- **time-averaged** mode-resolved spectra,
- or **correlation + FT** mode-resolved spectra.

In Cartesian mode, the script computes the velocity autocorrelation and writes:

- the Cartesian correlation function (`cvv`),
- a Cartesian FT autocorrelation spectrum,
- or a Cartesian TA spectrum.

The tool is especially useful when you want:

- **mode-specific vibrational analysis** from trajectory data,
- atom-projected contributions,
- outputs that can be plotted quickly,
- or spreadsheet-friendly numeric exports.

---

## Core workflow

A typical Flying Nimbus run looks like this:

1. Read the equilibrium geometry from `--xyz`.
2. Determine `nat` either from `-N/--nat` or from the first line of the XYZ file.
3. Assign atomic masses using either:
   - the internal mass database, or
   - a fifth column in the XYZ atom lines.
4. Build the normal-mode basis by either:
   - reading the Hessian and diagonalizing the mass-weighted Hessian, or
   - reading an existing `cnorm.dat`.
5. Read the trajectory from `--traj`.
6. Optionally discard early MD steps with `--nstart`.
7. Choose one of two coordinate systems:
   - `--coord nm` for normal-mode analysis,
   - `--coord cart` for Cartesian analysis.
8. Choose one of two strategies:
   - **TA mode** (default), or
   - **autocorrelation** mode via `--no-ta`.
9. Write `.dat` outputs, and optionally CSV and PNG files.

That makes Flying Nimbus a post-processing tool that sits naturally after geometry/Hessian preparation and trajectory generation.

---

## Features at a glance

| Capability | Supported |
|---|---:|
| Read masses from XYZ fifth column | Yes |
| Fall back to internal masses | Yes |
| Build `cnorm` from Hessian | Yes |
| Reuse existing `cnorm.dat` | Yes |
| Normal-mode analysis | Yes |
| Cartesian analysis | Yes |
| Time-averaged spectra | Yes |
| Correlation + FT spectra | Yes |
| Mode selection | Yes |
| Atom subset selection (Atom-Wise Spectra)| Yes |
| CSV export | Yes |
| Merged multi-mode CSV export | Yes |
| PNG plot export | Yes |
| Frequency-axis offset | Yes |
| Per-spectrum max normalization | Yes |

---

## Requirements

### Required Python packages

- `numpy`

### Optional package

- `matplotlib` — only needed if you use `--plot`

### Standard-library modules used

- `argparse`
- `csv`
- `math`
- `re`
- `dataclasses`
- `pathlib`
- `typing`

### Python version

Any modern Python 3 version that supports dataclasses, type annotations, `pathlib`, and `numpy` should work.

---

## Installation

### Clone the repository

```bash
git clone https://github.com/giacomande95-oss/FLYINGNIMBUS_GUI.git
cd flying_nimbus
```

### Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install numpy matplotlib
```

If you do not need PNG plots, `numpy` is enough for core functionality.

### Check the CLI

```bash
python flying_nimbus.py --help
```

---

## Quick start

### Minimal normal-mode TA run (Recommended)

```bash
python flying_nimbus.py \
  --xyz geom.xyz \
  --hess Hessian_flat.out \
  --traj traj.xyz \
  --modes 1
```

This uses:

- normal-mode analysis (`--coord nm`, **default**),
- time-averaged spectra (TA on by **default**),
- automatic `nat` detection from the XYZ file if `-N` is not given,
- and writes spectra prefixed by `QCT_` unless you change it with `-o`.

### Correlation + FT mode (Legacy Mode)

```bash
python flying_nimbus.py \
  --xyz geom.xyz \
  --hess Hessian_flat.out \
  --traj traj.xyz \
  --modes 3 4 5 \
  --no-ta
```

This writes both correlation functions and FT spectra for the selected modes.

### Cartesian spectrum

```bash
python flying_nimbus.py \
  --xyz geom.xyz \
  --hess Hessian_flat.out \
  --traj traj.xyz \
  --coord cart
```

### Reuse an existing `cnorm.dat`

```bash
python flying_nimbus.py \
  --xyz geom.xyz \
  --traj traj.xyz \
  --readcnorm 1 \
  --cnorm cnorm.dat \
  --modes 2 7 8
```

---

## General command syntax

The general form is:

```bash
python flying_nimbus.py --xyz <geometry.xyz> --traj <trajectory.xyz> [options]
```

Normal-mode analysis usually looks like:

```bash
python flying_nimbus.py \
  --xyz <geometry.xyz> \
  --hess <hessian_file> \
  --traj <trajectory.xyz> \
  --modes <mode1> [mode2 mode3 ...]
```

Cartesian analysis usually looks like:

```bash
python flying_nimbus.py \
  --xyz <geometry.xyz> \
  --hess <hessian_file> \
  --traj <trajectory.xyz> \
  --coord cart
```

If `--readcnorm 1` is used, `--hess` is no longer required.

---

## What the program expects as input

### Equilibrium geometry (`--xyz`)

The XYZ file is required in every run.

The script expects standard XYZ layout:

```text
N
comment line
Atom1   x   y   z
Atom2   x   y   z
...
```

It also supports an **optional fifth column** on each atom line that provides the atomic mass in atomic units:

```text
3
water with explicit masses
O   0.000000   0.000000   0.000000   29156.96
H   0.758602   0.000000   0.504284    1837.15
H  -0.758602   0.000000   0.504284    1837.15
```

This is important when:

- you are using an element not present in the internal mass table,
- or you want to override the built-in masses.

The first line is also used to auto-detect `nat` when `-N/--nat` is omitted or set to `0`.

### Hessian (`--hess`)

The Hessian is required when `--readcnorm 0`.

The implementation expects:

- **two header lines** at the top of the file,
- followed by lower-triangle Hessian values,
- read as a single column

The script reconstructs a full symmetric `3N × 3N` matrix from those lower-triangle values.

The parser is flexible about whitespace and accepts Fortran-style `D` exponents.

### Trajectory (`--traj`)

The trajectory must be an **extended XYZ trajectory** containing, for each atom:

- element symbol,
- `x y z`,
- `vx vy vz`.

Each frame is read as:

```text
N
comment line
Atom1   x   y   z   vx   vy   vz
Atom2   x   y   z   vx   vy   vz
...
```

Important notes:

- Positions are assumed to be in **Ångström** and velocities in **bohr**.
- The file must contain complete frames with exactly `nat` atom lines per frame.

### `cnorm.dat` reuse (`--readcnorm 1`)

When you run with:

```bash
--readcnorm 1 --cnorm cnorm.dat
```

the script skips Hessian diagonalization and instead loads the normal-mode basis from `cnorm.dat`.

The current implementation supports:

1. the script’s own `cnorm.dat` layout, and
2. a fallback numeric layout labeled in the code as a legacy or alternate path.

This is useful when you want to:

- run multiple analyses without repeatedly diagonalizing the Hessian,
- keep a fixed normal-mode basis across repeated runs.

---

## How Flying Nimbus works internally

### Mass assignment

The script first reads symbols and masses from the equilibrium XYZ.

Masses are assigned as follows:

1. If a fifth column is present and numeric, that value is used.
2. Otherwise the script looks up the symbol in its internal mass database.
3. If the symbol is not present and no mass is provided, the run fails.

### Building or loading the normal-mode basis

There are two paths.

#### Path A: compute from Hessian

When `--readcnorm 0` (the default):

1. The lower-triangle Hessian is read and reconstructed.
2. The Hessian is mass-weighted.
3. The Hessian is diagonalized.
4. The eigenpairs are reordered so that **vibrational modes come first** and roto-translational modes are moved to the end.
5. A `cnorm.dat` file is written.

By design, the script writes `cnorm.dat` during this path. If the target file already exists, the run stops unless you pass:

```bash
--rm-cnorm
```

#### Path B: read from `cnorm.dat`

When `--readcnorm 1`, the script reads:

- the normal-mode matrix,
- and the eigenvalue-derived `deltaq` data,

from the `cnorm.dat` file itself.

### Trajectory reading and unit handling

The trajectory is read frame-by-frame from extended XYZ.

Internally:

- positions are stored as a `NT × 3N` array (`NT` being the number of steps),
- velocities are stored as a `NT × 3N` array (`NT` being the number of steps),
- positions are converted from Å to bohr,
- velocities are left numerically unchanged by the current version.

The script then discards the first `nstart - 1` frames.

### Normal-mode projection

In normal-mode execution, the code projects both:

- the velocity series `v`, and
- the coordinate series `x`,

into the normal-mode basis.

Before projection, each Cartesian degree of freedom is multiplied by `sqrt(mass)`, so the projection is performed in a mass-weighted way.

If `--atoms` is used in normal-mode mode, a Cartesian mask is applied **before** projection. This means only the selected atoms contribute to the projected signal.

### Correlation vs time-averaged spectra

Flying Nimbus implements two strategies, that in first approximation differ in the function that is Fourier transformed.

#### TA mode (default)

If you do nothing, TA is enabled.

For normal-mode analysis:

- `TA-cpp` is built from the projected velocity-like mode amplitudes,
- `TA-cqq` is built from the projected coordinate-like mode amplitudes.

For Cartesian analysis:

- a TA Cartesian spectrum is built directly from the selected Cartesian velocity series.

#### Correlation mode

If you pass `--no-ta`, the script instead computes correlations and then Fourier transforms them.

For normal-mode analysis:

- `cpp` is the mode-resolved correlation built from projected velocities,
- `cqq` is the mode-resolved correlation built from projected coordinates,
- each is Fourier transformed to produce `FT-cpp` and `FT-cqq` spectra.

For Cartesian analysis:

- a Cartesian `cvv` correlation is computed,
- then Fourier transformed to `FT-cvv_cartesian`.

### Frequency grid construction

The printed frequency axis is controlled by:

- `--init-wnumb`
- `--spec-res`
- `--wnumb-span`

The number of frequency points is computed internally as:

```text
nf = int(wnumb_span / spec_res)
```

So the output grid is:

```text
init_wnumb + i * spec_res,  for i = 0 .. nf-1
```

This means the upper edge is controlled by integer truncation. If `wnumb_span` is not an exact multiple of `spec_res`, the last printed point will be below the nominal span limit.

---

## Coordinate systems

### Normal-mode mode (`--coord nm`)

This is the default mode.

You **must** provide:

```bash
--modes ...
```

Mode indices are:

- **1-based**,
- interpreted as **vibrational mode indices**,
- and must lie between `1` and `nvib = 3N - nrototrasl`.

In this mode the script can generate:

- `cpp` correlations and spectra,
- `cqq` correlations and spectra,
- TA mode spectra,
- CSV exports per mode,
- merged CSV files across multiple modes,
- and PNG plots.

### Cartesian mode (`--coord cart`)

This mode skips mode selection and works directly in Cartesian velocity space.

In this mode:

- `--modes` is not used,
- atom selection still works,
- the output is a single Cartesian correlation/spectrum rather than one file per mode.

This is the right choice when you want a global or atom-projected velocity-autocorrelation-style spectrum without decomposing into normal modes.

---

## Detailed CLI reference

### System and structure options

#### `-N`, `--nat`

Number of atoms.

Default:

```text
0
```

Behavior:

- if `0`, the script reads `nat` from the first line of `--xyz`.
- if positive, that explicit value is used.

Example:

```bash
python flying_nimbus.py --xyz geom.xyz --traj traj.xyz --hess Hessian.out -N 24 --modes 1
```

#### `--nrototrasl`

Number of rotational + translational modes to exclude from the vibrational count.

Default:
```text
6
```

Use `5` for linear molecules.

Example:

```bash
python flying_nimbus.py --xyz co2.xyz --traj co2_traj.xyz --hess hess.dat --modes 1 2 3 --nrototrasl 5
```

### Time and sampling options

#### `--nstart`

First MD step to use, **1-based**.

Default:

```text
1
```

The script discards the first `nstart - 1` frames.

#### `--ncorr`

Length of the correlation window.

Default:

```text
2500
```

This affects both TA and correlation-based branches because it defines how many time points are used in the spectral transform.

#### `--nbeads`

Number of time origins.

Default:

```text
0
```

Behavior:

- `0` means automatic: the script uses as many origins as possible given `ncorr` and trajectory length.

#### `--nbeadsstep`

Stride between time origins.

Default:

```text
1
```

Use values larger than `1` to thin the set of time origins.

#### `--dt`

Time step in **atomic units**.

Default:

```text
8.2682749151502
```

This value is used directly in the correlation and FT machinery. The script does not infer it from the trajectory file.

### Spectral-grid options

#### `--init-wnumb`

Initial wavenumber in `cm^-1`.

Default:

```text
0
```

#### `--spec-res`

Spectral resolution in `cm^-1`.

Default:

```text
1
```

#### `--wnumb-span`

Total spectral span in `cm^-1`.

Default:

```text
5000
```

Example:

```bash
python flying_nimbus.py \
  --xyz geom.xyz --traj traj.xyz --hess Hessian.out \
  --modes 2 3 4 \
  --init-wnumb 500 --spec-res 2 --wnumb-span 3500
```

### Analysis mode options

#### `--coord {nm,cart}`

Select analysis in:

- `nm` = normal-mode space,
- `cart` = Cartesian space.

Default:

```text
nm
```

#### `--no-ta`

Disable time-averaged spectra and switch to correlation + FT mode.

Default behavior without this flag: **TA is on**.

### Damping options

These are only relevant in the `--no-ta` branch.

#### `--alpha-pow`

Gaussian damping applied to `cpp` correlations.

Default:

```text
0.0
```

#### `--alpha-dip`

Gaussian damping applied to `cqq` correlations.

Default:

```text
1e-8
```

Example:

```bash
python flying_nimbus.py \
  --xyz geom.xyz --traj traj.xyz --hess Hessian.out \
  --modes 5 6 --no-ta \
  --alpha-pow 1e-8 --alpha-dip 1e-8
```

### Selection options

#### `--modes`

List of **1-based vibrational mode indices**.

Required when `--coord nm`.

Examples:

```bash
--modes 1
```

```bash
--modes 3 4 5 6
```

#### `--atoms`

List of **1-based atom indices** to include.

Default: all atoms.

Examples:

```bash
--atoms 1 2 3
```

```bash
--atoms 5 8 9 10
```

**Behavior differs slightly by coordinate system:**

- in `nm` mode, selected atoms contribute through a Cartesian mask before projection;
- in `cart` mode, only selected atoms are used in the Cartesian velocity series.

If you explicitly provide all atoms, the script treats that as equivalent to no selection.

### Input/output options

#### `--xyz`

Required equilibrium geometry file.

#### `--hess`

Hessian file.

Required unless:

```bash
--readcnorm 1
```

#### `--traj`

Required extended XYZ trajectory with positions and velocities.

#### `--readcnorm {0,1}`

Choose whether to:

- `0`: compute `cnorm` from the Hessian,
- `1`: read `cnorm.dat` instead.

Default:

```text
0
```

#### `--cnorm`

Path to the `cnorm.dat` file.

Default:

```text
cnorm.dat
```

#### `-o`, `--output`

Root output prefix.

Default:

```text
QCT_
```

Example:

```bash
-o water_
```

#### `--freq-offset`

Shift the **printed output wavenumber axis** by this offset in `cm^-1`.

Default:

```text
0.0
```

This changes the written x-axis values, not the underlying trajectory itself.

#### `--norm1`

Normalize each printed spectrum so its maximum is `1`.

This is applied independently per spectrum.

#### `--rm-cnorm`

If the script is about to write `cnorm.dat` and that file already exists, remove it first.

Without this flag, an existing `cnorm.dat` causes the run to stop with a file-exists error.

### Plotting and spreadsheet export

#### `--plot`

Save PNG plots of the spectra.

#### `--plot-dir`

Directory where PNG plots are written.

Default:

```text
.
```

#### `--plot-dpi`

PNG resolution.

Default:

```text
200
```

#### `--excel`

Also write spreadsheet-friendly CSV or TSV output without comment headers.

#### `--excel-sep`

Delimiter used for spreadsheet export.

Default:

```text
,
```

Useful values include:

- `,`
- `;`
- `tab`

#### `--excel-merge`

In normal-mode runs with multiple selected modes, also write one merged CSV per spectrum type, with one column per selected mode.

---

## Outputs

Output filenames are built from:

- the root prefix from `-o/--output`,
- an optional atom-selection tag,
- the spectrum/correlation type,
- and, in normal-mode mode, the mode index.

### Normal-mode outputs

#### TA mode (default)

For each selected mode `X`, the script writes:

```text
<root>_TA-cpp_mode_X.dat
<root>_TA-cqq_mode_X.dat
```

If `--excel` is active, it also writes:

```text
<root>_TA-cpp_mode_X.csv
<root>_TA-cqq_mode_X.csv
```

If `--plot` is active, it also writes PNGs with matching basenames.

#### Correlation + FT mode (`--no-ta`)

For each selected mode `X`, the script writes:

```text
<root>_cpp_mode_X.dat
<root>_cqq_mode_X.dat
<root>_FT-cpp_mode_X.dat
<root>_FT-cqq_mode_X.dat
```

Optional CSV exports are added for both correlation and FT outputs.

### Cartesian outputs

#### TA Cartesian mode

```text
<root>_TA-cvv_cartesian.dat
```

#### Correlation + FT Cartesian mode

```text
<root>_cvv_cartesian.dat
<root>_FT-cvv_cartesian.dat
```

Optional `.csv` and `.png` companions may also be produced.

### What is inside the `.dat` files

#### Correlation files

The correlation writers produce two numeric columns:

- time in atomic units,
- correlation value.

Examples:

```text
0.000000000000e+00  1.234567890123e-03
8.268274915150e+00  9.876543210987e-04
...
```

#### Normal-mode spectrum files

The normal-mode spectrum writers include a large comment header containing:

- normal-mode frequencies in Hartree, eV, and `cm^-1`,
- normal-mode vector components,
- and the zero-point energy.

After the header, the actual spectrum is printed as two columns:

- wavenumber (`cm^-1`),
- intensity.

This means the `.dat` files in normal-mode mode are both **machine-readable** and **self-documented**, but they are not as convenient as CSV for spreadsheets.

#### Cartesian spectrum files

Cartesian `.dat` spectrum files include a smaller header with the zero-point energy followed by two-column spectrum data.

### CSV outputs

When `--excel` is active, the script writes clean tabular files without comment blocks.

Examples:

```text
wn_cm-1,intensity
0.000000,1.234567890123e-05
1.000000,1.456789012345e-05
...
```

Correlation CSV files use time-axis headers such as:

- `t_au,cpp`
- `t_au,cqq`
- `t_au,cvv`

Spectrum CSV files use:

- `wn_cm-1,intensity`

### PNG outputs

When `--plot` is enabled, the script writes one PNG per spectrum using the same basename as the `.dat` file.

Example:

```text
QCT_TA-cpp_mode_3.png
```

The plots:

- use wavenumber on the x-axis,
- intensity on the y-axis,
- suppress y tick labels in the saved figure,
- and are saved at the requested DPI.

### Atom-selection filename tags

If `--atoms` is used, Flying Nimbus appends an atom-selection tag to the root.

For example:

```bash
--atoms 1 2 3 5 8 9
```

becomes:

```text
_atoms_1-3_5_8-9
```

So a file may look like:

```text
QCT__atoms_1-3_5_8-9_TA-cpp_mode_4.dat
```

This compression makes filenames manageable even when you select multiple non-consecutive atoms.

---

## Examples

### 1. Minimal normal-mode time-averaged spectrum

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 1
```

What happens:

- `nat` is read from `eq.xyz` if not specified,
- `cnorm.dat` is computed from the Hessian,
- the trajectory is projected to normal modes,
- TA normal mode spectra are written for mode 1.

### 2. Correlation + FT instead of TA

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 2 3 \
  --no-ta
```

This produces both:

- correlation functions (`cpp`, `cqq`),
- and Fourier-transformed spectra (`FT-cpp`, `FT-cqq`).

### 3. Multiple vibrational modes at once

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 4 5 6 7
```

You get one spectrum file per selected mode.

### 4. Reuse an existing `cnorm.dat`

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --traj md.xyz \
  --readcnorm 1 \
  --cnorm cnorm.dat \
  --modes 4 5 6
```

This is useful when you are repeating analyses with different:

- `--nstart`
- `--ncorr`
- `--atoms`
- `--freq-offset`
- `--norm1`

without rebuilding the basis each time. It is also useful if you are working with a cleaned CNORM matrix. 

### 5. Cartesian spectrum

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --coord cart \
  --no-ta
```

This writes:

```text
QCT__cvv_cartesian.dat
QCT__FT-cvv_cartesian.dat
```

### 6. Analyze only selected atoms

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 7 8 9 \
  --atoms 1 2 3
```

This restricts the signal to atoms 1–3 and adds an atom-selection tag to the filenames.

### 7. Export CSV files for Excel or LibreOffice

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 2 3 \
  --excel
```

If your spreadsheet locale expects semicolons:

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 2 3 \
  --excel --excel-sep ';'
```

### 8. Merge multiple mode spectra into one CSV

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 3 4 5 6 \
  --excel --excel-merge
```

This adds merged files such as:

```text
QCT__TA-cpp_modes_3_4_5_6.csv
QCT__TA-cqq_modes_3_4_5_6.csv
```

or, in non-TA mode:

```text
QCT__FT-cpp_modes_3_4_5_6.csv
QCT__FT-cqq_modes_3_4_5_6.csv
```

### 9. Save PNG plots

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 10 11 \
  --plot --plot-dir spectra_png --plot-dpi 300
```

### 10. Shift the printed frequency axis

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 3 \
  --freq-offset 35.0
```

Useful when you want to compare with an externally corrected or empirically shifted reference axis.

### 11. Normalize spectra to a maximum of 1

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 4 5 6 \
  --norm1
```

Each printed spectrum is normalized independently.

### 12. Overwrite an existing `cnorm.dat`

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 1 \
  --rm-cnorm
```

Without `--rm-cnorm`, the script refuses to overwrite an existing `cnorm.dat` when recomputing the basis.

### 13. Linear-molecule handling

```bash
python flying_nimbus.py \
  --xyz co2.xyz \
  --hess co2_hess.dat \
  --traj co2_traj.xyz \
  --modes 1 2 3 4 \
  --nrototrasl 5
```

### 14. Start from a later MD step

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 2 3 \
  --nstart 501
```

This skips the first 500 frames and starts analysis from frame 501.

---

## Typical workflows

### Workflow A: Hessian + trajectory → mode-resolved TA spectra

Use this when you have a single trajectory and want physically interpretable vibrational spectra by mode.

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 1 2 3 4 5
```

This is the most direct “full analysis” route.

### Workflow B: Precomputed `cnorm.dat` → fast repeat analyses

First run once to generate `cnorm.dat`.

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --hess Hessian_flat.out \
  --traj md.xyz \
  --modes 1 \
  --rm-cnorm
```

Then reuse it repeatedly:

```bash
python flying_nimbus.py \
  --xyz eq.xyz \
  --traj md.xyz \
  --readcnorm 1 --cnorm cnorm.dat \
  --modes 3 7 8 12 \
  --nstart 1001 --ncorr 1500 --norm1
```

This is especially convenient for parameter scans.

### Workflow C: Whole-system vs atom-projected comparison

Whole system:

```bash
python flying_nimbus.py \
  --xyz eq.xyz --hess Hessian_flat.out --traj md.xyz \
  --modes 5 6 7 --excel
```

Subset only:

```bash
python flying_nimbus.py \
  --xyz eq.xyz --hess Hessian_flat.out --traj md.xyz \
  --modes 5 6 7 --atoms 1 2 3 --excel
```

This gives you a practical way to compare full-mode behavior with the contribution from a selected fragment or functional group.

---

## Units and conventions

Flying Nimbus mixes a few unit conventions that are worth understanding clearly.

### Geometry input

- XYZ coordinates are read in **Ångström**.
- Internally they are converted to **bohr**.

### Velocities

- Trajectory velocities are read from the trajectory file.
- The current code requires them directly in **bohr** by default.

### Time step

- `--dt` must be given in **atomic units**.
- The default is `8.2682749151502` atomic units.

### Frequency axis

- `--init-wnumb`, `--spec-res`, `--wnumb-span`, and `--freq-offset` are all in `cm^-1`.

### Mode indexing

- Modes are **1-based** at the CLI.
- Internally the code converts them to 0-based indices.

### Atom indexing

- Atoms are **1-based** at the CLI.
- Internally the code converts them to 0-based indices.

---

## Supported atomic symbols and masses

The built-in mass table includes the following symbols:

| Symbol | Mass (au) |
|---|---:|
| `H` | 1837.15 |
| `D` | 3671.48 |
| `O` | 29156.96 |
| `Od` | 32810.46 |
| `C` | 21874.66 |
| `N` | 25526.06 |
| `Ti` | 87256.20 |
| `F` | 34631.97 |
| `S` | 58281.54 |
| `I` | 231332.70 |

If your element is not listed here, provide the mass explicitly as the fifth column in the XYZ atom line.

---

## Important implementation notes

### 1. TA is the default

This is easy to miss.

If you do not pass `--no-ta`, the script computes **time-averaged spectra**, not correlation + FT outputs. This mode is recommended and is the one that should be used in almost all applications.

### 2. `--modes` is mandatory only in normal-mode mode

With `--coord nm`, omitting `--modes` causes an argument error.

With `--coord cart`, mode selection is irrelevant.

### 3. `cnorm.dat` is written automatically in the Hessian path

When `--readcnorm 0`, the script computes the basis from the Hessian and writes `cnorm.dat`.

This is not just an internal temporary object; it is an explicit output artifact.

### 4. Existing `cnorm.dat` is protected by default

If `cnorm.dat` already exists, the script raises an error instead of overwriting it. Use `--rm-cnorm` to replace it.

### 5. Normal-mode spectrum `.dat` files contain large headers

These files are more informative than minimal two-column spectra because they include:

- mode vectors,
- frequencies,
- and ZPE.

That is useful for archival or manual inspection, but can surprise users expecting a plain two-column file.

### 6. `--freq-offset` affects printed/exported axes

The offset is applied to the written wavenumber axis of spectra and plots. It does not re-run the dynamics or alter the normal-mode basis.

### 7. `--excel-merge` supplements, not replaces, per-mode CSVs

If `--excel` and `--excel-merge` are both active, the merged CSVs are added **in addition to** the per-mode CSV outputs.

### 8. Plot display options exist internally but are not exposed in the current CLI

The configuration object has fields related to log-scale y axes and interactive display, but those arguments are not exposed as active CLI options in the current script version.

---

## Troubleshooting

### `--modes is required when --coord nm`

Cause:

- you are in normal-mode mode and did not provide any modes.

Fix:

```bash
--modes 1
```

or switch to Cartesian mode:

```bash
--coord cart
```

### `--hess is required when --readcnorm 0`

Cause:

- you asked the script to compute the mode basis but did not provide a Hessian.

Fix:

- either pass `--hess <file>`,
- or switch to `--readcnorm 1 --cnorm cnorm.dat`.

### `Mode X is out of range`

Cause:

- one of the selected mode indices exceeds `3N - nrototrasl`.

Fix:

- verify `nat`,
- verify `--nrototrasl`,
- and check whether your molecule is linear.

### `atoms selection out of range for nat`

Cause:

- at least one atom index in `--atoms` is outside `1..nat`.

Fix:

- recheck your indexing against the XYZ file.

### `Not enough post-nstart steps for ncorr=...`

Cause:

- after dropping the first `nstart - 1` frames, the remaining trajectory is shorter than `ncorr`.

Fix:

- lower `--ncorr`,
- lower `--nstart`,
- or provide a longer trajectory.

### `Not enough Hessian numbers`

Cause:

- the Hessian file does not contain enough lower-triangle values for a `3N × 3N` matrix.

Fix:

- verify the Hessian extraction workflow,
- and confirm that the file contains all lower-triangle elements after the two header lines.

### `Element 'X' not in mass database`

Cause:

- your XYZ contains an element missing from the internal mass table.

Fix:

- add a fifth mass column to each affected atom line.

### `cnorm.dat already exists; will not overwrite`

Cause:

- a previous `cnorm.dat` is present and you are in the Hessian-compute path.

Fix:

```bash
--rm-cnorm
```

or change the `--cnorm` target path.

---

## Limitations

The current script is powerful but intentionally narrow in scope.

### Input assumptions are strict

- The trajectory must be extended XYZ with `x y z vx vy vz` for every atom line.
- The Hessian reader expects lower-triangle values after exactly two header lines.

### Mass support is limited unless you provide explicit masses

Only a small internal set of atomic symbols is built in. For less common species, explicit mass columns are the safe solution.

### Plotting is intentionally simple

The plotting helper saves one PNG per spectrum and does not expose extensive styling controls in the current CLI.

### Spectra are post-processed outputs, not full uncertainty analyses

The script gives you spectra and correlations, but it does not attempt statistical error bars, bootstrap analysis, or trajectory-block uncertainty estimates.

---

## License

This project is marked in the source with:
```text
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
```
Check the repository for the full license text and any additional usage notes.

---

## Authors

Authors listed in the source:

- Giacomo Mandelli, Ph.D., Politecnico di Milano
- Giacomo Botti, Ph.D., University of South Carolina
