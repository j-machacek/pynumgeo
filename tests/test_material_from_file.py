# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#                                                pynumgeo
#                              Python API for the finite element code numgeo
#                                     Copyright (C) 2026 Jan Machacek
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#
# Author: Jan Machacek (with help of Claude Opus 5.5)
#
# pynumgeo writes, checks and runs numgeo input files and reads numgeo results. It follows the
# development of numgeo: new developments in the numgeo source code are taken over into the API, and a
# CI pipeline tests every change.
#
# License: BSD-3-Clause, see LICENSE.
#
# History
# 03.11.2026, J. Machacek - Initial version (with help of Claude Opus 5.5)
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""*Assign material, elset=<set>, from-file (numgeo-src 60135dc): deck, writer, reader, catalogue, the point
file, the assignment and the checks NG-MAT-130 to NG-MAT-132 (src/input/read_solid_section_.f90)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

import pynumgeo as ng
from conftest import small_deck
from pynumgeo import catalogue as cat
from pynumgeo.deck import Section
from pynumgeo.io import material_points as mp
from pynumgeo.io.writer import WriteError

POINTS = "x;y;z;material\n0.25;0.5;0;Sand\n0.75;0.5;0;clay layer\n5;5;0;Rock\n"


def _deck(name: str = "Ground.csv") -> ng.Deck:
    d = small_deck()
    d.sections.clear()
    d.assign_from_file("Soil", name)
    return d


def _material(name: str) -> ng.Material:
    m = ng.Material(name=name, phases=1)
    m.set_mechanical("linear_elasticity", [1.0e4, 0.3])
    m.add("*Density", data=[[2.0]])
    return m


def _issues(deck: ng.Deck, workdir: Path, prefix: str = "NG-MAT-13") -> list[tuple[str, str]]:
    return [(i.id, i.message) for i in ng.validate(deck, workdir=workdir) if i.id.startswith(prefix)]


# ----------------------------------------------------------------------------- deck, writer, reader
def test_section_needs_material_or_file():
    with pytest.raises(ValidationError):
        Section(elset="Soil")
    with pytest.raises(ValidationError):
        Section(elset="Soil", material="Sand", from_file="ground.csv")
    s = Section(elset="Soil", from_file="Ground Model.CSV")
    # numgeo reads the file name in lower case and without blanks
    assert s == Section(elset="SOIL", from_file="groundmodel.csv")
    assert s != Section(elset="Soil", material="groundmodel.csv")


def test_written_with_the_file_name_in_the_next_line():
    text = ng.write_text(_deck(), header=False, comments=False)
    lines = text.splitlines()
    i = lines.index("*Assign material, elset=Soil, from-file")
    assert lines[i + 1] == "Ground.csv"
    d = _deck()
    d.sections[0].amgcl_direct = True
    assert "*Assign material, elset=Soil, from-file, amgcl=direct" in ng.write_text(d, header=False, comments=False)


@pytest.mark.parametrize("name", ["*ground.csv", "a**b.csv", " "])
def test_file_names_that_cannot_be_written(name):
    with pytest.raises(WriteError, match="cannot be written"):
        ng.write_text(_deck(name), header=False, comments=False)


def test_round_trip():
    d = _deck()
    d.sections[0].amgcl_direct = True
    again = ng.parse_text(ng.write_text(d)).deck
    assert again == d
    assert again.sections[0].from_file == "Ground.csv" and again.sections[0].material is None
    assert again.summary()["sections"] == [("Soil", "from-file Ground.csv")]


@pytest.mark.parametrize(
    ("line", "data", "ids"),
    [
        ("*Assign material, from-file, elset=Soil", ["ground.csv"], []),
        ("*Solid section, elset=Soil, from-file, amgcl=direct", ["ground.csv"], []),
        ("*Assign material, elset=Soil, from-file=ground.csv", ["ground.csv"], ["NG-READ-SEC-004"]),
        ("*Assign material, elset=Soil, material=Sand, from-file", ["ground.csv"], ["NG-READ-SEC-004"]),
        ("*Assign material, from-file", ["ground.csv"], ["NG-READ-SEC-001"]),
        ("*Assign material, elset=Soil, from-file", [], ["NG-READ-SEC-005"]),
        ("*Assign material, elset=Soil, from-file", ["a.csv", "b.csv"], ["NG-READ-SEC-005"]),
    ],
)
def test_reader(line, data, ids):
    text = "*Node\n1, 0., 0.\n2, 1., 0.\n3, 1., 1.\n*Element, type=u3-solid\n1, 1, 2, 3\n*Elset, elset=Soil\n1\n"
    res = ng.parse_text(text + "\n".join([line, *data]) + "\n")
    assert sorted(i.id for i in res.issues if i.id.startswith("NG-READ-SEC")) == ids
    if not ids:
        (s,) = res.deck.sections
        assert (s.elset, s.material, s.from_file) == ("Soil", None, "ground.csv")


