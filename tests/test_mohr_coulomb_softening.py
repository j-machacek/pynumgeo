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
# 07.11.2026, J. Machacek - Initial version
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""Softening of the Mohr-Coulomb friction (uncommitted numgeo-src of 06.11.2026): data line
``[eps_T,] tan(delta), tan(theta), c [, tan(delta_r), u_r]`` of ``*Friction`` and ``*Model change, friction``
(src/input/read_interaction_.f90:404-467, read_model_change_.f90:204-224), merged IPS contact pairs
(src/contacts/contact_.f90:1400-1412,1479-1494), catalogue, messages and the bundled reference pages."""

from __future__ import annotations

import pytest

import pynumgeo as ng
from conftest import small_deck
from pynumgeo import catalogue as cat
from pynumgeo.deck import Keyword
from pynumgeo.solver.messages import classify, rules_for_source

SOFT = (1.0e6, 0.9325, 0.2309, 0.0, 0.6414, 0.005)  # example of docs/reference/contacts/interaction.md
PLAIN = (1.0e6, 0.9325, 0.2309, 0.0)


def _interaction(name: str, values, model: str = "Mohr-Coulomb", user: bool = False) -> Keyword:
    children = [
        Keyword.make("*Normal", options=["mechanical=penalty"], data=[[1.0e6]]),
        Keyword.make("*Friction", options=[("model", model)], data=[list(values)]),
    ]
    return Keyword.make("*Interaction", options=[("name", name)] + (["user"] if user else []), children=children)


def _deck(*interactions: Keyword, change=None) -> ng.Deck:
    d = small_deck()
    d.keywords.extend(interactions)
    if change is not None:
        d.steps[0].add("*Model change", options=["friction"], data=[list(r) for r in change])
    return d


def _found(deck: ng.Deck, rule: str) -> list[ng.Issue]:
    return [i for i in ng.validate(deck) if i.id == rule]


def _messages(deck: ng.Deck, rule: str) -> list[str]:
    return [i.message for i in _found(deck, rule)]


def test_catalogue_and_reference_pages():
    models = {m["name"]: m for m in cat.load().section("interactions", "contact_models")}
    for name in ("MC", "MOHR-COULOMB"):
        m = models[name]
        assert m["nprops"] == 4  # library parameters; tan(delta_r) and u_r follow with softening
        assert [p["name"] for p in m["parameters"]] == ["eps_T", "tan_phi", "tan_psi", "c", "tan_phi_r", "u_r"]
        assert "06.11.2026" in m["notes"]
    friction = cat.keyword("*Friction", "interaction")
    assert "with softening 5 or 6 values" in friction.data_lines[0].count_rule
    change = cat.keyword("*Model change", "step")
    assert "tan(delta_r), u_r" in change.data_lines[1].description
    assert "softening" in change.option("friction").notes
    page = cat.load().doc_page("docs/reference/contacts/interaction.md")
    assert page is not None and "#### Softening of friction and dilatancy" in page
    assert "1.0e6, 0.9325, 0.2309, 0.0, 0.6414, 0.005" in page
    page = cat.load().doc_page("docs/reference/model-change/friction.md")
    assert page is not None and "`[ε_T,] tan(δ), tan(ϑ), c, tan(δ_r), u_r`" in page
    page = cat.load().doc_page("docs/reference/contacts/contact-pair.md")
    assert page is not None and "also with or without [softening]" in page


@pytest.mark.parametrize("model", ["Mohr-Coulomb", "MC"])
@pytest.mark.parametrize("values", [PLAIN[1:], PLAIN, SOFT[1:], SOFT])
def test_three_to_six_values_are_accepted(model, values):
    d = _deck(_interaction("Grout", values, model))
    assert [i for i in ng.validate(d) if i.id in ("NG-CONT-110", "NG-CONT-126", "NG-KW-020")] == []


@pytest.mark.parametrize("values", [(0.9, 0.2), (*SOFT, 1.0), (*SOFT, 1.0, 2.0)])
def test_other_numbers_of_values_are_errors(values):
    found = _found(_deck(_interaction("Grout", values)), "NG-CONT-110")
    assert len(found) == 1 and found[0].severity == "error"
    assert found[0].message == (
        "interaction Grout: friction model mohr-coulomb needs 3 or 4 values ([eps_T,] tan(delta), tan(theta), c), "
        "with softening 5 or 6 values ([eps_T,] tan(delta), tan(theta), c, tan(delta_r), u_r), "
        f"{len(values)} given"
    )


def test_coulomb_counts_and_message_unchanged():
    assert _found(_deck(_interaction("Grout", (1.0e6, 0.6, 0.0), "Coulomb")), "NG-CONT-110") == []
    assert _messages(_deck(_interaction("Grout", (1.0e6, 0.6, 0.0, 0.5), "Coulomb")), "NG-CONT-110") == [
        "interaction Grout: friction model coulomb needs 2 or 3 values, 4 given"
    ]


@pytest.mark.parametrize(
    "values, texts",
    [
        ((1.0e6, 0.9, 0.2, 0.0, 0.6, 0.0), ["the plastic slip u_r up to the residual friction (last value, 0.0)"]),
        ((0.9, 0.2, 0.0, 0.6, -0.01), ["the plastic slip u_r up to the residual friction (last value, -0.01)"]),
        (
            (1.0e6, 0.9, 0.2, 0.0, 1.2, 0.005),
            ["tan(delta_r) (1.2) must lie between 0 and the peak friction tan(delta) (0.9)"],
        ),
        ((0.9, 0.2, 0.0, -0.1, 0.005), ["tan(delta_r) (-0.1) must lie between 0"]),
        ((1.0e6, 0.9, -0.2, 0.0, 0.6, 0.005), ["the dilatancy tan(theta) (-0.2) must not be negative"]),
        (
            (0.9, -0.2, 0.0, 1.0, 0.0),
            ["the plastic slip u_r", "tan(delta_r) (1.0) must lie between 0", "tan(theta) (-0.2) must not be negative"],
        ),
    ],
)
def test_softening_parameters(values, texts):
    found = _found(_deck(_interaction("Grout", values)), "NG-CONT-126")
    assert len(found) == len(texts), found
    for issue, text in zip(found, texts, strict=True):
        assert issue.severity == "error" and text in issue.message
        assert issue.message.startswith("interaction Grout: Mohr-Coulomb friction with softening: ")


def test_limits_are_accepted():
    # tan(delta_r) = tan(delta) and tan(delta_r) = 0, tan(theta) = 0 (numgeo: error only outside the limits)
    for values in ((0.9, 0.0, 0.0, 0.9, 1.0e-6), (0.9, 0.2, 0.0, 0.0, 0.005)):
        assert _found(_deck(_interaction("Grout", values)), "NG-CONT-126") == []


def test_user_contact_properties_are_not_checked():
    # *Interaction, user: numgeo reads no property lines (read_interaction_.f90:363)
    d = _deck(_interaction("Grout", (0.9, 0.2, 0.0, 1.2, 0.0), user=True))
    assert _found(d, "NG-CONT-126") == [] and _found(d, "NG-CONT-110") == []


def test_friction_change_with_softening():
    change = [["Grout", 1.0e6, 0.95, 0.25, 0.0, 0.65, 0.004]]
    d = _deck(_interaction("Grout", SOFT), change=change)
    assert [i for i in ng.validate(d) if i.id in ("NG-KW-012", "NG-CONT-125", "NG-CONT-126")] == []
    # five values (no tangential penalty) in *Friction and in the change
    d = _deck(_interaction("Grout", SOFT[1:]), change=[["Grout", 0.95, 0.25, 0.0, 0.65, 0.004]])
    assert [i for i in ng.validate(d) if i.id in ("NG-CONT-125", "NG-CONT-126")] == []


def test_friction_change_needs_the_softening_values_of_the_interaction():
    assert _messages(_deck(_interaction("Grout", SOFT), change=[["Grout", *PLAIN]]), "NG-CONT-125") == [
        "step Load: *Model change, friction: 4 parameters for interaction Grout, the data line of its *Friction has 6"
    ]
    assert _messages(_deck(_interaction("Grout", PLAIN), change=[["Grout", *SOFT]]), "NG-CONT-125") == [
        "step Load: *Model change, friction: 6 parameters for interaction Grout, the data line of its *Friction has 4"
    ]


def test_friction_change_keeps_the_tangential_penalty_with_softening():
    # numgeo compares the first value with nprops + 2 parameters (read_model_change_.f90:204-224)
    found = _found(_deck(_interaction("Grout", SOFT), change=[["Grout", 2.0e6, *SOFT[1:]]]), "NG-CONT-125")
    assert len(found) == 1 and "tangential penalty (first value, 2000000.0)" in found[0].message


def test_friction_change_parameters_are_checked():
    change = [["Grout", 1.0e6, 0.5, 0.25, 0.0, 0.65, 0.0]]
    assert _messages(_deck(_interaction("Grout", SOFT), change=change), "NG-CONT-126") == [
        "step Load: *Model change, friction of interaction Grout, Mohr-Coulomb friction with softening: the plastic "
        "slip u_r up to the residual friction (last value, 0.0) must be positive",
        "step Load: *Model change, friction of interaction Grout, Mohr-Coulomb friction with softening: the residual "
        "friction tan(delta_r) (0.65) must lie between 0 and the peak friction tan(delta) (0.5)",
    ]


def test_written_and_read_back():
    d = _deck(_interaction("Grout", SOFT), change=[["Grout", *SOFT]])
    text = ng.write_text(d)
    assert "*Friction, model=mohr-coulomb\n1000000.0, 0.9325, 0.2309, 0.0, 0.6414, 0.005\n" in text
    assert "*Model change, friction\nGrout, 1000000.0, 0.9325, 0.2309, 0.0, 0.6414, 0.005\n" in text
    back = ng.parse_text(text).deck
    assert [i for i in ng.validate(back) if i.id.startswith("NG-CONT-")] == []


# ------------------------------------------------------------------------------------------- merged IPS contact pairs
def _pairs(first, second, faces=("S1", "S2"), discretisation="IPS") -> ng.Deck:
    """Two contact pairs whose slave surfaces (faces of the one quad of small_deck) share node 2 for S1 and S2."""
    d = _deck(_interaction("A", first), _interaction("B", second))
    d.mesh.add_surface("Slave-a", [("Soil", faces[0])])
    d.mesh.add_surface("Slave-b", [("Soil", faces[1])])
    d.mesh.add_surface("Master-a", [("Soil", "S3")])
    d.mesh.add_surface("Master-b", [("Soil", "S4")])
    for interaction, slave, master in (("A", "Slave-a", "Master-a"), ("B", "Slave-b", "Master-b")):
        d.keywords.append(
            Keyword.make(
                "*Contact pair",
                options=[("interaction", interaction), ("discretisation", discretisation)],
                data=[[slave, master]],
            )
        )
    return d


def test_merged_ips_pairs_with_and_without_softening():
    found = _found(_pairs(SOFT, PLAIN), "NG-CONT-127")
    assert len(found) == 1 and found[0].severity == "warning"
    assert found[0].message == (
        "IPS contact pair Slave-b, Master-b (interaction B) shares slave nodes with the pair Slave-a, Master-a "
        "(interaction A) and is merged into it: Mohr-Coulomb friction with softening in A, without in B; numgeo uses "
        "the interaction A also on the master faces of this pair (merged pairs: all with softening or all without)"
    )
    assert "with softening in B, without in A" in _messages(_pairs(PLAIN, SOFT), "NG-CONT-127")[0]


@pytest.mark.parametrize(
    "first, second, faces, discretisation",
    [
        (SOFT, SOFT, ("S1", "S2"), "IPS"),  # all with softening
        (PLAIN, PLAIN, ("S1", "S2"), "IPS"),  # all without
        (SOFT, PLAIN, ("S1", "S3"), "IPS"),  # no common slave node: not merged
        (SOFT, PLAIN, ("S1", "S2"), "element mortar"),  # the rule of numgeo is for IPS
    ],
)
def test_merged_ips_pairs_without_finding(first, second, faces, discretisation):
    assert _found(_pairs(first, second, faces, discretisation), "NG-CONT-127") == []


def test_merged_ips_pairs_with_unresolved_surfaces():
    d = _pairs(SOFT, PLAIN)
    d.mesh.surfaces = [s for s in d.mesh.surfaces if s.name != "Slave-b"]  # e.g. a surface of an include
    assert _found(d, "NG-CONT-127") == []


# --------------------------------------------------------------------------------------------------------- messages
@pytest.mark.parametrize(
    "text, severity, rule",
    [
        (
            'Interaction "GROUT": the data line of *Friction, model=Mohr-Coulomb has 7 values. Give [eps_T,] '
            "tan(delta), tan(psi), c or, with softening, [eps_T,] tan(delta), tan(psi), c, tan(delta_r), u_r.",
            "error",
            "NG-CONT-110",
        ),
        (
            'Interaction "GROUT", Mohr-Coulomb friction with softening: the residual friction tan(delta_r) must lie '
            "between 0 and the peak friction tan(delta).",
            "error",
            "NG-CONT-126",
        ),
        (
            '*Model change, friction in step HARDENING, interaction "GROUT", Mohr-Coulomb friction with softening: '
            "the plastic slip u_r up to the residual friction (last value) must be positive.",
            "error",
            "NG-CONT-126",
        ),
        (
            "IPS: the contact pairs with the interactions GROUT-STEEL and GROUT-SOIL are merged (their slave surfaces "
            "share nodes). The interactions differ in the normal contact model or its penalty, the friction model "
            "(e.g. Coulomb with a friction coefficient of zero instead of frictionless, or Mohr-Coulomb with and "
            "without softening) or the contact options check_disp / check_dist: the interaction GROUT-STEEL is used "
            "on all faces of the merged pair.",
            "warning",
            "NG-CONT-127",
        ),
    ],
)
def test_numgeo_messages(text, severity, rule):
    m = classify(text, severity)
    assert m is not None and m.terminates == (severity == "error")
    assert rule in rules_for_source(m.file, m.line, m.candidates)
