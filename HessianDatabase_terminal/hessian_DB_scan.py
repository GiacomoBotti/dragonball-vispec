#!/usr/bin/env python3
"""Command-line interface for the trajectory / Hessian workflow.
This script uses named command-line arguments. It also reads the 
first geometry, assigns masses, builds the Cartesian mass array, 
reads the Hessian, mass-weights it, diagonalizes it, and reorders 
the modes so that the rotational/translational modes are placed
at the end.
Examples
--------
.. code-block:: bash
   python script.py \
       --nat 12 \
       --nmax 500 \
       --thr 0.25 \
       --input_traj traj.xyz \
       --input_hess hessian.dat \
       --output_geom final_geoms.xyz \
       --output_ind search_indexes.txt \
       --xyz equilibrium.xyz
"""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import List, Tuple
import numpy as np
# Atomic masses in atomic units (electron masses).
_MASS_DB = {
    "H": 1837.15,
    "D": 3671.48,
    "O": 29156.96,
    "Od": 32810.46,
    "C": 21874.66,
    "N": 25526.06,
    "Ti": 87256.20,
    "F": 34631.97,
    "S": 58281.54,
    "I": 231332.70,
}
SCAN_THR_VALUES = [
    "4.0e-1",
    "3.5e-1",
    "3.0e-1",
    "2.5e-1",
    "2.0e-1",
    "1.5e-1",
    "1.0e-1",
    "0.5e-1",
    "0.4e-1",
    "0.3e-1",
    "0.2e-1",
    "0.1e-1",
]
def read_first_geometry_from_traj(
    traj_path: str | Path,
    nat: int,
) -> tuple[list[str], np.ndarray]:
    """Read the first geometry from an extended XYZ trajectory.
    Parameters
    ----------
    traj_path
        Path to the trajectory file.
    nat
        Number of atoms.
    Returns
    -------
    list[str]
        Atomic symbols.
    numpy.ndarray
        Cartesian geometry with shape ``(nat, 3)``.
    Notes
    -----
    The trajectory format is assumed to be:
    .. code-block:: text
       nat
       comment line
       sym x y z vx vy vz
    Only the Cartesian coordinates are read.
    """
    p = Path(traj_path)
    if not p.exists():
        raise FileNotFoundError(f"Trajectory file not found: {p}")
    with p.open("r") as handle:
        line = handle.readline()
        if not line:
            raise ValueError("Empty trajectory file")
        nat_file = int(line.split()[0])
        if nat_file != nat:
            raise ValueError(
                f"nat={nat} does not match trajectory nat={nat_file}"
            )
        # Skip comment line
        _ = handle.readline()
        symbols: list[str] = []
        geom = np.zeros((nat, 3), dtype=float)
        for i in range(nat):
            parts = handle.readline().split()
            if len(parts) < 4:
                raise ValueError(
                    f"Malformed trajectory line for atom {i+1}"
                )
            symbols.append(parts[0])
            geom[i, 0] = _to_float(parts[1])
            geom[i, 1] = _to_float(parts[2])
            geom[i, 2] = _to_float(parts[3])
    return symbols, geom
def _to_float(token: str) -> float:
    """Parse a number that may use a Fortran ``D`` exponent."""
    token = token.strip().strip(",")
    token = token.replace("D", "E").replace("d", "e")
    return float(token)
