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
"""VTK output of numgeo-src 7052b69: ``*Output, field, vtk, binary-zlib`` (src/output/VTK_AppendedData_type_.f90:
380-462) read by :func:`pynumgeo.results.vtk.read_vtu`, and the element output variables ``SF`` and ``IP``."""

from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np
import pytest

import pynumgeo as ng
from conftest import small_deck
from pynumgeo import catalogue as cat
from pynumgeo.deck import Keyword
from pynumgeo.results.vtk import read_vtu

_ARRAYS = {
    # name: (location, VTK type, components, values)
    "points": ("Points", "Float64", 3, np.arange(12, dtype="<f8") * 0.5),
    "connectivity": ("Cells", "Int32", 1, np.array([0, 1, 2, 3], dtype="<i4")),
    "offsets": ("Cells", "Int32", 1, np.array([4], dtype="<i4")),
    "types": ("Cells", "UInt8", 1, np.array([9], dtype="u1")),
    "NodeLabel": ("PointData", "Int32", 1, np.array([1, 2, 3, 4], dtype="<i4")),
    "Stress": ("PointData", "Float64", 6, np.linspace(-1.0, 1.0, 24).astype("<f8")),
    "ElementLabel": ("CellData", "Int32", 1, np.array([7], dtype="<i4")),
}


def _block(raw: bytes, zlib_block: int | None) -> bytes:
    """Appended block as numgeo writes it: UInt64 byte count + data, or the vtkZLibDataCompressor layout."""
    if zlib_block is None:
        return np.uint64(len(raw)).tobytes() + raw
    chunks = [zlib.compress(raw[i : i + zlib_block], 6) for i in range(0, len(raw), zlib_block)]
    header = [len(chunks), zlib_block, len(raw) % zlib_block, *(len(c) for c in chunks)]
    return np.array(header, dtype="<u8").tobytes() + b"".join(chunks)


def _vtu(path: Path, zlib_block: int | None, compressor: str = "vtkZLibDataCompressor") -> Path:
    """One quad with appended data; with ``zlib_block`` compressed in blocks of that many bytes."""
    xml: dict[str, list[str]] = {"Points": [], "Cells": [], "PointData": [], "CellData": []}
    data = b""
    for name, (where, vtk_type, ncomp, values) in _ARRAYS.items():
        attr = "" if name == "points" else f' Name="{name}"'
        xml[where].append(
            f'<DataArray type="{vtk_type}"{attr} NumberOfComponents="{ncomp}" format="appended" offset="{len(data)}"/>'
        )
        data += _block(values.tobytes(), zlib_block)
    comp = f' compressor="{compressor}"' if zlib_block is not None else ""
    head = (
        f'<?xml version="1.0"?>\n<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian" '
        f'header_type="UInt64"{comp}>\n<UnstructuredGrid>\n<Piece NumberOfPoints="4" NumberOfCells="1">\n'
        + "".join(f"<{k}>\n{''.join(v)}\n</{k}>\n" for k, v in xml.items())
        + '</Piece>\n</UnstructuredGrid>\n  <AppendedData encoding="raw">\n_'
    )
    path.write_bytes(head.encode("ascii") + data + b"\n  </AppendedData>\n</VTKFile>\n")
    return path


def _same(a, b) -> None:
    assert np.array_equal(a.points, b.points) and np.array_equal(a.connectivity, b.connectivity)
    assert np.array_equal(a.offsets, b.offsets) and np.array_equal(a.types, b.types)
    assert a.point_names == b.point_names and a.cell_names == b.cell_names
    for n in a.point_names:
        assert a.point_data(n).dtype == b.point_data(n).dtype and np.array_equal(a.point_data(n), b.point_data(n))
    for n in a.cell_names:
        assert np.array_equal(a.cell_data(n), b.cell_data(n))


@pytest.mark.parametrize("block", [1048576, 16, 8, 5])
def test_zlib_blocks_read_like_raw_binary(tmp_path, block):
    # 16 and 8 divide every array (last block full: size 0 in the header), 5 leaves partial last blocks
    plain = read_vtu(_vtu(tmp_path / "plain.vtu", None))
    packed = read_vtu(_vtu(tmp_path / "zlib.vtu", block))
    _same(plain, packed)
    assert packed.point_data("Stress").shape == (4, 6) and packed.element_labels.tolist() == [7]


def test_other_compressors_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="compressor 'vtkLZ4DataCompressor' is not supported"):
        read_vtu(_vtu(tmp_path / "lz4.vtu", 64, compressor="vtkLZ4DataCompressor"))


def test_damaged_zlib_data(tmp_path):
    p = _vtu(tmp_path / "zlib.vtu", 64)
    raw = bytearray(p.read_bytes())
    start = raw.index(b"_", raw.index(b"<AppendedData")) + 1
    # first array (points, 96 bytes): header of 3 + 2 UInt64 values, then the first compressed block
    raw[start + 5 * 8 + 2] ^= 0xFF
    p.write_bytes(bytes(raw))
    with pytest.raises(ValueError, match="Points array '': block 1 of 2"):
        read_vtu(p)
    p = _vtu(tmp_path / "size.vtu", 64)
    raw = bytearray(p.read_bytes())
    raw[start + 2 * 8 : start + 3 * 8] = np.uint64(40).tobytes()  # last block claims 40 instead of 32 bytes
    p.write_bytes(bytes(raw))
    with pytest.raises(ValueError, match="block 2 of 2 has 32 bytes, the header says 40"):
        read_vtu(p)


def test_catalogue_output():
    out = cat.keyword("*Output", "step")
    names = [o.name for o in out.options]
    assert names.index("ASCII") < names.index("BINARY-ZLIB") < names.index("BINARY")
    assert "7052b69" in out.option("binary-zlib").notes
    section = cat.load().section("output", "output_variables")
    by_key = {v["key"]: v for v in section}
    assert by_key["SF"]["location"] == by_key["IP"]["location"] == "dataset"
    assert by_key["SF"]["components"] == ["N", "Qy", "Qz", "Mx", "My", "Mz"]
    files = [f["name_pattern"] for f in cat.load().section("output", "result_files")]
    assert (
        "<job>-out/<job>-sections-<istep>-<counter>.vtu" in files
        and "<job>-out/<job>-ip-<istep>-<counter>.vtu" in files
    )
    counts = cat.load().section("output", "counts")
    assert counts["output_variables"] == len(section) and counts["result_files"] == len(files)
    page = cat.load().doc_page("docs/reference/output/field.md")
    assert page is not None and "binary-zlib" in page and "- `SF` (only vtk" in page and "- `IP` (only vtk" in page


def test_deck_with_compressed_output_sections_and_ip():
    d = small_deck()
    d.steps[0].add(
        "*Output",
        options=["field", "vtk", "binary-zlib"],
        children=[Keyword.make("*Element output", data=[["S", "SF", "IP", "MAT"]])],
    )
    assert [i.id for i in ng.validate(d) if i.id.startswith(("NG-KW", "NG-OUT"))] == []
    text = ng.write_text(d, header=False, comments=False)
    assert "*Output, field, vtk, binary-zlib" in text.splitlines()
    assert ng.parse_text(text).deck == d
