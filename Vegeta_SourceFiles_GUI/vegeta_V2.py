#!/usr/bin/env python3
import re
import argparse
from pathlib import Path
import numpy as np

#SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#Authors: Giacomo Mandelli, Giacomo Botti

# =========================
# Constants
# =========================
TOCM = 219474.625  # au -> cm^-1

EH_TO_KJMOL  = 2625.499638
EH_TO_KCALMOL = 627.509474

# Atomic masses in a.u.
MASS_AU = {
    "H": 1837.15,
    "D": 3674.30,
    "O": 29156.96,
    "Op": 87470.88,
    "Od": 32810.46,
    "C": 21874.66,
    "Cp": 65623.98,
    "N": 25526.06,
    "S": 58281.54,
    "P": 56455.19,
    "F": 34631.97,
    "I": 231332.70,
}

ANG2BOHR = 1.0 / 0.529177
AU_TIME_S = 2.4188843265857e-17
AU_VEL_TO_BOHR_S = 1.0 / AU_TIME_S

# =========================
# Utilities
# =========================


def expand_mode_tokens(tokens: list[str], nvib: int) -> list[int]:
    """
    Expand tokens like ["1-5", "8", "10..12"] into a unique, ordered list of ints.
    Accepts separators: '-', ':', '..' and also comma-separated chunks.
    """
    modes: list[int] = []
    for tok in tokens:
        for part in tok.split(","):
            part = part.strip()
            if not part:
                continue

            m = re.match(r"^(\d+)\s*(?:-|:|\.\.)\s*(\d+)$", part)
            if m:
                a = int(m.group(1))
                b = int(m.group(2))
                step = 1 if a <= b else -1
                modes.extend(range(a, b + step, step))
            else:
                modes.append(int(part))

    # validate + de-duplicate while preserving order
    out: list[int] = []
    seen = set()
    for x in modes:
        if not (1 <= x <= nvib):
            raise ValueError(f"Mode {x} out of range 1..{nvib}")
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def expand_atom_tokens(tokens: list[str], nat: int) -> list[int]:
    """
    Expand tokens like ["1-5", "8", "10..12"] into a unique, ordered list of atom indices (1-based).
    Accepts separators: '-', ':', '..' and also comma-separated chunks.
    """
    atoms: list[int] = []
    for tok in tokens:
        for part in tok.split(","):
            part = part.strip()
            if not part:
                continue

            m = re.match(r"^(\d+)\s*(?:-|:|\.\.)\s*(\d+)$", part)
            if m:
                a = int(m.group(1))
                b = int(m.group(2))
                step = 1 if a <= b else -1
                atoms.extend(range(a, b + step, step))
            else:
                atoms.append(int(part))

    out: list[int] = []
    seen = set()
    for x in atoms:
        if not (1 <= x <= nat):
            raise ValueError(f"Atom index {x} out of range 1..{nat}")
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def write_cnorm(path: str | Path, evals: np.ndarray, cnorm: np.ndarray) -> None:
    """
    Write cnorm.dat for flying_nimbus:
      - 3N lines of eigenvectors, one eigenvector per line (columns of cnorm)
      - a line with sqrt(|eigenvalues|)
      - a final line with eigenvalues  <-- this is what flying_nimbus reads
    """
    p = Path(path)
    ncart = cnorm.shape[0]
    if cnorm.shape != (ncart, ncart):
        raise ValueError("cnorm must be square (3N x 3N)")
    if evals.shape[0] != ncart:
        raise ValueError("evals must have length 3N")

    gammaall = np.sqrt(np.abs(evals))

    with p.open("w") as f:
        f.write("#\n")
        f.write("# Scaled Hessian eigenvectors (au) (rot and trasl at end):\n")
        f.write("#\n")
        for i in range(ncart):
            # NOTE: write COLUMNS as lines
            f.write(" ".join(f"{cnorm[j, i]:21.14e}" for j in range(ncart)) + "\n")

        f.write("\n\n")
        f.write("# sqrt(|eigenvalues|) of scaled Hessian (au) (rot and trasl at end):\n")
        f.write(" ".join(f"{gammaall[i]:21.14e}" for i in range(ncart)) + "\n")

        f.write("\n\n")
        f.write("# eigenvalues of scaled Hessian (au) (rot and trasl at end):\n")
        f.write(" ".join(f"{evals[i]:21.14e}" for i in range(ncart)) + "\n")

def ffloat(s: str) -> float:
    return float(s.replace("D", "E").replace("d", "e"))


