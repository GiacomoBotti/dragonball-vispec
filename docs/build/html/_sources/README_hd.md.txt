# Hessian Database 

`hessian_DB_scan.py` selects representative geometries from a molecular dynamics trajectory using a Hessian Database (HDB) configuration-space search. It reads an equilibrium geometry and Hessian, constructs a mass-weighted normal-mode representation, and adds a trajectory geometry to the database only when no stored geometry lies within the chosen threshold in vibrational normal-coordinate space.

The selected geometries can then be passed to a batch Hessian calculator, avoiding an *ab initio* Hessian calculation at every trajectory step.

## Requirements

- Python 3
- NumPy

The scanner itself does not require a quantum-chemistry package. The equilibrium Hessian and trajectory must already be available.

## Usage

A standard run is:

```bash
python hessian_DB_scan.py \
    --nat 3 \
    --nmax 2500 \
    --thr 0.25 \
    --input_traj traj.xyz \
    --input_hess Hessian_flat.out \
    --output_geom geom_hessian.xyz \
    --output_ind search_indexes.txt \
    --xyz geometry.xyz
```

For a linear molecule, use:

```bash
--nrotransl 5
```

The default is 6 rotational/translational modes.

## Command-line options

| Option | Description |
|---|---|
| `--nat` | Number of atoms. |
| `--nmax` | Number of trajectory frames to analyze. |
| `--thr` | HDB distance threshold; required for a normal run. |
| `--input_traj` | Input extended XYZ trajectory. |
| `--input_hess` | Equilibrium Cartesian Hessian. |
| `--output_geom` | Output file containing selected geometries. |
| `--output_ind` | Output index map for the complete trajectory. |
| `--xyz` | Equilibrium XYZ file used to read geometry and masses. |
| `--nrotransl` | Number of rotational/translational modes; default `6`, use `5` for linear molecules. |
| `--scan-thr` | Run the built-in threshold scan. |
| `--scan-summary` | Threshold-scan summary file; default `graph_eps`. |

## Input files

### Equilibrium geometry

`--xyz` is a standard XYZ file:

```text
3
Equilibrium geometry
O    0.00000000    0.00000000    0.00000000
H    0.00000000    0.75700000    0.58600000
H    0.00000000   -0.75700000    0.58600000
```

The script uses this file to obtain the atomic symbols and masses. Its internal mass database contains `H`, `D`, `O`, `Od`, `C`, `N`, `Ti`, `F`, `S`, and `I`, with masses in atomic units (electron masses).

For an element not present in the internal database, the mass can be supplied in a fifth XYZ column:

```text
X    x    y    z    mass
```

### Equilibrium Hessian

`--input_hess` uses the DragonBall lower-triangular Hessian format. After two header lines, the lower triangle is listed sequentially:

```text
H(1,1)
H(2,1)
H(2,2)
H(3,1)
H(3,2)
H(3,3)
...
```

Both `E` and Fortran `D` exponential notation are accepted.

### Trajectory

`--input_traj` must be an extended multi-frame XYZ trajectory:

```text
nat
comment line
symbol    x    y    z    vx    vy    vz
...
```

The scanner uses the Cartesian coordinates in the HDB search. Velocities are read but are not used by the current selection procedure. The trajectory must contain at least `--nmax` frames.

## Method

For a molecule with `N` atoms,

```text
ncart = 3 N
nvib  = ncart - nrotransl
```

The equilibrium Cartesian Hessian is mass weighted,

```text
D_ij = H_ij / sqrt(m_i m_j)
```

and diagonalized with `numpy.linalg.eigh`. The modes are reordered so that the vibrational modes occur first and the rotational/translational modes are placed at the end. The resulting frequencies are printed in cm^-1.

Each trajectory geometry is projected onto this normal-mode basis. Only the first `nvib` normal coordinates are used by the HDB search.

The first trajectory frame is always inserted into the database. For each subsequent frame, candidate database configurations are filtered by requiring

```text
|q_k(DB) - q_k| < threshold
```

for every vibrational coordinate. If at least one database geometry survives, the closest stored geometry is selected. If no geometry survives, the current trajectory configuration is added as a new database entry.

The database archive is sorted by the first vibrational normal coordinate, allowing the first stage of the search to stop once configurations fall outside the threshold window.

## Outputs

### Selected geometries

`--output_geom` is a multi-frame XYZ file containing only geometries selected for addition to the database:

```text
3
HDB is the best
O    ...
H    ...
H    ...
3
HDB is the best
O    ...
H    ...
H    ...
```

The first trajectory geometry is always written. Further geometries are written only when the search finds no existing database configuration within the threshold.

This file can be passed directly to a batch Hessian calculator such as `hessianator.py`.

### Search indices

`--output_ind` contains one integer for each analyzed trajectory frame. The value identifies the database geometry assigned to that frame, using one-based indexing.

The index file therefore maps the complete trajectory onto the reduced set of representative HDB geometries.

## Threshold scan

Instead of selecting one threshold manually, run:

```bash
python hessian_DB_scan.py \
    --nat 3 \
    --nmax 2500 \
    --input_traj traj.xyz \
    --input_hess Hessian_flat.out \
    --xyz geometry.xyz \
    --scan-thr
```

The built-in thresholds are:

```text
4.0e-1
3.5e-1
3.0e-1
2.5e-1
2.0e-1
1.5e-1
1.0e-1
0.5e-1
0.4e-1
0.3e-1
0.2e-1
0.1e-1
```

For every threshold, the script creates:

```text
geom_<threshold>.dat
index_<threshold>.dat
```

and writes the threshold and number of selected geometries to the summary file. By default:

```text
graph_eps
```

This mode is useful for determining how the size of the Hessian database depends on the HDB threshold.

## Typical workflow

```text
 equilibrium geometry
         +
 equilibrium Hessian
         |
         |             trajectory
         |                 |
         +--------+--------+
                  |
                  v
       +----------------------+
       | hessian_DB_scan.py   |
       +----------------------+
            |             |
            v             v
 selected geometries   index map
```


For example:

```bash
# Select representative trajectory geometries
python hessian_DB_scan.py \
    --nat 3 \
    --nmax 2500 \
    --thr 0.25 \
    --input_traj traj.xyz \
    --input_hess Hessian_flat.out \
    --output_geom geom_hessian.xyz \
    --output_ind search_indexes.txt \
    --xyz geometry.xyz
```

The resulting Hessian database and index map can then be used by a dynamics workflow to retrieve representative stored Hessians instead of evaluating a new Hessian at every trajectory step.

## Notes

- The equilibrium geometry and trajectory should contain the same atoms in the same order; the script warns if their symbols differ.
- `--nmax` is the number of trajectory frames analyzed, and the trajectory must contain at least this many frames.
- Use `--nrotransl 5` for a linear molecule and `--nrotransl 6` for a nonlinear molecule.
- The first trajectory frame is always stored as database geometry 1.
- The scanner selects configurations; it does **not** calculate new *ab initio* Hessians.
