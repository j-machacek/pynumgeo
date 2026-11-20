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
# 19.11.2026, J. Machacek - Initial version
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""numgeo-src 1f48283 (19.11.2026): small sliding of contact pairs with ``discretisation=IPS``.

* ``sliding=small`` of ``*Contact pair`` also with ``IPS``, not with ``doublepass`` or ``general`` (catalogue,
  NG-CONT-130);
* ``*Model change, contact pair, sliding=small`` with data lines ``slave surface, master surface`` (catalogue,
  NG-CONT-131, repeated selection NG-CONT-134);
* not in a step with ``*PFEM remeshing`` (NG-CONT-132); a face in the slave surfaces of several IPS surface pairs
  needs one sliding formulation (NG-CONT-133);
* source lines of ``read_contact_pairing_.f90``, ``read_model_change_.f90`` and of the messages of ``contact_.f90``.
"""

from __future__ import annotations

import hashlib
import os
from importlib import resources
from pathlib import Path

import numpy as np
import pytest

import pynumgeo as ng
from conftest import small_deck
from pynumgeo import catalogue as cat
from pynumgeo.deck import Keyword
from pynumgeo.solver.messages import classify, rules_for_source

RULES = ("NG-CONT-130", "NG-CONT-131", "NG-CONT-132", "NG-CONT-133", "NG-CONT-134")
GENERIC = ("NG-KW-010", "NG-KW-011", "NG-KW-012", "NG-KW-013")
SMALL = ["contact pair", ("sliding", "small")]


def _doc(spec: cat.KeywordSpec, option: str) -> str | None:
    """Reference page of an option of a keyword."""
    return next(o for o in spec.raw["options"] if o["name"] == option)["doc"]


def _found(deck: ng.Deck, *rules: str) -> list[str]:
    return [i.message for i in ng.validate(deck) if i.id in rules]


def _ids(deck: ng.Deck, *rules: str) -> list[str]:
    return sorted({i.id for i in ng.validate(deck) if i.id in rules})


def _pair(slave: str, master: str, *options, discretisation: str = "IPS") -> Keyword:
    return Keyword.make(
        "*Contact pair",
        options=[("interaction", "Friction"), ("discretisation", discretisation), *options],
        data=[[slave, master]],
    )


def _deck(*pairs: Keyword, steps: int = 2) -> ng.Deck:
    """The small deck with four surfaces on its element, an interaction, contact pairs and ``steps`` steps."""
    d = small_deck()
    d.mesh.add_elset("Part", [1])
    for name, elset, face in (
        ("BlockA", "Soil", "S1"),
        ("SupportA", "Soil", "S3"),
        ("BlockB", "Soil", "S2"),
        ("SupportB", "Soil", "S4"),
        ("BlockAPart", "Part", "S1"),  # the face of BlockA
        ("SupportC", "Part", "S3"),
    ):
        d.mesh.add_surface(name, [(elset, face)])
    d.keywords.append(
        Keyword.make(
            "*Interaction",
            options=[("name", "Friction")],
            children=[
                Keyword.make("*Normal", options=["mechanical=penalty"], data=[[1.0e6]]),
                Keyword.make("*Friction", options=[("model", "Coulomb")], data=[[1.0e5, 0.3, 0.0]]),
            ],
        )
    )
    d.keywords.extend(pairs or (_pair("BlockA", "SupportA"), _pair("BlockB", "SupportB")))
    for name in ("Place", "Slide", "Reduce")[: steps - 1]:
        st = ng.Step(name=name, procedure=Keyword.make("*Static", data=[[0.1, 1.0, 1e-5, 0.5]]))
        st.add("*Boundary", data=[["Base", "u1", 0.0], ["Base", "u2", 0.0]])
        d.steps.append(st)
    return d


def _change(d: ng.Deck, rows, step: int = -1, options=SMALL) -> ng.Deck:
    d.steps[step].add("*Model change", options=list(options), data=[list(r) for r in rows])
    return d


# ------------------------------------------------------------------------------------------------------ catalogue
def test_catalogue_small_sliding_of_contact_pair():
    spec = cat.keyword("*Contact pair")
    sliding = spec.option("sliding")
    assert sliding is not None and sliding.values == ("SMALL", "FINITE") and sliding.default == "FINITE"
    assert (
        "for IPS" in sliding.notes and "DOUBLEPASS or GENERAL" in sliding.notes and "*PFEM remeshing" in sliding.notes
    )
    assert "SLIDING=SMALL" in spec.option("doublepass").notes and "SLIDING=SMALL" in spec.option("general").notes
    page = cat.load().doc_page(_doc(spec, "SLIDING"))
    assert page is not None and "### Small sliding with IPS" in page and "### Small sliding with element mortar" in page
    assert "[`*Model change, contact pair, sliding=small`](../model-change/contact-pair.md)" in page


def test_catalogue_model_change_contact_pair():
    spec = cat.keyword("*Model change", "step")
    pair, sliding = spec.option("contactpair"), spec.option("sliding")
    assert pair is not None and pair.value_type == "flag" and "checked first" in pair.match
    assert sliding is not None and sliding.value_type == "enum" and sliding.values == ("SMALL",)
    assert not pair.required and not sliding.required and "SLIDING=FINITE -> error" in sliding.notes
    line = spec.raw["data_lines"][-1]
    assert [f["name"] for f in line["fields"]] == ["slave_surface", "master_surface"] and line[
        "count_rule"
    ] == "narg == 2"
    assert line["description"].startswith("CONTACTPAIR:")
    assert "apply_contact_pair_sliding" in spec.notes and "1f48283" in spec.notes
    page = cat.load().doc_page(_doc(spec, "CONTACTPAIR"))
    assert page is not None and page.startswith("# Change a contact pair to small sliding")
    assert "*Model change, contact pair, sliding=small" in page and "## Restart" in page
    index = cat.load().doc_page(spec.doc)
    assert index is not None and "[Contact pair](./contact-pair.md)" in index
    restart = cat.load().doc_page("docs/reference/restart.md")
    assert restart is not None and "model-change/contact-pair.md#restart" in restart
    assert "small sliding" in restart and "_ips_contact_step_<n>.dat" in restart
    assert "small sliding" in cat.keyword("*PFEM remeshing", "step").notes
    described = cat.describe("*Model change")
    assert "CONTACTPAIR" in described and "# Model change" in described


def _reference_deck() -> str:
    """The input file of the example of the bundled page docs/reference/model-change/contact-pair.md."""
    data = resources.files("pynumgeo.catalogue").joinpath("data", "docs", "reference", "model-change", "assets")
    return data.joinpath("small-sliding-staged.inp").read_text(encoding="utf-8")


def test_reference_deck_of_the_bundled_page():
    page = cat.load().doc_page("docs/reference/model-change/contact-pair.md")
    assert page is not None and "(assets/small-sliding-staged.inp)" in page
    result = ng.parse_text(_reference_deck(), name="small-sliding-staged.inp")
    assert [i for i in result.issues if i.severity == "error"] == []
    found = [i for i in ng.validate(result.deck) if i.severity in ("error", "warning")]
    assert found == []
    change = result.deck.steps[3].items[1]
    assert change.keyword == "*MODELCHANGE" and [o for o, _ in change.options] == ["CONTACTPAIR", "SLIDING"]
    assert [[str(t) for t in r] for r in change.data] == [
        ["BLOCK_A_SURFACE", "SUPPORT_A"],
        ["BLOCK_B_SURFACE", "SUPPORT_B"],
    ]


# ----------------------------------------------------------------------------- sliding=small of *Contact pair
@pytest.mark.parametrize(
    "options, discretisation",
    [
        (("sliding=small",), "IPS"),
        (("sliding=small", "gap=activation", "nigp=3", "adjust"), "IPS"),
        (("sliding=small",), "integration-point-surface"),
        (("sliding=small",), "element mortar"),
        (("sliding=finite", "doublepass"), "IPS"),
        (("doublepass", "sliding=small", "sliding=finite"), "IPS"),  # the last one is kept
        ((), "segment mortar"),
    ],
)
def test_small_sliding_pair_accepted(options, discretisation):
    d = _deck(_pair("BlockA", "SupportA", *options, discretisation=discretisation))
    assert _found(d, "NG-CONT-130", *GENERIC) == []


@pytest.mark.parametrize(
    "options, discretisation, text",
    [
        (("sliding=small", "doublepass"), "IPS", "is not available with doublepass"),
        (("doublepass", "sliding=small"), "integration-point-surface", "is not available with doublepass"),
        (("sliding=small",), "segment mortar", "available for the discretisations IPS and element mortar only"),
        (("sliding=small",), "NTN", "available for the discretisations IPS and element mortar only"),
    ],
)
def test_small_sliding_pair_rejected(options, discretisation, text):
    d = _deck(_pair("BlockA", "SupportA", *options, discretisation=discretisation))
    found = [i for i in ng.validate(d) if i.id == "NG-CONT-130"]
    assert len(found) == 1 and found[0].severity == "error" and text in found[0].message, found


def test_small_sliding_pair_with_general():
    pair = Keyword.make(
        "*Contact pair", options=[("interaction", "Friction"), ("discretisation", "IPS"), "general", "sliding=small"]
    )
    found = _found(_deck(pair), "NG-CONT-130")
    assert len(found) == 1 and "is not available with general" in found[0]
    # element mortar does not have this restriction
    pair = Keyword.make(
        "*Contact pair",
        options=[("interaction", "Friction"), ("discretisation", "element mortar"), "general", "sliding=small"],
    )
    assert _found(_deck(pair), "NG-CONT-130") == []


# ------------------------------------------------------------------------- *Model change, contact pair: accepted
def test_sliding_change_accepted():
    d = _change(_deck(), [["BlockA", "SupportA"], ["BlockB", "SupportB"]])
    assert [i for i in ng.validate(d) if i.id in (*RULES, *GENERIC)] == []
    # names as numgeo compares them, a pair per keyword, a pair in a later step, the first step
    d = _change(_change(_deck(), [["BLOCKA", "supporta"]]), [["Block B", "SupportB"]])
    assert _found(d, *RULES, *GENERIC) == []
    d = _change(_change(_deck(steps=3), [["BlockA", "SupportA"]], step=1), [["BlockB", "SupportB"]], step=2)
    assert _found(d, *RULES, *GENERIC) == []
    assert _found(_change(_deck(), [["BlockA", "SupportA"]], step=0), *RULES, *GENERIC) == []
    # a pair of a *Contact pair with several data lines, with gap=activation
    pairs = Keyword.make(
        "*Contact pair",
        options=[("interaction", "Friction"), ("discretisation", "IPS"), ("gap", "activation")],
        data=[["BlockA", "SupportA"], ["BlockB", "SupportB"]],
    )
    assert _found(_change(_deck(pairs), [["BlockB", "SupportB"]]), *RULES, *GENERIC) == []


def test_sliding_change_in_a_reduction_step():
    d = _deck(steps=3)
    d.steps[2] = ng.Step(name="Reduce", procedure=Keyword.make("*Reduction", data=[[0.1, 1.0, 1e-5, 0.5]]))
    d.steps[2].add("*Boundary", data=[["Base", "u1", 0.0], ["Base", "u2", 0.0]])
    assert _found(_change(d, [["BlockA", "SupportA"]]), *RULES, *GENERIC) == []


# -------------------------------------------------------------------------- *Model change, contact pair: options
@pytest.mark.parametrize(
    "options, texts",
    [
        (["contact pair"], ["requires the option sliding=small (once)"]),
        (["contact pair", "sliding=small", "sliding=small"], ["requires the option sliding=small (once)"]),
        (["contact pair", "sliding=finite"], ["sliding=finite is not available"]),
        (["contact pair", "sliding=small", "sliding=finite"], ["sliding=finite is not available"]),
        (["contact pair", "sliding=large"], ["unknown option 'sliding=large'; numgeo stops"]),
        (["contact pair", "sliding"], ["unknown option 'sliding'; numgeo stops"]),
        (["contact pair", "sliding=small", "position=design"], ["unknown option 'position=design'; numgeo stops"]),
        (["contact pair", "sliding=small", "add"], ["unknown option 'add'; numgeo stops"]),
        (["contact pairs", "sliding=small"], ["unknown option 'contactpairs'; numgeo stops"]),
    ],
)
def test_sliding_change_options(options, texts):
    d = _change(_deck(), [["BlockA", "SupportA"]], options=options)
    found = [i for i in ng.validate(d) if i.id in (*RULES, *GENERIC)]
    assert [i.id for i in found] == ["NG-CONT-131"] * len(texts) and all(i.severity == "error" for i in found)
    assert all(t in i.message for t, i in zip(texts, found, strict=True)), found


def test_contact_pair_is_read_first():
    # numgeo looks for CONTACTPAIR before MATERIAL, FRICTION, REMOVE and ADD (read_model_change_.f90:98)
    d = _change(_deck(), [["Friction", 1.0e5, 0.5, 0.0]], options=["friction", "contact pair", "sliding=small"])
    assert _ids(d, "NG-CONT-125", "NG-CONT-131") == ["NG-CONT-131"]
    d = _change(_deck(), [["BlockA", "SupportA"]], options=["remove", "contact pair", "sliding=small"])
    d.steps[-1].add("*PFEM remeshing", options=["interval=0.5"])
    d.steps[-1].add("*PFEM write")
    assert not any("cannot be combined with *Model change" in m for m in _found(d, "NG-STEP-134"))


def test_sliding_without_contact_pair_is_ignored():
    d = _deck()
    d.steps[-1].add("*Model change", options=["add", "sliding=small"], data=[["Soil"]])
    found = [i for i in ng.validate(d) if i.id in (*RULES, *GENERIC)]
    assert [(i.id, i.severity) for i in found] == [("NG-KW-011", "warning")]
    assert "unknown option 'sliding=small'" in found[0].message and "numgeo ignores it" in found[0].message
    d = _deck()
    d.steps[-1].add("*Model change", data=[["Soil"]])
    assert any("needs one of contactpair, material, friction, remove, add" in m for m in _found(d, "NG-KW-012"))


# ----------------------------------------------------------------------- *Model change, contact pair: data lines
@pytest.mark.parametrize(
    "rows, pairs, text",
    [
        ([], None, "needs at least one line 'slave surface, master surface'"),
        ([["BlockA", "SupportA", "SupportB"]], None, "must give one surface pair as 'slave surface, master surface'"),
        ([["BlockA"]], None, "must give one surface pair as 'slave surface, master surface'"),
        ([["BlockC", "SupportA"]], None, "unknown surface 'BlockC'"),
        ([["BlockA", "SupportX"]], None, "unknown surface 'SupportX'"),
        (
            [["BlockA", "SupportB"]],
            None,
            "no *Contact pair has the slave surface BlockA and the master surface SupportB",
        ),
        ([["SupportA", "BlockA"]], None, "the pair is defined with BlockA as slave and SupportA as master surface"),
        (
            [["BlockA", "SupportA"]],
            (_pair("BlockA", "SupportA"), _pair("BlockA", "SupportA")),
            "is defined in 2 *Contact pair definitions; the selection is ambiguous",
        ),
        (
            [["BlockA", "SupportA"]],
            (_pair("BlockA", "SupportA", discretisation="element mortar"),),
            "does not use discretisation=IPS",
        ),
        (
            [["BlockA", "SupportA"]],
            (_pair("BlockA", "SupportA", discretisation="NTN"),),
            "does not use discretisation=IPS",
        ),
        ([["BlockA", "SupportA"]], (_pair("BlockA", "SupportA", "doublepass"),), "uses the option doublepass"),
        ([["BlockA", "SupportA"], ["BlockB", "SupportB"], ["BlockA", "SupportA"]], None, "is selected more than once"),
    ],
)
def test_sliding_change_data_lines(rows, pairs, text):
    d = _change(_deck(*(pairs or ())), rows)
    found = [i for i in ng.validate(d) if i.id == "NG-CONT-131"]
    assert len(found) == 1 and found[0].severity == "error" and text in found[0].message, found
    assert found[0].message.startswith("step Place: *Model change, contact pair")


def test_sliding_change_twice_in_a_step_by_two_keywords():
    d = _change(_change(_deck(), [["BlockA", "SupportA"]]), [["BlockA", "SupportA"]])
    found = _found(d, "NG-CONT-131")
    assert len(found) == 1 and "is selected more than once" in found[0]
    # the general contact pair has no data lines: its surfaces cannot be selected
    general = Keyword.make("*Contact pair", options=[("interaction", "Friction"), ("discretisation", "IPS"), "general"])
    found = _found(_change(_deck(general), [["BlockA", "SupportA"]]), "NG-CONT-131")
    assert len(found) == 1 and "no *Contact pair has the slave surface" in found[0]


# --------------------------------------------------------------------------------- repeated selection (warning)
def test_sliding_change_of_a_pair_with_small_sliding():
    d = _change(_deck(_pair("BlockA", "SupportA", "sliding=small")), [["BlockA", "SupportA"]])
    found = [i for i in ng.validate(d) if i.id in RULES]
    assert [(i.id, i.severity) for i in found] == [("NG-CONT-134", "warning")]
    assert "already uses small sliding (sliding=small of *Contact pair); its reference configuration is kept" in (
        found[0].message
    )
    d = _change(_change(_deck(steps=3), [["BlockA", "SupportA"]], step=1), [["BlockA", "SupportA"]], step=2)
    found = [i for i in ng.validate(d) if i.id in RULES]
    assert [(i.id, i.severity) for i in found] == [("NG-CONT-134", "warning")]
    assert found[0].message.startswith("step Slide:") and "(since step Place)" in found[0].message


# ----------------------------------------------------------------------------------------------- *PFEM remeshing
def _pfem(d: ng.Deck, step: int) -> ng.Deck:
    d.steps[step].add("*PFEM remeshing", options=["interval=0.5"])
    d.steps[step].add("*PFEM write", data=[["Soil", "material=Sand"]])
    return d


def test_small_sliding_with_pfem_remeshing():
    # in the step of the change and in a later step
    d = _pfem(_change(_deck(steps=3), [["BlockA", "SupportA"]], step=1), 1)
    found = [i for i in ng.validate(d) if i.id == "NG-CONT-132"]
    assert len(found) == 1 and found[0].severity == "error"
    assert found[0].message.startswith("step Place: *PFEM remeshing cannot be combined with small sliding")
    assert "*Model change, contact pair in step Place" in found[0].message
    d = _pfem(_change(_deck(steps=3), [["BlockA", "SupportA"]], step=1), 2)
    found = _found(d, "NG-CONT-132")
    assert len(found) == 1 and found[0].startswith("step Slide:") and "in step Place" in found[0]
    # sliding=small of *Contact pair: every step
    d = _pfem(_deck(_pair("BlockA", "SupportA", "sliding=small"), steps=3), 1)
    found = _found(d, "NG-CONT-132")
    assert len(found) == 1 and "sliding=small of *Contact pair" in found[0]


def test_pfem_remeshing_without_small_sliding():
    assert _found(_pfem(_deck(steps=3), 1), "NG-CONT-132") == []
    # the pair is changed after the step with the remeshing
    d = _pfem(_change(_deck(steps=3), [["BlockA", "SupportA"]], step=2), 1)
    assert _found(d, "NG-CONT-132") == []
    # small sliding of an element mortar pair has no reference of this kind
    d = _pfem(_deck(_pair("BlockA", "SupportA", "sliding=small", discretisation="element mortar"), steps=3), 1)
    assert _found(d, "NG-CONT-132") == []
    # a selection numgeo refuses does not count
    d = _pfem(_change(_deck(steps=3), [["SupportA", "BlockA"]], step=1), 1)
    assert _found(d, "NG-CONT-132") == [] and len(_found(d, "NG-CONT-131")) == 1


# ---------------------------------------------------------------------------------------------- shared slave faces
def _three(third: Keyword, first: Keyword | None = None) -> ng.Deck:
    return _deck(first or _pair("BlockA", "SupportA"), _pair("BlockB", "SupportB"), third, steps=3)


@pytest.mark.parametrize("slave", ["BlockA", "BlockAPart"])
def test_shared_slave_faces_need_one_sliding_formulation(slave):
    # one of two pairs changed
    d = _change(_three(_pair(slave, "SupportC")), [["BlockA", "SupportA"]], step=2)
    found = [i for i in ng.validate(d) if i.id == "NG-CONT-133"]
    assert len(found) == 1 and found[0].severity == "error"
    assert f"IPS surface pair BlockA, SupportA uses small sliding from step Slide on, the surface pair {slave}, " in (
        found[0].message
    )
    # the other one changed, and one changed a step later than the other
    d = _change(_three(_pair(slave, "SupportC")), [[slave, "SupportC"]], step=2)
    found = _found(d, "NG-CONT-133")
    assert len(found) == 1 and f"IPS surface pair {slave}, SupportC uses small sliding from step Slide on" in found[0]
    d = _change(_three(_pair(slave, "SupportC")), [["BlockA", "SupportA"]], step=1)
    found = _found(_change(d, [[slave, "SupportC"]], step=2), "NG-CONT-133")
    assert len(found) == 1 and "BlockA, SupportA uses small sliding from step Place on" in found[0]
    # sliding=small of one *Contact pair
    found = _found(_three(_pair(slave, "SupportC", "sliding=small")), "NG-CONT-133")
    assert len(found) == 1 and f"{slave}, SupportC uses small sliding from the first step on" in found[0]


@pytest.mark.parametrize("slave", ["BlockA", "BlockAPart"])
def test_shared_slave_faces_with_one_sliding_formulation(slave):
    assert _found(_three(_pair(slave, "SupportC")), "NG-CONT-133") == []
    d = _change(_three(_pair(slave, "SupportC")), [["BlockA", "SupportA"], [slave, "SupportC"]], step=2)
    assert _found(d, "NG-CONT-133") == []
    small = _three(_pair(slave, "SupportC", "sliding=small"), _pair("BlockA", "SupportA", "sliding=small"))
    assert _found(small, "NG-CONT-133") == []
    # a pair without common faces keeps finite sliding; so does a pair with another discretisation
    d = _change(_three(_pair(slave, "SupportC")), [["BlockB", "SupportB"]], step=2)
    assert _found(d, "NG-CONT-133") == []
    d = _change(_three(_pair(slave, "SupportC", discretisation="element mortar")), [["BlockA", "SupportA"]], step=2)
    assert _found(d, "NG-CONT-133") == []


def test_shared_faces_of_node_based_surfaces_are_not_resolved():
    d = _three(_pair("TopNodes", "SupportC"))
    d.mesh.add_surface("TopNodes", [("Base",)], type="node")
    assert _found(_change(d, [["BlockA", "SupportA"]], step=2), "NG-CONT-133") == []


# ---------------------------------------------------------------------------------------- written and read back
def test_written_and_read_back():
    d = _change(
        _deck(_pair("BlockA", "SupportA", "sliding=small"), _pair("BlockB", "SupportB")), [["BlockB", "SupportB"]]
    )
    text = ng.write_text(d)
    assert "*Contact pair, interaction=Friction, discretisation=ips, sliding=small\nBlockA, SupportA\n" in text
    assert "*Model change, contactpair, sliding=small\nBlockB, SupportB\n" in text
    result = ng.parse_text(text)
    assert [i for i in result.issues if i.severity == "error"] == [] and result.deck == d
    kw = result.deck.steps[-1].items[-1]
    assert kw.keyword == "*MODELCHANGE" and kw.has_option("contactpair") and kw.option("sliding") == "small"
    assert [[str(t) for t in r] for r in kw.data] == [["BlockB", "SupportB"]]
    assert _found(result.deck, *RULES, *GENERIC) == []
    assert ng.write_text(result.deck) == text


# ------------------------------------------------------------------------------------------- messages of numgeo
@pytest.mark.parametrize(
    "text, severity, file, rule",
    [
        (
            "The option SLIDING=SMALL of *CONTACTPAIRING is only available for DISCRETISATION=ELEMENT MORTAR and "
            "DISCRETISATION=IPS.",
            "error",
            "src/input/read_contact_pairing_.f90",
            "NG-CONT-130",
        ),
        (
            "The option SLIDING=SMALL of *CONTACTPAIRING is not available with the option doublepass "
            "(DISCRETISATION=IPS).",
            "error",
            "src/input/read_contact_pairing_.f90",
            "NG-CONT-130",
        ),
        (
            "The option SLIDING=SMALL of *CONTACTPAIRING is not available with the option general "
            "(DISCRETISATION=IPS).",
            "error",
            "src/input/read_contact_pairing_.f90",
            "NG-CONT-130",
        ),
        (
            "*Model change, contact pair in step SLIDE requires the option sliding=small (once).",
            "error",
            "src/input/read_model_change_.f90",
            "NG-CONT-131",
        ),
        (
            "*Model change, contact pair in step SLIDE: sliding=finite is not available. A surface pair with small "
            "sliding keeps its reference configuration for the rest of the analysis.",
            "error",
            "src/input/read_model_change_.f90",
            "NG-CONT-131",
        ),
        (
            "Unknown option POSITION=DESIGN for *Model change, contact pair in step SLIDE. Supported is: *Model "
            "change, contact pair, sliding=small",
            "error",
            "src/input/read_model_change_.f90",
            "NG-CONT-131",
        ),
        (
            'Unknown surface "BLOCK_C_SURFACE" for *Model change, contact pair in step SLIDE',
            "error",
            "src/input/read_model_change_.f90",
            "NG-CONT-131",
        ),
        (
            '*Model change, contact pair in step SLIDE: no *Contact pair has the slave surface "SUPPORT_A" and the '
            'master surface "BLOCK_A_SURFACE"; the pair is defined with "BLOCK_A_SURFACE" as slave and "SUPPORT_A" as '
            "master surface. Give the surfaces in the order of *Contact pair.",
            "error",
            "src/input/read_model_change_.f90",
            "NG-CONT-131",
        ),
        (
            '*Model change, contact pair in step SLIDE: the surface pair "BLOCK_A_SURFACE, SUPPORT_A" is defined in 2 '
            "*Contact pair definitions; the selection is ambiguous.",
            "error",
            "src/input/read_model_change_.f90",
            "NG-CONT-131",
        ),
        (
            '*Model change, contact pair in step SLIDE: the surface pair "BLOCK_A_SURFACE, SUPPORT_A" does not use '
            "discretisation=IPS. The change to small sliding is available for IPS contact pairs only.",
            "error",
            "src/input/read_model_change_.f90",
            "NG-CONT-131",
        ),
        (
            '*Model change, contact pair in step SLIDE: the surface pair "BLOCK_A_SURFACE, SUPPORT_A" is selected more '
            "than once.",
            "error",
            "src/input/read_model_change_.f90",
            "NG-CONT-131",
        ),
        (
            "Step SLIDE: IPS contact pairs with small sliding (SLIDING=SMALL, *Model change, contact pair) cannot be "
            "combined with *PFEM remeshing. The reference configuration of the pairs belongs to the mesh.",
            "error",
            "src/contacts/contact_.f90",
            "NG-CONT-132",
        ),
        (
            "Small sliding in step SLIDE: face 1 of element 17 belongs to the slave surface of the surface pair "
            '"BLOCK_A_SURFACE, SUPPORT_A" with small sliding and to that of the surface pair "BLOCK_A_SURFACE, '
            'SUPPORT_C" with finite sliding. An integration point has one sliding formulation: the selection is '
            "ambiguous. Change both surface pairs in the same step (*Model change, contact pair, sliding=small) or "
            "define both with SLIDING=SMALL.",
            "error",
            "src/contacts/contact_.f90",
            "NG-CONT-133",
        ),
        (
            '*Model change, contact pair in step SLIDE: the surface pair "BLOCK_A_SURFACE, SUPPORT_A" already uses '
            "small sliding (SLIDING=SMALL of *Contact pair). Its reference configuration is kept.",
            "warning",
            "src/contacts/contact_.f90",
            "NG-CONT-134",
        ),
        (
            '*Model change, contact pair in step SLIDE: the surface pair "BLOCK_A_SURFACE, SUPPORT_A" already uses '
            "small sliding (since step PLACE). Its reference configuration is kept.",
            "warning",
            "src/contacts/contact_.f90",
            "NG-CONT-134",
        ),
    ],
)
def test_numgeo_messages(text, severity, file, rule):
    m = classify(text, severity)
    assert m is not None and m.file == file and m.terminates == (severity == "error")
    assert rules_for_source(m.file, m.line, m.candidates) == (rule,)


def test_replaced_messages():
    old = "The option SLIDING=SMALL of *CONTACTPAIRING is only available for DISCRETISATION=ELEMENT MORTAR."
    assert not any(m["template"] == old for m in cat.load().messages())
    m = classify(
        "Unknown option for the *Model change statement in step LOAD. Supported are: *Model change, material / *Model "
        "change, remove / *Model change, add / *Model change, friction / *Model change, contact pair",
        "error",
    )
    assert m is not None and m.message_id.startswith("src/input/read_model_change_.f90:")
    # the messages of the other branches of the readers still lead to their rules
    m = classify('Unknown interaction "GROUT" for *Model change, friction in step HARDENING', "error")
    assert m is not None and rules_for_source(m.file, m.line, m.candidates) == ("NG-CONT-125",)
    m = classify(
        "The option water-filled gap of interaction GAP is not available with the option doublepass of *Contact pair.",
        "error",
    )
    assert m is not None and rules_for_source(m.file, m.line, m.candidates) == ("NG-CONT-129",)
    ids = [m["id"] for m in cat.load().messages() if m["file"].startswith("src/contacts/contact_")]
    assert len(ids) == len(set(ids))


# ------------------------------------------------------------------------------------------------- source anchors
@pytest.mark.skipif(not os.environ.get("NUMGEO_SRC"), reason="set NUMGEO_SRC")
@pytest.mark.source
def test_catalogue_anchors_match_the_source():
    """The entries of the two readers and the messages of contact_.f90 cite lines of numgeo-src 1f48283: their
    anchors must match it."""
    root = Path(os.environ["NUMGEO_SRC"])
    readers = ("src/input/read_contact_pairing_.f90", "src/input/read_model_change_.f90")
    entries: list[dict] = []

    def collect(node) -> None:
        if isinstance(node, dict):
            if {"anchor", "file", "line"} <= set(node) and node["file"] in readers:
                entries.append(node)
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    for name in ("*Contact pair", "*Model change"):
        collect(cat.keyword(name).raw)
    collect(cat.load().section("interactions", "contact_discretisations"))
    assert len(entries) == 46
    messages = [m for m in cat.load().messages() if m["file"] in (*readers, "src/contacts/contact_.f90")]
    assert len(messages) == 20 + 35 + 25
    feature = ("capture_small_sliding_reference", "small_sliding_master_face", "slave_area_ratio")
    messages += [m for m in cat.load().messages() if m["routine"] in feature]
    assert len(messages) == 20 + 35 + 25 + 4
    for e in entries + messages:
        line = (root / e["file"]).read_text(encoding="latin-1").splitlines()[e["line"] - 1]
        assert hashlib.sha256(line.strip().encode()).hexdigest()[:16] == e["anchor"], e


# ------------------------------------------------------------------------------------- deck built with the API
def _rectangle(d: ng.Deck, x0: float, y0: float, nx: int, ny: int, size: float = 0.25) -> np.ndarray:
    """A block of nx x ny u4-solid elements; returns the element labels, row by row from the bottom."""
    nodes = d.mesh.add_nodes([[x0 + i * size, y0 + j * size] for j in range(ny + 1) for i in range(nx + 1)]).reshape(
        ny + 1, nx + 1
    )
    cells = [[nodes[j, i], nodes[j, i + 1], nodes[j + 1, i + 1], nodes[j + 1, i]] for j in range(ny) for i in range(nx)]
    first = d.mesh.element_count + 1
    d.mesh.add_elements("u4-solid", cells)
    return np.arange(first, first + nx * ny).reshape(ny, nx)


def staged_blocks() -> ng.Deck:
    """Two blocks on a support (plane strain, kN and m), all nodes displacement-controlled: block A is pressed into the
    support by 1 mm, the support settles by 0.5 mm, block B is activated and pressed down by 1.5 mm, both blocks are
    slid by 20 mm. Pair A uses small sliding from the start, pair B from the last step on."""
    d = ng.Deck()
    support = _rectangle(d, 0.0, -0.25, 16, 1)
    block_a = _rectangle(d, 0.5, 0.0, 4, 2)
    block_b = _rectangle(d, 2.5, 0.0, 4, 2)
    for name, elements in (("Support", support), ("BlockA", block_a), ("BlockB", block_b)):
        d.mesh.add_elset(name, elements.ravel().tolist())
        block = next(b for b in d.mesh.blocks if elements[0, 0] in b.labels)
        rows = np.isin(block.labels, elements.ravel())
        d.mesh.add_nset(name, sorted(set(block.connectivity[rows].ravel().tolist())))
    # the two master surfaces are parts of the top of the support without common nodes
    d.mesh.add_elset("SupportTopA", support[0, :8].tolist())
    d.mesh.add_elset("SupportTopB", support[0, 9:].tolist())
    d.mesh.add_elset("BlockABottom", block_a[0].tolist())
    d.mesh.add_elset("BlockBBottom", block_b[0].tolist())
    d.mesh.add_surface("SupportA", [("SupportTopA", "S3")])
    d.mesh.add_surface("SupportB", [("SupportTopB", "S3")])
    d.mesh.add_surface("BlockASurface", [("BlockABottom", "S1")])
    d.mesh.add_surface("BlockBSurface", [("BlockBBottom", "S1")])
    m = ng.Material(name="Elastic", phases=1)
    m.set_mechanical("linear_elasticity", [1.0e4, 0.25])
    m.add("*Density", data=[[1.0]])
    d.materials.append(m)
    for name in ("Support", "BlockA", "BlockB"):
        d.assign(name, "Elastic")
    d.keywords.append(
        Keyword.make(
            "*Interaction",
            options=[("name", "Friction")],
            children=[
                Keyword.make("*Normal", options=["mechanical=penalty"], data=[[1.0e6]]),
                Keyword.make("*Friction", options=[("model", "Coulomb")], data=[[1.0e5, 0.3, 0.0]]),
            ],
        )
    )
    pair = [("interaction", "Friction"), ("discretisation", "IPS"), ("gap", "activation")]
    d.keywords.append(
        Keyword.make("*Contact pair", options=[*pair, ("sliding", "small")], data=[["BlockASurface", "SupportA"]])
    )
    d.keywords.append(Keyword.make("*Contact pair", options=pair, data=[["BlockBSurface", "SupportB"]]))
    for name, values in (
        ("PressA", [0.0, 0.0, 1.0, -0.001]),
        ("Settle", [0.0, 0.0, 1.0, -0.0005]),
        ("FollowA", [0.0, -0.001, 1.0, -0.0015]),
        ("PressB", [0.0, 0.0, 1.0, -0.0015]),
        ("Slide", [0.0, 0.0, 1.0, 0.02]),
    ):
        d.amplitudes.append(ng.Amplitude(name=name, type="ramp", data=[values]))

    def step(name: str, fixed, driven, change: Keyword | None = None) -> None:
        st = ng.Step(name=name, inc=1000, maxiter=35, procedure=Keyword.make("*Static", data=[[0.1, 1.0, 1e-6, 0.1]]))
        st.add("*Solver", options=["MUMPS"])
        if change is not None:
            st.items.append(change)
        st.add("*Boundary", data=fixed)
        for amplitude, row in driven:
            st.add("*Boundary", options=[("amplitude", amplitude)], data=[row])
        st.add(
            "*Output",
            options=["print"],
            children=[
                Keyword.make("*Frequency", value="1"),
                Keyword.make("*Node output", options=[("nset", "BlockA")], data=[["U", "RF"]]),
                Keyword.make("*Node output", options=[("nset", "BlockB")], data=[["U", "RF"]]),
            ],
        )
        st.add("*Controls", options=["global", "deactivate"])
        st.add("*Controls", options=["u", "activate"])
        d.steps.append(st)

    step(
        "Initial",
        [["Support", "u1", 0.0], ["Support", "u2", 0.0], ["BlockA", "u1", 0.0]],
        [("PressA", ["BlockA", "u2", 1.0])],
        Keyword.make("*Model change", options=["remove"], data=[["BlockB"]]),
    )
    step(
        "Settle",
        [["Support", "u1", 0.0], ["BlockA", "u1", 0.0]],
        [("Settle", ["Support", "u2", 1.0]), ("FollowA", ["BlockA", "u2", 1.0])],
    )
    step(
        "Place",
        [["Support", "u1", 0.0], ["Support", "u2", -0.0005], ["BlockA", "u1", 0.0], ["BlockA", "u2", -0.0015],
         ["BlockB", "u1", 0.0]],
        [("PressB", ["BlockB", "u2", 1.0])],
        Keyword.make("*Model change", options=["add"], data=[["BlockB"]]),
    )  # fmt: skip
    step(
        "Slide",
        [["Support", "u1", 0.0], ["Support", "u2", -0.0005], ["BlockA", "u2", -0.0015], ["BlockB", "u2", -0.0015]],
        [("Slide", ["BlockA", "u1", 1.0]), ("Slide", ["BlockB", "u1", 1.0])],
        Keyword.make("*Model change", options=SMALL, data=[["BlockBSurface", "SupportB"]]),
    )
    return d


def test_staged_deck_is_valid_and_survives_writing():
    d = staged_blocks()
    assert [i for i in ng.validate(d) if i.severity == "error"] == []
    assert _found(d, *RULES, *GENERIC) == []
    text = ng.write_text(d)
    assert "*Contact pair, interaction=Friction, discretisation=ips, gap=activation, sliding=small\n" in text
    assert "*Model change, contactpair, sliding=small\nBlockBSurface, SupportB\n" in text
    result = ng.parse_text(text)
    assert [i for i in result.issues if i.severity == "error"] == [] and result.deck == d


@pytest.mark.skipif(not os.environ.get("NUMGEO_EXE"), reason="set NUMGEO_EXE")
@pytest.mark.solver
def test_numgeo_runs_the_staged_deck(tmp_path):
    """The resultants on the blocks follow from the penalty and Coulomb laws: N = eps_N * penetration * L with
    eps_N = 1e6 kN/m3 and L = 1 m (block A 1 mm, block B 1.5 mm from its activation), T = -tan(delta) N = -0.3 N
    after the slip of 20 mm."""
    d = staged_blocks()
    ng.write(d, tmp_path / "blocks.inp")
    assert ng.read(tmp_path / "blocks.inp") == d
    res = ng.run(tmp_path / "blocks.inp", tmp_path, job="blocks", timeout=600)
    assert res.status == "SUCCESS", (res.reason, [m.text for m in res.messages if m.severity == "error"])
    log = (tmp_path / "blocks.log").read_text(encoding="latin-1")
    assert 'small sliding of surface pair "BLOCKBSURFACE, SUPPORTB" (contact pair 2) from step SLIDE on' in log
    results = ng.open_results(tmp_path, "blocks")
    for block, normal in (("BlockA", 1000.0), ("BlockB", 1500.0)):
        nodes = d.mesh.nset(block).members.tolist()
        series = [results.print_series(block, "node", n) for n in nodes]
        assert {float(s.time[-1]) for s in series} == {4.0}
        rf1 = sum(float(s.column("RF1")[-1]) for s in series)
        rf2 = sum(float(s.column("RF2")[-1]) for s in series)
        assert rf2 == pytest.approx(normal, rel=1e-6) and rf1 == pytest.approx(-0.3 * normal, rel=1e-6)
