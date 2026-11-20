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
#
# History
# 15.11.2026, J. Machacek - Initial version
# 19.11.2026, J. Machacek - Message of the water-filled gap told from the one of sliding=small with doublepass
# 20.11.2026, J. Machacek - Note on the entries of read_step_.f90 (checked in test_read_step_references.py)
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""numgeo-src working tree of 15.11.2026 and features of earlier commits which the catalogue did not have yet:

* pressure that varies linearly along a coordinate, ``*Dload HPi`` and ``*Dsload HP`` (catalogue, NG-LOAD-115);
* option ``water-filled gap`` of ``*Normal`` also with ``discretisation=IPS``, not with ``doublepass``
  (NG-CONT-128, NG-CONT-129);
* optional parameters ``TANGENT`` and ``E_MAX`` of Hardening-Soil-MN(-Bricks) and their automatic ``Ei``;
* ``*PFEM remeshing`` (numgeo-src ab1f76b; catalogue, NG-STEP-134);
* 3D u-J elements and the u-J quadrilaterals with a formulation;
* reader: only a line starting with ``*Include`` is an include, lines that are too long stop numgeo
  (numgeo-src aa15af6, 23530eb).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

import pynumgeo as ng
from conftest import small_deck
from pynumgeo import catalogue as cat
from pynumgeo.deck import Keyword
from pynumgeo.solver.messages import classify, rules_for_source


def _found(deck: ng.Deck, *rules: str) -> list[str]:
    return [i.message for i in ng.validate(deck) if i.id in rules]


# ------------------------------------------------------------------------------------------------ pressure HPi / HP
def _pressure_deck(keyword: str, row: list, options=("ramp",)) -> ng.Deck:
    d = small_deck()
    d.steps[0].add(keyword, options=list(options), data=[row])
    return d


def test_catalogue_linear_pressure_labels():
    types = cat.load().section("loads", "load_types")
    assert cat.load().section("loads", "counts")["load_types"] == len(types)
    hpi = next(t for t in types if t["keyword"] == "*DLOAD" and t["stored_label"] == "HPi")
    hp = next(t for t in types if t["keyword"] == "*DSLOAD" and t["stored_label"] == "HP")
    for entry in (hpi, hp):
        assert [p["name"] for p in entry["parameters"]] == ["coordinate", "p1", "c1", "p2", "c2"]
        assert "zero outside" in entry["notes"] and "read_hydrostatic_pressure" not in entry["restrictions"]
        assert "no USER, no SIDE" in entry["restrictions"]
    assert "always rejected" not in hpi["restrictions"]
    for page in ("docs/reference/boundary-conditions/dload.md", "docs/reference/boundary-conditions/dsload.md"):
        text = cat.load().doc_page(page)
        assert text is not None and "## Hydrostatic and triangular pressure" in text


@pytest.mark.parametrize(
    "keyword, row",
    [
        ("*Dsload", ["Wall", "HP", "Y", 0.0, 18.0, -180.0, 0.0]),
        ("*Dsload", ["Top", "hp", "x", 0.0, 2.0, -40.0, 6.0]),
        ("*Dload", ["Soil", "HP2", "2", 0.0, 1.0, -10.0, 0.0]),
        ("*Dload", ["Soil", "P2", -10.0]),  # other labels are not touched
    ],
)
def test_linear_pressure_accepted(keyword, row):
    assert _found(_pressure_deck(keyword, row), "NG-LOAD-115") == []


@pytest.mark.parametrize(
    "keyword, row, options, text",
    [
        ("*Dsload", ["Wall", "HP", 0.0, 18.0, -180.0, 0.0], ("ramp",), "needs 7 fields"),
        ("*Dsload", ["Wall", "HP", "Y", 0.0, 18.0, -180.0, 0.0, 1.0], ("ramp",), "needs 7 fields"),
        ("*Dload", ["Soil", "HP2", "W", 0.0, 1.0, -10.0, 0.0], ("ramp",), "coordinate along which the pressure varies"),
        ("*Dsload", ["Wall", "HP", "Z", 0.0, 18.0, -180.0, 0.0], ("ramp",), "which a 2D model does not have"),
        ("*Dsload", ["Wall", "HP", "Y", 0.0, 18.0, -180.0, 18.0], ("ramp",), "two different coordinates c1 and c2"),
        ("*Dsload", ["Wall", "HP", "Y", 0.0, "top", -180.0, 0.0], ("ramp",), "must be numbers"),
        ("*Dsload", ["Wall", "HP", "Y", 0.0, 18.0, -180.0, 0.0], ("user",), "not available as user load"),
        ("*Dload", ["Soil", "HP2", "Y", 0.0, 1.0, -10.0, 0.0], ("side=1", "ramp"), "not available as user load"),
    ],
)
def test_linear_pressure_rejected(keyword, row, options, text):
    found = _found(_pressure_deck(keyword, row, options), "NG-LOAD-115")
    assert any(text in m for m in found), found


