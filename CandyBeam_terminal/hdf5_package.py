#!/usr/bin/env python3
"""Package molecular simulation text files into a portable HDF5 archive.

Required logical files:
    geometry, hessian, velocity, trajectory

The HDF5 datasets contain the exact original bytes. Metadata are stored as
HDF5 attributes, and a companion JSON file is written next to the archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import h5py
import numpy as np


ARCHIVE_FORMAT_VERSION = "1.0"
METADATA_SCHEMA_VERSION = "1.0"
REQUIRED_DATASETS = ("geometry", "hessian", "velocity", "trajectory")
DEFAULT_FILES = {
    "geometry": "geo_opt.xyz",
    "hessian": "Hessian_flat.out",
    "velocity": "velocity.xyz",
    "trajectory": "parsed_log_traj.xyz",
}

# Numeric token used by Hessian parsing. Scientific notation is supported.
_FLOAT_RE = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?$"
)


class ArchiveError(RuntimeError):
    """Expected user-facing archive/validation error."""


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_readable_file(path: Path, label: str) -> None:
    if not path.exists():
        raise ArchiveError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise ArchiveError(f"{label} path is not a file: {path}")
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError as exc:
        raise ArchiveError(f"Cannot read {label} file '{path}': {exc}") from exc


def _display_compression(compression: Optional[str], compression_opts) -> str:
    if compression is None:
        return "none"
    if compression == "gzip":
        return f"gzip (level={compression_opts})"
    return str(compression)


def _write_sidecar_json_to_path(json_path: Path, metadata: dict) -> Path:
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True, default=_json_default)
        handle.write("\n")
    return json_path


def _write_sidecar_json(archive_path: Path, metadata: dict) -> Path:
    json_path = archive_path.with_suffix(archive_path.suffix + ".json")
    return _write_sidecar_json_to_path(json_path, metadata)


def _h5_attr_value(value):
    # h5py stores native scalars and UTF-8 strings cleanly. JSON handles nested
    # values that are not convenient as HDF5 attributes.
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=_json_default)
    return value


def _relative_path_text(path: Path, base_dir: Optional[Path]) -> str:
    if base_dir is not None:
        try:
            return path.resolve().relative_to(base_dir.resolve()).parent.as_posix()
        except ValueError:
            return Path(".").as_posix()

    # The extraction path must always be relative to the extraction root.
    # Absolute source paths are preserved separately in `original_path`, but
    # must never become extraction targets.
    if path.is_absolute():
        return Path(".").as_posix()
    return path.parent.as_posix() or Path(".").as_posix()


def _safe_extract_target(output_dir: Path, relative_path: str, filename: str) -> Path:
    # Archive metadata is untrusted: never allow absolute paths or .. traversal.
    rel_dir = Path(relative_path) if relative_path else Path()
    if rel_dir.is_absolute() or any(part == ".." for part in rel_dir.parts):
        raise ArchiveError(f"Unsafe archived path: {relative_path!r}")
    target = (output_dir / rel_dir / filename).resolve()
    root = output_dir.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ArchiveError(f"Archived path escapes extraction directory: {filename!r}") from exc
    return target


def _xyz_frames(path: Path) -> List[List[str]]:
    """Return atom-symbol sequences for every XYZ frame."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ArchiveError(f"{path} is not valid UTF-8 text and cannot be XYZ-validated") from exc
    except OSError as exc:
        raise ArchiveError(f"Cannot read XYZ file '{path}': {exc}") from exc

    lines = text.splitlines()
    frames: List[List[str]] = []
    i = 0
    while i < len(lines):
        # Permit blank lines between frames, but an incomplete frame is an error.
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break
        try:
            natoms = int(lines[i].strip())
        except ValueError as exc:
            raise ArchiveError(f"Invalid XYZ atom count in {path} at line {i + 1}") from exc
        if natoms <= 0:
            raise ArchiveError(f"Invalid XYZ atom count {natoms} in {path} at line {i + 1}")
        if i + 1 + natoms >= len(lines) + 1:
            raise ArchiveError(f"Incomplete XYZ frame in {path} starting at line {i + 1}")
        start = i + 2
        end = start + natoms
        if end > len(lines):
            raise ArchiveError(f"Incomplete XYZ frame in {path} starting at line {i + 1}")
        symbols: List[str] = []
        for line_no, line in enumerate(lines[start:end], start=start + 1):
            fields = line.split()
            if len(fields) < 4:
                raise ArchiveError(f"Invalid XYZ atom line in {path} at line {line_no}")
            symbols.append(fields[0])
        frames.append(symbols)
        i = end
    if not frames:
        raise ArchiveError(f"No XYZ frames found in {path}")
    return frames


