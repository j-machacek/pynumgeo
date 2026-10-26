# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#                                                pynumgeo
#                              Python API for the finite element code numgeo
#                                     Copyright (C) 2026 Jan Machacek
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#
# Author: Jan Machacek
#
# pynumgeo writes, checks and runs numgeo input files and reads numgeo results. It follows the
# development of numgeo: new developments in the numgeo source code are taken over into the API, and a
# CI pipeline tests every change.
#
# License: BSD-3-Clause, see LICENSE.
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""Reader for numgeo's print output (``*Output, print``), ``<job>-print-out/<SET>_<kind>_<n>.dat``.

Everything below is taken from ``src/output/print_type.f90`` (cited as ``:line``).

**Files.** ``<SET>_node_<n>.dat``, ``<SET>_element_<n>.dat``, ``<SET>_ip_<n>.dat`` (:125, :172, :219).
``<SET>`` is the set name as stored by numgeo: upper case, ``INSTANCE.SET`` for sets of an instance
(``src/input/read_part_.f90:246,263``). ``<n>`` is the set member (I0): the node label for node sets, the
element *position* in the order of definition for element sets (equal to the label for meshes numbered
1..n, which pynumgeo writes). Each file is created once, with the header of the **first** step/card
that defines it (:114-248); all later steps append rows built from their *own* variable list (:384).

**Rows.** Node and element files: ``(E14.9, *(E15.6))`` = total time and values (:387, :449); the time
column has no leading zero (``.100000000E+01``). Integration-point files: ``(E15.9, *(E15.6))`` (:514).
Values with a 3-digit exponent drop the ``E`` (``0.123456-100``). A node gets **no row** when none of the
requested variables exists there (:387).

**Column order is the order of the code, not of the input**; keys the code does not know are ignored.

Node rows (``print_get_output_array_node``, :582-983)::

    COORDS X1 X2 X3 | U U1 U2 U3 | UR UR1-3 | U_ACC U1_ACC-U3_ACC | V V1-3 | A A1-3 | PW Pw* | CC Cc* |
    TEMP Temp* | DTEMP dTemp* | TEMP_RATE Temp_rate* | RFL RFL* | PA Pa | RPW RPW* | RPA RPA* |
    RF RF1-3 | RM RM1-3 | CONTACT (2D 5, 3D 7 columns)* (+ Normal water stress*) |
    CONTACT_SDV 13 columns* (+ 6 HCA columns*) | CON_F Connector force | FDYN FDYN1-3

Vector variables always have 3 columns (0 in 2D). The header (:1535-1645) lists ``FDYN`` before
``CONTACT``; the data has it last (:967-983), and so does this reader. Columns marked ``*`` are omitted in
the data while the header keeps them: ``Pw``/``RPW`` at nodes without pore water pressure dof, ``Cc``
without concentration dof, ``Temp``/``dTemp``/``Temp_rate``/``RFL`` without temperature dof, ``RPA``
without pore air pressure dof (:681-764), the contact columns at nodes outside a paired contact surface
(:797-921). The reader drops such columns when exactly one combination of these conditions explains the
row width, and reports it in :attr:`PrintSeries.issues`; otherwise it raises :class:`PrintFormatError`
(pass ``columns=`` then).

Element rows (``print_get_output_array_element``, :1049-1302): mean over the integration points::

    COORDS_IGP(_UPD) 3 per IP | COORDS(_UPD) X1 X2 X3 | S_IGP 6 per IP |
    S STRESS11 STRESS22 STRESS33 STRESS12 STRESS13 STRESS23 |
    E STRAIN11 STRAIN22 STRAIN33 STRAIN12 STRAIN13 STRAIN23 | STRAIN-HENCKY 6 | F F11 F12 F13 F21 .. F33 |
    VOID | DELTA-T | DELTA-PW | element and material variables in input order

The element ``STRAIN-HENCKY`` columns are not the mean Hencky strain (:1170-1189); the reader
adds a warning issue. The header labels the strain shear columns ``STRAIN12 STRAIN23 STRAIN13`` (:1682)
while the data is numgeo's Voigt order ``[11, 22, 33, 12, 13, 23]``: the reader names the columns
in data order. ``COORDS_IGP``/``S_IGP`` write 3/6 columns per integration point under one header group,
``COORDS_UPD`` without ``COORDS`` has no header group (:1658-1673); such files raise
:class:`PrintFormatError`.

