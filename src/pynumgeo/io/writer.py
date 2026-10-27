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

Comments: the ``comment`` of a keyword, element block, set, surface, material, amplitude, section or step
is written above it as ``**`` lines (``comments=False`` leaves them out). Include files: :func:`write_texts`
and ``write(..., includes=...)`` put the mesh and the materials into files of their own that the main file
includes, the numgeo-GiD layout.

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
import textwrap
from collections.abc import Mapping
from pathlib import Path

import numpy as np

from pynumgeo import catalogue as _cat
from pynumgeo._provenance import input_file_header
from pynumgeo.deck.deck import Amplitude, Deck, Material, Section, Step
from pynumgeo.deck.keyword import Keyword, Token
from pynumgeo.deck.names import named_objects, risky_words
from pynumgeo.io.numbers import format_real
from pynumgeo.mesh.mesh import ElementSet, Mesh, NodeSet

__all__ = [
    "PARTS",
    "WriteError",
    "display_keyword",
    "format_keyword",
    "format_material",
    "write",
    "write_text",
    "write_texts",
]

MAX_LINE = 256
_PER_LINE = 16  # set members per line
_COMMENT_WIDTH = 120  # comment lines are wrapped at this width (numgeo ignores them)
#: Parts of a deck that can be written to include files (:func:`write_texts`): ``mesh`` = nodes, elements,
#: sets and surfaces; ``materials`` = the ``*Material`` blocks.
PARTS = ("mesh", "materials")


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
    def __init__(self, deck: Deck, comments: bool = True, names: set[str] | None = None) -> None:
        self.deck = deck
        self.names = deck.defined_names() if names is None else names
        self.comments = comments
        self.out: list[str] = []

    # ------------------------------------------------------------------ helpers
    def line(self, text: str) -> None:
        if len(text) > MAX_LINE:
            raise WriteError(f"line longer than {MAX_LINE} characters: {text[:60]}...")
        self.out.append(text)

    def comment(self, text: str | None) -> None:
        """``text`` as ``**`` lines (wrapped, a blank line before them); numgeo ignores everything after ``**``."""
        if not self.comments or not text:
            return
        if self.out and self.out[-1] != "" and not self.out[-1].startswith("**"):
            self.out.append("")
        for para in text.splitlines():
            for ln in textwrap.wrap(para, _COMMENT_WIDTH, break_long_words=True, break_on_hyphens=False) or [""]:
                self.out.append(("** " + ln).rstrip())

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
        self.comment(kw.comment)
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
            self.comment(m.comment)
            self.line("*Node")
            for lab, xyz in zip(m.node_labels.tolist(), m.coords.tolist(), strict=True):
                self.line(", ".join([str(lab), *(format_real(x) for x in xyz)]))
        for b in m.blocks:
            self.comment(b.comment)
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
            self.comment(sf.comment)
            self.line(f"*Surface, type={sf.type}, name={sf.name}")
            for r in sf.rows:
                self.line(", ".join(self.word(x) if i else x for i, x in enumerate(r)))

    def label_set(self, kw: str, key: str, s: NodeSet | ElementSet) -> None:
        self.comment(s.comment)
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
        self.comment(a.comment)
        self.line(f"*Amplitude, name={a.name}, type={a.type.lower()}")
        for row in a.data:
            self.line(", ".join(self.token(t) for t in row))

    def material(self, m: Material) -> None:
        self.comment(m.comment)
        opts = [f"name={m.name}"]
        if m.phases is not None:
            opts.append(f"phases={m.phases}")
        opts += [self.option(k, v) for k, v in m.extra_options]
        self.line(", ".join(["*Material", *opts]))
        for p in m.properties:
            self.keyword(p, "material")

    def section(self, s: Section) -> None:
        self.comment(s.comment)
        opts = [f"elset={s.elset}", f"material={s.material}"]
        if s.amgcl_direct:
            opts.append("amgcl=direct")
        self.line(", ".join([display_keyword(s.keyword), *opts]))

    def step(self, s: Step) -> None:
        self.comment(s.comment)
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

    def check_names(self) -> None:
        risky = [(kind, name, risky_words(kind, name)) for kind, name in named_objects(self.deck)]
        risky = [r for r in risky if r[2]]
        if risky:
            listed = "; ".join(f"{k} {n!r} ({', '.join(w.lower() for w in ws)})" for k, n, ws in risky[:5])
            more = f" and {len(risky) - 5} more" if len(risky) > 5 else ""
            raise WriteError(
                f"names that numgeo would read as options: {listed}{more}. Rename them with "
                "deck.rename(old, new), or all at once with deck.safe_names() (returns the mapping)"
            )

    def run(self, header: bool, includes: Mapping[str, str] | None = None) -> dict[str, str]:
        """Texts of the main file (``"main"``) and of the parts written to include files."""
        self.check_names()
        includes = dict(includes or {})
        unknown = sorted(set(includes) - set(PARTS))
        if unknown:
            raise WriteError(f"unknown include parts {unknown}; the parts are {list(PARTS)}")
        seen: set[str] = set()
        for part, name in includes.items():
            _check_include_name(part, name)
            if name.lower() in seen:
                raise WriteError(f"two parts are written to the same include file {name!r}")
            seen.add(name.lower())
        files: dict[str, list[str]] = {"main": []}

        def target(part: str) -> list[str]:
            if part not in includes:
                return files["main"]
            if part not in files:
                files[part] = input_file_header() if header else []
                files["main"].append(f"*Include, input={includes[part]}")
            return files[part]

        self.out = files["main"]
        if header:
            self.out += input_file_header()
            for c in self.deck.comments:
                self.out.append("** " + c)
        self.out = target("mesh")
        self.mesh(self.deck.mesh)
        self.out = files["main"]
        for a in self.deck.amplitudes:
            self.amplitude(a)
        self.out = target("materials")
        for m in self.deck.materials:
            self.material(m)
        self.out = files["main"]
        for s in self.deck.sections:
            self.section(s)
        for kw in self.deck.keywords:
            self.keyword(kw, "model")
        for st in self.deck.steps:
            self.step(st)
        self.comment(self.deck.end_comment)
        self.out.append("*End input")
        return {part: "\n".join(lines) + "\n" for part, lines in files.items()}