def test_catalogue():
    spec = cat.keyword("*Assign material")
    opt = {o.name: o for o in spec.options}
    assert opt["FROM-FILE"].value_type == "flag" and "60135dc" in opt["FROM-FILE"].notes
    assert not opt["MATERIAL"].required and opt["ELSET"].required
    (dl,) = spec.data_lines
    assert [f["name"] for f in dl.fields] == ["file"] and "FROM-FILE" in dl.count_rule
    page = cat.load().doc_page(spec.doc)
    assert page is not None and "## Materials from a point file" in page


# ----------------------------------------------------------------------------- point file
def test_point_file(tmp_path):
    p = tmp_path / "p.csv"
    text = "﻿x_m;y_m;z_m;mat\r\n\r\n1.5;-2;0d0;Layer 1;\r\n\t3e-1 ; +.5 ;7.;LAYER1\r\n4;5;6;sand\r\n"
    p.write_bytes(text.encode("utf-8"))
    pts = mp.read_material_points(p)
    assert pts.header == "x_m;y_m;z_m;mat"
    assert pts.coords.tolist() == [[1.5, -2.0, 0.0], [0.3, 0.5, 7.0], [4.0, 5.0, 6.0]]
    assert pts.names == ("LAYER1", "SAND") and pts.point_name.tolist() == [0, 0, 1]
    assert pts.lines.tolist() == [3, 4, 5]


def test_first_line_with_a_number_is_a_point(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("x;2;z;a\n1;2;3;b\n")
    with pytest.raises(mp.MaterialPointsError, match=r'line 1 .* invalid coordinate "x"'):
        mp.read_material_points(p)


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("1;2;3", "has 3 fields"),
        ("1;2;3;a;b", "has 5 fields"),
        ("1;2,5;3;a", 'invalid coordinate "2,5"'),
        ("1;2;3e;a", 'invalid coordinate "3e"'),
        ("1;inf;3;a", 'invalid coordinate "inf"'),
        ("1;2;1e400;a", 'invalid coordinate "1e400"'),
        ("1;2;3;  ", "contains no material name"),
        ("1;2;3;" + "a" * 257, "more than 256 characters"),
    ],
)
def test_invalid_lines(tmp_path, line, message):
    p = tmp_path / "p.csv"
    p.write_text(f"x;y;z;m\n0;0;0;ok\n{line}\n9;9;9;also-wrong;x;\n")
    with pytest.raises(mp.MaterialPointsError, match=rf"line 3 .*{message}"):
        mp.read_material_points(p)


def test_file_without_points(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("x;y;z;m\n\n")
    with pytest.raises(mp.MaterialPointsError, match="no data points"):
        mp.read_material_points(p)


# ----------------------------------------------------------------------------- nearest point
def test_tie_rule_takes_the_point_given_first():
    pts = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0 - 1e-12]])
    idx, dist = mp.nearest_points(pts, [[0.0, 0.0], [0.0, 0.9]], tolerance=1e-9)
    assert idx.tolist() == [0, 1] and dist.tolist() == [1.0, pytest.approx(0.1)]
    idx, _ = mp.nearest_points(pts[::-1], [[0.0, 0.0]], tolerance=1e-9)
    assert idx.tolist() == [0]  # the point at distance 1 + 1e-12 counts as equidistant


