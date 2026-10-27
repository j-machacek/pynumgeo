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
"""Read a numgeo input file into a :class:`~pynumgeo.deck.Deck`.

The reader interprets the input the way numgeo does (:mod:`pynumgeo.io.lexer` for preprocessing, the
solver's option rules for the keywords modelled here) and reports everything that numgeo would reject or
read differently than a user would expect as :class:`~pynumgeo.validation.issue.Issue` objects. Keywords
that pynumgeo does not model are kept as generic :class:`~pynumgeo.deck.keyword.Keyword` objects.

Models with ``*Part`` / ``*Instance`` / ``*Assembly`` are flattened with numgeo's rules: instance-scoped
set names become ``<instance>.<set>``, node and element labels are offset per instance (each part must
be numbered 1..n in input order, which is what numgeo needs anyway), instance translations and
rotations are applied to the coordinates, and ``find`` queries inside an instance are evaluated in
the instance's scope.

Examples:
    >>> import pathlib, tempfile
    >>> p = pathlib.Path(tempfile.mkdtemp()) / "job.inp"
    >>> _ = p.write_text("*Node\\n1, 0., 0.\\n2, 1., 0.\\n*Element, type=u2-truss\\n1, 1, 2\\n"
    ...                  "*Nset, nset=Fix\\n1\\n*Step, name=S1\\n*Static\\n1., 1., 1., 1.\\n"
    ...                  "*Boundary\\nFix, u1, 0.\\n*End step\\n")
    >>> res = parse(p)
    >>> res.deck.mesh.node_count, res.deck.steps[0].items[0].data
    (2, [['Fix', 'u1', 0.0]])
    >>> [i.id for i in res.issues]
    []
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import numpy as np

from pynumgeo import catalogue as _cat
from pynumgeo.deck.deck import Amplitude, Deck, Material, Section, Step
from pynumgeo.deck.keyword import Keyword, Token
from pynumgeo.io.lexer import (
    Preprocessed,
    _delete_blanks,
    _drop_trailing_comma,
    _strip_comment,
    preprocess,
    preprocess_text,
)
from pynumgeo.io.numbers import parse_real, to_token
from pynumgeo.io.syntax import _ENDS, MATERIAL_CHILDREN, KeywordBlock, Option, parse_blocks, split_options
from pynumgeo.issue import Issue, has_errors
from pynumgeo.mesh.mesh import ElementBlock, ElementSet, Mesh, NodeSet, SetKind, Surface

__all__ = [
    "FragmentResult",
    "ReadError",
    "ReadResult",
    "data_tokens",
    "parse",
    "parse_fragment",
    "parse_text",
    "read",
    "to_token",
]


class ReadError(ValueError):
    """Raised by :func:`read` with ``strict=True`` when the input has errors."""

    def __init__(self, issues: list[Issue]) -> None:
        self.issues = issues
        errs = [str(i) for i in issues if i.severity == "error"]
        super().__init__("input has errors:\n" + "\n".join(errs[:20]))


@dataclass
class ReadResult:
    """Deck plus everything worth reporting about the input."""

    deck: Deck
    issues: list[Issue] = field(default_factory=list)
    preprocessed: Preprocessed | None = None

    @property
    def ok(self) -> bool:
        """True if no issue has severity ``error``."""
        return not has_errors(self.issues)


def _loc(b: KeywordBlock) -> str | None:
    return str(b.pos) if b.pos else None


def data_tokens(line: str) -> list[Token] | None:
    """The tokens numgeo reads from one data line, ``None`` for a line it skips (blank or comment).

    numgeo cuts the line at ``**``, deletes the blanks (not between ``$`` signs) and a trailing comma and
    splits it at the commas; numbers become ``int`` / ``float`` (:func:`to_token`), text keeps its spelling.
    A builder can give a line in any spelling and gets the tokens the reader would produce from it.

    >>> data_tokens("Base, u1, 0   ** fixed")
    ['Base', 'u1', 0]
    >>> data_tokens("2.0d6, 0.3,"), data_tokens("  ** note")
    ([2000000.0, 0.3], None)
    """
    cased = _strip_comment(line)
    if cased.strip(" ") == "":
        return None
    cased = _drop_trailing_comma(_delete_blanks(cased))
    return [to_token(c) for c in split_options(cased)]


def _rows(b: KeywordBlock) -> list[list[Token]]:
    return [[to_token(c) for c in cased] for _, _, cased in b.data_tokens()]


_OUTPUT_CARDS = {"*NODE": "*NODEOUTPUT", "*ELEMENT": "*ELEMENTOUTPUT"}


def _generic(b: KeywordBlock, parent: str | None = None) -> Keyword:
    kw = _OUTPUT_CARDS.get(b.keyword, b.keyword) if parent == "*OUTPUT" else b.keyword
    return Keyword(
        keyword=kw,
        value=b.value_cased,
        options=[(o.key, o.value_cased) for o in b.options],
        data=_rows(b),
        children=[_generic(c, b.keyword) for c in b.children],
        source=_loc(b),
    )


# ----------------------------------------------------------------------------- scopes (parts)
@dataclass
class _Scope:
    kind: str  # "part" | "instance"
    name: str
    part: str | None = None
    mesh: Mesh = field(default_factory=Mesh)
    transform: list[list[float]] = field(default_factory=list)
    has_mesh: bool = False


class _Reader:
    def __init__(self, pre: Preprocessed) -> None:
        self.pre = pre
        self.issues: list[Issue] = [
            Issue("NG-READ-INPUT-" + q.code.upper(), "warning", q.message, str(q.pos) if q.pos else None)
            for q in pre.quirks
        ]
        self.deck = Deck()
        self.cat = _cat.load()
        self.parts: dict[str, _Scope] = {}
        self.instances: list[_Scope] = []
        self.scope: _Scope | None = None
        self.in_assembly = False
        self.flattened = False
        self.node_blocks = 0
        self.pending_assembly_sets: list[tuple[str, NodeSet | ElementSet, str | None]] = []

    def issue(self, id: str, severity: str, msg: str, b: KeywordBlock | None = None, **kw: str) -> None:
        self.issues.append(Issue(id, severity, msg, _loc(b) if b else None, b.keyword if b else None, **kw))  # type: ignore[arg-type]

    # ------------------------------------------------------------------ driver
    def run(self) -> Deck:
        blocks = parse_blocks(self.pre.lines)
        ended = False
        for b in blocks:
            if ended:
                self.issue("NG-READ-INPUT-AFTER-END", "warning", "keyword after *End input is ignored by numgeo", b)
                continue
            if b.line.pos is None and b.keyword == "*AMPLITUDE":  # prepended DEFAULT amplitude
                if b.data:
                    self.issues.append(
                        Issue(
                            "NG-READ-INPUT-002",
                            "warning",
                            "lines before the first keyword are skipped by numgeo",
                            str(b.data[0].pos) if b.data[0].pos else None,
                        )
                    )
                continue
            ended = self.block(b)
        if (self.parts or self.instances) and not self.flattened:
            self.issue("NG-READ-PART-002", "error", "*Part/*Instance without *End assembly")
            self.flatten()
        m = self.deck.mesh
        if m.node_count and m.coords.shape[1] == 3 and _model_ndim(m, self.cat) == 2:
            # numgeo reads only label, x1, x2 in 2D models (read_nodes_.f90:115-121)
            if np.any(m.coords[:, 2] != 0.0):
                self.issue(
                    "NG-READ-MESH-013",
                    "warning",
                    "2D model: numgeo ignores the third node coordinate, which is not zero for some nodes",
                )
            m.coords = np.ascontiguousarray(m.coords[:, :2])
        return self.deck

    @property
    def mesh(self) -> Mesh:
        return self.scope.mesh if self.scope is not None else self.deck.mesh

    def block(self, b: KeywordBlock) -> bool:
        k = b.keyword
        if k == "*ENDINPUT":
            return True
        if k == "*PART":
            self.scope = _Scope("part", (b.options[0].value_cased if b.options else "") or "")
            self.parts[self.scope.name.upper()] = self.scope
            for c in b.children:
                if c.keyword != "*ENDPART":
                    self.block(c)
            self.scope = None
            return False
        if k == "*ASSEMBLY":
            self.in_assembly = True
            for c in b.children:
                if c.keyword != "*ENDASSEMBLY":
                    self.block(c)
            self.in_assembly = False
            self.flatten()
            return False
        if k == "*INSTANCE":
            self.instance(b)
            return False
        if k in ("*ENDPART", "*ENDINSTANCE", "*ENDASSEMBLY"):
            sev = "info" if k == "*ENDASSEMBLY" and not self.parts else "error"
            self.issue(
                "NG-READ-PART-003",
                sev,
                f"{k} without matching start" + (" (ignored by numgeo without parts)" if sev == "info" else ""),
                b,
            )
            return False
        if k == "*NODE":
            self.nodes(b)
        elif k == "*ELEMENT":
            self.elements(b)
        elif k == "*NSET":
            self.label_set(b, NodeSet)
        elif k == "*ELSET":
            self.label_set(b, ElementSet)
        elif k == "*SURFACE":
            self.surface(b)
        elif k == "*AMPLITUDE":
            self.amplitude(b)
        elif k == "*MATERIAL":
            self.material(b)
        elif k in ("*SOLIDSECTION", "*ASSIGNMATERIAL"):
            self.section(b)
        elif k == "*STEP":
            self.step(b)
        else:
            if self.scope is not None:
                self.issue("NG-READ-PART-004", "error", f"{k} is not allowed inside *Part/*Instance", b)
            if not self.cat.keyword_entries(k):
                self.issue(
                    "NG-READ-INPUT-001",
                    "error",
                    f"unknown keyword {k} (numgeo: invalid input statement); did you mean {self.cat.suggest(k)}?",
                    b,
                )
            self.deck.keywords.append(_generic(b))
        return False

    # ------------------------------------------------------------------ mesh
    def nodes(self, b: KeywordBlock) -> None:
        if b.options:
            self.issue("NG-READ-MESH-010", "info", "*Node options are ignored by numgeo", b)
        if self.scope is None:
            self.node_blocks += 1
            if self.node_blocks == 2:
                self.issue(
                    "NG-READ-MESH-011",
                    "error",
                    "numgeo reads only one *Node block per model or part",
                    b,
                )
        else:
            self.scope.has_mesh = True
        labels, coords = [], []
        for ln, toks, _ in b.data_tokens():
            try:
                labels.append(int(toks[0]))
                coords.append([parse_real(t) for t in toks[1:]])
            except ValueError:
                self.issue("NG-READ-MESH-012", "error", f"cannot read node line {ln.cased!r}", b)
        if not labels:
            return
        width = max(len(c) for c in coords)
        arr = np.array([c + [0.0] * (width - len(c)) for c in coords], dtype=np.float64)
        self.mesh.add_nodes(arr, labels)

    def elements(self, b: KeywordBlock) -> None:
        if self.scope is not None:
            self.scope.has_mesh = True
        if not b.options or b.options[0].key != "TYPE" or not b.options[0].value:
            self.issue(
                "NG-READ-MESH-020",
                "error",
                "*Element needs type= as its first option",
                b,
                source="src/input/read_elements_.f90:59-73",
            )
            return
        etype = b.options[0].value_cased or ""
        try:
            spec = self.cat.element_type(etype)
            nn = spec.nnodes
            if len(b.options) > 1 and spec.name.upper() != etype.upper().replace(" ", ""):
                # Abaqus names (C3D8, ...) are translated only when type= is the only option
                self.issue(
                    "NG-READ-MESH-025",
                    "error",
                    f"element type {etype} is translated by numgeo only when type= is the only option of "
                    f"*Element; use type={spec.name.lower()}",
                    b,
                    source="src/input/scanning_for_numbers_.f90:182-214",
                )
        except KeyError as e:
            self.issue("NG-READ-MESH-021", "error", str(e).strip('"'), b)
            nn = 0
        rows: list[list[int]] = []
        pending: list[int] | None = None
        for ln, toks, _ in b.data_tokens():
            try:
                vals = [int(t) for t in toks if t != ""]
            except ValueError:
                self.issue("NG-READ-MESH-022", "error", f"cannot read element line {ln.cased!r}", b)
                continue
            if pending is not None:
                vals = pending + vals
                pending = None
            if nn and len(vals) < nn + 1:
                pending = vals
                continue
            rows.append(vals)
        if pending is not None:
            self.issue("NG-READ-MESH-023", "error", "incomplete element record at the end of *Element", b)
        if not rows:
            return
        widths = {len(r) for r in rows}
        if len(widths) != 1:
            self.issue("NG-READ-MESH-024", "error", "element records have different numbers of nodes", b)
            w = max(widths)
            rows = [r + [0] * (w - len(r)) for r in rows]
        arr = np.array(rows, dtype=np.int64)
        blk = ElementBlock(etype, arr[:, 0], arr[:, 1:], [(o.key, o.value_cased) for o in b.options[1:]])
        self.mesh.blocks.append(blk)

    def label_set(self, b: KeywordBlock, cls: type[NodeSet] | type[ElementSet]) -> None:
        key = "NSET" if cls is NodeSet else "ELSET"
        kind: SetKind = "list"
        # read_set_.f90:123-152 (nsets), :558-582 (elsets): every option is tested for every word with
        # index(), independently; the last option containing a word wins. *Elset knows no CYLINDER.
        words = ("GENERATE", "INTERNAL", "INSTANCE", "FIND", "BOUNDINGBOX") + (("CYLINDER",) if key == "NSET" else ())
        flags: set[str] = set()
        name_opt: Option | None = None
        inst_opt: Option | None = None
        for o in b.options:
            t = o.token
            matched = [w for w in (key, *words) if w in t]
            if not matched:
                if o.key == "NAME":
                    self.issue(
                        "NG-READ-MESH-030", "error", f"*{key.capitalize()} does not accept name=, use {key.lower()}=", b
                    )
                else:
                    self.issue("NG-READ-MESH-031", "error", f"unknown option {o.key_cased!r}", b)
                continue
            for w in matched:
                if w == key:
                    name_opt = o
                elif w == "INSTANCE":
                    inst_opt = o
                else:
                    flags.add(w)
                if o.key != w and not (w == key and o.key == key):
                    self.issue(
                        "NG-READ-NAME-001",
                        "warning",
                        f"option {o.key_cased if o.value is None else o.key_cased + '=' + str(o.value_cased)!r} "
                        f"is also read as {w.lower()} (numgeo matches option words inside the text)",
                        b,
                    )
        name = None if name_opt is None else (name_opt.value_cased or "")
        instance = None if inst_opt is None else (inst_opt.value_cased or "")
        if inst_opt is not None and inst_opt is name_opt:
            # the name option is split at "=" first, so the same option then gives an empty instance name
            self.issue(
                "NG-READ-MESH-039",
                "error",
                f"the {key.lower()} name {name!r} contains INSTANCE; numgeo reads the option also as the instance "
                "name, finds it empty and stops",
                b,
                source="src/input/read_set_.f90:178-193" if key == "NSET" else "src/input/read_set_.f90:605-620",
            )
            instance = None
        if not name:
            self.issue("NG-READ-MESH-032", "error", f"*{key.capitalize()} needs {key.lower()}=<name>", b)
            return
        what = f"*{key.capitalize()}"
        src = "src/input/read_set_.f90:160-175" if key == "NSET" else "src/input/read_set_.f90:589-602"
        if "GENERATE" in flags and "FIND" in flags:
            self.issue(
                "NG-READ-MESH-036", "error", f"generate and find cannot be combined in one {what}", b, source=src
            )
        if ("BOUNDINGBOX" in flags or "CYLINDER" in flags) and "FIND" not in flags:
            self.issue(
                "NG-READ-MESH-037", "error", f"boundingbox and cylinder require the find option ({what})", b, source=src
            )
        if "BOUNDINGBOX" in flags and "CYLINDER" in flags:
            self.issue(
                "NG-READ-MESH-038", "error", f"boundingbox and cylinder cannot be combined in one {what}", b, source=src
            )
        values: list[float] = []
        members: list[int] = []
        rows = [toks for _, toks, _ in b.data_tokens()]
        if "FIND" in flags:
            kind = "boundingbox" if "BOUNDINGBOX" in flags else "cylinder" if "CYLINDER" in flags else "find"
            values = [parse_real(t) for r in rows[:1] for t in r if t != ""]
            if len(rows) > 1:
                self.issue("NG-READ-MESH-033", "warning", "only the first data line of a find set is read", b)
        elif "GENERATE" in flags:
            kind = "generate"
            vals = [int(t) for r in rows[:1] for t in r if t != ""]
            if len(vals) != 3:
                self.issue("NG-READ-MESH-034", "error", "generate needs exactly first, last, increment", b)
                return
            values = [float(v) for v in vals]
            members = list(range(vals[0], vals[1] + 1, vals[2])) if vals[2] > 0 else []
        else:
            for r in rows:
                for t in r:
                    if t == "":
                        continue
                    try:
                        members.append(int(t))
                    except ValueError:
                        self.issue("NG-READ-MESH-035", "error", f"set member {t!r} is not a label", b)
        s = cls(
            name=name,
            kind=kind,
            members=np.array(members, dtype=np.int64),
            values=values,
            internal="INTERNAL" in flags,
            instance=instance,
        )
        if self.scope is not None:
            if kind in ("find", "boundingbox", "cylinder"):
                self.evaluate_query(s, self.scope.mesh)
            (self.scope.mesh.nsets if cls is NodeSet else self.scope.mesh.elsets).append(s)  # type: ignore[arg-type]
        elif self.in_assembly:
            self.pending_assembly_sets.append((key, s, instance))
        elif instance is not None and self.flattened:
            self.relabel_assembly_set(key, s, instance)
            self.add_set(key, s)
        else:
            self.add_set(key, s)

    def add_set(self, key: str, s: NodeSet | ElementSet) -> None:
        if key == "NSET":
            self.deck.mesh.nsets.append(s)  # type: ignore[arg-type]
        else:
            self.deck.mesh.elsets.append(s)  # type: ignore[arg-type]

    def evaluate_query(self, s: NodeSet | ElementSet, mesh: Mesh) -> None:
        """Evaluate find / bounding box / cylinder in a part or instance scope (numgeo does it on reading)."""
        if not mesh.node_count:
            return
        if s.kind == "find":
            node = mesh.find_nearest_node(s.values[:3])
            if isinstance(s, NodeSet):
                s.members = np.array([node], dtype=np.int64)
            else:
                lab = [
                    int(bl.labels[i])
                    for bl in mesh.blocks
                    for i in np.nonzero((bl.connectivity == node).any(axis=1))[0]
                ]
                s.members = np.array(lab[:1], dtype=np.int64)
        elif s.kind == "boundingbox" and len(s.values) >= 6:
            # read_set_.f90:251-267 (nodes), 692-736 (elements: all nodes inside); strict, tol 1e-6,
            # z only in 3D models
            v = s.values
            tol = 1.0e-6
            lo = np.minimum(v[0:3], v[3:6]) - tol
            hi = np.maximum(v[0:3], v[3:6]) + tol
            nd = 3 if _model_ndim(mesh, self.cat) == 3 else 2
            c = mesh.coords[:, :nd]
            inside = np.all((c > lo[:nd]) & (c < hi[:nd]), axis=1)
            if isinstance(s, NodeSet):
                s.members = mesh.node_labels[inside]
            else:
                ok = set(mesh.node_labels[inside].tolist())
                s.members = np.array(
                    [
                        int(bl.labels[i])
                        for bl in mesh.blocks
                        for i in range(bl.labels.size)
                        if all(int(n) in ok for n in bl.connectivity[i])
                    ],
                    dtype=np.int64,
                )
        else:
            self.issues.append(
                Issue("NG-READ-PART-010", "error", f"{s.kind} sets inside parts are not supported by pynumgeo yet")
            )
            return
        s.kind = "list"
        s.values = []
        self.issues.append(
            Issue("NG-READ-PART-011", "info", f"set {s.name} ({'find'}) evaluated by pynumgeo in its part scope")
        )

    def surface(self, b: KeywordBlock) -> None:
        name, stype = None, "element"
        for o in b.options:
            if "NAME" in o.key:
                name = o.value_cased
            elif "TYPE" in o.key:
                stype = (o.value or "").lower()
                if stype not in ("node", "element"):
                    self.issue(
                        "NG-READ-MESH-040",
                        "error",
                        f"*Surface type must be node or element, got {o.value_cased!r}",
                        b,
                    )
            elif "INSTANCE" in o.key:
                self.issue("NG-READ-MESH-041", "info", "*Surface instance= is ignored by numgeo", b)
            else:
                self.issue("NG-READ-MESH-042", "error", f"unknown *Surface option {o.key_cased!r}", b)
        if not name:
            self.issue("NG-READ-MESH-043", "error", "*Surface needs name=", b)
            return
        rows = [tuple(c for c in cased if c != "") for _, _, cased in b.data_tokens()]
        surf = Surface(name=name, type="node" if stype == "node" else "element", rows=list(rows))
        self.mesh.surfaces.append(surf)

    # ------------------------------------------------------------------ parts
    def instance(self, b: KeywordBlock) -> None:
        name = part = None
        for o in b.options:
            if "PART" in o.key:
                part = o.value_cased
            elif "NAME" in o.key:
                name = o.value_cased
        if not name or not part:
            self.issue("NG-READ-PART-001", "error", "*Instance needs name= and part=", b)
            return
        sc = _Scope("instance", name, part)
        p = self.parts.get(part.upper())
        if p is None:
            self.issue("NG-READ-PART-005", "error", f"*Instance refers to unknown part {part!r}", b)
        elif p.has_mesh:  # meshed on part: the instance gets the part's mesh
            sc.mesh = _copy_mesh(p.mesh)
            sc.has_mesh = True
        sc.transform = [[parse_real(t) for t in toks if t != ""] for _, toks, _ in b.data_tokens()]
        self.instances.append(sc)
        prev, self.scope = self.scope, sc
        for c in b.children:
            if c.keyword != "*ENDINSTANCE":
                self.block(c)
        self.scope = prev

    def flatten(self) -> None:
        """numgeo's relabel_parts at *End assembly (see module docstring)."""
        if self.flattened:
            return
        self.flattened = True
        if len(self.instances) != len(self.parts):
            self.issues.append(
                Issue("NG-READ-PART-006", "error", "every *Part needs exactly one *Instance, in the same order")
            )
        target = self.deck.mesh
        node_off = int(target.node_labels.max()) if target.node_count else 0
        el_off = int(target.element_labels.max()) if target.element_count else 0
        self.offsets: dict[str, tuple[int, int]] = {}
        for sc in self.instances:
            m = sc.mesh
            n = m.node_count
            if n and not np.array_equal(m.node_labels, np.arange(1, n + 1)):
                self.issues.append(
                    Issue(
                        "NG-READ-MESH-001",
                        "error",
                        f"node labels of {sc.name} must be 1..n in the order "
                        "of definition (numgeo uses node labels as positions)",
                    )
                )
            coords = _transform(m.coords, sc.transform, self.issues, sc.name)
            target.add_nodes(coords, m.node_labels + node_off) if n else None
            for blk in m.blocks:
                target.blocks.append(
                    ElementBlock(blk.type, blk.labels + el_off, blk.connectivity + node_off, list(blk.options))
                )
            prefix = sc.name + "."
            for s in m.nsets:
                target.nsets.append(
                    NodeSet(
                        prefix + s.name,
                        s.kind,
                        s.members + node_off,
                        _shift_gen(s, node_off),
                        s.internal,
                        None,
                    )
                )
            for e in m.elsets:
                target.elsets.append(
                    ElementSet(prefix + e.name, e.kind, e.members + el_off, _shift_gen(e, el_off), e.internal, None)
                )
            for sf in m.surfaces:
                rows = [tuple([prefix + r[0], *r[1:]]) if r else r for r in sf.rows]
                target.surfaces.append(Surface(sf.name, sf.type, rows))
            self.offsets[sc.name.upper()] = (node_off, el_off)
            node_off += int(m.node_labels.max()) if n else 0
            el_off += int(m.element_labels.max()) if m.element_count else 0
        for key, aset, inst in self.pending_assembly_sets:
            if inst is not None:
                self.relabel_assembly_set(key, aset, inst)
            self.add_set(key, aset)
        self.pending_assembly_sets = []

    def relabel_assembly_set(self, key: str, s: NodeSet | ElementSet, inst: str) -> None:
        off = self.offsets.get(inst.upper())
        if off is None:
            self.issues.append(Issue("NG-READ-PART-007", "error", f"set {s.name}: unknown instance {inst!r}"))
            return
        o = off[0] if key == "NSET" else off[1]
        if s.kind in ("find", "boundingbox", "cylinder"):
            sub = Mesh()
            m = self.deck.mesh
            sel = (m.node_labels > off[0]) & (m.node_labels <= off[0] + max(1, int(m.node_count)))
            sub.coords, sub.node_labels = m.coords[sel], m.node_labels[sel]
            sub.blocks = list(m.blocks)
            self.evaluate_query(s, sub)
        else:
            s.members = s.members + o
            s.values = _shift_gen(s, o)
        s.instance = None

    # ------------------------------------------------------------------ model keywords
    def amplitude(self, b: KeywordBlock) -> None:
        if len(b.options) != 2:
            self.issue(
                "NG-READ-AMPL-001",
                "error",
                "*Amplitude needs exactly two options, name= and type=",
                b,
                source="src/input/read_amplitude_.f90:75-79",
            )
        name = typ = None
        for o in b.options:
            if "NAME" in o.key:
                name = o.value_cased
            elif "TYPE" in o.key:
                typ = o.value
        if not name or not typ:
            self.issue("NG-READ-AMPL-002", "error", "*Amplitude needs name= and type=", b)
            return
        if name.upper() == "DEFAULT":
            self.issue("NG-READ-AMPL-003", "error", "the amplitude name DEFAULT is reserved by numgeo", b)
        self.deck.amplitudes.append(Amplitude(name=name, type=typ.lower(), data=_rows(b), source=_loc(b)))

    def material(self, b: KeywordBlock) -> None:
        name, phases, extra = None, None, []
        for o in b.options:
            if o.key == "NAME":
                name = o.value_cased
            elif o.key == "PHASES":
                try:
                    phases = int(o.value or "")
                except ValueError:
                    self.issue("NG-READ-MAT-002", "error", f"phases must be an integer, got {o.value_cased!r}", b)
            else:
                extra.append((o.key, o.value_cased))
                self.issue("NG-READ-MAT-003", "warning", f"unexpected *Material option {o.key_cased!r}", b)
        if not name:
            self.issue("NG-READ-MAT-001", "error", "*Material needs name=", b)
            name = ""
        mat = Material(
            name=name,
            phases=phases,
            properties=[_generic(c) for c in b.children],
            extra_options=extra,
            source=_loc(b),
        )
        self.deck.materials.append(mat)

    def section(self, b: KeywordBlock) -> None:
        elset = material = None
        amgcl = False
        for o in b.options:
            if o.key == "AMGCL":
                amgcl = (o.value or "") == "DIRECT"
            elif "ELSET" in o.key:
                elset = o.value_cased
            elif "MATERIAL" in o.key:
                material = o.value_cased
            else:
                self.issue("NG-READ-SEC-002", "error", f"unknown option {o.key_cased!r}", b)
        if not elset or not material:
            self.issue("NG-READ-SEC-001", "error", f"{b.keyword} needs elset= and material=", b)
            return
        if b.data:
            self.issue("NG-READ-SEC-003", "error", "a material assignment has no data line (numgeo rejects it)", b)
        self.deck.sections.append(
            Section(elset=elset, material=material, keyword=b.keyword, amgcl_direct=amgcl, source=_loc(b))
        )

    def step(self, b: KeywordBlock) -> None:
        opts = b.options
        if not opts or "NAME" not in opts[0].key:
            self.issue(
                "NG-READ-STEP-001",
                "error",
                "name= must be the first option of *Step",
                b,
                source="src/input/read_step_.f90:273-280",
            )
        name = (opts[0].value_cased or "") if opts else ""
        st: dict[str, object] = {}
        extra = []
        for o in opts[1:]:
            t = o.token
            if "SCALEFACTOR=" in t:
                st["scalefactor"] = parse_real(o.value or "0")
                if o is not opts[1]:
                    self.issue(
                        "NG-READ-STEP-003",
                        "error",
                        "scalefactor= must be the second option of *Step",
                        b,
                        source="src/input/read_step_.f90:507-511",
                    )
            elif "MAXITER" in t:
                st["maxiter"] = int(parse_real(o.value or "")) if o.value else None
            elif "MINITER" in t:
                st["miniter"] = int(parse_real(o.value or "")) if o.value else None
            elif "NLGEOM" in t:
                st["nlgeom"] = True
                if o.value is not None:
                    self.issue("NG-READ-STEP-004", "warning", f"nlgeom takes no value; {o.token} switches it ON", b)
            elif "NOCUTBACK" in t:
                st["nocutback"] = True
            elif "INC" in t:
                st["inc"] = int(parse_real(o.value)) if o.value else None
            else:
                extra.append((o.key, o.value_cased))
                self.issue("NG-READ-STEP-005", "warning", f"*Step option {o.key_cased!r} is ignored by numgeo", b)
        kids = list(b.children)
        if kids and kids[-1].keyword == "*ENDSTEP":
            kids = kids[:-1]
        else:
            self.issue("NG-READ-STEP-006", "error", "*Step without *End step", b)
        if not kids:
            self.issue("NG-READ-STEP-002", "error", "*Step must be followed by a procedure", b)
            return
        proc = _generic(kids[0])
        procedures = {
            "*GEOSTATIC",
            "*STATIC",
            "*REDUCTION",
            "*TRANSIENT",
            "*TRANSIENT-CRITICAL",
            "*EXPLICITDYNAMIC",
            "*EXPLICITDYNAMICS",
            "*DYNAMIC",
        }
        if proc.keyword not in procedures:
            self.issue(
                "NG-READ-STEP-002",
                "error",
                f"the line after *Step must be the procedure, got {proc.keyword}",
                kids[0],
            )
        items = []
        for c in kids[1:]:
            if not self.cat.keyword_entries(c.keyword) and c.keyword not in _STEP_ALIASES:
                self.issue(
                    "NG-READ-INPUT-001",
                    "error",
                    f"unknown step keyword {c.keyword}; did you mean {self.cat.suggest(c.keyword)}?",
                    c,
                )
            items.append(_generic(c))
        self.deck.steps.append(Step(name=name, procedure=proc, items=items, extra_options=extra, source=_loc(b), **st))


