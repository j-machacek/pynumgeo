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
"""Decks written by numgeo-FreeCAD (numgeo-GiD layout: three files, GiD spelling, comments).

The fixtures in ``data/plugin-decks`` are tutorials exported by the workbench before it used pynumgeo. They must
be read without issues, round-trip, and come back the same from the three-file layout pynumgeo writes.
Set ``NUMGEO_EXAMPLES`` to a folder of further decks (e.g. the numgeo benchmarks) to round-trip those too.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import pynumgeo as ng
from conftest import DATA

PLUGIN = sorted((DATA / "plugin-decks").glob("*/*-calculation.inp"))


@pytest.mark.parametrize("calc", PLUGIN, ids=[p.parent.name for p in PLUGIN])
def test_plugin_decks_round_trip(calc, tmp_path):
    res = ng.parse(calc)
    assert res.ok, [str(i) for i in res.issues]
    assert not [i for i in ng.validate(res.deck) if i.severity == "error"]
    deck = res.deck
    assert ng.parse_text(ng.write_text(deck)).deck == deck
    model = calc.name[: -len("-calculation.inp")]
    out = ng.write(deck, tmp_path / calc.name, includes={"mesh": model + "-mesh", "materials": "material-definitions"})
    again = ng.parse(out)
    assert again.ok and again.deck == deck
    assert ng.write_texts(again.deck, includes={"mesh": model + "-mesh"}) == ng.write_texts(
        deck, includes={"mesh": model + "-mesh"}
    )


def _example_decks() -> list[Path]:
    root = os.environ.get("NUMGEO_EXAMPLES")
    if not root:
        return []
    decks = sorted(Path(root).rglob("*.inp"))
    included = set()
    for p in decks:
        text = p.read_text(errors="replace").upper()
        for line in text.splitlines():
            line = line.split("**")[0]
            if "INCLUDE" in line and "=" in line:
                included.add((p.parent / (line.split("=", 1)[1].strip() + ".INP")).as_posix().upper())
    return [p for p in decks if p.as_posix().upper() not in included]


@pytest.mark.examples
@pytest.mark.skipif(not os.environ.get("NUMGEO_EXAMPLES"), reason="set NUMGEO_EXAMPLES")
@pytest.mark.parametrize("path", _example_decks(), ids=lambda p: p.parent.name)
def test_example_decks_round_trip(path):
    deck = ng.parse(path).deck
    text = ng.write_text(deck)
    back = ng.parse_text(text).deck
    assert back == deck
    assert ng.write_text(back) == text