def test_linear_pressure_messages():
    m = classify(
        "*DSLOAD definition in step EXCAVATION: the pressure HP needs two different coordinates c1 and c2 "
        "(set_name, HP, coordinate, p1, c1, p2, c2).",
        "error",
    )
    assert m is not None and m.message_id.startswith("src/input/read_dload_.f90:")
    assert "NG-LOAD-115" in rules_for_source(m.file, m.line)
    assert classify("*DLOAD statement in step LOAD: hydrostatic pressure is not yet available", "error") is None


# ------------------------------------------------------------------------------------------------ water-filled gap
def _gap_deck(pair_options, normal=("mechanical=penalty", "water-filled gap"), model: str | None = "Coulomb"):
    d = small_deck()
    children = [Keyword.make("*Normal", options=list(normal), data=[[1.0e6]])]
    if model:
        children.append(Keyword.make("*Friction", options=[("model", model)], data=[[1.0e6, 0.3, 0.0]]))
    d.keywords.append(Keyword.make("*Interaction", options=[("name", "Gap")], children=children))
    d.keywords.append(
        Keyword.make("*Contact pair", options=[("interaction", "Gap"), *pair_options], data=[["SoilFace", "WallFace"]])
    )
    return d


def test_catalogue_water_filled_gap():
    option = cat.keyword("*Normal").option("WATER-FILLEDGAP")
    assert option is not None and "IPS, element mortar or NTN" in option.notes and "DOUBLEPASS" in option.notes
    double = cat.keyword("*Contact pair").option("doublepass")
    assert double is not None and "water-filled gap" in double.notes
    page = cat.load().doc_page("docs/reference/contacts/interaction.md")
    assert page is not None and "[water-filled gap]" in page and "`IPS`" in page


@pytest.mark.parametrize("pair", [("discretisation=IPS",), ("discretisation=element mortar",), ("discretisation=NTN",),
                                  ("discretisation=IPS", "nigp=3", "gap=activation")])  # fmt: skip
def test_water_filled_gap_accepted(pair):
    assert _found(_gap_deck(pair), "NG-CONT-128", "NG-CONT-129") == []
    assert _found(_gap_deck(pair, model=None), "NG-CONT-128", "NG-CONT-129") == []
    assert _found(_gap_deck(pair, model="Mohr-Coulomb"), "NG-CONT-129") == []


def test_water_filled_gap_rejected():
    found = _found(_gap_deck(("discretisation=IPS", "doublepass")), "NG-CONT-129")
    assert len(found) == 1 and "not available with doublepass" in found[0]
    found = _found(_gap_deck(("discretisation=segment mortar",)), "NG-CONT-129")
    assert len(found) == 1 and "IPS, element mortar and NTN only" in found[0]
    found = _found(_gap_deck(("discretisation=IPS",), model="some-other-model"), "NG-CONT-129")
    assert len(found) == 1 and "frictionless contact and the friction models Coulomb and Mohr-Coulomb" in found[0]
    found = _found(_gap_deck(("discretisation=IPS",), normal=("mechanical=augmented_lagrange", "water-filled gap")),
                   "NG-CONT-128")  # fmt: skip
    assert len(found) == 1 and "requires mechanical=penalty" in found[0]
    # without the option the double pass and other normal models are not touched
    assert _found(_gap_deck(("discretisation=IPS", "doublepass"), normal=("mechanical=penalty",)), "NG-CONT-129") == []


