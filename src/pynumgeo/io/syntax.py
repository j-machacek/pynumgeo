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
"""Keyword blocks: the internal lines grouped the way numgeo's readers consume them.

A :class:`KeywordBlock` is a keyword line, its data lines (the following lines that do not start with
``*``) and, for container keywords, its child blocks:

=====================  ==============================================================================
container              children
=====================  ==============================================================================
``*STEP``              every block up to ``*ENDSTEP`` (``src/input/read_step_.f90``)
``*PART``              blocks up to ``*ENDPART``; ``*INSTANCE`` / ``*ASSEMBLY`` likewise
``*MATERIAL``          the following material sub-keywords (``src/input/read_material_.f90``)
``*INTERACTION``       ``*NORMAL`` / ``*FRICTION`` lines that follow
``*OUTPUT``            ``*FREQUENCY``, ``*NODE[OUTPUT]``, ``*ELEMENT[OUTPUT]``, ``*INTEGRATIONPOINT``
``*DYNAMIC``           ``*HILBER-HUGHES-TAYLOR`` / ``*HHT`` / ``*BACKWARDEULER`` / ``*BWE``
``*EXPLICITDYNAMIC``   ``*MASSSCALING``
``*EQUATION``          ``*PENALTY`` (also under ``*RIGIDBODY``)
=====================  ==============================================================================

The grouping is purely syntactic; whether numgeo accepts a block is decided by the reader and the
validator.

Examples:
    >>> from pynumgeo.io.lexer import preprocess_text
    >>> blocks = parse_blocks(preprocess_text(
    ...     "*Material, name=Soil\\n*Density\\n2.0\\n*Step, name=S1\\n*Static\\n1,1,1,1\\n*End step\\n").lines)
    >>> [(b.keyword, [c.keyword for c in b.children]) for b in blocks]
    [('*AMPLITUDE', []), ('*MATERIAL', ['*DENSITY']), ('*STEP', ['*STATIC', '*ENDSTEP'])]
    >>> blocks[1].option("NAME").value_cased
    'Soil'
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from pynumgeo.io.lexer import Line, SourcePos

__all__ = ["KeywordBlock", "Option", "parse_blocks", "split_options"]

MATERIAL_CHILDREN = frozenset(
    {
        "*THERMALCONDUCTIVITY", "*SPECIFICHEAT", "*THERMALCAPACITY", "*THERMALSTABILISATION",
        "*MECHANICAL", "*USERPROPERTIES", "*OPTIONALMECHANICALPARAMETER", "*HYDRAULICITERATION",
        "*HYDRAULIC", "*JACOBIAN", "*RELATIVEPERMEABILITY", "*RESIDUALAIRMASSTRANSFER", "*SWELLING",
        "*BISHOPEFFECTIVESTRESS", "*DENSITY", "*PERMEABILITY", "*BULKMODULUS", "*SOLIDBULKMODULUS",
        "*CAVITATION", "*DYNAMICVISCOSITY", "*MECHANICALVISCOSITY", "*PHANTOMELASTICITY",
        "*MINPRESSURE", "*MINIMUMEPSAMPL", "*MAXIMUMEPSAMPL", "*IMPLICITHCASTEPS",
        "*RECORDINGHCASTEPS", "*EXPLICITHCASTEPS", "*HCACYCLETIME", "*HCARECORDINGTIME", "*DAMPING",
        "*VISCOUSDAMPING", "*ADAPTIVESTRAINAMPL", "*REDUCIBLESTRENGTH", "*HOURGLASS",
        "*FPL-STABILISATION", "*PPP-STABILISATION", "*TRUSSPROPERTIES", "*BEAMPROPERTIES",
        "*SHELLPROPERTIES",
    }
)  # fmt: skip
INTERACTION_CHILDREN = frozenset({"*NORMAL", "*FRICTION"})
OUTPUT_CHILDREN = frozenset({"*FREQUENCY", "*NODE", "*NODEOUTPUT", "*ELEMENT", "*ELEMENTOUTPUT", "*INTEGRATIONPOINT"})
DYNAMIC_CHILDREN = frozenset({"*HILBER-HUGHES-TAYLOR", "*HHT", "*BACKWARDEULER", "*BWE"})
EXPLICIT_CHILDREN = frozenset({"*MASSSCALING"})
EQUATION_CHILDREN = frozenset({"*PENALTY"})
_ENDS = {"*STEP": "*ENDSTEP", "*PART": "*ENDPART", "*INSTANCE": "*ENDINSTANCE", "*ASSEMBLY": "*ENDASSEMBLY"}
_FOLLOWERS = {
    "*MATERIAL": MATERIAL_CHILDREN,
    "*INTERACTION": INTERACTION_CHILDREN,
    "*OUTPUT": OUTPUT_CHILDREN,
    "*DYNAMIC": DYNAMIC_CHILDREN,
    "*EXPLICITDYNAMIC": EXPLICIT_CHILDREN,
    "*EXPLICITDYNAMICS": EXPLICIT_CHILDREN,
    "*EQUATION": EQUATION_CHILDREN,
    "*RIGIDBODY": EQUATION_CHILDREN,
}


def split_options(text: str) -> list[str]:
    """Split at commas that are not inside a ``$...$`` string.

    >>> split_options("*SOLVER,EXTERNAL,ARG=$-A,-B$,MPI=2")
    ['*SOLVER', 'EXTERNAL', 'ARG=$-A,-B$', 'MPI=2']
    """
    if "$" not in text:
        return text.split(",")
    parts: list[str] = []
    cur: list[str] = []
    inside = False
    for ch in text:
        if ch == "$":
            inside = not inside
        if ch == "," and not inside:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


@dataclass(frozen=True)
class Option:
    """One comma-separated option of a keyword line.

    ``key`` is the text before the first ``=`` (upper-case), ``value`` the text after it (``None`` for a
    flag). The ``*_cased`` variants keep the user's spelling.
    """

    key: str
    value: str | None
    key_cased: str
    value_cased: str | None

    @property
    def token(self) -> str:
        """The whole option as numgeo sees it."""
        return self.key if self.value is None else f"{self.key}={self.value}"


def _option(text: str, cased: str) -> Option:
    eq = text.find("=")
    if eq < 0:
        return Option(text, None, cased, None)
    return Option(text[:eq], text[eq + 1 :], cased[:eq], cased[eq + 1 :])


@dataclass
class KeywordBlock:
    """A keyword line with its data lines and child blocks.

    Attributes:
        line: the keyword line.
        keyword: upper-case keyword without options, e.g. ``*STEP`` or ``*MECHANICAL``.
        value: text after ``=`` in the keyword itself (``*MECHANICAL=MOHR-COULOMB``), upper-case.
        value_cased: ``value`` in the user's spelling.
        options: the comma-separated options after the keyword.
        data: data lines (lines not starting with ``*``).
        children: child blocks of a container keyword.
    """

    line: Line
    keyword: str
    value: str | None
    value_cased: str | None
    options: list[Option]
    data: list[Line] = field(default_factory=list)
    children: list[KeywordBlock] = field(default_factory=list)

    @property
    def pos(self) -> SourcePos | None:
        """Source position of the keyword line."""
        return self.line.pos

    @property
    def option_text(self) -> str:
        """Upper-case text after the first comma (what many numgeo readers search with ``index``)."""
        t = self.line.text
        c = t.find(",")
        return t[c + 1 :] if c >= 0 else ""

    def option(self, key: str) -> Option | None:
        """First option whose key equals ``key`` exactly (upper-case comparison)."""
        k = key.upper()
        for o in self.options:
            if o.key == k:
                return o
        return None

    def has_flag(self, key: str) -> bool:
        """True if an option with exactly this key is present (with or without value)."""
        return self.option(key) is not None

    def data_tokens(self) -> Iterator[tuple[Line, list[str], list[str]]]:
        """Data lines split at commas: ``(line, tokens, cased tokens)``."""
        for ln in self.data:
            yield ln, split_options(ln.text), split_options(ln.cased)

    def walk(self) -> Iterator[KeywordBlock]:
        """This block and all descendants, depth first."""
        yield self
        for c in self.children:
            yield from c.walk()


def _make_block(line: Line) -> KeywordBlock:
    parts = split_options(line.text)
    cparts = split_options(line.cased)
    head, chead = parts[0], cparts[0]
    eq = head.find("=")
    if eq >= 0:
        keyword, value, value_cased = head[:eq], head[eq + 1 :], chead[eq + 1 :]
    else:
        keyword, value, value_cased = head, None, None
    opts = [_option(t, c) for t, c in zip(parts[1:], cparts[1:], strict=True)]
    return KeywordBlock(line=line, keyword=keyword, value=value, value_cased=value_cased, options=opts)


def _flat_blocks(lines: Sequence[Line]) -> list[KeywordBlock]:
    blocks: list[KeywordBlock] = []
    orphan: list[Line] = []
    for ln in lines:
        if ln.is_keyword:
            blocks.append(_make_block(ln))
        elif blocks:
            blocks[-1].data.append(ln)
        else:
            orphan.append(ln)
    if orphan:  # numeric lines before any keyword: numgeo skips lines whose first token is numeric
        raise ValueError(f"{orphan[0].pos}: data line before the first keyword")
    return blocks


def _group(flat: list[KeywordBlock], start: int, stop_kw: str | None) -> tuple[list[KeywordBlock], int]:
    out: list[KeywordBlock] = []
    i = start
    while i < len(flat):
        b = flat[i]
        if stop_kw is not None and b.keyword == stop_kw:
            return out, i
        i += 1
        if b.keyword in _ENDS:
            end_kw = _ENDS[b.keyword]
            kids, j = _group(flat, i, end_kw)
            b.children = kids
            if j < len(flat):  # the end keyword itself becomes the last child
                b.children.append(flat[j])
                i = j + 1
            else:
                i = j
        elif b.keyword in _FOLLOWERS:
            allowed = _FOLLOWERS[b.keyword]
            while i < len(flat) and flat[i].keyword in allowed:
                child = flat[i]
                i += 1
                if child.keyword in _FOLLOWERS:  # e.g. none today, kept general
                    pass
                b.children.append(child)
        out.append(b)
    return out, i


def parse_blocks(lines: Sequence[Line]) -> list[KeywordBlock]:
    """Group internal lines into a tree of :class:`KeywordBlock` (see the module docstring).

    Raises:
        ValueError: if a data line comes before the first keyword.
    """
    blocks, _ = _group(_flat_blocks(lines), 0, None)
    return blocks
