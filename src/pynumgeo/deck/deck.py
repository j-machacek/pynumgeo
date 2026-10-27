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
"""The semantic model of a numgeo input deck.

A :class:`Deck` holds the :class:`~pynumgeo.mesh.Mesh`, amplitudes, materials, section assignments,
further model-level keywords (initial conditions, contact, embedded regions, ...) and the steps. What
pynumgeo does not model with a dedicated class is a generic :class:`~pynumgeo.deck.keyword.Keyword`.

Nothing is inherited between steps except field output (numgeo behaviour); every step carries its own
boundary conditions, loads, solver and controls.

Example (a one-element beam, benchmark ``beam-slender-1elem``):
    >>> from pynumgeo.deck import Deck, Material, Step, Keyword
    >>> d = Deck()
    >>> d.mesh.add_nodes([[0.0, 0.0], [0.2, 0.0]])
    array([1, 2])
    >>> d.mesh.add_elements("u2-beam", [[1, 2]])
    array([1])
    >>> _ = d.mesh.add_nset("Fix", [1]); _ = d.mesh.add_nset("Load", [2]); _ = d.mesh.add_elset("All", [1])
    >>> beam = Material(name="Beam", phases=1)
    >>> beam.add("*Beam properties", data=[[1e-4, 210e6, 80.77e6, 8.33e-10, 8.33e-10, 16.67e-10, 0.8333, 0.8333]])
    >>> beam.add("*Density", data=[[1.0]])
    >>> d.materials.append(beam)
    >>> _ = d.assign("All", "Beam")
    >>> s = Step(name="Loading", inc=1000000, procedure=Keyword.make("*Static", data=[[0.05, 1.0, 0.05, 0.05]]))
    >>> _ = s.add("*Boundary", data=[["Fix", "u1", 0.0], ["Fix", "u2", 0.0], ["Fix", "r3", 0.0]])
    >>> _ = s.add("*Cload", options=["ramp"], data=[["Load", 2, -1.0]])
    >>> d.steps.append(s)
    >>> [x.name for x in d.materials], d.steps[0].name, len(d.steps[0].items)
    (['Beam'], 'Loading', 2)
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pynumgeo.deck.keyword import Keyword, OptionInput, Token
from pynumgeo.io.numbers import to_token
from pynumgeo.mesh.mesh import Mesh

__all__ = ["Amplitude", "Deck", "Material", "Section", "Step"]


def _key(name: str) -> str:
    return name.upper().replace(" ", "")


class Amplitude(BaseModel):
    """``*Amplitude, name=..., type=...`` with its data lines (type in lower case, e.g. ``tabular``)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: str
    type: str
    data: list[list[Token]] = Field(default_factory=list)
    source: str | None = Field(default=None, exclude=True, repr=False)
    #: ``**`` lines the writer puts above it (not part of comparisons)
    comment: str | None = Field(default=None, exclude=True, repr=False)

    @field_validator("data")
    @classmethod
    def _norm_data(cls, v: list[list[Token]]) -> list[list[Token]]:
        return [[to_token(t) if isinstance(t, str) else t for t in row] for row in v]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Amplitude):
            return NotImplemented
        return (
            _key(self.name) == _key(other.name)
            and _key(self.type) == _key(other.type)
            and Keyword(keyword="*X", data=self.data) == Keyword(keyword="*X", data=other.data)
        )

    __hash__ = None  # type: ignore[assignment]


