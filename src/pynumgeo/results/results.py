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
"""The results of one numgeo run: :func:`open_results`, :class:`Results`, :class:`Frame`.

File names follow the job name ``<job>`` (command-line ``out=``, else the input name without ``.inp``;
``src/input/read_command_prompt_.f90:102,165``): ``<job>-all-results.pvd`` and ``<job>-out/`` (VTK),
``<job>-print-out/`` (print output), ``<job>.sta``, ``<job>.msg``.

Examples:
    >>> import pathlib, tempfile
    >>> d = pathlib.Path(tempfile.mkdtemp())
    >>> (d / "sim-print-out").mkdir()
    >>> _ = (d / "sim-print-out" / "LOAD_node_2.dat").write_text(
    ...     "    Time             U1             U2             U3\\n"
    ...     ".100000000E+01   0.000000E+00  -0.152739E-01   0.000000E+00\\n")
    >>> res = open_results(d, job="sim")
    >>> [(f.set_name, f.kind, f.index) for f in res.print_files()]
    [('LOAD', 'node', 2)]
    >>> float(res.print_series("Load", kind="node").column("U2")[-1])
    -0.0152739
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from pynumgeo.results.printfiles import (
    PrintFileInfo,
    PrintKind,
    PrintSeries,
    list_print_files,
    read_print_file,
)
from pynumgeo.results.sta import StaRow, read_msg_steps, read_sta
from pynumgeo.results.vtk import VtuData, cell_blocks, read_pvd, read_vtm, read_vtu

__all__ = ["MODEL_BLOCK", "Frame", "Results", "open_results"]

#: Name of the ``.vtm`` block holding the 1D/2D/3D model datasets (VTK_write_results_.f90:1135).
MODEL_BLOCK = "Model elements"
#: Relative tolerance for matching a frame time with the ``g11.4`` times of the ``.sta`` (4 digits).
_STA_RTOL = 5.1e-4

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]


class Frame:
    """One written VTK frame (one ``<DataSet>`` of the ``.pvd``); datasets are read on first use.

    Attributes:
        path: the ``.vtm`` file.
        time: total time from the ``.pvd`` (full precision).
        step: step number from the file name ``<job>-all-results-<step>-<counter>.vtm``
            (VTK_write_results_.f90:147-150), ``None`` if the name does not follow it.
        counter: number of the frame within its step (starts at 1 in every step; it is not the increment).
        step_name: step name (upper case) from the ``.msg`` file, ``None`` if unknown.
        increment: increment of the frame, ``None`` if not determinable. numgeo does not write it into the
            VTK files; it is taken from the ``.sta`` rows of the same step that are not known to be rejected
            and whose total time equals :attr:`time` within the 4 digits of the ``.sta``, if they name
            exactly one increment. Needs the ``.msg`` file for the step numbers.

    The frame-level properties (:attr:`points`, :attr:`cells`, :meth:`point_data`, ...) concatenate the
    datasets of the block ``Model elements`` (``1D elements``, ``2D elements``, ``3D elements``) in this
    order. Each dataset has its own points, so a node shared by beam and solid elements appears in both
    (with the nodal averages of its own dataset, VTK_write_results_.f90:291-339). With ``EMBEDDED``
    output, embedded regions and their guest beams are separate datasets; use
    :attr:`datasets` for them.
    """

    def __init__(
        self,
        path: Path,
        time: float,
        step: int | None,
        counter: int | None,
        step_name: str | None = None,
        increment: int | None = None,
    ) -> None:
        self.path = path
        self.time = time
        self.step = step
        self.counter = counter
        self.step_name = step_name
        self.increment = increment
        self._datasets: list[VtuData] | None = None

    def __repr__(self) -> str:
        return (
            f"Frame(step={self.step}, counter={self.counter}, step_name={self.step_name!r}, "
            f"increment={self.increment}, time={self.time!r}, path={str(self.path)!r})"
        )

    @property
    def datasets(self) -> list[VtuData]:
        """All datasets of the ``.vtm`` in file order (with :attr:`VtuData.name`, :attr:`VtuData.block`)."""
        if self._datasets is None:
            self._datasets = [read_vtu(e.file, name=e.name, block=e.block) for e in read_vtm(self.path)]
        return self._datasets

    @property
    def model_datasets(self) -> list[VtuData]:
        """The datasets of the block ``Model elements``."""
        return [d for d in self.datasets if d.block[:1] == (MODEL_BLOCK,)]

    def dataset(self, name: str) -> VtuData:
        """The dataset with this name (e.g. ``"2D elements"``).

        Raises:
            KeyError: no or more than one dataset with this name.
        """
        found = [d for d in self.datasets if d.name == name]
        if len(found) != 1:
            raise KeyError(f"{len(found)} datasets named {name!r} in {self.path}: {[d.name for d in self.datasets]}")
        return found[0]

    @property
    def points(self) -> FloatArray:
        """``(n, 3)`` point coordinates of the model datasets."""
        parts = [d.points for d in self.model_datasets]
        return np.concatenate(parts) if parts else np.zeros((0, 3))

    @property
    def cells(self) -> list[tuple[int, IntArray]]:
        """Cells of the model datasets as ``(vtk_type, connectivity[k, nodes_per_cell])`` blocks.

        Connectivity indexes :attr:`points` (0-based); the blocks in order give the cells in the order of
        :meth:`cell_data`. VTK cell types are numgeo's (e.g. 3 line, 9 quad, 23 quad8, 12 hexahedron) and
        node order is numgeo's element node order (VTK_write_cells_.f90:87-104).
        """
        blocks: list[tuple[int, IntArray]] = []
        shift = 0
        for d in self.model_datasets:
            blocks.extend((t, c + shift) for t, c in cell_blocks(d.connectivity, d.offsets, d.types))
            shift += d.number_of_points
        return blocks

    @property
    def node_labels(self) -> IntArray:
        """Node label of each point (``NodeLabel``)."""
        return np.asarray(self.point_data("NodeLabel"), dtype=np.int64)

    @property
    def element_labels(self) -> IntArray:
        """Element label of each cell (``ElementLabel``)."""
        return np.asarray(self.cell_data("ElementLabel"), dtype=np.int64)

    @property
    def point_names(self) -> list[str]:
        """``PointData`` names present in every model dataset (order of the first)."""
        return _common_names([d.point_names for d in self.model_datasets])

    @property
    def cell_names(self) -> list[str]:
        """``CellData`` names present in every model dataset (order of the first)."""
        return _common_names([d.cell_names for d in self.model_datasets])

    def point_data(self, name: str) -> npt.NDArray[Any]:
        """``PointData`` array over all model datasets (names as numgeo writes them, blanks stripped)."""
        return _concat([d.point_data for d in self.model_datasets], name, self.path)

    def cell_data(self, name: str) -> npt.NDArray[Any]:
        """``CellData`` array over all model datasets (names as numgeo writes them, blanks stripped)."""
        return _concat([d.cell_data for d in self.model_datasets], name, self.path)


def _common_names(lists: Sequence[list[str]]) -> list[str]:
    if not lists:
        return []
    rest = [set(n) for n in lists[1:]]
    return [n for n in lists[0] if all(n in r for r in rest)]


def _concat(getters: Sequence[Any], name: str, path: Path) -> npt.NDArray[Any]:
    if not getters:
        raise KeyError(f"{path}: no dataset in the block {MODEL_BLOCK!r}")
    parts = []
    for get in getters:
        try:
            parts.append(get(name))
        except KeyError as exc:
            raise KeyError(f"{exc.args[0]} (frame {path}; use Frame.datasets for single datasets)") from None
    return np.concatenate(parts)


class Results:
    """Result files of one job in one folder (see :func:`open_results`)."""

    def __init__(self, workdir: str | Path, job: str = "job") -> None:
        self.workdir = Path(workdir)
        self.job = job

    def __repr__(self) -> str:
        return f"Results(workdir={str(self.workdir)!r}, job={self.job!r})"

    @property
    def pvd_path(self) -> Path:
        """``<job>-all-results.pvd`` (VTK_type.f90:1204)."""
        return self.workdir / f"{self.job}-all-results.pvd"

    @property
    def print_dir(self) -> Path:
        """``<job>-print-out`` (print_type.f90:93)."""
        return self.workdir / f"{self.job}-print-out"

    @property
    def sta_path(self) -> Path:
        """``<job>.sta`` (report_construct_.f90:51)."""
        return self.workdir / f"{self.job}.sta"

    @property
    def msg_path(self) -> Path:
        """``<job>.msg`` (report_construct_.f90:53)."""
        return self.workdir / f"{self.job}.msg"

    def step_names(self) -> dict[int, str]:
        """Step number -> name (upper case) of the executed steps, from the ``.msg`` file ({} without it)."""
        if not self.msg_path.is_file():
            return {}
        return dict(read_msg_steps(self.msg_path))

    def sta(self) -> list[StaRow]:
        """Increment rows of ``<job>.sta`` (see :func:`pynumgeo.results.read_sta`), with step numbers
        from the ``.msg`` file when it exists.

        Raises:
            FileNotFoundError: no ``.sta`` file.
        """
        if not self.sta_path.is_file():
            raise FileNotFoundError(f"{self.sta_path} not found")
        numbers = None
        if self.msg_path.is_file():
            numbers = [n for n, _ in read_msg_steps(self.msg_path)]
        return read_sta(self.sta_path, step_numbers=numbers)

    def frames(self) -> list[Frame]:
        """All VTK frames in the order of the ``.pvd``.

        Raises:
            FileNotFoundError: no ``.pvd`` (the run wrote no VTK field output).
        """
        if not self.pvd_path.is_file():
            raise FileNotFoundError(f"{self.pvd_path} not found: the run wrote no VTK field output")
        names = self.step_names()
        rows = self.sta() if self.sta_path.is_file() else []
        pattern = re.compile(rf"^{re.escape(self.job)}-all-results-(\d+)-(\d+)\.vtm$")
        frames = []
        for e in read_pvd(self.pvd_path):
            m = pattern.match(e.file.name)
            step = int(m.group(1)) if m else None
            counter = int(m.group(2)) if m else None
            name = names.get(step) if step is not None else None
            frames.append(Frame(e.file, e.time, step, counter, name, _increment(rows, step, e.time)))
        return frames

    def print_files(self) -> list[PrintFileInfo]:
        """The print files of the run (``[]`` if there is no ``<job>-print-out`` folder)."""
        if not self.print_dir.is_dir():
            return []
        return list_print_files(self.print_dir)

    def print_series(
        self,
        set_name: str,
        kind: PrintKind = "node",
        index: int | None = None,
        *,
        columns: Sequence[str] | None = None,
    ) -> PrintSeries:
        """Read the print file of one set member.

        Args:
            set_name: set name, compared case-insensitively (numgeo upper-cases it); sets of an instance
                are named ``"Instance.Set"``.
            kind: ``node``, ``element`` or ``ip``.
            index: node label or element number in the file name; may be omitted if the set has one file.
            columns: column names to use instead of the header (see
                :func:`pynumgeo.results.read_print_file`).

        Raises:
            FileNotFoundError: no such file (the message lists what exists).
            ValueError: ``index`` omitted but the set has several files.
        """
        key = set_name.strip().casefold()
        files = [f for f in self.print_files() if f.kind == kind and f.set_name.casefold() == key]
        if not files:
            sets = sorted({f.set_name for f in self.print_files() if f.kind == kind})
            raise FileNotFoundError(f"no {kind} print file for set {set_name!r} in {self.print_dir}; sets: {sets}")
        if index is None:
            if len(files) > 1:
                indices = [f.index for f in files]
                raise ValueError(f"set {set_name!r} has {len(files)} {kind} files, pass index= one of {indices}")
            return read_print_file(files[0].path, kind=kind, columns=columns)
        chosen = [f for f in files if f.index == index]
        if not chosen:
            raise FileNotFoundError(f"no {kind} file {index} for set {set_name!r}; indices: {[f.index for f in files]}")
        return read_print_file(chosen[0].path, kind=kind, columns=columns)


def _increment(rows: list[StaRow], step: int | None, time: float) -> int | None:
    if step is None:
        return None
    found = {
        r.increment
        for r in rows
        if r.step_number == step
        and r.accepted is not False
        and r.total_time is not None
        and math.isclose(r.total_time, time, rel_tol=_STA_RTOL, abs_tol=1e-300)
    }
    return found.pop() if len(found) == 1 else None


def open_results(workdir: str | Path, job: str = "job") -> Results:
    """Open the results of job ``job`` in ``workdir``.

    Raises:
        FileNotFoundError: ``workdir`` is not a folder, or it holds none of ``<job>-all-results.pvd``,
            ``<job>-print-out/``, ``<job>.sta``.
    """
    res = Results(workdir, job)
    if not res.workdir.is_dir():
        raise FileNotFoundError(f"{res.workdir} is not a folder")
    if not (res.pvd_path.is_file() or res.print_dir.is_dir() or res.sta_path.is_file()):
        raise FileNotFoundError(f"no results of job {job!r} in {res.workdir}")
    return res
