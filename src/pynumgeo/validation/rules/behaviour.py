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
"""Rules on numgeo's behaviour in particular cases: input that numgeo rejects, ignores, clamps or reads
differently than the text suggests. Every rule names the solver source it mirrors (``source``).

Names of models that the public catalogue does not describe are compared by their hash
(:meth:`~pynumgeo.catalogue.Catalogue.is_private_name`) and never spelled out here.

Examples:
    >>> from pynumgeo.io.reader import parse_text
    >>> from pynumgeo.validation import validate
    >>> deck = parse_text("*Amplitude, name=A, type=tabular\\n0., 1.\\n").deck
    >>> [i.id for i in validate(deck, select=["NG-AMPL-101"])]
    ['NG-AMPL-101']
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Iterator

import numpy as np

from pynumgeo import catalogue as _cat
from pynumgeo.deck.deck import Deck, Material, Step
from pynumgeo.deck.keyword import Keyword, Token
from pynumgeo.validation.engine import Context, Finding, rule
from pynumgeo.validation.rules.keywords import (
    display,
    is_int_token,
    is_real_token,
    line_text,
    output_type,
)

__all__ = ["bc_type"]


# ----------------------------------------------------------------------------- helpers
_C3D20 = ("C3D20", "C3D20R")


def _key(name: str | None) -> str:
    return "" if name is None else name.upper().replace(" ", "").replace("\t", "")


def _hash(name: str) -> str:
    return hashlib.sha256(_cat.normalise_name(name).encode()).hexdigest()[:20]


# Hashes of names the public catalogue omits (catalogue ``private_name_hashes``).
_H_WITHHELD = "a797b3b5132443f92e07"  # a material model the public catalogue omits
_H_FRIC_HYPO = "973b59146abc43a961ea"  # a hypoplastic friction model without implementation
_H_FRIC_HYPO_IC = frozenset(
    {  # hypoplastic friction models that take the initial contact state
        "a9b686e099cf711a2226",
        "c2895bdb60eaeaa33581",
        "0159db5c2c0bd2eb232c",
        "ffb68991e14d625f9a53",
        "f9c5f63030358e1dc8ab",
    }
)
_H_FRIC_SANISAND = "e2da4af484ecb08eb127"  # friction model whose initial state has no effect
_H_FRIC_17 = frozenset({"c2895bdb60eaeaa33581", "0159db5c2c0bd2eb232c", "a9b686e099cf711a2226"})  # 17 values
_H_FRIC_HCA = frozenset({"ffb68991e14d625f9a53", "f9c5f63030358e1dc8ab"})  # 37 values


def _num(t: Token | None) -> float | None:
    if t is None or isinstance(t, bool):
        return None
    if isinstance(t, (int, float)):
        return float(t)
    if is_real_token(t):
        try:
            return float(t.replace("d", "e").replace("D", "E"))
        except ValueError:
            return None
    return None


def _flat(rows: Iterable[list[Token]]) -> list[Token]:
    return [t for r in rows for t in r]


def _loc(kw: Keyword, fallback: str) -> str:
    return kw.source or fallback


def _mloc(m: Material) -> str:
    return m.source or f"material {m.name}"


def _sloc(st: Step, kw: Keyword | None = None) -> str:
    if kw is not None and kw.source:
        return kw.source
    return st.source or f"step {st.name}"


def _mech(m: Material) -> str:
    p = m.property("*Mechanical")
    return _key(p.value) if p is not None else ""


def _ndim(ctx: Context) -> int:
    """numgeo's model dimension: 3 if any element type is 3D (src/input/scanning_for_numbers_.f90:217)."""
    for b in ctx.deck.mesh.blocks:
        try:
            if ctx.catalogue.element_type(b.type).ndim == 3:
                return 3
        except KeyError:
            continue
    return 2


def _etype(ctx: Context, name: str) -> _cat.ElementTypeSpec | None:
    try:
        return ctx.catalogue.element_type(name)
    except KeyError:
        return None


def _elset_members(deck: Deck, name: str) -> set[int] | None:
    """Element labels of a set, ``None`` if unknown or a query numgeo evaluates."""
    try:
        s = deck.mesh.elset(name)
    except KeyError:
        return None
    if s.kind not in ("list", "generate") and not s.members.size:
        return None
    return set(s.members.tolist())


def _nset_members(deck: Deck, name: str) -> set[int] | None:
    try:
        s = deck.mesh.nset(name)
    except KeyError:
        return None
    if s.kind not in ("list", "generate") and not s.members.size:
        return None
    return set(s.members.tolist())


def _element_types(deck: Deck) -> dict[int, str]:
    out: dict[int, str] = {}
    for b in deck.mesh.blocks:
        t = _key(b.type)
        for lab in b.labels.tolist():
            out[int(lab)] = t
    return out


def _material_types(ctx: Context) -> dict[str, set[str]]:
    """Element types per material (upper-case names), from the material assignments."""
    deck = ctx.deck
    types = _element_types(deck)
    out: dict[str, set[str]] = {}
    for s in deck.sections:
        mem = _elset_members(deck, s.elset)
        if mem is None:
            continue
        out.setdefault(_key(s.material), set()).update(types[e] for e in mem if e in types)
    return out


def _canon(ctx: Context, name: str) -> str:
    e = _etype(ctx, name)
    return _key(e.name) if e is not None else _key(name)


def _node_dofs(ctx: Context) -> dict[int, set[str]]:
    """Degrees of freedom per node label: union over the elements connected to it."""
    out: dict[int, set[str]] = {}
    for b in ctx.deck.mesh.blocks:
        e = _etype(ctx, b.type)
        if e is None:
            continue
        dofs = set(e.dofs)
        for n in np.unique(b.connectivity).tolist():
            out.setdefault(int(n), set()).update(dofs)
    return out


def _step_items(deck: Deck) -> Iterator[tuple[int, Step, int, Keyword]]:
    for si, st in enumerate(deck.steps):
        for ki, kw in enumerate(st.items):
            yield si, st, ki, kw


def _model_kws(deck: Deck, keyword: str) -> list[Keyword]:
    return [k for k in deck.keywords if k.keyword == keyword]


def _opt_text(kw: Keyword) -> str:
    """Option text as numgeo searches it (after the first comma, upper case, no blanks)."""
    t = line_text(kw)
    c = t.find(",")
    return t[c + 1 :] if c >= 0 else ""


def _has_word(kw: Keyword, word: str) -> bool:
    return word in _opt_text(kw)


# ============================================================================= model, mesh, amplitudes
@rule(
    "NG-MESH-101",
    "error",
    "bi-quadratic is not available for u4p4-sat-3d-mini",
    source="src/database/database.f90:2060-2061 (add_nodes); src/input/scanning_for_numbers_.f90:220-228",
)
def biquadratic_mini(ctx: Context) -> Iterator[Finding]:
    blocks = ctx.deck.mesh.blocks
    flagged = any(_key(k) in ("BI-QUADRATIC", "P-REFINEMENT") for b in blocks for k, _ in b.options)
    if flagged and any(_canon(ctx, b.type) == "U4P4-SAT-3D-MINI" for b in blocks):
        yield (
            "bi-quadratic (p-refinement) is requested in a model with u4p4-sat-3d-mini elements; numgeo "
            "cannot convert them (the conversion in add_nodes is unreachable)"
        )


@rule(
    "NG-MESH-102",
    "warning",
    "20-node elements with contact should be converted with bi-quadratic",
    source="src/input/scanning_for_numbers_.f90:399-411",
)
def serendipity_contact(ctx: Context) -> Iterator[Finding]:
    deck = ctx.deck
    if not _model_kws(deck, "*CONTACTPAIR"):
        return
    if any(
        _key(k) in ("BI-QUADRATIC", "P-REFINEMENT") or _key(b.type) in _C3D20
        for b in deck.mesh.blocks
        for k, _ in b.options
    ):
        return
    t20 = sorted(
        {b.type.lower() for b in deck.mesh.blocks if (e := _etype(ctx, b.type)) and e.nnodes == 20 and e.ndim == 3}
    )
    if t20:
        yield (
            f"3D elements with 20 nodes ({', '.join(t20)}) are combined with contact; convert them to "
            "27-node elements with the bi-quadratic option of *Element (numgeo's own warning is never shown)"
        )


@rule(
    "NG-MESH-103",
    "error",
    "user elements are not supported",
    source="src/input/scanning_for_numbers_.f90:206-214; src/input/read_uel_property_.f90:57-61,129",
)
def user_elements(ctx: Context) -> Iterator[Finding]:
    for i, kw in enumerate(ctx.deck.keywords):
        if kw.keyword in ("*USERELEMENT", "*UELPROPERTY"):
            yield (
                f"{display(ctx.catalogue, kw.keyword)} is not supported (user element types are never added "
                "to the element library)",
                _loc(kw, f"keywords[{i}]"),
            )


def _surface_nodes(deck: Deck, surf_rows: list[tuple[str, ...]]) -> set[int] | None:
    nodes: set[int] = set()
    for r in surf_rows:
        if not r:
            continue
        mem = _nset_members(deck, r[0])
        if mem is None:
            return None
        nodes |= mem
    return nodes


def _contact_surfaces(deck: Deck) -> set[str]:
    return {_key(str(t)) for kw in _model_kws(deck, "*CONTACTPAIR") for r in kw.data for t in r[:2]}


@rule(
    "NG-MESH-104",
    "error",
    "node-based surfaces must not take in truss or beam elements unintentionally",
    source="src/input/read_surface_.f90:238-292 (read_surface)",
)
def surface_beams(ctx: Context) -> Iterator[Finding]:
    deck = ctx.deck
    line_types = {
        _key(b.type)
        for b in deck.mesh.blocks
        if (e := _etype(ctx, b.type)) is not None and e.family.startswith(("truss", "Timoshenko beam"))
    }
    if not line_types:
        return
    contact = _contact_surfaces(deck)
    for s in deck.mesh.surfaces:
        if s.type != "node":
            continue
        nodes = _surface_nodes(deck, s.rows)
        if not nodes:
            continue
        node_list = list(nodes)
        covered = [
            (b, np.all(np.isin(b.connectivity, node_list), axis=1))
            for b in deck.mesh.blocks
            if _key(b.type) in line_types
        ]
        hit = [(b, c) for b, c in covered if c.any()]
        if not hit:
            continue
        # A surface on beams only (ground springs along a beam) is intended; mixed/contact ones are not.
        mixed = any(
            _key(b.type) not in line_types and np.isin(b.connectivity, node_list).any() for b in deck.mesh.blocks
        )
        if s.key in contact or mixed:
            b, c = hit[0]
            lab = int(b.labels[int(np.argmax(c))])
            yield (
                f"node-based surface {s.name} contains all nodes of {b.type.lower()} element {lab}; numgeo "
                "adds the truss/beam element to the surface"
                + (" used in *Contact pair" if s.key in contact else " together with the solid faces")
            )


@rule(
    "NG-MESH-105",
    "error",
    "node-based surfaces are not possible with u3p2-sat elements",
    source="src/input/read_surface_.f90:261-262; src/fem/fem_element_faces.f90:84-89",
)
def surface_u3p2(ctx: Context) -> Iterator[Finding]:
    deck = ctx.deck
    if not any(_canon(ctx, b.type) == "U3P2-SAT" for b in deck.mesh.blocks):
        return
    for s in deck.mesh.surfaces:
        if s.type == "node":
            yield (f"node-based surface {s.name} in a model with u3p2-sat elements: numgeo stops in element_face_nodes")


@rule(
    "NG-MESH-106",
    "error",
    "bi-quadratic conversion needs every element to be convertible",
    source="src/input/scanning_for_numbers_.f90:174-186,220-228,252,399-418 (scanning_for_numbers)",
)
def biquadratic_mix(ctx: Context) -> Iterator[Finding]:
    blocks = ctx.deck.mesh.blocks
    serendipity, three_d, flag = False, False, False
    n_all = n_conv = 0
    for b in blocks:
        e = _etype(ctx, b.type)
        if e is None:
            return
        # C3D20/C3D20R switch the conversion on themselves (scanning_for_numbers_.f90:190-193)
        flag = any(_key(k) in ("BI-QUADRATIC", "P-REFINEMENT") for k, _ in b.options) or _key(b.type) in _C3D20
        three_d = three_d or e.ndim == 3
        if three_d and (e.nnodes == 20 or (e.nnodes == 8 and flag)):
            serendipity = True
        n = int(b.labels.shape[0])
        n_all += n
        if serendipity:
            n_conv += n
    if serendipity and flag and n_conv != n_all:
        yield (
            f"bi-quadratic conversion of {n_conv} of {n_all} elements: numgeo converts only when all elements "
            "are 20-node (or flagged 8-node) 3D elements and stops otherwise; the flag of the last *Element "
            "block decides whether the conversion is done"
        )


