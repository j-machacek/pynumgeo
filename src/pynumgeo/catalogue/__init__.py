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
"""What numgeo accepts: keywords, options, element types, constitutive models, messages.

The catalogue is generated from the numgeo source; every entry cites the source line it was read from
(``file``, ``line``, ``routine``, and an ``anchor`` hash of that line, which reveals when the source has
moved on). Where the numgeo documentation and the source disagree, the source wins.

Examples:
    >>> from pynumgeo import catalogue as cat
    >>> cat.keyword("*Step").display
    '*Step'
    >>> [o.name for o in cat.keyword("step").options][:3]
    ['NAME', 'INC', 'NLGEOM']
    >>> m = cat.material_model("Mohr-Coulomb")
    >>> m.nprops, [p.name for p in m.parameters]
    (6, ['E', 'nu', 'c', 'phi', 'psi', 'theta'])
    >>> cat.element_type("u8p4-sat").nnodes
    8
    >>> cat.suggest("*Bounday")[0]
    '*Boundary'
"""

from __future__ import annotations

import difflib
import functools
import hashlib
import json
import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from pynumgeo._version import NUMGEO_DOCS_COMMIT, NUMGEO_SOURCE_COMMIT

__all__ = [
    "Catalogue",
    "DataLineSpec",
    "ElementTypeSpec",
    "KeywordSpec",
    "MaterialModelSpec",
    "OptionSpec",
    "ParameterSpec",
    "describe",
    "element_type",
    "keyword",
    "load",
    "material_model",
    "normalise_keyword",
    "suggest",
]


def normalise_keyword(name: str) -> str:
    """Solver spelling of a keyword: upper case, no blanks, leading ``*``.

    >>> normalise_keyword("initial conditions")
    '*INITIALCONDITIONS'
    """
    k = name.strip().upper().replace(" ", "")
    return k if k.startswith("*") else "*" + k


def normalise_name(name: str) -> str:
    """Library spelling of a model or element name (upper case, no blanks)."""
    return name.strip().upper().replace(" ", "")


@dataclass(frozen=True)
class OptionSpec:
    """An option of a keyword as numgeo reads it."""

    name: str
    value_type: str
    values: tuple[str, ...]
    required: bool
    default: Any
    match: str
    notes: str
    source: dict[str, Any] | None

    @classmethod
    def from_raw(cls, o: dict[str, Any]) -> OptionSpec:
        return cls(
            name=str(o.get("name", "")),
            value_type=str(o.get("value_type") or ""),
            values=tuple(str(v) for v in o.get("values") or ()),
            required=bool(o.get("required")),
            default=o.get("default"),
            match=str(o.get("match") or ""),
            notes=str(o.get("notes") or ""),
            source=o.get("source"),
        )


@dataclass(frozen=True)
class DataLineSpec:
    """A data line of a keyword: its fields, count rule and repetition."""

    description: str
    fields: tuple[dict[str, Any], ...]
    count_rule: str
    repeat: str

    @classmethod
    def from_raw(cls, d: dict[str, Any]) -> DataLineSpec:
        return cls(
            description=str(d.get("description") or ""),
            fields=tuple(d.get("fields") or ()),
            count_rule=str(d.get("count_rule") or ""),
            repeat=str(d.get("repeat") or ""),
        )


@dataclass(frozen=True)
class KeywordSpec:
    """A keyword in one context (the same keyword can mean different things in different contexts)."""

    keyword: str
    display: str
    area: str
    context: str
    parent: str | None
    match_forms: tuple[str, ...]
    options: tuple[OptionSpec, ...]
    data_lines: tuple[DataLineSpec, ...]
    doc: str | None
    notes: str
    raw: dict[str, Any] = field(repr=False, compare=False)

    @property
    def contexts(self) -> tuple[str, ...]:
        """Contexts in which the keyword is read (``model``, ``part``, ``step``, ``material``, ...)."""
        return tuple(c.strip() for c in self.context.split("|") if c.strip())

    def option(self, name: str) -> OptionSpec | None:
        """Option by name (case-insensitive)."""
        n = name.upper()
        for o in self.options:
            if o.name.upper() == n:
                return o
        return None