#: step keywords numgeo reads that the catalogue lists under another spelling
_STEP_ALIASES = ("*HHT", "*BWE", "*UBOUNDARY", "*DSLOAD", "*RIGIDBODY", "*LINESEARCH")


def _model_ndim(mesh: Mesh, cat: _cat.Catalogue) -> int:
    """numgeo's model dimension: 3 if any element type is 3D, else 2 (scanning_for_numbers_.f90:217)."""
    for b in mesh.blocks:
        try:
            if cat.element_type(b.type).ndim == 3:
                return 3
        except KeyError:
            continue
    return 2


def _shift_gen(s: NodeSet | ElementSet, off: int) -> list[float]:
    if s.kind == "generate" and len(s.values) == 3:
        return [s.values[0] + off, s.values[1] + off, s.values[2]]
    return list(s.values)


def _copy_mesh(m: Mesh) -> Mesh:
    c = Mesh()
    c.node_labels, c.coords = m.node_labels.copy(), m.coords.copy()
    c.blocks = [ElementBlock(b.type, b.labels.copy(), b.connectivity.copy(), list(b.options)) for b in m.blocks]
    c.nsets = [NodeSet(s.name, s.kind, s.members.copy(), list(s.values), s.internal, s.instance) for s in m.nsets]
    c.elsets = [ElementSet(s.name, s.kind, s.members.copy(), list(s.values), s.internal, s.instance) for s in m.elsets]
    c.surfaces = [Surface(s.name, s.type, list(s.rows)) for s in m.surfaces]
    return c


