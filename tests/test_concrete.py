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
"""*Mechanical = Concrete (numgeo-src working tree of 30./31.10.2026): catalogue entry, number of parameters, the
optional parameter VISCOSITY, state variables, messages and the bundled reference page."""

from __future__ import annotations

import pytest

import pynumgeo as ng
from conftest import small_deck
from pynumgeo import catalogue as cat
from pynumgeo.solver.messages import classify

# grout of the grouted-anchor example (examples/grouted_anchor_casing_concrete.py of numgeo-FreeCAD)
GROUT = [1.5e7, 0.2, 35.0e3, 2.5e3, 37.0, 0.0, 0.15, 0.1, 0.1, 30.0, -1.0e-3, 16.0, 0.0, 0.022]


def _deck(values=GROUT, optional=None) -> ng.Deck:
    d = small_deck()
    m = d.materials[0]
    m.properties = [p for p in m.properties if p.keyword != "*MECHANICAL"]
    m.set_mechanical("concrete", list(values))
    if optional is not None:
        m.add("*Optional mechanical parameter", data=[list(r) for r in optional])
    return d


def _ids(deck: ng.Deck, prefix: str = "NG-MAT-") -> list[str]:
    return [i.id for i in ng.validate(deck) if i.id.startswith(prefix)]


def test_catalogue_entry():
    spec = cat.load().material_model("Concrete")
    assert spec.name == "CONCRETE" and spec.nprops == 14 and spec.nstatev == 14 and spec.public
    assert [p.name for p in spec.parameters][:6] == ["E", "nu", "f_c", "f_t", "phi_max", "psi"]
    assert [p.unit for p in spec.parameters][9::4] == ["F/L", "F/L"]
    assert [o["name"] for o in spec.optional_parameters] == ["VISCOSITY"]
    assert [s["statev_index"] for s in spec.raw["statev_names"]] == list(range(1, 15))
    names = [s["name"] for s in spec.raw["statev_names"]]
    assert names[:8] == ["EPS-PL-C", "EPS-PL-T", "H-C", "H-T", "F-CY", "F-TY", "L-EQ", "YIELD-MODE"]
    assert names[8:] == ["Q11", "Q22", "Q33", "Q12", "Q13", "Q23"]
    page = cat.load().doc_page(spec.doc)
    assert page is not None and page.startswith("# Concrete")


def test_concrete_is_accepted():
    assert _ids(_deck()) == []


def test_number_of_parameters():
    with pytest.raises(ValueError, match="CONCRETE needs exactly 14 parameters, got 13"):
        _deck(GROUT[:13])
    d = _deck()
    p = d.materials[0].property("*Mechanical")
    assert p is not None
    p.data[-1] = p.data[-1][:-1]  # a deck read from a file with a missing value
    found = [i for i in ng.validate(d) if i.id == "NG-MAT-001"]
    assert len(found) == 1 and "concrete needs 14 parameters, 13 given" in found[0].message


def test_optional_viscosity():
    assert _ids(_deck(optional=[["viscosity", 0.001]])) == []
    found = [i for i in ng.validate(_deck(optional=[["tol_yield", 1.0e-4]])) if i.id == "NG-MAT-115"]
    assert len(found) == 1 and "known: viscosity" in found[0].message


def test_written_and_read_back():
    text = ng.write_text(_deck())
    back = ng.parse_text(text).deck
    p = back.materials[0].property("*Mechanical")
    assert p is not None and (p.value or "").upper() == "CONCRETE"
    assert [float(t) for r in p.data for t in r] == GROUT
    assert _ids(back) == []


def test_numgeo_messages_of_the_model():
    m = classify("Concrete model in material GROUT: the tensile fracture energy G_t (p14) must be positive.", "error")
    assert m is not None and m.file == "src/materials/models/material_concrete_.f90" and m.terminates
    m = classify(
        "Concrete model, element 12: the equivalent length Leq = 0.5 is not smaller than the limit 2 min(E,K) G_t / "
        "((1 - f_tun^2) f_t^2) = 0.1 of the tension softening (snap-back on the stress-point level). Refine the mesh "
        "or increase G_t.",
        "error",
    )
    assert m is not None and m.routine == "concrete"
