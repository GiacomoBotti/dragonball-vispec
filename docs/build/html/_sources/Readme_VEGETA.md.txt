# VEGETA

**VEGETA** = **Velocity Generator for Time-Averaged Quasiclassical Spectra**

VEGETA is a Python tool that generates **initial atomic velocities** from a molecular **Hessian** and an **XYZ geometry**, with options for normal-mode excitation, selective deactivation of modes, principal-axis geometry setting, normal-mode movie generation, and `flying_nimbus`-compatible `cnorm` output.

It is designed for spectroscopy and dynamics workflows where you want a reproducible way to obtain:

- velocity initial conditions in atomic units,
- optional velocity files converted to `bohr/s`,
- normal-mode visualization files,
- frequency and zero-point-energy reports,
- and eigenvector/eigenvalue files that other tools can read. 

The current implementation is contained in a single script, `vegeta.py`, and uses the actual logic documented below.

---

## Table of Contents

- [What VEGETA does](#what-vegeta-does)
- [What VEGETA expects as input](#what-vegeta-expects-as-input)
- [Core workflow](#core-workflow)
- [Features at a glance](#features-at-a-glance)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Command syntax](#command-syntax)
- [Detailed CLI reference](#detailed-cli-reference)
- [Input formats](#input-formats)
  - [Geometry file (`--xyz`)](#geometry-file---xyz)
  - [Hessian file (`-H` / `--hessian`)](#hessian-file)
- [How VEGETA builds velocities](#how-vegeta-builds-velocities)
- [Mode selection and indexing rules](#mode-selection-and-indexing-rules)
- [Geometry-only and principal-axis output](#geometry-only-and-principal-axis-output)
- [Outputs](#outputs)
  - [Velocity file](#velocity-file)
  - [Converted Gaussian-style velocity file](#converted-gaussian-style-velocity-file)
  - [`freq.dat`](#freqdat)
  - [Normal-mode XYZ movies](#normal-mode-xyz-movies)
  - [`cnorm` export](#cnorm-export)
- [Examples](#examples)
- [Units and conventions](#units-and-conventions)
- [Supported atomic symbols](#supported-atomic-symbols)
- [Typical workflow with external tools](#typical-workflow-with-external-tools)
- [Important implementation notes](#important-implementation-notes)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [License](#license)
- [Authors](#authors)

---

## What VEGETA does

VEGETA takes an equilibrium geometry and a Hessian, diagonalizes the **mass-weighted Hessian**, constructs a normal-mode basis, and generates a set of initial velocities.

In practical terms, it can:

- read an **XYZ geometry** in Ångström,
- read a **lower-triangular Hessian file** written one value per line,
- compute normal modes and harmonic frequencies,
- optionally **clean** the normal-mode basis so the roto-translational subspace is explicitly separated,
- selectively **excite** chosen vibrational modes by one quantum,
- selectively **switch off** chosen modes,
- automatically switch off low-frequency modes below a threshold,
- optionally force selected atoms to have zero velocity,
- remove rotational motion from the generated velocities,
- rescale the velocities so the target kinetic energy is preserved,
- write a velocity file in **atomic units**,
- optionally write a second velocity file converted to **bohr/s**,
- export `cnorm` in the layout expected by **flying_nimbus**,
- and generate animated-style XYZ files for each normal mode.

VEGETA is therefore most useful when you want to prepare initial conditions for a dynamics or spectroscopy workflow starting from a harmonic analysis.

---

## What VEGETA expects as input

VEGETA does **not** parse full Gaussian, ORCA, or Q-Chem output files directly.

Instead, it expects two explicit inputs:

1. **A geometry file** in standard XYZ format (`--xyz`)
2. **A Hessian file** containing the **lower triangle** of the Hessian in a flattened one column style (`-H` / `--hessian`)

That makes VEGETA especially suitable as the second stage of a workflow where another tool has already extracted or reshaped the Hessian from an electronic-structure output.

---

## Core workflow

A typical VEGETA run follows this sequence:

1. Read the XYZ geometry and flatten it into a `3N` coordinate vector.
2. Assign atomic masses using the script’s internal mass table.
3. Read the Hessian as a `3N × 3N` symmetric matrix.
4. Build the **mass-weighted Hessian**.
5. Diagonalize it with the internal EISPACK routine.
6. Reorder the eigenvectors so the **vibrational modes come first**.
7. Optionally clean the basis so roto-translational modes are explicitly enforced.
8. Build a normal mode amplitude vector based on:
   - the zero-point level for active modes,
   - `+1` excitation for modes given with `--on`,
   - zero amplitude for modes given with `--off`.
9. Transform the mode amplitudes back to Cartesian velocities.
10. Remove rotational motion and rescale to preserve the target kinetic energy.
11. Write the requested outputs.

---

## Features at a glance

| Capability | Supported |
|---|---:|
| Read XYZ geometry | Yes |
| Read lower-triangular Hessian | Yes |
| Use 5 or 6 roto-translational modes | Yes |
| Excite chosen vibrational modes | Yes |
| Turn off chosen vibrational modes | Yes |
| Turn off low-frequency modes with threshold | Yes |
| Zero selected atoms velocities | Yes |
| Export principal-axis geometry | Yes |
| Generate normal-mode XYZ movies | Yes |
| Export `cnorm` for other tools | Yes |
| Convert velocity units to `bohr/s` | Yes |

---

## Requirements

VEGETA is lightweight and depends on only a small set of Python modules.

### Required Python packages

- `numpy`

### Standard-library modules used

- `argparse`
- `pathlib`
- `re`
- `typing`

### Python version

Any modern Python 3 version that supports:

- type annotations,
- `pathlib`,
- `numpy`,
- and standard CLI execution

should work.

---

## Installation

### Clone the repository

```bash
git clone https://github.com/giacomande95-oss/FLYINGNIMBUS_GUI.git
cd vegeta
```

### Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install numpy
```

### Test the CLI

```bash
python vegeta.py --help
```

---

## Quick start

### Minimal velocity generation

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out
```

This generates:

- `velocity.xyz`
- `freq.dat`

### Excite one mode

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --on 3
```

### Switch off a range of modes

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --off 1-6
```


### Write `cnorm` for `flying_nimbus`

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --cnorm-out cnorm.dat
```

### Generate principal-axis geometry only

```bash
python vegeta.py --xyz geom.xyz --geo-only
```

---

## Command syntax

The general form is:

```bash
python vegeta.py --xyz <geometry.xyz> -H <hessian_file> [options]
```

There is also a geometry-only mode:

```bash
python vegeta.py --xyz <geometry.xyz> --geo-only [--pa-xyz output.xyz]
```

The most important thing to remember is:

- `--xyz` is always required
- `-H` / `--hessian` is required unless `--geo-only` is used

---

## Detailed CLI reference

### Required or workflow-defining arguments

#### `--xyz`
Path to the molecular geometry in XYZ format, in **Ångström**.

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out
```

---

#### `-H`, `--hessian`
Path to the lower-triangular Hessian file.

This is required unless you are using `--geo-only`.

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out
```

---

#### `--geo-only`
Run only the geometry-processing branch:

- shift the geometry to the **center of mass**,
- rotate it into the **principal-axis frame**,
- write the result as an XYZ file,
- and exit without attempting any Hessian or velocity generation.

Example:

```bash
python vegeta.py --xyz geom.xyz --geo-only
```

---

### Normal-mode / vibrational control

#### `--nrotrasl {5,6}`
Number of roto-translational modes to remove.

- Default: `6`
- Use `5` for **linear molecules**
- Use `6` for **nonlinear molecules**

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --nrotrasl 5
```

---

#### `--on`
Modes to excite by **+1 quantum**.

Mode numbering is **1-based** and refers to the **vibrational modes only**, not the full `3N` Cartesian eigenvalue list.

Accepted forms include:

- single values: `3`
- hyphen ranges: `1-5`
- colon ranges: `10:12`
- double-dot ranges: `20..23`
- comma-separated values: `1,3,7`

Examples:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --on 3
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --on 1-3 7 10..12
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --on 1,2,5
```

---

#### `--off`
Modes to switch off completely.

Switched-off modes are assigned zero amplitude.

Examples:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --off 1-6
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --off 2 4 8..10
```

If a mode appears in both `--on` and `--off`, **off wins**.

---

#### `--freq-thresh <cm^-1>`
Switch off all vibrational modes below the chosen harmonic-frequency threshold.

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --freq-thresh 50
```

This is useful when you want to suppress floppy modes in the generated initial conditions.

---

### Velocity and atom-level control

#### `-o`, `--output`
Name of the output velocity file in atomic units.

Default:

```text
velocity.xyz
```

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out -o init_vel.xyz
```

---

#### `--zero-vel-atoms`
Force chosen atoms to have exactly zero velocity after the normal-mode velocity generation step.

Atom indexing is **1-based** and supports the same token syntax as mode selection:

- `1-5`
- `8`
- `10..12`
- `20:22`
- `1,4,6`

Examples:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --zero-vel-atoms 1
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --zero-vel-atoms 1-3 7
```

---

#### `--gau-vel`
In addition to the main atomic-units velocity file, also write a converted velocity file in `bohr/s`.

If the main output is:

```text
velocity.xyz
```

the converted file is:

```text
velocity_gau.xyz
```

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --gau-vel
```

---

### Basis cleaning and cnorm export

#### `--clean-cnorm {0,1}`
Enable or disable the normal-mode cleaning procedure.

- Default: `0`
- Set to `1` to force explicit roto-translational separation and rebuild the vibrational subspace with Gram–Schmidt projection

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --clean-cnorm 1
```

This is especially useful when contamination makes the roto-translational modes less clean than desired.

---

#### `--cnorm-out <file>`
Write the eigenvector/eigenvalue data in a `cnorm`-style text layout intended for tools such as `flying_nimbus`.

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --cnorm-out cnorm.dat
```

---

### Geometry export and visualization

#### `--pa-xyz <file>`
Write the center-of-mass-shifted, principal-axis geometry to the chosen file.

If `--pa-xyz` is used **without** `--geo-only`, VEGETA still writes the principal-axis geometry **and then continues** with the full velocity-generation workflow.

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --pa-xyz geom_pa.xyz
```

---

#### `--print {0,1}`
Write one multi-frame XYZ file per vibrational mode.

- Default: `0`
- Set to `1` to export normal-mode motion files for visualization

Example:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --print 1
```

---

## Input formats

### Geometry file (`--xyz`)

VEGETA expects a standard XYZ file:

```text
3
water
O   0.000000   0.000000   0.000000
H   0.000000   0.757000   0.586000
H   0.000000  -0.757000   0.586000
```

Rules:

- line 1 = number of atoms
- line 2 = comment line
- lines 3 onward = atomic symbol + `x y z`
- coordinates must be in **Ångström**

---

(hessian-file)=
### Hessian file (`-H` / `--hessian`)

VEGETA expects a lower-triangular Hessian file in a specific layout:

- the first **two lines are skipped**
- the remaining values are read as the **lower triangle**
- data are read in nested `i,j` order
- one numeric value is expected per line
- `D` and `E` exponent notation are both accepted

Conceptually, the file after the first two lines should look like:

```text
H11
H21
H22
H31
H32
H33
...
```

for all lower-triangular entries of a `3N × 3N` matrix.

This means VEGETA does **not** read a full square matrix dump and does **not** auto-detect alternate Hessian layouts.

---

## How VEGETA builds velocities

This is the core numerical workflow implemented by the script.

### 1. Assign masses

Atomic masses are taken from the script’s internal `MASS_AU` table and then expanded from per-atom masses to Cartesian masses:

```text
[m1, m1, m1, m2, m2, m2, ...]
```

---

### 2. Build the mass-weighted Hessian

If `H` is the Cartesian Hessian and `m` is the Cartesian mass vector, VEGETA forms:

```text
H_mw(i,j) = H(i,j) / sqrt(m_i m_j)
```

---

### 3. Diagonalize

The mass-weighted Hessian is diagonalized with the internal EISPACK-style solver.

The result is:

- eigenvalues
- eigenvectors

VEGETA then reorders the eigenvectors so that the **vibrational modes are placed first** in the `cnorm` matrix.

---

### 4. Optionally clean the normal-mode basis

When `--clean-cnorm 1` is used, VEGETA:

1. extracts the roto-translational block from the current basis,
2. orthonormalizes it with modified Gram–Schmidt,
3. constructs a vibrational subspace orthogonal to it,
4. projects the mass-weighted Hessian into that subspace,
5. diagonalizes again inside the vibrational space,
6. and rebuilds the full basis as:

```text
[vibrational modes | roto-translational modes]
```

This can reduce mixing between the physical vibrational modes and near-zero modes.

---

### 5. Build mode amplitudes

For each vibrational mode, VEGETA defines a scalar amplitude:

```text
P_i = sqrt(gamma_i) * sqrt(2 n_i + 1)
```

where:

- `gamma_i = sqrt(|eigenvalue_i|)`
- `n_i = 0` for a mode left at the harmonic ground-state level
- `n_i = 1` for a mode selected with `--on`
- switched-off modes are assigned zero amplitude

That means the current implementation supports:

- the default harmonic level
- plus one extra quantum for selected modes

---

### 6. Transform back to Cartesian velocity space

The vector of mode amplitudes is projected back to Cartesian space:

```text
P_cart = cnorm @ P
v = P_cart / sqrt(m)
```

This produces the initial Cartesian velocity vector.

---

### 7. Remove rotational motion and rescale kinetic energy

VEGETA then:

- rotates coordinates/velocities to a principal-axis frame,
- computes angular momentum,
- removes rotational contamination,
- transforms back,
- and rescales the final velocities to preserve the target kinetic energy.

This step is crucial because the raw mode-based reconstruction can still contain unwanted rotations.

---

## Mode selection and indexing rules

Both `--on` and `--off` use the same parser and the same conventions.

### Index base

Mode indices are **1-based**.

So:

- `1` = first vibrational mode
- `2` = second vibrational mode
- etc.

### Allowed tokens

All of the following are valid:

```text
1
1-5
1:5
1..5
1,3,7
1-3,7,10..12
```

### Duplicate handling

Duplicates are automatically removed while preserving order.

### Validation

If a mode index falls outside:

```text
1 .. nvib
```

VEGETA raises an error.

### Precedence

If the same mode is passed to both:

- `--on`
- `--off`

the mode is treated as **off**.

---

## Geometry-only and principal-axis output

VEGETA can also be used as a geometry-preparation tool.

### Geometry-only mode

```bash
python vegeta.py --xyz geom.xyz --geo-only
```

This:

- reads the XYZ file,
- shifts coordinates to the center of mass,
- rotates them into the principal-axis frame,
- writes a new XYZ file,
- and exits.

### Default output name

If you do not provide `--pa-xyz`, the output becomes:

```text
<original_stem>_pa.xyz
```

For example:

- input: `geom.xyz`
- output: `geom_pa.xyz`

### Custom output name

```bash
python vegeta.py --xyz geom.xyz --geo-only --pa-xyz pa_frame.xyz
```

### Comment line content

The written XYZ comment line includes the center-of-mass shift that was applied.

---

## Outputs

### Velocity file

The main output is an XYZ-like velocity file in **atomic units**.

Default name:

```text
velocity.xyz
```

Example content:

```text
3
Velocities (a.u.)
O    1.2345678901234567e-04  2.3456789012345678e-05 -3.4567890123456789e-05
H   -4.5678901234567890e-04  5.6789012345678901e-05  6.7890123456789012e-05
H    3.3333333333333333e-04 -7.0000000000000000e-05 -3.0000000000000000e-05
```

The file preserves the atom ordering from the input geometry.

---

### Converted Gaussian-style velocity file

If `--gau-vel` is enabled, VEGETA writes a second file where the velocities are converted from:

```text
bohr / atomic-time-unit
```

to:

```text
bohr / s
```

using the script’s built-in atomic time constant.

Example:

- main output: `velocity.xyz`
- converted output: `velocity_gau.xyz`

---

### `freq.dat`

VEGETA always writes a frequency report named:

```text
freq.dat
```

in the output directory.

This file contains:

- all frequencies, including roto-translational modes,
- harmonic zero-point energy over all vibrational modes,
- active-mode zero-point energy if some modes were switched off,
- and the name of the written velocity file.

The current implementation also reports ZPE in:

- Hartree
- cm<sup>-1</sup>
- kJ/mol
- kcal/mol

---

### Normal-mode XYZ movies

If `--print 1` is used, VEGETA writes one multi-frame XYZ file per vibrational mode:

```text
<output_stem>_mode_001.xyz
<output_stem>_mode_002.xyz
...
```

Each file:

- contains a concatenated XYZ trajectory,
- samples a sinusoidal displacement,
- uses `21` frames by default,
- uses `1` cycle by default,
- scales the displacement so the maximum Cartesian displacement is `0.10 Å`.

These files are intended for mode visualization, not for production dynamics.

---

### `cnorm` export

When `--cnorm-out` is used, VEGETA writes a structured text file containing:

1. one line per eigenvector,
2. a line with `sqrt(|eigenvalues|)`,
3. a final line with eigenvalues.

The script writes the eigenvectors in the exact layout expected by tools that read `cnorm` in a **vib-first** ordering.

This is especially useful in combined workflows with `flying_nimbus`.

---

## Examples

### 1. Basic nonlinear molecule run

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out
```

Use this for a standard nonlinear molecule with the default `6` roto-translational modes removed.

---

### 2. Linear molecule run

```bash
python vegeta.py --xyz co2.xyz -H Hessian_flat.out --nrotrasl 5
```

Use `5` for linear molecules.

---

### 3. Excite selected modes

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --on 2 5 7
```

This places modes 2, 5, and 7 at the `n = 1` level, while all other active modes remain at the default harmonic energy.

---

### 4. Combine excitation and deactivation

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --on 2-4 --off 3
```

Mode 3 is switched off because `off` takes precedence.

---

### 5. Switch off soft modes automatically

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --freq-thresh 80
```

Useful when low-frequency floppy modes are present.

---

### 6. Freeze selected atoms

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --zero-vel-atoms 1 2
```

This zeroes the final velocities on atoms 1 and 2 after the normal-mode generation step.

---

### 7. Write custom output filenames

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out -o sample01_velocity.xyz --cnorm-out sample01_cnorm.dat
```

---

### 8. Export a principal-axis geometry and continue

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --pa-xyz geom_pa.xyz
```

This writes `geom_pa.xyz` and still performs the full velocity-generation workflow.

---

### 9. Geometry-only principal-axis export

```bash
python vegeta.py --xyz geom.xyz --geo-only --pa-xyz geom_pa.xyz
```

This writes the geometry and exits without requiring a Hessian.

---

### 10. Export normal-mode visualization files

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --print 1
```

This writes a mode movie file for every vibrational mode.

---

### 11. Write converted velocities for external tools

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --gau-vel
```

This writes:

- `velocity.xyz`
- `velocity_gau.xyz`

---

### 12. Use cnorm cleaning for problematic Hessian

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --clean-cnorm 1 --cnorm-out cnorm_clean.dat
```

This is a good choice when modes do not look sufficiently separated.

---

### 13. A production-style example

```bash
python vegeta.py \
  --xyz geom.xyz \
  -H Hessian_flat.out \
  --nrotrasl 6 \
  --on 3 5 8 \
  --off 1-2 \
  --freq-thresh 50 \
  --zero-vel-atoms 10..12 \
  --clean-cnorm 1 \
  --cnorm-out cnorm.dat \
  --print 1 \
  --gau-vel \
  -o traj_init.xyz
```

This run will:

- read geometry and Hessian,
- treat the system as nonlinear,
- excite modes 3, 5, and 8,
- switch off modes 1 and 2,
- additionally switch off vibrational modes below 50 cm<sup>-1</sup>,
- zero the velocities on atoms 10–12,
- clean the normal-mode basis,
- export `cnorm.dat`,
- generate normal mode visualization files,
- write the velocity file as `traj_init.xyz`,
- and also write `traj_init_gau.xyz`.

---

## Units and conventions

VEGETA uses several internal and output units.

### Geometry input
- **Ångström**

### Internal geometry for some velocity operations
- **bohr**

### Hessian
- expected in atomic-unit-compatible values consistent with the mass-weighting and diagonalization

### Frequencies
- reported in **cm<sup>-1</sup>**

### Output velocities
- main file: **atomic units**
- optional converted file for Gaussian: **bohr/s**

### Energies in `freq.dat`
- **Hartree**
- **cm<sup>-1</sup>**
- **kJ/mol**
- **kcal/mol**

### Mode numbering
- **1-based**
- indexed over the **vibrational modes only**

---

## Supported atomic symbols 

VEGETA uses a built-in atomic-mass dictionary (MASS DATABASE). At the time of this implementation, the accepted symbols are:

| Symbol | Supported |
|---|---:|
| `H` | Yes |
| `D` | Yes |
| `O` | Yes |
| `Op` | Yes |
| `Od` | Yes |
| `C` | Yes |
| `Cp` | Yes |
| `N` | Yes |
| `S` | Yes |
| `P` | Yes |
| `F` | Yes |
| `I` | Yes |

If the XYZ file contains an atomic symbol not present in the internal mass table, VEGETA raises an error.

So before running a large workflow, make sure your geometry uses the exact labels expected by the script.

---

## Typical workflow with external tools

A common end-to-end job looks like this:

### Step 1 — Obtain a geometry (BULMA code)
Use your quantum-chemistry package to optimize the structure and export an XYZ file.

### Step 2 — Extract or reshape the Hessian (BULMA code)
Use a separate extraction tool or preprocessing script to produce the lower-triangular Hessian format VEGETA expects.

### Step 3 — Run VEGETA
Generate the velocity field, normal-mode information, and optional files.

### Step 4 — Feed outputs into later stages
Possible uses include:

- starting a molecular-dynamics trajectory,
- visualizing normal modes,
- or passing `cnorm.dat` to a tool like `flying_nimbus`.

---

## Important implementation notes

### 1. VEGETA assumes a specific Hessian layout
It does not auto-detect alternative formats.

### 2. The `--on` interface is binary
A selected mode is promoted to `n = 1`.
There is no direct `n = 2`, `n = 3`, etc. interface in the current release.

### 3. `--off` overrides `--on`
If both are given for the same mode, the mode is disabled.

### 4. `freq.dat` is always named `freq.dat`
It is written in the output directory.

### 5. Mode movies use fixed visualization settings
The helper uses:

- `21` frames
- `1` cycle
- maximum displacement target of `0.10 Å`

These are currently hard-coded.

### 6. `--pa-xyz` is not geometry-only by itself
It writes the principal-axis geometry, but unless `--geo-only` is also set, the code continues with Hessian processing.

### 7. Unknown atomic labels fail immediately
Mass lookup is strict.

---

## Troubleshooting

### “Missing -H/--hessian”
You used the program without a Hessian file.

Fix:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out
```
or use:

```bash
python vegeta.py --xyz geom.xyz --geo-only
```

if you only want the principal-axis geometry.

---

### “Unknown atom symbol”
Your XYZ file contains a symbol not present in the internal mass table.

Fix:

- update the geometry labels to match the supported symbols,
- or extend the mass table in the script. (In this case If you are using the precompiled version feel free to contact us on Github.)

---

### “Mode X out of range”
A mode given to `--on` or `--off` exceeds the valid range `1..nvib`.

Fix:

- verify the number of vibrational modes,
- check whether you set `--nrotrasl` correctly,
- and correct the requested mode numbers.

---

### “Atom index X out of range”
A requested atom in `--zero-vel-atoms` is outside `1..N`.

Fix the indexing so it matches the atoms present in the input XYZ file.

---

### Bad-looking roto-translational separation
If the near-zero modes are numerically contaminated, try:

```bash
python vegeta.py --xyz geom.xyz -H Hessian_flat.out --clean-cnorm 1
```

---

### Unexpected number of vibrational modes
Check whether the molecule is linear or nonlinear:

- nonlinear → `--nrotrasl 6`
- linear → `--nrotrasl 5`

---

## Limitations

The current script is intentionally focused and not a universal parser.

### Current limitations

- It does **not** read Gaussian/ORCA/Q-Chem outputs directly. BULMA is the tool for you in this case.
- It expects a very specific Hessian layout. Use BULMA to prepare everything.
- It supports only the atomic labels present in the built-in mass table.
- It does not offer arbitrary quantum occupations beyond the default level and `+1` excitation.
- Mode-movie settings are not exposed on the CLI.

---

## License

This project is marked in the source with:
```text
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
```
Check the repository for the full license text and any additional usage notes.

---

## Authors

The script header lists:

- Giacomo Mandelli, Ph.D., Politecnico di Milano
- Giacomo Botti, Ph.D., University of South Carolina
