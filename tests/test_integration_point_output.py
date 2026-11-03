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
# 02.11.2026, J. Machacek - Initial version (with help of Claude Opus 5.5)
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""*Integration point in *Output, field (numgeo-src working tree of 02.11.2026): catalogue, check, writer and the
dataset ``Integration points`` of the results (src/input/read_step_.f90:1917-1959,
src/output/VTK_write_results_.f90:248-291)."""

from __future__ import annotations

from pathlib import Path

import pytest

import pynumgeo as ng
from conftest import small_deck
from pynumgeo import catalogue as cat
from pynumgeo.deck import Keyword
from pynumgeo.results import open_results


def _deck(*cards: Keyword) -> ng.Deck:
    d = small_deck()
    d.steps[0].add("*Output", options=["field", "vtk", "binary"], children=list(cards))
    return d


def _kw_ids(deck: ng.Deck) -> list[str]:
    return [i.id for i in ng.validate(deck) if i.id.startswith("NG-KW")]


def test_catalogue_knows_the_field_card():
    spec = cat.keyword("*Integration point", "output-field")
    assert spec.parent == "*OUTPUT,FIELD" and not spec.options
    assert spec.doc == "docs/reference/output/field.md#integration-point-output"
    # the print card keeps its mandatory element set
    assert [o.name for o in cat.keyword("*Integration point", "output-print").options] == ["ELSET"]


def test_field_card_is_accepted():
    d = _deck(Keyword.make("*Element output", data=[["S", "E"]]),
              Keyword.make("*Integration point", data=[["S", "E", "VOID"]]))
    assert _kw_ids(d) == []


def test_field_card_takes_no_element_set():
    d = _deck(Keyword.make("*Integration point", options=[("elset", "Soil")], data=[["S"]]))
    found = [i for i in ng.validate(d) if i.id.startswith("NG-KW")]
    assert [i.id for i in found] == ["NG-KW-010"]
    assert "unknown option 'elset=soil' of *Integration point (numgeo stops; it takes no options" in found[0].message


def test_written_under_the_field_output():
    d = _deck(Keyword.make("*Integration point", data=[["S", "E"]]))
    text = ng.write_text(d, header=False, comments=False)
    lines = [line.strip() for line in text.splitlines()]
    i = next(k for k, line in enumerate(lines) if line.lower().startswith("*output, field"))
    assert [line.upper() for line in lines[i + 1:i + 3]] == ["*INTEGRATION POINT", "S, E"]
    again = ng.parse_text(text).deck
    out = again.steps[0].keywords("*Output")[0]
    assert [c.keyword for c in out.children] == ["*INTEGRATIONPOINT"]


_IP_VTU = """<?xml version="1.0"?>
<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">
  <UnstructuredGrid>
    <Piece NumberOfPoints="2" NumberOfCells="2">
      <Points><DataArray type="Float64" NumberOfComponents="3" format="ascii">
        0.25 0.25 0.0 0.75 0.25 0.0 </DataArray></Points>
      <Cells>
        <DataArray Name="connectivity" type="Int32" format="ascii"> 0 1 </DataArray>
        <DataArray Name="offsets" type="Int32" format="ascii"> 1 2 </DataArray>
        <DataArray type="UInt8" Name="types" format="ascii"> 1 1 </DataArray>
      </Cells>
      <PointData>
        <DataArray Name="IntegrationPoint" type="Int32" format="ascii"> 1 2 </DataArray>
        <DataArray Name="Stress" type="Float64" NumberOfComponents="6" format="ascii">
          -1.0 -4.0 -1.0 0.5 0.0 0.0 -2.0 -4.0 -2.0 0.0 0.0 0.0 </DataArray>
      </PointData>
      <CellData>
        <DataArray Name="ElementLabel" type="Int32" format="ascii"> 1 1 </DataArray>
        <DataArray Name="MaterialID" type="Int32" format="ascii"> 1 1 </DataArray>
      </CellData>
    </Piece>
  </UnstructuredGrid>
</VTKFile>
"""


def _results(tmp_path: Path, with_ip: bool) -> Path:
    out = tmp_path / "job-out"
    out.mkdir()
    (out / "job-ip-1-1.vtu").write_text(_IP_VTU)
    ip = '    <DataSet index="1" name="Integration points" file="job-ip-1-1.vtu"/>\n' if with_ip else ""
    (out / "job-all-results-1-1.vtm").write_text(
        '<?xml version="1.0"?>\n<VTKFile type="vtkMultiBlockDataSet" version="1.0" byte_order="LittleEndian">\n'
        f"  <vtkMultiBlockDataSet>\n{ip}  </vtkMultiBlockDataSet>\n</VTKFile>\n")
    (tmp_path / "job-all-results.pvd").write_text(
        '<?xml version="1.0"?>\n<VTKFile type="Collection" version="0.1">\n  <Collection>\n'
        '    <DataSet timestep="1.0" part="0" file="job-out/job-all-results-1-1.vtm"/>\n'
        "  </Collection>\n</VTKFile>\n")
    return tmp_path


def test_frame_integration_points(tmp_path):
    frame = open_results(_results(tmp_path, True), "job").frames()[-1]
    ip = frame.integration_points
    assert ip.name == "Integration points" and ip.block == ()
    assert ip.point_data("IntegrationPoint").tolist() == [1, 2]
    assert ip.point_data("Stress")[:, 0].tolist() == [-1.0, -2.0]
    assert ip.element_labels.tolist() == [1, 1]
    assert ip.points[:, 0].tolist() == [0.25, 0.75]


def test_frame_without_integration_points(tmp_path):
    frame = open_results(_results(tmp_path, False), "job").frames()[-1]
    with pytest.raises(KeyError, match=r"\*Integration point in the \*Output, field"):
        frame.integration_points
