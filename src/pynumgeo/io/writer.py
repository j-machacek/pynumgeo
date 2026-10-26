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
"""Write a :class:`~pynumgeo.deck.Deck` as a numgeo input file.

Spelling: never all capitals. Keywords are written in sentence case with
the docs' word breaks (``*Step``, ``*Initial conditions``, ``*Node output``), option keys and enumerated
values in lower case, names defined in the deck (sets, surfaces, materials, amplitudes, steps, ...)
exactly as given. numgeo upper-cases every line and deletes blanks, so this is what it reads.

Canonical order: nodes, elements, sets, surfaces, amplitudes, materials, material assignments, other
model keywords (in their original order), steps, ``*End input``. Options are written in the order the
solver's readers require (``name=`` first and ``scalefactor=`` second on ``*Step``, ``type=`` first on
``*Element``). Reals are written as Python's shortest round-trip text. Lines never exceed 256 characters
(:class:`WriteError` otherwise); element records that would are split over two lines with different field
counts, which is what numgeo's pre-scan needs.

The output is byte-stable: the same deck always gives the same text.

Examples:
    >>> from pynumgeo.deck import Deck, Keyword, Step
    >>> d = Deck()
    >>> _ = d.mesh.add_nodes([[0, 0], [1, 0]]); _ = d.mesh.add_elements("u2-truss", [[1, 2]])
    >>> _ = d.mesh.add_nset("Fix", [1])
    >>> d.steps.append(Step(name="Load", procedure=Keyword.make("*Static", data=[[0.1, 1.0, 1e-5, 0.5]]),
    ...     items=[Keyword.make("*Boundary", data=[["Fix", "U1", 0.0]])]))
    >>> print(write_text(d, header=False))
    *Node
    1, 0.0, 0.0
    2, 1.0, 0.0
    *Element, type=u2-truss
    1, 1, 2
    *Nset, nset=Fix
    1
    *Step, name=Load
    *Static
    0.1, 1.0, 1e-05, 0.5
    *Boundary
    Fix, u1, 0.0
    *End step
    *End input
    <BLANKLINE>
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from pynumgeo import catalogue as _cat
from pynumgeo._provenance import input_file_header
from pynumgeo.deck.deck import Amplitude, Deck, Material, Section, Step
from pynumgeo.deck.keyword import Keyword, Token
from pynumgeo.deck.names import named_objects, risky_words
from pynumgeo.io.numbers import format_real
from pynumgeo.mesh.mesh import ElementSet, Mesh, NodeSet

__all__ = ["WriteError", "display_keyword", "write", "write_text"]

MAX_LINE = 256
_PER_LINE = 16  # set members per line


class WriteError(ValueError):
    """The deck cannot be written as valid numgeo input (e.g. a line would exceed 256 characters)."""


_DISPLAY_FALLBACK = {
    "*NODEOUTPUT": "*Node output",
    "*ELEMENTOUTPUT": "*Element output",
    "*INTEGRATIONPOINT": "*Integration point",
    "*SOLIDSECTION": "*Solid section",
    "*ASSIGNMATERIAL": "*Assign material",
    "*ENDSTEP": "*End step",
    "*ENDINPUT": "*End input",
}


def display_keyword(keyword: str, context: str | None = None) -> str:
    """Normal-case spelling of a solver keyword (sentence case, docs' word breaks).

    >>> display_keyword("*INITIALCONDITIONS"), display_keyword("*NODEOUTPUT", "output-field")
    ('*Initial conditions', '*Node output')
    """
    k = _cat.normalise_keyword(keyword)
    if k in _DISPLAY_FALLBACK:
        return _DISPLAY_FALLBACK[k]
    try:
        entries = _cat.load().keyword_entries(k)
    except Exception:  # pragma: no cover - catalogue always loads in a built package
        entries = []
    if context:
        entries = [e for e in entries if context in e.contexts] or entries
    for e in entries:
        d = e.display.strip()
        d = "*" + d[1].upper() + d[2:].lower() if len(d) > 1 else d
        if d.upper().replace(" ", "") == k:
            return d
    return "*" + k[1].upper() + k[2:].lower() if len(k) > 1 else k


class _Writer:
    def __init__(self, deck: Deck) -> None:
        self.deck = deck
        self.names = deck.defined_names()
        self.out: list[str] = []

    # ------------------------------------------------------------------ helpers
    def line(self, text: str) -> None:
        if len(text) > MAX_LINE:
            raise WriteError(f"line longer than {MAX_LINE} characters: {text[:60]}...")
        self.out.append(text)

    def word(self, s: str) -> str:
        """Text value: names defined in the deck keep their spelling, other words become lower case."""
        if s == "" or "$" in s:
            return s
        if s.upper().replace(" ", "") in self.names:
            return s
        return s.lower()

    def token(self, t: Token) -> str:
        if isinstance(t, bool):
            raise WriteError("boolean values are not numgeo syntax")
        if isinstance(t, int):
            return str(t)
        if isinstance(t, float):
            return format_real(t)
        return self.word(str(t))

    def option(self, key: str, value: str | None) -> str:
        k = key.lower()
        if value is None:
            return k
        return f"{k}={self.word(value)}"

    def keyword(self, kw: Keyword, context: str | None) -> None:
        head = display_keyword(kw.keyword, context)
        if kw.value is not None:
            head += "=" + self.word(kw.value)
        parts = [head] + [self.option(k, v) for k, v in kw.options]
        self.line(", ".join(parts))
        for row in kw.data:
            self.line(", ".join(self.token(t) for t in row))
        child_ctx = {
            "*MATERIAL": "material",
            "*OUTPUT": _output_context(kw),
            "*INTERACTION": "interaction sub-keyword",
            "*DYNAMIC": "step-procedure",
            "*EXPLICITDYNAMIC": "step-procedure",
            "*EQUATION": "step",
            "*RIGIDBODY": "step",
        }.get(kw.keyword, context)
        for c in kw.children:
            self.keyword(c, child_ctx)

    # ------------------------------------------------------------------ sections
    def mesh(self, m: Mesh) -> None:
        if m.node_count:
            self.line("*Node")
            for lab, xyz in zip(m.node_labels.tolist(), m.coords.tolist(), strict=True):
                self.line(", ".join([str(lab), *(format_real(x) for x in xyz)]))
        for b in m.blocks:
            opts = "".join(", " + self.option(k, v) for k, v in b.options)
            self.line(f"*Element, type={b.type.lower()}{opts}")
            rows = np.column_stack([b.labels, b.connectivity]).tolist()
            texts = [", ".join(map(str, r)) for r in rows]
            if any(len(t) > MAX_LINE for t in texts):
                nn = b.connectivity.shape[1]
                first = nn // 2 + 2  # fields on the first line (label included); the second line differs
                if first == nn + 1 - first:
                    first += 1
                for r in rows:
                    self.line(", ".join(map(str, r[:first])))
                    self.line(", ".join(map(str, r[first:])))
            else:
                for t in texts:
                    self.line(t)
        for s in m.nsets:
            self.label_set("*Nset", "nset", s)
        for e in m.elsets:
            self.label_set("*Elset", "elset", e)
        for sf in m.surfaces:
            self.line(f"*Surface, type={sf.type}, name={sf.name}")
            for r in sf.rows:
                self.line(", ".join(self.word(x) if i else x for i, x in enumerate(r)))

    def label_set(self, kw: str, key: str, s: NodeSet | ElementSet) -> None:
        opts = [f"{key}={s.name}"]
        if s.internal:
            opts.append("internal")
        if s.instance:
            opts.append(f"instance={s.instance}")
        if s.kind == "generate":
            opts.append("generate")
            self.line(", ".join([kw, *opts]))
            self.line(", ".join(str(int(v)) for v in s.values))
            return
        if s.kind in ("find", "boundingbox", "cylinder"):
            opts.append("find")
            if s.kind != "find":
                opts.append(s.kind)
            self.line(", ".join([kw, *opts]))
            self.line(", ".join(format_real(v) for v in s.values))
            return
        self.line(", ".join([kw, *opts]))
        mem = s.members.tolist()
        if not mem:
            raise WriteError(f"set {s.name} is empty (numgeo rejects empty sets)")
        for i in range(0, len(mem), _PER_LINE):
            self.line(", ".join(map(str, mem[i : i + _PER_LINE])))

    def amplitude(self, a: Amplitude) -> None:
        self.line(f"*Amplitude, name={a.name}, type={a.type.lower()}")
        for row in a.data:
            self.line(", ".join(self.token(t) for t in row))

    def material(self, m: Material) -> None:
        opts = [f"name={m.name}"]
        if m.phases is not None:
            opts.append(f"phases={m.phases}")
        opts += [self.option(k, v) for k, v in m.extra_options]
        self.line(", ".join(["*Material", *opts]))
        for p in m.properties:
            self.keyword(p, "material")

    def section(self, s: Section) -> None:
        opts = [f"elset={s.elset}", f"material={s.material}"]
        if s.amgcl_direct:
            opts.append("amgcl=direct")
        self.line(", ".join([display_keyword(s.keyword), *opts]))

    def step(self, s: Step) -> None:
        opts = [f"name={s.name}"]
        if s.scalefactor is not None:
            opts.append(f"scalefactor={format_real(s.scalefactor)}")
        if s.inc is not None:
            opts.append(f"inc={s.inc}")
        if s.maxiter is not None:
            opts.append(f"maxiter={s.maxiter}")
        if s.miniter is not None:
            opts.append(f"miniter={s.miniter}")
        if s.nlgeom:
            opts.append("nlgeom")
        if s.nocutback:
            opts.append("nocutback")
        opts += [self.option(k, v) for k, v in s.extra_options]
        self.line(", ".join(["*Step", *opts]))
        self.keyword(s.procedure, "step-procedure")
        for kw in s.items:
            self.keyword(kw, "step")
        self.line("*End step")

    def run(self, header: bool) -> str:
        risky = [(kind, name, risky_words(kind, name)) for kind, name in named_objects(self.deck)]
        risky = [r for r in risky if r[2]]
        if risky:
            listed = "; ".join(f"{k} {n!r} ({', '.join(w.lower() for w in ws)})" for k, n, ws in risky[:5])
            more = f" and {len(risky) - 5} more" if len(risky) > 5 else ""
            raise WriteError(
                f"names that numgeo would read as options: {listed}{more}. Rename them with "
                "deck.rename(old, new), or all at once with deck.safe_names() (returns the mapping)"
            )
        if header:
            self.out += input_file_header()
            for c in self.deck.comments:
                self.out.append("** " + c)
        self.mesh(self.deck.mesh)
        for a in self.deck.amplitudes:
            self.amplitude(a)
        for m in self.deck.materials:
            self.material(m)
        for s in self.deck.sections:
            self.section(s)
        for kw in self.deck.keywords:
            self.keyword(kw, "model")
        for st in self.deck.steps:
            self.step(st)
        self.out.append("*End input")
        return "\n".join(self.out) + "\n"


def _output_context(kw: Keyword) -> str:
    keys = {k for k, _ in kw.options}
    if any("FIELD" in k for k in keys):
        return "output-field"
    if any("PRINT" in k for k in keys):
        return "output-print"
    return "output-user"


def write_text(deck: Deck, *, header: bool = True) -> str:
    """The input file text of ``deck`` (see module docstring)."""
    return _Writer(deck).run(header)


def write(deck: Deck, path: str | os.PathLike[str], *, header: bool = True) -> Path:
    """Write ``deck`` to ``path`` (UTF-8 without BOM, ``\\n`` line ends) and return the path.

    Missing parent folders are created.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(write_text(deck, header=header), encoding="utf-8", newline="\n")
    return p
