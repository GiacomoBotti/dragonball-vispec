# BULMA

**BULMA** = **Batch Utilities for Log parsing, hessian Matrix & Automation**

BULMA is a command-line Python utility. It is built around one main script and supports three broad categories of tasks:

1. **Extracting data from calculations**
2. **Generating new input files for Gaussian, ORCA, and Q-Chem**
3. **Parsing molecular dynamics trajectories**

The tool is especially useful when you need to move quickly between quantum chemistry packages, reuse geometries and velocities, or convert outputs into formats compatible with other analysis tools such as **Flying Nimbus**.

---

## Table of Contents

- [What BULMA does](#what-bulma-does)
- [Supported workflows](#supported-workflows)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [General command syntax](#general-command-syntax)
- [Hessian extraction](#hessian-extraction)
  - [Gaussian Hessian extraction](#gaussian-hessian-extraction)
  - [ORCA Hessian extraction](#orca-hessian-extraction)
  - [Q-Chem Hessian extraction](#q-chem-hessian-extraction)
- [Geometry extraction](#geometry-extraction)
  - [Gaussian geometry extraction](#gaussian-geometry-extraction)
  - [ORCA geometry extraction](#orca-geometry-extraction)
  - [Q-Chem geometry extraction](#q-chem-geometry-extraction)
- [Input generation](#input-generation)
  - [Gaussian input generation](#gaussian-input-generation)
  - [ORCA input generation](#orca-input-generation)
  - [Q-Chem input generation](#q-chem-input-generation)
- [Dynamics and MD workflows](#dynamics-and-md-workflows)
  - [Gaussian BOMD input generation](#gaussian-bomd-input-generation)
  - [ORCA QMD input generation](#orca-qmd-input-generation)
  - [Q-Chem AIMD input generation](#q-chem-aimdqmd-input-generation)
- [Trajectory parsing](#trajectory-parsing)
  - [Parsing Gaussian BOMD output](#parsing-gaussian-bomd-output)
  - [Parsing ORCA QMD](#parsing-orca-qmd-dumps)
  - [Parsing Q-Chem AIMD output](#parsing-q-chem-aimd-output)
- [Complete CLI reference](#complete-cli-reference)
- [Units and conventions](#units-and-conventions)
- [Common file naming conventions](#common-file-naming-conventions)
- [Typical end-to-end examples](#typical-end-to-end-examples)
- [Limitations and important notes](#limitations-and-important-notes)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Authors](#authors)

---

## What BULMA does

BULMA combines several quantum chemistry tasks into a single CLI.

### Core capabilities

- Extract lower-triangular Hessians from:
  - **Gaussian16** output
  - **ORCA** `.hess` files
  - **Q-Chem** `HESS` files
- Extract optimized geometries from:
  - Gaussian output
  - ORCA output
  - Q-Chem output
- Generate new input files for:
  - **Gaussian** optimization and frequency jobs
  - **ORCA** optimization and frequency jobs
  - **Q-Chem** optimization, frequency, and AIMD jobs
- Generate molecular dynamics inputs for:
  - **Gaussian BOMD**
  - **ORCA QMD**
  - **Q-Chem AIMD**
- Parse MD output and trajectory into formats that can be reused later
- Export trajectories compatible with the **flying_nimbus** code

In short, BULMA is a workflow glue tool: it helps you move data between electronic structure calculations, geometry files, MD trajectories, and post-processing.

---

## Supported workflows

| Workflow | Gaussian | ORCA | Q-Chem |
|---|---:|---:|---:|
| Hessian extraction | Yes | Yes | Yes |
| Geometry extraction | Yes | Yes | Yes |
| Optimization input generation | Yes | Yes | Yes |
| Frequency input generation | Yes | Yes | Yes |
| BOMD / AIMD / QMD input generation | Yes | Yes | Yes |
| MD trajectory parsing | Yes | Yes | Yes |
| flying_nimbus trajectory output | Yes | Yes | Yes |

---

## Project structure

The current project is implemented as a single script:

```text
bulma.py
```

The script handles all supported modes through command-line flags. Different behaviors are selected with mutually exclusive options such as:

- `--opt`
- `--freq`
- `--orca-opt`
- `--orca-freq`
- `--dyn`
- `--orca-qmd`
- `--qchem-opt`
- `--qchem-opt-freq`
- `--qchem-qmd`
- `--parse-dyn`
- `--parse-orca-qmd`
- `--parse-qchem-qmd`
- `--extract-geo`
- `--orca-hess`
- `--qchem-hess`

---

## Requirements

### Minimum

- Python 3
- Standard Python library modules used by the script:
  - `argparse`
  - `pathlib`
  - `re`
  - `sys`

### Optional but required for some MD parsing paths

- `numpy`

`numpy` is used in the Gaussian BOMD parsing branch when converting coordinates, weighted velocities, and energies into array form.

---

## Installation

### Clone the repository

```bash
git clone https://github.com/giacomande95-oss/FLYINGNIMBUS_GUI.git
cd Bulma_terminal_version
```

### Run directly

```bash
python bulma.py --help
```

### Optional virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install numpy
```

If you only use Hessian extraction or input generation, you may not need any extra package beyond Python itself. For Gaussian BOMD parsing, install `numpy`.

---

## Quick start

### 1. Extract a Gaussian Hessian

```bash
python bulma.py job.out
```

This writes:

- `Hessian.out`
- `Hessian_flat.out`

### 2. Generate a Gaussian optimization input from an XYZ file

```bash
python bulma.py geo.xyz --opt
```

This writes:

- `geom.com`

### 3. Extract the final optimized geometry from an output file

```bash
python bulma.py opt.out --extract-geo
```

This writes:

- `geo_opt.xyz`

### 4. Generate ORCA optimization input

```bash
python bulma.py geo.xyz --orca-opt
```

This writes:

- `geom.inp`

### 5. Parse Gaussian BOMD output and write a flying_nimbus trajectory

```bash
python bulma.py dyn.out --parse-dyn --inizio 1 --fine 2500 --xyz geo.xyz --nimbus-traj
```

---

## General command syntax

BULMA takes one positional argument:

```bash
python bulma.py <input_file> [options]
```

The meaning of `<input_file>` depends on the selected mode.

### Examples

- In default mode, `<input_file>` is usually a **Gaussian output file** for Hessian extraction.
- With `--opt`, `--freq`, `--orca-opt`, `--orca-freq`, `--dyn`, `--qchem-*`, `<input_file>` is an **XYZ geometry file**.
- With `--orca-hess`, `<input_file>` is an **ORCA `.hess` file**.
- With `--qchem-hess`, `<input_file>` is a **Q-Chem `HESS` file**.
- With `--parse-qchem-qmd`, `<input_file>` is a **Q-Chem AIMD/QMD `.out` file**.

---

## Hessian extraction

BULMA writes Hessians in two different output forms:

1. **Matrix-style lower-triangular text output**
2. **Flattened one-column vector output**

Both outputs use **Fortran `D` exponent notation**.

### Default output names

- Matrix file: `Hessian.out`
- Flat vector: `Hessian_flat.out`

You can change them with:

- `-m` / `--matrix-out`
- `-v` / `--vector-out`

---

## Gaussian Hessian extraction

This is the default behavior when no mutually exclusive generation or parsing flag is used.

BULMA scans the output for the block between:

- `Force constants in Cartesian coordinates`
- `Final forces over variables`

and then reconstructs the **lower triangular Hessian** and writes both outputs.

### Basic example

```bash
python bulma.py gaussian_freq.out
```

### Custom output names

```bash
python bulma.py gaussian_freq.out \
  --matrix-out my_hessian.out \
  --vector-out my_hessian_flat.out
```

### What gets written

- `my_hessian.out` contains rows where row `r` has exactly `r` values
- `my_hessian_flat.out` contains the same values as a one-column vector
- The flat vector file begins with **two blank lines**

### Typical use case

Use this mode when the code expects a lower-triangular Hessian or a flattened vector in Fortran-style notation.

---

## ORCA Hessian extraction

Use `--orca-hess` when the input file is an ORCA `.hess` file.

BULMA reads the ORCA Hessian block starting at `$hessian`, reconstructs the **full symmetric matrix**, and converts it into the same lower-triangular BULMA format used elsewhere.

### Basic example

```bash
python bulma.py job.hess --orca-hess
```

### Custom outputs

```bash
python bulma.py job.hess --orca-hess \
  -m orca_hessian.out \
  -v orca_hessian_flat.out
```

### Output behavior

- Full ORCA matrix is parsed internally
- Output is converted to BULMA’s lower-triangle convention
- Exponents are written in `D` format

---

## Q-Chem Hessian extraction

Use `--qchem-hess` when the input file is a Q-Chem `HESS` file.

BULMA looks for a block shaped like:

```text
$hessian
Dimension N
...
$end
```

It then reads the lower triangle, validates the expected number of elements, and writes the same two output files as for Gaussian and ORCA.

### Basic example

```bash
python bulma.py HESS --qchem-hess
```

### Custom outputs

```bash
python bulma.py HESS --qchem-hess \
  -m qchem_hessian.out \
  -v qchem_hessian_flat.out
```

---

## Geometry extraction

Use `--extract-geo` to extract the final geometry from a finished calculation.

Default output:

```text
geo_opt.xyz
```

Override with:

```bash
--geo-out my_geometry.xyz
```

### How BULMA detects the engine

BULMA automatically selects the extraction strategy depending on the file content:

- **Gaussian**: last `Standard orientation:` block
- **Q-Chem**: last `Standard Nuclear Orientation (Angstroms)` block
- **ORCA**: last `CARTESIAN COORDINATES (ANGSTROEM)` block after `THE OPTIMIZATION HAS CONVERGED`

---

## Gaussian geometry extraction

For Gaussian outputs, BULMA extracts coordinates from the **last** `Standard orientation:` block.

Because Gaussian standard orientation blocks do not contain the element symbols in the final XYZ, BULMA uses an **XYZ template** to recover the atomic symbols and ordering.

### Default template

```text
geo.xyz
```

### Example

```bash
python bulma.py opt.out --extract-geo --xyz-template geo.xyz
```

### Custom output

```bash
python bulma.py opt.out --extract-geo \
  --xyz-template geo.xyz \
  --geo-out extracted.xyz
```

### Important note

For Gaussian geometry extraction, the template file must contain the **same atoms in the same order** as the calculation.

---

## ORCA geometry extraction

For ORCA outputs, BULMA finds the optimization convergence marker and then extracts the last Cartesian block in Ångström units.

### Example

```bash
python bulma.py orca_opt.out --extract-geo --geo-out orca_final.xyz
```

No template is needed because ORCA prints element symbols directly in the coordinate block.

---

## Q-Chem geometry extraction

For Q-Chem outputs, BULMA reads the last `Standard Nuclear Orientation (Angstroms)` block.

### Example

```bash
python bulma.py qchem_opt.out --extract-geo --geo-out qchem_final.xyz
```

No template is required.

---

## Input generation

BULMA can generate new job inputs directly from an XYZ file.

These modes share a common set of ab initio options.

### Shared ab initio options

```bash
--BS            Basis set                (default: Def2TZVP)
--THEORY        Electronic structure method (default: B3LYP)
--convergence   Optimization keyword     (default: VeryTight)
--Nproc         Number of processors     (default: 48)
--mem           Memory                   (default: 300Gb)
--charge        Total charge             (default: 0)
--mult          Spin multiplicity        (default: 1)
```

---

## Gaussian input generation

### Gaussian optimization input

Use `--opt` to generate `geom.com`.

```bash
python bulma.py geo.xyz --opt
```

#### Output

```text
geom.com
```

#### Default route details

The generated input includes:

- `EmpiricalDispersion=GD3BJ`
- `Opt=(CalcAll,MaxCycles=200,<convergence>)`
- `int=ultrafine`
- `SCF(XQC,Tight)`

#### Customized example

```bash
python bulma.py geo.xyz --opt \
  --THEORY M06-2X \
  --BS Def2TZVP \
  --Nproc 16 \
  --mem 64Gb \
  --charge 1 \
  --mult 2 \
  --convergence Tight
```

---

### Gaussian frequency input

Use `--freq` to generate `geom_freq.com`.

```bash
python bulma.py geo.xyz --freq
```

#### Output

```text
geom_freq.com
```

#### Default route details

The generated frequency input includes:

- `EmpiricalDispersion=GD3BJ`
- `Freq`
- `Iop(7/33=1)`
- `int=ultrafine`
- `SCF(XQC,Tight)`
- `nosymm`

#### Example

```bash
python bulma.py geo.xyz --freq \
  --THEORY B3LYP \
  --BS Def2TZVP \
  --Nproc 24 \
  --mem 128Gb
```

---

## ORCA input generation

### ORCA optimization input

Use `--orca-opt` to generate `geom.inp`.

```bash
python bulma.py geo.xyz --orca-opt
```

#### Output

```text
geom.inp
```

### ORCA optimization + frequency input

Use `--orca-freq` to generate `geom_freq.inp`.

```bash
python bulma.py geo.xyz --orca-freq
```

#### Output

```text
geom_freq.inp
```

### Default ORCA behavior

BULMA maps some generic defaults into ORCA-style settings:

- If `--BS` is left at the global default `Def2TZVP`, ORCA input uses `Def2-TZVPD`
- If `--Nproc` is left at the global default `48`, ORCA input uses `20`
- If `--mem` is left at the global default `300Gb`, no `%maxcore` line is written
- Convergence (`--convergence`) is translated into ORCA optimization keywords such as:
  - `VeryTight` → `VERYTIGHTOPT`
  - `Tight` → `TIGHTOPT`
  - `Normal` → `OPT`

### Example

```bash
python bulma.py geo.xyz --orca-opt \
  --THEORY B3LYP \
  --BS Def2TZVP \
  --Nproc 12 \
  --mem 48Gb \
  --charge 0 \
  --mult 1 \
  --convergence VeryTight
```

### What is written

The ORCA input includes:

- keyword line with method, dispersion, basis, SCF keyword, and job type
- `%PAL NPROCS ... END`
- optional `%maxcore`
- `%SCF` with `MAXITER 500`
- `%geom` with `MAXITER 500`
- Cartesian geometry block in XYZ style

---

## Q-Chem input generation

BULMA supports multiple Q-Chem generation modes.

### 1. Single-job optimization input

Use `--qchem-opt-single`.

```bash
python bulma.py geo.xyz --qchem-opt-single
```

Output:

```text
opt.inp
```

### 2. Single-job frequency input

Use `--qchem-freq`.

```bash
python bulma.py geo.xyz --qchem-freq
```

Output:

```text
freq.inp
```

### 3. Multi-job optimization input

Use `--qchem-opt`.

```bash
python bulma.py geo.xyz --qchem-opt
```

Output:

```text
opt.inp
```

This creates a chained Q-Chem workflow that starts with a frequency job and then launches an optimization that reads the Hessian and SCF guess.

### 4. Multi-job optimization + final frequency input

Use `--qchem-opt-freq`.

```bash
python bulma.py geo.xyz --qchem-opt-freq
```

Output:

```text
opt-freq.inp
```

This creates a three-stage input:

1. Initial frequency job
2. Optimization reading Hessian and guess
3. Final frequency job reading the SCF guess and printing vibrational analysis data

### Q-Chem basis naming

BULMA automatically maps:

```text
Def2TZVP -> def2-TZVP
```

when writing Q-Chem inputs.

### Example

```bash
python bulma.py geo.xyz --qchem-opt-freq \
  --THEORY B3LYP \
  --BS Def2TZVP \
  --charge 0 \
  --mult 1
```

---

## Dynamics and MD workflows

BULMA can both **generate** MD inputs and **parse** MD outputs.

---

## Gaussian BOMD input generation

Use `--dyn` to generate a Gaussian BOMD input file.

### Basic example

```bash
python bulma.py geo.xyz --dyn
```

Default output:

```text
dyn.com
```

### Default supporting files

By default, BULMA expects a velocity file named:

```text
velocity_gau.xyz
```

Override it with:

```bash
--vel-file my_velocities.xyz
```

### Additional options

```bash
--stepsize   BOMD StepSize   (default: 2000)
--npoints    BOMD MaxPoints  (default: 2500)
--dyn-out    Output filename (default: dyn.com)
--chk        Checkpoint name (default: dyn.chk)
```

### Example

```bash
python bulma.py geo.xyz --dyn \
  --vel-file velocity_gau.xyz \
  --stepsize 2000 \
  --npoints 5000 \
  --dyn-out dyn.com \
  --chk dyn.chk
```

### Notes

- Velocities are appended after the geometry block
- BULMA writes the separator line `0` before the velocity section
- The script expects one velocity triplet per atom

---

## ORCA QMD input generation

Use `--orca-qmd` to generate both:

- an ORCA QMD input file
- an ORCA MD restart file

### Basic example

```bash
python bulma.py geo.xyz --orca-qmd
```

### Default outputs

If the XYZ file is `geo.xyz`, BULMA writes:

```text
geo_qmd.inp
geo_qmd.mdrestart
```

### Default supporting file

```text
velocity_orca.xyz
```

Override it with:

```bash
--orca-vel-file my_velocity.xyz
```

### Velocity units

You can specify whether the ORCA velocity file uses:

- `au`      (default)
- `angfs`

with:

```bash
--orca-vel-unit au
--orca-vel-unit angfs
```

### Example

```bash
python bulma.py geo.xyz --orca-qmd \
  --orca-vel-file velocity_orca.xyz \
  --orca-vel-unit au \
  --qmd-timestep 0.20 \
  --qmd-run 2501 \
  --qmd-prefix test_run
```

This writes:

```text
test_run_qmd.inp
test_run_qmd.mdrestart
```

### Notes

- The restart writer converts `au` velocities into `Å/fs` when needed
- The MD input enables position and velocity dumps with stride 1
- The thermostat is set to `none`
- Restart mode is explicitly enabled in the `%md` block

---

## Q-Chem AIMD/QMD input generation

Use `--qchem-qmd` to generate a Q-Chem AIMD input.

### Basic example

```bash
python bulma.py geo.xyz --qchem-qmd
```

### Default files

Input XYZ:

- positional argument, e.g. `geo.xyz`

Default velocity file:

```text
velocity.xyz
```

Default output:

```text
dyn.inp
```

### Q-Chem AIMD-specific options

```bash
--qchem-vel-file   Velocity file      (default: velocity.xyz)
--qchem-qmd-out    Output filename    (default: dyn.inp)
--qchem-timestep   Time_step          (default: 8)
--qchem-steps      aimd_steps         (default: 2500)
--qchem-print      aimd_print         (default: 1)
```

### Example

```bash
python bulma.py geo.xyz --qchem-qmd \
  --qchem-vel-file velocity.xyz \
  --qchem-qmd-out dyn.inp \
  --qchem-timestep 8 \
  --qchem-steps 5000 \
  --qchem-print 1
```

### Notes

- Velocities are written without unit conversion
- The `$velocity` block contains one `(vx vy vz)` triplet per atom
- The generated `$rem` section sets `JOBTYPE = aimd`
- `AIMD_METHOD` defaults to `bomd`
- `DFT_D = D4`
- `no_reorient = true`
- `sym_ignore = true`

---

## Trajectory parsing

BULMA supports parsing output from multiple engines into trajectory formats suitable for visualization, energy analysis, or workflows such as flying_nimbus.

---

## Parsing Gaussian BOMD output

Use `--parse-dyn` to parse Gaussian BOMD output.

### Required arguments

```bash
--parse-dyn
--inizio <start_step>
--fine <end_step_exclusive>
--xyz <reference_geometry.xyz>
```

### Optional arguments

```bash
--gout       Explicit Gaussian output file
--vel        Fallback velocity file
--output     Basename for written files (default: parsed_log)
--movie      Also write coordinates-only movie XYZ
--total      Also write energies file
--scale      Shift Epot and Etot by --Emin
--Emin       Minimum energy used with --scale
--nimbus-traj Print the trajectory for Flying Nimbus 
--nimbus-out Trajectory file name for Flying Nimbus (default: parsed_log_traj.xyz)
--Natom      Number of atoms (OPTIONAL, deprecated)
```

### Basic example

```bash
python bulma.py dyn.out --parse-dyn \
  --inizio 1 \
  --fine 1001 \
  --xyz geo.xyz
```

### Output files

By default, BULMA writes:

```text
parsed_log_xv.xyz
```

Optional outputs:

- `parsed_log.xyz` if `--movie` is used
- `parsed_log_energies.dat` if `--total` is used
- `parsed_log_traj.xyz` if `--nimbus-traj` is used and `--nimbus-out` is not provided

### Example with all major outputs

```bash
python bulma.py dyn.out --parse-dyn \
  --inizio 100 \
  --fine 600 \
  --xyz geo.xyz \
  --movie \
  --total \
  --nimbus-traj \
  --output run1
```

This writes:

```text
run1_xv.xyz
run1.xyz
run1_energies.dat
run1_traj.xyz
```

### What BULMA parses from Gaussian output

It supports step segmentation based on either of these markers:

- `Summary information for step N`
- `Trajectory Number 1 Step Number N`

For each selected step, it attempts to read:

- Cartesian coordinates
- Mass-weighted Cartesian velocities
- `EKin`, `EPot`, and `ETot` when `--total` is requested

### Important note on masses

The Gaussian BOMD parser uses an internal mass database. The current implementation includes:

- H
- C
- O
- N
- S

If your system contains a different element, you must extend the mass table in the source code. If you are using the precompiled version feel free to write on github and we will do it for you.

---

## Parsing ORCA QMD dumps

Use `--parse-orca-qmd` to parse ORCA trajectory dump files.

### Default input files

```text
trajectory.xyz
velocity.xyz
```

Override them with:

```bash
--orca-traj custom_trajectory.xyz
--orca-vel custom_velocity.xyz
```

### Basic example

```bash
python bulma.py dummy_input --parse-orca-qmd
```

The positional `input_file` is still required by the CLI, but in this mode BULMA actually reads the trajectory and velocity files given by `--orca-traj` and `--orca-vel`. Give it the orca output file name if you feel more comfortable.

### Output

By default:

```text
parsed_log_traj.xyz
```

or whatever basename you set with:

```bash
--output myrun
```

### Example with explicit range and Epot output

```bash
python bulma.py placeholder --parse-orca-qmd \
  --orca-traj trajectory.xyz \
  --orca-vel velocity.xyz \
  --inizio 10 \
  --fine 500 \
  --output orca_run \
  --epot-out epot.dat
```

### Behavior

- Positions are read in Ångström
- Velocities are read in Å/fs
- BULMA converts velocities to **bohr/au_time** for flying_nimbus-style output
- Potential energies can be parsed from `trajectory.xyz` comments when available
- Output step numbering is renormalized so that the first exported frame becomes step 1

---

## Parsing Q-Chem AIMD output

Use `--parse-qchem-qmd` when the input file is a Q-Chem AIMD output file.

### Basic example

```bash
python bulma.py qchem_aimd.out --parse-qchem-qmd
```

### Optional controls

```bash
--inizio
--fine
--output
--nimbus-out
--epot-out
```

### Example

```bash
python bulma.py qchem_aimd.out --parse-qchem-qmd \
  --inizio 1 \
  --fine 1000 \
  --output qmd_run \
  --epot-out qmd_epot.dat
```

### Behavior

BULMA looks for blocks marked by:

```text
Nuclear coordinates (Angst) and velocities (a.u.)
```

and matches them to corresponding `TIME STEP #` sections.

It writes a flying_nimbus-style trajectory where:

- positions are in **Ångström**
- velocities are kept in **atomic units**

If `--epot-out` is requested, BULMA tries to obtain the potential energy from:

1. `V(Electronic)`
2. otherwise `E(Total) - T(Nuclear)`

Output step numbering is renormalized so that the first exported frame becomes step 1.

---

## Complete CLI reference

Available options by purpose.

### Positional argument

```bash
input_file
```

Meaning depends on the selected mode.

---

### Hessian output control

```bash
-m, --matrix-out   Output Hessian matrix file    (default: Hessian.out)
-v, --vector-out   Output Hessian vector file    (default: Hessian_flat.out)
```

---

### Hessian mode selection

```bash
--orca-hess        Extract Hessian from ORCA .hess
--qchem-hess       Extract Hessian from Q-Chem HESS
```

If neither is used, the default Hessian mode assumes Gaussian output.

---

### Geometry extraction

```bash
--extract-geo      Extract final geometry and exit
--geo-out          Output XYZ name               (default: geo_opt.xyz)
--xyz-template     Template XYZ for Gaussian     (default: geo.xyz)
```

---

### Input generation mode selection

These options are mutually exclusive:

```bash
--opt
--freq
--orca-opt
--orca-freq
--dyn
--orca-qmd
--qchem-qmd
--qchem-opt-single
--qchem-freq
--qchem-opt
--qchem-opt-freq
```

---

### Shared ab initio options

```bash
--BS             Basis set              (default: Def2TZVP)
--THEORY         Method                 (default: B3LYP)
--convergence    Opt keyword            (default: VeryTight)
--Nproc          Number of processors   (default: 48)
--mem            Memory                 (default: 300Gb)
--charge         Total charge           (default: 0)
--mult           Spin multiplicity      (default: 1)
```

---

### Gaussian BOMD generation options

```bash
--stepsize       BOMD StepSize          (default: 2000)
--npoints        BOMD MaxPoints         (default: 2500)
--vel-file       Velocity file          (default: velocity_gau.xyz)
--dyn-out        Output filename        (default: dyn.com)
--chk            Checkpoint filename    (default: dyn.chk)
```

---

### ORCA QMD generation options

```bash
--orca-vel-file  Velocity file          (default: velocity_orca.xyz)
--orca-vel-unit  Velocity unit          (choices: au, angfs; default: au)
--qmd-timestep   Timestep in fs         (default: 0.20)
--qmd-run        Number of MD steps     (default: 2501)
--qmd-prefix     Prefix for output files
```

---

### Q-Chem AIMD/QMD generation options

```bash
--qchem-vel-file Velocity file          (default: velocity.xyz)
--qchem-qmd-out  Output filename        (default: dyn.inp)
--qchem-timestep Time_step              (default: 8)
--qchem-steps    aimd_steps             (default: 2500)
--qchem-print    aimd_print             (default: 1)
```

---

### Gaussian BOMD parsing options

```bash
--parse-dyn
-i, --inizio     Starting step
-f, --fine       Ending step (exclusive)
-N, --Natom      Total number of atoms
-g, --gout       Gaussian output override
--xyz            Reference equilibrium xyz
--vel            Fallback initial velocity file
-o, --output     Output basename        (default: parsed_log)
--Emin           Minimum potential energy for scaling (default: 0.0)
--scale          Shift Epot and Etot by Emin
--movie          Write coordinates-only xyz
--total          Write energies file
--nimbus-traj    Write flying_nimbus-compatible trajectory
--nimbus-out     Output filename for nimbus trajectory
```

---

### ORCA and Q-Chem trajectory parsing options

```bash
--parse-orca-qmd
--parse-qchem-qmd
--orca-traj      ORCA trajectory file   (default: trajectory.xyz)
--orca-vel       ORCA velocity file     (default: velocity.xyz)
--epot-out       Output potential energy file
```

---

## Units and conventions

BULMA works across multiple programs that use different conventions. Understanding the units is important.

### Constants used internally

- Bohr to Ångström conversion is built in
- Atomic time to femtoseconds conversion is built in
- Velocity conversions are handled when needed

### Common conventions in BULMA outputs

- Hessian outputs are written with **Fortran `D` exponents**
- ORCA trajectory parsing converts velocities from **Å/fs** to **bohr/au_time** for flying_nimbus output
- Q-Chem QMD trajectory parsing keeps velocities in **a.u.**
- Gaussian BOMD parsing writes:
  - an `xv` file with coordinates and converted velocities
  - an optional flying_nimbus trajectory in **Å + bohr/au_time**

### Geometry units

- Extracted XYZ files are written in **Ångström**

---

## Common file naming conventions

### Hessian extraction

- `Hessian.out`
- `Hessian_flat.out`

### Geometry extraction

- `geo_opt.xyz`

### Gaussian generation

- `geom.com`
- `geom_freq.com`
- `dyn.com`

### ORCA generation

- `geom.inp`
- `geom_freq.inp`
- `<prefix>_qmd.inp`
- `<prefix>_qmd.mdrestart`

### Q-Chem generation

- `opt.inp`
- `freq.inp`
- `opt-freq.inp`
- `dyn.inp`

### Parsing outputs

- `<output>_xv.xyz`
- `<output>.xyz`
- `<output>_energies.dat`
- `<output>_traj.xyz`
- custom `--epot-out` file

---

## Typical end-to-end examples

### Example 1: Gaussian optimization input from XYZ

```bash
python bulma.py ethanol.xyz --opt \
  --THEORY B3LYP \
  --BS Def2TZVP \
  --Nproc 8 \
  --mem 16Gb
```

Result:

- `geom.com`

---

### Example 2: Extract final Gaussian geometry and reuse it for ORCA

```bash
python bulma.py gaussian_opt.out --extract-geo \
  --xyz-template geo.xyz \
  --geo-out gaussian_final.xyz

python bulma.py gaussian_final.xyz --orca-opt \
  --THEORY B3LYP \
  --BS Def2TZVP
```

Result:

- `gaussian_final.xyz`
- `geom.inp`

---

### Example 3: Generate Q-Chem opt+freq workflow from optimized XYZ

```bash
python bulma.py final.xyz --qchem-opt-freq \
  --THEORY B3LYP \
  --BS Def2TZVP \
  --charge 0 \
  --mult 1
```

Result:

- `opt-freq.inp`

---

### Example 4: Convert ORCA QMD into a flying_nimbus trajectory

```bash
python bulma.py dummy.dat --parse-orca-qmd \
  --orca-traj trajectory.xyz \
  --orca-vel velocity.xyz \
  --output nimbus_orca \
  --epot-out epot_orca.dat
```

Result:

- `nimbus_orca_traj.xyz`
- `epot_orca.dat`

---

### Example 5: Parse Gaussian BOMD and write Nimbus compatible outputs

```bash
python bulma.py bomd.out --parse-dyn \
  --inizio 1 \
  --fine 2501 \
  --xyz eq.xyz \
  --movie \
  --total \
  --nimbus-traj \
  --output bomd_analysis
```

Result:

- `bomd_analysis_xv.xyz`
- `bomd_analysis.xyz`
- `bomd_analysis_energies.dat`
- `bomd_analysis_traj.xyz`

---

## Limitations and important notes

### 1. Gaussian geometry extraction needs an XYZ template

For Gaussian `--extract-geo`, BULMA uses `--xyz-template` to restore element labels and ordering. If the template does not match the output, the extracted XYZ will be incorrect or fail.

### 2. Gaussian BOMD mass table is limited

The internal mass database currently includes only:

- H
- C
- O
- N
- S

If your system contains other elements, you must extend the source code in `get_masses_cart()`. If you are using a precompiled version feel free to contact us on Github.

### 3. Velocity file sizes must match the atom count

For all generated dynamics inputs and restart files, the number of velocity lines must match the number of atoms in the XYZ geometry.

### 4. Some CLI modes still require a positional `input_file` even if they mainly read auxiliary files

For example, `--parse-orca-qmd` uses `--orca-traj` and `--orca-vel`, but the CLI still expects a positional first argument.

### 5. ORCA and Q-Chem defaults are adapted internally

Some defaults are translated to engine-specific settings instead of being copied literally.

Examples:

- ORCA default basis becomes `Def2-TZVPD`
- ORCA default processor count becomes `20`
- Q-Chem default basis string becomes `def2-TZVP`

---

## Troubleshooting

### “Could not find start marker” during Gaussian Hessian extraction

Cause:

- The file is not a Gaussian Hessian-containing output
- The calculation did not reach the expected section (Error messages?)
- The wrong file was passed as input

Fix:

- Confirm the file is a Gaussian frequency output containing `Force constants in Cartesian coordinates`

---

### “Could not find ORCA start marker” or incomplete ORCA Hessian parsing

Cause:

- The input is not a valid ORCA `.hess` file
- The file is truncated

Fix:

- Use the `.hess` file rather than the `.out`
- Confirm the `$hessian` section is complete

---

### “Q-Chem Hessian size mismatch”

Cause:

- The `HESS` file is incomplete or malformed

Fix:

- Regenerate the Q-Chem Hessian file
- Check for accidental editing or truncation

---

### “Velocity/geometry mismatch”

Cause:

- Number of atoms in the XYZ file and velocity file differ

Fix:

- Ensure that the velocity file contains one line per atom
- Confirm both files refer to the same molecular system

---

### “No MD step markers found” in Gaussian trajectory parsing

Cause:

- The Gaussian output does not contain one of the supported step markers
- The output is not a compatible BOMD job

Fix:

- Confirm the file is a Gaussian BOMD output and that the relevant sections are present

---

### “Atom X not in mass database”

Cause:

- The molecule contains an element not hardcoded in `get_masses_cart()`

Fix:

- Add the missing atomic mass to the source code before running the parser again

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