def test_water_filled_gap_messages():
    m = classify(
        "The option water-filled gap of interaction GAP is not available with the option doublepass of *Contact pair.",
        "error",
    )
    assert m is not None and m.message_id.startswith("src/input/read_contact_pairing_.f90:")
    assert "NG-CONT-129" in rules_for_source(m.file, m.line)
    m = classify(
        "The option water-filled gap of interaction GAP is available for the discretisations IPS, element mortar "
        "and NTN only.",
        "error",
    )
    assert m is not None


# ------------------------------------------------------------------------------------------- Hardening-Soil-MN
@pytest.mark.parametrize("model, nprops", [("hardening-soil-mn", 14), ("hardening-soil-mn-bricks", 16)])
def test_hardening_soil_optional_parameters(model, nprops):
    spec = cat.material_model(model)
    assert [o["name"] for o in spec.optional_parameters] == ["MIN_PRESSURE", "TANGENT", "E_MAX"]
    assert [o["default"] for o in spec.optional_parameters] == ["1.0e-1", "1.0", "0.0"]
    assert "Ei if props(12) <= 1e-6" in spec.notes
    d = small_deck()
    m = d.materials[0]
    m.set_mechanical(model, [4.0e4] * nprops)
    m.add("*Optional mechanical parameter", data=[["TANGENT", 2], ["E_MAX", 0.9]])
    assert _found(d, "NG-MAT-115") == []
    d = small_deck()
    d.materials[0].set_mechanical(model, [4.0e4] * nprops)
    d.materials[0].add("*Optional mechanical parameter", data=[["TANGENT", 2], ["E_MIN", 0.5]])
    found = _found(d, "NG-MAT-115")
    assert len(found) == 1 and "'E_MIN' is not an optional parameter" in found[0] and "tangent, e_max" in found[0]


def test_hardening_soil_messages():
    m = classify(
        "Hardening-Soil-MN model determined internal constants using optimisation process: Eiref = 47500.0, "
        "alpha = 0.8, Hpp = 3500.0.",
        "warning",
    )
    assert m is not None and m.message_id.startswith("src/input/read_material_.f90:")
    text = "HARDENING-SOIL-MN: the optional parameter TANGENT must be 1 (elastic) or 2 (consistent)."
    assert classify(text) is not None


# ---------------------------------------------------------------------------------------------- *PFEM remeshing
def _pfem_deck(*options, write: bool = True, procedure: str = "*Static", second: bool = True, items=()) -> ng.Deck:
    d = small_deck()
    st = ng.Step(name="Penetration", procedure=Keyword.make(procedure, data=[[0.1, 1.0, 1e-5, 0.5]]))
    st.add("*Boundary", data=[["Base", "u1", 0.0], ["Base", "u2", 0.0]])
    if options:
        st.add("*PFEM remeshing", options=list(options))
    if write:
        st.add("*PFEM write")
    for kw in items:
        st.items.append(kw)
    if second:
        d.steps.append(st)
    else:
        d.steps[0] = st
    return d


def test_catalogue_pfem_remeshing():
    spec = cat.keyword("*PFEM remeshing", "step")
    assert [o.name for o in spec.options] == [
        "INTERVAL", "EXACT", "ENDOFSTEP", "INCREMENTS", "QUALITY", "DROP", "LIMIT", "ELSET", "MININTERVAL",
        "MININCREMENTS",
    ]  # fmt: skip
    assert spec.option("QUALITY").values == ("SCALEDJACOBIAN", "EDGERATIO", "MINANGLE")
    assert spec.option("MININCREMENTS").default == 1 and "ab1f76b" in spec.notes


@pytest.mark.parametrize(
    "options",
    [
        ("interval=0.05",),
        ("interval=0.05", "exact=yes", "min increments=2"),
        ("increments=20", "end of step=yes"),
        ("quality=scaled jacobian", "drop=0.3", "limit=0.2", "elset=Soil", "min interval=0.01"),
    ],
)
def test_pfem_remeshing_accepted(options):
    d = _pfem_deck(*options)
    assert _found(d, "NG-STEP-134") == []
    assert [i for i in ng.validate(d) if i.id.startswith("NG-KW") and "PFEM" in i.message] == []


