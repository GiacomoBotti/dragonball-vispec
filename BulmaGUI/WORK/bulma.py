#!/usr/bin/env python3
from __future__ import annotations
import re
import argparse
import sys
from pathlib import Path

#SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#Authors: Giacomo Mandelli, Giacomo Botti

FLOAT_RE = r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DE][+-]?\d+)?)"
START_MARKER = "Force constants in Cartesian coordinates"
END_MARKER   = "Final forces over variables"
BOHR_TO_ANG = 0.52917721067
SEC_PER_AUTIME = 2.4188843265857e-17
AU_TIME_TO_FS = 0.02418884326505
AUVEL_TO_ANGFS = BOHR_TO_ANG / AU_TIME_TO_FS  # ~21.877

# BULMA = Batch Utilities for Log parsing, hessian Matrix & Automation
# ----------------------------
# Hessian extraction utilities
# ----------------------------
def extract_hessian_chunk(text_lines: list[str]) -> list[str]:
    start = None
    end = None
    for i, line in enumerate(text_lines):
        if start is None and START_MARKER in line:
            start = i
            continue
        if start is not None and END_MARKER in line:
            end = i
            break
    if start is None:
        raise RuntimeError(f"Could not find start marker: {START_MARKER!r}")
    if end is None:
        raise RuntimeError(f"Could not find end marker: {END_MARKER!r}")
    return text_lines[start + 1 : end]


def to_D_exp(s: str) -> str:
    # Convert scientific notation to Fortran D exponent
    return s.replace("E", "D").replace("e", "D")


def parse_lower_triangular_rows(chunk_lines: list[str]) -> dict[int, list[str]]:
    """
    Collect numeric Hessian rows (lower-triangular) (GAUSSIAN16).
    Keeps tokens as strings; normalizes any 'D/d' to 'E' internally for consistency.
    """
    rows: dict[int, list[str]] = {}
    max_row = 0

    for raw in chunk_lines:
        if "." not in raw:   # mimic grep '[.]'
            continue
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

        vals = toks[1:]
        vals = [v.replace("D", "E").replace("d", "E") for v in vals]

        rows.setdefault(r, []).extend(vals)
        max_row = max(max_row, r)

    if max_row == 0:
        raise RuntimeError("No Hessian numeric rows detected.")

    # sanity: lower-triangular => row r has exactly r values
    bad = [(r, len(rows.get(r, []))) for r in range(1, max_row + 1) if len(rows.get(r, [])) != r]
    if bad:
        ex = ", ".join([f"row {r} has {k} values" for r, k in bad[:8]])
        raise RuntimeError(
            "Parsed Hessian rows do not match expected lower-triangular shape "
            f"(expected row r to have r values). Examples: {ex}."
        )

    return rows


def write_hessian_out(rows: dict[int, list[str]], path: Path) -> None:
    nrow = max(rows.keys())
    with path.open("w", newline="\n") as f:
        for r in range(1, nrow + 1):
            vals = [to_D_exp(v) for v in rows[r]]
            line = "".join(f"{v:>15}   " for v in vals).rstrip()
            f.write(line + "\n")


def write_hess_vec(rows: dict[int, list[str]], path: Path) -> None:
    nrow = max(rows.keys())
    with path.open("w", newline="\n") as f:
        f.write("\n\n")  # two blank lines
        for r in range(1, nrow + 1):
            for v in rows[r]:
                f.write(to_D_exp(v) + "\n")

# ----------------------------
# Hessian extraction utilities for Q-Chem (HESS file)
# ----------------------------
QCHEM_HESS_START = "$hessian"
QCHEM_HESS_END   = "$end"
_QCHEM_DIM_RE = re.compile(r"^\s*Dimension\s+(\d+)\s*$", re.IGNORECASE)

def extract_qchem_hessian_lower_triangle_rows(text_lines: list[str]) -> dict[int, list[str]]:
    """
    Parse Q-Chem HESS file lower-triangular Hessian:

      $hessian
      Dimension   N
      <lower-triangle numbers, free-form whitespace>
      $end

    Returns rows dict in Bulma format: rows[1] has 1 value, rows[2] has 2 values, ...
    Values are kept as strings normalized to 'E' internally (Bulma writes 'D' on output).
    """
    start = None
    end = None
    for i, ln in enumerate(text_lines):
        s = ln.strip().lower()
        if start is None and s == QCHEM_HESS_START:
            start = i
            continue
        if start is not None and s == QCHEM_HESS_END:
            end = i
            break
    if start is None:
        raise RuntimeError(f"Could not find Q-Chem start marker: {QCHEM_HESS_START!r}")
    if end is None:
        raise RuntimeError(f"Could not find Q-Chem end marker: {QCHEM_HESS_END!r}")

    # Find 'Dimension N' line
    dim = None
    dim_i = None
    for j in range(start + 1, min(end, start + 20)):
        m = _QCHEM_DIM_RE.match(text_lines[j])
        if m:
            dim = int(m.group(1))
            dim_i = j
            break
    if dim is None or dim_i is None:
        raise RuntimeError("Could not find 'Dimension N' line after $hessian in Q-Chem HESS.")

    tokens: list[str] = []
    for ln in text_lines[dim_i + 1 : end]:
        if not ln.strip():
            continue
        for part in ln.split():
            try:
                float(part.replace("D", "E").replace("d", "E"))
            except ValueError:
                continue
            tokens.append(part.replace("D", "E").replace("d", "E"))

    expected = dim * (dim + 1) // 2
    if len(tokens) != expected:
        raise RuntimeError(
            f"Q-Chem Hessian size mismatch: parsed {len(tokens)} numbers, expected {expected} "
            f"for Dimension {dim} (lower triangle)."
        )

    rows: dict[int, list[str]] = {}
    k = 0
    for r in range(1, dim + 1):
        rows[r] = tokens[k : k + r]
        k += r
    return rows


# ----------------------------
# Hessian extraction utilities for ORCA
# ----------------------------

ORCA_HESS_START = "$hessian"
ORCA_HESS_END   = "$vibrational_frequencies"

def extract_orca_hessian_chunk(text_lines: list[str]) -> list[str]:
    """
    Extract the ORCA hessian block
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

    chunk = text_lines[start:end+1]
    if len(chunk) < 5:
        raise RuntimeError("ORCA Hessian chunk too short.")

    # drop first 2 lines ($hessian + dimension) and last 2 lines (end marker + dimension)
    return chunk[2:-2]


def parse_orca_full_matrix(chunk_lines: list[str]) -> list[list[str]]:
    """
    Parse ORCA full Hessian matrix (symmetric) printed in column blocks.
    We rebuild full rows by concatenating values across blocks.
    Returns full[ncart][ncart] as strings.
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
        # ORCA numeric rows start with integer index (often 0-based)
        try:
            r = int(toks[0])
        except ValueError:
            continue
        # require at least one float-like token (avoid header lines)
        if not any("." in t or "E" in t or "D" in t or "e" in t or "d" in t for t in toks[1:]):
            continue

        vals = [v.replace("D", "E").replace("d", "E") for v in toks[1:]]
        rows.setdefault(r, []).extend(vals)
        max_row = max(max_row, r)

    if max_row < 0:
        raise RuntimeError("No ORCA Hessian numeric rows detected.")

    ncart = max_row + 1
    full = []
    for r in range(ncart):
        if r not in rows:
            raise RuntimeError(f"Missing ORCA Hessian row {r}.")
        if len(rows[r]) != ncart:
            raise RuntimeError(
                f"ORCA Hessian row {r} has {len(rows[r])} values; expected {ncart} "
                "(chunk may be incomplete)."
            )
        full.append(rows[r])
    return full


def orca_full_to_lower_triangle_rows(full: list[list[str]]) -> dict[int, list[str]]:
    """
    Convert full matrix (0-based) to Bulma's lower-triangle:
      rows[1] has 1 value, rows[2] has 2 values, ...
    """
    ncart = len(full)
    out: dict[int, list[str]] = {}
    for i in range(ncart):
        out[i + 1] = [full[i][j] for j in range(i + 1)]
    return out



# ----------------------------
# Gaussian .com generation
# ----------------------------
def read_xyz(xyz_path: Path) -> tuple[str, list[tuple[str, float, float, float]]]:
    """
    Read a standard XYZ file:
      line1: natoms
      line2: comment/title
      remaining: Elem x y z
    Returns (title, atoms).
    """
    lines = xyz_path.read_text(errors="replace").splitlines()
    if len(lines) < 3:
        raise RuntimeError(f"XYZ file too short: {xyz_path}")

    # title: use comment line if present/non-empty; else file stem
    comment = lines[1].strip()
    title = comment if comment else xyz_path.stem

    atoms: list[tuple[str, float, float, float]] = []
    for ln in lines[2:]:
        if not ln.strip():
            continue
        parts = ln.split()
        if len(parts) < 4:
            continue
        sym = parts[0]
        try:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        except ValueError:
            raise RuntimeError(f"Bad XYZ coordinate line: {ln!r}")
        atoms.append((sym, x, y, z))

    if not atoms:
        raise RuntimeError(f"No atoms parsed from XYZ: {xyz_path}")

    return title, atoms