def _check_include_name(part: str, name: str) -> None:
    """numgeo opens ``<text after '='>.inp`` from the run folder; the name must survive that unchanged."""
    bad = [c for c in (" ", "\t", ",", "*", "$", "=", "/", "\\") if c in name]
    if not name or bad or name.lower().endswith(".inp"):
        why = "is empty" if not name else (f"contains {bad[0]!r}" if bad else "ends in .inp (numgeo adds .inp)")
        raise WriteError(f"include name {name!r} for part {part!r} {why}")


def _output_context(kw: Keyword) -> str:
    keys = {k for k, _ in kw.options}
    if any("FIELD" in k for k in keys):
        return "output-field"
    if any("PRINT" in k for k in keys):
        return "output-print"
    return "output-user"


def write_text(deck: Deck, *, header: bool = True, comments: bool = True) -> str:
    """The input file text of ``deck`` (see module docstring).

    Args:
        header: write the provenance header and ``deck.comments``.
        comments: write the ``comment`` of the deck's objects as ``**`` lines above them.
    """
    return _Writer(deck, comments).run(header)["main"]


def write_texts(
    deck: Deck, *, includes: Mapping[str, str], header: bool = True, comments: bool = True
) -> dict[str, str]:
    """The text of the main file and of include files, the numgeo-GiD layout of an input deck.

    ``includes`` maps parts of the deck (:data:`PARTS`) to include names: ``{"mesh": "model-mesh",
    "materials": "material-definitions"}`` moves the mesh to ``model-mesh.inp`` and the materials to
    ``material-definitions.inp``; the main file includes them (``*Include, input=model-mesh``) where they
    stood. numgeo copies an include into the input before it reads it, so the files mean the same as the
    single file of :func:`write_text`, and :func:`~pynumgeo.parse` reads them back.

    Returns:
        ``{"main": text, "<part>": text, ...}``; included files carry the header but no ``*End input``.

    >>> from pynumgeo.deck import Deck
    >>> d = Deck()
    >>> _ = d.mesh.add_nodes([[0, 0], [1, 0]]); _ = d.mesh.add_elements("u2-truss", [[1, 2]])
    >>> texts = write_texts(d, includes={"mesh": "model-mesh"}, header=False)
    >>> print(texts["main"] + texts["mesh"])
    *Include, input=model-mesh
    *End input
    *Node
    1, 0.0, 0.0
    2, 1.0, 0.0
    *Element, type=u2-truss
    1, 1, 2
    <BLANKLINE>
    """
    return _Writer(deck, comments).run(header, includes)


def write(
    deck: Deck,
    path: str | os.PathLike[str],
    *,
    header: bool = True,
    comments: bool = True,
    includes: Mapping[str, str] | None = None,
) -> Path:
    """Write ``deck`` to ``path`` (UTF-8 without BOM, ``\\n`` line ends) and return the path.

    With ``includes`` (see :func:`write_texts`) the parts are written next to ``path`` as
    ``<include name>.inp``. Missing parent folders are created.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    texts = _Writer(deck, comments).run(header, includes)
    for part, text in texts.items():
        target = p if part == "main" else p.parent / (dict(includes or {})[part] + ".inp")
        target.write_text(text, encoding="utf-8", newline="\n")
    return p


def format_keyword(kw: Keyword, context: str | None = None, *, names: set[str] | frozenset[str] = frozenset()) -> str:
    """One keyword (with its data lines and children) as the writer spells it, e.g. for a preview.

    ``names`` are kept in their spelling (upper-case keys are matched); other words are written in lower case.

    >>> print(format_keyword(Keyword.make("*Boundary", data=[["Fix", "U1", 0.0]]), names={"FIX"}), end="")
    *Boundary
    Fix, u1, 0.0
    """
    w = _Writer(Deck(), True, {n.upper().replace(" ", "") for n in names})
    w.keyword(kw, context)
    return "\n".join(w.out) + "\n"


def format_material(m: Material, *, names: set[str] | frozenset[str] = frozenset()) -> str:
    """A ``*Material`` block as the writer spells it (preview of a material)."""
    w = _Writer(Deck(), True, {n.upper().replace(" ", "") for n in names} | {m.name.upper().replace(" ", "")})
    w.material(m)
    return "\n".join(w.out) + "\n"
