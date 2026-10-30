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
"""Catalogue-driven checks of every generic keyword of a deck.

Every :class:`~pynumgeo.deck.keyword.Keyword` of a deck is visited in its context: model keywords,
material sub-keywords, the procedure of a step and its integrator line, step keywords, the cards of an
``*Output`` block, ``*Normal`` / ``*Friction`` after ``*Interaction`` and ``*Penalty`` after
``*Equation``. Each is checked the way numgeo dispatches it:

* the keyword exists in this context (``NG-KW-001``) and its line has a form numgeo's ``select case``
  accepts (``NG-KW-002``: e.g. ``*Density, x`` or ``*Termination, x`` are not keywords for numgeo);
* sub-keywords that numgeo only reads at one position are at that position (``NG-KW-003``);
* options are known for the keyword, with numgeo's matching (substring or exact token): unknown
  options that numgeo rejects are errors (``NG-KW-010``), unknown options it ignores are warnings
  (``NG-KW-011``); required options are present (``NG-KW-012``); enumerated values are valid
  (``NG-KW-013``); integer and real option values are numbers (``NG-KW-014``);
* data lines have the field count of the catalogue's count rule and numbers where numbers are read
  (``NG-KW-020``); data lines on keywords that read none are reported (``NG-KW-020`` / ``NG-KW-021``).

The option names, enumerated values, count rules and field types come from the catalogue; how a keyword
matches its options (``_OPTION_POLICY``) and which count rules are machine-checkable are taken from the
reader routines cited in each entry. Keywords with option or data semantics that depend on other options
(``*Boundary``, ``*Solver``, ``*Controls``, ``*Initial conditions``, ...) are left to the specific rules
in :mod:`pynumgeo.validation.rules.behaviour`.

Examples:
    >>> from pynumgeo.io.reader import parse_text
    >>> from pynumgeo.validation import validate
    >>> text = "*Material, name=M\\n*Mechanical=linear_elasticity\\n1e4, 0.3\\n*Density, solid\\n2.0\\n"
    >>> deck = parse_text(text).deck
    >>> [i.id for i in validate(deck, select=["NG-KW-002"])]
    ['NG-KW-002']
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from pynumgeo import catalogue as _cat
from pynumgeo.catalogue import KeywordSpec
from pynumgeo.deck.deck import Deck, Material, Step
from pynumgeo.deck.keyword import Keyword, Token
from pynumgeo.io.numbers import is_number
from pynumgeo.validation.engine import Context, Finding, rule

__all__ = [
    "Site",
    "display",
    "is_int_token",
    "is_real_token",
    "line_text",
    "output_type",
    "sites",
    "spec_for",
]

# ----------------------------------------------------------------------------- walking a deck
#: Catalogue contexts and parent keyword of each site context.
_CTX: dict[str, tuple[tuple[str, ...], str | None]] = {
    "model": (("model",), None),
    "material": (("material",), None),
    "step": (("step",), None),
    "procedure": (("step-procedure",), "*STEP"),
    "dynamic": (("step-procedure",), "*DYNAMIC"),
    "explicit": (("step-procedure",), "*EXPLICITDYNAMIC"),
    "output-field": (("output-field", "output"), None),
    "output-print": (("output-print", "output"), None),
    "output-user": (("output-user", "output"), None),
    "interaction": (("interaction sub-keyword",), None),
    "equation": ((), None),
}
_CTX_WORDS = {
    "model": "the model section",
    "material": "a *Material block",
    "step": "a *Step",
    "procedure": "the procedure line of a *Step",
    "dynamic": "the line after the *Dynamic data line",
    "explicit": "the line after the *Explicit dynamic data line",
    "output-field": "*Output, field",
    "output-print": "*Output, print",
    "output-user": "*Output, user",
    "interaction": "an *Interaction block",
    "equation": "an *Equation block",
}


@dataclass(frozen=True)
class Site:
    """A keyword in its context.

    Attributes:
        kw: the keyword.
        ctx: ``model``, ``material``, ``step``, ``procedure``, ``dynamic``, ``explicit``, ``output-field``,
            ``output-print``, ``output-user``, ``interaction`` or ``equation``.
        path: object path in the deck, e.g. ``steps[0].items[3]``.
        parent: the keyword this one belongs to (``*Output``, ``*Interaction``, the procedure, ...).
        material: the material of a material sub-keyword.
        step: the step of a step keyword.
        index: position among its siblings.
        siblings: all keywords of the same container, in order.
    """

    kw: Keyword
    ctx: str
    path: str
    parent: Keyword | None = None
    material: Material | None = None
    step: Step | None = None
    index: int = 0
    siblings: tuple[Keyword, ...] = ()

    @property
    def loc(self) -> str:
        """Source position if known, else the object path."""
        return self.kw.source or self.path

    @property
    def where(self) -> str:
        """Human-readable owner, e.g. ``material Soil`` or ``step Load``."""
        if self.material is not None:
            return f"material {self.material.name}"
        if self.step is not None:
            return f"step {self.step.name}"
        return "model"

    @property
    def previous(self) -> Keyword | None:
        """The sibling directly before this keyword."""
        return self.siblings[self.index - 1] if self.index > 0 else None

    @property
    def next(self) -> Keyword | None:
        """The sibling directly after this keyword."""
        return self.siblings[self.index + 1] if self.index + 1 < len(self.siblings) else None


def output_type(kw: Keyword) -> str:
    """Type of an ``*Output`` block as numgeo decides it: substring FIELD, then PRINT, then USER.

    ``src/input/read_step_.f90:1742,1925,2192`` (``index(..., back=.true.)`` on the option text).

    >>> output_type(Keyword.make("*Output", options=["print"]))
    'print'
    """
    text = _option_text(kw)
    for t in ("FIELD", "PRINT", "USER"):
        if t in text:
            return t.lower()
    return ""


def _children(kw: Keyword, ctx: str, path: str, base: Site) -> Iterator[Site]:
    if not kw.children:
        return
    if kw.keyword == "*OUTPUT":
        child_ctx = "output-" + (output_type(kw) or "field")
    elif kw.keyword == "*INTERACTION":
        child_ctx = "interaction"
    elif kw.keyword == "*DYNAMIC":
        child_ctx = "dynamic"
    elif kw.keyword in ("*EXPLICITDYNAMIC", "*EXPLICITDYNAMICS"):
        child_ctx = "explicit"
    elif kw.keyword in ("*EQUATION", "*RIGIDBODY"):
        child_ctx = "equation"
    else:
        child_ctx = ctx
    sib = tuple(kw.children)
    for i, c in enumerate(sib):
        s = Site(c, child_ctx, f"{path}.children[{i}]", kw, base.material, base.step, i, sib)
        yield s
        yield from _children(c, child_ctx, s.path, s)


def sites(deck: Deck) -> Iterator[Site]:
    """Every generic keyword of ``deck`` with its context, depth first, in deck order."""
    sib = tuple(deck.keywords)
    for i, kw in enumerate(sib):
        s = Site(kw, "model", f"keywords[{i}]", index=i, siblings=sib)
        yield s
        yield from _children(kw, "model", s.path, s)
    for mi, m in enumerate(deck.materials):
        sib = tuple(m.properties)
        for i, kw in enumerate(sib):
            s = Site(kw, "material", f"materials[{mi}].properties[{i}]", material=m, index=i, siblings=sib)
            yield s
            yield from _children(kw, "material", s.path, s)
    for si, st in enumerate(deck.steps):
        p = Site(st.procedure, "procedure", f"steps[{si}].procedure", step=st, siblings=(st.procedure,))
        yield p
        yield from _children(st.procedure, "procedure", p.path, p)
        sib = tuple(st.items)
        for i, kw in enumerate(sib):
            s = Site(kw, "step", f"steps[{si}].items[{i}]", step=st, index=i, siblings=sib)
            yield s
            yield from _children(kw, "step", s.path, s)


# ----------------------------------------------------------------------------- catalogue lookups
_QUOTED = re.compile(r"'(\*[A-Z0-9_\-]+)")
_LEAD = re.compile(r"^(\*[A-Z0-9_\-]+)")


@dataclass(frozen=True)
class _Forms:
    """Keyword-line forms numgeo's dispatch accepts for one catalogue entry."""

    literal: frozenset[str]  # complete heads, e.g. '*NSET,' or '*TRUSSPROPERTIES,TENSION-ONLY'
    prefixes: frozenset[str]  # '<ignored>' remainders: any text after the prefix
    substring: bool  # descriptive form: recognised by substring, any form accepted