@rule(
    "NG-MESH-107",
    "warning",
    "u4p4-ax-sw is computed as plane strain",
    source="src/database/library_elements_up_stab_swelling_.txt:84-87",
)
def u4p4_ax_sw(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when the library entry is fixed.
    n = sum(int(b.labels.shape[0]) for b in ctx.deck.mesh.blocks if _canon(ctx, b.type) == "U4P4-AX-SW")
    if n:
        yield (
            f"{n} u4p4-ax-sw element(s): numgeo's library entry has axisymmetric = .false., so they are "
            "computed as plane strain, not axisymmetric"
        )


@rule(
    "NG-AMPL-101",
    "error",
    "a tabular amplitude needs at least two points",
    source="src/database/amplitude_.f90:423-427 (amplitude_get_value_at_time)",
)
def tabular_points(ctx: Context) -> Iterator[Finding]:
    for a in ctx.deck.amplitudes:
        if _key(a.type) != "TABULAR":
            continue
        vals = _flat(a.data)
        if len(a.data) == 1 and len(a.data[0]) == 1 and not is_real_token(a.data[0][0]):
            continue  # values in a file
        if len(vals) < 4:
            yield (
                f"amplitude {a.name}: type=tabular needs at least two points (t, value); numgeo evaluates "
                "x(0) for a one-point table",
                a.source or f"amplitude {a.name}",
            )


_LAB_COMPONENTS = ("S11", "S12", "S22", "S33", "S11-S22")


@rule(
    "NG-AMPL-102",
    "error",
    "lab-cyclic amplitudes accept only the components s11, s12, s22, s33, s11-s22",
    source="src/input/read_amplitude_.f90:351; src/database/amplitude_.f90:513-534",
)
def lab_component(ctx: Context) -> Iterator[Finding]:
    for a in ctx.deck.amplitudes:
        if _key(a.type) != "LAB-CYCLIC-STRESS-STRAIN-CONTROL":
            continue
        for r in a.data:
            if len(r) >= 2 and _key(str(r[1])) not in _LAB_COMPONENTS:
                yield (
                    f"amplitude {a.name}: component {r[1]!r} is not one of s11, s12, s22, s33, s11-s22 "
                    "(numgeo accepts any text containing one of them)",
                    a.source or f"amplitude {a.name}",
                )


@rule(
    "NG-AMPL-103",
    "warning",
    "equally spaced amplitudes start at t = dx and misread the first point",
    source="src/input/read_amplitude_.f90:493-496; src/database/amplitude_.f90:376-379",
)
def equally_spaced(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for a in ctx.deck.amplitudes:
        if _key(a.type) == "EQUALLY_SPACED":
            yield (
                f"amplitude {a.name}: type=equally_spaced places value i at t = i*dx (not (i-1)*dx) and "
                "reads y(0) at t = dx; use type=tabular",
                a.source or f"amplitude {a.name}",
            )


_FILE_OK = re.compile(r"^[a-z0-9_.\-]+$")


@rule(
    "NG-AMPL-104",
    "error",
    "amplitude data files must be lower-case names without path",
    source="src/input/read_amplitude_.f90:452-460,535-540",
)
def amplitude_files(ctx: Context) -> Iterator[Finding]:
    for a in ctx.deck.amplitudes:
        t = _key(a.type)
        name: Token | None = None
        if t == "EQUALLY_SPACED" and len(a.data) >= 2 and a.data[1]:
            name = a.data[1][0]
        elif t == "TABULAR" and len(a.data) == 1 and len(a.data[0]) == 1 and not is_real_token(a.data[0][0]):
            name = a.data[0][0]
        if isinstance(name, str) and not _FILE_OK.match(name.strip()):
            yield (
                f"amplitude {a.name}: data file {name!r} must be a lower-case name without path in the job "
                "folder (numgeo lower-cases it and prefixes the working directory)",
                a.source or f"amplitude {a.name}",
            )


# ============================================================================= materials
def _user_props(m: Material) -> tuple[Keyword | None, Keyword | None]:
    mech = m.property("*Mechanical")
    if mech is None or _key(mech.value) not in ("USER", "USER_UNSAT"):
        return None, None
    return mech, m.property("*User properties")


@rule(
    "NG-MAT-101",
    "error",
    "user materials need exactly props= parameters",
    source="src/input/read_material_.f90:509 (read_material)",
)
def user_props_count(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        mech, up = _user_props(m)
        if mech is None or up is None:
            continue
        n = up.option("PROPS")
        given = len(_flat(mech.data)) + len(_flat(up.data))
        if n is not None and is_int_token(n) and int(n) != given:
            yield (
                f"material {m.name}: *User properties, props={n} but {given} values are given (numgeo does "
                "not compare them)",
                _mloc(m),
            )


@rule(
    "NG-MAT-102",
    "error",
    "user materials need statev >= 1 and props >= 1",
    source="src/input/read_material_.f90:342-358,449 (read_material)",
)
def user_statev(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        _, up = _user_props(m)
        if up is None:
            continue
        for key in ("STATEV", "PROPS"):
            v = up.option(key)
            if v is not None and is_int_token(v) and int(v) < 1:
                yield (f"material {m.name}: *User properties, {key.lower()}={v} must be at least 1", _mloc(m))


@rule(
    "NG-MAT-103",
    "error",
    "*User properties takes exactly props= and statev=",
    source="src/input/read_material_.f90:325-376 (read_material)",
)
def user_props_options(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        _, up = _user_props(m)
        if up is None:
            continue
        keys = [k for k, _ in up.options]
        if sorted(keys) != ["PROPS", "STATEV"] or any(v is None for _, v in up.options):
            yield (
                f"material {m.name}: *User properties needs exactly props=<n>, statev=<m> (given: "
                f"{', '.join(k.lower() for k in keys) or 'nothing'}; numgeo reads only statev=, not matvar=)",
                _mloc(m),
            )


@rule(
    "NG-MAT-104",
    "error",
    "user materials take no *Optional mechanical parameter",
    source="src/input/read_material_.f90:559 (read_material)",
)
def user_optional(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        mech, _ = _user_props(m)
        if mech is not None and m.property("*Optional mechanical parameter") is not None:
            yield (
                f"material {m.name}: *Optional mechanical parameter is rejected for *Mechanical="
                f"{_key(mech.value).lower()}",
                _mloc(m),
            )


@rule(
    "NG-MAT-105",
    "error",
    "*Damping needs two values, *Viscous damping one",
    source="src/input/read_material_.f90:1535-1541,1561-1567",
)
def damping_count(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        for kw, n in (("*Damping", 2), ("*Viscous damping", 1)):
            p = m.property(kw)
            if p is None:
                continue
            if len(p.data) != 1 or len(p.data[0]) != n or not all(is_real_token(t) for t in p.data[0]):
                yield (
                    f"material {m.name}: {kw} needs exactly one line with {n} value(s); numgeo silently "
                    "ignores it otherwise",
                    _loc(p, _mloc(m)),
                )


@rule(
    "NG-MAT-106",
    "error",
    "*HCA recording time needs start/end pairs on one data line",
    source="src/input/read_material_.f90:1489-1504 (read_material)",
)
def hca_recording(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*HCA recording time")
        if p is None:
            continue
        if len(p.data) > 1:
            yield (
                f"material {m.name}: *HCA recording time with {len(p.data)} data lines; numgeo stores wrong "
                "values for every line after the first (write all pairs on one line)",
                _loc(p, _mloc(m)),
            )
        for r in p.data:
            if len(r) < 2 or len(r) % 2:
                yield (
                    f"material {m.name}: *HCA recording time needs start/end pairs, {len(r)} values given",
                    _loc(p, _mloc(m)),
                )


@rule(
    "NG-MAT-107",
    "error",
    "*Density must not come before *Truss properties",
    source="src/input/read_material_.f90:1760 (read_material)",
)
def truss_density_order(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        ks = [p.keyword for p in m.properties]
        if "*TRUSSPROPERTIES" in ks and "*DENSITY" in ks and ks.index("*DENSITY") < ks.index("*TRUSSPROPERTIES"):
            yield (
                f"material {m.name}: *Density before *Truss properties: numgeo allocates the density twice "
                "and stops (write *Density after *Truss properties)",
                _mloc(m),
            )


# Sub-keywords that may legitimately appear more than once in a material.
_REPEATABLE = frozenset({"*JACOBIAN", "*MECHANICAL"})  # *Mechanical: NG-MAT-001


@rule(
    "NG-MAT-108",
    "error",
    "a material sub-keyword may appear only once",
    source="src/input/read_material_.f90:1088,1146,1231 (read_material)",
)
def repeated_property(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        seen: set[str] = set()
        for p in m.properties:
            if p.keyword in seen and p.keyword not in _REPEATABLE:
                fails = p.keyword in ("*BULKMODULUS", "*DYNAMICVISCOSITY", "*PHANTOMELASTICITY")
                yield (
                    f"material {m.name}: {display(ctx.catalogue, p.keyword)} is given more than once ("
                    + ("numgeo stops: allocated twice)" if fails else "numgeo uses the last one)"),
                    _loc(p, _mloc(m)),
                )
            seen.add(p.keyword)


_SUBMODELS = {
    "*BISHOPEFFECTIVESTRESS": ("bishop_models", "src/input/read_material_.f90:911"),
    "*MECHANICALVISCOSITY": ("mechanical_viscosity_models", "src/input/read_material_.f90:1198"),
    "*HYDRAULIC": ("hydraulic_models", "src/input/read_material_.f90:676"),
    "*RELATIVEPERMEABILITY": ("relative_permeability_models", "src/input/read_material_.f90:784"),
}


@rule(
    "NG-MAT-109",
    "error",
    "sub-models need their full parameter list",
    source="src/input/read_material_.f90:512,676,784,911,1198 (read_material)",
)
def submodel_params(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        for p in m.properties:
            spec = _SUBMODELS.get(p.keyword)
            if spec is None or p.value is None:
                continue
            table = {_key(x["name"]): x for x in ctx.catalogue.section("materials", spec[0])}
            entry = table.get(_key(p.value))
            if entry is None or not isinstance(entry.get("nprops"), int):
                continue
            n, given = int(entry["nprops"]), len(_flat(p.data))
            if given != n:
                yield (
                    f"material {m.name}: {display(ctx.catalogue, p.keyword)}={p.value.lower()} needs {n} "
                    f"parameter(s), {given} given ({spec[1]})",
                    _loc(p, _mloc(m)),
                )


@rule(
    "NG-MAT-110",
    "warning",
    "multi-phase materials should give *Dynamic viscosity explicitly",
    source="src/database/database.f90:2424-2428 (check_mat_definition)",
)
def dynamic_viscosity(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        if (m.phases or 1) > 1 and m.property("*Dynamic viscosity") is None:
            yield (
                f"material {m.name} ({m.phases} phases) has no *Dynamic viscosity; numgeo uses 1.0e-6 "
                "(water) and 1.6e-9 (air) kPa s, the air value is about 11 times too low",
                _mloc(m),
            )


_PERMEABILITY = {"ISOTROPIC", "ANISOTROPIC", "KOZENY-CARMAN", "CARRIER", "SOMOGYI", "TABULAR"}


@rule(
    "NG-MAT-111",
    "error",
    "*Permeability accepts only the six documented models",
    source="src/input/read_material_.f90:943-1072 (read_material)",
)
def permeability_model(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        for p in m.properties:
            if p.keyword == "*PERMEABILITY" and p.value is not None and _key(p.value) not in _PERMEABILITY:
                yield (
                    f"material {m.name}: *Permeability={p.value} is not a permeability model; numgeo "
                    "silently uses anisotropic",
                    _loc(p, _mloc(m)),
                )


_PERM_COUNT = {"ISOTROPIC": 1, "ANISOTROPIC": 3, "KOZENY-CARMAN": 2, "CARRIER": 2, "SOMOGYI": 2}


@rule(
    "NG-MAT-112",
    "error",
    "*Permeability data must match the model",
    source="src/input/read_material_.f90:943-1072 (read_material)",
)
def permeability_data(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        for p in m.properties:
            if p.keyword != "*PERMEABILITY":
                continue
            model = _key(p.value) or "ANISOTROPIC"
            if model == "TABULAR":
                if len(p.data) < 2 or any(len(r) != 2 for r in p.data):
                    yield (
                        f"material {m.name}: *Permeability=tabular needs at least two lines 'e, k'",
                        _loc(p, _mloc(m)),
                    )
                continue
            n = _PERM_COUNT.get(model)
            if n is None:
                continue
            if model == "ISOTROPIC" and (len(p.data) != 1 or len(p.data[0]) != 1):
                yield (
                    f"material {m.name}: *Permeability=isotropic needs exactly one value on one line (numgeo "
                    "reads it list-directed and takes the first number it finds)",
                    _loc(p, _mloc(m)),
                )
            elif len(_flat(p.data)) != n:
                yield (
                    f"material {m.name}: *Permeability={model.lower()} needs {n} value(s), {len(_flat(p.data))} given",
                    _loc(p, _mloc(m)),
                )


@rule(
    "NG-MAT-113",
    "error",
    "Kozeny-Carman needs c > 0 and d > 0",
    source="src/input/read_material_.f90:952-971; src/materials/permeability_.f90:80-92",
)
def kozeny_carman(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*Permeability")
        if p is None or _key(p.value) != "KOZENY-CARMAN":
            continue
        vals = [_num(t) for t in _flat(p.data)]
        for i, label in enumerate(("c", "d (effective grain size)")):
            v = vals[i] if i < len(vals) else None
            if v is not None and v <= 0:
                yield (
                    f"material {m.name}: Kozeny-Carman {label} = {v:g} must be positive",
                    _loc(p, _mloc(m)),
                )


def _opt_names(ctx: Context, model: str) -> list[str] | None:
    try:
        spec = ctx.catalogue.material_model(model)
    except KeyError:
        return None
    return [_key(str(o.get("name"))) for o in spec.optional_parameters if o.get("name")]


@rule(
    "NG-MAT-114",
    "error",
    "*Adaptive strain ampl only after an HCA sand model",
    source="src/input/read_material_.f90:1576-1577 (read_material)",
)
def adaptive_strain(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        ks = [p.keyword for p in m.properties]
        if "*ADAPTIVESTRAINAMPL" not in ks:
            continue
        names = _opt_names(ctx, _mech(m)) or []
        before = "*MECHANICAL" in ks and ks.index("*MECHANICAL") < ks.index("*ADAPTIVESTRAINAMPL")
        if "GA_DEFINITION" not in names or not before:
            yield (
                f"material {m.name}: *Adaptive strain ampl needs a preceding *Mechanical of an HCA sand "
                "model (one "
                "with the optional parameter ga_definition); numgeo writes the flag without checking",
                _mloc(m),
            )


@rule(
    "NG-MAT-115",
    "error",
    "optional parameters must exist for the model",
    source="src/input/read_material_.f90:1937-1954 (read_optional_parameter)",
)
def optional_parameters(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*Optional mechanical parameter")
        model = _mech(m)
        if p is None or model in ("USER", "USER_UNSAT", ""):
            continue
        names = _opt_names(ctx, model)
        if names is None:
            continue  # model not in this catalogue
        if not names:
            yield (
                f"material {m.name}: {model.lower()} has no optional mechanical parameters",
                _loc(p, _mloc(m)),
            )
            continue
        for r in p.data:
            if r and _key(str(r[0])) not in names:
                yield (
                    f"material {m.name}: {r[0]!r} is not an optional parameter of {model.lower()} (known: "
                    f"{', '.join(n.lower() for n in names)})",
                    _loc(p, _mloc(m)),
                )


_PPP_REQUIRED = frozenset({"U3PMEAN3-HYPER-SOLID", "U3PMEAN3-HYPER-SOLID-AX"})


@rule(
    "NG-MAT-116",
    "error",
    "*PPP-stabilisation: required for u3pmean3-hyper elements, valid options and values",
    source="src/input/read_material_.f90:1662-1700; src/elements/element_Us_pmean_hyper_stab_.f90:229",
)
def ppp_stabilisation(ctx: Context) -> Iterator[Finding]:
    types = _material_types(ctx)
    for m in ctx.deck.materials:
        p = m.property("*PPP-stabilisation")
        used = {_canon(ctx, t) for t in types.get(_key(m.name), set())}
        if p is None:
            if used & _PPP_REQUIRED:
                yield (
                    f"material {m.name} is used by "
                    f"{', '.join(sorted(t.lower() for t in used & _PPP_REQUIRED))} "
                    "elements, which need *PPP-stabilisation",
                    _mloc(m),
                )
            continue
        method = "CONSTANT"
        if p.options:
            vals = [_key(v) for _, v in p.options if v is not None]
            if len(p.options) != 1 or not vals or vals[0] not in ("CONSTANT", "ELEMENTWISE"):
                yield (
                    f"material {m.name}: *PPP-stabilisation takes one option with the value constant or elementwise",
                    _loc(p, _mloc(m)),
                )
                continue
            method = vals[0]
        n = len(p.data[0]) if len(p.data) == 1 else -1
        if n != 1 and not (n == 3 and method == "ELEMENTWISE"):
            yield (
                f"material {m.name}: *PPP-stabilisation needs one line with 1 value (3 values only with "
                "method=elementwise)",
                _loc(p, _mloc(m)),
            )


@rule(
    "NG-MAT-117",
    "error",
    "neo_hooke_up only with u3pmean3-hyper-solid elements and vice versa",
    source="src/materials/material_library.f90:2017-2020; src/elements/element_Us_pmean_hyper_stab_.f90:401",
)
def neo_hooke_up(ctx: Context) -> Iterator[Finding]:
    types = _material_types(ctx)
    for m in ctx.deck.materials:
        used = {_canon(ctx, t) for t in types.get(_key(m.name), set())}
        is_up = _mech(m) == "NEO_HOOKE_UP"
        if is_up and used - _PPP_REQUIRED:
            yield (
                f"material {m.name}: neo_hooke_up is used by "
                f"{', '.join(sorted(t.lower() for t in used - _PPP_REQUIRED))}"
                "; it works only with u3pmean3-hyper-solid(-ax) elements",
                _mloc(m),
            )
        if not is_up and used & _PPP_REQUIRED and _mech(m):
            yield (
                f"material {m.name} ({_mech(m).lower()}) is used by u3pmean3-hyper-solid elements, which "
                "compute neo_hooke_up whatever the material says",
                _mloc(m),
            )


@rule(
    "NG-MAT-118",
    "error",
    "min_pressure has no effect for hardening-soil-mn",
    source="src/materials/material_library.f90:354,366,1640,1647",
)
def hs_min_pressure(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*Optional mechanical parameter")
        if p is None or _mech(m) not in ("HARDENING-SOIL-MN", "HARDENING-SOIL-MN-BRICKS"):
            continue
        if any(r and _key(str(r[0])) == "MIN_PRESSURE" for r in p.data):
            yield (
                f"material {m.name}: the optional parameter min_pressure of {_mech(m).lower()} is never "
                "passed to the model (no effect)",
                _loc(p, _mloc(m)),
            )


@rule(
    "NG-MAT-119",
    "warning",
    "projection_dev > 1 is read as cut-off angle from the integrator slot",
    source="src/materials/models/material_hypoplasticity_isa_sf_.f90:1090-1095; "
    "src/materials/models/material_BC_hypoplasticity_igs_sf_.f90:1095-1100",
)
def projection_dev(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for m in ctx.deck.materials:
        p = m.property("*Optional mechanical parameter")
        if p is None or _mech(m) not in ("HYPO-ISA-SF", "BC-HYPO-IGS-SF"):
            continue
        for r in p.data:
            v = _num(r[1]) if len(r) > 1 else None
            if r and _key(str(r[0])) == "PROJECTION_DEV" and v is not None and v > 1:
                yield (
                    f"material {m.name}: projection_dev = {v:g} > 1: numgeo takes the cut-off angle from the "
                    "integrator value instead",
                    _loc(p, _mloc(m)),
                )


@rule(
    "NG-MAT-120",
    "error",
    "a non-public constitutive model is not offered",
    source="src/input/read_material_.f90:258-266 (model looked up by name; non-public model recognised by hash)",
)
def withheld_model(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*Mechanical")
        if p is not None and p.value and _hash(p.value) == _H_WITHHELD:
            yield (
                f"material {m.name}: *Mechanical={p.value} is not available through pynumgeo "
                "(its intergranular-strain branches are not reliable)",
                _mloc(m),
            )


@rule(
    "NG-MAT-121",
    "error",
    "barodesy-clay needs 0 < phi_c < 90 degrees",
    source="src/materials/models/material_bardodesy_clay_.f90:2182,2203",
)
def barodesy_clay(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*Mechanical")
        if p is None or _mech(m) != "BARODESY-CLAY":
            continue
        vals = _flat(p.data)
        v = _num(vals[0]) if vals else None
        if v is not None and not 0 < v < 90:
            yield (
                f"material {m.name}: barodesy-clay phi_c = {v:g} must lie between 0 and 90 degrees (numgeo "
                "compares the upper bound after converting to radians)",
                _mloc(m),
            )


@rule(
    "NG-MAT-122",
    "warning",
    "hca-hypo-isa/igs need *Maximum eps ampl",
    source="src/database/database.f90:2457,2587,2637 (check_mat_definition)",
)
def hca_epsampl(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        if _mech(m) in ("HCA-HYPO-ISA", "HCA-HYPO-IGS") and m.property("*Maximum eps ampl") is None:
            yield (
                f"material {m.name}: {_mech(m).lower()} without *Maximum eps ampl: numgeo keeps epsampl_max "
                "= 0 (no default for these models)",
                _mloc(m),
            )


_THERMAL = "solid with temperature"


@rule(
    "NG-MAT-123",
    "error",
    "thermal_elasticity needs T_ref > 0",
    source="src/materials/models/material_thermal_elasticity_.f90:65-68",
)
def thermal_tref(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*Mechanical")
        if p is None or _mech(m) != "THERMAL_ELASTICITY":
            continue
        vals = _flat(p.data)
        v = _num(vals[3]) if len(vals) >= 4 else None
        if v is not None and v <= 0:
            yield f"material {m.name}: thermal_elasticity T_ref = {v:g} must be positive", _mloc(m)


@rule(
    "NG-MAT-124",
    "warning",
    "thermal_elasticity acts as linear elasticity on elements without temperature",
    source="src/database/database.f90:1191-1194 (check_thermal_elements)",
)
def thermal_elements(ctx: Context) -> Iterator[Finding]:
    types = _material_types(ctx)
    for m in ctx.deck.materials:
        if _mech(m) != "THERMAL_ELASTICITY":
            continue
        other = sorted(
            t.lower()
            for t in types.get(_key(m.name), set())
            if (e := _etype(ctx, t)) is not None and not e.family.startswith(_THERMAL)
        )
        if other:
            yield (
                f"material {m.name}: thermal_elasticity on {', '.join(other)} elements acts as linear elasticity",
                _mloc(m),
            )


# Models whose *Min pressure numgeo replaces by -1e-8 when it is above -1e-8 (check_mat_definition).
_MINP_RESET = frozenset(
    {
        "HYPOPLASTICITY",
        "HCA_HYPOPLASTICITY",
        "SANISAND",
        "HCA_SANISAND",
        "HCA-SANISAND-2",
        "HCA_LINEAR_ELASTICITY",
        "AVISA",
    }
)


def _min_pressure(m: Material) -> tuple[Keyword, float] | None:
    p = m.property("*Min pressure")
    if p is None or _mech(m) not in _MINP_RESET:
        return None
    v = _num(p.data[0][0]) if p.data and p.data[0] else None
    return (p, v) if v is not None else None


@rule(
    "NG-MAT-125",
    "error",
    "*Min pressure must be negative",
    source="src/database/database.f90:2527-2535,2609-2617,2650-2658 (check_mat_definition)",
)
def min_pressure_sign(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        mp = _min_pressure(m)
        if mp is not None and mp[1] >= 0:
            yield (
                f"material {m.name}: *Min pressure = {mp[1]:g} must be negative; numgeo replaces it by -1e-8",
                _loc(mp[0], _mloc(m)),
            )


@rule(
    "NG-MAT-126",
    "warning",
    "*Min pressure between -1e-8 and 0 is replaced by -1e-8",
    source="src/database/database.f90:2527-2535,2609-2617,2650-2658 (check_mat_definition)",
)
def min_pressure_small(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        mp = _min_pressure(m)
        if mp is not None and -1e-8 < mp[1] < 0:
            yield (
                f"material {m.name}: *Min pressure = {mp[1]:g} is replaced by -1e-8 by numgeo",
                _loc(mp[0], _mloc(m)),
            )


_FIXED_KS = frozenset({"element_UP_saturated", "element_UP_sat_stab", "element_UPC_sat_stab"})


@rule(
    "NG-MAT-127",
    "warning",
    "saturated u-p elements ignore *Solid bulk modulus",
    source="src/elements/element_UP_saturated_.f90:312; src/elements/element_UP_sat_stab_.f90:230; "
    "src/elements/element_UPC_sat_stab_.f90:279",
)
def solid_bulk_ignored(ctx: Context) -> Iterator[Finding]:
    types = _material_types(ctx)
    for m in ctx.deck.materials:
        if m.property("*Solid bulk modulus") is None:
            continue
        hit = sorted(
            t.lower()
            for t in types.get(_key(m.name), set())
            if (e := _etype(ctx, t)) is not None and e.raw.get("formulation_routine") in _FIXED_KS
        )
        if hit:
            yield (
                f"material {m.name}: *Solid bulk modulus is ignored by {', '.join(hit)} elements (they use a "
                "fixed grain bulk modulus of 15e6)",
                _mloc(m),
            )


# ============================================================================= steps
@rule(
    "NG-STEP-101",
    "error",
    "*Step options must be known",
    source="src/input/read_step_.f90:293-352 (read_step)",
)
def step_options(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        for k, v in st.extra_options:
            tok = k if v is None else f"{k}={v}"
            yield (
                f"step {st.name}: unknown *Step option {tok.lower()!r}; numgeo ignores it silently (known: "
                "inc, nlgeom, nocutback, maxiter, miniter, scalefactor)",
                _sloc(st),
            )


def _value_count(kw: Keyword) -> int:
    """Number of comma-separated values after ``=`` (``*HHT=a, b, c`` -> 3); 0 without ``=``."""
    if kw.value is None:
        return 0
    return 1 + len(kw.options)


def _values_numeric(kw: Keyword) -> bool:
    return (
        kw.value is not None and is_real_token(kw.value) and all(v is None and is_real_token(k) for k, v in kw.options)
    )


@rule(
    "NG-STEP-102",
    "error",
    "*Hilber-Hughes-Taylor needs alpha (or alpha, beta, gamma)",
    source="src/input/read_step_.f90:590-600; src/tools/strings_.f90:435",
)
def hht_values(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        for c in st.procedure.children:
            if c.keyword in ("*HILBER-HUGHES-TAYLOR", "*HHT"):
                n = _value_count(c)
                if n not in (1, 3) or not _values_numeric(c):
                    yield (
                        f"step {st.name}: {display(ctx.catalogue, c.keyword)} needs =alpha or =alpha, beta, "
                        "gamma (the bare keyword crashes numgeo)",
                        _sloc(st, c),
                    )


@rule(
    "NG-STEP-103",
    "error",
    "*Mass scaling needs one factor",
    source="src/input/read_step_.f90:548-561 (read_step)",
)
def mass_scaling(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        for c in st.procedure.children:
            if c.keyword == "*MASSSCALING" and (_value_count(c) != 1 or not _values_numeric(c)):
                yield (
                    f"step {st.name}: *Mass scaling needs =<factor> (the bare keyword crashes numgeo; omit "
                    "the line for no mass scaling)",
                    _sloc(st, c),
                )


@rule(
    "NG-STEP-104",
    "error",
    "*Termination takes no options",
    source="src/input/read_step_.f90:2352 (read_step)",
)
def termination_options(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword == "*TERMINATION" and (kw.options or kw.value is not None):
            yield (
                f"step {st.name}: *Termination with options is not recognised by numgeo (the case literal is "
                "'TERMINATION,' without '*'); write *Termination alone",
                _sloc(st, kw),
            )


@rule(
    "NG-STEP-105",
    "warning",
    "*Extrapolation, coupled runs quadratic extrapolation",
    source="src/input/read_step_.f90:655-660; src/soe/soe_extrapolate_solution_.f90:276",
)
def extrapolation_coupled(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for _, st, _, kw in _step_items(ctx.deck):
        t = _opt_text(kw)
        if kw.keyword == "*EXTRAPOLATION" and "COUPLED" in t and "QUADRATIC" not in t:
            yield (
                f"step {st.name}: *Extrapolation, coupled: numgeo currently runs quadratic extrapolation",
                _sloc(st, kw),
            )


@rule(
    "NG-STEP-106",
    "info",
    "*Controls, global has no effect",
    source="src/input/read_step_.f90:2410-2448; src/database/controls_ty_.f90:58-64",
)
def controls_global(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword == "*CONTROLS" and kw.options and _key(kw.options[0][0]) == "GLOBAL":
            yield f"step {st.name}: *Controls, global is read but has no effect in numgeo", _sloc(st, kw)


_CONTROL_FIELDS = ("GLOBAL", "U", "PW", "TT", "PA", "MAX-DPW", "W", "R")


def _control_mode(kw: Keyword) -> str | None:
    t = _key(kw.options[1][0]) if len(kw.options) > 1 else ""
    for mode in ("MODIFY", "DEACTIVATE", "ACTIVATE"):
        if mode in t:
            return mode
    return None


@rule(
    "NG-STEP-107",
    "error",
    "*Controls needs a known field and mode",
    source="src/input/read_step_.f90:2397-2790 (read_step)",
)
def controls_mode(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*CONTROLS":
            continue
        if len(kw.options) != 2:
            yield f"step {st.name}: *Controls needs exactly two options: <field>, <mode>", _sloc(st, kw)
            continue
        field = _key(kw.options[0][0])
        if field not in _CONTROL_FIELDS:
            yield (
                f"step {st.name}: *Controls field {kw.options[0][0]!r} is not one of "
                f"{', '.join(f.lower() for f in _CONTROL_FIELDS)}",
                _sloc(st, kw),
            )
        elif _control_mode(kw) is None:
            yield (
                f"step {st.name}: *Controls, {field.lower()}: mode {kw.options[1][0]!r} is not modify, "
                "deactivate or "
                "activate" + (" (numgeo silently ignores it for global)" if field == "GLOBAL" else ""),
                _sloc(st, kw),
            )


@rule(
    "NG-STEP-108",
    "error",
    "*Controls, max-dpw, deactivate activates the control",
    source="src/input/read_step_.f90:2663 (read_step)",
)
def controls_maxdpw(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if (
            kw.keyword == "*CONTROLS"
            and len(kw.options) == 2
            and _key(kw.options[0][0]) == "MAX-DPW"
            and "DEACTIVATE" in _key(kw.options[1][0])
        ):
            yield (
                f"step {st.name}: *Controls, max-dpw, deactivate switches the control ON in numgeo; omit the "
                "block to keep it off",
                _sloc(st, kw),
            )


_CONTROL_DATA = {"MODIFY": (5, 6), "GLOBAL-MODIFY": (3,), "MAX-DPW-ACTIVATE": (2,)}


@rule(
    "NG-STEP-131",
    "error",
    "*Controls data line must match field and mode",
    source="src/input/read_step_.f90:2410-2790 (read_step)",
)
def controls_data(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*CONTROLS" or len(kw.options) != 2:
            continue
        field, mode = _key(kw.options[0][0]), _control_mode(kw)
        if field not in _CONTROL_FIELDS or mode is None:
            continue
        if field == "MAX-DPW" and mode != "ACTIVATE":
            continue  # NG-STEP-108
        need = (
            _CONTROL_DATA["GLOBAL-MODIFY"]
            if field == "GLOBAL" and mode == "MODIFY"
            else _CONTROL_DATA["MAX-DPW-ACTIVATE"]
            if field == "MAX-DPW"
            else _CONTROL_DATA["MODIFY"]
            if mode == "MODIFY"
            else ()
        )
        if not need:
            if kw.data:
                yield (
                    f"step {st.name}: *Controls, {field.lower()}, {mode.lower()} takes no data line",
                    _sloc(st, kw),
                )
        elif len(kw.data) != 1 or len(kw.data[0]) not in need:
            yield (
                f"step {st.name}: *Controls, {field.lower()}, {mode.lower()} needs one data line with "
                f"{' or '.join(map(str, need))} values",
                _sloc(st, kw),
            )


@rule(
    "NG-STEP-109",
    "error",
    "*Pfem write: at most one per job and not with a complete *Restart write",
    source="src/input/read_step_.f90:2960,2976-2990; src/output/restart_.f90:180",
)
def pfem_write(ctx: Context) -> Iterator[Finding]:
    pfem = [(st, kw) for _, st, _, kw in _step_items(ctx.deck) if kw.keyword == "*PFEMWRITE"]
    if not pfem:
        return
    if len(pfem) > 1:
        yield (
            f"*Pfem write appears in {len(pfem)} steps; numgeo's PFEM write flags are global (the last one "
            "decides for every step)",
            _sloc(pfem[1][0], pfem[1][1]),
        )
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword == "*RESTARTWRITE" and not kw.options:
            yield (
                f"step {st.name}: a complete *Restart write in a job with *Pfem write: numgeo writes both "
                "with the same global flags",
                _sloc(st, kw),
            )


_EXPLICIT = ("*EXPLICITDYNAMIC", "*EXPLICITDYNAMICS")


@rule(
    "NG-STEP-110",
    "error",
    "*Time integration only in explicit steps and with instance=",
    source="src/input/read_step_.f90:3049-3089 (read_step)",
)
def time_integration(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*TIMEINTEGRATION":
            continue
        if st.procedure.keyword not in _EXPLICIT:
            yield (
                f"step {st.name}: *Time integration is only meaningful in *Explicit dynamic steps",
                _sloc(st, kw),
            )
        if "INSTANCE=" not in _opt_text(kw):
            yield (
                f"step {st.name}: *Time integration without instance= is silently ignored by numgeo",
                _sloc(st, kw),
            )


@rule(
    "NG-STEP-111",
    "warning",
    "*Read stress without *Read state",
    source="src/database/step_ty_.f90:155; src/input/read_step_.f90:3096",
)
def read_stress_alone(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for st in ctx.deck.steps:
        ks = [k.keyword for k in st.items]
        if "*READSTRESS" in ks and "*READSTATE" not in ks:
            yield (
                f"step {st.name}: *Read stress without *Read state leaves the state-file frequency "
                "uninitialised (may misbehave after the first increment)",
                _sloc(st),
            )


def _restart_opts(kw: Keyword) -> list[tuple[str, str | None]]:
    return [(_key(k), None if v is None else _key(v)) for k, v in kw.options]


@rule(
    "NG-STEP-112",
    "error",
    "*Restart read / *Pfem read take step= (and igp= for *Pfem read) only",
    source="src/input/scanning_for_numbers_.f90:308-328 (scanning_for_numbers)",
)
def restart_read(ctx: Context) -> Iterator[Finding]:
    for i, kw in enumerate(ctx.deck.keywords):
        if kw.keyword not in ("*RESTARTREAD", "*PFEMREAD"):
            continue
        o = _restart_opts(kw)
        ok = bool(o) and o[0][0] == "STEP" and o[0][1] is not None and is_int_token(o[0][1])
        if ok and len(o) == 2:
            if kw.keyword == "*PFEMREAD":
                ok = o[1][0] == "IGP" and o[1][1] in ("MIXED", "TOTAL")
            else:
                ok = o[1] == ("SUBMODEL", None)  # NG-STEP-113
        ok = ok and len(o) <= 2
        if not ok:
            form = "step=<n>[, igp=mixed|total]" if kw.keyword == "*PFEMREAD" else "step=<n>"
            yield (
                f"{display(ctx.catalogue, kw.keyword)} takes {form} in this order (numgeo reads the options "
                "by position; otherwise the restart step stays 0)",
                _loc(kw, f"keywords[{i}]"),
            )


@rule(
    "NG-STEP-113",
    "warning",
    "the submodel option of *Restart read is ignored",
    source="src/input/scanning_for_numbers_.f90:302,311-327",
)
def restart_submodel(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for i, kw in enumerate(ctx.deck.keywords):
        if kw.keyword == "*RESTARTREAD" and any(k == "SUBMODEL" for k, _ in _restart_opts(kw)):
            yield (
                "*Restart read, ..., submodel: numgeo ignores the submodel option (restart%submodel stays false)",
                _loc(kw, f"keywords[{i}]"),
            )


@rule(
    "NG-STEP-114",
    "error",
    "*Restart read lines must fit into 80 characters",
    source="src/input/scanning_for_numbers_.f90:73,101 (scanning_for_numbers)",
)
def restart_line(ctx: Context) -> Iterator[Finding]:
    for i, kw in enumerate(ctx.deck.keywords):
        if kw.keyword in ("*RESTARTREAD", "*PFEMREAD") and len(line_text(kw)) > 80:
            yield (
                f"{display(ctx.catalogue, kw.keyword)}: the line has {len(line_text(kw))} characters after "
                "preprocessing; the pre-scan reads only 80",
                _loc(kw, f"keywords[{i}]"),
            )


@rule(
    "NG-STEP-115",
    "error",
    "*Submodel needs a variable option (statev, stress or disp)",
    source="src/input/read_step_.f90:3435-3440 (read_submodel_options)",
)
def submodel_variables(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword == "*SUBMODEL" and not any(w in _opt_text(kw) for w in ("STATEV", "STRESS", "DISP")):
            yield f"step {st.name}: *Submodel needs statev, stress or disp", _sloc(st, kw)


@rule(
    "NG-STEP-116",
    "error",
    "*Submodel takes no numgeo= or inp=",
    source="src/input/read_step_.f90:3355-3387 (read_submodel_options)",
)
def submodel_names(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*SUBMODEL":
            continue
        for k, _v in kw.options:
            if k in ("NUMGEO", "INP"):
                yield f"step {st.name}: *Submodel, {k.lower()}= has no effect in numgeo", _sloc(st, kw)


_NONLOCAL_WORDS = ("STATEV", "FREQUENCY", "LOCAL-LEN", "TIME", "ELSET")


@rule(
    "NG-STEP-117",
    "error",
    "*Non-local element set names must not contain option words",
    source="src/input/read_step_.f90:3475-3481 (read_nonlocal_options)",
)
def nonlocal_names(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*NON-LOCAL":
            continue
        name = kw.option("ELSET")
        words = [w for w in _NONLOCAL_WORDS if name and w in _key(name)]
        if words:
            yield (
                f"step {st.name}: *Non-local element set {name!r} contains "
                f"{', '.join(w.lower() for w in words)}, which numgeo reads as an option",
                _sloc(st, kw),
            )


def _solver_key(kw: Keyword) -> str:
    """numgeo's solver key: first option up to '=' (src/input/read_step_.f90:678-682)."""
    return _key(kw.options[0][0]) if kw.options else ""


def _external(kw: Keyword) -> bool:
    return kw.keyword == "*SOLVER" and "EXTERNAL" in _solver_key(kw)


@rule(
    "NG-STEP-118",
    "error",
    "external solver exe= and arg= must not contain 'external'",
    source="src/input/read_step_.f90:763 (read_step)",
)
def external_word(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for _, st, _, kw in _step_items(ctx.deck):
        if _external(kw):
            for k, v in kw.options[1:]:
                if "EXTERNAL" in _key(k) or (v is not None and "EXTERNAL" in _key(v)):
                    yield (
                        f"step {st.name}: *Solver, external: {k.lower()}= contains 'external'; numgeo reads "
                        "the options after the last occurrence of that word",
                        _sloc(st, kw),
                    )


_EXTERNAL_OPTIONS = ("EXE", "ARG", "MPI", "OMP", "ONEAPI")


@rule(
    "NG-STEP-119",
    "warning",
    "unknown external-solver options are ignored",
    source="src/input/read_step_.f90:773-825 (read_step)",
)
def external_options(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if _external(kw):
            for k, v in kw.options[1:]:
                if not any(w in _key(k) for w in _EXTERNAL_OPTIONS):
                    tok = k if v is None else f"{k}={v}"
                    yield (
                        f"step {st.name}: *Solver, external: unknown option {tok.lower()!r} is ignored "
                        "(known: exe=, arg=, mpi=, omp=, oneapi)",
                        _sloc(st, kw),
                    )


@rule(
    "NG-STEP-120",
    "error",
    "external solver mpi= must be at least 2",
    source="src/input/read_step_.f90:795-805 (read_step)",
)
def external_mpi(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if _external(kw):
            v = kw.option("MPI")
            n = _num(v)
            if v is not None and (n is None or n < 2):
                yield (
                    f"step {st.name}: *Solver, external, mpi={v}: numgeo rejects fewer than 2 processes "
                    "(omit mpi= for one process)",
                    _sloc(st, kw),
                )


def _has_upper(text: str) -> bool:
    return any("A" <= c <= "Z" for c in text.replace("$", ""))


@rule(
    "NG-STEP-121",
    "error",
    "solver options and commands passed to the shell must be lower case",
    source="src/input/read_step_.f90:784,793,847; src/tools/execute_command_.f90:46-58",
)
def lower_case_commands(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword == "*SOLVER":
            for k, v in kw.options:
                if v is not None and k in ("EXE", "ARG", "LIS") and _has_upper(v):
                    yield (
                        f"step {st.name}: *Solver {k.lower()}={v}: numgeo lower-cases the value, upper-case "
                        "letters cannot be passed",
                        _sloc(st, kw),
                    )
        elif kw.keyword == "*EXECUTECOMMAND":
            for r in kw.data:
                text = ", ".join(str(t) for t in r)
                if _has_upper(text):
                    yield (
                        f"step {st.name}: *Execute command {text!r}: numgeo lower-cases commands, upper-case "
                        "letters cannot be passed",
                        _sloc(st, kw),
                    )


_SOLVERS = (
    "PARDISO",
    "MUMPS",
    "CUDSS",
    "SIMPLE",
    "NONE",
    "EXTERNAL",
    "LIS",
    "BICGSTAB",
    "BICGSTAB(L)",
    "GMRES",
    "AMGCL",
    "FGMRES",
)


@rule(
    "NG-STEP-122",
    "error",
    "solver names must be exact",
    source="src/input/read_step_.f90:678-1305 (read_step)",
)
def solver_names(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*SOLVER":
            continue
        k = _solver_key(kw)
        if k not in _SOLVERS and not re.fullmatch(r"BICGSTAB\([2-8]\)", k):
            yield (
                f"step {st.name}: *Solver, {k.lower() or '(nothing)'} is not a solver name ("
                f"{', '.join(s.lower() for s in _SOLVERS)}); numgeo matches names by substring and keeps "
                "Pardiso for unknown ones",
                _sloc(st, kw),
            )


_DIRECT = {
    "PARDISO": "PARDISO",
    "MUMPS": "MUMPS",
    "CUDSS": "CUDSS",
    "LIS": "LIS",
    "AMGCL": "AMGCL",
    "FGMRES": "FGMRES",
}


@rule(
    "NG-STEP-123",
    "error",
    "solvers must be compiled into the target build",
    source="src/database/solver_ty_.f90:98; src/solver/solver.f90:771-826,897-921",
)
def solver_profile(ctx: Context) -> Iterator[Finding]:
    avail = ctx.profile.solvers
    if avail is None:
        return
    have = {_key(s) for s in avail}
    for st in ctx.deck.steps:
        if st.procedure.keyword in _EXPLICIT:
            continue
        sv = [k for k in st.items if k.keyword == "*SOLVER"]
        if not sv:
            if "PARDISO" not in have:
                yield (
                    f"step {st.name} has no *Solver: numgeo's default is Pardiso, which the build profile "
                    f"{ctx.profile.name!r} does not have; write *Solver explicitly",
                    _sloc(st),
                )
            continue
        need = _DIRECT.get(_solver_key(sv[-1]))
        if need is not None and need not in have:
            yield (
                f"step {st.name}: *Solver, {need.lower()} is not available in build profile {ctx.profile.name!r}",
                _sloc(st, sv[-1]),
            )


_ACCEL = {"BACK-LOOKING": 2, "LINEAR": 2, "RELAXATION": 1, "ANDERSON": 2}


@rule(
    "NG-STEP-124",
    "error",
    "*Accelerator needs one of the four methods and its data line",
    source="src/input/read_step_.f90:2794-2910 (read_step)",
)
def accelerator(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword not in ("*ACCELERATOR", "*LINESEARCH"):
            continue
        t = _opt_text(kw)
        method = next((m for m in _ACCEL if m in t), None)  # numgeo's test order
        if method is None:
            yield (
                f"step {st.name}: {display(ctx.catalogue, kw.keyword)} needs a method: back-looking, linear, "
                "relaxation or anderson",
                _sloc(st, kw),
            )
            continue
        if "DEFAULT" in t:
            if kw.data:
                yield (
                    f"step {st.name}: {display(ctx.catalogue, kw.keyword)}, default takes no data line",
                    _sloc(st, kw),
                )
            continue
        n = _ACCEL[method]
        if len(kw.data) != 1 or len(kw.data[0]) != n or not all(is_real_token(x) for x in kw.data[0]):
            yield (
                f"step {st.name}: {display(ctx.catalogue, kw.keyword)} ({method.lower()}) needs one data "
                f"line with {n} value(s) or the option default",
                _sloc(st, kw),
            )


_TERMINATION_QUANTITIES = ("E11", "E22", "E33", "E12", "E13", "E23", "S11", "S22", "S33", "S12", "S13", "S23")


@rule(
    "NG-STEP-125",
    "error",
    "*Termination quantity must be one of e11..e23, s11..s23",
    source="src/input/read_step_.f90:2379; src/fem/fem_global_early_termination_.f90:303-367",
)
def termination_quantity(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*TERMINATION":
            continue
        for r in kw.data:
            if len(r) >= 2 and _key(str(r[1])) not in _TERMINATION_QUANTITIES:
                yield (
                    f"step {st.name}: *Termination quantity {r[1]!r} is not one of "
                    f"{', '.join(q.lower() for q in _TERMINATION_QUANTITIES)}",
                    _sloc(st, kw),
                )


@rule(
    "NG-STEP-126",
    "error",
    "reduction steps need inc=",
    source="src/input/read_step_.f90:415-418 (read_step)",
)
def reduction_inc(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        if st.procedure.keyword == "*REDUCTION" and st.inc is None:
            yield (
                f"step {st.name}: *Reduction ties its time scale to inc= (t_end = inc); give inc= explicitly",
                _sloc(st),
            )


@rule(
    "NG-STEP-127",
    "error",
    "one *Solver, one *Extrapolation and one *Controls block per field in a step",
    source="src/input/read_step_.f90:645,673,2397 (read_step)",
)
def repeated_step_keywords(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        seen: dict[str, int] = {}
        for kw in st.items:
            if kw.keyword in ("*SOLVER", "*EXTRAPOLATION"):
                k = kw.keyword
            elif kw.keyword == "*CONTROLS" and kw.options:
                k = "*CONTROLS," + _key(kw.options[0][0])
            else:
                continue
            seen[k] = seen.get(k, 0) + 1
            if seen[k] == 2:
                what = display(ctx.catalogue, kw.keyword) + (f", {k.split(',')[1].lower()}" if "," in k else "")
                yield (
                    f"step {st.name}: {what} is given more than once (numgeo uses the last one)",
                    _sloc(st, kw),
                )


@rule(
    "NG-STEP-128",
    "warning",
    "a step should have a *Boundary",
    source="src/input/read_step_.f90:3192,3202; src/soe/soe_apply_boundary_conditions_.f90:92",
)
def step_without_bc(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    model_bc = any(k.keyword == "*BOUNDARY" for k in ctx.deck.keywords)
    for i, st in enumerate(ctx.deck.steps):
        if any(k.keyword in ("*BOUNDARY", "*UBOUNDARY") for k in st.items) or (i == 0 and model_bc):
            continue
        yield (
            f"step {st.name} has no *Boundary; numgeo then takes size() of its unallocated "
            "boundary-condition array (undefined behaviour); write the boundary conditions of every step",
            _sloc(st),
        )


# ============================================================================= boundary conditions
_BC_TYPES = {
    "VELOCITY": 1,
    "ACCELERATION": 2,
    "HYDROSTATIC": 3,
    "CONTACTPRESSURE": 4,
    "INCREMENT": 5,
    "MOVING-HYDROSTATIC": 6,
}
_BC_NAMES = {v: k.lower() for k, v in _BC_TYPES.items()} | {0: "none (total value)"}


def bc_type(text: str) -> int:
    """Boundary-condition type numgeo reads from the option text (src/input/read_step_.f90:1384-1397).

    >>> bc_type("TYPE=HYDROSTATIC,AMPLITUDE=A"), bc_type("AMPLITUDE=A,TYPE=HYDROSTATIC")
    (3, 0)
    >>> bc_type("MOVING-HYDROSTATIC"), bc_type("TYPE=MOVING-HYDROSTATIC")
    (3, 6)
    """
    if "VELOCITY" in text:
        return 1
    if "ACCELERATION" in text:
        return 2
    i = text.rfind("HYDROSTATIC")
    if 0 <= i < 9:  # Fortran: index(..., back=.true.) < 10
        return 3
    if "CONTACTPRESSURE" in text:
        return 4
    if "INCREMENT" in text:
        return 5
    if "MOVING-HYDROSTATIC" in text:
        return 6
    return 0


def _intended_type(kw: Keyword) -> tuple[str | None, int | None]:
    """The type the user wrote (``type=<t>`` or a bare type word) and its number (``None`` if unknown)."""
    for k, v in kw.options:
        if k == "TYPE" and v is not None:
            return v, _BC_TYPES.get(_key(v))
    for k, v in kw.options:
        if v is None and k in _BC_TYPES:
            return k.lower(), _BC_TYPES[k]
    return None, 0


def _bcs(deck: Deck) -> Iterator[tuple[Step | None, Keyword]]:
    for kw in deck.keywords:
        if kw.keyword == "*BOUNDARY":
            yield None, kw
    for _, st, _, kw in _step_items(deck):
        if kw.keyword in ("*BOUNDARY", "*UBOUNDARY"):
            yield st, kw


def _bloc(st: Step | None, kw: Keyword) -> str:
    return _sloc(st, kw) if st is not None else (kw.source or "model *Boundary")


def _where(st: Step | None) -> str:
    return f"step {st.name}" if st is not None else "model"


@rule(
    "NG-BC-101",
    "error",
    "a model-level *Boundary takes no options",
    source="src/input/read_boundary_condition_.f90:54-81 (read_boundary_condition)",
)
def model_bc_options(ctx: Context) -> Iterator[Finding]:
    for i, kw in enumerate(ctx.deck.keywords):
        if kw.keyword == "*BOUNDARY" and kw.options:
            yield (
                "a *Boundary before the first *Step takes no options (numgeo leaves the type undefined); "
                "give typed or amplitude-driven conditions in a step",
                _loc(kw, f"keywords[{i}]"),
            )


@rule(
    "NG-BC-102",
    "warning",
    "hydrostatic boundary condition with zero level 0",
    source="src/soe/soe_apply_boundary_conditions_.f90:170-174,180-184",
)
def hydrostatic_zero(ctx: Context) -> Iterator[Finding]:
    for st, kw in _bcs(ctx.deck):
        if st is None or kw.keyword != "*BOUNDARY" or bc_type(_opt_text(kw)) != 3:
            continue
        for r in kw.data:
            zl = _num(r[3]) if len(r) > 3 else None
            if zl is not None and abs(zl) <= 1e-7:
                yield (
                    f"step {st.name}: hydrostatic boundary condition on {r[0]} with zero level 0: numgeo "
                    "uses p = slope*x_v instead of slope*(0 - x_v) (sign flips)",
                    _bloc(st, kw),
                )


@rule(
    "NG-BC-103",
    "error",
    "the boundary-condition type numgeo reads must be the one written",
    source="src/input/read_step_.f90:1384-1412 (read_step)",
)
def bc_type_read(ctx: Context) -> Iterator[Finding]:
    for st, kw in _bcs(ctx.deck):
        if st is None:
            continue
        written, want = _intended_type(kw)
        got = bc_type(_opt_text(kw))
        if written is not None and want is None:
            yield (
                f"{_where(st)}: {display(ctx.catalogue, kw.keyword)}, type={written} is not a "
                f"boundary-condition type; numgeo reads type {_BC_NAMES[got]}",
                _bloc(st, kw),
            )
        elif want is not None and want != 0 and want != got:
            yield (
                f"{_where(st)}: {display(ctx.catalogue, kw.keyword)} is meant as type {_BC_NAMES[want]} but "
                f"numgeo reads type {_BC_NAMES[got]} (write type=... as the first option)",
                _bloc(st, kw),
            )


_BC_WORDS = ("VELOCITY", "ACCELERATION", "HYDROSTATIC", "CONTACTPRESSURE", "INCREMENT")


@rule(
    "NG-BC-104",
    "error",
    "amplitude names on *Boundary must not contain type words",
    source="src/input/read_step_.f90:1385-1397,1419-1464 (read_step)",
)
def bc_amplitude_names(ctx: Context) -> Iterator[Finding]:
    for st, kw in _bcs(ctx.deck):
        for k, v in kw.options:
            if "AMPL" in k and v is not None:
                words = [w.lower() for w in _BC_WORDS if w in _key(v)]
                if words:
                    yield (
                        f"{_where(st)}: amplitude name {v!r} on {display(ctx.catalogue, kw.keyword)} "
                        f"contains {', '.join(words)}, which numgeo reads as the boundary-condition type",
                        _bloc(st, kw),
                    )


def _dof_names(ctx: Context) -> set[str]:
    return {_key(str(d["name"])) for d in ctx.catalogue.section("loads", "dof_names")}


def _bc_rows(deck: Deck) -> Iterator[tuple[Step | None, Keyword, list[Token]]]:
    for st, kw in _bcs(deck):
        for r in kw.data:
            yield st, kw, r
    for _, st, _, kw in _step_items(deck):
        if kw.keyword in ("*BOUNDARY-FLEXIBLE", "*ROBIN"):
            for r in kw.data:
                yield st, kw, r


@rule(
    "NG-BC-105",
    "error",
    "boundary-condition dofs must be numgeo dof names",
    source="src/input/read_boundary_condition_.f90:118; src/input/read_step_.f90:1548; src/input/read_robin_.f90:98",
)
def bc_dof_names(ctx: Context) -> Iterator[Finding]:
    known = _dof_names(ctx)
    for st, kw, r in _bc_rows(ctx.deck):
        if len(r) >= 2 and _key(str(r[1])) not in known:
            yield (
                f"{_where(st)}: {display(ctx.catalogue, kw.keyword)} dof {r[1]!r} is not one of "
                f"{', '.join(sorted(d.lower() for d in known))}",
                _bloc(st, kw),
            )


def _refnode_sets(deck: Deck) -> set[str]:
    out = set()
    for _, _, _, kw in _step_items(deck):
        if kw.keyword == "*RIGIDBODY":
            for k, v in kw.options:
                if "REFNODE" in k and v is not None:
                    out.add(_key(v))
    return out


def _missing_dof(ctx: Context, dofs: dict[int, set[str]], nset: str, dof: str) -> int | None:
    """Number of nodes of ``nset`` without ``dof`` (``None`` if the set cannot be evaluated)."""
    mem = _nset_members(ctx.deck, nset)
    if mem is None:
        return None
    return sum(1 for n in mem if dof not in dofs.get(n, set()))


def _dof_findings(ctx: Context, user: bool) -> Iterator[Finding]:
    known = _dof_names(ctx)
    dofs = _node_dofs(ctx)
    refs = _refnode_sets(ctx.deck)
    for st, kw, r in _bc_rows(ctx.deck):
        if (kw.keyword != "*BOUNDARY") != user or len(r) < 2:
            continue
        d = _key(str(r[1]))
        if d not in known or (d.startswith("R") and _key(str(r[0])) in refs):
            continue
        miss = _missing_dof(ctx, dofs, str(r[0]), d)
        if miss:
            what = "numgeo skips them with a warning" if not user else "numgeo does not skip them"
            yield (
                f"{_where(st)}: {display(ctx.catalogue, kw.keyword)}, {r[0]}, {d.lower()}: {miss} node(s) of "
                f"the set have no {d.lower()} dof ({what})",
                _bloc(st, kw),
            )


@rule(
    "NG-BC-106",
    "warning",
    "*Boundary dofs should exist at the nodes of the set",
    source="src/soe/soe_apply_boundary_conditions_.f90:123-133",
)
def bc_dof_missing(ctx: Context) -> Iterator[Finding]:
    yield from _dof_findings(ctx, user=False)


@rule(
    "NG-BC-107",
    "error",
    "*UBoundary, *Boundary-flexible and *Robin dofs must exist at every node of the set",
    source="src/input/read_flexible_bc_.f90:91; src/input/read_robin_.f90:98",
)
def bc_dof_missing_user(ctx: Context) -> Iterator[Finding]:
    yield from _dof_findings(ctx, user=True)


@rule(
    "NG-BC-108",
    "error",
    "*UBoundary takes only the types none, velocity and acceleration",
    source="src/soe/soe_apply_boundary_conditions_.f90:315-346 (apply_boundary_conditions)",
)
def ubc_type(ctx: Context) -> Iterator[Finding]:
    for st, kw in _bcs(ctx.deck):
        if kw.keyword == "*UBOUNDARY" and bc_type(_opt_text(kw)) > 2:
            yield (
                f"step {st.name if st else '?'}: *UBoundary with type {_BC_NAMES[bc_type(_opt_text(kw))]} "
                "has no effect (user boundary conditions support none, velocity, acceleration)",
                _bloc(st, kw),
            )


@rule(
    "NG-BC-109",
    "error",
    "*Robin / *Boundary-flexible data lines must match the type",
    source="src/input/read_robin_.f90:81-95; src/input/read_flexible_bc_.f90:80-95",
)
def robin_fields(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword not in ("*ROBIN", "*BOUNDARY-FLEXIBLE"):
            continue
        moving = "MOVING-HYDROSTATIC" in _opt_text(kw)
        robin = kw.keyword == "*ROBIN"
        need = ((8, 9) if robin else (8,)) if moving else ((3, 4) if robin else (3,))
        for r in kw.data:
            if len(r) not in need:
                yield (
                    f"step {st.name}: {display(ctx.catalogue, kw.keyword)}"
                    f"{', type=moving-hydrostatic' if moving else ''} needs {' or '.join(map(str, need))} "
                    f"fields per line, {len(r)} given",
                    _sloc(st, kw),
                )
                break


@rule(
    "NG-BC-110",
    "error",
    "*Boundary data lines must match the type numgeo reads",
    source="src/input/read_step_.f90:1480-1503 (read_step); src/input/read_boundary_condition_.f90:92",
)
def bc_fields(ctx: Context) -> Iterator[Finding]:
    for st, kw in _bcs(ctx.deck):
        t = bc_type(_opt_text(kw)) if st is not None else 0
        need = {3: 4, 6: 8}.get(t, 3)
        for r in kw.data:
            if len(r) != need:
                yield (
                    f"{_where(st)}: {display(ctx.catalogue, kw.keyword)} (type {_BC_NAMES[t]}) needs {need} "
                    f"fields per line, {len(r)} given",
                    _bloc(st, kw),
                )
                break
            if not all(is_real_token(x) for x in r[2:]):
                yield (
                    f"{_where(st)}: {display(ctx.catalogue, kw.keyword)}: values after the dof must be "
                    f"numbers ({', '.join(str(x) for x in r)})",
                    _bloc(st, kw),
                )
                break


# ============================================================================= loads, constraints, reactions
@rule(
    "NG-LOAD-101",
    "error",
    "*Contact penalty takes instant or ramp, not amplitude=",
    source="src/input/read_penalty_factor_.f90:96-104 (read_penalty_factor)",
)
def penalty_amplitude(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword == "*CONTACTPENALTY" and "AMPLITUDE=" in _opt_text(kw):
            yield (
                f"step {st.name}: *Contact penalty, amplitude= can never succeed in numgeo (the amplitude is "
                "looked up with the whole option text); use instant or ramp",
                _sloc(st, kw),
            )


@rule(
    "NG-LOAD-102",
    "error",
    "*Contact penalty, stiffness needs instant or ramp",
    source="src/input/read_penalty_factor_.f90:86,114-116; src/load/load_library.f90:235-262",
)
def penalty_stiffness(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        t = _opt_text(kw)
        if kw.keyword == "*CONTACTPENALTY" and "STIFFNESS" in t and not any(w in t for w in ("INSTANT", "RAMP")):
            yield (
                f"step {st.name}: *Contact penalty, stiffness without instant or ramp leaves the amplitude id at -1",
                _sloc(st, kw),
            )


def _rigid_sets(kw: Keyword) -> tuple[str | None, str | None]:
    nset = ref = None
    for k, v in kw.options:  # numgeo: substring NSET first, then REFNODE (read_equation_.f90:291-309)
        if "NSET" in k and nset is None:
            nset = v
        elif "REFNODE" in k:
            ref = v
    return nset, ref


@rule(
    "NG-LOAD-103",
    "error",
    "*Rigid body needs existing nset= and refnode= sets",
    source="src/input/read_equation_.f90:296-299,305-308 (parse_rigid_body_keywords)",
)
def rigid_body_sets(ctx: Context) -> Iterator[Finding]:
    nsets = {s.key for s in ctx.deck.mesh.nsets}
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*RIGIDBODY":
            continue
        for label, v in zip(("nset", "refnode"), _rigid_sets(kw), strict=True):
            if not v:
                yield f"step {st.name}: *Rigid body needs {label}=<node set>", _sloc(st, kw)
            elif _key(v) not in nsets:
                yield f"step {st.name}: *Rigid body, {label}={v}: node set not defined", _sloc(st, kw)


@rule(
    "NG-LOAD-104",
    "error",
    "*Penalty after *Rigid body swallows the next line",
    source="src/input/read_equation_.f90:77-92 (read_equation)",
)
def rigid_body_penalty(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword == "*RIGIDBODY" and any(c.keyword == "*PENALTY" for c in kw.children):
            yield (
                f"step {st.name}: *Penalty after *Rigid body: numgeo reads and discards the line after it "
                "(the next keyword is lost)",
                _sloc(st, kw),
            )


@rule(
    "NG-LOAD-105",
    "error",
    "*Rigid body refnode names must not contain 'nset'",
    source="src/input/read_equation_.f90:291-309 (parse_rigid_body_keywords)",
)
def rigid_body_refnode_name(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword != "*RIGIDBODY":
            continue
        for k, v in kw.options:
            if "REFNODE" in k and v is not None and "NSET" in _key(v):
                yield (
                    f"step {st.name}: *Rigid body, refnode={v}: the name contains 'nset' and numgeo reads it "
                    "as the nset= option",
                    _sloc(st, kw),
                )


@rule(
    "NG-LOAD-106",
    "error",
    "with *Rigid body only r3 on reference sets is converted",
    source="src/input/read_equation_.f90:414-462 (add_boundary_conditions_rigid_body)",
)
def rigid_body_rotations(ctx: Context) -> Iterator[Finding]:
    refs = _refnode_sets(ctx.deck)
    if not any(kw.keyword == "*RIGIDBODY" for _, _, _, kw in _step_items(ctx.deck)):
        return
    for st, kw, r in _bc_rows(ctx.deck):
        if kw.keyword not in ("*BOUNDARY", "*UBOUNDARY") or len(r) < 2:
            continue
        d, s = _key(str(r[1])), _key(str(r[0]))
        if d in ("R1", "R2") and s in refs:
            yield (
                f"{_where(st)}: {d.lower()} on the rigid-body reference set {r[0]} is not converted by "
                "numgeo (only r3)",
                _bloc(st, kw),
            )
        elif d in ("R1", "R2", "R3") and s not in refs:
            yield (
                f"{_where(st)}: rotational boundary condition {d.lower()} on {r[0]} in a model with *Rigid "
                "body: numgeo searches it among the rigid-body equations and reads out of bounds",
                _bloc(st, kw),
            )


@rule(
    "NG-LOAD-107",
    "error",
    "*Save reaction force and *Reaction force must not be interleaved in a step",
    source="src/input/read_step_.f90:1607-1631; src/input/read_save_reaction_force_.f90:60-74",
)
def reaction_interleaved(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        seq = "".join(
            "S" if k.keyword == "*SAVEREACTIONFORCE" else "R"
            for k in st.items
            if k.keyword in ("*SAVEREACTIONFORCE", "*REACTIONFORCE")
        )
        if re.search(r"SR+S|RS+R", seq):
            yield (
                f"step {st.name}: *Save reaction force and *Reaction force are interleaved; numgeo's shared "
                "counter overwrites an entry (write all of one kind first)",
                _sloc(st),
            )


def _rf_pairs(st: Step, keyword: str) -> set[tuple[str, str]]:
    out = set()
    for k in st.items:
        if k.keyword == keyword:
            for r in k.data:
                if len(r) >= 2:
                    out.add((_key(str(r[0])), _key(str(r[1]))))
    return out


@rule(
    "NG-LOAD-108",
    "error",
    "*Reaction force needs the matching save in the last saving step",
    source="src/soe/soe_reaction_force_.f90:109-124,182-186 (soe_reaction_force)",
)
def reaction_saved(ctx: Context) -> Iterator[Finding]:
    last: set[tuple[str, str]] | None = None
    last_name = ""
    for st in ctx.deck.steps:
        for set_, d in sorted(_rf_pairs(st, "*REACTIONFORCE")):
            if last is None or (set_, d) not in last:
                where = f"step {last_name}" if last is not None else "no earlier step"
                yield (
                    f"step {st.name}: *Reaction force {set_.lower()}, {d.lower()} has no matching *Save "
                    f"reaction force in the last earlier step that saves reaction forces ({where})",
                    _sloc(st),
                )
        saved = _rf_pairs(st, "*SAVEREACTIONFORCE")
        if saved:
            last, last_name = saved, st.name


def _dload_rows(deck: Deck) -> Iterator[tuple[Step, Keyword, list[Token]]]:
    for _, st, _, kw in _step_items(deck):
        if kw.keyword in ("*DLOAD", "*DSLOAD"):
            for r in kw.data:
                yield st, kw, r


@rule(
    "NG-LOAD-109",
    "error",
    "*Dload Di directions are x, y, z or 1, 2, 3",
    source="src/input/read_dload_.f90:453-462 (read_dload)",
)
def dload_direction(ctx: Context) -> Iterator[Finding]:
    for st, kw, r in _dload_rows(ctx.deck):
        is_di = kw.keyword == "*DLOAD" and len(r) >= 3 and re.fullmatch(r"D[1-6]", _key(str(r[1])))
        if is_di and _key(str(r[2])) not in ("X", "Y", "Z", "1", "2", "3"):
            yield (
                f"step {st.name}: *Dload {r[1]} direction {r[2]!r} is not x, y, z, 1, 2 or 3 (numgeo "
                "leaves the direction undefined)",
                _sloc(st, kw),
            )


def _compliant(kw: Keyword, label: str) -> bool:
    if kw.keyword == "*DLOAD":
        return re.fullmatch(r"COMPLIANT0?[1-6]", label) is not None
    return label in ("COMPLIANT", "COMPLIANT0")


@rule(
    "NG-LOAD-110",
    "error",
    "compliant-base directions are integers 1..ndim",
    source="src/input/read_dload_.f90:482,502,906,925 (read_dload)",
)
def compliant_direction(ctx: Context) -> Iterator[Finding]:
    nd = _ndim(ctx)
    for st, kw, r in _dload_rows(ctx.deck):
        if len(r) >= 3 and _compliant(kw, _key(str(r[1]))):
            d = r[2]
            if not is_int_token(d) or not 1 <= int(d) <= nd:
                yield (
                    f"step {st.name}: {display(ctx.catalogue, kw.keyword)} {r[1]} direction {d!r} must be an "
                    f"integer 1..{nd}",
                    _sloc(st, kw),
                )


@rule(
    "NG-LOAD-111",
    "error",
    "compliant-base loads need amplitude=",
    source="src/load/load_library.f90:165-172; src/load/load.f90:341-411",
)
def compliant_amplitude(ctx: Context) -> Iterator[Finding]:
    for st, kw, r in _dload_rows(ctx.deck):
        if len(r) >= 2 and _compliant(kw, _key(str(r[1]))) and kw.option("AMPLITUDE") is None:
            yield (
                f"step {st.name}: {display(ctx.catalogue, kw.keyword)} {r[1]} needs amplitude=<velocity "
                "history> (with instant/ramp the signal is the value itself)",
                _sloc(st, kw),
            )


@rule(
    "NG-LOAD-112",
    "error",
    "body forces with different directions must not overlap",
    source="src/fem/fem_global_assemble_elements_.f90:401-410,810-820",
)
def body_force_overlap(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        seen: list[tuple[str, set[int] | None, tuple[float, ...]]] = []
        for kw in st.items:
            if kw.keyword != "*BODYFORCE":
                continue
            for r in kw.data:
                vec = [_num(x) for x in r[3:6]]
                if len(r) < 6 or any(v is None for v in vec):
                    continue
                norm = math.sqrt(sum(float(v) ** 2 for v in vec if v is not None)) or 1.0
                d = tuple(round(float(v) / norm, 9) for v in vec if v is not None)
                mem = _elset_members(ctx.deck, str(r[0]))
                for name, other, od in seen:
                    overlap = (_key(name) == _key(str(r[0]))) or (
                        mem is not None and other is not None and bool(mem & other)
                    )
                    if overlap and od != d:
                        yield (
                            f"step {st.name}: body forces on {name} and {r[0]} overlap with different "
                            "directions; numgeo adds the magnitudes and keeps the last direction",
                            _sloc(st, kw),
                        )
                seen.append((str(r[0]), mem, d))


@rule(
    "NG-LOAD-113",
    "error",
    "swp loads exist only in 2D",
    source="src/load/load.f90:301-337 (get_distributed_load)",
)
def swp_3d(ctx: Context) -> Iterator[Finding]:
    if _ndim(ctx) != 3:
        return
    for st, kw, r in _dload_rows(ctx.deck):
        if len(r) >= 2 and re.fullmatch(r"SWP([1-4]W?)?", _key(str(r[1]))):
            yield (
                f"step {st.name}: {display(ctx.catalogue, kw.keyword)} {r[1]} is a 2D load; in 3D numgeo "
                "applies no load and reports no error",
                _sloc(st, kw),
            )


@rule(
    "NG-LOAD-114",
    "error",
    "*Penalty= takes exactly one value",
    source="src/input/read_equation_.f90:77-85 (read_equation)",
)
def penalty_value(ctx: Context) -> Iterator[Finding]:
    for _, st, _, kw in _step_items(ctx.deck):
        if kw.keyword not in ("*EQUATION", "*RIGIDBODY"):
            continue
        for c in kw.children:
            if c.keyword == "*PENALTY" and (_value_count(c) != 1 or not _values_numeric(c)):
                yield f"step {st.name}: *Penalty needs exactly one value (*Penalty=<factor>)", _sloc(st, c)


# ============================================================================= initial conditions
_IC_TYPES = (
    "VOIDRATIO",
    "STRESS",
    "STATEVARIABLES",
    "POREWATERPRESSURE",
    "POREAIRPRESSURE",
    "TEMPERATURE",
    "CONCENTRATION",
    "CONTACT",
    "MEANPRESSURE",
    "VELOCITY",
    "ACCELERATION",
)
# Sub-options per type (catalogue initial_condition_types); '' = omitted.
_IC_SUB = {
    "VOIDRATIO": ("", "DEFAULT", "USER", "CONSTITUTIVEMODEL"),
    "STRESS": ("", "DEFAULT", "NONE", "HOMOGENEOUS", "FULL", "GEOSTATIC", "USER", "FILE"),
    "STATEVARIABLES": (
        "",
        "DEFAULT",
        "X-DATA",
        "Y-DATA",
        "Z-DATA",
        "XY-DATA",
        "XYZ-DATA",
        "FLUCTUATION",
        "USER",
    ),
    "POREWATERPRESSURE": ("", "DEFAULT", "USER"),
    "POREAIRPRESSURE": ("", "DEFAULT", "USER"),
    "TEMPERATURE": ("", "DEFAULT"),
    "CONCENTRATION": ("", "DEFAULT", "USER"),
    "CONTACT": ("", "DEFAULT"),
    "MEANPRESSURE": ("HOMOGENEOUS", "FULL", "GEOSTATIC"),
    "VELOCITY": ("", "DEFAULT"),
    "ACCELERATION": ("", "DEFAULT"),
}


def _ic(kw: Keyword) -> tuple[str, str, str]:
    """(key of the first option, type, sub-option) of ``*Initial conditions`` as numgeo reads them."""
    if not kw.options:
        return "", "", ""
    k, v = kw.options[0]
    sub = ",".join(_key(o) if w is None else f"{_key(o)}={_key(w)}" for o, w in kw.options[1:])
    return _key(k), _key(v), sub


def _ics(deck: Deck) -> Iterator[tuple[int, Keyword, str, str]]:
    for i, kw in enumerate(deck.keywords):
        if kw.keyword == "*INITIALCONDITIONS":
            _, t, sub = _ic(kw)
            yield i, kw, t, sub


def _sub_kind(t: str, sub: str) -> str:
    if t == "STRESS" and sub.startswith("FILE="):
        return "FILE"
    return sub


@rule(
    "NG-IC-101",
    "error",
    "*Initial conditions needs type= as its first option",
    source="src/input/read_input.f90:429; src/input/read_initial_condition_.f90:86-87,456",
)
def ic_type_key(ctx: Context) -> Iterator[Finding]:
    for i, kw in enumerate(ctx.deck.keywords):
        if kw.keyword != "*INITIALCONDITIONS":
            continue
        key, _, _ = _ic(kw)
        if key != "TYPE":
            yield (
                "*Initial conditions: the first option must be type=<type>, got "
                f"{key.lower() or 'nothing'!r} (numgeo "
                "does not check the key; pynumgeo rejects anything else)",
                _loc(kw, f"keywords[{i}]"),
            )


@rule(
    "NG-IC-102",
    "error",
    "*Initial conditions needs a known type and exactly one valid sub-option",
    source="src/input/read_initial_condition_.f90:118-1271 (read_initial_condition)",
)
def ic_suboption(ctx: Context) -> Iterator[Finding]:
    for i, kw, t, sub in _ics(ctx.deck):
        loc = _loc(kw, f"keywords[{i}]")
        if t not in _IC_TYPES:
            yield (
                f"*Initial conditions, type={t.lower() or '?'} is not one of "
                f"{', '.join(x.lower() for x in _IC_TYPES)} (numgeo ignores it silently)",
                loc,
            )
            continue
        kind = _sub_kind(t, sub)
        if kind == "FILE":
            extra = [x for x in sub.split(",")[1:] if x != "MESH=MATCHING"]
            if extra:
                yield (
                    f"*Initial conditions, type=stress, file=...: unknown option(s) {', '.join(extra).lower()}",
                    loc,
                )
        elif kind not in _IC_SUB[t]:
            allowed = ", ".join(x.lower() for x in _IC_SUB[t] if x) or "none"
            yield (
                f"*Initial conditions, type={t.lower()}: sub-option {sub.lower()!r} is not valid (allowed: "
                f"{allowed}{'' if t == 'MEANPRESSURE' else ' or nothing'})",
                loc,
            )


@rule(
    "NG-IC-103",
    "error",
    "the user option has no effect for these initial conditions",
    source="src/initial/initial_pore_air_pressure_.f90:40,59; src/input/read_initial_condition_.f90:962,1023",
)
def ic_user(ctx: Context) -> Iterator[Finding]:
    for i, kw, t, sub in _ics(ctx.deck):
        if sub == "USER" and t in ("VOIDRATIO", "POREWATERPRESSURE", "POREAIRPRESSURE", "CONCENTRATION"):
            yield (
                f"*Initial conditions, type={t.lower()}, user has no effect in numgeo (the application is a "
                "no-op or loops over an unallocated set)",
                _loc(kw, f"keywords[{i}]"),
            )


# Field positions of z1 and z2 in the two-point profiles.
_PROFILES = {
    ("POREWATERPRESSURE", ""),
    ("POREWATERPRESSURE", "DEFAULT"),
    ("POREAIRPRESSURE", ""),
    ("POREAIRPRESSURE", "DEFAULT"),
    ("CONCENTRATION", ""),
    ("CONCENTRATION", "DEFAULT"),
    ("STRESS", "GEOSTATIC"),
    ("MEANPRESSURE", "GEOSTATIC"),
}


@rule(
    "NG-IC-104",
    "error",
    "two-point profiles need z1 /= z2",
    source="src/initial/initial_pore_water_pressure_.f90:90; src/initial/initial_stress_.f90:133; "
    "src/initial/initial_mean_pressure_.f90:91",
)
def ic_z1_z2(ctx: Context) -> Iterator[Finding]:
    for i, kw, t, sub in _ics(ctx.deck):
        if (t, sub) not in _PROFILES:
            continue
        for r in kw.data:
            z1, z2 = (_num(r[1]), _num(r[3])) if len(r) > 3 else (None, None)
            if z1 is not None and z2 is not None and z1 == z2:
                yield (
                    f"*Initial conditions, type={t.lower()}: z1 = z2 = {z1:g} for {r[0]} (numgeo divides by z2 - z1)",
                    _loc(kw, f"keywords[{i}]"),
                )


def _set_nodes(deck: Deck, name: str, element_set: bool) -> set[int] | None:
    if not element_set:
        return _nset_members(deck, name)
    mem = _elset_members(deck, name)
    if mem is None:
        return None
    nodes: set[int] = set()
    for b in deck.mesh.blocks:
        sel = np.isin(b.labels, list(mem))
        if sel.any():
            nodes.update(np.unique(b.connectivity[sel]).tolist())
    return nodes


@rule(
    "NG-IC-105",
    "warning",
    "geostatic profiles mirror beyond z1",
    source="src/initial/initial_stress_.f90:128-134; src/initial/initial_mean_pressure_.f90:86-92",
)
def ic_beyond_z1(ctx: Context) -> Iterator[Finding]:
    mesh = ctx.deck.mesh
    if not mesh.node_count:
        return
    vert = 2 if _ndim(ctx) == 3 else 1  # last model coordinate
    if mesh.coords.shape[1] <= vert:
        return
    zpos = dict(zip(mesh.node_labels.tolist(), mesh.coords[:, vert].tolist(), strict=True))
    for i, kw, t, sub in _ics(ctx.deck):
        if sub != "GEOSTATIC" or t not in ("STRESS", "MEANPRESSURE"):
            continue
        for r in kw.data:
            z1, z2 = (_num(r[1]), _num(r[3])) if len(r) > 4 else (None, None)
            if z1 is None or z2 is None or z1 == z2 or _num(r[2]) == _num(r[4]):
                continue  # a constant profile is not changed by the mirror
            nodes = _set_nodes(ctx.deck, str(r[0]), t == "STRESS")
            if not nodes:
                continue
            side = math.copysign(1.0, z2 - z1)
            tol = 1e-9 * max(1.0, abs(z1), abs(z2))
            beyond = [n for n in nodes if n in zpos and (zpos[n] - z1) * side < -tol]
            if beyond:
                yield (
                    f"*Initial conditions, type={t.lower()}, geostatic: set {r[0]} extends beyond z1 = "
                    f"{z1:g} (away from z2 = {z2:g}); numgeo uses |z1 - z| and mirrors the profile there",
                    _loc(kw, f"keywords[{i}]"),
                )


@rule(
    "NG-IC-106",
    "error",
    "mean pressure initial conditions only with geostatic",
    source="src/initial/initial_mean_pressure_.f90:105-107 (apply_initial_mean_pressure)",
)
def ic_mean_pressure(ctx: Context) -> Iterator[Finding]:
    for i, kw, t, sub in _ics(ctx.deck):
        if t == "MEANPRESSURE" and sub in ("HOMOGENEOUS", "FULL"):
            yield (
                f"*Initial conditions, type=mean pressure, {sub.lower()} is read but rejected when applied; "
                "use geostatic",
                _loc(kw, f"keywords[{i}]"),
            )


@rule(
    "NG-IC-107",
    "warning",
    "only one initial contact state line is used",
    source="src/input/read_initial_condition_.f90:1062-1101; src/initial/initial_state_contact_.f90:61-75",
)
def ic_contact_lines(ctx: Context) -> Iterator[Finding]:
    for i, kw, t, _ in _ics(ctx.deck):
        if t == "CONTACT" and len(kw.data) > 1:
            yield (
                f"*Initial conditions, type=contact has {len(kw.data)} lines; numgeo applies the first line "
                "to every interaction",
                _loc(kw, f"keywords[{i}]"),
            )


def _ic_sets(kw: Keyword) -> list[str]:
    return [str(r[0]) for r in kw.data if r]


@rule(
    "NG-IC-108",
    "error",
    "default and user state-variable blocks must come before a fluctuation block on the same elements",
    source="src/initial/initial_state_variables_.f90:90-102,176-178 (get_initial_state_variables); "
    "src/fem/fem_global_assemble_elements_.f90:271-306",
)
def ic_fluctuation_last(ctx: Context) -> Iterator[Finding]:
    # numgeo sets default and user state variables per integration point, going through the blocks in input
    # order; a block whose sets do not hold the element is passed over, but the fluctuation branch returns, so
    # for the elements of a fluctuation block every later default or user block is lost. Fluctuation and
    # *-DATA blocks are applied afterwards, outside that loop, and are not affected.
    fluct: list[tuple[str, set[int] | None]] = []  # (set name, members or None if unknown)
    for i, kw, t, sub in _ics(ctx.deck):
        if t != "STATEVARIABLES":
            continue
        if sub == "FLUCTUATION":
            fluct += [(s, _elset_members(ctx.deck, s)) for s in _ic_sets(kw)]
            continue
        if not fluct or sub.endswith("-DATA"):
            continue
        hit: set[str] = set()
        for s in _ic_sets(kw):
            mem = _elset_members(ctx.deck, s)
            for fs, fmem in fluct:
                if _key(fs) == _key(s) or mem is None or fmem is None or mem & fmem:
                    hit.add(fs)
        if hit:
            yield (
                f"*Initial conditions, type=state variables{', ' + sub.lower() if sub else ''} after the "
                f"fluctuation block of {', '.join(sorted(hit))}: numgeo skips it for the elements of that "
                "set (the fluctuation branch returns); write fluctuation blocks last",
                _loc(kw, f"keywords[{i}]"),
            )


@rule(
    "NG-IC-109",
    "error",
    "spatial-data state variables: one data line per block",
    source="src/initial/initial_state_variables_.f90:238-239 (get_initial_matvar_from_file)",
)
def ic_data_one_line(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for i, kw, t, sub in _ics(ctx.deck):
        if t == "STATEVARIABLES" and sub.endswith("-DATA") and len(kw.data) > 1:
            yield (
                f"*Initial conditions, type=state variables, {sub.lower()} with {len(kw.data)} lines: numgeo "
                "reads the file name of the wrong line; use one block per file",
                _loc(kw, f"keywords[{i}]"),
            )


@rule(
    "NG-IC-110",
    "error",
    "initial concentrations need nodes with a concentration dof",
    source="src/initial/initial_concentration_.f90:77-79 (apply_initial_concentration)",
)
def ic_concentration_dof(ctx: Context) -> Iterator[Finding]:
    dofs = _node_dofs(ctx)
    for i, kw, t, _ in _ics(ctx.deck):
        if t != "CONCENTRATION":
            continue
        for r in kw.data:
            miss = _missing_dof(ctx, dofs, str(r[0]), "CC") if r else None
            if miss:
                yield (
                    f"*Initial conditions, type=concentration: {miss} node(s) of {r[0]} have no concentration dof",
                    _loc(kw, f"keywords[{i}]"),
                )


def _ic_count(t: str, kind: str) -> tuple[str, int | None, int | None, bool] | None:
    """(text, min fields, max fields, lines allowed) of a type/sub-option from the catalogue table."""
    for row in _IC_TABLE.get(t, ()):
        if kind in row[0]:
            return row[1]
    return None


# (sub-options, (rule text, min narg, max narg, data lines allowed)); catalogue initial_condition_types.
_IC_TABLE: dict[str, list[tuple[tuple[str, ...], tuple[str, int | None, int | None, bool]]]] = {
    "VOIDRATIO": [
        (("", "DEFAULT"), ("2", 2, 2, True)),
        (("USER", "CONSTITUTIVEMODEL"), ("none", None, None, False)),
    ],
    "STRESS": [
        (("", "DEFAULT", "NONE", "USER", "FILE"), ("none", None, None, False)),
        (("HOMOGENEOUS",), ("4", 4, 4, True)),
        (("FULL", "GEOSTATIC"), ("7", 7, 7, True)),
    ],
    "STATEVARIABLES": [
        (("", "DEFAULT", "X-DATA", "Y-DATA", "Z-DATA", "XY-DATA", "XYZ-DATA"), ("3", 3, 3, True)),
        (("FLUCTUATION",), ("5 to 7", 5, 7, True)),
        (("USER",), ("1", 1, 1, True)),
    ],
    "POREWATERPRESSURE": [(("", "DEFAULT"), ("5", 5, 5, True)), (("USER",), ("none", None, None, False))],
    "POREAIRPRESSURE": [(("", "DEFAULT"), ("5", 5, 5, True)), (("USER",), ("none", None, None, False))],
    "TEMPERATURE": [(("", "DEFAULT"), ("2", 2, 2, True))],
    "CONCENTRATION": [(("", "DEFAULT"), ("5", 5, 5, True)), (("USER",), ("none", None, None, False))],
    "CONTACT": [(("", "DEFAULT"), ("2 or 8", 2, 8, True))],
    "MEANPRESSURE": [(("HOMOGENEOUS",), ("4", 4, 4, True)), (("FULL", "GEOSTATIC"), ("7", 7, 7, True))],
    "VELOCITY": [(("", "DEFAULT"), ("3", 3, 3, True))],
    "ACCELERATION": [(("", "DEFAULT"), ("3", 3, 3, True))],
}
_IC_AT_LEAST_ONE = {
    ("STATEVARIABLES", k)
    for k in ("", "DEFAULT", "X-DATA", "Y-DATA", "Z-DATA", "XY-DATA", "XYZ-DATA", "FLUCTUATION", "USER")
} | {("VELOCITY", ""), ("ACCELERATION", "")}


@rule(
    "NG-IC-120",
    "error",
    "initial-condition data lines must match type and sub-option",
    source="src/input/read_initial_condition_.f90:118-1706 (catalogue initial_condition_types)",
)
def ic_data(ctx: Context) -> Iterator[Finding]:
    for i, kw, t, sub in _ics(ctx.deck):
        kind = _sub_kind(t, sub)
        spec = _ic_count(t, kind)
        if spec is None:
            continue  # NG-IC-102
        text, lo, hi, allowed = spec
        loc = _loc(kw, f"keywords[{i}]")
        name = f"*Initial conditions, type={t.lower()}" + (f", {sub.lower()}" if sub else "")
        if not allowed:
            if kw.data:
                yield f"{name} takes no data line (numgeo reads it as a keyword and stops)", loc
            continue
        if not kw.data and (t, kind) in _IC_AT_LEAST_ONE:
            yield f"{name} needs at least one data line", loc
        for r in kw.data:
            n = len(r)
            ok = (n in (2, 8)) if t == "CONTACT" else (lo is not None and hi is not None and lo <= n <= hi)
            if not ok:
                yield f"{name} needs {text} fields per line, {n} given ({_row(r)})", loc
                break


def _row(r: list[Token]) -> str:
    return ", ".join(str(t) for t in r)


# ============================================================================= contact and embedded regions
def _interactions(deck: Deck) -> list[Keyword]:
    return _model_kws(deck, "*INTERACTION")


def _friction(kw: Keyword) -> Keyword | None:
    return next((c for c in kw.children if c.keyword == "*FRICTION"), None)


def _friction_model(fr: Keyword) -> str:
    for k, v in fr.options:
        if "MODEL" in k and v is not None:
            return _key(v)
    return ""


def _ic_contact(deck: Deck) -> bool:
    return any(t == "CONTACT" for _, _, t, _ in _ics(deck))


@rule(
    "NG-CONT-101",
    "error",
    "hypoplastic friction needs *Initial conditions, type=contact",
    source="src/initial/initial_state_contact_.f90:55-75 (get_initial_state_contact)",
)
def hypo_friction_ic(ctx: Context) -> Iterator[Finding]:
    deck = ctx.deck
    if _ic_contact(deck):
        return
    for kw in _interactions(deck):
        fr = _friction(kw)
        if fr is not None and _hash(_friction_model(fr) or "-") in _H_FRIC_HYPO_IC:
            yield (
                f"interaction {kw.option('NAME')}: hypoplastic friction needs the initial void ratio of the "
                "interface (*Initial conditions, type=contact)",
                _loc(fr, "model *Friction"),
            )


@rule(
    "NG-CONT-102",
    "warning",
    "the initial contact state has no effect for this friction model",
    source="src/contacts/contact_library.f90:2023-2040; src/initial/initial_state_contact_.f90:73-75",
)
def sanisand_friction_ic(ctx: Context) -> Iterator[Finding]:
    deck = ctx.deck
    if not _ic_contact(deck):
        return
    for kw in _interactions(deck):
        fr = _friction(kw)
        if fr is not None and _hash(_friction_model(fr) or "-") == _H_FRIC_SANISAND:
            yield (
                f"interaction {kw.option('NAME')}: *Initial conditions, type=contact has no effect for "
                f"friction model {_friction_model(fr).lower()}",
                _loc(fr, "model *Friction"),
            )


@rule(
    "NG-CONT-103",
    "error",
    "this hypoplastic friction model cannot run",
    source="src/contacts/contact_.f90:2402-2406; src/contacts/contact_models.f90:786-801",
)
def hypo_friction_plain(ctx: Context) -> Iterator[Finding]:
    for kw in _interactions(ctx.deck):
        fr = _friction(kw)
        if fr is not None and _hash(_friction_model(fr) or "-") == _H_FRIC_HYPO:
            yield (
                f"interaction {kw.option('NAME')}: friction model {_friction_model(fr).lower()} is in "
                "numgeo's library but has no runnable implementation",
                _loc(fr, "model *Friction"),
            )


def _normal_models(kw: Keyword) -> Iterator[tuple[Keyword, str]]:
    for k in (kw, *[c for c in kw.children if c.keyword == "*NORMAL"]):
        for o, v in k.options:
            if "MECHANICAL" in o and v is not None:
                yield k, _key(v)


@rule(
    "NG-CONT-104",
    "error",
    "normal model kragelsky is not implemented",
    source="src/contacts/contact_.f90:2372-2375; src/contacts/contact_models.f90:841-875",
)
def kragelsky(ctx: Context) -> Iterator[Finding]:
    for kw in _interactions(ctx.deck):
        for k, model in _normal_models(kw):
            if model == "KRAGELSKY":
                yield (
                    f"interaction {kw.option('NAME')}: mechanical=kragelsky is not implemented (runtime "
                    "error 'Constitutive contact model is not available')",
                    _loc(k, "model *Interaction"),
                )


_NORMAL_VALUE_OPTIONS = ("STIFFNESS_FACTOR", "VISCOUS")


@rule(
    "NG-CONT-105",
    "warning",
    "normal options belong on *Normal only",
    source="src/input/read_interaction_.f90:187,223,554-568",
)
def normal_options_twice(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo is fixed.
    for kw in _interactions(ctx.deck):
        on_int = [w for w in _NORMAL_VALUE_OPTIONS if w in _opt_text(kw)]
        normal = next((c for c in kw.children if c.keyword == "*NORMAL"), None)
        if on_int and normal is not None and normal.options:
            yield (
                f"interaction {kw.option('NAME')}: {', '.join(w.lower() for w in on_int)} on *Interaction "
                "together with a *Normal line: numgeo reads the *Normal option at the same position",
                _loc(kw, "model"),
            )


@rule(
    "NG-CONT-106",
    "warning",
    "*Normal without mechanical= resets the normal model to penalty",
    source="src/input/read_interaction_.f90:534-539 (read_normal_contact_setting)",
)
def normal_reset(ctx: Context) -> Iterator[Finding]:
    for kw in _interactions(ctx.deck):
        normal = next((c for c in kw.children if c.keyword == "*NORMAL"), None)
        on_int = [v for o, v in kw.options if "MECHANICAL" in o and v is not None]
        if normal is not None and on_int and not any("MECHANICAL" in o for o, _ in normal.options):
            yield (
                f"interaction {kw.option('NAME')}: mechanical={on_int[0]} on *Interaction is reset to "
                "penalty by the following *Normal line without mechanical=",
                _loc(normal, "model *Normal"),
            )


def _names_with(kws: Iterable[Keyword], key: str, words: tuple[str, ...]) -> Iterator[tuple[Keyword, str, list[str]]]:
    for kw in kws:
        for k, v in kw.options:
            if key in k and v is not None:
                base = _key(v)
                hit = [w for w in words if w in base]
                if hit:
                    yield kw, v, hit
                break


_INTERACTION_WORDS = (
    "USER",
    "NORMAL",
    "MECHANICAL",
    "NOSEPARATION",
    "STIFFNESS_FACTOR",
    "NONCONSTANT",
    "VISCOUS",
    "WATER-FILLEDGAP",
    "WATERFILLEDGAP",
)
_PAIR_WORDS = (
    "ADJUST",
    "PERTURBATION",
    "REFINE",
    "GENERAL",
    "NIGP",
    "NGP",
    "NLGEOM",
    "DOUBLEPASS",
    "DISCRETISATION=",
    "SLIDING=",
    "GAP=",
)
_OPTIONS_WORDS = ("CLEARANCE", "CHECKDISP", "CHECKDIST", "REDUCTION")


@rule(
    "NG-CONT-107",
    "error",
    "interaction names must not contain *Interaction option words",
    source="src/input/read_interaction_.f90:425-512 (read_normal_contact_setting)",
)
def interaction_names(ctx: Context) -> Iterator[Finding]:
    for kw, v, hit in _names_with(_interactions(ctx.deck), "NAME", _INTERACTION_WORDS):
        yield (
            f"interaction name {v!r} contains {', '.join(h.lower() for h in hit)}, which numgeo reads as an option",
            _loc(kw, "model *Interaction"),
        )


@rule(
    "NG-CONT-108",
    "error",
    "interaction names in *Contact pair must not contain pair option words",
    source="src/input/read_contact_pairing_.f90:80-154 (read_contact_pairing)",
)
def pair_names(ctx: Context) -> Iterator[Finding]:
    for kw, v, hit in _names_with(_model_kws(ctx.deck, "*CONTACTPAIR"), "INTERACTION", _PAIR_WORDS):
        yield (
            f"*Contact pair, interaction={v}: the name contains {', '.join(h.lower() for h in hit)}, which "
            "numgeo reads as an option",
            _loc(kw, "model *Contact pair"),
        )


@rule(
    "NG-CONT-109",
    "error",
    "names in *Contact options must not contain its option words",
    source="src/input/read_contact_options_.f90:70,99-123 (read_contact_options)",
)
def options_names(ctx: Context) -> Iterator[Finding]:
    for kw, v, hit in _names_with(_model_kws(ctx.deck, "*CONTACTOPTIONS"), "NAME", _OPTIONS_WORDS):
        yield (
            f"*Contact options, name={v}: the name contains {', '.join(h.lower() for h in hit)}, which "
            "numgeo reads as an option",
            _loc(kw, "model *Contact options"),
        )


_COULOMB = {"COULOMB": (2, 3), "MC": (3, 4), "MOHR-COULOMB": (3, 4)}


@rule(
    "NG-CONT-110",
    "error",
    "friction models need their number of properties",
    source="src/contacts/contact_models.f90:342-355 (contact_selection)",
)
def friction_count(ctx: Context) -> Iterator[Finding]:
    models = {_key(str(m["name"])): m for m in ctx.catalogue.section("interactions", "contact_models")}
    for kw in _interactions(ctx.deck):
        fr = _friction(kw)
        if fr is None or _has_word(kw, "USER"):
            continue
        model, n = _friction_model(fr), len(_flat(fr.data))
        allowed: tuple[int, ...] | None = _COULOMB.get(model)
        if allowed is None and model in models and isinstance(models[model].get("nprops"), int):
            allowed = (int(models[model]["nprops"]),)
        if allowed is not None and n not in allowed:
            yield (
                f"interaction {kw.option('NAME')}: friction model {model.lower()} needs "
                f"{' or '.join(map(str, allowed))} values, {n} given",
                _loc(fr, "model *Friction"),
            )


def _surface_types(ctx: Context, surface: str) -> set[str]:
    """Element types of the elements whose faces form a surface."""
    deck = ctx.deck
    try:
        s = deck.mesh.surface(surface)
    except KeyError:
        return set()
    out: set[str] = set()
    for b in deck.mesh.blocks:
        for r in s.rows:
            if not r:
                continue
            if s.type == "element":
                mem = _elset_members(deck, r[0])
                if mem and np.isin(b.labels, list(mem)).any():
                    out.add(_key(b.type))
            else:
                nodes = _nset_members(deck, r[0])
                if nodes and np.isin(b.connectivity, list(nodes)).any():
                    out.add(_key(b.type))
    return out


@rule(
    "NG-CONT-111",
    "error",
    "one *Fluid interaction per *Interaction, same order and names",
    source="src/contacts/contact_models.f90:376-378; src/input/read_input.f90:158",
)
def fluid_interactions(ctx: Context) -> Iterator[Finding]:
    deck = ctx.deck
    fluids = _model_kws(deck, "*FLUIDINTERACTION")
    water = False
    for kw in _model_kws(deck, "*CONTACTPAIR"):
        for r in kw.data:
            for surf in r[:2]:
                types = _surface_types(ctx, str(surf))
                if any((e := _etype(ctx, t)) is not None and "W1" in e.dofs for t in types):
                    water = True
    if not fluids and not water:
        return
    names = [_key(k.option("NAME")) for k in _interactions(deck)]
    fnames = [_key(next((v for o, v in k.options if "NAME" in o), None)) for k in fluids]
    if names != fnames:
        yield (
            f"*Fluid interaction names {[n.lower() for n in fnames]} must match the *Interaction names "
            f"{[n.lower() for n in names]} one to one and in the same order (numgeo indexes fluid "
            "interactions by the solid interaction)",
            _loc(fluids[0], "model") if fluids else "model",
        )


_FLUID_OPTIONS = ("NAME", "MECHANICAL", "NOSEPARATION")
_CONTACT_OPTIONS = ("NAME", "CLEARANCE", "CHECKDISP", "CHECKDIST", "REDUCTION")


@rule(
    "NG-CONT-112",
    "warning",
    "unknown options of *Fluid interaction and *Contact options are ignored",
    source="src/input/read_fluid_interaction_.f90:66-70; src/input/read_contact_options_.f90:99-221",
)
def contact_unknown_options(ctx: Context) -> Iterator[Finding]:
    for kw in ctx.deck.keywords:
        known = {"*FLUIDINTERACTION": _FLUID_OPTIONS, "*CONTACTOPTIONS": _CONTACT_OPTIONS}.get(kw.keyword)
        if known is None:
            continue
        for k, v in kw.options:
            if not any(w in k for w in known):
                tok = k if v is None else f"{k}={v}"
                yield (
                    f"{display(ctx.catalogue, kw.keyword)}: unknown option {tok.lower()!r} is ignored "
                    f"(known: {', '.join(w.lower() for w in known)})",
                    _loc(kw, "model"),
                )


@rule(
    "NG-CONT-113",
    "error",
    "the general option needs a single contact pair",
    source="src/input/read_contact_pairing_.f90:73,176-180 (read_contact_pairing)",
)
def contact_general(ctx: Context) -> Iterator[Finding]:
    pairs = _model_kws(ctx.deck, "*CONTACTPAIR")
    rows = sum(max(1, len(k.data)) for k in pairs)
    for kw in pairs:
        if _has_word(kw, "GENERAL") and rows > 1:
            yield (
                "*Contact pair, general is only safe in a model with a single contact pair (numgeo's check "
                "reads pairs that are not parsed yet)",
                _loc(kw, "model *Contact pair"),
            )


@rule(
    "NG-CONT-114",
    "error",
    "clearance, check disp and check dist need a value",
    source="src/input/read_contact_options_.f90:99-121 (read_contact_options)",
)
def contact_option_values(ctx: Context) -> Iterator[Finding]:
    for kw in _model_kws(ctx.deck, "*CONTACTOPTIONS"):
        for k, v in kw.options:
            if v is None and any(w in k for w in ("CLEARANCE", "CHECKDISP", "CHECKDIST")):
                yield (
                    f"*Contact options: {k.lower()} needs a value ({k.lower()}=<value>); numgeo's read fails",
                    _loc(kw, "model *Contact options"),
                )


@rule(
    "NG-CONT-115",
    "error",
    "hypoplastic friction needs 17 values",
    source="src/contacts/contact_models.f90:2196-2199,2261,2290,2355-2357 (HypoFric_NUMGEO)",
)
def hypo_friction_count(ctx: Context) -> Iterator[Finding]:
    for kw in _interactions(ctx.deck):
        fr = _friction(kw)
        if fr is None or _has_word(kw, "USER") or _hash(_friction_model(fr) or "-") not in _H_FRIC_17:
            continue
        n = len(_flat(fr.data))
        if n != 17:
            yield (
                f"interaction {kw.option('NAME')}: hypoplastic friction needs 17 values (15 continuum "
                f"parameters, chi, K^w), {n} given",
                _loc(fr, "model *Friction"),
            )


@rule(
    "NG-CONT-116",
    "error",
    "HCA hypoplastic friction needs 37 values and an hca_hypoplasticity material",
    source="src/contacts/contact_.f90:2432-2442; src/contacts/contact_models.f90:2234-2235,2261",
)
def hca_friction(ctx: Context) -> Iterator[Finding]:
    has_hca = any(_mech(m) == "HCA_HYPOPLASTICITY" for m in ctx.deck.materials)
    for kw in _interactions(ctx.deck):
        fr = _friction(kw)
        if fr is None or _hash(_friction_model(fr) or "-") not in _H_FRIC_HCA:
            continue
        n = len(_flat(fr.data))
        if n != 37 and not _has_word(kw, "USER"):
            yield (
                f"interaction {kw.option('NAME')}: HCA hypoplastic friction needs 37 values, {n} given",
                _loc(fr, "model *Friction"),
            )
        if not has_hca:
            yield (
                f"interaction {kw.option('NAME')}: HCA hypoplastic friction needs a continuum material with "
                "*Mechanical=hca_hypoplasticity in the model",
                _loc(fr, "model *Friction"),
            )


def _embedded_method(kw: Keyword) -> str:
    keys = [_key(k) for k, _ in kw.options]
    if any("ABSORBED" in k for k in keys):
        return "ABSORBED"
    if any(k.startswith("INTERACTION") and k != "INTERACTION" for k in keys):
        return "OTHER"  # variants the public catalogue does not describe
    if any("INTERACTION" in k for k in keys):
        return "INTERACTION"
    return ""


@rule(
    "NG-CONT-117",
    "error",
    "*Embedded region needs at least one data line",
    source="src/input/read_embedded_region_.f90:105,777 (read_embedded_region)",
)
def embedded_lines(ctx: Context) -> Iterator[Finding]:
    for kw in _model_kws(ctx.deck, "*EMBEDDEDREGION"):
        if _embedded_method(kw) in ("ABSORBED", "INTERACTION") and not kw.data:
            yield (
                f"*Embedded region, {_embedded_method(kw).lower()} needs at least one data line (numgeo's "
                "check uses global counters)",
                _loc(kw, "model *Embedded region"),
            )


_EMB_VALUES = {"TYPE": ("CONSTANT", "MOHR-COULOMB"), "SECTION": ("BAR", "SHEET")}


@rule(
    "NG-CONT-118",
    "error",
    "*Embedded region, interaction: type and section values",
    source="src/input/read_embedded_region_.f90:749-765 (read_embedded_region)",
)
def embedded_values(ctx: Context) -> Iterator[Finding]:
    for kw in _model_kws(ctx.deck, "*EMBEDDEDREGION"):
        if _embedded_method(kw) != "INTERACTION":
            continue
        for k, v in kw.options:
            if k in _EMB_VALUES and (v is None or _key(v) not in _EMB_VALUES[k]):
                yield (
                    f"*Embedded region, interaction: {k.lower()}={v} is not one of "
                    f"{', '.join(x.lower() for x in _EMB_VALUES[k])} (numgeo matches by substring)",
                    _loc(kw, "model *Embedded region"),
                )


@rule(
    "NG-CONT-119",
    "error",
    "*Embedded region, interaction takes only type= and section=",
    source="src/input/read_embedded_region_.f90:746-770 (read_embedded_region)",
)
def embedded_options(ctx: Context) -> Iterator[Finding]:
    for kw in _model_kws(ctx.deck, "*EMBEDDEDREGION"):
        if _embedded_method(kw) != "INTERACTION":
            continue
        for k, v in kw.options:
            if k != "INTERACTION" and k not in _EMB_VALUES:
                tok = k if v is None else f"{k}={v}"
                yield (
                    f"*Embedded region, interaction: unknown option {tok.lower()!r} (numgeo ignores it)",
                    _loc(kw, "model *Embedded region"),
                )


@rule(
    "NG-CONT-120",
    "error",
    "*Embedded region needs a method numgeo reads",
    source="src/input/read_embedded_region_.f90:881-886; src/database/embedded_region_ty_.f90:333-354",
)
def embedded_method(ctx: Context) -> Iterator[Finding]:
    for kw in _model_kws(ctx.deck, "*EMBEDDEDREGION"):
        if not _embedded_method(kw):
            yield (
                f"*Embedded region, {_opt_text(kw).lower() or '(no method)'}: unknown method (absorbed or "
                "interaction; coupled and contact embedding have no reader)",
                _loc(kw, "model *Embedded region"),
            )


def _friction_publicity(ctx: Context) -> Iterator[tuple[Keyword, str, bool | None]]:
    """(friction keyword, model, public) for every friction model; public None = not described publicly."""
    models = {_key(str(m["name"])): m for m in ctx.catalogue.section("interactions", "contact_models")}
    for kw in _interactions(ctx.deck):
        fr = _friction(kw)
        if fr is None:
            continue
        model = _friction_model(fr)
        if model in models:
            yield fr, model, bool(models[model].get("public", True))
        elif model and ctx.catalogue.is_private_name(model):
            yield fr, model, None


@rule(
    "NG-CONT-121",
    "warning",
    "non-public friction models run only in non-public builds",
    source="src/tools/global_settings_.f90:27; src/input/read_interaction_.f90:349-353",
)
def friction_nonpublic(ctx: Context) -> Iterator[Finding]:
    if ctx.profile.public:
        return
    for fr, model, public in _friction_publicity(ctx):
        if public is not True:
            yield (
                f"friction model {model.lower()} is accepted only by numgeo builds with public_version = "
                ".false.; public builds reject it",
                _loc(fr, "model *Friction"),
            )


@rule(
    "NG-CONT-122",
    "error",
    "non-public friction models are rejected by public builds",
    source="src/input/read_interaction_.f90:349-353 (read_interaction)",
)
def friction_public_build(ctx: Context) -> Iterator[Finding]:
    if not ctx.profile.public:
        return
    for fr, model, public in _friction_publicity(ctx):
        if public is not True:
            yield (
                f"friction model {model.lower()} is not available in public numgeo builds",
                _loc(fr, "model *Friction"),
            )


@rule(
    "NG-CONT-123",
    "error",
    "segment mortar is not available in 3D",
    source="src/output/VTK_write_contact_diagnostic_.f90:86-99,240-251,278-292",
)
def segment_mortar_3d(ctx: Context) -> Iterator[Finding]:
    if _ndim(ctx) != 3:
        return
    for kw in _model_kws(ctx.deck, "*CONTACTPAIR"):
        if "DISCRETISATION=SEGMENTMORTAR" in _opt_text(kw):
            yield (
                "*Contact pair, discretisation=segmentmortar in a 3D model: numgeo writes the contact "
                "diagnostics out of bounds",
                _loc(kw, "model *Contact pair"),
            )


@rule(
    "NG-CONT-124",
    "error",
    "friction models must exist in numgeo's contact library",
    source="src/input/read_interaction_.f90:341-347 (read_interaction)",
)
def friction_unknown(ctx: Context) -> Iterator[Finding]:
    models = {_key(str(m["name"])) for m in ctx.catalogue.section("interactions", "contact_models")}
    for kw in _interactions(ctx.deck):
        fr = _friction(kw)
        if fr is None:
            continue
        model = _friction_model(fr)
        if model and model not in models and not ctx.catalogue.is_private_name(model):
            yield (
                f"interaction {kw.option('NAME')}: friction model {model.lower()} is not in numgeo's contact "
                f"library ({', '.join(sorted(m.lower() for m in models))})",
                _loc(fr, "model *Friction"),
            )


# ============================================================================= output
def _outputs(deck: Deck) -> Iterator[tuple[Step, Keyword]]:
    for _, st, _, kw in _step_items(deck):
        if kw.keyword == "*OUTPUT":
            yield st, kw


@rule(
    "NG-OUT-101",
    "error",
    "pa print output needs nodes with a pore-air dof",
    source="src/output/print_type.f90:739-745 (print_get_output_array_node)",
)
def print_pa(ctx: Context) -> Iterator[Finding]:
    dofs: dict[int, set[str]] | None = None
    for st, kw in _outputs(ctx.deck):
        if output_type(kw) != "print":
            continue
        for c in kw.children:
            if c.keyword != "*NODEOUTPUT" or not c.data or "PA" not in {_key(str(t)) for t in c.data[0]}:
                continue
            nset = c.option("NSET")
            if nset is None:
                continue
            dofs = dofs if dofs is not None else _node_dofs(ctx)
            miss = _missing_dof(ctx, dofs, nset, "PA")
            if miss:
                yield (
                    f"step {st.name}: print output pa for {nset}: {miss} node(s) have no pore-air dof "
                    "(numgeo does not check it)",
                    _sloc(st, c),
                )


@rule(
    "NG-OUT-102",
    "error",
    "*Frequency needs a positive integer",
    source="src/input/read_step_.f90:1826-1837,1937-1946,2202-2211 (read_step)",
)
def output_frequency(ctx: Context) -> Iterator[Finding]:
    for st, kw in _outputs(ctx.deck):
        for c in kw.children:
            if c.keyword == "*FREQUENCY" and (
                c.options or c.value is None or not is_int_token(c.value) or int(c.value) < 1
            ):
                yield (
                    f"step {st.name}: *Frequency needs =<positive integer>, got {line_text(c).lower()!r}",
                    _sloc(st, c),
                )


@rule(
    "NG-OUT-103",
    "error",
    "*Output, field, vtk, hdf5 is not supported",
    source="src/input/read_step_.f90:1786-1790 (read_step)",
)
def vtk_hdf5(ctx: Context) -> Iterator[Finding]:
    for st, kw in _outputs(ctx.deck):
        t = _opt_text(kw)
        if output_type(kw) == "field" and "GID" not in t and "HDF5" in t and "ASCII" not in t and "BINARY" not in t:
            yield (
                f"step {st.name}: *Output, field with vtk (or no format) and hdf5 is not supported (numgeo "
                "accepts it without a message)",
                _sloc(st, kw),
            )


@rule(
    "NG-OUT-104",
    "warning",
    "*Output, user element output overwrites user_initial_state_variables.f90",
    source="src/output/user_type.f90:209-224,399-405 (user_write_results)",
)
def user_output_files(ctx: Context) -> Iterator[Finding]:
    for st, kw in _outputs(ctx.deck):
        if output_type(kw) == "user" and any(c.keyword == "*ELEMENTOUTPUT" for c in kw.children):
            yield (
                f"step {st.name}: *Output, user element output writes user_initial_stress.f90 and replaces "
                "user_initial_state_variables.f90 in the job folder",
                _sloc(st, kw),
            )


# (model, parameter position, test, message) of the values numgeo clamps silently.
_CLAMPS = (
    ("BAROTROPIC_ELASTICITY", 4, lambda v: v < 1.0, "p0 < 1 is replaced by 1"),
    ("UNSATURATED_ELASTICITY", 4, lambda v: v < 1.0, "s0 < 1 is replaced by 1"),
    ("MOHR-COULOMB", 6, lambda v: not 25.0 <= v <= 29.5, "theta is clamped to 25..29.5 degrees"),
)


@rule(
    "NG-MAT-128",
    "warning",
    "parameters that numgeo clamps silently",
    source="src/materials/models/material_barotropic_elasticity.f90:68; "
    "src/materials/models/material_unsaturated_elasticity.f90:67; "
    "src/materials/models/material_mohr_coulomb_.f90:1002-1003",
)
def clamped_parameters(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*Mechanical")
        if p is None:
            continue
        vals = _flat(p.data)
        for model, pos, test, what in _CLAMPS:
            v = _num(vals[pos - 1]) if _mech(m) == model and len(vals) >= pos else None
            if v is not None and test(v):
                yield (
                    f"material {m.name}: {model.lower()} parameter {pos} = {v:g}: {what} by numgeo",
                    _mloc(m),
                )


def _statev_rows(deck: Deck) -> Iterator[tuple[Keyword, list[Token], str]]:
    """(keyword, row, location) of every row that names a state variable: ``elset, sv_name, ...``."""
    for i, kw, t, sub in _ics(deck):
        if t == "STATEVARIABLES" and sub != "USER":
            for r in kw.data:
                yield kw, r, _loc(kw, f"keywords[{i}]")
    for _, st, _, kw in _step_items(deck):
        if kw.keyword == "*MODIFY":
            for r in kw.data:
                yield kw, r, _sloc(st, kw)


@rule(
    "NG-MAT-129",
    "error",
    "state-variable names without a state-variable index cannot be used",
    source="src/materials/material_library.f90:150,295-299,865-868,887-890; src/output/output_variables_.f90:66-69",
)
def statev_without_index(ctx: Context) -> Iterator[Finding]:
    # TODO: also bathytropic-elasticity E0 and neo_hooke STRESS_INITIAL*.
    deck = ctx.deck
    section = {_key(s.elset): _key(s.material) for s in deck.sections}
    mats = {_key(m.name): m for m in deck.materials}
    for kw, r, loc in _statev_rows(deck):
        if len(r) < 2:
            continue
        m = mats.get(section.get(_key(str(r[0])), ""))
        if m is None:
            continue
        try:
            spec = ctx.catalogue.material_model(_mech(m))
        except KeyError:
            continue
        index = {_key(str(x.get("name"))): x.get("statev_index") for x in spec.raw.get("statev_names") or ()}
        sv = _key(str(r[1]))
        if sv in index and index[sv] is None:
            yield (
                f"{display(ctx.catalogue, kw.keyword)}: state variable {r[1]} of {spec.name.lower()} has no "
                "state-variable index in numgeo (the name cannot be resolved)",
                loc,
            )