@pytest.mark.parametrize("ndim", [2, 3])
def test_grid_search_equals_brute_force(ndim):
    rng = np.random.default_rng(3)
    pts = rng.uniform(-1.0, 1.0, (700, ndim))
    grid = np.stack(np.meshgrid(*[np.arange(5.0)] * ndim, indexing="ij"), -1).reshape(-1, ndim)
    pts = np.vstack([pts, grid])  # exact ties at the midpoints of the grid cells
    qs = np.vstack([rng.uniform(-3.0, 6.0, (900, ndim)), grid + 0.5, [[50.0] * ndim]])
    tol = mp.TIE_TOLERANCE * float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0)))
    g = mp._Grid(pts).nearest(qs, tol)
    b = mp._brute(pts, qs, tol)
    assert np.array_equal(g[0], b[0]) and np.array_equal(g[1], b[1])


# ----------------------------------------------------------------------------- checks
def test_assignment_and_undefined_names(tmp_path):
    (tmp_path / "ground.csv").write_text(POINTS)
    d = _deck()
    # the centroid (0.5, 0.5) is equidistant to Sand and clay layer: Sand, given first
    found = _issues(d, tmp_path)
    assert [i for i, _ in found] == ["NG-MAT-132"]
    assert "CLAYLAYER, ROCK of the file not defined" in found[0][1]
    d.materials[0].name = "Clay Layer"
    found = _issues(d, tmp_path)
    assert [i for i, _ in found] == ["NG-MAT-131", "NG-MAT-132"]
    assert "SAND (1 element(s)) assigned to elements of the set" in found[0][1]
    assert "ROCK of the file" in found[1][1] and "CLAYLAYER" not in found[1][1]
    # NG-REF-001 checks the element set only
    assert [i.id for i in ng.validate(d, workdir=tmp_path) if i.id == "NG-REF-001"] == []


def test_three_dimensional_analyses_use_z(tmp_path):
    d = ng.Deck()
    d.mesh.add_nodes([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
    d.mesh.add_elements("u8-solid-3d", [[1, 2, 3, 4, 5, 6, 7, 8]])
    d.mesh.add_elset("Soil", [1])
    d.materials += [_material("Top"), _material("Bottom")]
    d.assign_from_file("Soil", "p.csv")
    (tmp_path / "p.csv").write_text("0.5;0.5;5;bottom\n0.5;0.5;0.6;top\n")  # nearest in 3D: top
    assert _issues(d, tmp_path) == []
    (tmp_path / "p.csv").write_text("0.5;0.5;5;top\n0.5;0.5;0.6;deep\n")
    assert [i for i, _ in _issues(d, tmp_path)] == ["NG-MAT-131"]


def test_missing_file(tmp_path):
    (tmp_path / "Ground.csv").write_text(POINTS)
    found = _issues(_deck("sub dir/Ground.csv"), tmp_path)
    assert [i for i, _ in found] == ["NG-MAT-130"]
    assert "'subdir/ground.csv' (given as 'sub dir/Ground.csv') does not exist" in found[0][1]


def test_invalid_file(tmp_path):
    (tmp_path / "ground.csv").write_text("x;y;z;m\n0;0;0;sand\n1;0,5;0;sand\n")
    found = _issues(_deck(), tmp_path)
    assert [i for i, _ in found] == ["NG-MAT-130"]
    assert "line 3 of the file" in found[0][1] and 'invalid coordinate "0,5"' in found[0][1]


def test_set_members_unknown_to_pynumgeo(tmp_path):
    (tmp_path / "ground.csv").write_text(POINTS)
    d = _deck()
    d.mesh.elsets[0].members = np.zeros(0, dtype=np.int64)
    d.mesh.elsets[0].kind = "find"
    found = _issues(d, tmp_path)
    assert [i for i, _ in found] == ["NG-MAT-132"]
    assert "numgeo stops if one of them is assigned to an element (not checked" in found[0][1]


def test_command_line_looks_next_to_the_input_file(tmp_path, capsys):
    from pynumgeo.cli.__main__ import main

    (tmp_path / "ground.csv").write_text("x;y;z;m\n0.5;0.5;0;sand\n9;9;0;gravel\n")
    inp = tmp_path / "model.inp"
    inp.write_text(ng.write_text(_deck("ground.csv")))
    main(["validate", str(inp)])
    out = capsys.readouterr().out
    assert "NG-MAT-132" in out and "GRAVEL of the file not defined" in out and "NG-MAT-130" not in out
