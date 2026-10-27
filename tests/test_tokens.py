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
"""Tokens given as text are the tokens numgeo reads; options and values compare by value."""

from __future__ import annotations

import pynumgeo as ng
from pynumgeo.deck import Amplitude, Keyword


def test_numeric_text_tokens_become_numbers():
    kw = Keyword.make("*Density", data=[["2.0", " 3 ", "1d-3", "Fix", "u1"]])
    assert kw.data == [[2.0, 3, 0.001, "Fix", "u1"]]
    assert isinstance(kw.data[0][1], int)


def test_numeric_text_tokens_on_assignment_and_amplitudes():
    kw = Keyword.make("*Density")
    kw.data = [["2.5"]]
    assert kw.data == [[2.5]]
    a = Amplitude(name="Ramp", type="tabular", data=[["0", "0.0"], ["1.0", "1"]])
    assert a.data == [[0, 0.0], [1.0, 1]]


def test_deck_built_from_text_tokens_round_trips(deck):
    deck.materials[0].properties[1] = Keyword.make("*Density", data=[["2.0"]])
    deck.steps[0].items[1] = Keyword.make("*Cload", options=["ramp"], data=[["Top", "2", "-1.0"]])
    back = ng.parse_text(ng.write_text(deck)).deck
    assert back == deck


def test_options_and_values_compare_by_value():
    a = Keyword.make("*Output", options=["field", ("frequency", "1")])
    b = Keyword.make("*Output", options=["FIELD", ("frequency", "1.0")])
    assert a == b
    assert Keyword.make("*Hilber-Hughes-Taylor", value="-0.1") == Keyword.make("*Hilber-Hughes-Taylor", value="-1d-1")
    assert Keyword.make("*Output", options=[("frequency", "1")]) != Keyword.make(
        "*Output", options=[("frequency", "2")]
    )
    assert Keyword.make("*Mechanical", value="mohr-coulomb") == Keyword.make("*Mechanical", value="MOHR-COULOMB")


def test_booleans_stay_refused():
    import pytest

    with pytest.raises(Exception, match="boolean"):
        Keyword.make("*Density", data=[[True]])