Integration-point rows (``print_get_output_array_integration_point``, :1373-1451), per IP::

    x1 x2 x3 (always) | S 6 | E 6 | STRAIN-HENCKY 6 | F 9 | VOID | PHANTOM-ELASTICITY 6 |
    PHANTOM-VISCOSITY 6 | element and material variables in input order

with a two-line header in fields of 15 characters (``IP-<j>`` and the names, :1837-1846); names are cut
to 15 characters (:1525).

Tensor columns are ``[11, 22, 33, 12, 13, 23]`` (zero-padded in 2D); strain shear columns are
**engineering** shear strains. The node/element header line is a 500-character variable (:1524):
longer headers are cut, which the reader reports.

Examples:
    >>> import pathlib, tempfile
    >>> f = pathlib.Path(tempfile.mkdtemp()) / "LOAD_node_2.dat"
    >>> _ = f.write_text(
    ...     "    Time             U1             U2             U3\\n"
    ...     ".100000000E+01   0.000000E+00  -0.152739E-01   0.000000E+00\\n")
    >>> s = read_print_file(f)
    >>> s.columns, s.time.tolist(), float(s.column("U2")[-1])
    (['U1', 'U2', 'U3'], [1.0], -0.0152739)
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np
import numpy.typing as npt

from pynumgeo.results._fortran import parse_result_reals

if TYPE_CHECKING:
    from pynumgeo.issue import Issue, Severity

__all__ = [
    "PrintFileInfo",
    "PrintFormatError",
    "PrintKind",
    "PrintSeries",
    "list_print_files",
    "read_print_blocks",
    "read_print_file",
    "read_print_rows",
]

PrintKind = Literal["node", "element", "ip"]
FloatArray = npt.NDArray[np.float64]

_SRC = "src/output/print_type.f90"
_FILE_RE = re.compile(r"^(?P<set>.+)_(?P<kind>node|element|ip)_(?P<index>\d+)\.dat$")
_HEADER_LENGTH = 500  # character(len=500) :: header, print_type.f90:1524
_IP_FIELD = 15  # (A15,*(A15)), print_type.f90:1845-1846


class PrintFormatError(ValueError):
    """The rows of a print file cannot be matched to its header (see the module docstring)."""


@dataclass(frozen=True)
class PrintFileInfo:
    """A print file found in ``<job>-print-out/``.

    Attributes:
        set_name: set name as in the file name (upper case; ``INSTANCE.SET`` for instance sets).
        kind: ``node``, ``element`` or ``ip``.
        index: number in the file name: node label, or element position (= label for meshes numbered 1..n).
        path: the file.
    """

    set_name: str
    kind: PrintKind
    index: int
    path: Path


@dataclass(frozen=True, eq=False)
class PrintSeries:
    """Contents of one print file.

    Attributes:
        columns: names of the value columns in data order (time excluded).
        time: total time of each row.
        values: ``(rows, len(columns))``.
        path: the file.
        kind: ``node``, ``element`` or ``ip``.
        ip: integration point of each column (``ip`` files), ``None`` otherwise.
        header: names as written in the header (time excluded), for reference.
        issues: what the reader had to interpret (dropped columns, header deviations).
    """

    columns: list[str]
    time: FloatArray
    values: FloatArray
    path: Path
    kind: PrintKind
    ip: tuple[int, ...] | None = None
    header: tuple[str, ...] = ()
    issues: tuple[Issue, ...] = field(default=())

    def column(self, name: str, ip: int | None = None) -> FloatArray:
        """Values of one column; the name is matched exactly, else case-insensitively.

        Args:
            name: column name (e.g. ``"U2"``, ``"STRESS11"``).
            ip: integration point (required for ``ip`` files).

        Raises:
            KeyError: no such column.
            ValueError: the name (and ``ip``) matches more than one column.
        """
        idx = [i for i, c in enumerate(self.columns) if c == name and self._ip_ok(i, ip)]
        if not idx:
            idx = [i for i, c in enumerate(self.columns) if c.casefold() == name.casefold() and self._ip_ok(i, ip)]
        if not idx:
            raise KeyError(f"no column {name!r}{'' if ip is None else f' at IP {ip}'} in {self.path}")
        if len(idx) > 1:
            hint = "; pass ip=" if self.ip is not None and ip is None else ""
            raise ValueError(f"column {name!r} is ambiguous in {self.path} ({len(idx)} columns){hint}")
        return self.values[:, idx[0]]

    def _ip_ok(self, i: int, ip: int | None) -> bool:
        return ip is None or (self.ip is not None and self.ip[i] == ip)


