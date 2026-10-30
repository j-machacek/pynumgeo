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
"""*Model change, friction (numgeo-src 60fca8b5): catalogue, check of the options and of the data lines
(src/input/read_model_change_.f90:136-217), messages and the bundled reference page."""

from __future__ import annotations

import pytest

import pynumgeo as ng
from conftest import small_deck
from pynumgeo import catalogue as cat
from pynumgeo.deck import Keyword
from pynumgeo.solver.messages import classify, rules_for_source


def _interaction(name: str, model: str = "Coulomb", values=(1.0e6, 0.0, 0.0), options=()) -> Keyword:
    children = [Keyword.make("*Normal", options=["mechanical=penalty"], data=[[1.0e6]])]
    if model:
        children.append(Keyword.make("*Friction", options=[("model", model), *options], data=[list(values)]))
    return Keyword.make("*Interaction", options=[("name", name)], children=children)


def _deck(rows, interaction=None) -> ng.Deck:
    d = small_deck()
    d.keywords.append(interaction or _interaction("Interface"))
    d.steps[0].add("*Model change", options=["friction"], data=[list(r) for r in rows])
    return d


def _ids(deck: ng.Deck, prefix: str = "NG-") -> list[str]:
    return [i.id for i in ng.validate(deck) if i.id.startswith(prefix)]


def _messages(deck: ng.Deck, rule: str) -> list[str]:
    return [i.message for i in ng.validate(deck) if i.id == rule]


def test_catalogue_knows_the_option():
    spec = cat.keyword("*Model change", "step")
    option = spec.option("friction")
    assert option is not None and option.value_type == "flag" and "60fca8b5" in option.notes
    assert [o.name for o in spec.options] == ["MATERIAL", "FRICTION", "REMOVE", "ADD", "POSITION"]
    page = cat.load().doc_page("docs/reference/model-change/friction.md")
    assert page is not None and page.startswith("# Change friction")


def test_friction_change_is_accepted():
    d = _deck([["Interface", 1.0e6, 0.7, 0.0]])
    found = [i for i in ng.validate(d) if i.id in ("NG-KW-010", "NG-KW-011", "NG-KW-012", "NG-CONT-125")]
    assert found == []


def test_stiffness_factor_without_penalty_in_the_data_line():
    inter = _interaction("Interface", values=(0.0, 0.0), options=[("stiffness_factor", 1.0)])
    assert _ids(_deck([["Interface", 0.7, 0.0]], inter), "NG-CONT-125") == []
    assert _ids(_deck([["Interface", 1.0e6, 0.7, 0.0]], inter), "NG-CONT-125") == ["NG-CONT-125"]


def test_mohr_coulomb_parameters():
    inter = _interaction("Interface", "Mohr-Coulomb", (1.0e6, 0.1, 0.0, 0.0))
    assert _ids(_deck([["Interface", 1.0e6, 0.6, 0.05, 1.5]], inter), "NG-CONT-125") == []
    assert _messages(_deck([["Interface", 1.0e6, 0.6, 1.5]], inter), "NG-CONT-125") == [
        "step Load: *Model change, friction: 3 parameters for interaction Interface, the data line of its *Friction "
        "has 4"
    ]


@pytest.mark.parametrize(
    "rows, interaction, text",
    [
        ([["Other", 1.0e6, 0.7, 0.0]], None, "unknown interaction 'Other'"),
        ([["Interface"]], None, "needs the interaction name and the parameters"),
        ([["Interface", 2.0e6, 0.7, 0.0]], None, "tangential penalty"),
        ([["Interface", 1.0e6, 0.7, 0.0]], _interaction("Interface", model=""), "has no friction model"),
        (
            [["Interface", 1.0e6, 0.7, 0.0]],
            Keyword.make(
                "*Interaction",
                options=[("name", "Interface"), "user"],
                children=[Keyword.make("*Friction", options=[("model", "Coulomb")])],
            ),
            "user defined contact properties",
        ),
    ],
)
def test_friction_change_errors(rows, interaction, text):
    found = [i for i in ng.validate(_deck(rows, interaction)) if i.id == "NG-CONT-125"]
    assert len(found) == 1 and found[0].severity == "error" and text in found[0].message, found


def test_names_are_compared_as_numgeo_reads_them():
    assert _ids(_deck([["INTERFACE", 1.0e6, 0.7, 0.0]]), "NG-CONT-125") == []


def test_material_is_read_first():
    # numgeo checks MATERIAL before FRICTION (read_model_change_.f90:82,136): no friction check then
    d = small_deck()
    d.steps[0].add("*Model change", options=["material", "friction"], data=[["Soil", "Sand"]])
    assert _ids(d, "NG-CONT-125") == []


def test_written_and_read_back():
    text = ng.write_text(_deck([["Interface", 1.0e6, 0.7, 0.0]]))
    assert "*Model change, friction\nInterface, 1000000.0, 0.7, 0.0\n" in text
    back = ng.parse_text(text).deck
    kw = back.steps[0].items[-1]
    assert kw.keyword == "*MODELCHANGE" and kw.has_option("friction") and str(kw.data[0][0]) == "Interface"
    assert _ids(back, "NG-KW-012") == [] and _ids(back, "NG-CONT-125") == []


def test_numgeo_messages_of_the_reader():
    m = classify('Unknown interaction "GROUT" for *Model change, friction in step HARDENING', "error")
    assert m is not None and m.file == "src/input/read_model_change_.f90" and m.terminates
    assert "NG-CONT-125" in rules_for_source(m.file, m.line, m.candidates)
    m = classify(
        "*Model change, friction in step HARDENING: the tangential penalty factor (first value) of interaction "
        '"GROUT" cannot be changed; give the value of its *Friction definition.',
        "error",
    )
    assert m is not None and "NG-CONT-125" in rules_for_source(m.file, m.line, m.candidates)