def read_first_geometry_and_masses(
    xyz_path: str | Path,
    nat: int,
) -> Tuple[List[str], np.ndarray, np.ndarray, np.ndarray]:
    """Read the first geometry from an XYZ file and assign atomic masses.
    Parameters
    ----------
    xyz_path
        Path to the XYZ file.
    nat
        Number of atoms expected in the first geometry.
    Returns
    -------
    list[str]
        Atomic symbols in file order.
    numpy.ndarray
        Cartesian coordinates with shape ``(nat, 3)``.
    numpy.ndarray
        Atomic masses in atomic units with shape ``(nat,)``.
    numpy.ndarray
        Cartesian mass array with shape ``(3 * nat,)`` obtained via
        ``np.repeat(np.array(masses, dtype=float), 3)``.
    Raises
    ------
    FileNotFoundError
        If the XYZ file does not exist.
    ValueError
        If the file is empty or the first geometry is malformed.
    KeyError
        If an element is not found in the internal mass database and no mass
        is provided in the optional fifth XYZ column.
    """
    p = Path(xyz_path)
    if not p.exists():
        raise FileNotFoundError(f"XYZ file not found: {p}")
    lines = p.read_text().splitlines()
    if len(lines) < nat + 2:
        raise ValueError(f"XYZ file {p} has too few lines for nat={nat}")
    try:
        nat_file = int(lines[0].split()[0])
    except Exception as exc:
        raise ValueError(f"Could not read atom count from first line of {p}") from exc
    if nat_file != nat:
        raise ValueError(f"nat={nat} does not match first XYZ geometry atom count nat={nat_file}")
    symbols: List[str] = []
    geom = np.zeros((nat, 3), dtype=float)
    masses = np.zeros(nat, dtype=float)
    for i in range(nat):
        parts = lines[i + 2].split()
        if len(parts) < 4:
            raise ValueError(f"Malformed atom line {i+1} in {p}: expected at least 4 columns")
        sym = parts[0]
        symbols.append(sym)
        geom[i, 0] = _to_float(parts[1])
        geom[i, 1] = _to_float(parts[2])
        geom[i, 2] = _to_float(parts[3])
        mass = None
        if len(parts) >= 5:
            try:
                mass = _to_float(parts[4])
            except Exception:
                mass = None
        if mass is None:
            if sym not in _MASS_DB:
                raise KeyError(
                    f"Element '{sym}' not in the mass database. "
                    "Provide the mass in the 5th XYZ column or extend _MASS_DB."
                )
            mass = float(_MASS_DB[sym])
        masses[i] = float(mass)
    xm = np.repeat(np.array(masses, dtype=float), 3)
    return symbols, geom, masses, xm
def print_geometry_and_masses(symbols: List[str], geom: np.ndarray, masses: np.ndarray) -> None:
    """Print the geometry and masses in a human-readable format."""
    print("First geometry:")
    for i, (sym, xyz, mass) in enumerate(zip(symbols, geom, masses), start=1):
        print(
            f"  {i:3d}  {sym:>2s}  "
            f"{xyz[0]: .10f}  {xyz[1]: .10f}  {xyz[2]: .10f}   "
            f"mass = {mass: .6f}"
        )
    print()
def print_vector(name: str, vec: np.ndarray) -> None:
    """Print a one-dimensional vector with line wrapping."""
    print(f"{name}:")
    print("  " + " ".join(f"{value: .8e}" for value in vec))
    print()
def print_matrix(name: str, mat: np.ndarray) -> None:
    """Print a two-dimensional matrix in a readable format."""
    print(f"{name}:")
    for row in mat:
        print("  " + " ".join(f"{value: .8e}" for value in row))
    print()
def read_hessian_nwchem_lower_triangle(
    hess_filename: str | Path,
    ncart: int,
) -> np.ndarray:
    """Read a lower-triangular Hessian matrix from file.
    The Hessian format follows the convention used in Dragonball:
    after two header lines, the lower-triangular matrix elements are listed
    sequentially.
    Parameters
    ----------
    hess_filename
        Path to the Hessian file.
    ncart
        Number of Cartesian coordinates.
    Returns
    -------
    numpy.ndarray
        Symmetric Hessian matrix with shape ``(ncart, ncart)``.
    Raises
    ------
    FileNotFoundError
        If the Hessian file does not exist.
    ValueError
        If the file does not contain enough matrix elements.
    """
    p = Path(hess_filename)
    if not p.exists():
        raise FileNotFoundError(f"Hessian file not found: {p}")
    values = []
    with p.open("r") as handle:
        _ = handle.readline()
        _ = handle.readline()
        for line in handle:
            for token in line.replace(",", " ").split():
                try:
                    values.append(_to_float(token))
                except Exception:
                    pass
    expected = ncart * (ncart + 1) // 2
    if len(values) < expected:
        raise ValueError(
            f"Not enough Hessian elements. "
            f"Expected {expected}, got {len(values)}."
        )
    values = values[:expected]
    hessian = np.zeros((ncart, ncart), dtype=float)
    k = 0
    for i in range(ncart):
        for j in range(i + 1):
            hessian[i, j] = values[k]
            hessian[j, i] = values[k]
            k += 1
    return hessian
