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
"""Names that numgeo reads as options, and renaming them throughout a deck.

numgeo finds the options of a keyword line by searching for words inside each option's text. A
name that contains such a word switches the option on: ``*Nset, nset=FindFix`` is read as a ``find``
set, ``*Nset, nset=BodenInstance.All`` as a set of an instance whose name is then empty (numgeo stops).
:data:`RISKY_WORDS` lists the words per kind of name, from the readers of the keywords:

* node and element sets: ``src/input/read_set_.f90:123-152, 558-582``; element sets also ``MATERIAL``
  (``*Solid section`` reads ``ELSET``/``MATERIAL`` by substring);
* surfaces, materials, amplitudes: the option tests of their readers (``read_surface_``,
  ``read_material_``, ``read_amplitude_``);
* interactions: their name stands in ``*Interaction, name=``, ``*Contact pair, interaction=`` and
  ``*Contact options, name=``, and each of these readers searches its own words in it
  (``read_interaction_.f90:425-512``, ``read_contact_pairing_.f90:80-154``, ``read_contact_options_.f90:99-123``).

Sets that pynumgeo creates when it flattens parts and instances are named ``<instance>.<set>`` like
numgeo's internal names; written as a flat deck, an instance name such as ``BodenInstance`` puts the
word ``INSTANCE`` into the set's option text. :func:`safe_names` renames all such names (and every
reference to them) and returns the mapping.

Examples:
    >>> risky_words("node set", "FindFix")
    ['FIND']
    >>> safe_name("node set", "BodenInstance.All")
    'BodenInst.All'
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from pynumgeo.deck.deck import Deck
    from pynumgeo.deck.keyword import Keyword

__all__ = ["RISKY_WORDS", "named_objects", "rename", "risky_words", "safe_name", "safe_names"]

#: Words that numgeo reads as options when they occur in a name, per kind of name. ``INCLUDE`` makes the
#: whole line an include (input_create_internal_input_.f90:71) and is risky for every kind.
RISKY_WORDS: dict[str, tuple[str, ...]] = {
    "node set": ("GENERATE", "INTERNAL", "INSTANCE", "FIND", "BOUNDINGBOX", "CYLINDER", "INCLUDE"),
    "element set": ("GENERATE", "INTERNAL", "INSTANCE", "FIND", "BOUNDINGBOX", "MATERIAL", "INCLUDE"),
    "surface": ("TYPE", "INSTANCE", "INCLUDE"),
    "material": ("ELSET", "PHASES", "INCLUDE"),
    "amplitude": ("NAME", "TYPE", "VELOCITY", "ACCELERATION", "HYDROSTATIC", "INCREMENT", "INSTANT", "INCLUDE"),
    "interaction": (
        # *Interaction, name=... (read_normal_contact_setting)
        "USER",
        "NORMAL",
        "MECHANICAL",
        "NOSEPARATION",
        "STIFFNESS_FACTOR",
        "NONCONSTANT",
        "VISCOUS",
        "WATER-FILLEDGAP",
        "WATERFILLEDGAP",
        # *Contact pair, interaction=... (read_contact_pairing)
        "ADJUST",
        "PERTURBATION",
        "REFINE",
        "GENERAL",
        "NIGP",
        "NGP",
        "NLGEOM",
        "DOUBLEPASS",
        # *Contact options, name=... (read_contact_options)
        "CLEARANCE",
        "CHECKDISP",
        "CHECKDIST",
        "REDUCTION",
        "INCLUDE",
    ),
    "step": ("INCLUDE",),
}

_SHORT = {
    "GENERATE": "Gen",
    "INTERNAL": "Intl",
    "INSTANCE": "Inst",
    "FIND": "Fnd",
    "BOUNDINGBOX": "Bbox",
    "CYLINDER": "Cyl",
    "MATERIAL": "Mat",
    "TYPE": "Typ",
    "ELSET": "Elst",
    "PHASES": "Phs",
    "NAME": "Nam",
    "VELOCITY": "Vel",
    "ACCELERATION": "Acc",
    "HYDROSTATIC": "Hydro",
    "INCREMENT": "Incr",
    "INSTANT": "Inst",
    "INCLUDE": "Incl",
    "USER": "Usr",
    "NORMAL": "Nrml",
    "MECHANICAL": "Mech",
    "NOSEPARATION": "NoSep",
    "STIFFNESS_FACTOR": "Stiff_fac",
    "NONCONSTANT": "NonConst",
    "VISCOUS": "Visc",
    "WATER-FILLEDGAP": "Water-gap",
    "WATERFILLEDGAP": "WaterGap",
    "ADJUST": "Adj",
    "PERTURBATION": "Pert",
    "REFINE": "Refn",
    "GENERAL": "Genl",
    "NIGP": "N_igp",
    "NGP": "N_gp",
    "NLGEOM": "Nl_geom",
    "DOUBLEPASS": "Dbl_pass",
    "CLEARANCE": "Clr",
    "CHECKDISP": "ChkDisp",
    "CHECKDIST": "ChkDist",
    "REDUCTION": "Redn",
}


def _key(name: str) -> str:
    return name.upper().replace(" ", "")


def risky_words(kind: str, name: str) -> list[str]:
    """The words of ``RISKY_WORDS[kind]`` that occur in ``name`` (case-insensitive, blanks removed)."""
    k = _key(name)
    return [w for w in RISKY_WORDS[kind] if w in k]


def safe_name(kind: str, name: str) -> str:
    """``name`` with every risky word replaced by a short form (``Instance`` -> ``Inst``), case kept."""
    out = name
    for _ in range(10):  # a replacement never creates a new risky word; the loop is a safeguard
        words = risky_words(kind, out)
        if not words:
            return out
        for w in sorted(words, key=len, reverse=True):
            short = _SHORT[w]

            def repl(m: re.Match[str], short: str = short) -> str:
                return _cased(short, m.group(0))

            # numgeo deletes blanks before it searches, so the word may stand with blanks in the name
            out = re.sub(r"\s*".join(map(re.escape, w)), repl, out, flags=re.I)
    raise ValueError(f"cannot make {name!r} safe")  # pragma: no cover


def _cased(short: str, original: str) -> str:
    if original.isupper():
        return short.upper()
    if original.islower():
        return short.lower()
    if original[:1].islower():  # the word starts inside a word of the name ("LongPile" -> "Lon_gpile")
        return short[:1].lower() + short[1:]
    return short


def named_objects(deck: Deck) -> Iterator[tuple[str, str]]:
    """``(kind, name)`` of everything the deck names (sets, surfaces, materials, amplitudes, interactions,
    steps)."""
    for ns in deck.mesh.nsets:
        yield "node set", ns.name
    for es in deck.mesh.elsets:
        yield "element set", es.name
    for sf in deck.mesh.surfaces:
        yield "surface", sf.name
    for a in deck.amplitudes:
        yield "amplitude", a.name
    for m in deck.materials:
        yield "material", m.name
    for kw in deck.keywords:
        if kw.keyword == "*INTERACTION":
            name = kw.option("NAME")
            if name:
                yield "interaction", name
    for st in deck.steps:
        yield "step", st.name


def rename(deck: Deck, old: str, new: str) -> int:
    """Rename every set, surface, material, amplitude and interaction called ``old`` (case-insensitive) to
    ``new``, and every reference to it: section assignments, surface rows, option values and data-line words
    of all keywords (model, materials, steps). Returns the number of places changed.

    Step names are not renamed. A word that equals ``old`` is replaced wherever it stands, so ``old``
    should be a name, not a word with another meaning in the deck (``All`` is fine, ``u1`` is not).
    """
    k_old = _key(old)
    n = 0

    def hit(s: str | None) -> bool:
        return s is not None and _key(s) == k_old

    for s in (*deck.mesh.nsets, *deck.mesh.elsets):
        if hit(s.name):
            s.name, n = new, n + 1
    for sf in deck.mesh.surfaces:
        if hit(sf.name):
            sf.name, n = new, n + 1
        rows = [tuple(new if hit(x) else x for x in r) for r in sf.rows]
        n += sum(a != b for ra, rb in zip(rows, sf.rows, strict=True) for a, b in zip(ra, rb, strict=True))
        sf.rows = rows
    for a in deck.amplitudes:
        if hit(a.name):
            a.name, n = new, n + 1
    for m in deck.materials:
        if hit(m.name):
            m.name, n = new, n + 1
        for p in m.properties:
            n += _rename_keyword(p, hit, new)
    for sec in deck.sections:
        if hit(sec.elset):
            sec.elset, n = new, n + 1
        if hit(sec.material):
            sec.material, n = new, n + 1
    for kw in deck.keywords:
        n += _rename_keyword(kw, hit, new)
    for st in deck.steps:
        n += _rename_keyword(st.procedure, hit, new)
        for kw in st.items:
            n += _rename_keyword(kw, hit, new)
    return n


def _rename_keyword(kw: Keyword, hit: Callable[[str | None], bool], new: str) -> int:
    n = 0
    opts = [(k, new if hit(v) else v) for k, v in kw.options]
    n += sum(a != b for a, b in zip(opts, kw.options, strict=True))
    data = [[new if isinstance(t, str) and hit(t) else t for t in row] for row in kw.data]
    n += sum(a is not b for ra, rb in zip(data, kw.data, strict=True) for a, b in zip(ra, rb, strict=True))
    if n:
        kw.options = opts
        kw.data = data
    for c in kw.children:
        n += _rename_keyword(c, hit, new)
    return n


def safe_names(deck: Deck) -> dict[str, str]:
    """Rename every name that numgeo would read as an option (see :data:`RISKY_WORDS`), with all its
    references, and return ``{old: new}``. New names are unique among the deck's names.
    """
    taken = {_key(name) for _, name in named_objects(deck)}
    mapping: dict[str, str] = {}
    for kind, name in list(named_objects(deck)):
        if kind == "step" or not risky_words(kind, name) or name in mapping:
            continue
        new = safe_name(kind, name)
        base, i = new, 2
        while _key(new) in taken:
            new, i = f"{base}{i}", i + 1
        taken.add(_key(new))
        mapping[name] = new
    for old, new in mapping.items():
        rename(deck, old, new)
    return mapping