def _parse_forms(spec: KeywordSpec) -> _Forms:
    lit: set[str] = set()
    pre: set[str] = set()
    sub = False
    for f in spec.match_forms:
        if "(dead" in f:
            continue
        if "'" in f or " " in f:
            sub = True
            continue
        if f.startswith("<either>"):
            pre.add(spec.keyword + f[len("<either>") :].replace("<ignored>", ""))
            continue
        if f.endswith("<ignored>"):
            pre.add(f[: -len("<ignored>")])
            continue
        lit.add(f)
    return _Forms(frozenset(lit), frozenset(pre), sub)


class _Index:
    """Keyword names and aliases (``*HHT``, ``*BWE``, ``*LINESEARCH``, ``*NODEOUTPUT``, ...) to entries."""

    def __init__(self, cat: _cat.Catalogue) -> None:
        self.by_name: dict[str, list[KeywordSpec]] = {}
        self.forms: dict[int, _Forms] = {}
        for spec in cat.keywords:
            names = {spec.keyword}
            for f in spec.match_forms:
                if "(dead" in f:
                    continue
                if "'" in f or " " in f:
                    names.update(_QUOTED.findall(f))
                else:
                    m = _LEAD.match(f)
                    if m:
                        names.add(m.group(1))
            for n in names:
                self.by_name.setdefault(n, []).append(spec)
            self.forms[id(spec)] = _parse_forms(spec)


_INDEXES: dict[int, tuple[_cat.Catalogue, _Index]] = {}


def _idx(cat: _cat.Catalogue) -> _Index:
    entry = _INDEXES.get(id(cat))
    if entry is None or entry[0] is not cat:
        entry = (cat, _Index(cat))
        _INDEXES[id(cat)] = entry
    return entry[1]


def spec_for(cat: _cat.Catalogue, kw: Keyword, ctx: str) -> KeywordSpec | None:
    """Catalogue entry of ``kw`` in site context ``ctx`` (aliases included); ``None`` if unknown there."""
    contexts, parent = _CTX[ctx]
    for spec in _idx(cat).by_name.get(kw.keyword, ()):
        if any(c in spec.contexts for c in contexts) and (parent is None or spec.parent == parent):
            return spec
    return None


# Spellings of aliases the catalogue lists only as match forms.
_ALIAS_DISPLAY = {
    "*NODEOUTPUT": "*Node output",
    "*ELEMENTOUTPUT": "*Element output",
    "*HHT": "*HHT",
    "*BWE": "*BWE",
    "*LINESEARCH": "*Line search",
    "*SOLIDSECTION": "*Solid section",
    "*EXPLICITDYNAMICS": "*Explicit dynamics",
    "*PENALTY": "*Penalty",
}


