#!/usr/bin/env python3
"""Collect Hessian blocks from per-geometry folders into one file.

This script reproduces the ORCA Hessian collection workflow in Python.

Workflow
--------
1. Read ``--nat`` and ``--ngeo`` from the command line.
2. Loop over ``geo1``, ``geo2``, ..., ``geoN``.
3. Read ``geoN/geoN.hess``.
4. Extract the ORCA Hessian block between ``$hessian`` and
   ``$vibrational_frequencies``.
5. Reconstruct the full symmetric Hessian matrix from the block.
6. Append the matrix values to ``Hessian.out`` after two blank lines.

Examples
--------
.. code-block:: bash

   python collect_hessian.py --nat 12 --ngeo 20
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal


# Gaussian 16 Hessian markers (same conventions used by Bulma)
GAUSSIAN_HESS_START = "Force constants in Cartesian coordinates"
GAUSSIAN_HESS_END = "Final forces over variables"

# Q-Chem HESS markers (same conventions used by Bulma)
QCHEM_HESS_START = "$hessian"
QCHEM_HESS_END = "$end"


ORCA_HESS_START = "$hessian"
ORCA_HESS_END = "$vibrational_frequencies"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser for the Hessian collection workflow.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Collect Hessian matrices from geoN/geoN.hess files and append "
            "them to a single Hessian.out file."
        )
    )

    parser.add_argument(
        "--nat",
        required=True,
        type=int,
        help="Number of atoms.",
    )
    parser.add_argument(
        "--ngeo",
        required=True,
        type=int,
        help="Number of geometry folders to scan.",
    )
    parser.add_argument(
        "--output",
        default="Hessian.out",
        help="Output file to write the collected Hessians.",
    )
    parser.add_argument(
        "--geo-prefix",
        default="geo",
        help="Prefix for the geometry folders (default: geo1, geo2, ...).",
    )
    parser.add_argument(
        "--program",
        choices=("orca", "qchem", "gaussian"),
        default="orca",
        help="Quantum-chemistry program used for the Hessian calculations (default: orca).",
    )
    parser.add_argument(
        "--hess-suffix",
        default=None,
        help=(
            "Override the Hessian output filename suffix. By default: "
            "ORCA=.hess, Q-Chem=HESS, Gaussian=.log."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debugging information while processing the files.",
    )

    return parser


def extract_orca_hessian_chunk(text_lines: list[str]) -> list[str]:
    """Extract the ORCA Hessian block.

    Parameters
    ----------
    text_lines
        Full contents of an ORCA ``.hess`` file split into lines.

    Returns
    -------
    list[str]
        Lines belonging to the Hessian block, with the first two and last two
        lines removed.

    Raises
    ------
    RuntimeError
        If the start or end markers are missing, or if the block is too short.
    """
    start = None
    end = None

    for i, ln in enumerate(text_lines):
        if start is None and ln.strip().startswith(ORCA_HESS_START):
            start = i
            continue
        if start is not None and ln.strip().startswith(ORCA_HESS_END):
            end = i
            break

    if start is None:
        raise RuntimeError(f"Could not find ORCA start marker: {ORCA_HESS_START!r}")
    if end is None:
        raise RuntimeError(f"Could not find ORCA end marker: {ORCA_HESS_END!r}")

    chunk = text_lines[start : end + 1]
    if len(chunk) < 5:
        raise RuntimeError("ORCA Hessian chunk too short.")

    return chunk[2:-2]


def parse_orca_full_matrix(chunk_lines: list[str]) -> list[list[str]]:
    """Parse the ORCA full Hessian matrix printed in column blocks.

    Parameters
    ----------
    chunk_lines
        Hessian chunk extracted by :func:`extract_orca_hessian_chunk`.

    Returns
    -------
    list[list[str]]
        Full symmetric matrix as a list of rows, each row containing strings.

    Raises
    ------
    RuntimeError
        If no numeric Hessian rows are detected, if a row is missing, or if a
        row has the wrong number of values.
    """
    rows: dict[int, list[str]] = {}
    max_row = -1

    for raw in chunk_lines:
        s = raw.strip()
        if not s:
            continue

        toks = s.split()
        if len(toks) < 2:
            continue

        try:
            r = int(toks[0])
        except ValueError:
            continue

        # Skip header rows like "0 1 2 3 4 ...".
        if not any("." in t or "E" in t or "D" in t or "e" in t or "d" in t for t in toks[1:]):
            continue

        vals = [v.replace("D", "E").replace("d", "E") for v in toks[1:]]
        rows.setdefault(r, []).extend(vals)
        max_row = max(max_row, r)

    if max_row < 0:
        raise RuntimeError("No ORCA Hessian numeric rows detected.")

    ncart = max_row + 1
    full: list[list[str]] = []

    for r in range(ncart):
        if r not in rows:
            raise RuntimeError(f"Missing ORCA Hessian row {r}.")
        if len(rows[r]) != ncart:
            raise RuntimeError(
                f"ORCA Hessian row {r} has {len(rows[r])} values; expected {ncart}."
            )
        full.append(rows[r])

    return full

def orca_full_to_lower_triangle_rows(full: list[list[str]]) -> list[list[str]]:
    """Convert a full symmetric matrix to lower-triangle row blocks.

    Parameters
    ----------
    full
        Full symmetric matrix as ``full[i][j]``.

    Returns
    -------
    list[list[str]]
        Lower-triangle rows where row 0 has 1 value, row 1 has 2 values, etc.
        Each entry is a matrix value, not an index.
    """
    ncart = len(full)
    out: list[list[str]] = []

    for i in range(ncart):
        out.append([full[i][j] for j in range(i + 1)])

    return out


def extract_gaussian_hessian_chunk(text_lines: list[str]) -> list[str]:
    """Extract the Gaussian 16 Cartesian force-constant block.

    This follows Bulma's Gaussian Hessian parser: the block starts at
    ``Force constants in Cartesian coordinates`` and ends at
    ``Final forces over variables``.
    """
    start = None
    end = None

    for i, line in enumerate(text_lines):
        if start is None and GAUSSIAN_HESS_START in line:
            start = i
            continue
        if start is not None and GAUSSIAN_HESS_END in line:
            end = i
            break

    if start is None:
        raise RuntimeError(
            f"Could not find Gaussian 16 start marker: {GAUSSIAN_HESS_START!r}"
        )
    if end is None:
        raise RuntimeError(
            f"Could not find Gaussian 16 end marker: {GAUSSIAN_HESS_END!r}"
        )

    return text_lines[start + 1 : end]


def parse_lower_triangular_rows(chunk_lines: list[str]) -> dict[int, list[str]]:
    """Parse the Gaussian 16 lower-triangular Hessian rows.

    This is the same parsing convention used by Bulma. Gaussian prints the
    Hessian as lower-triangular rows, with row 1 containing one value, row 2
    two values, etc.
    """
    rows: dict[int, list[str]] = {}
    max_row = 0

    for raw in chunk_lines:
        if "." not in raw:
            continue
        s = raw.strip()
        if not s:
            continue

        toks = s.split()
        if len(toks) < 2:
            continue

        try:
            row = int(toks[0])
        except ValueError:
            continue

        values = [v.replace("D", "E").replace("d", "E") for v in toks[1:]]
        rows.setdefault(row, []).extend(values)
        max_row = max(max_row, row)

    if max_row == 0:
        raise RuntimeError("No Gaussian 16 Hessian numeric rows detected.")

    bad = [
        (row, len(rows.get(row, [])))
        for row in range(1, max_row + 1)
        if len(rows.get(row, [])) != row
    ]
    if bad:
        examples = ", ".join(
            f"row {row} has {count} values" for row, count in bad[:8]
        )
        raise RuntimeError(
            "Parsed Gaussian 16 Hessian rows do not match expected "
            f"lower-triangular shape (expected row r to have r values). {examples}."
        )

    return rows


def extract_qchem_hessian_lower_triangle_rows(
    text_lines: list[str],
) -> dict[int, list[str]]:
    """Extract the lower-triangular Hessian from a Q-Chem HESS file.

    This follows Bulma's Q-Chem parser. The HESS section has the form::

        $hessian
        Dimension   N
        <N*(N+1)/2 numbers>
        $end

    The numerical values are reconstructed into rows[1], rows[2], ... .
    """
    start = None
    end = None

    for i, line in enumerate(text_lines):
        stripped = line.strip().lower()
        if start is None and stripped == QCHEM_HESS_START:
            start = i
            continue
        if start is not None and stripped == QCHEM_HESS_END:
            end = i
            break

    if start is None:
        raise RuntimeError(
            f"Could not find Q-Chem start marker: {QCHEM_HESS_START!r}"
        )
    if end is None:
        raise RuntimeError(
            f"Could not find Q-Chem end marker: {QCHEM_HESS_END!r}"
        )

    import re
    dim_re = re.compile(r"^\s*Dimension\s+(\d+)\s*$", re.IGNORECASE)
    dim = None
    dim_i = None

    for j in range(start + 1, min(end, start + 20)):
        match = dim_re.match(text_lines[j])
        if match:
            dim = int(match.group(1))
            dim_i = j
            break

    if dim is None or dim_i is None:
        raise RuntimeError(
            "Could not find 'Dimension N' line after $hessian in Q-Chem HESS."
        )

    tokens: list[str] = []
    for line in text_lines[dim_i + 1 : end]:
        for part in line.split():
            try:
                float(part.replace("D", "E").replace("d", "E"))
            except ValueError:
                continue
            tokens.append(part.replace("D", "E").replace("d", "E"))

    expected = dim * (dim + 1) // 2
    if len(tokens) != expected:
        raise RuntimeError(
            f"Q-Chem Hessian size mismatch: parsed {len(tokens)} numbers, "
            f"expected {expected} for Dimension {dim} (lower triangle)."
        )

    rows: dict[int, list[str]] = {}
    k = 0
    for row in range(1, dim + 1):
        rows[row] = tokens[k : k + row]
        k += row

    return rows


def _default_hessian_path(
    folder: Path,
    stem: str,
    program: Literal["orca", "qchem", "gaussian"],
    hess_suffix: str | None,
) -> Path:
    """Return the expected Hessian output file for one geometry."""
    if hess_suffix is not None:
        suffix = hess_suffix
        if suffix.startswith("."):
            return folder / f"{stem}{suffix}"
        return folder / suffix

    if program == "orca":
        return folder / f"{stem}.hess"
    if program == "qchem":
        return folder / "HESS"
    return folder / f"{stem}.log"


def extract_hessian_rows(
    text_lines: list[str],
    program: Literal["orca", "qchem", "gaussian"],
) -> dict[int, list[str]]:
    """Extract a lower-triangular Hessian in the common collector format."""
    if program == "orca":
        chunk = extract_orca_hessian_chunk(text_lines)
        full = parse_orca_full_matrix(chunk)
        return {
            i + 1: [full[i][j] for j in range(i + 1)]
            for i in range(len(full))
        }

    if program == "qchem":
        return extract_qchem_hessian_lower_triangle_rows(text_lines)

    chunk = extract_gaussian_hessian_chunk(text_lines)
    return parse_lower_triangular_rows(chunk)

def collect_hessians(
    nat: int,
    ngeo: int,
    output: str | Path,
    geo_prefix: str = "geo",
    program: Literal["orca", "qchem", "gaussian"] = "orca",
    hess_suffix: str | None = None,
    debug: bool = False,
) -> None:
    """Collect Hessian blocks from all geometry folders and write one output file.

    Parameters
    ----------
    nat
        Number of atoms.
    ngeo
        Number of geometries / folders to process.
    output
        Output file path.
    geo_prefix
        Folder prefix (``geo`` means ``geo1``, ``geo2``, ...).
    program
        Hessian-producing program: ``orca``, ``qchem``, or ``gaussian``.
    hess_suffix
        Optional override for the Hessian output filename/suffix.
    debug
        If ``True``, print progress information.
    """
    ncart = 3 * nat

    if debug:
        print(f"[debug] nat   = {nat}")
        print(f"[debug] ngeo  = {ngeo}")
        print(f"[debug] ncart = {ncart}")
        print(f"[debug] program = {program}")
        print(f"[debug] output = {output}")

    out_path = Path(output)
    if out_path.exists():
        out_path.unlink()

    with out_path.open("w", encoding="utf-8") as out:
        for fold in range(1, ngeo + 1):
            folder = Path(f"{geo_prefix}{fold}")
            stem = f"{geo_prefix}{fold}"
            hess_path = _default_hessian_path(
                folder, stem, program, hess_suffix
            )

            if debug:
                print(f"[debug] processing {hess_path}")

            if not hess_path.exists():
                raise FileNotFoundError(
                    f"Hessian output not found for geometry {fold}: {hess_path}"
                )

            text_lines = hess_path.read_text(errors="replace").splitlines()
            lower_rows = extract_hessian_rows(text_lines, program)

            expected_ncart = 3 * nat
            actual_ncart = max(lower_rows)
            if actual_ncart != expected_ncart:
                raise RuntimeError(
                    f"Geometry {fold}: {program} Hessian has dimension {actual_ncart}, "
                    f"expected {expected_ncart} for nat={nat}."
                )

            out.write("\n")
            out.write("\n")

            #for row in full:
            #    for value in row:
            #        out.write(f"{value:>16s}\n")
            #for value in outH:
            #     out.write(f"{value:>16.10E}\n")
            for row in lower_rows:
                  for value in row:
                     out.write(f"{float(value):16.10E}\n")

    if debug:
        print(f"[debug] written {out_path}")


def main() -> None:
    """Program entry point."""
    args = build_parser().parse_args()
    collect_hessians(
        nat=args.nat,
        ngeo=args.ngeo,
        output=args.output,
        geo_prefix=args.geo_prefix,
        program=args.program,
        hess_suffix=args.hess_suffix,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