@pytest.mark.parametrize(
    "kwargs, options, text",
    [
        ({}, ("min increments=2",), "needs at least one criterion"),
        ({}, ("quality=min angle",), "needs drop= and/or limit="),
        ({}, ("interval=0.1", "drop=0.2"), "without the criterion quality="),
        ({}, ("increments=5", "exact=yes"), "exact without the criterion interval="),
        ({}, ("interval=0.1", "min interval=0.2"), "min interval larger than the interval"),
        ({}, ("increments=5", "min increments=6"), "min increments larger than increments"),
        ({}, ("interval=-0.1",), "invalid value of interval"),
        ({}, ("increments=2.5",), "invalid value of increments"),
        ({}, ("quality=aspect", "drop=0.1"), "unknown quality measure"),
        ({}, ("quality=edge ratio", "limit=3", "elset=Nowhere"), "unknown element set Nowhere"),
        ({"write": False}, ("interval=0.1",), "requires *PFEM write in the same step"),
        ({"second": False}, ("interval=0.1",), "not possible in the first step"),
        ({"procedure": "*Geostatic"}, ("interval=0.1",), "only available for steps of type static"),
    ],
)
def test_pfem_remeshing_rejected(kwargs, options, text):
    found = _found(_pfem_deck(*options, **kwargs), "NG-STEP-134")
    assert any(text in m for m in found), found


def test_pfem_remeshing_with_model_change_and_unknown_option():
    change = Keyword.make("*Model change", options=["remove"], data=[["Soil"]])
    found = _found(_pfem_deck("interval=0.1", items=[change]), "NG-STEP-134")
    assert any("cannot be combined with *Model change" in m for m in found)
    issues = [i for i in ng.validate(_pfem_deck("interval=0.1", "frequency=2")) if i.id.startswith("NG-KW")]
    assert any("frequency" in i.message.lower() for i in issues), issues
    m = classify("The *PFEM REMESHING command in step PUSH requires at least one criterion: INTERVAL, INCREMENTS or "
                 "QUALITY.", "error")  # fmt: skip
    assert m is not None and m.message_id.startswith("src/input/read_step_.f90:")