def display(cat: _cat.Catalogue, keyword: str) -> str:
    """Normal-case spelling of a keyword (catalogue ``display``), e.g. ``*Initial conditions``.

    >>> display(_cat.load(), "*NODEOUTPUT"), display(_cat.load(), "*INITIALCONDITIONS")
    ('*Node output', '*Initial conditions')
    """
    if keyword in _ALIAS_DISPLAY:
        return _ALIAS_DISPLAY[keyword]
    specs = _idx(cat).by_name.get(keyword)
    if specs and specs[0].keyword == keyword:
        return specs[0].display
    return keyword[:2] + keyword[2:].lower() if keyword.startswith("*") else keyword


# ----------------------------------------------------------------------------- text helpers
def _norm(v: str | None) -> str:
    return "" if v is None else v.upper().replace(" ", "").replace("\t", "")


def _token(k: str, v: str | None) -> str:
    return k if v is None else f"{k}={_norm(v)}"


def _option_text(kw: Keyword) -> str:
    """The option text numgeo searches (after the first comma), upper case, blanks removed."""
    return ",".join(_token(k, v) for k, v in kw.options)


def line_text(kw: Keyword) -> str:
    """The keyword line as numgeo sees it after preprocessing (upper case, no blanks).

    >>> line_text(Keyword.make("*Hydraulic", value="vanGenuchten", options=[("swr", 0.1)]))
    '*HYDRAULIC=VANGENUCHTEN,SWR=0.1'
    """
    head = kw.keyword + ("" if kw.value is None else "=" + _norm(kw.value))
    opts = _option_text(kw)
    return head + ("," + opts if kw.options else "")


def _head(kw: Keyword, ctx: str) -> str:
    """The part of the keyword line numgeo's ``select case`` compares, per reader."""
    line = line_text(kw)
    if ctx == "material":  # src/input/read_material_.f90:165-178
        eq, comma = line.find("="), line.find(",")
        if eq >= 0:
            return line[: comma + 1] if 0 <= comma < eq else line[: eq + 1]
        return line
    comma = line.find(",")
    head = line[: comma + 1] if comma >= 0 else line
    if ctx == "procedure":  # src/input/read_step_.f90:357-359: commas deleted
        head = head.replace(",", "")
    return head


def is_real_token(t: Token) -> bool:
    """True if numgeo's list-directed read of a real accepts the token."""
    return not isinstance(t, str) or (t != "" and is_number(t))


def is_int_token(t: Token) -> bool:
    """True if numgeo's list-directed read of an integer accepts the token."""
    if isinstance(t, bool):
        return False
    if isinstance(t, int):
        return True
    return isinstance(t, str) and re.fullmatch(r"\s*[+-]?\d+\s*", t) is not None


def _bare(name: str) -> str:
    """Catalogue option name without descriptors: ``'TYPE (method)'`` -> ``'TYPE'``."""
    return re.sub(r"\s*\(.*\)\s*$", "", name).strip().upper().replace(" ", "")


def _values(values: Sequence[str]) -> set[str] | None:
    out = set()
    for v in values:
        if v.lower().startswith("see "):
            return None
        out.add(_bare(v))
    return out or None


# ----------------------------------------------------------------------------- NG-KW-001 / 002
_SOURCES_DISPATCH = (
    "src/input/read_input.f90:487-497 (model); src/input/read_step_.f90:3160-3165 (step); "
    "src/input/read_material_.f90:1867-1870 (material); src/input/read_step_.f90:626-628 (procedure)"
)


@rule("NG-KW-001", "error", "the keyword must exist in its context", source=_SOURCES_DISPATCH)
def unknown_keyword(ctx: Context) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        if s.ctx == "equation":
            if s.kw.keyword != "*PENALTY":
                parent = display(cat, s.parent.keyword) if s.parent is not None else "*Equation"
                yield (
                    f"{s.where}: {display(cat, s.kw.keyword)} is not read after {parent} (only "
                    "*Penalty=<factor>); numgeo stops with 'invalid input statement'",
                    s.loc,
                )
            continue
        if spec_for(cat, s.kw, s.ctx) is not None:
            continue
        other = sorted({c for spec in _idx(cat).by_name.get(s.kw.keyword, ()) for c in spec.contexts})
        name = display(cat, s.kw.keyword)
        if other:
            yield (
                f"{s.where}: {name} is not read in {_CTX_WORDS[s.ctx]} (it belongs to: {', '.join(other)}); "
                "numgeo stops with 'invalid input statement'",
                s.loc,
            )
        else:
            yield (
                f"{s.where}: unknown keyword {name}; numgeo stops with 'invalid input statement'; "
                f"did you mean {cat.suggest(s.kw.keyword)}?",
                s.loc,
            )


# Keywords whose form is reported by a specific rule.
_FORM_ELSEWHERE = frozenset({"*TERMINATION"})


@rule("NG-KW-002", "error", "the keyword line must have a form numgeo accepts", source=_SOURCES_DISPATCH)
def keyword_form(ctx: Context) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        if s.ctx in ("dynamic", "explicit", "interaction", "equation") or s.kw.keyword in _FORM_ELSEWHERE:
            continue  # recognised by substring
        spec = spec_for(cat, s.kw, s.ctx)
        if spec is None:
            continue
        forms = _idx(cat).forms[id(spec)]
        if forms.substring or not (forms.literal or forms.prefixes):
            continue
        head = _head(s.kw, s.ctx)
        if s.ctx == "procedure":
            ok = head in {f.replace(",", "") for f in forms.literal | forms.prefixes} or head in {
                f.split(",")[0] for f in forms.literal
            }
        else:
            ok = head in forms.literal or any(head.startswith(p) for p in forms.prefixes)
        if not ok:
            accepted = sorted(forms.literal | {p + "..." for p in forms.prefixes})
            yield (
                f"{s.where}: numgeo reads the keyword as {head!r}, which it does not accept (accepted: "
                f"{', '.join(accepted)}); src {_src(spec.raw.get('handler'))}",
                s.loc,
            )