def read_velocity_xyz_noatoms(vel_path: Path) -> list[tuple[str, str, str]]:
    """
    Read velocity_gau.xyz-like file:
      line1: natoms
      line2: comment
      then:  Sym   vx   vy   vz
    """
    lines = vel_path.read_text(errors="replace").splitlines()
    if len(lines) < 3:
        raise RuntimeError(f"Velocity file too short: {vel_path}")

    try:
        nat = int(lines[0].split()[0])
    except Exception:
        nat = None

    vels: list[tuple[str, str, str]] = []
    for ln in lines[2:]:
        if not ln.strip():
            continue
        parts = ln.split()
        if len(parts) < 4:
            continue
        # take last 3 tokens (vx vy vz), ignore atom label
        vx, vy, vz = parts[-3], parts[-2], parts[-1]
        vels.append((vx, vy, vz))

    if not vels:
        raise RuntimeError(f"No velocities parsed from: {vel_path}")

    if nat is not None and nat != len(vels):
        raise RuntimeError(
            f"Velocity count mismatch: header says {nat}, parsed {len(vels)} lines in {vel_path}"
        )

    return vels

def fmtD(x: float, sig: int = 14) -> str:
    return f"{x:.{sig}E}".replace("E", "D")

def _f2float(s: str) -> float:
    return float(s.replace("D", "E").replace("d", "E"))

def read_xyz_symbols(xyz_path: Path) -> list[str]:
    lines = xyz_path.read_text(errors="replace").splitlines()
    if len(lines) < 3:
        raise RuntimeError(f"XYZ file too short: {xyz_path}")
    nat = int(lines[0].split()[0])
    symb = []
    for i in range(nat):
        parts = lines[2 + i].split()
        if not parts:
            raise RuntimeError(f"Bad XYZ line {2+i+1} in {xyz_path}")
        symb.append(parts[0])
    return symb

def get_masses_cart(symb: list[str]):
    import numpy as np
    mass = {"H": 1.008, "C": 12.01, "O": 16.00, "N": 14.01, "S": 32.06}
    xm = np.zeros(3 * len(symb), dtype=float)
    for i, s in enumerate(symb):
        if s not in mass:
            raise RuntimeError(f"Atom {s} not in mass database (add it in get_masses_cart).")
        xm[3*i:3*i+3] = mass[s]
    return xm


def split_bomd_blocks(lines: list[str]) -> list[tuple[int, int, int]]:
    """
    Split MD steps in blocks. Supports both:
      - 'Summary information for step   N'
      - 'Trajectory Number  1 Step Number  N'
    """
    #import re

    pat1 = re.compile(r"Summary information for step\s+(\d+)")
    pat2 = re.compile(r"Trajectory Number\s*1\s*Step Number\s*(\d+)")

    hits1 = []
    hits2 = []
    for i, ln in enumerate(lines):
        m1 = pat1.search(ln)
        if m1:
            hits1.append((int(m1.group(1)), i))
        m2 = pat2.search(ln)
        if m2:
            hits2.append((int(m2.group(1)), i))

    hits = hits1 if len(hits1) >= len(hits2) else hits2
    if not hits:
        raise RuntimeError("No MD step markers found (neither 'Summary information...' nor 'Trajectory Number...').")

    blocks = []
    for k, (step, i0) in enumerate(hits):
        i1 = hits[k+1][1] if k+1 < len(hits) else len(lines)
        blocks.append((step, i0, i1))
    return blocks


def parse_xyzv_from_tables(seg_lines: list[str], nat: int, vel_fallback=None):
    """
    Parse positions from 'Cartesian coordinates: (bohr)' table
    and velocities from 'MW cartesian velocity: (sqrt(amu)*bohr/sec)' table.
    Returns (xflat, vflat) as lists of floats length 3*nat.
    """
    #import re

    num = FLOAT_RE
    row_pat = re.compile(
        rf"I=\s*\d+\s+X=\s*{num}\s+Y=\s*{num}\s+Z=\s*{num}"
    )

    def grab_table(after_key: str) -> list[tuple[float, float, float]] | None:
        try:
            i0 = next(i for i, ln in enumerate(seg_lines) if after_key in ln)
        except StopIteration:
            return None

        triples = []
        for ln in seg_lines[i0+1:]:
            m = row_pat.search(ln)
            if m:
                triples.append((_f2float(m.group(1)), _f2float(m.group(2)), _f2float(m.group(3))))
                if len(triples) == nat:
                    break
        if len(triples) != nat:
            raise RuntimeError(f"Found '{after_key}' but parsed {len(triples)}/{nat} rows.")
        return triples

    coords = grab_table("Cartesian coordinates:")
    if coords is None:
        raise RuntimeError("No 'Cartesian coordinates:' table found in step segment.")

    vels = grab_table("MW cartesian velocity:")
    if vels is None:
        if vel_fallback is None:
            raise RuntimeError("No 'MW cartesian velocity:' table found and no --vel fallback provided.")
        # fallback velocities from file (strings -> float)
        if len(vel_fallback) != nat:
            raise RuntimeError("Velocity fallback size mismatch.")
        vels = [(_f2float(vx), _f2float(vy), _f2float(vz)) for (vx, vy, vz) in vel_fallback]

    xflat = [c for (x, y, z) in coords for c in (x, y, z)]
    vflat = [c for (x, y, z) in vels   for c in (x, y, z)]
    return xflat, vflat

def get_energies_line(seg_text: str):
    """
    EKin = ...; EPot = ...; ETot = ...
    """
    m = re.search(
        rf"\bEKin\b\s*=\s*{FLOAT_RE}\s*;\s*"
        rf"\bEPot\b\s*=\s*{FLOAT_RE}\s*;\s*"
        rf"\bETot\b\s*=\s*{FLOAT_RE}",
        seg_text
    )
    if not m:
        raise RuntimeError("Could not find 'EKin ...; EPot ...; ETot ...' line in segment")
    ekin = _f2float(m.group(1))
    epot = _f2float(m.group(2))
    etot = _f2float(m.group(3))
    return ekin, epot, etot

def write_gaussian_com(
    out_path: Path,
    *,
    atoms: list[tuple[str, float, float, float]],
    title: str,
    theory: str,
    basis: str,
    nproc: int,
    mem: str,
    mode: str,            # "opt" or "freq"
    convergence: str,     # used only for opt
    charge: int = 0,
    mult: int = 1,
) -> None:
    if mode == "opt":
        route = (
            f"# {theory}/{basis} EmpiricalDispersion=GD3BJ "
            f"Opt=(CalcAll,MaxCycles=200,{convergence}) "
            f"int=ultrafine SCF(XQC,Tight)"
        )
    elif mode == "freq":
        route = (
            f"# {theory}/{basis} EmpiricalDispersion=GD3BJ "
            f"Freq Iop(7/33=1) int=ultrafine SCF(XQC,Tight) nosymm"
        )
    else:
        raise ValueError(f"Unknown mode: {mode!r}")

    with out_path.open("w", newline="\n") as f:
        f.write(f"%mem={mem}\n")
        f.write(f"%NProcShared={nproc}\n")
        f.write(route + "\n\n")
        f.write(title + "\n\n")
        f.write(f"{charge} {mult}\n")
        for sym, x, y, z in atoms:
            f.write(f"{sym:<2s} {x:>12.6f} {y:>12.6f} {z:>12.6f}\n")
        f.write("\n")  # Gaussian expects a trailing blank line
########################
#INP generation for ORCA
########################

def _mem_to_mb_per_core(mem: str, nproc: int) -> int:
    """
    Convert strings like '300Gb', '64GB', '8000Mb' into ORCA %maxcore (MB/core).
    If parsing fails, raise.
    """
    s = mem.strip()
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([gGmMkK][bB])\s*$", s)
    if not m:
        raise RuntimeError(f"Unrecognized --mem format for ORCA: {mem!r} (use e.g. 300Gb, 64000Mb)")
    val = float(m.group(1))
    unit = m.group(2).lower()  # gb, mb, kb
    if unit == "gb":
        total_mb = val * 1024.0
    elif unit == "mb":
        total_mb = val
    elif unit == "kb":
        total_mb = val / 1024.0
    else:
        raise RuntimeError(f"Unrecognized mem unit: {unit!r}")
    mb_per_core = int(total_mb / max(1, nproc))
    return max(1, mb_per_core)


def _orca_opt_keyword_from_convergence(conv: str) -> str:
    """
    Map Bulma's --convergence into an ORCA Opt keyword.
    Default Gaussian conv is 'VeryTight' ORCA uses VERYTIGHTOPT.
    """
    c = conv.strip().lower()
    if c == "verytight":
        return "VERYTIGHTOPT"
    if c == "tight":
        return "TIGHTOPT"
    if c == "normal":
        return "OPT"
    return conv


def write_orca_inp(
    out_path: Path,
    *,
    atoms: list[tuple[str, float, float, float]],
    title: str,
    theory: str,
    basis: str,
    nproc: int,
    mem: str | None,
    mode: str,        # "opt" or "freq"
    convergence: str,
    charge: int = 0,
    mult: int = 1,
) -> None:
    """
    ORCA .inp writer using defaults:
    - keywords include: VERYTIGHTOPT, (optional FREQ), THEORY, D4, BS, VeryTightSCF
    - %PAL NPROCS ...
    - %SCF MAXITER 500 / %geom MAXITER 500
    - * xyz charge mult ... *
    """
    optkw = _orca_opt_keyword_from_convergence(convergence)
    kws = [optkw]
    if mode == "freq":
        kws.append("FREQ")
    kws += [theory, "D4", basis, "VeryTightSCF"]

    with out_path.open("w", newline="\n") as f:
        f.write("! " + " ".join(kws) + "\n\n")
        f.write(f"%PAL NPROCS {nproc} END\n")
        if mem is not None:
            maxcore = _mem_to_mb_per_core(mem, nproc)
            f.write(f"%maxcore {maxcore}\n")
        f.write("\n")
        f.write("%SCF\nMAXITER 500\nEND\n\n")
        f.write("%geom\nMAXITER 500\nend\n\n")
        f.write(f"* xyz {charge} {mult}\n")
        for sym, x, y, z in atoms:
            f.write(f" {sym:<2s}  {x: .12f}  {y: .12f}  {z: .12f}\n")
        f.write("*\n")