class Material(BaseModel):
    """``*Material`` with its sub-keywords (``*Mechanical``, ``*Density``, ``*Permeability``, ...).

    ``phases`` is written only when given (numgeo's default is 1).
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: str
    phases: int | None = None
    properties: list[Keyword] = Field(default_factory=list)
    extra_options: list[tuple[str, str | None]] = Field(default_factory=list)
    source: str | None = Field(default=None, exclude=True, repr=False)
    #: ``**`` lines the writer puts above it (not part of comparisons)
    comment: str | None = Field(default=None, exclude=True, repr=False)

    def add(
        self,
        keyword: str,
        value: str | None = None,
        options: Iterable[OptionInput] = (),
        data: Sequence[Sequence[Token]] = (),
        comment: str | None = None,
    ) -> None:
        """Append a material sub-keyword, e.g. ``add("*Density", data=[[2.0]])``."""
        self.properties.append(Keyword.make(keyword, value=value, options=options, data=data, comment=comment))

    def property(self, keyword: str) -> Keyword | None:
        """First sub-keyword of that kind (``*Mechanical``, ``*Density``, ...)."""
        k = Keyword(keyword=keyword).keyword
        return next((p for p in self.properties if p.keyword == k), None)

    def set_mechanical(self, model: str, parameters: Sequence[float] | dict[str, float]) -> None:
        """Set ``*Mechanical = <model>`` with parameters in library order (list) or by name (dict).

        Named parameters are mapped with the catalogue; a dict must name every parameter.

        Raises:
            KeyError: unknown model or parameter name.
            ValueError: wrong number of parameters.
        """
        from pynumgeo import catalogue

        spec = catalogue.material_model(model)
        if isinstance(parameters, dict):
            names = [p.name for p in spec.parameters]
            unknown = set(parameters) - set(names)
            if unknown:
                raise KeyError(f"unknown parameters {sorted(unknown)} for {spec.name}; parameters are {names}")
            missing = [n for n in names if n not in parameters]
            if missing:
                raise ValueError(f"missing parameters {missing} for {spec.name}")
            values = [float(parameters[n]) for n in names]
        else:
            values = [float(v) for v in parameters]
        if spec.nprops is not None and len(values) != spec.nprops:
            raise ValueError(f"{spec.name} needs exactly {spec.nprops} parameters, got {len(values)}")
        self.properties = [p for p in self.properties if p.keyword != "*MECHANICAL"]
        rows = [values[i : i + 8] for i in range(0, len(values), 8)] or [[]]
        self.properties.insert(0, Keyword.make("*Mechanical", value=spec.name.lower(), data=rows))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Material):
            return NotImplemented
        return (
            _key(self.name) == _key(other.name)
            and (self.phases or 1) == (other.phases or 1)
            and self.properties == other.properties
        )

    __hash__ = None  # type: ignore[assignment]


class Section(BaseModel):
    """Material assignment ``*Solid section, elset=..., material=...`` (``*Assign material`` is the same)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    elset: str
    material: str
    keyword: str = "*SOLIDSECTION"
    amgcl_direct: bool = False
    source: str | None = Field(default=None, exclude=True, repr=False)
    #: ``**`` lines the writer puts above it (not part of comparisons)
    comment: str | None = Field(default=None, exclude=True, repr=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Section):
            return NotImplemented
        return (_key(self.elset), _key(self.material), self.amgcl_direct) == (
            _key(other.elset),
            _key(other.material),
            other.amgcl_direct,
        )

    __hash__ = None  # type: ignore[assignment]