@dataclass(frozen=True)
class ParameterSpec:
    """A parameter of a constitutive model (position in the data lines is ``index``)."""

    index: int
    name: str
    symbol: str
    unit: str | None
    meaning: str
    default: Any
    required: bool


@dataclass(frozen=True)
class MaterialModelSpec:
    """A constitutive model of numgeo's material library (``*Mechanical = <name>``)."""

    name: str
    nprops: int | None
    parameters: tuple[ParameterSpec, ...]
    nstatev: Any
    optional_parameters: tuple[dict[str, Any], ...]
    public: bool
    doc: str | None
    notes: str
    raw: dict[str, Any] = field(repr=False, compare=False)

    @property
    def parameters_known(self) -> bool:
        """True if the meaning of every parameter is established."""
        return bool(self.raw.get("order_established_from_source")) and len(self.parameters) == (self.nprops or 0)


@dataclass(frozen=True)
class ElementTypeSpec:
    """An element type of numgeo's element library (``*Element, type=<name>``)."""

    name: str
    nnodes: int
    ndim: int
    axisymmetric: bool
    dofs: tuple[str, ...]
    family: str
    shape: str
    interpolation: str
    face_topology: str | None
    vtk_type: int | None
    status: str
    raw: dict[str, Any] = field(repr=False, compare=False)

    @property
    def usable(self) -> bool:
        """False for library entries without a formulation (numgeo stops when they are used)."""
        return self.status == "ok"


