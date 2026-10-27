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
"""Shared fixtures of the pynumgeo test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

import pynumgeo as ng
from pynumgeo.deck import Keyword

DATA = Path(__file__).parent / "data"


def small_deck() -> ng.Deck:
    """Four nodes, one quad, two sets, one material, one step: the smallest deck numgeo accepts."""
    d = ng.Deck()
    d.mesh.add_nodes([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    d.mesh.add_elements("u4-solid", [[1, 2, 3, 4]])
    d.mesh.add_elset("Soil", [1])
    d.mesh.add_nset("Base", [1, 2])
    d.mesh.add_nset("Top", [3, 4])
    m = ng.Material(name="Sand", phases=1)
    m.set_mechanical("linear_elasticity", [1.0e4, 0.3])
    m.add("*Density", data=[[2.0]])
    d.materials.append(m)
    d.assign("Soil", "Sand")
    st = ng.Step(name="Load", procedure=Keyword.make("*Static", data=[[0.1, 1.0, 1e-5, 0.5]]))
    st.add("*Boundary", data=[["Base", "u1", 0.0], ["Base", "u2", 0.0]])
    st.add("*Cload", options=["ramp"], data=[["Top", 2, -1.0]])
    d.steps.append(st)
    return d


@pytest.fixture
def deck() -> ng.Deck:
    return small_deck()