class Step(BaseModel):
    """``*Step`` ... ``*End step``: header options, the procedure keyword and the step's keywords in order.

    Header defaults are the solver's (``inc`` 1 000 000, ``maxiter`` 24, ``miniter`` 1); ``None`` means
    "not written".
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: str
    procedure: Keyword
    inc: int | None = None
    maxiter: int | None = None
    miniter: int | None = None
    nlgeom: bool = False
    nocutback: bool = False
    scalefactor: float | None = None
    items: list[Keyword] = Field(default_factory=list)
    extra_options: list[tuple[str, str | None]] = Field(default_factory=list)
    source: str | None = Field(default=None, exclude=True, repr=False)
    #: ``**`` lines the writer puts above it (not part of comparisons)
    comment: str | None = Field(default=None, exclude=True, repr=False)

    def add(
        self,
        keyword: str,
        value: str | None = None,
        options: Iterable[OptionInput] = (),
        data: Sequence[Sequence[Token]] = (),
        children: Iterable[Keyword] = (),
        comment: str | None = None,
    ) -> Keyword:
        """Append a step keyword (``*Boundary``, ``*Cload``, ``*Output``, ``*Solver``, ...) and return it."""
        kw = Keyword.make(keyword, value=value, options=options, data=data, children=children, comment=comment)
        self.items.append(kw)
        return kw

    def keywords(self, keyword: str) -> list[Keyword]:
        """All step keywords of one kind, in order."""
        k = Keyword(keyword=keyword).keyword
        return [x for x in self.items if x.keyword == k]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Step):
            return NotImplemented
        return (
            _key(self.name) == _key(other.name)
            and self.procedure == other.procedure
            and (self.inc, self.maxiter, self.miniter, self.nlgeom, self.nocutback, self.scalefactor)
            == (other.inc, other.maxiter, other.miniter, other.nlgeom, other.nocutback, other.scalefactor)
            and self.items == other.items
        )

    __hash__ = None  # type: ignore[assignment]


def _mech_name(m: Material) -> str | None:
    p = m.property("*Mechanical")
    return p.value if p is not None else None


class Deck(BaseModel):
    """A numgeo input deck (see module docstring)."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True, validate_assignment=True)

    mesh: Mesh = Field(default_factory=Mesh)
    amplitudes: list[Amplitude] = Field(default_factory=list)
    materials: list[Material] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    keywords: list[Keyword] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)
    #: ``**`` lines the writer puts above ``*End input`` (not part of comparisons)
    end_comment: str | None = Field(default=None, exclude=True, repr=False)

    def assign(self, elset: str, material: str) -> Section:
        """Assign a material to an element set (``*Solid section``)."""
        s = Section(elset=elset, material=material)
        self.sections.append(s)
        return s

    def material(self, name: str) -> Material:
        """Material by name (case-insensitive)."""
        for m in self.materials:
            if _key(m.name) == _key(name):
                return m
        raise KeyError(f"no material {name!r}")

    def step(self, name: str) -> Step:
        """Step by name (case-insensitive)."""
        for s in self.steps:
            if _key(s.name) == _key(name):
                return s
        raise KeyError(f"no step {name!r}")

    def rename(self, old: str, new: str) -> int:
        """Rename a set, surface, material or amplitude and every reference to it (see
        :func:`pynumgeo.deck.names.rename`); returns the number of places changed."""
        from pynumgeo.deck.names import rename

        return rename(self, old, new)

    def safe_names(self) -> dict[str, str]:
        """Rename every name numgeo would read as an option (``FindFix``, ``BodenInstance.All``, ...) and
        return ``{old: new}`` (see :func:`pynumgeo.deck.names.safe_names`)."""
        from pynumgeo.deck.names import safe_names

        return safe_names(self)

    def defined_names(self) -> set[str]:
        """Upper-case names of everything the deck defines (sets, surfaces, materials, amplitudes, ...)."""
        names = {s.key for s in self.mesh.nsets} | {s.key for s in self.mesh.elsets}
        names |= {s.key for s in self.mesh.surfaces}
        names |= {_key(m.name) for m in self.materials} | {_key(a.name) for a in self.amplitudes}
        names |= {_key(s.name) for s in self.steps}
        for kw in self.keywords:
            n = kw.option("NAME")
            if n:
                names.add(_key(n))
        return names

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Deck):
            return NotImplemented
        return (
            self.mesh == other.mesh
            and self.amplitudes == other.amplitudes
            and self.materials == other.materials
            and self.sections == other.sections
            and self.keywords == other.keywords
            and self.steps == other.steps
        )

    __hash__ = None  # type: ignore[assignment]

    def summary(self) -> dict[str, Any]:
        """Short description for agents and logs."""
        return {
            "mesh": self.mesh.summary(),
            "amplitudes": [a.name for a in self.amplitudes],
            "materials": [{"name": m.name, "mechanical": _mech_name(m)} for m in self.materials],
            "sections": [(s.elset, s.material) for s in self.sections],
            "model_keywords": [k.keyword for k in self.keywords],
            "steps": [
                {"name": s.name, "procedure": s.procedure.keyword, "keywords": [k.keyword for k in s.items]}
                for s in self.steps
            ],
        }
