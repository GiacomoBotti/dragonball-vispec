#!/usr/bin/env python3
"""Prepare Hessian input folders from an XYZ trajectory.

The script reads geometries from an XYZ trajectory and creates one folder per
geometry (``geo1``, ``geo2``, ...) containing an input file for one of:

* ORCA
* Q-Chem
* Gaussian 16

The trajectory parser is shared by all programs; only the input writer and
file extension differ between backends.

Examples
--------
    python prep_multi.py --program orca --ngeo 265 --nat 3 --traj trj.xyz
    python prep_multi.py --program qchem --ngeo 265 --nat 3 --traj trj.xyz
    python prep_multi.py --program gaussian --ngeo 265 --nat 3 --traj trj.xyz

A helper script can be copied into every geometry directory with
``--template-script``. If omitted, the default is selected from the program.
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple


Atom = Tuple[str, float, float, float]


@dataclass(frozen=True)
class Backend:
    """Description of one quantum-chemistry input backend."""

    name: str
    extension: str
    default_template_script: str
    writer: Callable[[Path, List[Atom], str], None]


# ---------------------------------------------------------------------------
# Input writers
# ---------------------------------------------------------------------------

def write_orca_input(
    out_path: Path,
    atoms: List[Atom],
    title: str,
) -> None:
    """Write an ORCA frequency/Hessian input file."""

    header_lines = [
        "! B3LYP D3BJ Def2-TZVPD FREQ TightSCF",
        "%PAL NPROCS 20 END",
        "%SCF",
        "MAXITER 500",
        "END",
        "* xyz 0 1",
    ]

    with out_path.open("w", encoding="utf-8") as handle:
        for line in header_lines:
            handle.write(f"{line}\n")
        for sym, x, y, z in atoms:
            handle.write(f"{sym} {x:.10f} {y:.10f} {z:.10f}\n")
        handle.write("*\n")


def write_qchem_input(
    out_path: Path,
    atoms: List[Atom],
    title: str,
) -> None:
    """Write a Q-Chem frequency/Hessian input file."""

    with out_path.open("w", encoding="utf-8") as handle:
        handle.write("$comment\n")
        handle.write(f"{title}\n")
        handle.write("$end\n\n")

        handle.write("$molecule\n")
        handle.write("0 1\n")
        for sym, x, y, z in atoms:
            handle.write(f"{sym} {x:.10f} {y:.10f} {z:.10f}\n")
        handle.write("$end\n\n")

        handle.write("$rem\n")
        handle.write("JOBTYPE FREQ\n")
        handle.write("METHOD B3LYP\n")
        handle.write("BASIS DEF2-TZVPD\n")
        handle.write("DFT_D D3_BJ\n")
        handle.write("SCF_CONVERGENCE 8\n")
        handle.write("MAX_SCF_CYCLES 500\n")
        handle.write("$end\n")


def write_gaussian_input(
    out_path: Path,
    atoms: List[Atom],
    title: str,
) -> None:
    """Write a Gaussian 16 frequency/Hessian input file."""

    with out_path.open("w", encoding="utf-8") as handle:
# B3LYP/Def2TZVP EmpiricalDispersion=GD3BJ Opt=(CalcAll,MaxCycles=200,Tight) int=ultrafine SCF(XQC,Tight)
        handle.write("%mem=250Gb\n")
        handle.write("%NProcShared=48\n")
        handle.write(f"%Chk={out_path.with_suffix('.chk').name}\n")
        handle.write("# B3LYP/Def2TZVP EmpiricalDispersion=GD3BJ int=ultrafine Freq Iop(7/33=1) SCF=(XQC,Tight)\n")
        handle.write("\n")
        handle.write(f"{title}\n")
        handle.write("\n")
        handle.write("0 1\n")
        for sym, x, y, z in atoms:
            handle.write(f"{sym} {x:.10f} {y:.10f} {z:.10f}\n")
        handle.write("\n")


BACKENDS = {
    "orca": Backend(
        name="orca",
        extension=".inp",
        default_template_script="lancia_orca.sh",
        writer=write_orca_input,
    ),
    "qchem": Backend(
        name="qchem",
        extension=".in",
        default_template_script="lancia_qchem.sh",
        writer=write_qchem_input,
    ),
    "gaussian": Backend(
        name="gaussian",
        extension=".gjf",
        default_template_script="lancia_g16.sh",
        writer=write_gaussian_input,
    ),
}


# ---------------------------------------------------------------------------
# Trajectory handling
# ---------------------------------------------------------------------------

def read_next_geometry(
    handle,
    nat: int,
) -> Tuple[str, List[Atom]]:
    """Read one XYZ geometry from an open trajectory file."""

    comment = handle.readline()
    if not comment:
        raise ValueError("Unexpected end of file while reading trajectory comment line")

    atoms: List[Atom] = []
    for i in range(nat):
        line = handle.readline()
        if not line:
            raise ValueError(f"Unexpected end of file while reading atom {i + 1}")
        parts = line.split()
        if len(parts) < 4:
            raise ValueError(f"Malformed atom line: {line!r}")
        try:
            atoms.append(
                (parts[0], float(parts[1]), float(parts[2]), float(parts[3]))
            )
        except ValueError as exc:
            raise ValueError(f"Malformed coordinate line: {line!r}") from exc

    return comment.rstrip("\n"), atoms


def copy_template_script(
    template_script: str | Path,
    folder: Path,
    debug: bool = False,
) -> None:
    """Copy a helper shell script into a geometry directory, if it exists."""

    src = Path(template_script)
    if not src.exists():
        if debug:
            print(f"[debug] template script not found: {src}")
        return

    dst = folder / src.name
    shutil.copy2(src, dst)
    if debug:
        print(f"[debug] copied template script to {dst}")


# ---------------------------------------------------------------------------
# Main preparation routine
# ---------------------------------------------------------------------------

def prepare_geometries(
    ngeo: int,
    nat: int,
    traj_path: str | Path,
    backend: Backend,
    template_script: str | Path | None = None,
    debug: bool = False,
) -> None:
    """Prepare inputs for all requested geometries."""

    if ngeo <= 0:
        raise ValueError("--ngeo must be a positive integer")
    if nat <= 0:
        raise ValueError("--nat must be a positive integer")

    traj = Path(traj_path)
    if not traj.exists():
        raise FileNotFoundError(f"Trajectory file not found: {traj}")

    if template_script is None:
        template_script = backend.default_template_script

    with traj.open("r", encoding="utf-8", errors="replace") as handle:
        for i in range(1, ngeo + 1):
            nat_line = handle.readline()
            if not nat_line:
                raise ValueError(f"Trajectory ended before geometry {i}")

            try:
                nat_file = int(nat_line.split()[0])
            except (ValueError, IndexError) as exc:
                raise ValueError(
                    f"Could not read atom count for geometry {i}"
                ) from exc

            if nat_file != nat:
                raise ValueError(
                    f"Geometry {i}: nat in trajectory is {nat_file}, expected {nat}"
                )

            comment, atoms = read_next_geometry(handle, nat)

            folder = Path(f"geo{i}")
            folder.mkdir(exist_ok=True)
            copy_template_script(template_script, folder, debug=debug)

            inp_path = folder / f"geo{i}{backend.extension}"
            backend.writer(inp_path, atoms, comment or f"Geometry {i}")

            if debug:
                print(f"[debug] wrote {inp_path}")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Split an XYZ trajectory into per-geometry Hessian inputs for "
            "ORCA, Q-Chem, or Gaussian 16."
        )
    )

    parser.add_argument(
        "--program",
        "--backend",
        dest="program",
        required=True,
        choices=sorted(BACKENDS),
        help="Quantum-chemistry program used to generate the input files.",
    )
    parser.add_argument(
        "--ngeo",
        required=True,
        type=int,
        help="Number of geometries to export from the trajectory.",
    )
    parser.add_argument(
        "--nat",
        required=True,
        type=int,
        help="Number of atoms in each geometry.",
    )
    parser.add_argument(
        "--traj",
        default="trj.xyz",
        help="Input trajectory file in XYZ format.",
    )
    parser.add_argument(
        "--template-script",
        default=None,
        help=(
            "Helper script copied into each geometry folder. If omitted, "
            "a program-specific default is used."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debugging information while processing the trajectory.",
    )

    return parser


def main() -> None:
    """Program entry point."""

    args = build_parser().parse_args()
    backend = BACKENDS[args.program]

    if args.debug:
        print(f"[debug] program         = {backend.name}")
        print(f"[debug] ngeo            = {args.ngeo}")
        print(f"[debug] nat             = {args.nat}")
        print(f"[debug] traj            = {args.traj}")
        print(
            f"[debug] template_script = "
            f"{args.template_script or backend.default_template_script}"
        )

    prepare_geometries(
        ngeo=args.ngeo,
        nat=args.nat,
        traj_path=args.traj,
        backend=backend,
        template_script=args.template_script,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