def _transform(coords: np.ndarray, rows: list[list[float]], issues: list[Issue], name: str) -> np.ndarray:
    """Instance translation (ndim values) and rotation (7 values), rotation first (read_part_.f90:217-238)."""
    if not rows:
        return coords
    d = coords.shape[1]
    trans = np.zeros(d)
    rot: list[float] | None = None
    for r in rows:
        if len(r) == 7:
            rot = r
        elif len(r) in (2, 3):
            trans[: min(d, len(r))] += r[:d]
        else:
            issues.append(
                Issue(
                    "NG-READ-PART-008",
                    "error",
                    f"instance {name}: data lines must hold a translation or 7 rotation values",
                )
            )
    out = coords.copy()
    if rot is not None:
        p1, p2, theta = np.array(rot[:3]), np.array(rot[3:6]), math.radians(rot[6])
        axis = np.abs((p1 - p2) / np.linalg.norm(p1 - p2))
        x = np.zeros((out.shape[0], 3))
        x[:, :d] = out
        b_ = axis
        rotated = x * math.cos(theta) + np.cross(x, b_) * math.sin(theta) + np.outer(x @ b_, b_) * (1 - math.cos(theta))
        out = rotated[:, :d]
        issues.append(Issue("NG-READ-PART-009", "info", f"instance {name}: rotation applied by pynumgeo"))
    return out + trans