def _src(d: object) -> str:
    if isinstance(d, dict) and d.get("file"):
        return f"{d['file']}:{d.get('line')}"
    return "-"


# ----------------------------------------------------------------------------- NG-KW-003 placement
@rule(
    "NG-KW-003",
    "error",
    "sub-keywords that numgeo reads at one position only must stand there",
    source="src/input/read_material_.f90:285-287,416,715-729,794-807; src/input/read_step_.f90:546-561,"
    "586-622,1820-1837; src/input/read_equation_.f90:77-92; src/input/read_interaction_.f90:180-330",
)
def placement(ctx: Context) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        k, prev = s.kw.keyword, s.previous
        pk = prev.keyword if prev is not None else ""
        if s.ctx == "material":
            if k == "*USERPROPERTIES" and not (
                pk == "*MECHANICAL" and _norm(prev.value if prev else "") in ("USER", "USER_UNSAT")
            ):
                yield (
                    f"{s.where}: *User properties is read only on the line directly after *Mechanical=user "
                    "or *Mechanical=user_unsat; elsewhere it ends the material block and numgeo stops",
                    s.loc,
                )
            if k == "*MECHANICAL" and _norm(s.kw.value) in ("USER", "USER_UNSAT"):
                nxt = s.next
                if nxt is None or nxt.keyword != "*USERPROPERTIES":
                    yield (
                        f"{s.where}: *Mechanical={_norm(s.kw.value).lower()} must be followed directly by "
                        "*User properties, props=<n>, statev=<m> (src/input/read_material_.f90:325-376)",
                        s.loc,
                    )
            if k == "*JACOBIAN" and pk not in ("*HYDRAULIC", "*RELATIVEPERMEABILITY"):
                yield (
                    f"{s.where}: *Jacobian is read only directly after the data of *Hydraulic or *Relative "
                    "permeability; elsewhere it ends the material block and numgeo stops",
                    s.loc,
                )
        elif s.ctx in ("dynamic", "explicit", "equation") and s.index > 0:
            what = {
                "dynamic": "time-integrator line",
                "explicit": "*Mass scaling line",
                "equation": "*Penalty line",
            }
            yield (
                f"{s.where}: only one {what[s.ctx]} is read after "
                f"{display(cat, s.parent.keyword if s.parent else '')};"
                f" numgeo reads {display(cat, k)} as a step keyword and stops",
                s.loc,
            )
        elif s.ctx == "interaction":
            if k == "*NORMAL" and any(x.keyword == "*FRICTION" for x in s.siblings[: s.index]):
                yield (
                    f"{s.where}: *Normal after *Friction: numgeo leaves the *Interaction block after "
                    "*Friction and stops at *Normal",
                    s.loc,
                )
            if k in ("*NORMAL", "*FRICTION") and any(x.keyword == k for x in s.siblings[: s.index]):
                yield (f"{s.where}: second {display(cat, k)} in one *Interaction block; numgeo stops", s.loc)
        elif s.ctx.startswith("output-") and k == "*FREQUENCY" and pk == "*FREQUENCY":
            yield (
                f"{s.where}: two consecutive *Frequency lines; the second ends the *Output block and numgeo "
                "stops (src/input/read_step_.f90:1826-1905)",
                s.loc,
            )


# ----------------------------------------------------------------------------- options
@dataclass(frozen=True)
class _Policy:
    """How numgeo reads the options of one keyword.

    ``match``: ``substring`` (a token is recognised if it contains a known name), ``exact`` (the key before
    ``=`` must equal a known name), ``ignored`` (options are never read). ``unknown``: what numgeo does
    with an unrecognised option (``error`` / ``warning`` = silently ignored / ``None`` = not checked here).
    ``one_of``: at least one of these options is required; ``exactly_one``: the keyword takes exactly one
    option. ``names``: replaces the catalogue's option names (for descriptive entries).
    """

    match: str
    unknown: str | None
    source: str
    one_of: tuple[str, ...] = ()
    exactly_one: bool = False
    names: tuple[str, ...] = ()
    strip: tuple[str, ...] = ()  # options cut out before the others are evaluated (``SIDE=``)