def _qchem_basis_name(bs: str) -> str:
    # Your Gaussian default is "Def2TZVP", Q-Chem typically wants "def2-TZVP"
    if bs.strip().lower().replace("-", "") == "def2tzvp":
        return "def2-TZVP"
    return bs

def write_qchem_single_inp(
    out_path: Path,
    *,
    atoms: list[tuple[str, float, float, float]],
    method: str,
    basis: str,
    charge: int = 0,
    mult: int = 1,
    mode: str,  # "opt" or "freq"
) -> None:
    """
    Write a *single-job* Q-Chem input:
      - opt.inp  : JOBTYPE = OPT  (MEM_TOTAL=20000)
      - freq.inp : JOBTYPE = FREQ (MEM_TOTAL=40000)
    Geometry is written explicitly (no 'read').
    """
    basis_qc = _qchem_basis_name(basis)

    if mode not in ("opt", "freq"):
        raise ValueError(f"write_qchem_single_inp: unknown mode {mode!r}")

    mem_total = 20000 if mode == "opt" else 40000

    with out_path.open("w", newline="\n") as f:
        # --- molecule ---
        f.write("$molecule\n")
        f.write(f"{charge} {mult}\n")
        for sym, x, y, z in atoms:
            f.write(f"{sym:<2s} {x: .16f} {y: .16f} {z: .16f}\n")
        f.write("$end\n\n")

        # --- rem  ---
        f.write("$rem\n")
        f.write(f"JOBTYPE = {'OPT' if mode == 'opt' else 'FREQ'}\n")
        f.write(f"METHOD = {method}\n")
        f.write(f"BASIS = {basis_qc}\n")
        f.write("DFT_D = D4\n")
        f.write("SCF_CONVERGENCE = 8\n")
        f.write("GEOM_OPT_MAX_CYCLES = 400\n")
        f.write("GEOM_OPT_COORDS = -1\n")
        f.write("GEOM_OPT_TOL_DISPLACEMENT = 1\n")
        f.write("GEOM_OPT_TOL_GRADIENT = 1\n")
        f.write("GEOM_OPT_TOL_ENERGY = 1\n")
        f.write("MEM_STATIC = 5000\n")
        f.write(f"MEM_TOTAL = {mem_total}\n")
        f.write("SYM_IGNORE = TRUE\n")
        f.write("XC_GRID = 3\n")
        f.write("$end\n")

def write_qchem_inp(
    out_path: Path,
    *,
    atoms: list[tuple[str, float, float, float]],
    method: str,
    basis: str,
    charge: int = 0,
    mult: int = 1,
    mode: str,  # "opt" or "opt-freq"
) -> None:
    """
    Write Q-Chem multi-job input
      - opt.inp:   FREQ  + OPT(read hess/guess)
      - opt-freq:  FREQ  + OPT(read hess/guess) + FREQ(read guess, vibman)
    """
    basis_qc = _qchem_basis_name(basis)

    def write_job_freq(f, *, scf_guess_read: bool, vibman_print: bool):
        f.write("$molecule\n")
        if scf_guess_read:
            f.write("read\n")
        else:
            f.write(f"   {charge}  {mult}\n")
            for sym, x, y, z in atoms:
                f.write(f"   {sym:<2s} {x: .6f} {y: .6f} {z: .6f}\n")
        f.write("$end\n\n")

        f.write("$rem\n")
        f.write("  JOBTYPE FREQ\n")
        f.write(f"  METHOD        {method}\n")
        f.write("  DFT_D = D4\n")
        f.write(f"  BASIS         {basis_qc}\n")
        if scf_guess_read:
            f.write("  SCF_GUESS read\n")
        if vibman_print:
            f.write("  VIBMAN_PRINT 4\n")
        f.write("$end\n")

    def write_job_opt_read(f):
        f.write("$molecule\n")
        f.write("read\n")
        f.write("$end\n\n")

        f.write("$rem\n")
        f.write(f"   METHOD        {method}\n")
        f.write("   DFT_D = D4\n")
        f.write(f"   BASIS         {basis_qc}   Basis set\n")
        f.write("   JOBTYPE         OPT\n")
        f.write("   GEOM_OPT_COORDS -1\n")
        f.write("   GEOM_OPT_TOL_DISPLACEMENT   1\n")
        f.write("   GEOM_OPT_TOL_GRADIENT       1\n")
        f.write("   GEOM_OPT_TOL_ENERGY         1\n")
        f.write("   SCF_GUESS          read\n")
        f.write("   GEOM_OPT_HESSIAN   read\n")
        f.write("$end\n")

    with out_path.open("w", newline="\n") as f:
        # Job 1: FREQ at the starting geometry (creates Hessian for the next OPT)
        write_job_freq(f, scf_guess_read=False, vibman_print=False)

        f.write("\n@@@\n\n")

        # Job 2: OPT reading guess + Hessian
        write_job_opt_read(f)

        # Job 3 (only for opt-freq): final FREQ reading SCF guess
        if mode == "opt-freq":
            f.write("\n@@@\n\n")
            write_job_freq(f, scf_guess_read=True, vibman_print=True)

def write_qchem_aimd_inp(
    out_path: Path,
    *,
    atoms: list[tuple[str, float, float, float]],
    velocities: list[tuple[str, str, str]],
    method: str,
    basis: str,
    charge: int = 0,
    mult: int = 1,
    aimd_method: str = "bomd",
    time_step_au: int = 8,
    aimd_steps: int = 2500,
    aimd_print: int = 1,
    dft_d: str = "D4",
    no_reorient: bool = True,
    sym_ignore: bool = True,
) -> None:
    """Write a Q-Chem AIMD/QMD input.
    Notes:
      - Velocities are written (no unit conversion).
      - The $velocity block expects 3 numbers per atom (vx vy vz).
      - time_step_au is in Q-Chem atomic time units (Time_step = 8).
    """
    if len(velocities) != len(atoms):
        raise RuntimeError(
            f"Velocity/geometry mismatch: {len(atoms)} atoms but {len(velocities)} velocity lines."
        )

    basis_qc = _qchem_basis_name(basis)

    def _qe(s: str) -> str:
        # Q-Chem accepts E notation; normalize any D/d from Fortran-style files.
        return s.replace("D", "E").replace("d", "E")

    with out_path.open("w", newline="\n") as f:
        f.write("$molecule\n")
        f.write(f"{charge} {mult}\n")
        for sym, x, y, z in atoms:
            f.write(f"{sym:<2s} {x: .16f} {y: .16f} {z: .16f}\n")
        f.write("$end\n\n")

        f.write("$velocity\n")
        for vx, vy, vz in velocities:
            f.write(f" {_qe(vx)}   {_qe(vy)}   {_qe(vz)}\n")
        f.write("$end\n\n")

        f.write("$rem\n")
        f.write("JOBTYPE =  aimd\n")
        f.write(f"AIMD_METHOD = {aimd_method}\n")
        f.write(f"METHOD = {method}\n")
        f.write(f"BASIS  = {basis_qc}\n")
        f.write(f"DFT_D   = {dft_d}\n")
        f.write(f"Time_step = {int(time_step_au)}\n")
        f.write(f"aimd_steps = {int(aimd_steps)}\n")
        f.write(f"aimd_print = {int(aimd_print)}\n")
        if no_reorient:
            f.write("no_reorient = true\n")
        if sym_ignore:
            f.write("sym_ignore = true\n")
        f.write("$end\n")

def write_gaussian_dyn_com(
    out_path: Path,
    *,
    atoms: list[tuple[str, float, float, float]],
    velocities: list[tuple[str, str, str]],
    title: str,
    theory: str,
    basis: str,
    nproc: int,
    mem: str,
    stepsize: int = 2000,
    maxpoints: int = 2500,
    charge: int = 0,
    mult: int = 1,
    chk: str | None = None,
) -> None:
    """
    Write Gaussian16 BOMD input (dyn.com). Velocities are appended as numbers only:
    after geometry block, write a line '0', then N lines with vx vy vz.
    """
    if len(velocities) != len(atoms):
        raise RuntimeError(
            f"Velocity/geometry mismatch: {len(atoms)} atoms but {len(velocities)} velocity lines."
        )

    route = (
        f"# {theory}/{basis} EmpiricalDispersion=GD3BJ "
        f"SCF=(XQC,Tight) int=ultrafine "
        f"BOMD(GradOnly,Sample=Microcanonical,ReadVelocity,MaxPoints={maxpoints},StepSize={stepsize}) "
        f"nosymm"
    )

    with out_path.open("w", newline="\n") as f:
        if chk:
            f.write(f"%Chk={chk}\n")
        f.write(f"%NProcShared={nproc}\n")
        f.write(f"%Mem={mem}\n")
        f.write(route + "\n\n")
        f.write(title + "\n\n")
        f.write(f"{charge} {mult}\n")

        # geometry
        for sym, x, y, z in atoms:
            f.write(f"{sym:<2s} {x:>12.6f} {y:>12.6f} {z:>12.6f}\n")

        f.write("\n")
        f.write("0\n\n")
        for vx, vy, vz in velocities:
            f.write(f"   {vx}   {vy}   {vz}\n")
        f.write("\n")

def _orca_basis(bs: str) -> str:
    """Map common Gaussian-style basis names to ORCA equivalents."""
    key = bs.strip().lower().replace("_", "").replace("-", "")
    if key == "def2tzvp":
        return "Def2-TZVPD"
    return bs