def parse(path: str | os.PathLike[str], workdir: str | os.PathLike[str] | None = None) -> ReadResult:
    """Read an input file; never raises for input errors, they are in ``issues``.

    Raises:
        FileNotFoundError: if the file or an include is missing.
    """
    pre = preprocess(path, workdir)
    r = _Reader(pre)
    deck = r.run()
    return ReadResult(deck=deck, issues=r.issues, preprocessed=pre)


def _resolver(includes: Mapping[str, str] | None) -> Callable[[str], tuple[str, str]] | None:
    if includes is None:
        return None
    files = dict(includes)

    def resolve(inc: str) -> tuple[str, str]:
        # numgeo opens the name as written; Windows matches it in any case
        if inc in files:
            return inc + ".inp", files[inc]
        hit = [k for k in files if k.lower() == inc.lower()]
        if hit:
            return hit[0] + ".inp", files[hit[0]]
        raise FileNotFoundError(f"INCLUDE file not found: {inc}.inp (numgeo stops)")

    return resolve


def parse_text(text: str, name: str = "<string>", *, includes: Mapping[str, str] | None = None) -> ReadResult:
    """Like :func:`parse` for a string.

    Args:
        includes: include name (the text after ``=`` of the include line) -> content of that file, e.g. the
            result of :func:`~pynumgeo.io.writer.write_texts` keyed by include name. Without it, includes raise
            :class:`FileNotFoundError`.
    """
    pre = preprocess_text(text, name, include_resolver=_resolver(includes))
    r = _Reader(pre)
    return ReadResult(deck=r.run(), issues=r.issues, preprocessed=pre)