_LOAD_OPTIONS = ("INSTANT", "RAMP", "AMPLITUDE")
# Substrings read_normal_contact_setting recognises (src/input/read_interaction_.f90:425-512).
_NORMAL_WORDS = (
    "NAME",
    "NORMAL",
    "MECHANICAL",
    "NOSEPARATION",
    "USER",
    "STIFFNESS_FACTOR",
    "NONCONSTANT",
    "VISCOUS",
    "WATER-FILLEDGAP",
    "WATERFILLEDGAP",
)
# Substrings read_contact_pairing recognises (src/input/read_contact_pairing_.f90:80-154).
_PAIR_WORDS = (
    "INTERACTION",
    "DISCRETISATION=ELEMENTMORTAR",
    "DISCRETISATION=NTS",
    "DISCRETISATION=IPS",
    "DISCRETISATION=INTEGRATION-POINT-SURFACE",
    "DISCRETISATION=SEGMENTMORTAR",
    "DISCRETISATION=NTN",
    "ADJUST",
    "PERTURBATION",
    "REFINE",
    "GENERAL",
    "NIGP",
    "NGP",
    "NLGEOM",
    "DOUBLEPASS",
    "SLIDING=SMALL",
    "SLIDING=FINITE",
    "GAP=ACTIVATION",
    "GAP=MESH",
)
_OPTION_POLICY: dict[tuple[str, str], _Policy] = {
    ("step", "*BODYFORCE"): _Policy("exact", "error", "src/input/read_bodyforce_.f90:78-125", _LOAD_OPTIONS, True),
    ("step", "*CLOAD"): _Policy("exact", "error", "src/input/read_cload_ .f90:86-133", _LOAD_OPTIONS, True),
    ("step", "*MASSPOINT"): _Policy("exact", "error", "src/input/read_mass_point_.f90:77-126", _LOAD_OPTIONS, True),
    ("step", "*REACTIONFORCE"): _Policy(
        "exact", "error", "src/input/read_apply_reaction_force.f90:80-128", _LOAD_OPTIONS, True
    ),
    ("step", "*DLOAD"): _Policy(
        "exact", "error", "src/input/read_dload_.f90:111-233", (*_LOAD_OPTIONS, "USER"), True, strip=("SIDE",)
    ),
    ("step", "*DSLOAD"): _Policy(
        "exact", "error", "src/input/read_dload_.f90:111-233", (*_LOAD_OPTIONS, "USER"), True, strip=("SIDE",)
    ),
    ("step", "*MODIFY"): _Policy("exact", "error", "src/input/read_modify_.f90:83-111", ("AMPLITUDE",), True),
    ("step", "*CONTACTPENALTY"): _Policy("substring", "warning", "src/input/read_penalty_factor_.f90:86-112"),
    ("step", "*OUTPUT"): _Policy(
        "substring", "warning", "src/input/read_step_.f90:1742,1925,2192", ("FIELD", "PRINT", "USER")
    ),
    ("step", "*MODELCHANGE"): _Policy(
        "substring",
        "warning",
        "src/input/read_model_change_.f90:82,136,221,333-338",
        ("MATERIAL", "FRICTION", "REMOVE", "ADD"),
    ),
    ("step", "*EQUATION"): _Policy("substring", "warning", "src/input/read_equation_.f90:46-120"),
    ("step", "*EXECUTECOMMAND"): _Policy("substring", "warning", "src/input/read_step_.f90:3296-3330"),
    ("step", "*READSTATE"): _Policy("substring", "warning", "src/input/read_step_.f90:3252-3290"),
    ("step", "*NON-LOCAL"): _Policy("substring", "warning", "src/input/read_step_.f90:3463-3500"),
    ("step", "*SUBMODEL"): _Policy("substring", "warning", "src/input/read_step_.f90:3340-3440"),
    ("step", "*TIMEINTEGRATION"): _Policy("substring", "warning", "src/input/read_step_.f90:3049-3089"),
    ("step", "*RIGIDBODY"): _Policy("substring", "warning", "src/input/read_equation_.f90:276-310"),
    ("step", "*PFEMWRITE"): _Policy("substring", "warning", "src/input/read_step_.f90:2974-3040"),
    ("step", "*ROBIN"): _Policy("substring", "warning", "src/input/read_robin_.f90:60-80"),
    ("step", "*BOUNDARY-FLEXIBLE"): _Policy("substring", "warning", "src/input/read_flexible_bc_.f90:60-80"),
    ("step", "*CONNECTORELEMENT"): _Policy("ignored", "warning", "src/input/read_connector_element_.f90:72"),
    ("step", "*SAVEREACTIONFORCE"): _Policy("ignored", "warning", "src/input/read_save_reaction_force_.f90:80-108"),
    ("step", "*NODALDYNAMICFORCE"): _Policy("ignored", "warning", "src/input/read_dynforce_.f90:41-75"),
    ("step", "*RESET"): _Policy("ignored", "warning", "src/input/read_step_.f90:2929-2950"),
    ("model", "*INTERACTION"): _Policy(
        "substring", "error", "src/input/read_interaction_.f90:425-529", names=_NORMAL_WORDS
    ),
    ("model", "*CONTACTPAIR"): _Policy(
        "substring", "error", "src/input/read_contact_pairing_.f90:80-198", names=_PAIR_WORDS
    ),
    ("interaction", "*NORMAL"): _Policy(
        "substring", "error", "src/input/read_interaction_.f90:425-529", names=_NORMAL_WORDS
    ),
    ("interaction", "*FRICTION"): _Policy("substring", "error", "src/input/read_interaction_.f90:314-319"),
    ("output-field", "*NODE"): _Policy("exact", "error", "src/input/read_step_.f90:3700-3780"),
    ("output-field", "*ELEMENT"): _Policy("exact", "error", "src/input/read_step_.f90:3791-3860"),
    # print and user cards: nset=/elset= are required options of the catalogue (NG-KW-012)
    ("output-print", "*NODE"): _Policy("exact", "error", "src/input/read_step_.f90:1966-2054"),
    ("output-print", "*ELEMENT"): _Policy("exact", "error", "src/input/read_step_.f90:2061-2112"),
    ("output-print", "*INTEGRATIONPOINT"): _Policy("exact", "error", "src/input/read_step_.f90:2115-2168"),
    ("output-user", "*NODE"): _Policy("exact", "error", "src/input/read_step_.f90:2217-2270"),
    ("output-user", "*ELEMENT"): _Policy("exact", "error", "src/input/read_step_.f90:2272-2325"),
    ("procedure", "*DYNAMIC"): _Policy("exact", "warning", "src/input/read_step_.f90:570-573"),
    ("material", "*HOURGLASS"): _Policy(
        "substring", None, "src/input/read_material_.f90:1611-1621", ("STIFFNESS", "SCALING")
    ),
}
for _p in ("*STATIC", "*TRANSIENT", "*TRANSIENT-CRITICAL", "*REDUCTION", "*GEOSTATIC", "*EXPLICITDYNAMIC"):
    _OPTION_POLICY[("procedure", _p)] = _Policy("ignored", "warning", "src/input/read_step_.f90:357-359")


