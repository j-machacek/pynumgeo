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
"""A keyword of an input deck in generic form.

Every keyword that pynumgeo does not represent by a dedicated class is a :class:`Keyword`: the solver
keyword, an optional value (``*Mechanical = mohr-coulomb``), options in order, data lines and children.
The validator checks generic keywords against the catalogue (known keyword in this context, known
options, data-line field counts); the writer spells them in normal case.

Examples:
    >>> kw = Keyword.make("*Boundary", data=[["Fix", "u1", 0.0], ["Fix", "u2", 0.0]])
    >>> kw.keyword, kw.data[1]
    ('*BOUNDARY', ['Fix', 'u2', 0.0])
    >>> Keyword.make("*Output", options=["field", "vtk", ("frequency", 2)]).options
    [('FIELD', None), ('VTK', None), ('FREQUENCY', '2')]
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pynumgeo.catalogue import normalise_keyword

__all__ = ["Keyword", "OptionInput", "Token"]

#: A data-line token: integer, real or text (names keep the user's spelling).
Token = Union[int, float, str]  # noqa: UP007  (pydantic needs a runtime union)
#: How options can be given to :meth:`Keyword.make`: ``"flag"``, ``("key", value)`` or ``"key=value"``.
OptionInput = Union[str, tuple[str, Any]]  # noqa: UP007


class Keyword(BaseModel):
    """A keyword block in generic form.

    Attributes:
        keyword: solver spelling (upper case, no blanks), e.g. ``*BOUNDARY``.
        value: text after ``=`` in the keyword itself (``*MECHANICAL=...``), as given.
        options: ``(KEY, value)`` pairs in order; ``KEY`` upper case, value as given or ``None`` for a flag.
        data: data lines, one list of tokens per line.
        children: child keywords (material sub-keywords, output cards, ``*Normal``/``*Friction``, ...).
        source: where the keyword was read from (``file:line``), not part of comparisons.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    keyword: str
    value: str | None = None
    options: list[tuple[str, str | None]] = Field(default_factory=list)
    data: list[list[Token]] = Field(default_factory=list)
    children: list[Keyword] = Field(default_factory=list)
    source: str | None = Field(default=None, exclude=True, repr=False)

    @field_validator("keyword")
    @classmethod
    def _norm_kw(cls, v: str) -> str:
        return normalise_keyword(v)

    @field_validator("data", mode="before")
    @classmethod
    def _no_bools(cls, v: Any) -> Any:
        if isinstance(v, list | tuple):
            for row in v:
                if isinstance(row, list | tuple) and any(isinstance(t, bool) for t in row):
                    raise TypeError("boolean values are not numgeo syntax; give 1/0 or the keyword's own words")
        return v

    @field_validator("options")
    @classmethod
    def _norm_opts(cls, v: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]:
        return [(k.strip().upper().replace(" ", ""), val) for k, val in v]

    def __eq__(self, other: object) -> bool:  # source position is not part of the identity
        if not isinstance(other, Keyword):
            return NotImplemented
        return (
            self.keyword == other.keyword
            and _ieq(self.value, other.value)
            and [(k, _up(v)) for k, v in self.options] == [(k, _up(v)) for k, v in other.options]
            and _data_eq(self.data, other.data)
            and self.children == other.children
        )

    __hash__ = None  # type: ignore[assignment]

    @classmethod
    def make(
        cls,
        keyword: str,
        value: str | None = None,
        options: Iterable[OptionInput] = (),
        data: Sequence[Sequence[Token]] = (),
        children: Iterable[Keyword] = (),
    ) -> Keyword:
        """Convenience constructor (see the module example)."""
        opts: list[tuple[str, str | None]] = []
        for o in options:
            if isinstance(o, tuple):
                opts.append((str(o[0]), None if o[1] is None else _fmt_option(o[1])))
            elif "=" in o:
                k, v = o.split("=", 1)
                opts.append((k, v.strip()))
            else:
                opts.append((o, None))
        return cls(keyword=keyword, value=value, options=opts, data=[list(r) for r in data], children=list(children))

    def option(self, key: str) -> str | None:
        """Value of the first option whose key equals ``key`` (case-insensitive); ``None`` if absent."""
        k = key.upper()
        for kk, v in self.options:
            if kk == k:
                return v
        return None

    def has_option(self, key: str) -> bool:
        """True if an option with this key is present (flag or with value)."""
        k = key.upper()
        return any(kk == k for kk, _ in self.options)


def _fmt_option(v: Any) -> str:
    if isinstance(v, bool):
        raise TypeError("boolean option values are not numgeo syntax; give a flag instead")
    if isinstance(v, float):
        from pynumgeo.io.numbers import format_real

        return format_real(v)
    return str(v)


def _up(v: str | None) -> str | None:
    return None if v is None else v.upper().replace(" ", "")


def _ieq(a: str | None, b: str | None) -> bool:
    return _up(a) == _up(b)


def _tok_eq(a: Token, b: Token) -> bool:
    if isinstance(a, str) or isinstance(b, str):
        return isinstance(a, str) and isinstance(b, str) and a.upper() == b.upper()
    return float(a) == float(b)


def _data_eq(a: list[list[Token]], b: list[list[Token]]) -> bool:
    return len(a) == len(b) and all(len(x) == len(y) and all(map(_tok_eq, x, y)) for x, y in zip(a, b, strict=True))
