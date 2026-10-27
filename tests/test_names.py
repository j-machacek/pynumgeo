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
"""Names numgeo would read as options: interactions are covered like sets and materials."""

from __future__ import annotations

import pytest

import pynumgeo as ng
from pynumgeo.deck import Keyword
from pynumgeo.deck.names import _SHORT, RISKY_WORDS, risky_words, safe_name
from pynumgeo.validation.rules import behaviour


def _with_contact(deck: ng.Deck, name: str) -> ng.Deck:
    deck.mesh.add_surface("S1", [("Base",)], type="node")
    deck.mesh.add_surface("S2", [("Top",)], type="node")
    deck.keywords.append(
        Keyword.make(
            "*Interaction", options=[("name", name)], children=[Keyword.make("*Normal", options=["mechanical=penalty"])]
        )
    )
    deck.keywords.append(
        Keyword.make("*Contact pair", options=[("interaction", name), ("discretisation", "ntn")], data=[["S1", "S2"]])
    )
    deck.keywords.append(Keyword.make("*Contact options", options=[("name", name), ("clearance", "1e-6")]))
    return deck


@pytest.mark.parametrize("name", ["UserPile", "LongPile", "General_contact", "Refined", "soil normal"])
def test_writer_refuses_risky_interaction_names(deck, name):
    with pytest.raises(ng.WriteError, match="interaction"):
        ng.write_text(_with_contact(deck, name))


@pytest.mark.parametrize("name", ["UserPile", "LongPile", "General_contact"])
def test_safe_names_renames_interactions_and_their_references(deck, name):
    d = _with_contact(deck, name)
    assert any(i.id in ("NG-CONT-107", "NG-CONT-108") for i in ng.validate(d))
    mapping = d.safe_names()
    new = mapping[name]
    assert not risky_words("interaction", new)
    assert d.keywords[0].option("NAME") == new
    assert d.keywords[1].option("INTERACTION") == new
    assert d.keywords[2].option("NAME") == new
    assert not [i for i in ng.validate(d) if i.id in ("NG-CONT-107", "NG-CONT-108", "NG-CONT-109")]
    assert ng.parse_text(ng.write_text(d)).deck == d


def test_interaction_words_cover_the_validator():
    words = set(RISKY_WORDS["interaction"])
    pair = {w for w in behaviour._PAIR_WORDS if not w.endswith("=")}
    assert set(behaviour._INTERACTION_WORDS) <= words
    assert pair <= words
    assert set(behaviour._OPTIONS_WORDS) <= words


def test_short_forms_are_safe_for_every_kind():
    for words in RISKY_WORDS.values():
        for w in words:
            for kind in RISKY_WORDS:
                assert not risky_words(kind, _SHORT[w]), (w, kind)


def test_safe_name_handles_blanks_and_case():
    assert safe_name("interaction", "soil-water-filled gap") == "soil-water-gap"
    assert safe_name("node set", "Find Fix") == "Fnd Fix"
    assert safe_name("interaction", "LongPile") == "Lon_gpile"
    assert safe_name("interaction", "USER") == "USR"
