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
"""Validation rules whose conditions depend on the mesh (checked against the numgeo source they cite)."""

from __future__ import annotations

import pynumgeo as ng
from conftest import small_deck
from pynumgeo.deck import Keyword


def _two_elements() -> ng.Deck:
    d = small_deck()
    d.mesh.add_nodes([[2.0, 0.0], [2.0, 1.0]])
    d.mesh.add_elements("u4-solid", [[2, 5, 6, 3]])
    d.mesh.add_elset("Lower", [2])
    d.mesh.add_elset("All", [1, 2])
    return d


def _state(sets_values, sub=None):
    options = [("type", "state variables")] + ([sub] if sub else [])
    return Keyword.make("*Initial conditions", options=options, data=[list(r) for r in sets_values])


def _ids(deck, rule):
    return [i for i in ng.validate(deck) if i.id == rule]


def test_fluctuation_before_default_on_other_elements_is_accepted():
    # numgeo passes over a block whose sets do not hold the element (initial_state_variables_.f90:90-102)
    d = _two_elements()
    d.keywords += [
        _state([["Soil", "void_ratio", 0.8, 0.6, 2.0]], "fluctuation"),
        _state([["Lower", "void_ratio", 0.7]]),
    ]
    assert _ids(d, "NG-IC-108") == []


def test_fluctuation_before_default_on_shared_elements_is_an_error():
    d = _two_elements()
    d.keywords += [_state([["Soil", "void_ratio", 0.8, 0.6, 2.0]], "fluctuation"), _state([["All", "alpha", 0.1]])]
    found = _ids(d, "NG-IC-108")
    assert len(found) == 1 and found[0].severity == "error" and "Soil" in found[0].message


def test_data_blocks_after_a_fluctuation_block_are_accepted():
    # *-DATA blocks are applied outside the integration-point loop (fem_global_assemble_elements_.f90:294-306)
    d = _two_elements()
    d.keywords += [
        _state([["Soil", "void_ratio", 0.8, 0.6, 2.0]], "fluctuation"),
        _state([["All", "alpha", "alpha.txt"]], "x-data"),
    ]
    assert _ids(d, "NG-IC-108") == []


def test_fluctuation_last_is_accepted():
    d = _two_elements()
    d.keywords += [_state([["All", "alpha", 0.1]]), _state([["Soil", "void_ratio", 0.8, 0.6, 2.0]], "fluctuation")]
    assert _ids(d, "NG-IC-108") == []