@dataclass
class FragmentResult:
    """What :func:`parse_fragment` read: keywords of one context, or a partial deck (``context="model"``)."""

    keywords: list[Keyword]
    deck: Deck
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if no issue has severity ``error``."""
        return not has_errors(self.issues)


_FRAGMENT_CONTEXTS = ("model", "step", "material")
_FORBIDDEN_IN_FRAGMENT = frozenset({*_ENDS, *_ENDS.values(), "*MATERIAL", "*ENDINPUT"})


def parse_fragment(text: str, context: str = "model", name: str = "<fragment>") -> FragmentResult:
    """Read keyword lines that belong inside a deck, e.g. lines a user types for a model, a step or a material.

    The lines are preprocessed like numgeo input (upper case, blanks, ``**``) and grouped like the reader
    groups them. Includes are not allowed.

    Args:
        context: ``"model"`` - model definitions; they may define sets, amplitudes, materials, assignments
            and other model keywords, all of which are in ``deck``; ``keywords`` are the deck's model keywords.
            ``"step"`` - keywords inside a ``*Step`` (no procedure); ``"material"`` - sub-keywords of a
            ``*Material``. For these two, ``keywords`` holds them and ``deck`` is empty.

    >>> r = parse_fragment("*Controls, u, modify\\n1e-3, 1e-3, 1e-2, 1e-5, 1e-6, 1.0", "step")
    >>> [(k.keyword, k.data) for k in r.keywords], r.ok
    ([('*CONTROLS', [[0.001, 0.001, 0.01, 1e-05, 1e-06, 1.0]])], True)
    """
    if context not in _FRAGMENT_CONTEXTS:
        raise ValueError(f"context must be one of {_FRAGMENT_CONTEXTS}, not {context!r}")
    pre = preprocess_text(text, name)
    if context == "model":
        r = _Reader(pre)
        deck = r.run()
        return FragmentResult(keywords=list(deck.keywords), deck=deck, issues=r.issues)
    issues = [
        Issue("NG-READ-INPUT-" + q.code.upper(), "warning", q.message, str(q.pos) if q.pos else None)
        for q in pre.quirks
    ]
    lines = [ln for ln in pre.lines if ln.pos is not None]  # without the prepended default amplitude
    try:
        blocks = parse_blocks(lines)
    except ValueError as e:
        issues.append(Issue("NG-READ-INPUT-002", "error", str(e)))
        return FragmentResult(keywords=[], deck=Deck(), issues=issues)
    cat = _cat.load()
    out: list[Keyword] = []
    for b in blocks:
        if context == "material" and b.keyword not in MATERIAL_CHILDREN:
            issues.append(
                Issue("NG-READ-MAT-004", "error", f"{b.keyword} is not a *Material sub-keyword", _loc(b), b.keyword)
            )
            continue
        if b.keyword in _FORBIDDEN_IN_FRAGMENT:
            issues.append(
                Issue("NG-READ-INPUT-003", "error", f"{b.keyword} cannot stand inside a {context}", _loc(b), b.keyword)
            )
            continue
        if context == "step" and not cat.keyword_entries(b.keyword) and b.keyword not in _STEP_ALIASES:
            issues.append(
                Issue(
                    "NG-READ-INPUT-001",
                    "error",
                    f"unknown step keyword {b.keyword}; did you mean {cat.suggest(b.keyword)}?",
                    _loc(b),
                    b.keyword,
                )
            )
        out.append(_generic(b))
    return FragmentResult(keywords=out, deck=Deck(), issues=issues)


def read(path: str | os.PathLike[str], *, strict: bool = False) -> Deck:
    """Read an input file into a :class:`~pynumgeo.deck.Deck`.

    Args:
        path: the master ``.inp`` file (includes are resolved relative to its folder).
        strict: raise :class:`ReadError` if the input has errors (see :func:`parse` for all issues).
    """
    res = parse(path)
    if strict and not res.ok:
        raise ReadError(res.issues)
    return res.deck
