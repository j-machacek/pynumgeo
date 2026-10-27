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
"""Include files (numgeo-GiD layout) and comments."""

from __future__ import annotations

import pytest

import pynumgeo as ng
from pynumgeo.deck import Keyword

GID = {"mesh": "model-mesh", "materials": "material-definitions"}


def test_write_texts_splits_mesh_and_materials(deck):
    texts = ng.write_texts(deck, includes=GID)
    assert set(texts) == {"main", "mesh", "materials"}
    main = texts["main"].splitlines()
    assert "*Include, input=model-mesh" in main and "*Include, input=material-definitions" in main
    assert main.index("*Include, input=model-mesh") < main.index("*Include, input=material-definitions")
    assert "*Node" in texts["mesh"] and "*Node" not in texts["main"]
    assert "*Material, name=Sand, phases=1" in texts["materials"]
    assert texts["main"].rstrip().endswith("*End input")
    for part in ("mesh", "materials"):
        assert "*End input" not in texts[part]
        assert texts[part].startswith("** =~~=")  # provenance header in every file
        assert "INCLUDE" not in "\n".join(ln for ln in texts[part].upper().splitlines() if not ln.startswith("**"))


def test_included_files_read_back_as_the_same_deck(deck, tmp_path):
    texts = ng.write_texts(deck, includes=GID)
    back = ng.parse_text(texts["main"], includes={GID[k]: v for k, v in texts.items() if k != "main"}).deck
    assert back == deck
    path = ng.write(deck, tmp_path / "model-calculation.inp", includes=GID)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "material-definitions.inp",
        "model-calculation.inp",
        "model-mesh.inp",
    ]
    res = ng.parse(path)
    assert res.ok and res.deck == deck
    assert ng.write_text(res.deck) == ng.write_text(deck)  # one file or three: the same deck


def test_parts_are_optional_and_checked(deck):
    assert set(ng.write_texts(deck, includes={"materials": "mat"})) == {"main", "materials"}
    for bad in ("model mesh", "a,b", "x.inp", "", "sub/mesh", "a=b"):
        with pytest.raises(ng.WriteError, match="include name"):
            ng.write_texts(deck, includes={"mesh": bad})
    with pytest.raises(ng.WriteError, match="unknown include parts"):
        ng.write_texts(deck, includes={"steps": "s"})
    with pytest.raises(ng.WriteError, match="same include file"):
        ng.write_texts(deck, includes={"mesh": "x", "materials": "X"})


def test_include_names_resolve_case_insensitively(deck):
    texts = ng.write_texts(deck, includes={"mesh": "Model-Mesh"})
    assert ng.parse_text(texts["main"], includes={"model-mesh": texts["mesh"]}).deck == deck
    with pytest.raises(FileNotFoundError):
        ng.parse_text(texts["main"], includes={})


def test_comments_are_written_and_ignored_when_read(deck):
    deck.mesh.comment = "nodes of the column"
    deck.mesh.blocks[0].comment = "group 'Soil': 1 quad4 element"
    deck.mesh.nsets[0].comment = "bottom edge"
    deck.materials[0].comment = "Material = Sand"
    deck.steps[0].comment = "Step 1\nloading"
    deck.steps[0].items[0].comment = "fixed base (Solid displacement)"
    text = ng.write_text(deck)
    for c in (
        "** nodes of the column",
        "** group 'Soil': 1 quad4 element",
        "** bottom edge",
        "** Material = Sand",
        "** Step 1\n** loading",
        "** fixed base (Solid displacement)",
    ):
        assert c in text
    assert ng.parse_text(text).deck == deck
    plain = ng.write_text(deck, comments=False)
    assert "** nodes" not in plain and ng.parse_text(plain).deck == deck
    assert ng.write_text(deck) == text  # deterministic


def test_long_comments_are_wrapped_and_survive_renumbering(deck):
    deck.mesh.nsets[0].comment = "word " * 200
    text = ng.write_text(deck)
    assert max(len(ln) for ln in text.splitlines()) <= 256
    new, _, _ = deck.mesh.renumbered()
    assert new.nsets[0].comment == deck.mesh.nsets[0].comment


def test_keyword_comment_in_make():
    kw = Keyword.make("*Boundary", data=[["Fix", "u1", 0.0]], comment="support")
    assert kw.comment == "support" and kw == Keyword.make("*Boundary", data=[["Fix", "u1", 0.0]])


def test_end_comment_above_end_input(deck):
    deck.end_comment = "\nStep 2\n\nStep skipped"
    text = ng.write_text(deck)
    assert text.endswith("*End step\n\n**\n** Step 2\n**\n** Step skipped\n*End input\n")
    assert ng.parse_text(text).deck == deck
    assert "Step skipped" not in ng.write_text(deck, comments=False)