def _orca_scf_keyword(conv: str) -> str:
    """Map 'VeryTight' -> 'VeryTightSCF', etc."""
    c = conv.strip()
    if c.lower().endswith("scf"):
        return c
    return f"{c}SCF"
def _vel_to_angfs(vels: list[tuple[float, float, float]], unit: str) -> list[tuple[float, float, float]]:
    unit = unit.lower()
    if unit == "angfs":
        return vels
    if unit != "au":
        raise RuntimeError(f"Unknown velocity unit: {unit!r} (use 'au' or 'angfs')")
    return [(vx * AUVEL_TO_ANGFS, vy * AUVEL_TO_ANGFS, vz * AUVEL_TO_ANGFS) for (vx, vy, vz) in vels]

def write_orca_qmd_inp(
    out_path: Path,
    *,
    atoms: list[tuple[str, float, float, float]],
    theory: str,
    basis: str,
    nproc: int,
    scf_kw: str,
    charge: int = 0,
    mult: int = 1,
    timestep_fs: float = 0.20,
    run_steps: int = 2501,
) -> None:
    """Write ORCA MD input."""
    basis = _orca_basis(basis)

    with out_path.open("w", newline="\n") as f:
        f.write(f"! MD {theory} D4 {basis} {scf_kw}\n")
        f.write(f"%PAL NPROCS {nproc} END\n")
        f.write("%md\n")
        f.write("  restart\n")
        f.write(f"  timestep {timestep_fs:.2f}_fs\n")
        f.write("  thermostat none\n")
        f.write("  dump position stride 1 filename \"trajectory.xyz\"\n")
        f.write("  dump velocity stride 1 filename \"velocity.xyz\"\n")
        f.write(f"  run {run_steps}\n")
        f.write("end\n\n")

        f.write(f"* xyz {charge} {mult}\n")
        for sym, x, y, z in atoms:
            f.write(f"  {sym:<2s} {x:>20.14f} {y:>20.14f} {z:>20.14f}\n")
        f.write("*\n")

def write_orca_mdrestart(
    out_path: Path,
    *,
    atoms: list[tuple[str, float, float, float]],
    velocities: list[tuple[float, float, float]],
    timestep_fs: float = 0.20,
    current_step: int = 1,
    vel_unit: str = "au",
) -> None:
    """Write ORCA AIMD restart file"""
    if len(velocities) != len(atoms):
        raise RuntimeError(
            f"Velocity/geometry mismatch: {len(atoms)} atoms but {len(velocities)} velocity lines."
        )

    v_angfs = _vel_to_angfs(velocities, vel_unit)

    with out_path.open("w", newline="\n") as f:
        f.write("# ORCA AIMD Restart File\n")
        f.write("&AtomCount\n")
        f.write(f"{len(atoms)}\n")
        f.write("&CurrentStep\n")
        f.write(f"{current_step}\n")
        f.write("&SimulationTime\n")
        f.write(f"{timestep_fs:.2f}\n")

        f.write("&Positions\n")
        for sym, x, y, z in atoms:
            f.write(f"  {sym:<2s} {x:>20.14f} {y:>20.14f} {z:>20.14f}\n")

        f.write("&Velocities\n")
        for (sym, _, _, _), (vx, vy, vz) in zip(atoms, v_angfs):
            f.write(f"{sym:<2s} {vx: .16E} {vy: .16E} {vz: .16E}\n")

# ----------------------------
# ORCA QMD trajectory parser (trajectory.xyz + velocity.xyz)
# ----------------------------

def iter_xyz_frames(path: Path):
    """Yield (nat, comment, records) from a multi-frame XYZ file.
    records is a list of (sym, x, y, z) as floats.
    """
    raw = path.read_text(errors="replace").splitlines()
    i = 0
    nline = len(raw)
    while i < nline:
        if not raw[i].strip():
            i += 1
            continue
        nat = int(raw[i].split()[0])
        if i + 1 >= nline:
            raise RuntimeError(f"Truncated XYZ frame at end of {path}")
        comment = raw[i+1].rstrip("\n")

        start = i + 2
        end = start + nat
        if end > nline:
            raise RuntimeError(f"Truncated XYZ frame (nat={nat}) starting at line {i+1} in {path}")

        rec = []
        for ln in raw[start:end]:
            parts = ln.split()
            if len(parts) < 4:
                raise RuntimeError(f"Bad XYZ atom line in {path}: {ln!r}")
            sym = parts[0]
            x = float(parts[1]); y = float(parts[2]); z = float(parts[3])
            rec.append((sym, x, y, z))

        yield nat, comment, rec
        i = end


def _parse_step_from_comment(comment: str):
    m = re.search(r"\bStep\s+(\d+)\b", comment)
    return int(m.group(1)) if m else None


def _parse_epot_from_comment(comment: str):
    # Example comment contains: E_Pot=-302.62881587 Hartree
    m = re.search(r"\bE_Pot\s*=\s*" + FLOAT_RE, comment)
    return _f2float(m.group(1)) if m else None


def write_nimbus_traj_from_orca(
    traj_xyz: Path,
    vel_xyz: Path,
    *,
    out_traj: Path,
    out_epot: Path | None,
    step_start: int | None,
    step_end_excl: int | None,
) -> None:
    """Read ORCA dumps (x in Å, v in Å/fs) and write flying_nimbus traj (x in Å, v in bohr/au_time).
    Also optionally write E_Pot (Hartree) column vector parsed from trajectory.xyz comments.
    """
    # Convert Å/fs -> bohr/au_time (inverse of AUVEL_TO_ANGFS)
    # v_bohr/au = v_A/fs * (AU_TIME_TO_FS / BOHR_TO_ANG)
    ANGFS_TO_AUVEL = AU_TIME_TO_FS / BOHR_TO_ANG

    it_pos = iter_xyz_frames(traj_xyz)
    it_vel = iter_xyz_frames(vel_xyz)

    # Renumber steps so the first written frame is step 1.
    # If the ORCA dumps start at Step 2 (common), we shift by (first_step-1).
    step_offset = None
    out_counter = 0

    
    epot_vals = []
    with out_traj.open("w", newline="\n") as f:
        for (nat_p, c_p, rec_p), (nat_v, c_v, rec_v) in zip(it_pos, it_vel):
            if nat_p != nat_v:
                raise RuntimeError(f"Natoms mismatch between {traj_xyz} ({nat_p}) and {vel_xyz} ({nat_v})")

            step = _parse_step_from_comment(c_p) or _parse_step_from_comment(c_v)

            if step_start is not None and step is not None and step < step_start:
                continue
            if step_end_excl is not None and step is not None and step >= step_end_excl:
                break

            if out_epot is not None:
                ep = _parse_epot_from_comment(c_p)
                if ep is not None:
                    epot_vals.append(ep)
          
            if step_offset is None:
                step_offset = (step - 1) if step is not None else 0
            out_counter += 1
            out_step = (step - step_offset) if step is not None else out_counter

            f.write(f"{nat_p}\n")
            f.write(f"step {out_step}\n")

            if len(rec_p) != nat_p or len(rec_v) != nat_p:
                raise RuntimeError("Frame size mismatch while reading ORCA dumps")

            for (sym_p, x, y, z), (_sym_v, vx, vy, vz) in zip(rec_p, rec_v):
                v_boa = (vx * ANGFS_TO_AUVEL, vy * ANGFS_TO_AUVEL, vz * ANGFS_TO_AUVEL)
                f.write(
                    f"{sym_p} {x: .12e} {y: .12e} {z: .12e} "
                    f"{v_boa[0]: .12e} {v_boa[1]: .12e} {v_boa[2]: .12e}\n"
                )

    if out_epot is not None:
        with out_epot.open("w", newline="\n") as g:
            for v in epot_vals:
                g.write(fmtD(v, 14) + "\n")

# ----------------------------
# Q-Chem QMD output parser (single .out)
# ----------------------------

QCHEM_QMD_MARKER = "Nuclear coordinates (Angst) and velocities (a.u.)"

_TIME_STEP_RE = re.compile(r"TIME\s+STEP\s*#\s*(\d+)", re.IGNORECASE)
_V_ELEC_RE = re.compile(r"V\(Electronic\)\s*=\s*" + FLOAT_RE)
_E_TOT_RE  = re.compile(r"E\(Total\)\s*=\s*" + FLOAT_RE)
_T_NUC_RE  = re.compile(r"T\(Nuclear\)\s*=\s*" + FLOAT_RE)

def _parse_qchem_qmd_block(lines: list[str], i_marker: int):
    """
    Parse one block starting at the marker line:
      Nuclear coordinates (Angst) and velocities (a.u.)
    Returns (records, next_index).
    records: list of (sym, xA, yA, zA, vx_au, vy_au, vz_au)
    """
    n = len(lines)
    j = i_marker + 1

    # Find the header line containing v_x v_y v_z
    while j < n and ("v_x" not in lines[j] or "v_y" not in lines[j] or "v_z" not in lines[j]):
        j += 1
    if j >= n:
        raise RuntimeError("Found Q-Chem QMD marker but could not find 'v_x v_y v_z' header.")

    # Next line is dashed, data starts after it
    j += 2
    rec = []

    while j < n:
        s = lines[j].strip()
        if not s:
            j += 1
            continue
        if s.startswith("-"):  # dashed line ends the table
            break

        parts = s.split()
        # Expected: idx sym x y z vx vy vz
        if len(parts) >= 8:
            # parts[0] = index, parts[1] = symbol
            sym = parts[1]
            x = _f2float(parts[2]); y = _f2float(parts[3]); z = _f2float(parts[4])
            vx = _f2float(parts[5]); vy = _f2float(parts[6]); vz = _f2float(parts[7])
            rec.append((sym, x, y, z, vx, vy, vz))

        j += 1

    if not rec:
        raise RuntimeError("Q-Chem QMD block parsed zero atoms.")

    return rec, j