class Catalogue:
    """The loaded catalogue. Use :func:`load` (cached) rather than constructing it."""

    def __init__(self, data: dict[str, Any], messages: list[dict[str, Any]] | None = None) -> None:
        self.data = data
        self.source_commit: str = data.get("source_commit", NUMGEO_SOURCE_COMMIT)
        self.docs_commit: str = data.get("docs_commit", NUMGEO_DOCS_COMMIT)
        self._messages = messages
        self._keywords = [self._kw(k) for k in data["keywords"]]
        sec = data["sections"]
        self._elements = {
            normalise_name(e["name"]): self._el(e)
            for e in sec["model"]["element_types"]
            if not str(e.get("status", "")).startswith("alias")
        }
        self._aliases = {
            normalise_name(e["name"]): normalise_name(str(e.get("alias_of", "")))
            for e in sec["model"]["element_types"]
            if str(e.get("status", "")).startswith("alias")
        }
        self._models = {normalise_name(m["name"]): self._mat(m) for m in sec["materials"]["mechanical_models"]}
        for m in sec["materials"]["mechanical_models"]:
            for a in m.get("aliases") or []:
                self._models.setdefault(normalise_name(a), self._models[normalise_name(m["name"])])

    # ------------------------------------------------------------------ construction helpers
    @staticmethod
    def _kw(k: dict[str, Any]) -> KeywordSpec:
        return KeywordSpec(
            keyword=k["keyword"],
            display=k.get("display") or k["keyword"],
            area=k.get("area", ""),
            context=str(k.get("context") or ""),
            parent=k.get("parent"),
            match_forms=tuple(str(x) for x in k.get("match_forms") or ()),
            options=tuple(OptionSpec.from_raw(o) for o in k.get("options") or ()),
            data_lines=tuple(DataLineSpec.from_raw(d) for d in k.get("data_lines") or ()),
            doc=k.get("doc"),
            notes=str(k.get("notes") or ""),
            raw=k,
        )

    @staticmethod
    def _el(e: dict[str, Any]) -> ElementTypeSpec:
        return ElementTypeSpec(
            name=e["name"],
            nnodes=int(e.get("nnodes") or 0),
            ndim=int(e.get("ndim") or 0),
            axisymmetric=bool(e.get("axisymmetric")),
            dofs=tuple(e.get("dofs_per_node") or ()),
            family=str(e.get("family") or ""),
            shape=str(e.get("shape") or ""),
            interpolation=str(e.get("interpolation") or ""),
            face_topology=e.get("surface_face_topology"),
            vtk_type=e.get("vtk_type"),
            status=str(e.get("status") or ""),
            raw=e,
        )

    @staticmethod
    def _mat(m: dict[str, Any]) -> MaterialModelSpec:
        np_ = m.get("nprops") or {}
        nprops = np_.get("exact") if isinstance(np_, dict) else np_
        params = tuple(
            ParameterSpec(
                index=int(p.get("index", i + 1)),
                name=str(p.get("name") or f"p{i + 1}"),
                symbol=str(p.get("symbol") or ""),
                unit=p.get("unit"),
                meaning=str(p.get("meaning") or ""),
                default=p.get("default"),
                required=bool(p.get("required", True)),
            )
            for i, p in enumerate(m.get("parameters") or ())
        )
        return MaterialModelSpec(
            name=m["name"],
            nprops=int(nprops) if isinstance(nprops, int) else None,
            parameters=params,
            nstatev=m.get("nstatev"),
            optional_parameters=tuple(m.get("optional_parameters") or ()),
            public=bool(m.get("public", True)),
            doc=m.get("doc"),
            notes=str(m.get("notes") or ""),
            raw=m,
        )

    # ------------------------------------------------------------------ lookups
    @property
    def keywords(self) -> list[KeywordSpec]:
        """All keyword entries (one per keyword and context)."""
        return list(self._keywords)

    def keyword_entries(self, name: str) -> list[KeywordSpec]:
        """All entries of a keyword (it may exist in several contexts)."""
        k = normalise_keyword(name)
        return [s for s in self._keywords if s.keyword == k]

    def keyword(self, name: str, context: str | None = None) -> KeywordSpec:
        """A keyword entry, optionally for a context (``model``, ``step``, ``material``, ``output-print``...).

        Raises:
            KeyError: if the keyword (in that context) is unknown; the message suggests similar names.
        """
        entries = self.keyword_entries(name)
        if context is not None:
            entries = [e for e in entries if context in e.contexts] or entries
        if not entries:
            raise KeyError(f"unknown keyword {name!r}; did you mean {self.suggest(name)}?")
        return entries[0]

    def element_type(self, name: str) -> ElementTypeSpec:
        """An element type by library name or alias (case-insensitive).

        Raises:
            KeyError: if numgeo has no such element type.
        """
        n = normalise_name(name)
        n = self._aliases.get(n, n)
        if n not in self._elements:
            close = difflib.get_close_matches(n, list(self._elements), n=3)
            raise KeyError(f"unknown element type {name!r}; did you mean {close}?")
        return self._elements[n]

    @property
    def element_types(self) -> list[ElementTypeSpec]:
        """All element types of the library (without aliases)."""
        return list(self._elements.values())

    def material_model(self, name: str) -> MaterialModelSpec:
        """A constitutive model by library name (case-insensitive).

        Raises:
            KeyError: if the model is not in this catalogue (the public catalogue omits some models).
        """
        n = normalise_name(name)
        if n not in self._models:
            close = difflib.get_close_matches(n, list(self._models), n=3)
            raise KeyError(f"unknown constitutive model {name!r}; did you mean {close}?")
        return self._models[n]

    @property
    def material_models(self) -> list[MaterialModelSpec]:
        """All constitutive models in this catalogue."""
        seen: dict[str, MaterialModelSpec] = {}
        for m in self._models.values():
            seen.setdefault(m.name, m)
        return list(seen.values())

    def is_private_name(self, name: str) -> bool:
        """True for a model/contact/embedded name that numgeo knows but the public catalogue omits."""
        h = hashlib.sha256(normalise_name(name).encode()).hexdigest()[:20]
        return h in set(self.data.get("private_name_hashes", ()))

    def section(self, area: str, name: str) -> Any:
        """Raw access to a catalogue section, e.g. ``section("loads", "dof_names")``."""
        return self.data["sections"][area][name]

    def messages(self) -> list[dict[str, Any]]:
        """The message inventory (every error/warning/stop site of the solver)."""
        if self._messages is None:
            self._messages = _load_json("messages.json")
        return self._messages

    def suggest(self, name: str, n: int = 3) -> list[str]:
        """Keywords (display spelling) similar to ``name``."""
        k = normalise_keyword(name)
        names = sorted({s.keyword for s in self._keywords})
        hits = difflib.get_close_matches(k, names, n=n, cutoff=0.6)
        return [self.keyword(h).display for h in hits]

    def doc_page(self, page: str | None) -> str | None:
        """Text of a bundled documentation page (``docs/reference/...md``), if bundled."""
        if not page:
            return None
        rel = page.split("#")[0].removeprefix("docs/")
        try:
            return resources.files("pynumgeo.catalogue").joinpath("data", "docs", rel).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None

    def describe(self, name: str, *, with_docs: bool = True) -> str:
        """Human/agent readable description of a keyword, ``material:<model>`` or ``element:<type>``."""
        if name.lower().startswith("material:"):
            m = self.material_model(name.split(":", 1)[1])
            lines = [f"*Mechanical = {m.name.lower()}  ({m.nprops} parameters)", ""]
            lines += [f"{p.index:3d}  {p.name:<14} {p.unit or '':<8} {p.meaning}" for p in m.parameters]
            if m.notes:
                lines += ["", m.notes]
            page = self.doc_page(m.doc) if with_docs else None
            return "\n".join(lines + (["", page] if page else []))
        if name.lower().startswith("element:"):
            e = self.element_type(name.split(":", 1)[1])
            return (
                f"*Element, type={e.name.lower()}\n  nodes {e.nnodes}, dimension {e.ndim}"
                f"{' (axisymmetric)' if e.axisymmetric else ''}, dofs per node {', '.join(e.dofs)}\n"
                f"  family {e.family}, shape {e.shape}, interpolation {e.interpolation}, status {e.status}"
            )
        out = []
        for s in self.keyword_entries(name) or [self.keyword(name)]:
            out.append(f"{s.display}   (context: {s.context}; area: {s.area})")
            for o in s.options:
                req = "required" if o.required else "optional"
                vals = f" values {', '.join(v.lower() for v in o.values)}" if o.values else ""
                out.append(f"  {o.name.lower():<16} {o.value_type:<8} {req}{vals}")
            for d in s.data_lines:
                names = ", ".join(str(f.get("name")) for f in d.fields)
                out.append(f"  data: {names}" + (f"   [{d.count_rule}]" if d.count_rule else ""))
            if s.notes:
                out.append("  notes: " + s.notes)
            page = self.doc_page(s.doc) if with_docs else None
            if page:
                out += ["", page]
        return "\n".join(out)


