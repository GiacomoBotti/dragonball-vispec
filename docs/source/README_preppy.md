# PrepPy: Hessian Utilities

A Python package for preparing, collecting, and reconstructing *ab initio* Hessians for a set of molecular geometries.

The package contains three command-line utilities:

- `prep.py` — prepares one quantum-chemistry Hessian calculation for each geometry.
- `collect_hessian.py` — collects the calculated Hessians into a common DragonBall-compatible file.
- `reconstruct_hessian.py` — reconstructs a full trajectory Hessian sequence from a reduced Hessian database and an index map.

The preparation and collection tools support **ORCA**, **Q-Chem**, and **Gaussian 16**.

## Requirements

- Python 3
- A supported quantum-chemistry package for the Hessian calculations: ORCA, Q-Chem, or Gaussian 16.

The Python utilities themselves use only the standard library.

## 1. `prep.py`

`prep.py` reads geometries from a multi-frame XYZ trajectory and creates one directory per geometry:

```text
geo1/
geo2/
...
geoN/
```

Each directory receives an input file for the selected quantum-chemistry backend.

### Usage

```bash
python prep.py --program orca --ngeo 20 --nat 3 --traj geometries.xyz
```

Supported backends are:

```text
orca
qchem
gaussian
```

`--backend` is accepted as an alias for `--program`.

### Options

| Option | Description |
|---|---|
| `--program`, `--backend` | Backend: `orca`, `qchem`, or `gaussian`. |
| `--ngeo` | Number of geometries to prepare. |
| `--nat` | Number of atoms per geometry. |
| `--traj` | Input XYZ trajectory; default `trj.xyz`. |
| `--template-script` | Helper shell script copied into every geometry folder. |
| `--debug` | Print diagnostic information. |

The trajectory is a standard multi-frame XYZ file. Only the first four atom-line columns (`symbol x y z`) are used, so extended XYZ trajectories containing velocities are also accepted.

### Generated files

| Backend | Input file | Default helper script |
|---|---|---|
| ORCA | `geoN/geoN.inp` | `lancia_orca.sh` |
| Q-Chem | `geoN/geoN.in` | `lancia_qchem.sh` |
| Gaussian 16 | `geoN/geoN.gjf` | `lancia_g16.sh` |

If the helper script is absent, preparation continues without it.

The current templates use B3LYP with D3(BJ) dispersion. ORCA and Q-Chem use `Def2-TZVPD`; the Gaussian template uses `Def2TZVP`. Charge and multiplicity are currently fixed to `0 1`.

The ORCA template requests:

```text
! B3LYP D3BJ Def2-TZVPD FREQ TightSCF
```

The Q-Chem template requests a `FREQ` calculation with B3LYP/DEF2-TZVPD and D3(BJ).

The Gaussian template uses:

```text
# B3LYP/Def2TZVP EmpiricalDispersion=GD3BJ int=ultrafine Freq Iop(7/33=1) SCF=(XQC,Tight)
```

## 2. `collect_hessian.py`

After the quantum-chemistry jobs finish, `collect_hessian.py` extracts the Hessian from every geometry directory and writes the Hessians sequentially to one file.

### Usage

```bash
python collect_hessian.py --nat 3 --ngeo 20 --program orca
```

The default output is:

```text
Hessian.out
```

### Options

| Option | Description |
|---|---|
| `--nat` | Number of atoms. |
| `--ngeo` | Number of geometry folders. |
| `--output` | Collected Hessian file; default `Hessian.out`. |
| `--geo-prefix` | Folder prefix; default `geo`. |
| `--program` | `orca`, `qchem`, or `gaussian`; default `orca`. |
| `--hess-suffix` | Override the expected Hessian/output filename. |
| `--debug` | Print diagnostic information. |

By default the collector expects:

| Backend | Hessian source |
|---|---|
| ORCA | `geoN/geoN.hess` |
| Q-Chem | `geoN/HESS` |
| Gaussian 16 | `geoN/geoN.log` |

For ORCA, the matrix is extracted from the `$hessian` section and reconstructed from the full block representation. For Q-Chem, the lower triangle is read from the `$hessian ... $end` section of `HESS`. For Gaussian, the lower-triangular force constants are extracted between `Force constants in Cartesian coordinates` and `Final forces over variables`.