def write_nimbus_traj_from_qchem_qmd(
    qchem_out: Path,
    *,
    out_traj: Path,
    out_epot: Path | None,
    step_start: int | None,
    step_end_excl: int | None,
) -> None:
    """
    Read Q-Chem AIMD/QMD output .out and write flying_nimbus trajectory:
      - positions are already in Angstrom
      - velocities are already in atomic units (a.u.) -> write as-is
    Optionally write E_pot column vector (Hartree), taken from V(Electronic) if present,
    otherwise computed as E(Total) - T(Nuclear).
    """
    lines = qchem_out.read_text(errors="replace").splitlines()
    n = len(lines)

    pending_frame = None  # list of (sym,x,y,z,vx,vy,vz) for the next TIME STEP
    current_step = None

    # energy accumulators for the step we just wrote (only if out_epot is requested)
    awaiting_epot = False
    v_elec = None
    e_tot  = None
    t_nuc  = None
    epot_vals = []

    # renumber output steps so first written becomes step 1 (useful if you cut ranges)
    first_written_step = None
    out_counter = 0

    def finalize_epot_if_needed():
        nonlocal awaiting_epot, v_elec, e_tot, t_nuc, current_step, epot_vals
        if not awaiting_epot:
            v_elec = None; e_tot = None; t_nuc = None
            return

        ep = None
        if v_elec is not None:
            ep = v_elec
        elif (e_tot is not None) and (t_nuc is not None):
            ep = e_tot - t_nuc

        if ep is None:
            raise RuntimeError(f"Could not parse E_pot for TIME STEP #{current_step} in {qchem_out}")

        epot_vals.append(ep)
        awaiting_epot = False
        v_elec = None; e_tot = None; t_nuc = None

    with out_traj.open("w", newline="\n") as f:
        i = 0
        while i < n:
            ln = lines[i]

            # New coordinate+velocity table -> store as pending frame
            if QCHEM_QMD_MARKER in ln:
                pending_frame, i = _parse_qchem_qmd_block(lines, i)
                continue

            # Start of a new TIME STEP -> write the pending frame for this step
            mstep = _TIME_STEP_RE.search(ln)
            if mstep:
                # close previous step energy (if any)
                finalize_epot_if_needed()

                current_step = int(mstep.group(1))

                # stop if we reached end range
                if step_end_excl is not None and current_step >= step_end_excl:
                    break

                # decide if we keep this step
                keep = True
                if step_start is not None and current_step < step_start:
                    keep = False

                frame = pending_frame
                pending_frame = None  # frame belongs to this TIME STEP

                if keep:
                    if frame is None:
                        raise RuntimeError(f"TIME STEP #{current_step} found but no preceding QMD table was parsed.")

                    if first_written_step is None:
                        first_written_step = current_step
                    out_counter += 1
                    out_step = current_step - (first_written_step - 1)

                    nat = len(frame)
                    f.write(f"{nat}\n")
                    f.write(f"step {out_step}\n")
                    for (sym, x, y, z, vx, vy, vz) in frame:
                        f.write(
                            f"{sym} {x: .12e} {y: .12e} {z: .12e} "
                            f"{vx: .12e} {vy: .12e} {vz: .12e}\n"
                        )

                    awaiting_epot = (out_epot is not None)
                else:
                    awaiting_epot = False

                i += 1
                continue

            # Parse energies while we're inside a step we kept (awaiting_epot True)
            if awaiting_epot:
                mv = _V_ELEC_RE.search(ln)
                if mv:
                    v_elec = _f2float(mv.group(1))
                mt = _E_TOT_RE.search(ln)
                if mt:
                    e_tot = _f2float(mt.group(1))
                mk = _T_NUC_RE.search(ln)
                if mk:
                    t_nuc = _f2float(mk.group(1))

            i += 1

        # finalize last step energy if needed
        finalize_epot_if_needed()

    if out_epot is not None:
        with out_epot.open("w", newline="\n") as g:
            for v in epot_vals:
                g.write(fmtD(v, 14) + "\n")


# ----------------------------
# Gaussian geo extraction
# ----------------------------

def extract_last_standard_orientation(lines: list[str]) -> list[tuple[float, float, float]]:
    """
    Return coordinates (x,y,z) from the *last* 'Standard orientation:' block.
    The block format is:

        Standard orientation:
        ---------------------------------------------------------------------
        ... header ...
        ---------------------------------------------------------------------
           i   Z   type     X       Y       Z
        ...
        ---------------------------------------------------------------------
    """
    # find last occurrence
    last_idx = None
    for i, ln in enumerate(lines):
        if "Standard orientation:" in ln:
            last_idx = i
    if last_idx is None:
        raise RuntimeError("No 'Standard orientation:' block found in file.")

    # find the 2nd dashed line after the marker (data starts after it)
    dash_count = 0
    data_start = None
    for j in range(last_idx, len(lines)):
        if lines[j].strip().startswith("-----"):
            dash_count += 1
            if dash_count == 2:
                data_start = j + 1
                break
    if data_start is None:
        raise RuntimeError("Malformed 'Standard orientation' block (could not locate header separators).")

    # read data lines until next dashed line
    coords: list[tuple[float, float, float]] = []
    for j in range(data_start, len(lines)):
        if lines[j].strip().startswith("-----"):
            break
        toks = lines[j].split()
        if len(toks) < 6:
            continue
        # toks: center, atomic_number, atomic_type, x, y, z
        try:
            x, y, z = float(toks[3]), float(toks[4]), float(toks[5])
        except ValueError:
            continue
        coords.append((x, y, z))

    if not coords:
        raise RuntimeError("Found 'Standard orientation:' but no coordinate lines were parsed.")

    return coords

def write_xyz_from_template(
    out_xyz: Path,
    template_xyz: Path,
    coords: list[tuple[float, float, float]],
    title: str = "Extracted geometry (Standard orientation)"
) -> None:
    template_title, atoms = read_xyz(template_xyz)
    symbols = [a[0] for a in atoms]

    if len(symbols) != len(coords):
        raise RuntimeError(
            f"Atom count mismatch: template has {len(symbols)} atoms, "
            #f"Gaussian Standard orientation has {len(coords)} atoms."
            f"extracted geometry has {len(coords)} atoms."
        )

    with out_xyz.open("w", newline="\n") as f:
        f.write(f"{len(coords)}\n")
        f.write(title + "\n")
        for sym, (x, y, z) in zip(symbols, coords):
            f.write(f"{sym:<2s} {x:>12.6f} {y:>12.6f} {z:>12.6f}\n")

#ORCA geo extraction:

_ORCA_CONV_MARK = "THE OPTIMIZATION HAS CONVERGED"
_ORCA_CART_RE = re.compile(r"CARTESIAN COORDINATES\s*\((ANGSTROEM|ANGSTROM)\)", re.IGNORECASE)
def extract_last_orca_cartesian_angstroem(lines: list[str]) -> list[tuple[str, float, float, float]]:
    """
    ORCA: after the HURRAY/convergence banner, take the last
    'CARTESIAN COORDINATES (ANGSTROEM)' block and return atoms as (sym,x,y,z).
    """
    conv_idx = None
    for i, ln in enumerate(lines):
        if _ORCA_CONV_MARK in ln:
            conv_idx = i
    if conv_idx is None:
        raise ValueError(f"Could not find ORCA convergence marker: {_ORCA_CONV_MARK!r}")

    label_idx = None
    for i in range(conv_idx, len(lines)):
        if _ORCA_CART_RE.search(lines[i]):
            label_idx = i
    if label_idx is None:
        raise ValueError("Could not find ORCA 'CARTESIAN COORDINATES (ANGSTROEM)' after convergence banner.")

    # ORCA format is:
    # ---------------------------------
    # CARTESIAN COORDINATES (ANGSTROEM)
    # ---------------------------------
    #   O   x y z
    k = label_idx + 1
    while k < len(lines) and lines[k].strip().startswith("-"):
        k += 1

    atoms: list[tuple[str, float, float, float]] = []
    for j in range(k, len(lines)):
        s = lines[j].strip()
        if not s:
            break
        if s.startswith("-"):
            break
        if "CARTESIAN COORDINATES" in s.upper():
            break

        parts = s.split()
        if len(parts) < 4:
            break
        sym = parts[0]
        try:
            x = float(parts[1]); y = float(parts[2]); z = float(parts[3])
        except ValueError:
            break
        atoms.append((sym, x, y, z))

    if not atoms:
        raise ValueError("Parsed zero atoms from ORCA CARTESIAN COORDINATES (ANGSTROEM) block.")
    return atoms


def write_xyz_atoms(out_xyz: Path, atoms: list[tuple[str, float, float, float]], title: str) -> None:
    """Write a standard XYZ from explicit atom symbols and coordinates (already in Angstrom)."""
    with out_xyz.open("w", newline="\n") as f:
        f.write(f"{len(atoms)}\n")
        f.write(title + "\n")
        for sym, x, y, z in atoms:
            f.write(f"{sym:<2s} {x: .12f} {y: .12f} {z: .12f}\n")


#QCHEM geo extraction:

# Q-Chem geometry marker
QCHEM_GEO_MARKER = "Standard Nuclear Orientation (Angstroms)"
def extract_last_qchem_sno_atoms(lines: list[str]) -> list[tuple[str, float, float, float]]:
    last_idx = None
    for i, ln in enumerate(lines):
        if QCHEM_GEO_MARKER in ln:
            last_idx = i
    if last_idx is None:
        raise RuntimeError(f"No Q-Chem '{QCHEM_GEO_MARKER}' block found in file.")

    # find first dashed line after marker, then data starts after the next dashed line
    dash_count = 0
    data_start = None
    for j in range(last_idx, len(lines)):
        if lines[j].strip().startswith("---"):
            dash_count += 1
            if dash_count == 2:
                data_start = j + 1
                break
    if data_start is None:
        raise RuntimeError("Malformed Q-Chem geometry block (missing header separators).")

    atoms: list[tuple[str, float, float, float]] = []
    for j in range(data_start, len(lines)):
        if lines[j].strip().startswith("---"):
            break
        toks = lines[j].split()
        if len(toks) < 5:
            continue
        sym = toks[1]
        try:
            x = float(toks[2].replace("D","E").replace("d","E"))
            y = float(toks[3].replace("D","E").replace("d","E"))
            z = float(toks[4].replace("D","E").replace("d","E"))
        except ValueError:
            continue
        atoms.append((sym, x, y, z))

    if not atoms:
        raise RuntimeError("Found Q-Chem geometry marker but parsed zero atoms.")
    return atoms

# Q-Chem geometry marker
_QCHEM_GEO_LINE_RE = re.compile(
    r"^\s*\d+\s+([A-Za-z]{1,2})\s+([-\d\.DdEe+]+)\s+([-\d\.DdEe+]+)\s+([-\d\.DdEe+]+)"
)

def extract_last_qchem_standard_nuclear_orientation_atoms(
    lines: list[str],
) -> list[tuple[str, float, float, float]]:
    """
    Return (sym,x,y,z) from the *last* Q-Chem:
        Standard Nuclear Orientation (Angstroms)
    """
    last_idx = None
    for i, ln in enumerate(lines):
        if QCHEM_GEO_MARKER in ln:
            last_idx = i
    if last_idx is None:
        raise RuntimeError(f"No Q-Chem '{QCHEM_GEO_MARKER}' block found in file.")

    # find first dashed line after the marker (the one under the header)
    data_start = None
    for j in range(last_idx, len(lines)):
        if lines[j].strip().startswith("-"):
            data_start = j + 1
            break
    if data_start is None:
        raise RuntimeError("Malformed Q-Chem geometry block (missing dashed separator).")

    atoms: list[tuple[str, float, float, float]] = []
    for j in range(data_start, len(lines)):
        s = lines[j].strip()
        if not s:
            continue
        if s.startswith("-"):
            break
        m = _QCHEM_GEO_LINE_RE.match(lines[j])
        if not m:
            continue
        sym = m.group(1)
        x = float(m.group(2).replace("D", "E").replace("d", "E"))
        y = float(m.group(3).replace("D", "E").replace("d", "E"))
        z = float(m.group(4).replace("D", "E").replace("d", "E"))
        atoms.append((sym, x, y, z))

    if not atoms:
        raise RuntimeError("Found Q-Chem geometry marker but parsed zero atoms.")
    return atoms