def mass_weight_hessian(hessian: np.ndarray, xm: np.ndarray) -> np.ndarray:
    """Apply mass-weighting to a Cartesian Hessian.
    Parameters
    ----------
    hessian
        Cartesian Hessian matrix.
    xm
        Cartesian mass vector repeated three times per atom.
    Returns
    -------
    numpy.ndarray
        Mass-weighted Hessian.
    """
    m = np.asarray(xm, dtype=float)
    denom = np.sqrt(np.outer(m, m))
    return hessian / denom
def diagonalize_hessian(hessian: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Diagonalize a symmetric Hessian matrix.
    Parameters
    ----------
    hessian
        Symmetric Hessian matrix.
    Returns
    -------
    numpy.ndarray
        Eigenvalues in ascending order.
    numpy.ndarray
        Eigenvectors stored column-wise.
    """
    evals, evecs = np.linalg.eigh(hessian)
    return evals, evecs
def reorder_modes_rottrans_at_end(
    evals: np.ndarray,
    evecs: np.ndarray,
    nvib: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Move vibrational modes to the front and rotational/translational modes to the end.
    Parameters
    ----------
    evals
        Eigenvalues of the Hessian.
    evecs
        Eigenvectors stored column-wise.
    nvib
        Number of vibrational modes.
    Returns
    -------
    numpy.ndarray
        Reordered eigenvalues.
    numpy.ndarray
        Reordered eigenvectors with columns permuted accordingly.
    """
    ncart = evals.shape[0]
    idx_vib = np.arange(ncart - nvib, ncart)
    idx_rt = np.arange(0, ncart - nvib)
    idx = np.concatenate([idx_vib, idx_rt])
    return evals[idx], evecs[:, idx]
def read_trajectory_extended_xyz(traj_path: str | Path, nat: int) -> Tuple[List[str], np.ndarray, np.ndarray]:
    """Read an extended XYZ trajectory with coordinates and velocities.
    The expected format is the same as the Fortran driver:
    two header lines followed by ``nat`` atom lines per frame, where each atom
    line contains ``symbol x y z vx vy vz``.
    Parameters
    ----------
    traj_path
        Path to the trajectory file.
    nat
        Number of atoms.
    Returns
    -------
    list[str]
        Atomic symbols for the first frame.
    numpy.ndarray
        Cartesian coordinates with shape ``(nstep, 3 * nat)``.
    numpy.ndarray
        Cartesian velocities with shape ``(nstep, 3 * nat)``.
    """
    p = Path(traj_path)
    if not p.exists():
        raise FileNotFoundError(f"Trajectory file not found: {p}")
    frames_x = []
    frames_v = []
    symbols_ref: List[str] | None = None
    with p.open('r') as f:
        while True:
            line1 = f.readline()
            if not line1:
                break
            line2 = f.readline()
            if not line2:
                break
            try:
                nat_file = int(line1.split()[0])
            except Exception as exc:
                raise ValueError(f"Could not read atom count from trajectory frame in {p}") from exc
            if nat_file != nat:
                raise ValueError(f"Trajectory frame atom count {nat_file} does not match nat={nat}")
            x_step = np.zeros(3 * nat, dtype=float)
            v_step = np.zeros(3 * nat, dtype=float)
            symbols_step: List[str] = []
            for i in range(nat):
                parts = f.readline().split()
                if len(parts) < 7:
                    raise ValueError(
                        f"Malformed trajectory atom line in {p}: expected symbol x y z vx vy vz"
                    )
                symbols_step.append(parts[0])
                x_step[3 * i : 3 * i + 3] = [_to_float(parts[1]), _to_float(parts[2]), _to_float(parts[3])]
                v_step[3 * i : 3 * i + 3] = [_to_float(parts[4]), _to_float(parts[5]), _to_float(parts[6])]
            if symbols_ref is None:
                symbols_ref = symbols_step
            frames_x.append(x_step)
            frames_v.append(v_step)
    if symbols_ref is None:
        raise ValueError(f"No trajectory frames found in {p}")
    return symbols_ref, np.asarray(frames_x, dtype=float), np.asarray(frames_v, dtype=float)
def write_db(
    nvib: int,
    ncart: int,
    ndb: int,
    nmax: int,
    q: np.ndarray,
    hessian: np.ndarray,
    dbq: np.ndarray,
    cnorm: np.ndarray,
    arcv: np.ndarray,
) -> Tuple[int, np.ndarray, np.ndarray]:
    """Store a record in the database and update the archive ordering.
    The Cartesian vector ``q`` is projected into normal-mode
    space using ``cnorm`` and the first ``nvib`` coordinates are stored in
    ``dbq``. The archive vector ``arcv`` keeps the record indices sorted by
    the first normal coordinate.
    Parameters
    ----------
    nvib
        Number of vibrational modes.
    ncart
        Number of Cartesian coordinates.
    ndb
        Current number of database records.
    nmax
        Maximum number of database records.
    q
        Cartesian coordinate vector with shape ``(ncart,)``.
    hessian
        Cartesian Hessian matrix. It is accepted for API compatibility with
        the Fortran routine.
    dbq
        Database of normal coordinates with shape ``(nmax, nvib)``.
    cnorm
        Mass-weighted eigenvector matrix with shape ``(ncart, ncart)``.
    arcv
        Archive vector containing indices sorted by the first normal coordinate.
    Returns
    -------
    tuple[int, numpy.ndarray, numpy.ndarray]
        Updated ``ndb``, ``dbq`` and ``arcv``.
    """
    _ = hessian
    q = np.asarray(q, dtype=float).reshape(ncart)
    dbq = np.asarray(dbq, dtype=float)
    cnorm = np.asarray(cnorm, dtype=float)
    arcv = np.asarray(arcv, dtype=int)
    if dbq.shape[0] < nmax or dbq.shape[1] < nvib:
        raise ValueError(f"dbq must have shape at least ({nmax}, {nvib})")
    if cnorm.shape != (ncart, ncart):
        raise ValueError(f"cnorm must have shape ({ncart}, {ncart})")
    if arcv.shape[0] < nmax:
        raise ValueError(f"arcv must have length at least {nmax}")
    if ndb >= nmax:
        raise IndexError("database is full")
    qzn = cnorm.T @ q
    q_arcv = qzn[:nvib]
    dbq[ndb, :nvib] = q_arcv
    if ndb == 0:
        arcv[0] = 0
    elif q_arcv[0] > dbq[arcv[ndb - 1], 0]:
        arcv[ndb] = ndb
    else:
        for i in range(ndb):
            if q_arcv[0] <= dbq[arcv[i], 0]:
                arcv[i + 1 : ndb + 1] = arcv[i:ndb]
                arcv[i] = ndb
                break
        else:
            arcv[ndb] = ndb
    return ndb + 1, dbq, arcv
def projresearch(
    nvib: int,
    ncart: int,
    ndb: int,
    nmax: int,
    thr: float,
    dbq: np.ndarray,
    qzn: np.ndarray,
    arcv: np.ndarray,
    cnorm: np.ndarray,
) -> Tuple[int, int, np.ndarray]:
    """Search the database for a geometry close to the current point.
    Parameters
    ----------
    nvib
        Number of vibrational modes.
    ncart
        Number of Cartesian coordinates.
    ndb
        Number of stored database records.
    nmax
        Maximum number of database records.
    thr
        Threshold used to filter candidates.
    dbq
        Database of normal coordinates with shape ``(nmax, nvib)``.
    qzn
        Cartesian coordinate vector with shape ``(ncart,)``.
    arcv
        Archive indices sorted by the first normal coordinate.
    cnorm
        Mass-weighted eigenvector matrix with shape ``(ncart, ncart)``.
    Returns
    -------
    tuple[int, int, numpy.ndarray]
        ``hitcnt``, ``minhit``, and the surviving hit indices.
    """
    qzn = np.asarray(qzn, dtype=float).reshape(ncart)
    dbq = np.asarray(dbq, dtype=float)
    arcv = np.asarray(arcv, dtype=int)
    cnorm = np.asarray(cnorm, dtype=float)
    if ndb <= 0:
        return 0, -1, np.empty(0, dtype=int)
    q = cnorm.T @ qzn
    qtmp = q[:nvib]
    hit = np.full(nmax, -1, dtype=int)
    hitcnt = 0
    for i in range(ndb):
        idx = int(arcv[i])
        dq = abs(dbq[idx, 0] - qtmp[0])
        if dbq[idx, 0] > qtmp[0] and dq > thr:
            break
        if dq < thr:
            hit[hitcnt] = idx
            hitcnt += 1
    for k in range(1, nvib):
        cnt = 0
        for i in range(hitcnt):
            idx = int(hit[i])
            if idx < 0:
                continue
            dq = abs(dbq[idx, k] - qtmp[k])
            if dq < thr:
                hit[cnt] = idx
                cnt += 1
        hitcnt = cnt
    minimum = np.sqrt(float(nvib)) * thr
    minhit = -1
    for i in range(hitcnt):
        idx = int(hit[i])
        if idx < 0:
            continue
        dist = np.linalg.norm(dbq[idx, :nvib] - q[:nvib])
        if dist < minimum:
            minimum = dist
            minhit = idx
    return hitcnt, minhit, hit[:hitcnt]
def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser.
    Returns
    -------
    argparse.ArgumentParser
        Parser configured with the required workflow arguments.
    """
    parser = argparse.ArgumentParser(
        description="Read the trajectory-analysis inputs from command-line options."
    )
    parser.add_argument("--nat", type=int, required=True, help="Number of atoms.")
    parser.add_argument(
        "--nmax",
        type=int,
        required=True,
        help="Total number of steps in the trajectory.",
    )
    parser.add_argument(
        "--thr",
        type=float,
        default=None,
        help="Distance threshold value.",
    )
    parser.add_argument(
        "--input_traj",
        type=str,
        required=True,
        help="Name of the input trajectory file in .xyz format.",
    )
    parser.add_argument(
        "--input_hess",
        type=str,
        required=True,
        help="Name of the equilibrium Hessian file in standard format.",
    )
    parser.add_argument(
        "--output_geom",
        type=str,
        default=None,
        help="Name of the output file containing the final geometries.",
    )
    parser.add_argument(
        "--output_ind",
        type=str,
        default=None,
        help="Name of the output file containing the search indexes.",
    )
    parser.add_argument(
        "--xyz",
        type=str,
        required=True,
        help="Equilibrium XYZ file used to read the first geometry and masses.",
    )
    parser.add_argument(
        "--scan-thr",
        action="store_true",
        help="Run the database scan over the built-in threshold list.",
    )
    parser.add_argument(
        "--scan-summary",
        default="graph_eps",
        help="Summary file written in scan mode (threshold and number of geometries).",
    )
    parser.add_argument(
        "--nrotransl",
        type=int,
        default="6",
        help="Number or roto-translational modes: 5 for linear molecules, for all there rest is 6.",
    )
    return parser

def run_once(
    args: argparse.Namespace,
    thr: float,
    output_geom: str,
    output_ind: str,
    *,
    debug_label: str | None = None,
) -> int:
    """Run one Hessian-database search for a single threshold.

    Parameters
    ----------
    args
        Parsed command-line arguments.
    thr
        Threshold value used in ``projresearch``.
    output_geom
        Geometry output file for this run.
    output_ind
        Index output file for this run.
    debug_label
        Optional text label printed at the start of the run.

    Returns
    -------
    int
        Number of geometries written to ``output_geom``.
    """
    nat: int = args.nat
    ncart: int = 3 * nat
    nvib: int = ncart - args.nrototrasl 
    nmax: int = args.nmax

    if debug_label is None:
        debug_label = f"thr={thr}"

    print(f"\n=== Running HDB for {debug_label} ===")
    print(f"nat         = {nat}")
    print(f"ncart       = {ncart}")
    print(f"nvib        = {nvib}")
    print(f"nmax        = {nmax}")
    print(f"thr         = {thr}")
    print(f"input_traj  = {args.input_traj}")
    print(f"input_hess  = {args.input_hess}")
    print(f"output_geom = {output_geom}")
    print(f"output_ind  = {output_ind}")
    print()

    # Equilibrium geometry only builds the mass vector.
    symbols, geom, masses, xm = read_first_geometry_and_masses(args.xyz, nat)
    print_geometry_and_masses(symbols, geom, masses)

    hessian = read_hessian_nwchem_lower_triangle(args.input_hess, ncart)
    hessian_mw = mass_weight_hessian(hessian, xm)

    evals, evecs = diagonalize_hessian(hessian_mw)
    evals, cnorm = reorder_modes_rottrans_at_end(evals, evecs, nvib)

    frequencies_cm1 = np.sqrt(np.abs(evals)) * 219474.63
    print("Frequencies (cm^-1):")
    for i, freq in enumerate(frequencies_cm1, start=1):
        label = "VIB" if i <= nvib else "ROT/TRANS"
        print(f"  mode {i:3d} [{label:^9s}] : {freq:12.4f}")
    print()

    symb_traj, xtraj, vtraj = read_trajectory_extended_xyz(args.input_traj, nat)
    if symb_traj != symbols:
        print("Warning: trajectory symbols differ from equilibrium XYZ symbols")

    if xtraj.shape[0] < nmax:
        raise ValueError(f"Trajectory contains {xtraj.shape[0]} frames, but --nmax={nmax}")

    dbq = np.zeros((nmax, nvib), dtype=float)
    arcv = np.zeros(nmax, dtype=int)
    hess_db = np.zeros((nmax, ncart, ncart), dtype=float)

    ndb = 0

    # First record from the first trajectory frame.
    xz = xtraj[0, :].copy()
    ndb, dbq, arcv = write_db(nvib, ncart, ndb, nmax, xz, hessian_mw, dbq, cnorm, arcv)
    hess_db[0, :, :] = hessian

    geom_count = 0

    with open(output_geom, "w") as fgeom, open(output_ind, "w") as find:
        fgeom.write(f"{nat}\n")
        fgeom.write("HDB is the best\n")
        for i, sym in enumerate(symbols):
            fgeom.write(
                f"{sym:2s}   {xz[3*i:3*i+3][0]:16.8f} {xz[3*i:3*i+3][1]:16.8f} {xz[3*i:3*i+3][2]:16.8f}\n"
            )
            fgeom.flush()
        find.write("1\n")
        geom_count += 1

        # Cycle over all dynamics steps.
        for nrec in range(1, min(nmax, xtraj.shape[0])):
            qread = xtraj[nrec, :].copy()
            _vread = vtraj[nrec, :].copy()
            xz = qread

            hitcnt, minhit, _ = projresearch(
                nvib, ncart, ndb, nmax, thr, dbq, xz, arcv, cnorm
            )

            if hitcnt != 0:
                find.write(f"{minhit + 1}\n")
            else:
                ndb, dbq, arcv = write_db(
                    nvib, ncart, ndb, nmax, xz, hessian_mw, dbq, cnorm, arcv
                )
                hess_db[ndb - 1, :, :] = hessian

                fgeom.write(f"{nat}\n")
                fgeom.write("HDB is the best\n")
                for i, sym in enumerate(symbols):
                    fgeom.write(
                        f"{sym:2s}   {xz[3*i:3*i+3][0]:16.8f} {xz[3*i:3*i+3][1]:16.8f} {xz[3*i:3*i+3][2]:16.8f}\n"
                    )
                    fgeom.flush()
                find.write(f"{ndb}\n")
                geom_count += 1

    print(f"ndb = {ndb}")
    print(f"Geometries written: {geom_count}")
    return geom_count


def main() -> None:
    """Program entry point."""
    parser = build_parser()
    args = parser.parse_args()
    if not args.scan_thr: 
        if args.thr is None:
            parser.error("--thr is required unless --scan-thr is used")

        if args.output_geom is None:
            parser.error("--output_geom is required unless --scan-thr is used")

        if args.output_ind is None:
            parser.error("--output_ind is required unless --scan-thr is used")

    if args.scan_thr:
        summary_path = Path(args.scan_summary)
        summary_path.write_text("")
        for token in SCAN_THR_VALUES:
            thr = _to_float(token)
            output_geom = f"geom_{token}.dat"
            output_ind = f"index_{token}.dat"
            geom_count = run_once(
                args,
                thr,
                output_geom,
                output_ind,
                debug_label=token,
            )
            with summary_path.open("a") as fh:
                fh.write(f"{token}\t{geom_count}\n")
        print(f"\nScan summary written to {summary_path}")
    else:
        run_once(args, args.thr, args.output_geom, args.output_ind, debug_label=None)


if __name__ == "__main__":
    main()