def read_xyz_geometry(path: str | Path):
    raw = Path(path).read_text().splitlines()
    nat = int(raw[0].split()[0])
    if len(raw) < 2 + nat:
        raise ValueError(f"XYZ file '{path}' is too short: expected {2+nat} lines, got {len(raw)}")
    symb = []
    coords = np.zeros((nat, 3), dtype=float)
    for i in range(nat):
        parts = raw[2 + i].split()
        symb.append(parts[0])
        coords[i, :] = [float(parts[1]), float(parts[2]), float(parts[3])]
    return symb, coords.reshape(-1)  # flattened

def write_geom_xyz(path: str | Path, symb, x_ang_flat: np.ndarray, comment: str = "Geometry"):
    nat = len(symb)
    x = x_ang_flat.reshape(nat, 3)
    out = [f"{nat}\n", comment + "\n"]
    for i in range(nat):
        out.append(f"{symb[i]:2s}  {x[i,0]:14.8f}  {x[i,1]:14.8f}  {x[i,2]:14.8f}\n")
    Path(path).write_text("".join(out))

def build_cart_masses(symb):
    try:
        amass = np.array([MASS_AU[s] for s in symb], dtype=float)
    except KeyError as e:
        raise ValueError(f"Unknown atom symbol '{e.args[0]}' (not in MASS_AU).") from None
    return np.repeat(amass, 3)  # x,y,z masses

def shift_coords_to_com(mass_cart: np.ndarray, q: np.ndarray) -> np.ndarray:
    """
    Shift coordinates to the center of mass (in-place).
    q is flattened 3N, any length unit (Angstrom).
    Returns the COM vector that was subtracted (same unit as q).
    """
    nat = q.size // 3
    m_atom = mass_cart[2::3]  # one per atom
    q3 = q.reshape(nat, 3)
    com = (m_atom[:, None] * q3).sum(axis=0) / m_atom.sum()
    q3[:] -= com
    return com


def read_hessian_nwchem(path: str | Path, ncart: int) -> np.ndarray:
    """
    - Skip first two lines (NWChem style)
    - Then lower triangle values, one number per line in nested i,j loops
    """
    lines = Path(path).read_text().splitlines()
    data = lines[2:]
    hc = np.zeros((ncart, ncart), dtype=float)

    t = 0
    for i in range(ncart):
        for j in range(i + 1):
            val = ffloat(data[t].split()[0])
            hc[i, j] = val
            hc[j, i] = val
            t += 1
    return hc


# =========================
# Rotation removal
# =========================
def inertia_tensor(mass_cart: np.ndarray, q: np.ndarray) -> np.ndarray:
    nat = q.size // 3
    iten = np.zeros((3, 3), dtype=float)
    for i in range(nat):
        m = mass_cart[3*i + 2]
        x, y, z = q[3*i:3*i+3]
        iten[0, 0] += m * (y*y + z*z)
        iten[1, 1] += m * (z*z + x*x)
        iten[2, 2] += m * (x*x + y*y)
        iten[0, 1] -= m * x * y
        iten[0, 2] -= m * x * z
        iten[1, 2] -= m * y * z
    iten[1, 0] = iten[0, 1]
    iten[2, 0] = iten[0, 2]
    iten[2, 1] = iten[1, 2]
    return iten


def trframe(vec_cart: np.ndarray, nvec: np.ndarray) -> None:
    nat = vec_cart.size // 3
    for i in range(nat):
        pt = vec_cart[3*i:3*i+3]
        vec_cart[3*i:3*i+3] = nvec.T @ pt


def angmnt(mass_cart: np.ndarray, q: np.ndarray, v: np.ndarray) -> np.ndarray:
    nat = q.size // 3
    J = np.zeros(3, dtype=float)
    for i in range(nat):
        m = mass_cart[3*i + 2]
        x, y, z = q[3*i:3*i+3]
        vx, vy, vz = v[3*i:3*i+3]
        J[0] += m * (y*vz - z*vy)
        J[1] += m * (z*vx - x*vz)
        J[2] += m * (x*vy - y*vx)
    return J


def rotfreq(idia: np.ndarray, J: np.ndarray) -> np.ndarray:
    omega = np.zeros(3, dtype=float)
    for i in range(3):
        omega[i] = J[i] / idia[i] if idia[i] > 1.0e-3 else 0.0
    return omega


def zeroJ(mass_cart: np.ndarray, idia: np.ndarray, q: np.ndarray, v: np.ndarray) -> None:
    J = angmnt(mass_cart, q, v)
    omega = rotfreq(idia, J)

    nat = q.size // 3
    wx, wy, wz = omega
    for i in range(nat):
        x, y, z = q[3*i:3*i+3]
        vx, vy, vz = v[3*i:3*i+3]
        v[3*i + 0] = vx + (y*wz - z*wy)
        v[3*i + 1] = vy + (z*wx - x*wz)
        v[3*i + 2] = vz + (x*wy - y*wx)