def _policy(site: Site, spec: KeywordSpec) -> _Policy | None:
    return _OPTION_POLICY.get((site.ctx, spec.keyword))


def _known_names(spec: KeywordSpec, pol: _Policy) -> list[str]:
    if pol.names:
        return list(pol.names)
    out = []
    for o in spec.options:
        n = _bare(o.name)
        if n and not n.startswith("<") and not n.startswith("VALUE"):
            out.append(n)
    return out


def _recognised(key: str, val: str | None, names: Sequence[str], match: str) -> str | None:
    """Catalogue option name numgeo recognises in this option, or ``None``."""
    tok = _token(key, val)
    if match == "exact":
        return key if key in names else None
    for n in names:
        if n in tok:
            return n
    return None


def _options_of(site: Site, pol: _Policy) -> list[tuple[str, str | None]]:
    return [(k, v) for k, v in site.kw.options if not any(k.startswith(x) for x in pol.strip)]


def _option_findings(ctx: Context, severity: str) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        spec = spec_for(cat, s.kw, s.ctx)
        if spec is None:
            continue
        pol = _policy(s, spec)
        if pol is None or pol.unknown != severity:
            continue
        name = display(cat, s.kw.keyword)
        opts = _options_of(s, pol)
        if pol.match == "ignored":
            for k, v in opts:
                yield (
                    f"{s.where}: option {_token(k, v).lower()!r} of {name} is ignored by numgeo ({pol.source})",
                    s.loc,
                )
            continue
        names = _known_names(spec, pol)
        for k, v in opts:
            if _recognised(k, v, names, pol.match) is None:
                what = "numgeo stops" if severity == "error" else "numgeo ignores it"
                yield (
                    f"{s.where}: unknown option {_token(k, v).lower()!r} of {name} ({what}; known: "
                    f"{', '.join(n.lower() for n in names)}; {pol.source})",
                    s.loc,
                )


@rule(
    "NG-KW-010",
    "error",
    "options numgeo rejects or reads as something else",
    source="per keyword, see the message (catalogue option tables)",
)
def unknown_option_error(ctx: Context) -> Iterator[Finding]:
    yield from _option_findings(ctx, "error")


@rule(
    "NG-KW-011",
    "warning",
    "options numgeo silently ignores",
    source="per keyword, see the message (catalogue option tables)",
)
def unknown_option_warning(ctx: Context) -> Iterator[Finding]:
    yield from _option_findings(ctx, "warning")


# Required options reported by a specific rule instead, or read by the reader.
_REQUIRED_ELSEWHERE = frozenset(
    {
        "*RIGIDBODY",
        "*USERPROPERTIES",
        "*INITIALCONDITIONS",
        "*ACCELERATOR",
        "*CONTROLS",
        "*EMBEDDEDREGION",
        "*CONTACTOPTIONS",
        "*FLUIDINTERACTION",
        "*UELPROPERTY",
        "*USERELEMENT",
        "*HILBER-HUGHES-TAYLOR",
        "*MASSSCALING",
        "*PPP-STABILISATION",
        "*TIMEINTEGRATION",
    }
)


def _option_names(spec: KeywordSpec) -> list[str]:
    return [n for n in (_bare(o.name) for o in spec.options) if n and not n.startswith(("<", "VALUE"))]


@rule(
    "NG-KW-012",
    "error",
    "required options must be given",
    source="per keyword, see the message (catalogue option tables)",
)
def required_options(ctx: Context) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        spec = spec_for(cat, s.kw, s.ctx)
        if spec is None or spec.keyword in _REQUIRED_ELSEWHERE:
            continue
        pol = _policy(s, spec)
        name = display(cat, s.kw.keyword)
        opts = _options_of(s, pol) if pol is not None else list(s.kw.options)
        names = _known_names(spec, pol) if pol is not None else _option_names(spec)
        match = pol.match if pol is not None and pol.match != "ignored" else "substring"
        found = {_recognised(k, v, names, match) for k, v in opts}
        if pol is not None and pol.exactly_one:
            if len(opts) != 1 or not found & set(pol.one_of):
                yield (
                    f"{s.where}: {name} takes exactly one of {', '.join(o.lower() for o in pol.one_of)} "
                    f"(numgeo stops otherwise; {pol.source})",
                    s.loc,
                )
            continue
        if pol is not None and pol.one_of and not found & set(pol.one_of):
            yield (
                f"{s.where}: {name} needs one of {', '.join(o.lower() for o in pol.one_of)} ({pol.source})",
                s.loc,
            )
        for o in spec.options:
            n = _bare(o.name)
            if not o.required or not n or n.startswith(("<", "VALUE")) or o.name != o.name.upper():
                continue
            if not any(n in str(f) for f in found if f is not None):
                yield (f"{s.where}: {name} needs the option {n.lower()} ({_src(o.source)})", s.loc)


# Option values with semantics of their own (checked by specific rules or the reader).
_VALUES_ELSEWHERE = frozenset(
    {
        "*MECHANICAL",
        "*PERMEABILITY",
        "*ELEMENT",
        "*SOLVER",
        "*CONTROLS",
        "*EXTRAPOLATION",
        "*INITIALCONDITIONS",
        "*ACCELERATOR",
        "*FRICTION",
        "*BOUNDARY",
        "*UBOUNDARY",
        "*SURFACE",
        "*AMPLITUDE",
        "*EMBEDDEDREGION",
        "*NORMAL",
        "*INTERACTION",
        "*MATERIAL",
        "*CONTACTPAIR",
        "*FLUIDINTERACTION",
        "*PPP-STABILISATION",
    }
)
# *Jacobian= values per preceding keyword (src/input/read_material_.f90:715-729, 794-807).
_JACOBIAN = {
    "*HYDRAULIC": ("ANALYTICAL", "CHORD-SLOPE", "SMOOTHED", "TIME-STEP-CENTERED"),
    "*RELATIVEPERMEABILITY": ("ANALYTICAL", "CHORD-SLOPE", "SMOOTHED"),
}