def list_print_files(directory: str | Path) -> list[PrintFileInfo]:
    """All files of a ``<job>-print-out`` folder named ``<SET>_<kind>_<n>.dat``, sorted by set, kind, n."""
    d = Path(directory)
    out: list[PrintFileInfo] = []
    for p in d.iterdir():
        m = _FILE_RE.match(p.name)
        if m and p.is_file():
            kind: PrintKind = m.group("kind")  # type: ignore[assignment]
            out.append(PrintFileInfo(m.group("set"), kind, int(m.group("index")), p))
    out.sort(key=lambda f: (f.set_name, f.kind, f.index))
    return out


def read_print_rows(path: str | Path) -> tuple[list[str], list[FloatArray]]:
    """Raw access: header lines and every data row (time first) as written.

    Node and element files have one header line, integration-point files two (decided from the file
    name; a file not named ``*_ip_<n>.dat`` is treated as a node/element file).
    """
    p = Path(path)
    lines = p.read_text(encoding="latin-1").splitlines()
    nheader = 2 if _kind_from_name(p) == "ip" else 1
    rows: list[FloatArray] = []
    for k, line in enumerate(lines[nheader:], start=nheader + 1):
        tokens = line.split()
        if not tokens:
            continue
        try:
            rows.append(parse_result_reals(tokens))
        except ValueError as exc:
            raise PrintFormatError(f"{p}:{k}: {exc}") from None
    return lines[:nheader], rows


def read_print_file(
    path: str | Path, *, kind: PrintKind | None = None, columns: Sequence[str] | None = None
) -> PrintSeries:
    """Read one print file.

    Args:
        path: the ``.dat`` file.
        kind: ``node``, ``element`` or ``ip``; default from the file name.
        columns: names of the value columns (time excluded) to use instead of the header; their number
            must equal the row width.

    Raises:
        PrintFormatError: rows of different widths (variables changed between steps; use
            :func:`read_print_blocks`), or rows that do not match the header.
    """
    p = Path(path)
    k = kind or _kind_from_name(p)
    if k is None:
        raise ValueError(f"{p}: kind not given and not recognisable from the file name")
    header_lines, rows = read_print_rows(p)
    widths = sorted({len(r) for r in rows})
    if len(widths) > 1:
        raise PrintFormatError(f"{p}: rows of different widths ({_describe_blocks(rows)}); {_RAGGED_HINT}")
    return _series(p, k, header_lines, rows, columns, None)


def read_print_blocks(path: str | Path, *, kind: PrintKind | None = None) -> list[PrintSeries]:
    """Read a print file whose row width changes, as one series per run of equal-width rows.

    numgeo writes the header once, for the variables of the first step that defines the file
    (:126-134), and the rows of each step with that step's variables (:384). Blocks that match the
    header are named from it; other blocks get the names ``col1``, ``col2``, ... and a warning issue.
    """
    p = Path(path)
    k = kind or _kind_from_name(p)
    if k is None:
        raise ValueError(f"{p}: kind not given and not recognisable from the file name")
    header_lines, rows = read_print_rows(p)
    out: list[PrintSeries] = []
    for _, group in itertools.groupby(rows, key=len):
        block = list(group)
        try:
            out.append(_series(p, k, header_lines, block, None, None))
        except PrintFormatError:
            issue = _issue(
                "NG-RESULT-004",
                "warning",
                f"{len(block)} rows with {len(block[0]) - 1} values do not match the header; columns named col1..colN",
                location=str(p),
                source=f"{_SRC}:126-134,384",
            )
            names = [f"col{i + 1}" for i in range(len(block[0]) - 1)]
            out.append(_series(p, k, header_lines, block, names, issue))
    return out


_RAGGED_HINT = "the header describes only the first block; use read_print_blocks()"


def _issue(id: str, severity: Severity, message: str, *, location: str, source: str) -> Issue:
    # imported here: pynumgeo.validation loads the validator and the deck model, which reading does not need
    from pynumgeo.issue import Issue

    return Issue(id, severity, message, location=location, source=source)


