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
"""ng.diff: where two decks differ as numgeo reads them."""

from __future__ import annotations

import copy

import pynumgeo as ng
from conftest import DATA
from pynumgeo.deck import Keyword


def test_identical_and_respelled_decks_have_no_difference(deck):
    assert ng.diff(deck, deck) == []
    assert ng.diff(deck, ng.parse_text(ng.write_text(deck).upper()).deck) == []


def test_each_kind_of_change_is_named(deck):
    other = copy.deepcopy(deck)
    other.mesh.coords[2, 0] += 1e-3
    other.materials[0].properties[1] = Keyword.make("*Density", data=[[2.1]])
    other.steps[0].items[1].options.append(("AMPLITUDE", "Ramp"))
    other.mesh.nsets[1].members[0] = 1
    lines = ng.diff(deck, other)
    assert any(ln.startswith("mesh: coordinates differ") for ln in lines)
    assert any("material Sand" in ln and "*DENSITY" in ln for ln in lines)
    assert any("*CLOAD: options" in ln for ln in lines)
    assert "mesh: node set Top differs" in lines
    assert len(lines) == 4


def test_tolerance_applies_to_reals_and_coordinates(deck):
    other = copy.deepcopy(deck)
    other.mesh.coords[1, 0] *= 1 + 1e-12
    other.steps[0].items[1].data[0][2] = -1.0 * (1 + 1e-12)
    assert len(ng.diff(deck, other)) == 2
    assert ng.diff(deck, other, rtol=1e-9) == []


def test_gid_layout_of_plugin_decks_equals_its_rewrite():
    for calc in sorted((DATA / "plugin-decks").glob("*/*-calculation.inp")):
        d = ng.parse(calc).deck
        assert ng.diff(d, ng.parse_text(ng.write_text(d)).deck) == []