def _validate_xyz_consistency(paths: Dict[str, Path]) -> int:
    geometry_frames = _xyz_frames(paths["geometry"])
    velocity_frames = _xyz_frames(paths["velocity"])
    trajectory_frames = _xyz_frames(paths["trajectory"])

    expected = geometry_frames[0]
    for label, frames in (("velocity", velocity_frames), ("trajectory", trajectory_frames)):
        for frame_index, symbols in enumerate(frames, start=1):
            if symbols != expected:
                raise ArchiveError(
                    f"XYZ atom mismatch: {label} frame {frame_index} does not contain the "
                    "same atoms in the same order as geometry"
                )
    return len(expected)


def _numeric_tokens(lines: Iterable[str]) -> List[float]:
    values: List[float] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for token in stripped.replace(",", " ").split():
            if not _FLOAT_RE.match(token):
                raise ValueError(token)
            values.append(float(token.replace("D", "E").replace("d", "e")))
    return values


def _validate_hessian(path: Path, natoms: int) -> str:
    """Validate accepted Hessian encodings and return the detected format."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ArchiveError(f"Hessian file is not valid UTF-8 text: {path}") from exc
    except OSError as exc:
        raise ArchiveError(f"Cannot read Hessian file '{path}': {exc}") from exc

    dimension = 3 * natoms
    full_count = dimension * dimension
    triangular_count = dimension * (dimension + 1) // 2
    lines = text.splitlines()

    # Required lower-diagonal form: two blank lines followed by one value per line.
    blank_indices = [i for i, line in enumerate(lines[: min(len(lines), 20)]) if not line.strip()]
    lower_values: Optional[List[float]] = None
    if len(blank_indices) >= 2:
        second_blank = blank_indices[1]
        trailing = lines[second_blank + 1 :]
        if all((not ln.strip()) or len(ln.split()) == 1 for ln in trailing):
            try:
                candidate = _numeric_tokens(trailing)
            except ValueError:
                candidate = []
            if len(candidate) == triangular_count:
                lower_values = candidate

    if lower_values is not None:
        return "lower_triangular"

    try:
        full_values = _numeric_tokens(lines)
    except ValueError as exc:
        raise ArchiveError(
            f"Hessian '{path}' contains non-numeric data in the full-matrix representation"
        ) from exc
    if len(full_values) == full_count:
        return "full_matrix"
    if len(full_values) == triangular_count:
        return "lower_triangular"

    raise ArchiveError(
        f"Hessian '{path}' is inconsistent with {natoms} atoms: expected "
        f"{full_count} values (full matrix) or {triangular_count} values (lower triangle), "
        f"found {len(full_values)}"
    )


def _build_simulation_metadata(args: argparse.Namespace, natoms: int) -> dict:
    return {
        "molecule_name": args.molecule_name,
        "level_of_theory": args.level_of_theory,
        "basis_set": args.basis_set,
        "time_step": args.time_step,
        "simulation_steps": args.simulation_steps,
        "initial_condition_id": args.initial_condition_id,
        "electronic_structure_software": args.electronic_structure_software,
        "units": args.units,
        "atom_count": natoms,
    }


def _input_map_from_args(args: argparse.Namespace) -> Dict[str, Path]:
    inputs = {
        "geometry": Path(args.geometry),
        "hessian": Path(args.hessian),
        "velocity": Path(args.velocity),
        "trajectory": Path(args.trajectory),
    }
    for label, path in inputs.items():
        _validate_readable_file(path, label)
    for label in ("geometry", "velocity", "trajectory"):
        if inputs[label].suffix.lower() != ".xyz":
            raise ArchiveError(f"{label} file must have .xyz extension: {inputs[label]}")
    return inputs


def _create_dataset_from_file(group, dataset_name: str, path: Path, compression: Optional[str], compression_opts) -> dict:
    stat = path.stat()
    size = stat.st_size
    chunk_size = min(max(size, 1), 1024 * 1024)
    dtype = np.dtype("u1")

    kwargs = {
        "shape": (size,),
        "dtype": dtype,
        "chunks": (chunk_size,),
    }
    if compression is not None:
        kwargs["compression"] = compression
        kwargs["compression_opts"] = compression_opts
        kwargs["shuffle"] = False

    dataset = group.create_dataset(dataset_name, **kwargs)
    with path.open("rb") as handle:
        offset = 0
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            arr = np.frombuffer(chunk, dtype=np.uint8)
            dataset[offset : offset + len(arr)] = arr
            offset += len(arr)

    metadata = {
        "original_filename": path.name,
        "original_path": str(path),
        "extraction_path": _relative_path_text(path, None),
        "file_size": size,
        "last_modification_time": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "content_type": mimetypes.guess_type(path.name)[0] or "text/plain",
        "sha256": _file_sha256(path),
    }
    for key, value in metadata.items():
        dataset.attrs[key] = _h5_attr_value(value)
    return metadata


def create_archive(args: argparse.Namespace) -> int:
    inputs = _input_map_from_args(args)
    natoms = _validate_xyz_consistency(inputs)
    hessian_format = _validate_hessian(inputs["hessian"], natoms)

    archive = Path(args.output).resolve()
    if archive.exists() and not args.force:
        raise ArchiveError(f"Output archive already exists: {archive} (use --force to overwrite)")
    archive.parent.mkdir(parents=True, exist_ok=True)

    compression = None if args.no_compression else args.compression
    compression_opts = None if compression != "gzip" else args.gzip_level
    simulation = _build_simulation_metadata(args, natoms)
    archive_meta = {
        "archive_format_version": ARCHIVE_FORMAT_VERSION,
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "creation_timestamp": _utc_timestamp(),
        "compression_algorithm": compression or "none",
        "compression_settings": {"level": compression_opts} if compression == "gzip" else {},
    }
    file_meta: Dict[str, dict] = {}

    try:
        with h5py.File(archive, "w") as h5:
            for key, value in archive_meta.items():
                h5.attrs[key] = _h5_attr_value(value)
            h5.attrs["required_datasets"] = json.dumps(list(REQUIRED_DATASETS))
            h5.attrs["hessian_format"] = hessian_format

            molecule = h5.create_group(args.molecule_name)
            for key, value in simulation.items():
                molecule.attrs[key] = _h5_attr_value(value)

            for logical_name in REQUIRED_DATASETS:
                file_meta[logical_name] = _create_dataset_from_file(
                    molecule,
                    logical_name,
                    inputs[logical_name],
                    compression,
                    compression_opts,
                )
    except (OSError, ValueError, RuntimeError) as exc:
        try:
            archive.unlink(missing_ok=True)
        except OSError:
            pass
        raise ArchiveError(f"Failed to create archive '{archive}': {exc}") from exc

    # Re-open the completed archive and generate the external manifest from
    # the HDF5 attributes. HDF5 is therefore the canonical metadata source;
    # the JSON file is a derived, human-readable manifest.
    sidecar = _build_sidecar_from_hdf5(archive)
    _write_sidecar_json(archive, sidecar)
    print(f"Created archive: {archive}")
    print(f"JSON metadata:   {archive}.json")
    print(f"Molecule:        {args.molecule_name}")
    print(f"Atoms:           {natoms}")
    print(f"Hessian format:  {hessian_format}")
    print(f"Compression:     {_display_compression(compression, compression_opts)}")
    return 0



def _read_h5_json_attr(attrs, key: str):
    value = attrs[key]
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        # Only attributes intentionally serialized as JSON should be decoded.
        # Plain strings such as format versions must remain strings ("1.0"
        # must not silently become the JSON number 1.0).
        json_keys = {"compression_settings", "units"}
        if key in json_keys:
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ArchiveError(f"Invalid JSON-encoded HDF5 attribute: {key}") from exc
        return value
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _build_sidecar_from_hdf5(archive: Path) -> dict:
    with _open_archive(archive) as h5:
        archive_meta = {}
        for key in (
            "archive_format_version",
            "metadata_schema_version",
            "creation_timestamp",
            "compression_algorithm",
            "compression_settings",
        ):
            if key not in h5.attrs:
                raise ArchiveError(f"Archive is missing root metadata: {key}")
            archive_meta[key] = _read_h5_json_attr(h5.attrs, key)

        molecule, molecule_name = _get_molecule_group(h5)
        simulation_keys = (
            "molecule_name",
            "level_of_theory",
            "basis_set",
            "time_step",
            "simulation_steps",
            "initial_condition_id",
            "electronic_structure_software",
            "units",
            "atom_count",
        )
        simulation = {
            key: _read_h5_json_attr(molecule.attrs, key)
            for key in simulation_keys
            if key in molecule.attrs
        }

        datasets = {}
        for dataset_name in REQUIRED_DATASETS:
            if dataset_name not in molecule:
                raise ArchiveError(f"Missing required dataset: {molecule_name}/{dataset_name}")
            ds = molecule[dataset_name]
            keys = (
                "original_filename",
                "original_path",
                "extraction_path",
                "file_size",
                "last_modification_time",
                "content_type",
                "sha256",
            )
            datasets[dataset_name] = {
                key: _read_h5_json_attr(ds.attrs, key)
                for key in keys
                if key in ds.attrs
            }

        return {
            "archive": archive_meta,
            "molecule": simulation,
            "datasets": datasets,
        }

def _validate_archive_file_metadata(dataset, dataset_name: str) -> None:
    required = ("original_filename", "original_path", "extraction_path", "file_size", "last_modification_time", "content_type", "sha256")
    missing = [key for key in required if key not in dataset.attrs]
    if missing:
        raise ArchiveError(f"Dataset '{dataset_name}' is missing metadata: {', '.join(missing)}")
    stored_size = int(dataset.attrs["file_size"])
    if stored_size != dataset.shape[0]:
        raise ArchiveError(
            f"Dataset '{dataset_name}' size mismatch: metadata={stored_size}, actual={dataset.shape[0]}"
        )


def _open_archive(archive: Path):
    if not archive.exists():
        raise ArchiveError(f"Archive does not exist: {archive}")
    if not archive.is_file():
        raise ArchiveError(f"Archive path is not a file: {archive}")
    try:
        return h5py.File(archive, "r")
    except (OSError, IOError) as exc:
        raise ArchiveError(f"Invalid or unreadable HDF5 archive '{archive}': {exc}") from exc


def _get_molecule_group(h5):
    groups = [name for name, item in h5.items() if isinstance(item, h5py.Group)]
    if len(groups) != 1:
        raise ArchiveError(f"Expected exactly one molecule group, found {len(groups)}")
    return h5[groups[0]], groups[0]


def verify_archive(archive: Path) -> int:
    with _open_archive(archive) as h5:
        version = str(h5.attrs.get("archive_format_version", ""))
        if version != ARCHIVE_FORMAT_VERSION:
            raise ArchiveError(
                f"Unsupported archive format version {version!r}; supported version is {ARCHIVE_FORMAT_VERSION!r}"
            )
        for key in ("creation_timestamp", "compression_algorithm", "compression_settings"):
            if key not in h5.attrs:
                raise ArchiveError(f"Archive is missing root metadata: {key}")
        molecule, molecule_name = _get_molecule_group(h5)
        required_sim = (
            "molecule_name", "level_of_theory", "basis_set", "time_step",
            "simulation_steps", "initial_condition_id", "electronic_structure_software",
            "units", "atom_count",
        )
        missing_sim = [key for key in required_sim if key not in molecule.attrs]
        if missing_sim:
            raise ArchiveError(f"Molecule group is missing metadata: {', '.join(missing_sim)}")
        for dataset_name in REQUIRED_DATASETS:
            if dataset_name not in molecule:
                raise ArchiveError(f"Missing required dataset: {molecule_name}/{dataset_name}")
            _validate_archive_file_metadata(molecule[dataset_name], dataset_name)

    sidecar = archive.with_suffix(archive.suffix + ".json")
    if sidecar.exists():
        try:
            with sidecar.open("r", encoding="utf-8") as handle:
                sidecar_data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ArchiveError(f"External JSON metadata is invalid: {sidecar}: {exc}") from exc
        canonical = _build_sidecar_from_hdf5(archive)
        if sidecar_data != canonical:
            raise ArchiveError(
                f"External JSON metadata does not match canonical HDF5 metadata: {sidecar}"
            )
        sidecar_status = "External JSON metadata matches HDF5 metadata."
    else:
        sidecar_status = "No external JSON metadata file found; HDF5 metadata remain self-contained."

    print(f"Archive verified: {archive}")
    print("All required datasets and metadata are present; recorded sizes match stored sizes.")
    print(sidecar_status)
    return 0


def list_archive(archive: Path) -> int:
    with _open_archive(archive) as h5:
        molecule, molecule_name = _get_molecule_group(h5)
        print(f"Archive format: {h5.attrs.get('archive_format_version', '<missing>')}")
        print(f"Molecule:       {molecule_name}")
        print(f"Compression:    {h5.attrs.get('compression_algorithm', '<missing>')}")
        for dataset_name in REQUIRED_DATASETS:
            if dataset_name not in molecule:
                print(f"- {dataset_name}: MISSING")
                continue
            ds = molecule[dataset_name]
            print(
                f"- {dataset_name}: {ds.attrs.get('original_filename', '?')} "
                f"({int(ds.attrs.get('file_size', ds.shape[0]))} bytes)"
            )
    return 0


def extract_archive(args: argparse.Namespace) -> int:
    archive = Path(args.archive).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted = []
    with _open_archive(archive) as h5:
        version = str(h5.attrs.get("archive_format_version", ""))
        if version != ARCHIVE_FORMAT_VERSION:
            raise ArchiveError(
                f"Unsupported archive format version {version!r}; supported version is {ARCHIVE_FORMAT_VERSION!r}"
            )
        molecule, _ = _get_molecule_group(h5)
        for dataset_name in REQUIRED_DATASETS:
            if dataset_name not in molecule:
                raise ArchiveError(f"Missing required dataset: {dataset_name}")
            ds = molecule[dataset_name]
            _validate_archive_file_metadata(ds, dataset_name)
            filename = str(ds.attrs["original_filename"])
            relative_path = str(ds.attrs["extraction_path"])
            target = _safe_extract_target(output_dir, relative_path, filename)
            if target.exists() and not args.force:
                raise ArchiveError(f"Refusing to overwrite existing file: {target} (use --force)")
            target.parent.mkdir(parents=True, exist_ok=True)
            temp_target = target.with_name(target.name + ".part")
            try:
                with temp_target.open("wb") as handle:
                    data = ds
                    for start in range(0, data.shape[0], 1024 * 1024):
                        stop = min(start + 1024 * 1024, data.shape[0])
                        handle.write(data[start:stop].tobytes())
                os.replace(temp_target, target)
            except OSError as exc:
                try:
                    temp_target.unlink(missing_ok=True)
                except OSError:
                    pass
                raise ArchiveError(f"Failed to extract '{dataset_name}' to '{target}': {exc}") from exc

            expected_hash = str(ds.attrs["sha256"])
            actual_hash = _file_sha256(target)
            if expected_hash != actual_hash:
                raise ArchiveError(
                    f"Integrity check failed for extracted '{target}': SHA-256 does not match archive metadata"
                )
            extracted.append(target)

    metadata_path = output_dir / "metadata.json"
    if metadata_path.exists() and not args.force:
        raise ArchiveError(
            f"Refusing to overwrite existing metadata file: {metadata_path} (use --force)"
        )
    metadata = _build_sidecar_from_hdf5(archive)
    _write_sidecar_json_to_path(metadata_path, metadata)

    print(f"Extracted {len(extracted)} files to: {output_dir}")
    for path in extracted:
        print(f"  {path}")
    print(f"  {metadata_path}")
    return 0


def metadata_archive(args: argparse.Namespace) -> int:
    archive = Path(args.archive).resolve()
    metadata = _build_sidecar_from_hdf5(archive)

    if args.output:
        output = Path(args.output).resolve()
        if output.exists() and not args.force:
            raise ArchiveError(
                f"Refusing to overwrite metadata file: {output} (use --force)"
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        _write_sidecar_json_to_path(output, metadata)
        print(f"Metadata written to: {output}")
    else:
        print(json.dumps(metadata, indent=2, sort_keys=True, default=_json_default))
    return 0


def _add_simulation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--molecule-name", required=True)
    parser.add_argument("--level-of-theory", required=True)
    parser.add_argument("--basis-set", default="")
    parser.add_argument("--time-step", required=True)
    parser.add_argument("--simulation-steps", type=int, required=True)
    parser.add_argument("--initial-condition-id", required=True)
    parser.add_argument("--electronic-structure-software", required=True)
    parser.add_argument("--units", required=True, help="JSON object or descriptive string, e.g. '{\"length\":\"angstrom\"}'")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Package geometry, Hessian, velocity, and trajectory text files into HDF5."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a new HDF5 archive")
    create.add_argument("--geometry", default=DEFAULT_FILES["geometry"])
    create.add_argument("--hessian", default=DEFAULT_FILES["hessian"])
    create.add_argument("--velocity", default=DEFAULT_FILES["velocity"])
    create.add_argument("--trajectory", default=DEFAULT_FILES["trajectory"])
    create.add_argument("-o", "--output", required=True)
    create.add_argument("--no-compression", action="store_true")
    create.add_argument("--compression", choices=("lzf", "gzip"), default="lzf")
    create.add_argument("--gzip-level", type=int, choices=range(0, 10), default=4)
    create.add_argument("--force", action="store_true")
    _add_simulation_args(create)

    extract = subparsers.add_parser("extract", help="Extract all files from an HDF5 archive")
    extract.add_argument("archive")
    extract.add_argument("-o", "--output-dir", required=True)
    extract.add_argument("--force", action="store_true")

    metadata = subparsers.add_parser(
        "metadata", help="Display archive metadata or export it as JSON"
    )
    metadata.add_argument("archive")
    metadata.add_argument("-o", "--output", help="Write metadata JSON to this path instead of stdout")
    metadata.add_argument("--force", action="store_true")

    verify = subparsers.add_parser("verify", help="Verify archive structure and recorded sizes")
    verify.add_argument("archive")

    listing = subparsers.add_parser("list", help="List archive contents without extraction")
    listing.add_argument("archive")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            return create_archive(args)
        if args.command == "extract":
            return extract_archive(args)
        if args.command == "metadata":
            return metadata_archive(args)
        if args.command == "verify":
            return verify_archive(Path(args.archive).resolve())
        if args.command == "list":
            return list_archive(Path(args.archive).resolve())
        parser.error(f"Unknown command: {args.command}")
    except ArchiveError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
