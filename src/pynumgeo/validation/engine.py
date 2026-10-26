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
"""Rule engine of the validator.

A rule is a function ``(ctx) -> Iterable[Finding]`` registered with :func:`rule`. Its metadata (id,
severity, title, the solver source it mirrors) is part of the rule, so
every reported :class:`~pynumgeo.validation.issue.Issue` can say why it is reported. Rule ids are stable
(``NG-<AREA>-<nnn>``) and documented by :func:`rules`.

A finding is either a plain message or ``(message, location)``; the engine turns it into an Issue.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Union

from pynumgeo import catalogue as _cat
from pynumgeo.deck.deck import Deck
from pynumgeo.issue import Issue, Severity

__all__ = ["BuildProfile", "Context", "Finding", "Rule", "rule", "rules", "run_rules"]

Finding = Union[str, tuple[str, str | None]]  # noqa: UP007


@dataclass(frozen=True)
class BuildProfile:
    """Which numgeo build the deck is meant for.

    ``full`` (default): the current developer source as built (``public_version = .false.``) —
    every model of the catalogue is allowed. ``public``: a build with ``public_version = .true.``
    (non-public models, contact models and line-search options are rejected).
    ``solvers``: linear solvers compiled into the executable (``None`` = unknown, not checked).
    """

    name: str = "full"
    public: bool = False
    solvers: frozenset[str] | None = None

    @classmethod
    def full(cls) -> BuildProfile:
        """The current developer build (default)."""
        return cls()

    @classmethod
    def public_build(cls) -> BuildProfile:
        """A build with ``public_version = .true.``."""
        return cls(name="public", public=True)


@dataclass
class Context:
    """What a rule sees: the deck, the catalogue and the build profile."""

    deck: Deck
    catalogue: _cat.Catalogue
    profile: BuildProfile = field(default_factory=BuildProfile)


@dataclass(frozen=True)
class Rule:
    """A registered validation rule."""

    id: str
    severity: Severity
    title: str
    func: Callable[[Context], Iterable[Finding]]
    source: str | None = None


_RULES: dict[str, Rule] = {}


def rule(
    id: str,
    severity: Severity,
    title: str,
    *,
    source: str | None = None,
) -> Callable[[Callable[[Context], Iterable[Finding]]], Callable[[Context], Iterable[Finding]]]:
    """Register a rule (decorator). Ids must be unique."""

    def deco(func: Callable[[Context], Iterable[Finding]]) -> Callable[[Context], Iterable[Finding]]:
        if id in _RULES:
            raise ValueError(f"duplicate rule id {id}")
        _RULES[id] = Rule(id, severity, title, func, source)
        return func

    return deco


def rules() -> list[Rule]:
    """All registered rules, sorted by id."""
    return [_RULES[k] for k in sorted(_RULES)]


def run_rules(ctx: Context, select: Iterable[str] | None = None) -> list[Issue]:
    """Run all (or the selected) rules and return their issues in rule order."""
    chosen = set(select) if select is not None else None
    out: list[Issue] = []
    for r in rules():
        if chosen is not None and r.id not in chosen:
            continue
        for f in r.func(ctx):
            msg, loc = (f, None) if isinstance(f, str) else f
            out.append(Issue(r.id, r.severity, msg, loc, None, r.source))
    return out
