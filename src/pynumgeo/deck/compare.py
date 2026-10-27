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
"""Differences between two decks as numgeo reads them, for people and tests.

``deck_a == deck_b`` says whether two decks mean the same; :func:`diff` says where they differ. Reals are
compared with a relative tolerance (``rtol``; node coordinates relative to the size of the model), so that a deck
written with fewer digits compares equal to its exact counterpart. Spelling (case, blanks), source positions and
comments are ignored, as numgeo ignores them.

Examples:
    >>> from pynumgeo.deck import Deck, Keyword, Step
    >>> a = Deck(); b = Deck()
    >>> for d, v in ((a, -200.0), (b, -200.00001)):
    ...     d.steps.append(Step(name="Load", procedure=Keyword.make("*Static", data=[[0.1, 1.0, 0.01, 0.1]]),
    ...                         items=[Keyword.make("*Dsload", options=["ramp"], data=[["Top", "P", v]])]))
    >>> diff(a, b)
    ["step Load[0]/*DSLOAD: data line 1: ['Top', 'P', -200.0] != ['Top', 'P', -200.00001]"]
    >>> diff(a, b, rtol=1e-6)
    []
"""

from __future__ import annotations

import numpy as np

from pynumgeo.deck.deck import Deck
from pynumgeo.deck.keyword import Keyword, Token
from pynumgeo.io.numbers import is_number, parse_real

__all__ = ["diff"]


def _up(v: str | None) -> str | None:
    return None if v is None else v.upper().replace(" ", "")


def _feq(a: float, b: float, rtol: float) -> bool:
    return a == b or abs(a - b) <= rtol * max(abs(a), abs(b))


def _tok_eq(a: Token, b: Token, rtol: float) -> bool:
    if isinstance(a, str) or isinstance(b, str):
        return isinstance(a, str) and isinstance(b, str) and _up(a) == _up(b)
    if isinstance(a, int) and isinstance(b, int):
        return a == b
    return _feq(float(a), float(b), rtol)


def _val_eq(a: str | None, b: str | None, rtol: float) -> bool:
    if a is not None and b is not None and is_number(a) and is_number(b):
        return _feq(parse_real(a), parse_real(b), rtol)
    return _up(a) == _up(b)


def _keyword(a: Keyword, b: Keyword, path: str, rtol: float, out: list[str]) -> None:
    if a.keyword != b.keyword:
        out.append(f"{path}: keyword {a.keyword} != {b.keyword}")
        return
    p = f"{path}/{a.keyword}"
    if not _val_eq(a.value, b.value, rtol):
        out.append(f"{p}: value {a.value!r} != {b.value!r}")
    if [k for k, _ in a.options] != [k for k, _ in b.options]:
        out.append(f"{p}: options {a.options} != {b.options}")
    else:
        for (k, va), (_, vb) in zip(a.options, b.options, strict=True):
            if not _val_eq(va, vb, rtol):
                out.append(f"{p}: option {k}={va!r} != {vb!r}")
    if len(a.data) != len(b.data):
        out.append(f"{p}: {len(a.data)} data lines != {len(b.data)}")
    else:
        for i, (ra, rb) in enumerate(zip(a.data, b.data, strict=True)):
            if len(ra) != len(rb) or not all(_tok_eq(x, y, rtol) for x, y in zip(ra, rb, strict=True)):
                out.append(f"{p}: data line {i + 1}: {ra} != {rb}")
    _keywords(a.children, b.children, p, rtol, out)


def _keywords(a: list[Keyword], b: list[Keyword], path: str, rtol: float, out: list[str]) -> None:
    if [k.keyword for k in a] != [k.keyword for k in b]:
        out.append(f"{path}: keywords {[k.keyword for k in a]} != {[k.keyword for k in b]}")
        return
    for i, (x, y) in enumerate(zip(a, b, strict=True)):
        _keyword(x, y, f"{path}[{i}]", rtol, out)