# ----------------------------
# Main
# ----------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "1) Extract Gaussian16 lower-triangular Hessian and flatten to 1-column vector (D exponents)\n"
            "2) Extract ORCA lower-triangular Hessian and flatten to 1-column vector (D exponents)\n"
            "3) Generate Gaussian16 .com from XYZ using --opt or --freq\n"
            "4) Generate ORCA .inp from XYZ using --orca-freq\n"
            "5) Extract Gaussian16 last printed geometry in standart orientation (No Hessian Extraction)"
        )
    )

    # Primary input: gaussian .out (default behavior) OR xyz (when --opt/--freq are set)
    ap.add_argument("input_file", type=Path, help="Gaussian output (.out/.log) OR XYZ file (with --opt/--freq)")
    # Hessian outputs
    ap.add_argument("-m", "--matrix-out", type=Path, default=Path("Hessian.out"), help="Output Hessian file (default: Hessian.out)")
    ap.add_argument("-v", "--vector-out", type=Path, default=Path("Hessian_flat.out"), help="Output vector file (default: Hessian_flat.out)")
    #Hessian reading from ORCA:
    ap.add_argument("--orca-hess", action="store_true", help="Extract Hessian from an ORCA .hess file (input_file is .hess)")
    #Hessian reading from QCHEM:
    ap.add_argument("--qchem-hess", action="store_true", help="Extract Hessian from a Q-Chem HESS file (input_file is HESS)")
    # .com / .inp generation mode (mutually exclusive)
    mx = ap.add_mutually_exclusive_group()
    mx.add_argument("--opt", action="store_true", help="Generate geom.com for geometry optimization (input_file is XYZ)")
    mx.add_argument("--freq", action="store_true", help="Generate geom_freq.com for frequency job (input_file is XYZ)")
    mx.add_argument("--orca-opt", action="store_true", help="Generate ORCA optimization input geom.inp (input_file is XYZ)")
    mx.add_argument("--orca-freq", action="store_true", help="Generate ORCA opt+freq input geom_freq.inp (input_file is XYZ)")
    mx.add_argument("--dyn", action="store_true", help="Generate dyn.com for BOMD dynamics (input_file is XYZ)")
    mx.add_argument("--orca-qmd", action="store_true", help="Generate ORCA QMD inputs (<stem>_qmd.inp + <stem>_qmd.mdrestart) from equilibrium XYZ (input_file) and velocities (--orca-vel-file)") 
    mx.add_argument(
    "--qchem-qmd",
    action="store_true",
    help="Generate Q-Chem AIMD/QMD input dyn.inp from equilibrium XYZ (input_file) and velocities (--qchem-vel-file)",
    )
    #For qchem reuse THEORY, BS charge and mult already set =)
    mx.add_argument("--qchem-opt-single", action="store_true", help="Generate Q-Chem *single-job* OPT input (template-like) -> opt.inp (input_file is XYZ)")
    mx.add_argument("--qchem-freq", action="store_true", help="Generate Q-Chem *single-job* FREQ input (template-like) -> freq.inp (input_file is XYZ)")
    #Version 2 for QCHEM
    mx.add_argument("--qchem-opt", action="store_true", help="Generate Q-Chem multi-job optimization input opt.inp (input_file is XYZ)")
    mx.add_argument("--qchem-opt-freq", action="store_true", help="Generate Q-Chem multi-job opt+freq input opt-freq.inp (input_file is XYZ)")
    # Requested Gaussian settings
    ap.add_argument("--BS", default="Def2TZVP", help="Basis set (default: Def2TZVP)")
    ap.add_argument("--THEORY", default="B3LYP", help="DFT/ab-initio method (default: B3LYP)")
    ap.add_argument("--convergence", default="VeryTight", help="Opt convergence keyword (default: VeryTight)")
    ap.add_argument("--Nproc", type=int, default=48, help="%%NProcShared (default: 48)")
    ap.add_argument("--mem", default="300Gb", help="%%mem (default: 300Gb)")
    ap.add_argument("--charge", type=int, default=0, help="Total charge (default: 0)")
    ap.add_argument("--mult", type=int, default=1, help="Spin multiplicity (default: 1)")
    ap.add_argument(
            "--extract-geo",
            action="store_true",
            help="Extract optimized geometry and exit (skip Hessian extraction). Gaussian: last 'Standard orientation'. ORCA: last 'CARTESIAN COORDINATES (ANGSTROEM) after 'THE OPTIMIZATION HAS CONVERGED'. Q-Chem: last 'Standard Nuclear Orientation (Angstroms)'",
            )
    ap.add_argument("--geo-out", type=Path, default=Path("geo_opt.xyz"),
            help="Output XYZ name for extracted geometry (default: geo_opt.xyz)")
    ap.add_argument(
            "--xyz-template",
            type=Path,
            default=Path("geo.xyz"),
            help="XYZ file providing atom symbols/order for geometry output (default: geo.xyz).")
    ap.add_argument("--stepsize", type=int, default=2000, help="BOMD StepSize (default: 2000)")
    ap.add_argument("--npoints", type=int, default=2500, help="BOMD MaxPoints / number of points (default: 2500)")
    ap.add_argument("--vel-file", type=Path, default=Path("velocity_gau.xyz"), help="Velocity file (default: velocity_gau.xyz)")
    ap.add_argument("--dyn-out", type=Path, default=Path("dyn.com"), help="Output dynamics input file (default: dyn.com)")
    ap.add_argument("--chk", default=None, help="Checkpoint filename for dynamics (default: <xyz stem>.chk)")
    # ---- ORCA QMD input generator ----
    ap.add_argument("--orca-vel-file", type=Path, default=Path("velocity_orca.xyz"), help="Velocity file for ORCA QMD (default: velocity_orca.xyz)")
    ap.add_argument("--orca-vel-unit", choices=["au", "angfs"], default="au", help="Units of ORCA velocity file (default: au)")
    ap.add_argument("--qmd-timestep", type=float, default=0.20, help="ORCA MD timestep in fs (default: 0.20)")
    ap.add_argument("--qmd-run", type=int, default=2501, help="ORCA MD run steps (default: 2501)")
    ap.add_argument("--qmd-prefix", default=None, help="Prefix for ORCA QMD outputs (default: <input xyz stem>)")
    # ---- Q-Chem AIMD/QMD input generator ----
    ap.add_argument("--qchem-vel-file", type=Path, default=Path("velocity.xyz"), help="Velocity file for Q-Chem AIMD/QMD (default: velocity.xyz)")
    ap.add_argument("--qchem-qmd-out", type=Path, default=Path("dyn.inp"), help="Output Q-Chem AIMD input filename (default: dyn.inp)")
    ap.add_argument("--qchem-timestep", type=int, default=8, help="Q-Chem Time_step (a.u. of time) (default: 8)")
    ap.add_argument("--qchem-steps", type=int, default=2500, help="Q-Chem aimd_steps (default: 2500)")
    ap.add_argument("--qchem-print", type=int, default=1, help="Q-Chem aimd_print (default: 1)")

    # ---- Gaussian BOMD output parser ----
    ap.add_argument("--parse-dyn", action="store_true", help="Parse Gaussian BOMD dynamics from output")
    ap.add_argument("-i", "--inizio", type=int, help="Starting step (required with --parse-dyn)")
    ap.add_argument("-f", "--fine", type=int, help="Ending step (exclusive and required with --parse-dyn)")
    ap.add_argument("-N", "--Natom", type=int, help="Total number of atoms (optional; if omitted it is inferred from --xyz)")
    ap.add_argument("-g", "--gout", type=Path, help="Gaussian output file (optional; if omitted uses input_file)")
    ap.add_argument("--xyz", type=Path, help="Reference xyz at equilibrium geometry (required with --parse-dyn; provides symbols/order)")
    ap.add_argument("--vel", type=Path, help="Initial velocity file (optional fallback if velocities not found in output)")
    ap.add_argument("-o", "--output", default="parsed_log", type=str, help="Basename for outputs (default: parsed_log)")
    ap.add_argument("--Emin", type=float, default=0.0, help="Potential energy at minimum in Hartree (used if --scale)")
    ap.add_argument("--scale", action="store_true", help="Shift Epot and Etot by Emin")
    ap.add_argument("--movie", action="store_true", help="Write coordinates-only xyz for VMD")
    ap.add_argument("--total", action="store_true", help="Write energies file (EKin/EPot/ETot) for each step")
    ap.add_argument("--nimbus-traj", action="store_true", help="Also write a flying_nimbus-compatible trajectory (x in Angstrom, v in bohr/au_time).")
    ap.add_argument("--nimbus-out", type=Path, default=None, help="Output filename for nimbus trajectory (default: <output>_traj.xyz)")
    # ---- ORCA QMD output parser (trajectory.xyz + velocity.xyz) ----
    ap.add_argument("--parse-orca-qmd", action="store_true", help="Parse ORCA QMD dumps (trajectory.xyz + velocity.xyz) and write flying_nimbus trajectory")
    ap.add_argument(
            "--parse-qchem-qmd",
            action="store_true",
            help="Parse Q-Chem AIMD/QMD output (input_file) and write flying_nimbus trajectory (x in Angstrom, v in a.u.).",
    )
    ap.add_argument("--orca-traj", type=Path, default=Path("trajectory.xyz"), help="ORCA MD positions dump (default: trajectory.xyz)")
    ap.add_argument("--orca-vel", type=Path, default=Path("velocity.xyz"), help="ORCA MD velocities dump (default: velocity.xyz)")
    ap.add_argument("--epot-out", type=Path, default=None, help="ORCA: parsed from trajectory.xyz comments. Q-Chem: from V(Electronic) (or E(Total)-T(Nuclear))")
    
    args = ap.parse_args()

    # ---- Parse ORCA QMD dumps (trajectory.xyz + velocity.xyz) ----
    if args.parse_orca_qmd:
        outbase = args.output
        traj_out = args.nimbus_out if args.nimbus_out is not None else Path(outbase + "_traj.xyz")
        step_start = args.inizio if args.inizio is not None else None
        step_end   = args.fine   if args.fine   is not None else None
        write_nimbus_traj_from_orca(
                args.orca_traj,
                args.orca_vel,
                out_traj=traj_out,
                out_epot=args.epot_out,
                step_start=step_start,
                step_end_excl=step_end,
        )
        print(f"Wrote: {traj_out}")
        if args.epot_out is not None:
            print(f"Wrote: {args.epot_out}")
        return 0

    # ---- Parse Q-Chem QMD output (.out) ----
    if args.parse_qchem_qmd:
        outbase = args.output
        traj_out = args.nimbus_out if args.nimbus_out is not None else Path(outbase + "_traj.xyz")
        step_start = args.inizio if args.inizio is not None else None
        step_end   = args.fine   if args.fine   is not None else None
        write_nimbus_traj_from_qchem_qmd(
                args.input_file,
                out_traj=traj_out,
                out_epot=args.epot_out,
                step_start=step_start,
                step_end_excl=step_end,
                )
        print(f"Wrote: {traj_out}")
        if args.epot_out is not None:
            print(f"Wrote: {args.epot_out}")
        return 0


    # ---- Parse Gaussian BOMD dynamics output ----
    if args.parse_dyn:
        if args.inizio is None or args.fine is None:
            raise SystemExit("ERROR: --parse-dyn requires --inizio and --fine")
        if args.xyz is None:
            raise SystemExit("ERROR: --parse-dyn requires --xyz")

        gout_path = args.gout if args.gout else args.input_file
        lines = Path(gout_path).read_text(errors="replace").splitlines()
        symb = read_xyz_symbols(args.xyz)
        nat = len(symb)
        if args.Natom is not None and args.Natom != nat:
            raise SystemExit(f"ERROR: --Natom={args.Natom} but --xyz has {nat} atoms")
        vel_fallback = None
        if args.vel is not None:
            vel_fallback = read_velocity_xyz_noatoms(args.vel)
            if len(vel_fallback) != nat:
                raise SystemExit(f"ERROR: --vel has {len(vel_fallback)} lines but --xyz has {nat} atoms")
        blocks = split_bomd_blocks(lines)

        # selezione step [inizio, fine)
        selected = [(step, i0, i1) for (step, i0, i1) in blocks if args.inizio <= step < args.fine]
        if not selected:
            raise SystemExit("ERROR: No MD steps found in the requested range")

        import numpy as np
        nstep = len(selected)
        xtot = np.zeros((nstep, 3*nat), dtype=float)
        vtot = np.zeros((nstep, 3*nat), dtype=float)
        if args.total:
            Ekin = np.zeros(nstep, dtype=float)
            Epot = np.zeros(nstep, dtype=float)
            Etot = np.zeros(nstep, dtype=float)
        for i, (step, i0, i1) in enumerate(selected):
            seg_text = "\n".join(lines[i0:i1])
            seg_lines = lines[i0:i1]
            x, v = parse_xyzv_from_tables(seg_lines, nat, vel_fallback=vel_fallback)
            xtot[i, :] = np.array(x, dtype=float)
            vtot[i, :] = np.array(v, dtype=float)
            if args.total:
                Ekin[i], Epot[i], Etot[i] = get_energies_line(seg_text)
        # vtot (qui) = MW cartesian velocity: (sqrt(amu)*bohr/sec)
        xm = get_masses_cart(symb)  # 3*nat masses in amu
        v_bohr_s = vtot / np.sqrt(xm)[None, :]          # -> bohr/sec (unweighted)
        v_ang_fs = v_bohr_s * BOHR_TO_ANG * 1.0e-15     # -> Ang/fs
        v_bohr_au = v_bohr_s * SEC_PER_AUTIME           # -> bohr / au_time (flying_nimbus)

        # scale energies 
        if args.total and args.scale:
            Epot = Epot - args.Emin
            Etot = Etot - args.Emin
        # Output writing
        outbase = args.output
        with open(outbase + "_xv.xyz", "w") as f:
            for i, (step, _, _) in enumerate(selected):
                print(nat, file=f)
                print(f"step {step}", file=f)
                for j in range(nat):
                    x = xtot[i, 3*j:3*j+3]
                    v = v_ang_fs[i, 3*j:3*j+3]
                    print(f"{symb[j]}   {x[0]}  {x[1]}  {x[2]}     {v[0]}  {v[1]}  {v[2]}", file=f)
        if args.nimbus_traj:
            traj_path = args.nimbus_out if args.nimbus_out is not None else Path(outbase + "_traj.xyz")
            x_ang = xtot * BOHR_TO_ANG  # bohr -> Ang
            with traj_path.open("w", newline="\n") as f:
                for i, (step, _, _) in enumerate(selected):
                    f.write(f"{nat}\n")
                    f.write(f"step {step}\n")
                    for j in range(nat):
                        x = x_ang[i, 3*j:3*j+3]
                        v = v_bohr_au[i, 3*j:3*j+3]  # bohr / au_time (flying_nimbus)
                        f.write(
                                f"{symb[j]} "
                                f"{x[0]: .12e} {x[1]: .12e} {x[2]: .12e} "
                                f"{v[0]: .12e} {v[1]: .12e} {v[2]: .12e}\n"
                                )
            print(f"Wrote: {traj_path}")


        if args.movie:
            ang = xtot * 0.529177
            with open(outbase + ".xyz", "w") as f:
                for i, (step, _, _) in enumerate(selected):
                    print(nat, file=f)
                    print(f"step {step}", file=f)
                    for j in range(nat):
                        x = ang[i, 3*j:3*j+3]
                        print(f"{symb[j]}   {x[0]}  {x[1]}  {x[2]}", file=f)

        if args.total:
            with open(outbase + "_energies.dat", "w") as f:
                print("# Step    Ekin(Ha)          Epot(Ha)          Etot(Ha)", file=f)
                for i, (step, _, _) in enumerate(selected):
                    print(f"{step:6d}  {fmtD(Ekin[i],14)}  {fmtD(Epot[i],14)}  {fmtD(Etot[i],14)}", file=f)

        print(f"Wrote: {outbase}_xv.xyz")
        if args.movie:
            print(f"Wrote: {outbase}.xyz")
        if args.total:
            print(f"Wrote: {outbase}_energies.dat")
        return 0

    # Branch: generate .com from xyz
    if args.opt or args.freq or args.dyn or args.orca_opt or args.orca_freq or args.orca_qmd or args.qchem_opt or args.qchem_opt_freq or args.qchem_opt_single or args.qchem_freq or args.qchem_qmd:
        xyz = args.input_file
        title, atoms = read_xyz(xyz)

        if args.qchem_qmd:
            vels = read_velocity_xyz_noatoms(args.qchem_vel_file)
            write_qchem_aimd_inp(
                    args.qchem_qmd_out,
                    atoms=atoms,
                    velocities=vels,
                    method=args.THEORY,
                    basis=args.BS,
                    charge=args.charge,
                    mult=args.mult,
                    time_step_au=args.qchem_timestep,
                    aimd_steps=args.qchem_steps,
                    aimd_print=args.qchem_print,
                    )
            print(f"Wrote Q-Chem AIMD/QMD input: {args.qchem_qmd_out}")
            return 0


        if args.orca_qmd:
            # ORCA QMD: generate <prefix>_qmd.inp and <prefix>_qmd.mdrestart
            nproc = args.Nproc
            # match the defaults if the user did not override the global Gaussian defaults
            if nproc == 48:
                nproc = 20

            scf_kw = _orca_scf_keyword(args.convergence)
            prefix = args.qmd_prefix if args.qmd_prefix else xyz.stem
            out_inp = Path(f"{prefix}_qmd.inp")
            out_rst = Path(f"{prefix}_qmd.mdrestart")
            vels_s = read_velocity_xyz_noatoms(args.orca_vel_file)
            velocities = [(_f2float(vx), _f2float(vy), _f2float(vz)) for (vx, vy, vz) in vels_s]
            if len(velocities) != len(atoms):
                raise RuntimeError(f"Velocity/geometry mismatch: {len(atoms)} atoms but {len(velocities)} velocity lines.")
            write_orca_qmd_inp(
                    out_inp,
                    atoms=atoms,
                    theory=args.THEORY,
                    basis=args.BS,
                    nproc=nproc,
                    scf_kw=scf_kw,
                    charge=args.charge,
                    mult=args.mult,
                    timestep_fs=args.qmd_timestep,
                    run_steps=args.qmd_run,
                    )
            write_orca_mdrestart(
                    out_rst,
                    atoms=atoms,
                    velocities=velocities,
                    timestep_fs=args.qmd_timestep,
                    current_step=1,
                    vel_unit=args.orca_vel_unit,
                    )
            print(f"Wrote ORCA QMD input: {out_inp}")
            print(f"Wrote ORCA MD restart: {out_rst}")
            return 0


        # ---- ORCA input generation ----
        if args.orca_opt or args.orca_freq:
            out = Path("geom.inp") if args.orca_opt else Path("geom_freq.inp")
            # ORCA defaults, but keep user overrides:
            theory = args.THEORY  # default B3LYP already :contentReference[oaicite:8]{index=8}
            basis  = args.BS if args.BS != "Def2TZVP" else "Def2-TZVPD"
            nproc  = args.Nproc if args.Nproc != 48 else 20
            conv   = args.convergence
            # no %maxcore line unless user *really* changed mem
            mem = None if args.mem == "300Gb" else args.mem
            write_orca_inp(
                out,
                atoms=atoms,
                title=title,
                theory=theory,
                basis=basis,
                nproc=nproc,
                mem=mem,
                mode=("opt" if args.orca_opt else "freq"),
                convergence=conv,
                charge=args.charge,
                mult=args.mult,
            )
            print(f"Wrote ORCA input: {out}")
            return 0

        # ---- Q-Chem input generation ----
        if args.qchem_opt_single or args.qchem_freq:
            out = Path("opt.inp") if args.qchem_opt_single else Path("freq.inp")
            write_qchem_single_inp(
                    out,
                    atoms=atoms,
                    method=args.THEORY,
                    basis=args.BS,
                    charge=args.charge,
                    mult=args.mult,
                    mode=("opt" if args.qchem_opt_single else "freq"),
                    )
            print(f"Wrote Q-Chem input: {out}")
            return 0

        if args.qchem_opt or args.qchem_opt_freq:
            out = Path("opt.inp") if args.qchem_opt else Path("opt-freq.inp")
            write_qchem_inp(
                    out,
                    atoms=atoms,
                    method=args.THEORY,
                    basis=args.BS,
                    charge=args.charge,
                    mult=args.mult,
                    mode=("opt" if args.qchem_opt else "opt-freq"),
            )
            print(f"Wrote Q-Chem input: {out}")
            return 0

        if args.opt:
            out = Path("geom.com")
            write_gaussian_com(
                out,
                atoms=atoms,
                title=title,
                theory=args.THEORY,
                basis=args.BS,
                nproc=args.Nproc,
                mem=args.mem,
                mode="opt",
                convergence=args.convergence,
                charge=args.charge,
                mult=args.mult,
            )
            print(f"Wrote Gaussian16 opt input: {out}")
            return 0
        if args.freq:
            out = Path("geom_freq.com")
            write_gaussian_com(
                out,
                atoms=atoms,
                title=title,
                theory=args.THEORY,
                basis=args.BS,
                nproc=args.Nproc,
                mem=args.mem,
                mode="freq",
                convergence=args.convergence,
                charge=args.charge,
                mult=args.mult,
            )
            print(f"Wrote Gaussian16 freq input: {out}")
            return 0
        # dyn
        velocities = read_velocity_xyz_noatoms(args.vel_file)
        chkname = args.chk if args.chk else f"dyn.chk"
        write_gaussian_dyn_com(
                args.dyn_out,
                atoms=atoms,
                velocities=velocities,
                title=title,
                theory=args.THEORY,
                basis=args.BS,
                nproc=args.Nproc,
                mem=args.mem,
                stepsize=args.stepsize,
                maxpoints=args.npoints,
                charge=args.charge,
                mult=args.mult,
                chk=chkname,
                )
        print(f"Wrote Gaussian16 dynamics input: {args.dyn_out}")
        return 0
        

    # Default: Hessian extraction from Gaussian output
    gaussian_out = args.input_file
    lines = gaussian_out.read_text(errors="replace").splitlines()
    # ORCA Hessian extraction from .hess
    if args.orca_hess:
        chunk = extract_orca_hessian_chunk(lines)
        full  = parse_orca_full_matrix(chunk)
        rows  = orca_full_to_lower_triangle_rows(full)
        write_hessian_out(rows, args.matrix_out)   # writes D-exponents
        write_hess_vec(rows, args.vector_out)      # two blank lines + D-exponents
        print(f"Wrote ORCA Hessian: {args.matrix_out} and {args.vector_out}")
        return 0
    # Q-Chem Hessian extraction from HESS
    if args.qchem_hess:
        rows = extract_qchem_hessian_lower_triangle_rows(lines)
        write_hessian_out(rows, args.matrix_out)   # D exponents
        write_hess_vec(rows, args.vector_out)      # 2 blank lines + D exponents
        print(f"Wrote Q-Chem Hessian: {args.matrix_out} and {args.vector_out}")
        return 0
    # Geometry-only mode: no Hessian extraction
    if args.extract_geo:
        out_xyz = args.geo_out if args.geo_out is not None else Path("geo_opt.xyz")
        # Detect Gaussian vs Q-Chem vs ORCA and extract accordingly
        if any("Standard orientation:" in ln for ln in lines):
            coords = extract_last_standard_orientation(lines)
            write_xyz_from_template(
                    out_xyz=out_xyz,
                    template_xyz=args.xyz_template,
                    coords=coords,
                    title=f"Last Gaussian Standard orientation from {args.input_file.name}",
                    )
        elif any(QCHEM_GEO_MARKER in ln for ln in lines):
            atoms = extract_last_qchem_standard_nuclear_orientation_atoms(lines)
            write_xyz_atoms(
                    out_xyz=out_xyz,
                    atoms=atoms,
                    title=f"Last Q-Chem Standard Nuclear Orientation from {args.input_file.name}",
                    )
        elif any(_ORCA_CONV_MARK in ln for ln in lines):
            atoms = extract_last_orca_cartesian_angstroem(lines)
            write_xyz_atoms(
                    out_xyz=out_xyz,
                    atoms=atoms,
                    title=f"Final ORCA optimized geometry from {args.input_file.name}",
                    )
        else:
            raise ValueError(
                    "Could not detect geometry format. Expected one of:\n"
                    "  - Gaussian: 'Standard orientation:'\n"
                    f"  - Q-Chem: '{QCHEM_GEO_MARKER}'\n"
                    f"  - ORCA: '{_ORCA_CONV_MARK}' + 'CARTESIAN COORDINATES (ANGSTROEM)'\n"
                    )
        print(f"Wrote last geometry XYZ: {out_xyz}")
        return 0


    chunk = extract_hessian_chunk(lines)
    rows = parse_lower_triangular_rows(chunk)

    write_hessian_out(rows, args.matrix_out)
    write_hess_vec(rows, args.vector_out)

    n = max(rows.keys())
    print(f"Extracted lower-triangular Hessian with {n} rows.")
    print(f"Wrote: {args.matrix_out} (D exponents)")
    print(f"Wrote: {args.vector_out} (D exponents, two blank lines on top)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(1)