@rule(
    "NG-KW-013",
    "error",
    "enumerated option values must be valid",
    source="per keyword, see the message (catalogue option tables)",
)
def option_values(ctx: Context) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        spec = spec_for(cat, s.kw, s.ctx)
        if spec is None:
            continue
        name = display(cat, s.kw.keyword)
        if spec.keyword == "*JACOBIAN":
            prev = s.previous
            allowed_j = _JACOBIAN.get(prev.keyword if prev is not None else "")
            if allowed_j and s.kw.value is not None and _norm(s.kw.value) not in allowed_j:
                yield (
                    f"{s.where}: *Jacobian={s.kw.value} after {display(cat, prev.keyword if prev else '')} "
                    f"is not one of {', '.join(v.lower() for v in allowed_j)}; numgeo stops "
                    "(src/input/read_material_.f90:722,800)",
                    s.loc,
                )
            continue
        if spec.keyword in _VALUES_ELSEWHERE:
            continue
        for o in spec.options:
            allowed = _values(o.values)
            if not allowed:
                continue
            n = _bare(o.name)
            if n.startswith("VALUE"):  # '*Keyword=<value>'
                if s.kw.value is not None and _norm(s.kw.value) not in allowed:
                    yield (
                        f"{s.where}: {name}={s.kw.value} is not one of "
                        f"{', '.join(sorted(v.lower() for v in allowed))} ({_src(o.source)})",
                        s.loc,
                    )
                continue
            for k, v in s.kw.options:
                if k == n and v is not None and _norm(v) not in allowed:
                    yield (
                        f"{s.where}: {name}, {n.lower()}={v} is not one of "
                        f"{', '.join(sorted(x.lower() for x in allowed))} ({_src(o.source)})",
                        s.loc,
                    )


@rule(
    "NG-KW-014",
    "error",
    "integer and real option values must be numbers",
    source="per keyword, see the message (catalogue option tables)",
)
def option_types(ctx: Context) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        spec = spec_for(cat, s.kw, s.ctx)
        if spec is None:
            continue
        name = display(cat, s.kw.keyword)
        for o in spec.options:
            n = _bare(o.name)
            if o.value_type not in ("int", "real"):
                continue
            for k, v in s.kw.options:
                if k != n or v is None:
                    continue
                ok = is_int_token(v) if o.value_type == "int" else is_real_token(v)
                if not ok:
                    what = "an integer" if o.value_type == "int" else "a number"
                    yield (
                        f"{s.where}: {name}, {n.lower()}={v} must be {what} (numgeo's list-directed read "
                        f"fails; {_src(o.source)})",
                        s.loc,
                    )


# ----------------------------------------------------------------------------- data lines
@dataclass(frozen=True)
class _Count:
    pred: Callable[[int, int], bool]  # (narg, nphases) -> ok
    text: str


def _parse_count(rule_text: str) -> _Count | None:
    """Machine-checkable part of a catalogue count rule (``narg == 4``, ``3 <= narg <= 5``, ...).

    >>> c = _parse_count("narg == 1 or 2 (1114-1118)"); c.pred(2, 1), c.pred(3, 1)
    (True, False)
    >>> _parse_count("narg == nphases-1 (1081-1087)").pred(1, 2)
    True
    >>> _parse_count("type dependent") is None
    True
    """
    t = re.split(r"[;,]", re.sub(r"\([^)]*\)", "", rule_text))[0].strip()
    m = re.fullmatch(r"narg == (\d+)", t)
    if m:
        n = int(m.group(1))
        return _Count(lambda a, _p: a == n, f"{n}")
    m = re.fullmatch(r"narg == (\d+) or (?:narg == )?(\d+)", t)
    if m:
        a1, a2 = int(m.group(1)), int(m.group(2))
        return _Count(lambda a, _p: a in (a1, a2), f"{a1} or {a2}")
    m = re.fullmatch(r"(\d+) <= narg <= (\d+)", t)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return _Count(lambda a, _p: lo <= a <= hi, f"{lo} to {hi}")
    m = re.fullmatch(r"narg <= (\d+)", t)
    if m:
        hi = int(m.group(1))
        return _Count(lambda a, _p: a <= hi, f"at most {hi}")
    m = re.fullmatch(r"narg >= (\d+)", t)
    if m:
        lo = int(m.group(1))
        return _Count(lambda a, _p: a >= lo, f"at least {lo}")
    if t == "narg == nphases":
        return _Count(lambda a, p: a == p, "the number of phases")
    if t == "narg == nphases-1":
        return _Count(lambda a, p: a == p - 1, "the number of phases minus one")
    if t.startswith("first value"):
        return _Count(lambda a, _p: a >= 1, "at least 1")
    return None