def _mesh(a: Deck, b: Deck, rtol: float, out: list[str]) -> None:
    ma, mb = a.mesh, b.mesh
    if not np.array_equal(ma.node_labels, mb.node_labels):
        out.append(f"mesh: node labels differ ({ma.node_count} / {mb.node_count} nodes)")
    elif ma.coords.shape != mb.coords.shape:
        out.append(f"mesh: coordinates of shape {ma.coords.shape} != {mb.coords.shape}")
    elif ma.node_count:
        scale = float(np.abs(ma.coords).max())
        dev = float(np.abs(ma.coords - mb.coords).max())
        if dev > rtol * scale:
            node = int(ma.node_labels[int(np.argmax(np.abs(ma.coords - mb.coords).max(axis=1)))])
            out.append(f"mesh: coordinates differ by up to {dev:.6g} (node {node}, model size {scale:.6g})")
    ka = [(x.type.lower(), x.labels.size) for x in ma.blocks]
    kb = [(x.type.lower(), x.labels.size) for x in mb.blocks]
    if ka != kb:
        out.append(f"mesh: element blocks {ka} != {kb}")
    else:
        for ba, bb in zip(ma.blocks, mb.blocks, strict=True):
            if ba != bb:
                out.append(f"mesh: element block {ba.type.lower()} differs (labels, connectivity or options)")
    for kind, sa, sb in (("node set", ma.nsets, mb.nsets), ("element set", ma.elsets, mb.elsets)):
        if [s.key for s in sa] != [s.key for s in sb]:
            out.append(f"mesh: {kind}s {[s.name for s in sa]} != {[s.name for s in sb]}")
            continue
        for la, lb in zip(sa, sb, strict=True):
            if la != lb:
                out.append(f"mesh: {kind} {la.name} differs")
    if [s.key for s in ma.surfaces] != [s.key for s in mb.surfaces]:
        out.append(f"mesh: surfaces {[s.name for s in ma.surfaces]} != {[s.name for s in mb.surfaces]}")
    else:
        for fa, fb in zip(ma.surfaces, mb.surfaces, strict=True):
            if fa != fb:
                out.append(f"mesh: surface {fa.name}: {fa.type} {fa.rows} != {fb.type} {fb.rows}")


def diff(a: Deck, b: Deck, *, rtol: float = 0.0) -> list[str]:
    """Where ``b`` differs from ``a``, one line per difference (empty: the decks mean the same).

    Args:
        rtol: relative tolerance of reals (node coordinates: relative to the largest coordinate).
    """
    out: list[str] = []
    _mesh(a, b, rtol, out)
    if [x.name.upper() for x in a.amplitudes] != [x.name.upper() for x in b.amplitudes]:
        out.append(f"amplitudes {[x.name for x in a.amplitudes]} != {[x.name for x in b.amplitudes]}")
    else:
        for aa, ab in zip(a.amplitudes, b.amplitudes, strict=True):
            _keyword(
                Keyword(keyword="*AMPLITUDE", options=[("NAME", aa.name), ("TYPE", aa.type)], data=aa.data),
                Keyword(keyword="*AMPLITUDE", options=[("NAME", ab.name), ("TYPE", ab.type)], data=ab.data),
                "amplitude",
                rtol,
                out,
            )
    if [x.name.upper() for x in a.materials] != [x.name.upper() for x in b.materials]:
        out.append(f"materials {[x.name for x in a.materials]} != {[x.name for x in b.materials]}")
    else:
        for ma, mb in zip(a.materials, b.materials, strict=True):
            if (ma.phases or 1) != (mb.phases or 1):
                out.append(f"material {ma.name}: phases {ma.phases} != {mb.phases}")
            if [k for k, _ in ma.extra_options] != [k for k, _ in mb.extra_options]:
                out.append(f"material {ma.name}: options {ma.extra_options} != {mb.extra_options}")
            _keywords(ma.properties, mb.properties, f"material {ma.name}", rtol, out)
    if a.sections != b.sections:
        out.append(
            f"assignments {[(s.elset, s.material, s.amgcl_direct) for s in a.sections]} != "
            f"{[(s.elset, s.material, s.amgcl_direct) for s in b.sections]}"
        )
    _keywords(a.keywords, b.keywords, "model", rtol, out)
    if [s.name.upper() for s in a.steps] != [s.name.upper() for s in b.steps]:
        out.append(f"steps {[s.name for s in a.steps]} != {[s.name for s in b.steps]}")
        return out
    for x, y in zip(a.steps, b.steps, strict=True):
        hx = (x.inc, x.maxiter, x.miniter, x.nlgeom, x.nocutback)
        hy = (y.inc, y.maxiter, y.miniter, y.nlgeom, y.nocutback)
        sf = (x.scalefactor is None) == (y.scalefactor is None) and (
            x.scalefactor is None or y.scalefactor is None or _feq(x.scalefactor, y.scalefactor, rtol)
        )
        if hx != hy or not sf:
            out.append(f"step {x.name}: header {hx} scalefactor {x.scalefactor} != {hy} scalefactor {y.scalefactor}")
        if [k for k, _ in x.extra_options] != [k for k, _ in y.extra_options]:
            out.append(f"step {x.name}: options {x.extra_options} != {y.extra_options}")
        _keyword(x.procedure, y.procedure, f"step {x.name}/procedure", rtol, out)
        _keywords(x.items, y.items, f"step {x.name}", rtol, out)
    return out
