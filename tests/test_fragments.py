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
"""Fragments: keyword lines typed for a model, a step or a material; rendering for previews."""

from __future__ import annotations

import pytest

import pynumgeo as ng
from pynumgeo.deck import Keyword
from pynumgeo.io.reader import parse_fragment
from pynumgeo.io.writer import format_keyword, format_material


def test_step_fragment_groups_like_the_reader():
    text = (
        "** user lines\n*Controls, u, modify\n1e-3, 1e-3, 1e-2, 1e-5, 1e-6, 1.0\n"
        "*Output, print\n*Frequency = 2\n*Node output, nset=Top\nU\n"
    )
    r = parse_fragment(text, "step")
    assert r.ok
    assert [k.keyword for k in r.keywords] == ["*CONTROLS", "*OUTPUT"]
    assert [c.keyword for c in r.keywords[1].children] == ["*FREQUENCY", "*NODEOUTPUT"]
    full = ng.parse_text(
        "*Node\n1,0,0\n2,1,0\n*Element,type=u2-truss\n1,1,2\n*Nset,nset=Top\n2\n*Step,name=S\n*Static\n1,1,1,1\n"
        + text
        + "*End step\n"
    ).deck
    assert full.steps[0].items == r.keywords


def test_material_fragment():
    r = parse_fragment("*Damping\n0.1, 0.002\n*Min pressure\n1.0", "material")
    assert r.ok and [k.keyword for k in r.keywords] == ["*DAMPING", "*MINPRESSURE"]
    bad = parse_fragment("*Boundary\nFix, u1, 0", "material")
    assert not bad.ok and bad.keywords == []


def test_fragment_refuses_containers_and_unknown_keywords():
    assert not parse_fragment("*Step, name=X\n*Static\n1,1,1,1\n*End step", "step").ok
    r = parse_fragment("*Bondary\nFix, u1, 0", "step")
    assert not r.ok and r.issues[0].id == "NG-READ-INPUT-001"
    with pytest.raises(ValueError):
        parse_fragment("", "part")


def test_model_fragment_defines_sets_amplitudes_and_keywords():
    r = parse_fragment(
        "*Amplitude, name=Load, type=tabular\n0, 0, 1, 1\n*Initial conditions, type=temperature\nAll, 293.15", "model"
    )
    assert r.ok
    assert [a.name for a in r.deck.amplitudes] == ["Load"]
    assert [k.keyword for k in r.keywords] == ["*INITIALCONDITIONS"]


def test_format_keyword_and_material():
    kw = Keyword.make("*Boundary", data=[["Fix", "U1", 0.0]], comment="support")
    assert format_keyword(kw, names={"Fix"}) == "** support\n*Boundary\nFix, u1, 0.0\n"
    m = ng.Material(name="Sand", phases=1)
    m.set_mechanical("mohr-coulomb", [1e5, 0.3, 1.0, 0.5, 0.0, 29.0])
    text = format_material(m)
    assert text.splitlines()[0] == "*Material, name=Sand, phases=1"
    assert "*Mechanical=mohr-coulomb" in text