def _kind_from_name(p: Path) -> PrintKind | None:
    m = _FILE_RE.match(p.name)
    if m is None:
        return None
    kind: PrintKind = m.group("kind")  # type: ignore[assignment]
    return kind


def _describe_blocks(rows: list[FloatArray]) -> str:
    parts = []
    start = 0
    for width, group in itertools.groupby(rows, key=len):
        n = len(list(group))
        parts.append(f"rows {start + 1}-{start + n}: {width - 1} values")
        start += n
    return ", ".join(parts)


def _series(
    p: Path,
    kind: PrintKind,
    header_lines: list[str],
    rows: list[FloatArray],
    columns: Sequence[str] | None,
    extra_issue: Issue | None,
) -> PrintSeries:
    issues: list[Issue] = [] if extra_issue is None else [extra_issue]
    width = len(rows[0]) - 1 if rows else None
    ip: tuple[int, ...] | None = None
    if columns is not None:  # the caller's names; the header is kept for reference only
        header, names = _raw_header(kind, header_lines), list(columns)
    elif kind == "ip":
        header, ip = _ip_header(p, header_lines)
        names = list(header)
    elif kind == "node":
        header, names = _node_columns(p, header_lines, width, issues)
    else:
        header, names = _element_columns(p, header_lines, issues)
    if width is not None and len(names) != width:
        raise PrintFormatError(_mismatch_message(p, kind, len(names), width, columns is not None))
    data = np.array(rows, dtype=np.float64).reshape(len(rows), len(names) + 1)
    return PrintSeries(
        columns=names,
        time=data[:, 0].copy(),
        values=data[:, 1:].copy(),
        path=p,
        kind=kind,
        ip=ip,
        header=tuple(header),
        issues=tuple(issues),
    )


def _raw_header(kind: PrintKind, header_lines: list[str]) -> list[str]:
    """Header names without interpretation (time excluded)."""
    if kind == "ip":
        return _fields(header_lines[1])[1:] if len(header_lines) > 1 else []
    return header_lines[0].split()[1:] if header_lines else []


def _mismatch_message(p: Path, kind: PrintKind, nnames: int, width: int, given: bool) -> str:
    if given:
        return f"{p}: {nnames} column names given, the rows have {width} values"
    msg = f"{p}: the header names {nnames} columns, the rows have {width} values"
    if kind == "element":
        msg += (
            "; COORDS_IGP/COORDS_IGP_UPD and S_IGP write 3/6 values per integration point under one"
            " header group, COORDS_UPD without COORDS has no header group"
            f" ({_SRC}:1049-1127 vs 1658-1673)"
        )
    elif kind == "ip":
        msg += f" ({_SRC}:1373-1451 vs 1759-1846)"
    return msg + "; pass columns=[...] with the names in data order"


# --------------------------------------------------------------------------------------------------
# node files


@dataclass(frozen=True)
class _Group:
    key: str
    names: tuple[str, ...]
    requires: tuple[str, ...] = ()


_CONTACT_2D = ("Normal stress", "Tang stress x", "Tang stress y", "Contact force x", "Contact force y")
_CONTACT_3D = (
    "Normal stress",
    "Tang stress x",
    "Tang stress y",
    "Tang stress z",
    "Contact force x",
    "Contact force y",
    "Contact force z",
)
_SDV = (
    "Normal stress",
    "|_ stress",
    ". stress",
    "C. void",
    "C. h_12",
    "d_s",
    "error",
    "Normal strain",
    "|_strain",
    ". strain",
    "gamma_1",
    "gamma_2",
    "No. of iter.",
)
_SDV_HCA = ("(strain ampl)", "(g_A)", "(fp)", "(fampl)", "(fe)", "(fy)")