def _load_json(name: str) -> Any:
    return json.loads(resources.files("pynumgeo.catalogue").joinpath("data", name).read_text(encoding="utf-8"))


@functools.cache
def load() -> Catalogue:
    """The catalogue (cached). ``PYNUMGEO_CATALOGUE`` may point to a complete (private) catalogue file."""
    override = os.environ.get("PYNUMGEO_CATALOGUE")
    if override:
        return Catalogue(json.loads(Path(override).read_text(encoding="utf-8")))
    return Catalogue(_load_json("catalogue.json"))


def keyword(name: str, context: str | None = None) -> KeywordSpec:
    """Shortcut for ``load().keyword(...)``."""
    return load().keyword(name, context)


def element_type(name: str) -> ElementTypeSpec:
    """Shortcut for ``load().element_type(...)``."""
    return load().element_type(name)


def material_model(name: str) -> MaterialModelSpec:
    """Shortcut for ``load().material_model(...)``."""
    return load().material_model(name)


def suggest(name: str, n: int = 3) -> list[str]:
    """Shortcut for ``load().suggest(...)``."""
    return load().suggest(name, n)


def describe(name: str, *, with_docs: bool = True) -> str:
    """Shortcut for ``load().describe(...)``."""
    return load().describe(name, with_docs=with_docs)
