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
"""Readers for numgeo's result files (numpy and the standard library only).

* :func:`open_results` -> :class:`Results` of one job: VTK frames (:meth:`Results.frames`), print output
  (:meth:`Results.print_files`, :meth:`Results.print_series`), the status file (:meth:`Results.sta`).
* Single files: :func:`read_vtu`, :func:`read_vtm`, :func:`read_pvd` (:mod:`~pynumgeo.results.vtk`),
  :func:`read_print_file`, :func:`read_print_blocks` (:mod:`~pynumgeo.results.printfiles`),
  :func:`read_sta`, :func:`read_msg_steps` (:mod:`~pynumgeo.results.sta`).
* :func:`voigt_to_tensor`: stresses/strains as tensors with explicit component order and shear.

Values are returned as numgeo writes them: total time, Voigt components in the file's order, strains with
engineering shear, reaction forces with numgeo's sign. The format details and the source
lines they come from are in the module docstrings.

Examples:
    >>> import pathlib, tempfile
    >>> d = pathlib.Path(tempfile.mkdtemp())
    >>> (d / "sim-print-out").mkdir()
    >>> _ = (d / "sim-print-out" / "SOIL.TOP_node_3.dat").write_text(
    ...     "    Time             U1             U2             U3\\n"
    ...     ".500000000E+00   0.100000E-02   0.211464-100   0.000000E+00\\n")
    >>> s = open_results(d, "sim").print_series("soil.top", kind="node", index=3)
    >>> s.columns, s.values.tolist()
    (['U1', 'U2', 'U3'], [[0.001, 2.11464e-101, 0.0]])
"""

from pynumgeo.results.printfiles import (
    PrintFileInfo,
    PrintFormatError,
    PrintKind,
    PrintSeries,
    list_print_files,
    read_print_blocks,
    read_print_file,
    read_print_rows,
)
from pynumgeo.results.results import Frame, Results, open_results
from pynumgeo.results.sta import StaRow, read_msg_steps, read_sta
from pynumgeo.results.tensors import voigt_to_tensor
from pynumgeo.results.vtk import DataArray, PvdEntry, VtmEntry, VtuData, read_pvd, read_vtm, read_vtu

__all__ = [
    "DataArray",
    "Frame",
    "PrintFileInfo",
    "PrintFormatError",
    "PrintKind",
    "PrintSeries",
    "PvdEntry",
    "Results",
    "StaRow",
    "VtmEntry",
    "VtuData",
    "list_print_files",
    "open_results",
    "read_msg_steps",
    "read_print_blocks",
    "read_print_file",
    "read_print_rows",
    "read_pvd",
    "read_sta",
    "read_vtm",
    "read_vtu",
    "voigt_to_tensor",
]