def paframe(mass_cart: np.ndarray, q: np.ndarray):
    iten = inertia_tensor(mass_cart, q)
    idia, nvec = np.linalg.eigh(iten)
    trframe(q, nvec)
    return nvec, idia


def nilrot(mass_cart: np.ndarray, q: np.ndarray, v: np.ndarray) -> None:
    nvec, idia = paframe(mass_cart, q)
    trframe(v, nvec)
    zeroJ(mass_cart, idia, q, v)
    trframe(q, nvec.T)
    trframe(v, nvec.T)


def calc_kine_2(mass_cart: np.ndarray, v: np.ndarray) -> float:
    return 0.5 * np.sum(mass_cart * (v * v))


def scale_kine(mass_cart: np.ndarray, v: np.ndarray, ke_target: float) -> None:
    ke = calc_kine_2(mass_cart, v)
    factor = np.sqrt(ke_target / ke) if ke > 0 else 1.0
    v *= factor


# =========================
# EISPACK diagonalizer
# =========================
def _pythag(a, b):
    p = max(abs(a), abs(b))
    if p == 0.0:
        return 0.0
    r = (min(abs(a), abs(b)) / p) ** 2
    while True:
        t = 4.0 + r
        if t == 4.0:
            return p
        s = r / t
        u = 1.0 + 2.0 * s
        p = u * p
        r = (s / u) ** 2 * r


def _tred2(a):
    a = np.array(a, dtype=np.float64, copy=True)
    n = a.shape[0]
    z = np.zeros((n, n), dtype=np.float64)
    d = np.zeros(n, dtype=np.float64)
    e = np.zeros(n, dtype=np.float64)

    for i in range(n):
        for j in range(i, n):
            z[j, i] = a[j, i]
        d[i] = a[n - 1, i]

    if n == 1:
        z[n - 1, n - 1] = 1.0
        e[0] = 0.0
        return d, e, z

    for ii in range(1, n):
        i = n - ii
        l = i - 1
        h = 0.0
        scale = 0.0

        if l >= 1:
            for k in range(0, l + 1):
                scale += abs(d[k])

        if l < 1 or scale == 0.0:
            e[i] = d[l] if l >= 0 else 0.0
            for j in range(0, l + 1):
                d[j] = z[l, j]
                z[i, j] = 0.0
                z[j, i] = 0.0
            d[i] = h
            continue

        for k in range(0, l + 1):
            d[k] /= scale
            h += d[k] * d[k]

        f = d[l]
        g = -np.copysign(np.sqrt(h), f)
        e[i] = scale * g
        h = h - f * g
        d[l] = f - g

        for j in range(0, l + 1):
            e[j] = 0.0

        for j in range(0, l + 1):
            f = d[j]
            z[j, i] = f
            g = e[j] + z[j, j] * f
            jp1 = j + 1
            if jp1 <= l:
                for k in range(jp1, l + 1):
                    g += z[k, j] * d[k]
                    e[k] += z[k, j] * f
            e[j] = g

        f = 0.0
        for j in range(0, l + 1):
            e[j] /= h
            f += e[j] * d[j]

        hh = f / (h + h)

        for j in range(0, l + 1):
            e[j] -= hh * d[j]

        for j in range(0, l + 1):
            f = d[j]
            g = e[j]
            for k in range(j, l + 1):
                z[k, j] = z[k, j] - f * e[k] - g * d[k]
            d[j] = z[l, j]
            z[i, j] = 0.0

        d[i] = h

    for i in range(1, n):
        l = i - 1
        z[n - 1, l] = z[l, l]
        z[l, l] = 1.0
        h = d[i]
        if h != 0.0:
            for k in range(0, l + 1):
                d[k] = z[k, i] / h
            for j in range(0, l + 1):
                g = 0.0
                for k in range(0, l + 1):
                    g += z[k, i] * z[k, j]
                for k in range(0, l + 1):
                    z[k, j] = z[k, j] - g * d[k]
        for k in range(0, l + 1):
            z[k, i] = 0.0

    for i in range(n):
        d[i] = z[n - 1, i]
        z[n - 1, i] = 0.0
    z[n - 1, n - 1] = 1.0
    e[0] = 0.0
    return d, e, z


