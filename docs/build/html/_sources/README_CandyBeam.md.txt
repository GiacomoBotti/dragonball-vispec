# HDF5 Molecular Data Packager

A Python command-line utility for packaging molecular simulation files into a single compressed HDF5 archive and extracting them without loss of information.

The archive stores the original files as raw bytes, together with archive, simulation, and file metadata. Extracted files are verified using SHA-256 checksums to ensure byte-for-byte reconstruction.

## Requirements

* Python 3
* `h5py`
* `numpy`

Install the dependencies with:

```bash
pip install h5py numpy
```

## Input Files

Each archive contains exactly four files:

| Dataset    | Default file          |
| ---------- | --------------------- |
| Geometry   | `geo_opt.xyz`         |
| Hessian    | `Hessian_flat.out`    |
| Velocity   | `velocity.xyz`        |
| Trajectory | `parsed_log_traj.xyz` |

Alternative filenames can be specified through the command-line options.

## Create an Archive

Example:

```bash
python hdf5_package.py create \
    --molecule-name water \
    --level-of-theory B3LYP \
    --basis-set 6-31G \
    --time-step 0.5 \
    --simulation-steps 1000 \
    --initial-condition-id ic_001 \
    --electronic-structure-software "ORCA 6.0" \
    --units '{"length":"angstrom","energy":"hartree","time":"fs"}' \
    --output simulation.h5
```

By default, LZF compression is used.

The script creates:

```text
simulation.h5
simulation.h5.json
```

The HDF5 archive is the canonical source of the metadata. The JSON file provides a convenient human-readable representation.

## Compression

Available compression methods include:

```bash
--compression lzf
--compression gzip
--compression none
```

LZF is the default because packaging and extraction speed are prioritized over maximum compression.

## Extract an Archive

```bash
python hdf5_package.py extract simulation.h5 \
    --output-dir extracted
```

The output directory contains the original files and an exported metadata file:

```text
extracted/
├── geo_opt.xyz
├── Hessian_flat.out
├── velocity.xyz
├── parsed_log_traj.xyz
└── metadata.json
```

Existing files are not overwritten unless explicitly requested with the appropriate force option.

## View Metadata

Print the metadata stored inside the HDF5 archive:

```bash
python hdf5_package.py metadata simulation.h5
```

Export it to JSON:

```bash
python hdf5_package.py metadata simulation.h5 \
    --output metadata.json
```

The JSON metadata can therefore be reconstructed even if the original sidecar file has been deleted.

## Inspect an Archive

Display a summary of the archive without extracting it:

```bash
python hdf5_package.py list simulation.h5
```

The HDF5 structure is approximately:

```text
/
└── molecule_name/
    ├── geometry
    ├── hessian
    ├── velocity
    └── trajectory
```

Each dataset contains the raw bytes of the corresponding original file.

Because the files are stored as raw `uint8` data, programs such as HDFView will display the dataset contents as integer byte values rather than formatted XYZ or Hessian text.

## Verify an Archive

Check archive structure, metadata, file sizes, checksums, and other integrity information with:

```bash
python hdf5_package.py verify simulation.h5
```

SHA-256 checksums are used to detect changes or corruption.

## Metadata

The archive contains three levels of metadata.

### Archive Metadata

Stored as attributes on the HDF5 root group, including:

* archive format version
* metadata schema version
* creation timestamp
* compression algorithm
* compression settings

### Simulation Metadata

Stored as attributes on the molecule group, including:

* molecule name
* level of theory
* basis set
* time step
* number of simulation steps
* initial condition identifier
* electronic structure software
* units

### File Metadata

Stored as attributes on each dataset, including:

* original filename
* original path
* file size
* modification time
* content type
* SHA-256 checksum

## Scientific Validation

Before creating an archive, the utility validates the supplied molecular data.

XYZ files are checked for consistent atom counts, atom identities, and atom ordering.

The Hessian must represent a `3N × 3N` matrix, where `N` is the number of atoms. Both full-matrix and lower-triangular representations are supported.

## Data Integrity

The original files are stored as raw bytes rather than converted into another scientific representation.

This allows:

```text
original file
      ↓
HDF5 raw bytes
      ↓
extraction
      ↓
original file
```

The extracted files can therefore be reconstructed byte-for-byte, including whitespace, numerical formatting, comments, and line structure.

## Help

For the complete list of commands and options:

```bash
python hdf5_package.py --help
```

Individual commands also provide help, for example:

```bash
python hdf5_package.py create --help
python hdf5_package.py extract --help
```

## Tutorial

The sample input files are placed `example/input`. One can generate the outputs present in `example/output` by running
```
python ../../hdf5_package.py create \
        --geometry geometry.xyz \
	--hessian Hessian_flat.out \
	--velocity velocity.xyz \
	--trajectory traj.xyz \
	--output water.h5 \
	--compression lzf \
	--molecule-name Water \
	--level-of-theory B3LYP \
	--basis-set def2-SVP \
	--time-step 0.2 \
	--simulation-steps 2500 \
	--initial-condition-id qct_001 \
	--electronic-structure-software Runner \
	--units '{"length":"angstrom","energy":"hartree","time":"au"}'
```
The script should print
```
Created archive: <path>/example/input/water.h5
JSON metadata:   <path>/example/input/water.h5.json
Molecule:        Water
Atoms:           3
Hessian format:  lower_triangular
Compression:     lzf
```
