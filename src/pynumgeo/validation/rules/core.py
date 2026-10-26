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
"""Core rules: mesh, names, references, materials, steps.

Each rule mirrors a solver behaviour; ``source`` in the rule metadata names the solver lines.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator

import numpy as np

from pynumgeo.deck.deck import Material
from pynumgeo.deck.keyword import Keyword
from pynumgeo.deck.names import RISKY_WORDS
from pynumgeo.io.numbers import is_number
from pynumgeo.validation.engine import Context, Finding, rule

# Option words that numgeo's readers find inside a name (substring matching), per kind of name.
_RISKY_WORDS = RISKY_WORDS
_FORBIDDEN_CHARS = re.compile(r"[,=*$\t\"']")


def _key(s: str) -> str:
    return s.upper().replace(" ", "")


# ----------------------------------------------------------------------------- mesh
@rule(
    "NG-MESH-001",
    "error",
    "node labels must be 1..n in the order of definition",
    source="src/soe/soe_apply_boundary_conditions_.f90:119-120 (labels used as positions)",
)
def node_labels(ctx: Context) -> Iterator[Finding]:
    m = ctx.deck.mesh
    n = m.node_count
    if n and not np.array_equal(m.node_labels, np.arange(1, n + 1)):
        bad = int(np.argmax(m.node_labels != np.arange(1, n + 1)))
        yield (
            f"node {bad + 1} of the *Node block has label {int(m.node_labels[bad])}; numgeo uses node labels as "
            "positions, so they must be 1..n in order (use Mesh.renumbered())"
        )


@rule("NG-MESH-002", "error", "element labels must be unique", source="src/input/read_elements_.f90:167-179")
def element_labels(ctx: Context) -> Iterator[Finding]:
    el = ctx.deck.mesh.element_labels
    if el.size and np.unique(el).size != el.size:
        dup = Counter(el.tolist()).most_common(1)[0][0]
        yield f"element label {dup} is used more than once"
    if el.size and int(el.min()) < 1:
        yield "element labels must be positive"


@rule(
    "NG-MESH-003",
    "error",
    "connectivity must refer to defined nodes",
    source="src/database/database.f90:1762-1779",
)
def connectivity(ctx: Context) -> Iterator[Finding]:
    m = ctx.deck.mesh
    if not m.blocks:
        return
    defined = set(m.node_labels.tolist())
    for b in m.blocks:
        missing = set(np.unique(b.connectivity).tolist()) - defined
        if missing:
            yield f"*Element, type={b.type.lower()}: undefined node labels, e.g. {sorted(missing)[:5]}"


@rule(
    "NG-MESH-004",
    "error",
    "every node must be used by an element",
    source="src/database/database.f90:1791-1801",
)
def unused_nodes(ctx: Context) -> Iterator[Finding]:
    m = ctx.deck.mesh
    if not m.blocks or not m.node_count:
        return
    used = np.unique(np.concatenate([b.connectivity.reshape(-1) for b in m.blocks]))
    unused = np.setdiff1d(m.node_labels, used)
    if unused.size:
        yield f"{unused.size} node(s) not used by any element (numgeo stops), e.g. {unused[:5].tolist()}"


@rule("NG-MESH-005", "error", "element types must exist and have a formulation")
def element_types(ctx: Context) -> Iterator[Finding]:
    for b in ctx.deck.mesh.blocks:
        try:
            spec = ctx.catalogue.element_type(b.type)
        except KeyError as e:
            yield str(e).strip("\"'")
            continue
        if not spec.usable:
            yield f"element type {b.type.lower()} has no formulation in numgeo (status {spec.status})"
        if b.connectivity.shape[1] != spec.nnodes:
            yield f"element type {b.type.lower()} needs {spec.nnodes} nodes, the block has {b.connectivity.shape[1]}"


@rule("NG-MESH-006", "error", "all element types must have the same dimension")
def mixed_dimension(ctx: Context) -> Iterator[Finding]:
    dims = set()
    for b in ctx.deck.mesh.blocks:
        try:
            dims.add(ctx.catalogue.element_type(b.type).ndim)
        except KeyError:
            continue
    if len(dims) > 1:
        yield f"element types of dimensions {sorted(dims)} are mixed (numgeo treats the whole model as 3D)"


@rule("NG-MESH-007", "error", "set members must exist")
def set_members(ctx: Context) -> Iterator[Finding]:
    m = ctx.deck.mesh
    nodes = set(m.node_labels.tolist())
    elems = set(m.element_labels.tolist())
    for s in m.nsets:
        if s.kind in ("list", "generate"):
            missing = set(s.members.tolist()) - nodes
            if missing:
                yield f"node set {s.name}: undefined nodes {sorted(missing)[:5]}"
            if not s.members.size:
                yield f"node set {s.name} is empty (numgeo stops)"
    for e in m.elsets:
        if e.kind in ("list", "generate"):
            missing = set(e.members.tolist()) - elems
            if missing:
                yield f"element set {e.name}: undefined elements {sorted(missing)[:5]}"
            if not e.members.size:
                yield f"element set {e.name} is empty (numgeo stops)"


@rule("NG-MESH-008", "error", "every element needs a material", source="src/database/database.f90:512-520")
def elements_without_material(ctx: Context) -> Iterator[Finding]:
    m = ctx.deck.mesh
    if not m.blocks:
        return
    assigned: set[int] = set()
    for s in ctx.deck.sections:
        try:
            es = m.elset(s.elset)
        except KeyError:
            continue
        if es.kind != "list" and es.kind != "generate":
            return  # query sets are evaluated by numgeo; cannot check here
        assigned |= set(es.members.tolist())
    missing = set(m.element_labels.tolist()) - assigned
    if missing:
        yield f"{len(missing)} element(s) have no material (*Solid section), e.g. {sorted(missing)[:5]}"


# ----------------------------------------------------------------------------- names
def _names(ctx: Context) -> Iterator[tuple[str, str]]:
    d = ctx.deck
    for ns in d.mesh.nsets:
        yield "node set", ns.name
    for es in d.mesh.elsets:
        yield "element set", es.name
    for sf in d.mesh.surfaces:
        yield "surface", sf.name
    for a in d.amplitudes:
        yield "amplitude", a.name
    for mt in d.materials:
        yield "material", mt.name
    for st in d.steps:
        yield "step", st.name


@rule("NG-NAME-002", "error", "names must be safe for numgeo's option matching")
def unsafe_names(ctx: Context) -> Iterator[Finding]:
    for kind, name in _names(ctx):
        k = _key(name)
        base = k.rsplit(".", 1)[-1]  # instance prefixes are written by numgeo itself
        words = [w for w in _RISKY_WORDS[kind] if w in base]
        if words:
            listed = ", ".join(w.lower() for w in words)
            yield f"{kind} name {name!r} contains {listed}, which numgeo reads as an option"
        if _FORBIDDEN_CHARS.search(name) or "**" in name:
            yield f"{kind} name {name!r} contains a character with a meaning in numgeo input (, = * $ quotes tab)"
        if " " in name:
            yield f"{kind} name {name!r} contains blanks; numgeo deletes them"
        if is_number(k) or k in ("INF", "INFINITY", "NAN") or k.startswith("NAN("):
            yield f"{kind} name {name!r} reads as a number"


@rule(
    "NG-NAME-005",
    "warning",
    "instance prefixes must not contain option words when the deck is written flat",
    source="src/input/read_set_.f90:123-152,178-193",
)
def unsafe_instance_prefix(ctx: Context) -> Iterator[Finding]:
    for kind, name in _names(ctx):
        k = _key(name)
        if "." not in k:
            continue
        prefix, base = k.rsplit(".", 1)
        words = [w for w in _RISKY_WORDS[kind] if w in prefix and w not in base]
        if words:
            listed = ", ".join(w.lower() for w in words)
            yield (
                f"{kind} {name!r}: its instance prefix contains {listed}. numgeo reads the original input, but "
                "pynumgeo writes parts and instances as one flat model, where the prefix is part of the name and "
                "is read as an option; deck.safe_names() renames such names before writing or running"
            )


@rule(
    "NG-NAME-003",
    "error",
    "names of one kind must be unique (case-insensitive)",
    source="src/input/read_input.f90:519-532",
)
def duplicate_names(ctx: Context) -> Iterator[Finding]:
    per_kind: dict[str, Counter[str]] = {}
    for kind, name in _names(ctx):
        if kind != "step":
            per_kind.setdefault(kind, Counter())[_key(name)] += 1
    for kind, c in per_kind.items():
        for n, k in c.items():
            if k > 1:
                yield f"{kind} {n} is defined {k} times (numgeo uses the first one)"
    if any(_key(a.name) == "DEFAULT" for a in ctx.deck.amplitudes):
        yield "the amplitude name DEFAULT is reserved by numgeo"


@rule("NG-NAME-004", "warning", "step names should be unique")
def duplicate_steps(ctx: Context) -> Iterator[Finding]:
    c = Counter(_key(s.name) for s in ctx.deck.steps)
    for n, k in c.items():
        if k > 1:
            yield f"step name {n} is used {k} times"


# ----------------------------------------------------------------------------- references
@rule(
    "NG-REF-001",
    "error",
    "material assignments must refer to existing element sets and materials",
    source="src/input/read_solid_section_.f90:93-154; src/input/read_input.f90:539-546",
)
def section_refs(ctx: Context) -> Iterator[Finding]:
    d = ctx.deck
    elsets = {e.key for e in d.mesh.elsets}
    mats = {_key(m.name) for m in d.materials}
    for i, s in enumerate(d.sections):
        if _key(s.elset) not in elsets:
            yield (f"element set {s.elset!r} is not defined", f"sections[{i}]")
        if _key(s.material) not in mats:
            yield (f"material {s.material!r} is not defined", f"sections[{i}]")


_SET_FIRST_KEYWORDS = {
    "*BOUNDARY": "node",
    "*CLOAD": "node",
    "*BODYFORCE": "element",
    "*DLOAD": "element",
    "*DSLOAD": "surface",
    "*UBOUNDARY": "node",
}


@rule("NG-REF-002", "error", "step keywords must refer to existing sets, surfaces and amplitudes")
def step_refs(ctx: Context) -> Iterator[Finding]:
    d = ctx.deck
    nsets = {s.key for s in d.mesh.nsets}
    elsets = {s.key for s in d.mesh.elsets}
    surfs = {s.key for s in d.mesh.surfaces}
    ampl = {_key(a.name) for a in d.amplitudes} | {"DEFAULT"}
    for si, st in enumerate(d.steps):
        for ki, kw in enumerate(st.items):
            loc = f"steps[{si}].items[{ki}] {kw.keyword}"
            a = kw.option("AMPLITUDE")
            if a is not None and _key(a) not in ampl:
                yield (f"amplitude {a!r} is not defined", loc)
            kind = _SET_FIRST_KEYWORDS.get(kw.keyword)
            if kind is None:
                continue
            names = {"node": nsets, "element": elsets, "surface": surfs}[kind]
            for row in kw.data:
                if row and isinstance(row[0], str) and _key(row[0]) not in names:
                    yield (f"{kind} set {row[0]!r} is not defined", loc)


# ----------------------------------------------------------------------------- materials
@rule(
    "NG-MAT-001",
    "error",
    "*Mechanical needs a known model with exactly the library's number of parameters",
    source="src/input/read_material_.f90:258-266,512-517",
)
def mechanical(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        mech = [p for p in m.properties if p.keyword == "*MECHANICAL"]
        if len(mech) > 1:
            yield (f"material {m.name}: more than one *Mechanical", f"material {m.name}")
        for p in mech[:1]:
            model = (p.value or "").upper()
            if model in ("USER", "USER_UNSAT"):
                continue
            try:
                spec = ctx.catalogue.material_model(model)
            except KeyError as e:
                if ctx.catalogue.is_private_name(model):
                    continue  # reported by NG-MAT-003
                yield (str(e).strip("\"'"), f"material {m.name}")
                continue
            n = sum(len(r) for r in p.data)
            if spec.nprops is not None and n != spec.nprops:
                yield (
                    f"material {m.name}: {spec.name.lower()} needs {spec.nprops} parameters, {n} given",
                    f"material {m.name}",
                )
            if ctx.profile.public and not spec.public:
                yield (
                    f"material {m.name}: {spec.name.lower()} is not available in public builds",
                    f"material {m.name}",
                )


@rule("NG-MAT-003", "warning", "model not described in the public catalogue")
def private_model(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        p = m.property("*Mechanical")
        if p is not None and p.value and ctx.catalogue.is_private_name(p.value):
            try:
                ctx.catalogue.material_model(p.value)
            except KeyError:
                yield (
                    f"material {m.name}: {p.value} exists in numgeo but is not described in the public pynumgeo "
                    "catalogue; its parameters are not checked (PYNUMGEO_CATALOGUE can point to a full catalogue)",
                    f"material {m.name}",
                )


@rule("NG-MAT-002", "error", "a material needs *Density", source="src/input/read_material_.f90")
def density(ctx: Context) -> Iterator[Finding]:
    for m in ctx.deck.materials:
        if m.property("*Density") is None and m.property("*Mechanical") is not None:
            yield (f"material {m.name} has no *Density", f"material {m.name}")


def _bingham(ctx: Context) -> Iterator[tuple[Material, float | None, float | None]]:
    """(material, tau_y, eta) of every material with *Mechanical=bingham (None where not a number)."""
    for m in ctx.deck.materials:
        p = m.property("*Mechanical")
        if p is None or (p.value or "").upper().replace(" ", "") != "BINGHAM":
            continue
        vals = [t for r in p.data for t in r]
        num = [float(t) if isinstance(t, int | float) and not isinstance(t, bool) else None for t in vals]
        yield m, num[2] if len(num) > 2 else None, num[3] if len(num) > 3 else None


@rule(
    "NG-MAT-010",
    "warning",
    "negative Bingham yield stress or viscosity is used as zero",
    source="src/materials/models/material_bingham_.f90:70-71",
)
def bingham_negative(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo rejects negative values itself.
    for m, tau_y, eta in _bingham(ctx):
        for name, v in (("tau_y", tau_y), ("eta", eta)):
            if v is not None and v < 0:
                yield (f"material {m.name}: bingham {name} = {v:g} < 0; numgeo uses 0", f"material {m.name}")


@rule(
    "NG-MAT-011",
    "error",
    "a Bingham material needs a yield stress or a viscosity",
    source="src/materials/models/material_bingham_.f90:70-71,97,106-108; docs/reference/material/mechanical/bingham.md",
)
def bingham_no_shear(ctx: Context) -> Iterator[Finding]:
    # TODO: drop when numgeo rejects tau_y = eta = 0 itself.
    for m, tau_y, eta in _bingham(ctx):
        if tau_y is not None and eta is not None and tau_y <= 0 and eta <= 0:
            yield (
                f"material {m.name}: bingham with tau_y = eta = 0 has no deviatoric stiffness once it flows "
                "(not admissible; numgeo does not check it)",
                f"material {m.name}",
            )


# ----------------------------------------------------------------------------- steps
_PROCEDURE_DATA = {
    "*STATIC": (4,),
    "*TRANSIENT": (4,),
    "*TRANSIENT-CRITICAL": (4,),
    "*REDUCTION": (4,),
    "*DYNAMIC": (4,),
    "*EXPLICITDYNAMIC": (2, 4),
    "*EXPLICITDYNAMICS": (2, 4),
    "*GEOSTATIC": (0,),
}


@rule(
    "NG-STEP-010",
    "error",
    "the procedure line needs its time data",
    source="src/input/read_step_.f90:364-623",
)
def procedure_data(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        p = st.procedure
        allowed = _PROCEDURE_DATA.get(p.keyword)
        if allowed is None:
            yield (f"step {st.name}: {p.keyword} is not a procedure", f"step {st.name}")
            continue
        n = len(p.data[0]) if p.data else 0
        if n not in allowed or len(p.data) > 1:
            yield (
                f"step {st.name}: {p.keyword} needs one data line with {' or '.join(map(str, allowed))} values",
                f"step {st.name}",
            )
        if p.keyword == "*DYNAMIC" and not any(
            c.keyword in ("*HHT", "*HILBER-HUGHES-TAYLOR", "*BWE", "*BACKWARDEULER") for c in p.children
        ):
            yield (
                f"step {st.name}: *Dynamic needs an integrator line (*Hilber-Hughes-Taylor or *Backward euler)",
                f"step {st.name}",
            )


@rule(
    "NG-STEP-011",
    "error",
    "field output must name its format (vtk or gid)",
    source="src/input/read_step_.f90:1772-1776",
)
def field_output_format(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        for kw in st.keywords("*Output"):
            keys = {k for k, _ in kw.options}
            if "FIELD" in keys and not keys & {"VTK", "GID"}:
                yield (f"step {st.name}: *Output, field without vtk or gid writes nothing", f"step {st.name}")


@rule(
    "NG-STEP-012",
    "warning",
    "the increment limit must allow the step to finish",
    source="src/fem/fem_global_.f90 (increment loop ends silently)",
)
def increments(ctx: Context) -> Iterator[Finding]:
    for st in ctx.deck.steps:
        p = st.procedure
        if p.keyword in ("*STATIC", "*TRANSIENT", "*DYNAMIC") and p.data and len(p.data[0]) == 4:
            try:
                _dt0, t_end, _dtmin, dtmax = (float(x) for x in p.data[0])
            except (TypeError, ValueError):
                continue
            inc = st.inc if st.inc is not None else 1_000_000
            if dtmax > 0 and t_end / dtmax > inc:
                yield (
                    f"step {st.name}: inc={inc} cannot reach t_end={t_end} with dtmax={dtmax}; numgeo ends the step "
                    "silently when the increments are used up",
                    f"step {st.name}",
                )


@rule("NG-STEP-013", "error", "step names must be given", source="src/input/read_step_.f90:273-280")
def step_names(ctx: Context) -> Iterator[Finding]:
    for i, st in enumerate(ctx.deck.steps):
        if not st.name:
            yield (f"step {i + 1} has no name", f"steps[{i}]")


def _walk(kws: list[Keyword]) -> Iterator[Keyword]:
    for k in kws:
        yield k
        yield from _walk(k.children)