# -------------------------------------------------------------------------------------------------- u-J elements
def test_catalogue_uj_elements():
    c = cat.load()
    new = ("U4J4-SOLID-3D", "U4J4-SOLID-MINI-3D", "U10J4-SOLID-3D", "U8J8-SOLID-3D", "U20J8-SOLID-3D", "U27J8-SOLID-3D")
    for name in new:
        e = c.element_type(name)
        assert e.ndim == 3 and tuple(e.dofs) == ("U1", "U2", "U3", "JJ")
    assert (c.element_type("u20j8-solid-3d").nnodes, c.element_type("u10j4-solid-3d").nnodes) == (20, 10)
    count = c.section("model", "element_types_count")
    assert count["library"] == len(c.element_types) and count["accepted_names"] == count["library"] + count["aliases"]
    assert count["without_element_master_case"] == ["U4PMEAN4-SOLID", "U4PMEAN4-SOLID-AX"]
    d = ng.Deck()
    d.mesh.add_nodes([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
    d.mesh.add_elements("u8j8-solid-3d", [[1, 2, 3, 4, 5, 6, 7, 8]])
    assert [i for i in ng.validate(d) if "u8j8" in i.message.lower() and i.severity == "error"] == []


# -------------------------------------------------------------------------------------------------------- reader
def test_only_a_line_starting_with_include_is_an_include():
    text = "*Node\n1, 0., 0.\n2, 1., 0.\n*Nset, nset=IncludedNodes\n1, 2\n"
    result = ng.parse_text(text)  # no include file needed: the set name is not an include
    assert result.deck.mesh.nset("IncludedNodes").members.tolist() == [1, 2]
    assert [i.id for i in result.issues if "INCLUDE" in i.id.upper()] == []
    main = "  *include, input = mesh\n*Nset, nset=All\n1, 2\n"
    deck = ng.parse_text(main, includes={"mesh": "*Node\n1, 0., 0.\n2, 1., 0.\n"}).deck
    assert deck.mesh.node_count == 2
    with pytest.raises(FileNotFoundError):
        ng.parse_text(main, includes={})
    assert "INCLUDE" not in "".join(w for words in ng.deck.names.RISKY_WORDS.values() for w in words)


def test_lines_that_are_too_long_stop_numgeo():
    members = ", ".join(str(i) for i in range(1, 61))
    assert len(members.replace(" ", "")) <= 256 < len(members) + 60
    padded = "*Node\n1, 0., 0.\n2, 1., 0.\n*Nset, nset=A\n" + members.replace(", ", ",      ") + "\n"
    assert [i.id for i in ng.parse_text(padded).issues if "TOO-LONG" in i.id] == []  # blanks do not count
    long_line = ", ".join(str(i) for i in range(1, 120))
    head = "*Node\n1, 0., 0.\n*Nset, nset=A\n"
    issues = [i for i in ng.parse_text(head + long_line + "\n").issues if "TOO-LONG" in i.id]
    assert [(i.id, i.severity) for i in issues] == [("NG-READ-INPUT-LINE-TOO-LONG", "error")]
    assert "maximum is 256" in issues[0].message
    issues = [i for i in ng.parse_text(head + "1," + " " * 1021 + "1\n").issues if "LINE-" in i.id]  # 1024 characters
    assert [(i.id, i.severity) for i in issues] == [("NG-READ-INPUT-LINE-TOO-LONG", "error")]
    assert "at least 1024 characters" in issues[0].message
    assert [i for i in ng.parse_text(head + "1," + " " * 1020 + "1\n").issues if "LINE-" in i.id] == []  # 1023
    # the 1024th character is a blank: numgeo has no message and does not read the node behind it
    result = ng.parse_text(head + "1," + " " * 1100 + "1\n")
    issues = [i for i in result.issues if "LINE-" in i.id]
    assert [(i.id, i.severity) for i in issues] == [("NG-READ-INPUT-LINE-CUT", "warning")]
    assert result.deck.mesh.nset("A").members.tolist() == [1]
    comment = head + "1 ** " + "x" * 1100 + "\n"
    assert [i for i in ng.parse_text(comment).issues if "LINE-" in i.id] == []  # the rest is part of the comment
    assert [i for i in ng.parse_text(head + "1" + " " * 1100 + "** note\n").issues if "LINE-" in i.id] == []
    assert classify("An input line has 300 characters without blanks and comments, the maximum is 256. Split the data "
                    "over several lines. The line starts with: 1,2,3", "error") is not None  # fmt: skip


# ------------------------------------------------------------------------------------------------- source anchors
@pytest.mark.skipif(not os.environ.get("NUMGEO_SRC"), reason="set NUMGEO_SRC")
@pytest.mark.source
def test_catalogue_anchors_match_the_source():
    """The entries of this update cite lines of the numgeo-src working tree of 15.11.2026: their anchors must match
    it. (Entries of other files taken over from the catalogue commit keep the lines of that commit and are not checked
    here; all entries of read_step_.f90 are checked in test_read_step_references.py.)"""
    root = Path(os.environ["NUMGEO_SRC"])
    c = cat.load()
    spec = cat.keyword("*PFEM remeshing", "step")
    entries = [spec.raw["dispatch"], spec.raw["handler"]]
    entries += [o[k] for o in spec.raw["options"] for k in ("source", "default_source") if o.get(k)]
    for model in ("hardening-soil-mn", "hardening-soil-mn-bricks"):
        entries += [o["default_source"] for o in cat.material_model(model).optional_parameters]
    new = {
        "src/input/read_dload_.f90": ("the pressure",),
        "src/input/read_contact_pairing_.f90": ("IPS, element mortar and NTN only", "with the option doublepass of"),
        "src/input/read_step_.f90": ("PFEM REMESHING",),
        "src/input/read_material_.f90": ("optimisation process: Eiref",),
        "src/input/input_create_internal_input_.f90": ("An input line has",),
        "src/materials/material_library.f90": ("optional parameter TANGENT", "E_MAX"),
        "src/fem/fem_global_model_change_elements_.f90": ("the element force of element", "order of the element forces"),
    }
    messages = [m for m in c.messages() if m["template"] and any(t in m["template"] for t in new.get(m["file"], ()))]
    assert len(messages) == 38
    entries += messages
    for e in entries:
        line = (root / e["file"]).read_text(encoding="latin-1").splitlines()[e["line"] - 1]
        assert hashlib.sha256(line.strip().encode()).hexdigest()[:16] == e["anchor"], e
