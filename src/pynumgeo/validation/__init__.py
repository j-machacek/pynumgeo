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
"""Validation of a deck against what numgeo accepts.

Examples:
    >>> from pynumgeo.deck import Deck
    >>> d = Deck()
    >>> _ = d.mesh.add_nodes([[0, 0], [1, 0]], labels=[1, 3]); _ = d.mesh.add_elements("u2-truss", [[1, 3]])
    >>> [i.id for i in validate(d)]
    ['NG-MESH-001', 'NG-MESH-008']
"""

from __future__ import annotations

from collections.abc import Iterable

from pynumgeo import catalogue as _cat
from pynumgeo.deck.deck import Deck
from pynumgeo.validation import rules as _rules  # noqa: F401  (registers the rules)
from pynumgeo.validation.engine import BuildProfile, Context, Rule, rule, rules
from pynumgeo.validation.issue import Issue, has_errors

__all__ = ["BuildProfile", "Issue", "Rule", "has_errors", "rule", "rules", "validate"]


def validate(deck: Deck, *, profile: BuildProfile | None = None, select: Iterable[str] | None = None) -> list[Issue]:
    """Check ``deck`` and return the issues (errors first, then warnings and infos, each in rule order).

    Args:
        deck: the deck to check.
        profile: numgeo build the deck is meant for (default: the current developer build).
        select: only these rule ids.
    """
    from pynumgeo.validation.engine import run_rules

    ctx = Context(deck=deck, catalogue=_cat.load(), profile=profile or BuildProfile.full())
    issues = run_rules(ctx, select)
    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(issues, key=lambda i: order[i.severity])