All three formats are converted to the same output representation: two blank lines followed by the flattened lower triangle of the `3N x 3N` Cartesian Hessian.

```text


H(1,1)
H(2,1)
H(2,2)
H(3,1)
H(3,2)
H(3,3)
...
```

The collector checks that each Hessian dimension equals `3 * nat`.

## 3. `reconstruct_hessian.py`

`reconstruct_hessian.py` reconstructs the Hessian sequence for the complete trajectory using a reduced Hessian database and a 1-based index map.

### Usage

```bash
python reconstruct_hessian.py \
    --index-file search_indexes.txt \
    --hess-file Hessian.out \
    --hess-out Hessian_reconstructed.out \
    --hlen 47
```

### Options

| Option | Description |
|---|---|
| `--index-file` | One database index per trajectory frame. |
| `--hess-file` | File containing the computed database Hessians. |
| `--hess-out` | Reconstructed Hessian output. |
| `--hlen` | Number of lines in one Hessian block, including its two blank lines. |
| `--debug` | Print reconstruction details. |

The index file contains one positive, 1-based database index per trajectory frame:

```text
1
1
2
2
3
...
```

For every index, the corresponding Hessian block is copied to the reconstructed output.

### Hessian block length

For `nat` atoms:

```text
ncart = 3 * nat
nelem = ncart * (ncart + 1) / 2
hlen  = nelem + 2
```

The additional two lines are the blank lines preceding every Hessian.

For a three-atom molecule:

```text
ncart = 9
nelem = 45
hlen  = 47
```

## Typical workflow

The package is intended for a reduced-Hessian workflow in which representative geometries have already been selected:

```text
representative geometries
          |
          v
      +---------+
      | prep.py |
      +---------+
          |
          v
 geo1/ geo2/ ... geoN/
          |
          v
 ORCA / Q-Chem / Gaussian
 Hessian calculations
          |
          v
 +--------------------+
 | collect_hessian.py |
 +--------------------+
          |
          v
     Hessian.out
          |
          |       index map
          |           |
          +-----+-----+
                |
                v
 +------------------------+
 | reconstruct_hessian.py |
 +------------------------+
                |
                v
   full trajectory Hessians
```

For example, using ORCA:

```bash
# Prepare the selected geometries
python prep.py \
    --program orca \
    --ngeo 20 \
    --nat 3 \
    --traj selected_geometries.xyz

# Run the ORCA jobs in geo1 ... geo20

# Collect the calculated Hessians
python collect_hessian.py \
    --program orca \
    --nat 3 \
    --ngeo 20 \
    --output Hessian.out

# Reconstruct the complete trajectory Hessian sequence
python reconstruct_hessian.py \
    --index-file search_indexes.txt \
    --hess-file Hessian.out \
    --hess-out Hessian_reconstructed.out \
    --hlen 47
```

Changing `--program` to `qchem` or `gaussian` uses the corresponding preparation and collection backend.

## Integration with a Hessian Database workflow

These utilities naturally follow a representative-geometry/Hessian Database selection:

```text
full trajectory
      |
      v
representative-geometry selection
      |
      +----------------------> index map
      |
      v
selected geometries
      |
      v
prep.py
      |
      v
ab initio Hessian calculations
      |
      v
collect_hessian.py
      |
      v
reduced Hessian database
      |
      +----------- index map
                    |
                    v
           reconstruct_hessian.py
                    |
                    v
          full Hessian sequence
```

The expensive *ab initio* Hessian calculation is therefore performed only for representative configurations. The reconstruction step restores the Hessian sequence required by downstream trajectory or semiclassical-dynamics calculations.

## Notes

- `prep.py` reuses existing `geoN` directories if they already exist.
- The input trajectory must contain at least `ngeo` frames, each with `nat` atoms.
- Electronic-structure settings are currently hard-coded in the three input writers.
- Generated inputs currently assume charge 0 and singlet multiplicity.
- `collect_hessian.py` removes an existing output file before creating a new collection.
- `--hess-suffix` can override backend-specific output naming.
- `reconstruct_hessian.py` expects 1-based indices.
- `hlen` includes the two blank lines at the beginning of each Hessian block.
- `--debug` is available in all three utilities.