def _tql2(d, e, z):
    d = np.array(d, dtype=np.float64, copy=True)
    e = np.array(e, dtype=np.float64, copy=True)
    z = np.array(z, dtype=np.float64, copy=True)
    n = d.size
    if n == 1:
        return d, z

    for i in range(1, n):
        e[i - 1] = e[i]
    e[n - 1] = 0.0

    f = 0.0
    tst1 = 0.0

    for l in range(0, n):
        j = 0
        h = abs(d[l]) + abs(e[l])
        if tst1 < h:
            tst1 = h

        m = l
        while True:
            tst2 = tst1 + abs(e[m])
            if tst2 == tst1:
                break
            m += 1
            if m >= n:
                break

        if m == l:
            d[l] = d[l] + f
            continue

        while True:
            if j == 30:
                raise RuntimeError(f"tql2 did not converge for l={l+1}.")
            j += 1

            l1 = l + 1
            l2 = l1 + 1

            g = d[l]
            p = (d[l1] - g) / (2.0 * e[l])
            r = _pythag(p, 1.0)
            d[l] = e[l] / (p + np.copysign(r, p))
            d[l1] = e[l] * (p + np.copysign(r, p))
            dl1 = d[l1]
            h = g - d[l]

            if l2 < n:
                d[l2:n] -= h

            f += h

            p = d[m]
            c = 1.0
            c2 = 1.0
            el1 = e[l1]
            s = 0.0
            mml = m - l

            for ii in range(1, mml + 1):
                c3 = c2
                c2 = c
                s2 = s
                i = m - ii

                g = c * e[i]
                h = c * p
                r = _pythag(p, e[i])
                e[i + 1] = s * r
                s = e[i] / r
                c = p / r
                p = c * d[i] - s * g
                d[i + 1] = h + s * (c * g + s * d[i])

                zi1 = z[:, i + 1].copy()
                zi = z[:, i].copy()
                z[:, i + 1] = s * zi + c * zi1
                z[:, i] = c * zi - s * zi1

            p = -s * s2 * c3 * el1 * e[l] / dl1
            e[l] = s * p
            d[l] = c * p

            tst2 = tst1 + abs(e[l])
            if tst2 <= tst1:
                d[l] = d[l] + f
                break

    for ii in range(1, n):
        i = ii - 1
        k = i
        p = d[i]
        for j in range(ii, n):
            if d[j] < p:
                k = j
                p = d[j]
        if k != i:
            d[k] = d[i]
            d[i] = p
            z[:, [i, k]] = z[:, [k, i]]

    return d, z


def eispack_rs(a):
    d, e, z = _tred2(a)
    w, z = _tql2(d, e, z)
    return w, z


# =========================
# cnorm cleaning (roto-trans enforced)
# =========================
def _mgs_columns(A: np.ndarray, tol: float = 1e-12) -> np.ndarray:
    """Modified Gram-Schmidt orthonormalization of the *columns* of A."""
    n, k = A.shape
    Qcols = []
    for j in range(k):
        v = A[:, j].astype(float, copy=True)
        for q in Qcols:
            v -= q * float(np.dot(q, v))
        nrm = float(np.linalg.norm(v))
        if nrm > tol:
            Qcols.append(v / nrm)
    if len(Qcols) == 0:
        return np.zeros((n, 0), dtype=float)
    return np.stack(Qcols, axis=1)