#: Header groups in header order (print_write_header, :1545-1643). ``requires``: conditions under which the
#: data rows contain the group (dofs of the node, contact surface; :681-764, :797-921).
_NODE_HEADER: tuple[_Group, ...] = (
    _Group("COORDS", ("X1", "X2", "X3")),
    _Group("U", ("U1", "U2", "U3")),
    _Group("UR", ("UR1", "UR2", "UR3")),
    _Group("U_ACC", ("U1_ACC", "U2_ACC", "U3_ACC")),
    _Group("V", ("V1", "V2", "V3")),
    _Group("A", ("A1", "A2", "A3")),
    _Group("PW", ("Pw",), ("PW",)),
    _Group("CC", ("Cc",), ("CC",)),
    _Group("TEMP", ("Temp",), ("TT",)),
    _Group("DTEMP", ("dTemp",), ("TT",)),
    _Group("TEMP_RATE", ("Temp_rate",), ("TT",)),
    _Group("RFL", ("RFL",), ("TT",)),
    _Group("PA", ("Pa",)),
    _Group("RPW", ("RPW",), ("PW",)),
    _Group("RPA", ("RPA",), ("PA",)),
    _Group("RF", ("RF1", "RF2", "RF3")),
    _Group("RM", ("RM1", "RM2", "RM3")),
    _Group("FDYN", ("FDYN1", "FDYN2", "FDYN3")),
    _Group("CONTACT", _CONTACT_3D, ("CONTACT",)),
    _Group("CONTACT", _CONTACT_2D, ("CONTACT",)),
    _Group("CONTACT_WATER", ("Normal water stress",), ("CONTACT", "CONTACT_WATER")),
    _Group("CONTACT_SDV", _SDV, ("CONTACT_SDV",)),
    _Group("CONTACT_SDV_HCA", _SDV_HCA, ("CONTACT_SDV", "HCA")),
    _Group("CON_F", ("Connector force",)),
)
#: Data order (print_get_output_array_node): as the header, but FDYN last (:967-983).
_NODE_DATA_ORDER = [g.key for g in _NODE_HEADER if g.key != "FDYN"] + ["FDYN"]


