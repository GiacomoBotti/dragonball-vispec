#!/usr/bin/env python3
"""Reconstruct a Hessian file from a Hessian database.

This script reproduces the logic of the original Bash workflow:

1. Read the list of output indexes from an index file.
2. For each index, extract the corresponding Hessian block from the
   database file.
3. Write the selected Hessian blocks to a new output file.

The Hessian blocks are assumed to be printed with two blank lines at the
beginning, so the user must provide ``--hlen`` as the Hessian length plus 2.

Examples
--------
.. code-block:: bash

   python reconstruct_hessian.py \
       --index-file index.dat \
       --hess-file Hessians.dat \
       --hess-out Hess_out.dat \
       --hlen 104
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser for the Hessian reconstruction workflow.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct a Hessian file from database output indexes and a "
            "file containing computed Hessians."
        )
    )

    parser.add_argument(
        "--index-file",
        required=True,
        help="File containing the output indexes, one integer per line.",
    )
    parser.add_argument(
        "--hess-file",
        required=True,
        help="File containing the computed Hessians.",
    )
    parser.add_argument(
        "--hess-out",
        required=True,
        help="Output file where the reconstructed Hessians will be written.",
    )
    parser.add_argument(
        "--hlen",
        required=True,
        type=int,
        help="Hessian block length (lower-diagonal) plus 2.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debugging information while reconstructing the file.",
    )

    return parser


def read_indexes(index_file: str | Path) -> List[int]:
    """Read integer indexes from a text file.

    Parameters
    ----------
    index_file
        Path to the index file.

    Returns
    -------
    list[int]
        List of 1-based indexes read from the file.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If a non-integer line is found.
    """
    p = Path(index_file)
    if not p.exists():
        raise FileNotFoundError(f"Index file not found: {p}")

    indexes: List[int] = []
    for line_no, line in enumerate(p.read_text().splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            indexes.append(int(text))
        except Exception as exc:
            raise ValueError(f"Invalid index on line {line_no} of {p}: {text!r}") from exc

    return indexes


def read_lines(path: str | Path) -> List[str]:
    """Read all lines from a file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p.read_text().splitlines(keepends=True)


def reconstruct_hessians(
    index_file: str | Path,
    hess_file: str | Path,
    hess_out: str | Path,
    hlen: int,
    debug: bool = False,
) -> None:
    """Reconstruct the selected Hessian blocks.

    Parameters
    ----------
    index_file
        File containing the selected database indexes.
    hess_file
        File containing all computed Hessians.
    hess_out
        Output file to be written.
    hlen
        Hessian block length plus 2.
    debug
        If ``True``, print extra information.

    Notes
    -----
    The original Bash script used:

    .. code-block:: bash

       head -n $((2*$Hlen*$j)) $Hess_file | tail -n $((2*$Hlen)) | head -n $Hlen

    for each index ``j``. This Python implementation performs the same
    selection using list slicing.
    """
    indexes = read_indexes(index_file)
    hess_lines = read_lines(hess_file)

    if hlen <= 0:
        raise ValueError("--hlen must be a positive integer")

    #total_block = 2 * hlen
    total_block = hlen

    if debug:
        print(f"[debug] number of indexes: {len(indexes)}")
        print(f"[debug] Hessian block length + 2 (hlen): {hlen}")
        print(f"[debug] total block length used by script: {total_block}")
        print(f"[debug] total lines in Hessian file: {len(hess_lines)}")

    out_path = Path(hess_out)
    if out_path.exists():
        out_path.unlink()

    with out_path.open("w", encoding="utf-8") as out:
        for i, j in enumerate(indexes, start=1):
            if j <= 0:
                raise ValueError(f"Index values must be 1-based positive integers, got {j}")

            end = total_block * j
            start = end - total_block

            if start < 0 or end > len(hess_lines):
                raise ValueError(
                    f"Index {j} selects lines [{start}:{end}] but Hessian file has "
                    f"only {len(hess_lines)} lines."
                )

            block = hess_lines[start:end][:hlen]

            if debug:
                print(f"[debug] index #{i}: j={j}, slice=({start}, {end}), written_lines={len(block)}")

            out.writelines(block)

    if debug:
        print(f"[debug] reconstructed file written to {out_path}")


def main() -> None:
    """Program entry point."""
    args = build_parser().parse_args()

    reconstruct_hessians(
        index_file=args.index_file,
        hess_file=args.hess_file,
        hess_out=args.hess_out,
        hlen=args.hlen,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