def clean_cnorm_gs(mw: np.ndarray, cnorm_vibfirst: np.ndarray, nrotrasl: int,
                   tol: float = 1e-12) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Clean normal modes by:
      1) taking the roto-trans subspace from cnorm (last nrotrasl columns, because cnorm is vib-first),
      2) orthonormalizing it (modified Gram-Schmidt),
      3) constructing an orthonormal vibrational basis orthogonal to roto-trans,
      4) projecting mw onto the vibrational subspace and diagonalizing it,
      5) returning:
         - ww_clean: length 3N, first nrotrasl eigenvalues forced to 0, remaining are cleaned vib eigenvalues
         - cnorm_clean: vib-first eigenvectors (3N x 3N): [vib_modes | roto-trans_basis]
         - gamma_clean: sqrt(abs(vib_eigs_clean)) (length 3N-nrotrasl)
    """
    ncart = mw.shape[0]
    nvib = ncart - nrotrasl
    if cnorm_vibfirst.shape != (ncart, ncart):
        raise ValueError("cnorm_vibfirst must be 3N x 3N")

    # Split columns: vib first, roto-trans last
    C_v0 = cnorm_vibfirst[:, :nvib]
    C_rt0 = cnorm_vibfirst[:, nvib:]

    # (A) Orthonormal roto-trans basis
    Q_rt = _mgs_columns(C_rt0, tol=tol)
    if Q_rt.shape[1] != nrotrasl:
        # Fallback: stable orthonormalization
        Q_rt, _ = np.linalg.qr(C_rt0)
        Q_rt = Q_rt[:, :nrotrasl]

    # (B) Build an orthonormal vibrational basis orthogonal to Q_rt
    V = C_v0 - Q_rt @ (Q_rt.T @ C_v0)
    Q_v = _mgs_columns(V, tol=tol)

    if Q_v.shape[1] != nvib:
        # If Gram-Schmidt loses rank (e.g., near-degeneracies), build the complement via QR-complete
        Qfull, _ = np.linalg.qr(Q_rt, mode="complete")
        Q_v = Qfull[:, nrotrasl:]  # ncart x nvib

    # (C) Project mw into vibrational subspace and diagonalize
    Hv = Q_v.T @ mw @ Q_v
    w_v, U = eispack_rs(Hv)  # ascending
    C_v = Q_v @ U            # cleaned vib eigenvectors in full space

    # (D) Assemble cleaned full set (vib-first)
    cnorm_clean = np.zeros((ncart, ncart), dtype=float)
    cnorm_clean[:, :nvib] = C_v
    cnorm_clean[:, nvib:] = Q_rt

    ww_clean = np.zeros(ncart, dtype=float)
    ww_clean[:nrotrasl] = 0.0
    ww_clean[nrotrasl:] = w_v

    gamma_clean = np.sqrt(np.abs(w_v))
    return ww_clean, cnorm_clean, gamma_clean


# =========================
# Core
# =========================
def diagonalize_mass_weighted_hessian(hc: np.ndarray, xm: np.ndarray, nvib: int, clean: bool = False):
    """
    Build mass-weighted Hessian, diagonalize it, and reorder eigenvectors to vib-first.
    If clean=True, enforce roto-trans eigenvalues = 0 and re-diagonalize the vibrational subspace
    using Gram-Schmidt projection (see clean_cnorm_gs).
    """
    ncart = hc.shape[0]
    nrotrasl = ncart - nvib

    mw = hc / np.sqrt(np.outer(xm, xm))
    ww, cnorm = eispack_rs(mw)  # ww ascending; cnorm columns

    # Reorder eigenvectors: vib modes (last nvib) to the first nvib columns
    tmp = np.zeros_like(cnorm)
    tmp[:, :nvib] = cnorm[:, ncart - nvib:]
    tmp[:, nvib:] = cnorm[:, :ncart - nvib]
    cnorm_vibfirst = tmp

    if clean:
        ww_clean, cnorm_clean, gamma_clean = clean_cnorm_gs(mw, cnorm_vibfirst, nrotrasl)
        return ww_clean, cnorm_clean, gamma_clean

    vib_eigs = ww[ncart - nvib:]
    gamma = np.sqrt(np.abs(vib_eigs))
    return ww, cnorm_vibfirst, gamma



def generate_initial_velocities(xm, x_bohr, gamma, cnorm, nexc, nNOener):
    ncart = xm.size
    nvib = gamma.size

    P = np.zeros(ncart, dtype=float)
    for i in range(nvib):
        if nNOener[i] == 0:
            P[i] = np.sqrt(gamma[i]) * np.sqrt(2.0 * float(nexc[i]) + 1.0)
        # else: P[i]=0

    Pc = cnorm @ P
    vel = Pc / np.sqrt(xm)

    Ekin = calc_kine_2(xm, vel)

    q = x_bohr.copy()
    v = vel.copy()
    nilrot(xm, q, v)
    scale_kine(xm, v, Ekin)
    return v


def write_vel_xyz(path: str | Path, symb, v_au: np.ndarray):
    nat = len(symb)
    out = [f"{nat}\n", "Velocities (a.u.)\n"]
    #fmt = "{:2s}  {:14.8f}  {:14.8f}  {:14.8f}\n"
    fmt = "{:2s}  {: .16e}  {: .16e}  {: .16e}\n"
    for i in range(nat):
        vx, vy, vz = v_au[3*i:3*i+3].tolist()
        out.append(fmt.format(symb[i], vx, vy, vz))
    Path(path).write_text("".join(out))

def convert_vel_file_to_bohr_s(inpath: str | Path, outpath: str | Path,
                               precision: int = 16) -> None:
    """
    Convert a VEGETA velocity xyz file from bohr/(a.u. time) to bohr/s.
    """
    fmt = f"{{: .{precision}e}} {{: .{precision}e}} {{: .{precision}e}}\n"
    inpath = str(inpath)
    outpath = str(outpath)

    with open(inpath, "r") as inf, open(outpath, "w") as outf:
        lines = inf.readlines()

        if len(lines) >= 1:
            outf.write(lines[0])  # nat
        if len(lines) >= 2:
            comment = lines[1].rstrip("\n")
            if "bohr/s" not in comment:
                comment = comment + "   (converted to bohr/s)"
            outf.write(comment + "\n")

        for line in lines[2:]:
            stripped = line.strip()
            if not stripped:
                outf.write(line)
                continue

            toks = stripped.split()
            if len(toks) >= 4:
                try:
                    vx = float(toks[-3]); vy = float(toks[-2]); vz = float(toks[-1])
                    prefix = " ".join(toks[:-3])

                    vx_s = vx * AU_VEL_TO_BOHR_S
                    vy_s = vy * AU_VEL_TO_BOHR_S
                    vz_s = vz * AU_VEL_TO_BOHR_S

                    outf.write(f"{prefix:8s} " + fmt.format(vx_s, vy_s, vz_s))
                    continue
                except ValueError:
                    pass

            outf.write(line)


def write_mode_xyz_files(prefix_path: str | Path, symb, x_ang_flat: np.ndarray,
                         cnorm_vib: np.ndarray, xm: np.ndarray, freqs_cm1: np.ndarray,
                         scale_target_ang: float = 0.10,
                         nframes: int = 21, ncycles: int = 1):
    """
    Writes one multi-frame xyz "movie" per vibrational mode:
      <prefix>_mode_###.xyz

    Each file contains nframes*ncycles frames (XYZ concatenated).
    Displacement direction:
      dq = cnorm / sqrt(mass)
    """
    nat = len(symb)
    x_ang = x_ang_flat.reshape(nat, 3)

    base = Path(prefix_path)
    stem = base.stem
    parent = base.parent if str(base.parent) != "" else Path(".")

    nvib = cnorm_vib.shape[1]
    total_frames = max(1, int(nframes) * max(1, int(ncycles)))
    phases = np.linspace(0.0, 2.0*np.pi*max(1, int(ncycles)), total_frames, endpoint=False)

    for k in range(nvib):
        disp_cart = (cnorm_vib[:, k] / np.sqrt(xm)).reshape(nat, 3)

        maxabs = float(np.max(np.abs(disp_cart)))
        s = (scale_target_ang / maxabs) if maxabs > 0 else 1.0

        fname = parent / f"{stem}_mode_{k+1:03d}.xyz"
        out = []

        for iframe, phi in enumerate(phases, start=1):
            amp = np.sin(phi)  # oscillates + / - and returns smoothly
            coords = x_ang + (s * amp) * disp_cart

            comment = (f"mode {k+1:03d}  freq(cm^-1)={freqs_cm1[k]:.6f}  "
                       f"scale(A)={s:.6e}  frame={iframe}/{total_frames}  phase={phi:.6f}")

            out.append(f"{nat}\n")
            out.append(comment + "\n")
            for i in range(nat):
                out.append(f"{symb[i]:2s}  {coords[i,0]:14.8f}  {coords[i,1]:14.8f}  {coords[i,2]:14.8f}\n")

        fname.write_text("".join(out))

#def write_freq_dat(path: str | Path, ww: np.ndarray, vel_out: str | Path) -> None:
#    freqs_cm1_all = np.sqrt(np.abs(ww)) * TOCM
#    p = Path(path)
#    out = []
#    out.append("Frequencies including rot/trans (cm^-1):\n")
#    for i, f in enumerate(freqs_cm1_all, start=1):
#        out.append(f"  omega({i:3d}) = {f:15.6f}\n")
#    out.append(f"\nVelocities printed in: {vel_out}\n")
#    p.write_text("".join(out))
def write_freq_dat(path: str | Path, ww: np.ndarray, vel_out: str | Path,
                   gamma_vib: np.ndarray | None = None,
                   nNOener: np.ndarray | None = None) -> None:
    freqs_cm1_all = np.sqrt(np.abs(ww)) * TOCM

    p = Path(path)
    out = []
    out.append("Frequencies including rot/trans (cm^-1):\n")
    for i, f in enumerate(freqs_cm1_all, start=1):
        out.append(f"  omega({i:3d}) = {f:15.6f}\n")

    # ---------- ZPE ----------
    if gamma_vib is not None:
        zpe_eh_all = 0.5 * float(np.sum(gamma_vib))
        zpe_cm1_all = zpe_eh_all * TOCM

        out.append("\nHarmonic zero-point energy (ZPE):\n")
        out.append(f"  ZPE_all   (Eh)   = {zpe_eh_all: .12e}\n")
        out.append(f"  ZPE_all   (cm^-1)= {zpe_cm1_all: .6f}\n")

        # If you switched off modes, also print ZPE over active modes only
        if nNOener is not None and len(nNOener) == len(gamma_vib):
            mask = (nNOener == 0)
            zpe_eh_act = 0.5 * float(np.sum(gamma_vib[mask]))
            zpe_cm1_act = zpe_eh_act * TOCM
            out.append(f"  ZPE_active(Eh)   = {zpe_eh_act: .12e}\n")
            out.append(f"  ZPE_active(cm^-1)= {zpe_cm1_act: .6f}\n")

        # optional unit conversions (only if you added constants)
        try:
            out.append(f"  ZPE_all   (kJ/mol)= {zpe_eh_all * EH_TO_KJMOL: .6f}\n")
            out.append(f"  ZPE_all   (kcal/mol)= {zpe_eh_all * EH_TO_KCALMOL: .6f}\n")
        except NameError:
            pass
    # -------------------------

    out.append(f"\nVelocities printed in: {vel_out}\n")
    p.write_text("".join(out))

# =========================
def parse_args():
    p = argparse.ArgumentParser(description="Generate initial velocities from flat Hessian.")
    #p.add_argument("-N", "--nat", type=int, required=True, help="Number of atoms")
    p.add_argument("--nrotrasl", type=int, default=6, choices=[5, 6],
                   help="Number of roto-trans modes to remove (default 6; use 5 for linear molecules)")
    p.add_argument("--off", nargs="*", type=str, default=[],
                   help="Vibrational modes to switch off (1-based). Supports ranges: 1-5, 10..12, 20:22 and commas")
    p.add_argument("--on", nargs="*", type=str, default=[],
                   help="Vibrational modes to excite by +1 quantum (1-based). Supports ranges: 1-5, 10..12, 20:22 and commas")
    p.add_argument("-H", "--hessian", required=False, help="Hessian flat file")
    p.add_argument("--xyz", required=True, help="Geometry .xyz file (Angstrom)")
    p.add_argument("-o", "--output", default="velocity.xyz", help="Output velocity .xyz (a.u.)")
    p.add_argument("--print", dest="print_modes", type=int, choices=[0, 1], default=0,
                   help="0/1: write normal mode xyz files")
    p.add_argument("--clean-cnorm", type=int, choices=[0, 1], default=0,
                   help="0/1: clean cnorm by forcing roto-trans eigenvalues to 0 and re-diagonalizing the vib subspace (Gram-Schmidt)")
    p.add_argument("--cnorm-out", default=None, help="Write cnorm eigenvector matrix to this file (text).")
    # Geometry-only / PA frame output
    p.add_argument("--geo-only", action="store_true",
                   help="Geometry-only mode: only write Center of Mass COM-shifted + principal-axes geometry and exit")
    p.add_argument("--pa-xyz", default=None,
                   help="Write COM-shifted + principal-axes geometry to this xyz file (Angstrom)")
    #Convertion:
    p.add_argument("--gau-vel", action="store_true",
            help="Also write velocities converted to bohr/s. Output name: <output_stem>_gau.xyz")
    #Atoms OFF:
    p.add_argument("--zero-vel-atoms", nargs="*", type=str, default=[], help="Atom indices (1-based) to force to zero velocity. Supports ranges: 1-5, 10..12, 20:22 and commas")

    #NModes OFF soglia:
    p.add_argument("--freq-thresh", type=float, default=None, help="Switch off all vibrational modes with |harmonic freq| < this threshold (cm^-1).")

    return p.parse_args()


def main():
    args = parse_args()
    #nat = args.nat

    # Geometry and masses
    #symb, x_ang = read_xyz_geometry(args.xyz, nat)
    symb, x_ang = read_xyz_geometry(args.xyz)
    nat = len(symb)
    xm = build_cart_masses(symb)

    # If requested, write COM-shifted + PA-frame geometry (can be used in any mode)
    if args.geo_only or (args.pa_xyz is not None):
        x_pa = x_ang.copy()  # Angstrom
        com = shift_coords_to_com(xm, x_pa)
        _nvec, idia = paframe(xm, x_pa)  # rotates x_pa in-place into PA frame

        # choose default output name if not provided
        if args.pa_xyz is None:
            xyzp = Path(args.xyz)
            pa_out = xyzp.with_name(xyzp.stem + "_pa.xyz")
        else:
            pa_out = Path(args.pa_xyz)

        comment = f"COM shifted and rotated to principal axes; COM(Ang)={com[0]:.6f} {com[1]:.6f} {com[2]:.6f}"
        write_geom_xyz(pa_out, symb, x_pa, comment=comment)

        if args.geo_only:
            # Geometry-only mode: stop here
            return


    # From here on: full velocity generation requires Hessian
    if not args.hessian:
        raise ValueError("Missing -H/--hessian (required unless --geo-only is used).")

    nrotrasl = args.nrotrasl
    ncart = 3 * nat
    nvib = ncart - nrotrasl
    if nvib <= 0:
        raise ValueError(f"Invalid nvib={nvib}. Check -N and --nrotrasl.")

    # Geometry and masses
#    symb, x_ang = read_xyz_geometry(args.xyz, nat)
#    xm = build_cart_masses(symb)

    # Mode selection arrays
    nexc = np.zeros(nvib, dtype=int)      # quanta per mode
    nNOener = np.zeros(nvib, dtype=int)   # 1 => switch off (P=0)

    # Expand and apply excitations / switches-off (supports ranges)
    on_modes = expand_mode_tokens(args.on, nvib) if args.on else []
    off_modes = expand_mode_tokens(args.off, nvib) if args.off else []

    for m in on_modes:
        nexc[m - 1] = 1

    # switches off win over on
    for m in off_modes:
        nNOener[m - 1] = 1
        nexc[m - 1] = 0

    # Convert geometry to Bohr for rotation removal
    x_bohr = x_ang.copy() * ANG2BOHR

    # Hessian: (triang)
    hc = read_hessian_nwchem(args.hessian, ncart)

    # Diagonalize and build gamma/cnorm
    ww, cnorm, gamma = diagonalize_mass_weighted_hessian(hc, xm, nvib, clean=(args.clean_cnorm == 1))

    if args.freq_thresh is not None:
        # gamma is omega_v in a.u. for the vibrational modes (length nvib)
        freqs_vib_cm1 = gamma * TOCM
        low = np.where(freqs_vib_cm1 < args.freq_thresh)[0]
        if low.size > 0:
            nNOener[low] = 1   # switch off
            nexc[low] = 0      # off wins over on

    if args.cnorm_out:
        ncart = 3 * nat
        nrotrasl = args.nrotrasl
        nvib = ncart - nrotrasl
        # IMPORTANT: eigenvalues must be in the SAME order as cnorm columns (vib-first, rt last)
        if args.clean_cnorm == 1:
            # ww_clean is [rt zeros | vib eigs], but cnorm is [vib | rt]
            evals_out = np.concatenate([ww[nrotrasl:], ww[:nrotrasl]])
        else:
            # ww is ascending; cnorm was reordered to [vib(last nvib) | rt(first nrotrasl)]
            evals_out = np.concatenate([ww[ncart - nvib:], ww[:ncart - nvib]])
        write_cnorm(args.cnorm_out, evals_out, cnorm)

    # Generate velocities (a.u.)
    v_au = generate_initial_velocities(xm, x_bohr, gamma, cnorm, nexc, nNOener)

    if args.zero_vel_atoms:
        freeze_atoms = expand_atom_tokens(args.zero_vel_atoms, nat)
        for a in freeze_atoms:
            i0 = 3 * (a - 1)
            v_au[i0:i0+3] = 0.0

    # Write velocities
    write_vel_xyz(args.output, symb, v_au)

    if args.gau_vel:
        outp = Path(args.output)
        gau_out = outp.with_name(outp.stem + "_gau.xyz")
        convert_vel_file_to_bohr_s(outp, gau_out, precision=16)
        print(f"Wrote converted velocities (bohr/s) to: {gau_out}")
    # Frequencies printout
#    freqs_cm1_all = np.sqrt(np.abs(ww)) * TOCM
#    print("Frequencies including rot/trans (cm^-1):")
#    for i, f in enumerate(freqs_cm1_all, start=1):
#        print(f"  omega({i:3d}) = {f:15.6f}")
#    print(f"\nVelocities printed in: {args.output}")

    freq_path = Path(args.output).with_suffix("").with_name("freq.dat")
    write_freq_dat(freq_path, ww, args.output, gamma_vib=gamma, nNOener=nNOener)
    #write_freq_dat(freq_path, ww, args.output)

    freqs_cm1_all = np.sqrt(np.abs(ww)) * TOCM

    # Optional: write mode xyz files (vibrational modes only)
    if args.print_modes == 1:
        freqs_cm1_vib = freqs_cm1_all[ncart - nvib:]  # last nvib are vibrational
        cnorm_vib = cnorm[:, :nvib]                   # vib columns first
        write_mode_xyz_files(args.output, symb, x_ang, cnorm_vib, xm, freqs_cm1_vib)
        print(f"Wrote {nvib} normal-mode xyz files with prefix based on: {args.output}")


if __name__ == "__main__":
    main()