# Count rules the generic parser cannot read in full (the catalogue states them in words).
_COUNT_OVERRIDE: dict[str, _Count] = {
    "*CLOAD": _Count(lambda a, _p: a == 3, "3"),  # 'narg == 3 for every label'
    "*MASSPOINT": _Count(lambda a, _p: a == 3, "3"),  # 'narg == 3 (l.150)'
    "*BODYFORCE": _Count(lambda a, _p: a == 6, "6"),  # 'narg == 6 for GRAV' (the only label)
    "*PHANTOMELASTICITY": _Count(lambda a, _p: a == 2, "2"),  # 'line numeric (1216) and narg == 2'
}
# Data lines checked by specific rules, or with option-dependent layouts.
_DATA_ELSEWHERE = frozenset(
    {
        "*DAMPING",
        "*VISCOUSDAMPING",
        "*HCARECORDINGTIME",
        "*PPP-STABILISATION",
        "*MECHANICAL",
        "*USERPROPERTIES",
        "*CONTACTPENALTY",
    }
)
# Keywords whose data lines numgeo reads although the catalogue lists no data-line table.
_DATA_ALLOWED = frozenset({"*USERPROPERTIES"})
# Cards of an *Output block: exactly one line of variable names (src/input/read_step_.f90:1866-1873).
_OUTPUT_CARDS = frozenset({"*NODE", "*ELEMENT", "*INTEGRATIONPOINT"})
# Data lines compared as a whole (src/input/read_material_.f90:226-234; src/input/read_step_.f90:2944-2949).
_WHOLE_LINE = {
    "*THERMALCAPACITY": ("LUMPED", "CONSISTENT"),
    "*RESET": ("DISPLACEMENT", "DISPLACEMENT,STRAIN"),
}


def _single_line(repeat: str) -> bool:
    r = repeat.lower()
    return r.startswith("exactly one") or r == "one line only"


def _data_source(spec: KeywordSpec) -> str:
    raw = spec.raw.get("data_lines") or [{}]
    return _src(raw[0].get("source")) if raw[0].get("source") else _src(spec.raw.get("handler"))


@rule(
    "NG-KW-020",
    "error",
    "data lines must have the fields numgeo reads",
    source="per keyword, see the message (catalogue data-line tables)",
)
def data_lines(ctx: Context) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        if s.ctx in ("procedure", "dynamic", "explicit", "equation"):
            continue  # procedures: NG-STEP-010
        spec = spec_for(cat, s.kw, s.ctx)
        if spec is None or spec.keyword in _DATA_ELSEWHERE:
            continue
        name = display(cat, s.kw.keyword)
        rows = s.kw.data
        src = _data_source(spec)
        if spec.keyword in _WHOLE_LINE:
            allowed = _WHOLE_LINE[spec.keyword]
            text = ",".join(_norm(str(t)) for t in rows[0]) if len(rows) == 1 else None
            if text not in allowed:
                yield (
                    f"{s.where}: {name} needs exactly one data line "
                    f"{' or '.join(a.lower() for a in allowed)} (numgeo stops otherwise; {src})",
                    s.loc,
                )
            continue
        if s.ctx.startswith("output-") and spec.keyword in _OUTPUT_CARDS:
            if len(rows) != 1:
                yield (
                    f"{s.where}: {name} in *Output needs exactly one line of variable names, {len(rows)} "
                    "given (src/input/read_step_.f90:1866-1873)",
                    s.loc,
                )
            continue
        if not spec.data_lines:
            if rows and spec.keyword not in _DATA_ALLOWED and not (s.ctx == "model" and _all_numeric(rows)):
                yield (
                    f"{s.where}: {name} reads no data line; numgeo reads {_row_text(rows[0])!r} as a keyword and stops",
                    s.loc,
                )
            continue
        if len(spec.data_lines) != 1:
            continue  # option-dependent layouts: specific rules
        dl = spec.data_lines[0]
        cnt = _COUNT_OVERRIDE.get(spec.keyword) or _parse_count(dl.count_rule)
        if cnt is None:
            continue
        if _single_line(dl.repeat) and len(rows) != 1:
            yield (f"{s.where}: {name} reads exactly one data line, {len(rows)} given ({src})", s.loc)
        phases = (s.material.phases or 1) if s.material is not None else 1
        for r in rows[:1] if _single_line(dl.repeat) else rows:
            if not cnt.pred(len(r), phases):
                yield (
                    f"{s.where}: {name} needs {cnt.text} values per data line, {len(r)} given ({dl.count_rule}; {src})",
                    s.loc,
                )
                continue
            yield from _field_types(s, name, dl.fields, r)


def _all_numeric(rows: list[list[Token]]) -> bool:
    return all(r and is_real_token(r[0]) for r in rows)


def _row_text(r: list[Token]) -> str:
    return ", ".join(str(t) for t in r)


def _field_types(s: Site, name: str, fields: Sequence[dict[str, object]], row: list[Token]) -> Iterator[Finding]:
    if not fields:
        return
    types = [str(f.get("type") or "") for f in fields]
    if len(fields) == 1 and types[0] in ("real", "int"):  # a list of values
        types = types * len(row)
    for i, (t, tok) in enumerate(zip(types, row, strict=False)):
        field = fields[min(i, len(fields) - 1)].get("name")
        if t == "real" and not is_real_token(tok):
            yield (f"{s.where}: {name}: field {i + 1} ({field}) must be a number, got {tok!r}", s.loc)
        elif t == "int" and not is_int_token(tok):
            yield (f"{s.where}: {name}: field {i + 1} ({field}) must be an integer, got {tok!r}", s.loc)


@rule(
    "NG-KW-021",
    "warning",
    "numeric lines after a model keyword that reads none are skipped",
    source="src/input/read_input.f90:229 (numeric lines are skipped)",
)
def skipped_lines(ctx: Context) -> Iterator[Finding]:
    cat = ctx.catalogue
    for s in sites(ctx.deck):
        if s.ctx != "model":
            continue
        spec = spec_for(cat, s.kw, s.ctx)
        if spec is None or spec.data_lines or not s.kw.data or spec.keyword in _DATA_ALLOWED:
            continue
        if _all_numeric(s.kw.data):
            yield (
                f"{display(cat, s.kw.keyword)} reads no data line; numgeo skips the {len(s.kw.data)} numeric "
                "line(s) after it",
                s.loc,
            )