def _group_regex(names: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(r"\s*" + r"\s+".join(re.escape(n) for n in names) + r"(?=\s|$)")


_NODE_REGEX = [(_group_regex(g.names), g) for g in _NODE_HEADER]


def _node_columns(
    p: Path, header_lines: list[str], width: int | None, issues: list[Issue]
) -> tuple[list[str], list[str]]:
    """Header names and data column names of a node file."""
    line = header_lines[0] if header_lines else ""
    m = re.match(r"\s*Time(?=\s|$)", line)
    if m is None:
        raise PrintFormatError(f"{p}: header does not start with 'Time'")
    pos = m.end()
    found: list[_Group] = []
    seen: set[str] = set()
    for regex, group in _NODE_REGEX:
        if group.key in seen:
            continue
        mm = regex.match(line, pos)
        if mm:
            found.append(group)
            seen.add(group.key)
            pos = mm.end()
    rest = line[pos:].strip()
    header = [n for g in found for n in g.names]
    if rest:
        cut = len(line) >= _HEADER_LENGTH and line[_HEADER_LENGTH - 1] != " "
        why = f" (header cut at {_HEADER_LENGTH} characters, {_SRC}:1524)" if cut else ""
        raise PrintFormatError(f"{p}: unknown text in the node header{why}: {rest!r}; pass columns=[...]")
    ordered = sorted(found, key=lambda g: _NODE_DATA_ORDER.index(g.key))
    if [g.key for g in ordered] != [g.key for g in found]:
        issues.append(
            _issue(
                "NG-RESULT-001",
                "info",
                "header lists FDYN before the contact/connector columns, the rows have it last; "
                "columns follow the rows",
                location=str(p),
                source=f"{_SRC}:1615-1618,967-983",
            )
        )
    full = [n for g in ordered for n in g.names]
    if width is None or width == len(full):
        return header, full
    conditions = sorted({c for g in ordered for c in g.requires})
    candidates: list[tuple[frozenset[str], list[str]]] = []
    for r in range(1, len(conditions) + 1):
        for absent in itertools.combinations(conditions, r):
            gone = frozenset(absent)
            names = [n for g in ordered if not gone.intersection(g.requires) for n in g.names]
            if len(names) == width and all(n2 != names for _, n2 in candidates):
                candidates.append((gone, names))
    if len(candidates) == 1:
        gone, names = candidates[0]
        dropped = [n for g in ordered if gone.intersection(g.requires) for n in g.names]
        issues.append(
            _issue(
                "NG-RESULT-002",
                "info",
                f"columns {dropped} are in the header but not in the rows (no {'/'.join(sorted(gone))} at this node)",
                location=str(p),
                source=f"{_SRC}:681-764,797-921",
            )
        )
        return header, names
    if not candidates:
        raise PrintFormatError(
            f"{p}: the header names {len(full)} columns, the rows have {width} values; pass columns=[...]"
        )
    options = "; ".join(str(n) for _, n in candidates)
    raise PrintFormatError(
        f"{p}: the rows have {width} of the {len(full)} header columns and several column sets fit "
        f"(numgeo omits variables a node has no dof for, {_SRC}:681-764): {options}; pass columns=[...]"
    )


# --------------------------------------------------------------------------------------------------
# element files

_STRAIN_HEADER = ("STRAIN11", "STRAIN22", "STRAIN33", "STRAIN12", "STRAIN23", "STRAIN13")  # :1682
_STRAIN_DATA = ("STRAIN11", "STRAIN22", "STRAIN33", "STRAIN12", "STRAIN13", "STRAIN23")  # :1149-1166
_ELEMENT_HEADER: tuple[tuple[str, ...], ...] = (
    ("X1", "X2", "X3"),
    ("STRESS11", "STRESS22", "STRESS33", "STRESS12", "STRESS13", "STRESS23"),
    _STRAIN_HEADER,
    (
        "STRAIN_HENCKY11",
        "STRAIN_HENCKY22",
        "STRAIN_HENCKY33",
        "STRAIN_HENCKY12",
        "STRAIN_HENCKY13",
        "STRAIN_HENCKY23",
    ),
    ("F11", "F12", "F13", "F21", "F22", "F23", "F31", "F32", "F33"),
    ("VOID",),
    ("DELTA-T",),
    ("DELTA-PW",),
)


def _element_columns(p: Path, header_lines: list[str], issues: list[Issue]) -> tuple[list[str], list[str]]:
    line = header_lines[0] if header_lines else ""
    tokens = line.split()
    if not tokens or tokens[0] != "Time":
        raise PrintFormatError(f"{p}: header does not start with 'Time'")
    tokens = tokens[1:]
    header = list(tokens)
    names: list[str] = []
    i = 0
    for group in _ELEMENT_HEADER:
        if tuple(tokens[i : i + len(group)]) == group:
            if group == _STRAIN_HEADER:
                names.extend(_STRAIN_DATA)
                issues.append(
                    _issue(
                        "NG-RESULT-003",
                        "info",
                        "header labels the strain shear columns STRAIN12 STRAIN23 STRAIN13, the rows are "
                        "in numgeo order 12, 13, 23; columns are named in row order",
                        location=str(p),
                        source=f"{_SRC}:1682,1149-1166",
                    )
                )
            else:
                names.extend(group)
                if group[0] == "STRAIN_HENCKY11":
                    issues.append(
                        _issue(
                            "NG-RESULT-006",
                            "warning",
                            "element STRAIN_HENCKY columns are not the mean Hencky strain: numgeo adds "
                            "the last integration point to the mean strain; use *Integration point "
                            "output",
                            location=str(p),
                            source=f"{_SRC}:1170-1189",
                        )
                    )
            i += len(group)
    names.extend(tokens[i:])  # element and material variables, one column each (:1726-1748)
    if len(line) >= _HEADER_LENGTH and line[_HEADER_LENGTH - 1] != " ":
        issues.append(
            _issue(
                "NG-RESULT-005",
                "warning",
                f"the header fills all {_HEADER_LENGTH} characters; the last name may be cut",
                location=str(p),
                source=f"{_SRC}:1524",
            )
        )
    return header, names


# --------------------------------------------------------------------------------------------------
# integration point files


def _fields(line: str) -> list[str]:
    return [line[i : i + _IP_FIELD].strip() for i in range(0, len(line.rstrip()), _IP_FIELD)]


def _ip_header(p: Path, header_lines: list[str]) -> tuple[list[str], tuple[int, ...]]:
    if len(header_lines) < 2:
        raise PrintFormatError(f"{p}: integration point files have two header lines ({_SRC}:1845-1846)")
    labels = _fields(header_lines[0])[1:]
    names = _fields(header_lines[1])
    if not names or names[0] != "Time":
        raise PrintFormatError(f"{p}: second header line does not start with 'Time'")
    names = names[1:]
    if len(labels) != len(names):
        raise PrintFormatError(f"{p}: {len(labels)} IP labels for {len(names)} names")
    ips: list[int] = []
    for lab in labels:
        m = re.fullmatch(r"IP-(\d+)", lab)
        if m is None:
            raise PrintFormatError(f"{p}: unexpected IP label {lab!r}")
        ips.append(int(m.group(1)))
    return names, tuple(ips)
