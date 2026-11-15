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
# 26.10.2026, J. Machacek - Initial version
# 13.11.2026, J. Machacek - Strength reduction with arc-length control: StaRow.control, ArcLengthSummary
# 14.11.2026, J. Machacek - Summary of numgeo-src of 14.11.2026: FoS of the plateau at the end, first plateau
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""Reader for the status file ``<job>.sta`` and the step headers of ``<job>.msg``.

Writers: ``src/report/report_statistics.f90`` (``report_step`` :45-160, ``report_increment`` :184-324),
called from ``src/main.f90:322,337`` (step start/end) and ``src/main.f90:916`` (every increment
attempt). Each executed step starts with ``-> Step = <NAME>`` (upper case) and ``Type = <TYPE>``; one row
is written per increment **attempt**, also for rejected attempts (cut-back retries keep the increment
number, ``src/main.f90:574-579``):

=====================  ===============================================================  ============
step type              row (format)                                                     source
=====================  ===============================================================  ============
GEOSTATIC, STATIC,     inc, iterations, total time, step time, dt, rejection text        :207, :316
TRANSIENT, DYNAMIC     ``(4x,I6,6x,I3,7x,g11.4,4x,g11.4,4x,g11.4,2x,A)``
REDUCTION              inc, iterations, FoS, dFoS, max. displacement, rejection text     :207, :287
REDUCTION with         inc, iterations, FoS, dFoS, max. displacement, control ``F`` or   :248, :333
arc-length control     ``A`` (column ``Ctrl``), rejection text
                       ``(4x,I6,6x,I3,7x,g11.4,4x,g11.4,4x,g11.4,4x,A1,2x,A)``
EXPLICIT DYNAMIC       inc, CPU time, total time, step time, dt (first increment, then   :208, :298
                       after each minute of CPU time) ``(1x,I7,5x,g11.4,...)``
TRANSIENT CRITICAL     inc, iterations, total time, step time, dt, critical dt,          :210, :307
                       critical element, rejection text
=====================  ===============================================================  ============

Times have 4 significant digits (``g11.4``). Overflowing integer fields (``***``) are read as ``None``.
The rejection texts are set in :213-229; ``rejected (niter > maxiter)`` is also printed for
attempts that converged in the last allowed iteration, so :attr:`StaRow.accepted` follows the
rule given in :func:`read_sta`.

A strength reduction step with arc-length control (``*Reduction, arc-length``, line numbers of the uncommitted
numgeo-src of 14.11.2026) writes the column ``Ctrl`` (``report_statistics.f90:289,333``), the rejection text
``rejected (arc-length)`` (:255), its settings and notes at the start of the step
(``src/fem/arc_length_.f90:296-324``, ``arc_length_initialize``) and a summary at the end of the step
(``src/fem/arc_length_.f90:1149-1222``, ``arc_length_write_history``): :func:`read_arc_length_summaries`
reads it as :class:`ArcLengthSummary`.

``<job>.msg`` starts every executed step with ``Step <n>: <NAME>`` (``src/report/report_convergence_.f90:68``,
called once per step from ``src/main.f90:460``), the only place that gives the step *number* (restart
runs skip the first steps). :func:`read_msg_steps` reads these headers. The command-line options
``no-sta``/``no-msg`` suppress the rows/step headers (``src/report/report_start_end.f90:84-94``,
``src/main.f90:460,915``); the readers then return no rows/steps.

Examples:
    >>> import pathlib, tempfile
    >>> f = pathlib.Path(tempfile.mkdtemp()) / "sim.sta"
    >>> _ = f.write_text('''-> Step = LOAD
    ...    Type = STATIC
    ...      Inc  Equil. Iters   Total time     Step time    Inc of time
    ...          1        2        0.5000         0.5000         0.5000      rejected (niter > maxiter)
    ...          1        1        0.2500         0.2500         0.2500
    ...          2        1         1.000          1.000         0.7500
    ...    Step sucessfully terminated, Date: 26.10.2026, Time: 11:51: 24
    ... ''')
    >>> [(r.increment, r.total_time, r.accepted) for r in read_sta(f)]
    [(1, 0.5, False), (1, 0.25, True), (2, 1.0, True)]

    A strength reduction step with arc-length control (shortened):

    >>> _ = f.write_text('''-> Step = SAFETY
    ...    Type = REDUCTION
    ...      Inc  Equil. Iters          FoS          dFoS   Max. |u-u_0|    Ctrl
    ...          8        8         1.217         0.1667E-01     0.3704        F
    ...          9       18         1.222         0.5556E-02     0.1112E+08    F  rejected (divergence)
    ...          9        1         1.219         0.2164E-02     0.3931        A
    ...    Strength reduction with arc-length control
    ...    End of the step: arc-increments = 1 arc-length increments accepted
    ...    Factor of safety (no plateau; last accepted increment):  1.219000
    ...    Step sucessfully terminated, Date: 13.11.2026, Time: 20:12: 21
    ... ''')
    >>> [(r.increment, r.fos, r.control, r.accepted) for r in read_sta(f)]
    [(8, 1.217, 'F', True), (9, 1.222, 'F', False), (9, 1.219, 'A', True)]
    >>> s = read_arc_length_summaries(f)[0]
    >>> s.end_reason, s.fos, s.fos_basis
    ('arc-increments = 1 arc-length increments accepted', 1.219, 'last increment')
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from pynumgeo.results._fortran import parse_result_real

__all__ = ["ArcLengthSummary", "FosBasis", "StaRow", "read_arc_length_summaries", "read_msg_steps", "read_sta"]

_STEP_RE = re.compile(r"^-> Step = (?P<name>.*?)\s*$")
_TYPE_RE = re.compile(r"^\s+Type = (?P<type>[A-Z ]+?)\s*$")
_END_RE = re.compile(r"^\s+Step sucessfully terminated")  # spelling as written, report_statistics.f90:139
_STOP_RE = re.compile(r"^-> (Time Statistics|NUMGEO \*END\*)")
_INT = r"(\d+|\*+)"
_NUM = r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[EeDd]?[-+]?\d+)?|NaN|[-+]?Infinity|\*+)"
_STANDARD = re.compile(rf"^\s+{_INT}\s+{_INT}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s*(.*?)\s*$")
_ARC_ROW = re.compile(rf"^\s+{_INT}\s+{_INT}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+([FA])(?:\s+(.*?))?\s*$")
_EXPLICIT = re.compile(rf"^\s+{_INT}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s*$")
_CRITICAL = re.compile(rf"^\s+{_INT}\s+{_INT}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+{_INT}\s*(.*?)\s*$")
_NITER_LABEL = "rejected (niter > maxiter)"

# strength reduction with arc-length control: settings at the start of the step (arc_length_.f90:296-324)
_ARC_SETTINGS = re.compile(
    rf"^\s+Arc-length control of the factor of safety \(\*Reduction, arc-length\): plateau-tolerance =\s*{_NUM}, "
    rf"plateau-increments = {_INT}, arc-increments = {_INT}, perturbation =\s*{_NUM}\s*$"
)
_ARC_MAX_DISP = re.compile(rf"^\s+End of the step at the largest displacement max-displacement =\s*{_NUM}\s*$")
_ARC_NOTE = re.compile(r"^\s+Note: (?P<text>.*?)\s*$")
# summary at the end of the step (arc_length_.f90:1149-1222)
_ARC_SUMMARY = re.compile(r"^\s+Strength reduction with arc-length control\s*$")
_ARC_REASON = re.compile(r"^\s+End of the step: (?P<reason>.*?)\s*$")
_ARC_ENGAGED = re.compile(
    rf"^\s+Arc-length control engaged at increment {_INT} \(last converged FoS\s*{_NUM}\); {_INT} increments "
    rf"accepted and {_INT} rejected under arc-length control\s*$"
)
_ARC_NEVER = re.compile(r"^\s+Arc-length control was never engaged")
_ARC_LAST = re.compile(rf"^\s+FoS of the last accepted increment:\s*{_NUM}\s+\(max\. \|u-u_0\| =\s*{_NUM}\)\s*$")
_ARC_WINDOWS = re.compile(
    rf"^\s+Displacement windows at the end of the step, \(u/4,u/2\] and \(u/2,u\], u =\s*{_NUM}: "
    rf"mean\s*{_NUM} \({_INT} increments\),\s*{_NUM} \({_INT} increments\)\s*$"
)
_ARC_AGREE = re.compile(r"^\s+The windows at the end of the step (?P<no>do not )?agree within plateau-tolerance")
_ARC_ALL = re.compile(rf"^\s+All {_INT} accepted arc-length increments: mean\s*{_NUM}, min\s*{_NUM}, max\s*{_NUM}\s*$")
_ARC_FIRST = re.compile(
    rf"^\s+First plateau of the step: increment {_INT}, u =\s*{_NUM}, mean\s*{_NUM}\s+"
    rf"\(min\s*{_NUM}, max\s*{_NUM}\)\s*$"
)
_ARC_END_PLATEAU = re.compile(
    rf"^\s+Factor of safety \(plateau at the end of the step, u =\s*{_NUM}; mean over its windows\):\s*{_NUM}"
    rf"\s+\(min\s*{_NUM}, max\s*{_NUM}\)\s*$"
)
_ARC_FIRST_PLATEAU = re.compile(  # numgeo-src of 13.11.2026: "...; mean over its windows)"
    rf"^\s+Factor of safety \(first plateau, increment {_INT}, u =\s*{_NUM}; (?:the windows at the end of the "
    rf"step do not agree|mean over its windows)\):\s*{_NUM}\s+\(min\s*{_NUM}, max\s*{_NUM}\)\s*$"
)
_ARC_NO_PLATEAU = re.compile(
    rf"^\s+Factor of safety \(no plateau; mean over the windows at the end of the step\):\s*{_NUM}"
    rf"\s+\(min\s*{_NUM}, max\s*{_NUM}\)\s*$"
)
_ARC_NO_PLATEAU_LAST = re.compile(rf"^\s+Factor of safety \(no plateau; last accepted increment\):\s*{_NUM}\s*$")
_ARC_PEAK = re.compile(rf"^\s+Peak FoS of the step:\s*{_NUM}\s+\(max\. \|u-u_0\| =\s*{_NUM}, increment {_INT}\)\s*$")
_ARC_PEAK_NOTE = re.compile(r"^\s+Note: the peak exceeds the factor of safety")
_ARC_FOS_ERROR = re.compile(rf"^\s+Estimated FoS error \|dFoS\| of the last accepted iteration:\s*{_NUM}\s*$")
_ARC_CONSTRAINT = re.compile(rf"^\s+Largest constraint error .*?:\s*{_NUM}\s*$")
# end reasons of the arc-length control (arc_length_.f90:941,950,967,1144,1146): the end criteria
# arc-increments and max-displacement are checked after an accepted increment, the others end the step
# at a rejected one
_ENDS_ACCEPTED = ("arc-increments =", "largest displacement reached max-displacement")
_NO_CONVERGENCE = "no convergence under arc-length control"
_ENDS_REJECTED = (_NO_CONVERGENCE, "FoS control: dFoS below dFoS_min")


@dataclass(frozen=True)
class StaRow:
    """One increment attempt of the ``.sta`` file.

    Attributes:
        step: step name as written (upper case).
        step_type: ``GEOSTATIC``, ``STATIC``, ``TRANSIENT``, ``DYNAMIC``, ``EXPLICIT DYNAMIC``,
            ``TRANSIENT CRITICAL`` or ``REDUCTION``.
        step_number: number of the step in the input, if known (from the ``.msg`` file, see
            :func:`read_sta`), else ``None``.
        increment: increment number (``None`` if the field overflowed).
        iterations: equilibrium iterations (``None`` for explicit rows or an overflowed field).
        total_time: total time (``None`` in strength reduction rows).
        step_time: step time (``None`` in strength reduction rows).
        dt: time increment (``None`` in strength reduction rows).
        rejection: rejection text as written, ``""`` if none.
        accepted: ``True``/``False`` by the rule of :func:`read_sta`, ``None`` where the file
            does not tell (strength reduction rows without arc-length control; a labelled last attempt of an
            unfinished step).
        fos, dfos, max_disp: factor of safety, its increment and max. ``|u - u_0|`` (REDUCTION only).
        cpu_time: CPU time of the step (EXPLICIT DYNAMIC only).
        dt_crit, critical_element: critical time increment and element (TRANSIENT CRITICAL only).
        control: control of the increment in a strength reduction step with arc-length control (column
            ``Ctrl``): ``"F"`` factor of safety prescribed, ``"A"`` arc-length control; ``None`` in all other
            rows.
    """

    step: str
    step_type: str
    step_number: int | None
    increment: int | None
    iterations: int | None
    total_time: float | None
    step_time: float | None
    dt: float | None
    rejection: str
    accepted: bool | None
    fos: float | None = None
    dfos: float | None = None
    max_disp: float | None = None
    cpu_time: float | None = None
    dt_crit: float | None = None
    critical_element: int | None = None
    control: str | None = None


#: What the factor of safety of a strength reduction step with arc-length control is (:attr:`ArcLengthSummary.fos`).
FosBasis = Literal["plateau at the end", "first plateau", "no plateau", "last increment"]


@dataclass(frozen=True)
class ArcLengthSummary:
    """A strength reduction step with arc-length control (``*Reduction, arc-length``) as the ``.sta`` reports it.

    The settings and notes come from the start of the step, the other values from the summary at its end
    (``src/fem/arc_length_.f90``, ``arc_length_initialize`` and ``arc_length_write_history``, uncommitted
    numgeo-src of 14.11.2026). A value the file does not contain (step not finished, line not written, field
    overflow ``***``) is ``None``. Reals of the summary have 6 decimals (``F10.6``) or 5 significant digits
    (``ES11.4``).

    Attributes:
        step: step name as written (upper case).
        step_number: number of the step in the input, if known (see :func:`read_sta`).
        plateau_tolerance, plateau_increments, arc_increments, perturbation: settings of the step
            (options of ``*Reduction, arc-length`` or their defaults).
        max_displacement: ``max-displacement=`` of the step, ``None`` if not given.
        notes: notes at the start of the step (contact and embedded interfaces with reduction), without the
            leading ``Note:``.
        end_reason: why the step ended, e.g. ``arc-increments = 100 arc-length increments accepted``,
            ``largest displacement reached max-displacement``, ``no convergence under arc-length control (10
            consecutive rejections)``, ``FoS control: dFoS below dFoS_min`` or ``maximum number of increments of
            the step (INC)``; ``None`` without summary.
        engaged: ``True`` if the arc-length control took over, ``False`` if it was never engaged.
        switch_increment: increment at which the arc-length control was engaged.
        switch_fos: factor of safety of the last converged increment at the switch.
        accepted, rejected: increments accepted and rejected under arc-length control.
        last_fos, last_max_disp: factor of safety and max. ``|u - u_0|`` of the last accepted increment.
        window_u: largest displacement u of the last accepted increment (windows at the end of the step).
        window_means, window_counts: mean factor of safety and number of accepted arc-length increments in the
            windows ``(u/4, u/2]`` and ``(u/2, u]`` at the end of the step.
        windows_agree: the two windows at the end of the step agree within the plateau tolerance.
        arc_mean, arc_min, arc_max: mean, minimum and maximum factor of safety of all accepted arc-length
            increments.
        first_plateau_increment, first_plateau_u: increment and largest displacement u at which the first
            plateau of the step was found (``None`` without plateau).
        first_plateau_fos, first_plateau_min, first_plateau_max: mean, minimum and maximum factor of safety over
            the windows of the first plateau.
        fos: factor of safety of the step, see :attr:`fos_basis`.
        fos_basis: what :attr:`fos` is: ``"plateau at the end"`` (the windows at the end of the step agree: mean
            over them), ``"first plateau"`` (they do not agree: mean over the windows of the first plateau),
            ``"no plateau"`` (mean over the windows at the end of the step) or ``"last increment"`` (no plateau
            and no window: factor of safety of the last accepted increment).
        fos_min, fos_max: minimum and maximum over the windows of :attr:`fos` (``None`` for ``"last increment"``).
        peak_fos, peak_max_disp, peak_increment: largest factor of safety of the step, its max. ``|u - u_0|`` and
            increment.
        peak_exceeds_plateau: the peak exceeds the factor of safety of a plateau by more than the plateau
            tolerance (softening-like response).
        fos_error: estimated error ``|dFoS|`` of the factor of safety of the last accepted iteration.
        constraint_error: largest constraint error ``|b.(du-du_pred)|/|b|^2`` of the accepted increments.
    """

    step: str
    step_number: int | None
    plateau_tolerance: float | None = None
    plateau_increments: int | None = None
    arc_increments: int | None = None
    perturbation: float | None = None
    max_displacement: float | None = None
    notes: tuple[str, ...] = ()
    end_reason: str | None = None
    engaged: bool | None = None
    switch_increment: int | None = None
    switch_fos: float | None = None
    accepted: int | None = None
    rejected: int | None = None
    last_fos: float | None = None
    last_max_disp: float | None = None
    window_u: float | None = None
    window_means: tuple[float | None, float | None] | None = None
    window_counts: tuple[int | None, int | None] | None = None
    windows_agree: bool | None = None
    arc_mean: float | None = None
    arc_min: float | None = None
    arc_max: float | None = None
    first_plateau_increment: int | None = None
    first_plateau_u: float | None = None
    first_plateau_fos: float | None = None
    first_plateau_min: float | None = None
    first_plateau_max: float | None = None
    fos: float | None = None
    fos_basis: FosBasis | None = None
    fos_min: float | None = None
    fos_max: float | None = None
    peak_fos: float | None = None
    peak_max_disp: float | None = None
    peak_increment: int | None = None
    peak_exceeds_plateau: bool = False
    fos_error: float | None = None
    constraint_error: float | None = None


def _int(token: str) -> int | None:
    return None if token.startswith("*") else int(token)


def _real(token: str) -> float | None:
    return None if token.startswith("*") else parse_result_real(token)


@dataclass
class _Block:
    """What the ``.sta`` says about one step block."""

    step: str
    step_type: str = ""
    number: int | None = None
    ended: bool = False
    arc: dict[str, object] | None = None  # fields of ArcLengthSummary, None without arc-length control
    notes: list[str] = field(default_factory=list)
    in_summary: bool = False


def _scan(path: str | Path, step_numbers: Sequence[int] | None) -> tuple[list[StaRow], list[int], list[_Block]]:
    p = Path(path)
    rows: list[StaRow] = []
    row_blocks: list[int] = []
    blocks: list[_Block] = []
    cur: _Block | None = None
    for k, line in enumerate(p.read_text(encoding="latin-1").splitlines(), start=1):
        m = _STEP_RE.match(line)
        if m:
            n = len(blocks)
            number = step_numbers[n] if step_numbers is not None and n < len(step_numbers) else None
            cur = _Block(m.group("name"), number=number)
            blocks.append(cur)
            continue
        if _STOP_RE.match(line):
            cur = None
            continue
        if cur is None:
            continue
        mt = _TYPE_RE.match(line)
        if mt and not cur.step_type:
            cur.step_type = mt.group("type")
            continue
        if _END_RE.match(line):
            cur.ended = True
            continue
        if cur.step_type == "REDUCTION" and _arc_line(cur, line):
            continue
        try:
            row = _parse_row(line, cur.step, cur.step_type, cur.number)
        except ValueError as exc:
            raise ValueError(f"{p}:{k}: {exc}") from None
        if row is not None:
            if row.control is not None and cur.arc is None:
                cur.arc = {}
            rows.append(row)
            row_blocks.append(len(blocks) - 1)
    return rows, row_blocks, blocks


def read_sta(path: str | Path, *, step_numbers: Sequence[int] | None = None) -> list[StaRow]:
    """Read all increment rows of a ``.sta`` file.

    Args:
        path: the ``.sta`` file.
        step_numbers: step number of the 1st, 2nd, ... step block of the file (e.g. from
            :func:`read_msg_steps`); sets :attr:`StaRow.step_number`.

    Acceptance, :attr:`StaRow.accepted`:

    * a row followed by another row of its step: rejected if that row repeats the increment number (a
      cut-back keeps the number, ``src/main.f90:574-579``), else accepted, whatever the rejection text
      (under NOCUTBACK a non-converged attempt is accepted, ``src/main.f90:950-970``);
    * the last row of a step: accepted without rejection text, or with ``rejected (niter > maxiter)``
      when the step ended with ``Step sucessfully terminated`` (the text is also printed for attempts
      that converged in the last iteration); else ``None``. Not visible in the ``.sta``: a step that ran
      out of increments ends after a rejected attempt number ``maxinc + 1`` (``src/main.f90:555``),
      and is still reported as terminated; such a last row is then wrongly taken as accepted.
      :func:`pynumgeo.run` knows ``maxinc`` from the deck and decides this case correctly;
    * strength reduction rows: ``None``; the factor-of-safety logic decides
      (``src/database/step_ty_.f90:330-440``);
    * strength reduction rows with arc-length control (column ``Ctrl``; numgeo rejects every increment that
      does not converge, NOCUTBACK is not allowed, and repeats it with the same number; the step ends at a
      rejected increment with the number ``maxinc + 1``): a row followed by a row of its step with the same
      increment number is rejected; followed by another number, a row without rejection text is accepted, a
      row with ``rejected (niter > maxiter)`` is accepted if the next number is the following one and ``None``
      otherwise, a row with another rejection text is rejected. The last row of the step is accepted if
      the summary of the step names an end criterion that is checked after an accepted increment
      (``arc-increments``, ``max-displacement``), rejected if it names an end at a rejected increment (no
      convergence under arc-length control, ``dFoS`` below ``dFoS_min``), else decided by its rejection text
      as above (``None`` for ``rejected (niter > maxiter)``). After consecutive rejections (no convergence
      under arc-length control) the row before the last row is rejected as well.
    """
    rows, row_blocks, blocks = _scan(path, step_numbers)
    return _with_acceptance(rows, row_blocks, blocks)


def read_arc_length_summaries(path: str | Path, *, step_numbers: Sequence[int] | None = None) -> list[ArcLengthSummary]:
    """The strength reduction steps with arc-length control of a ``.sta`` file, in file order.

    A step block counts if it is a ``REDUCTION`` step with the settings line of the arc-length control, rows
    with the column ``Ctrl`` or the summary ``Strength reduction with arc-length control``; see
    :class:`ArcLengthSummary`.

    Args:
        path: the ``.sta`` file.
        step_numbers: step number of the 1st, 2nd, ... step block of the file (e.g. from
            :func:`read_msg_steps`); sets :attr:`ArcLengthSummary.step_number`.
    """
    _, _, blocks = _scan(path, step_numbers)
    out = []
    for b in blocks:
        if b.arc is None:
            continue
        values = dict(b.arc)
        if b.notes:
            values["notes"] = tuple(b.notes)
        out.append(ArcLengthSummary(step=b.step, step_number=b.number, **values))  # type: ignore[arg-type]
    return out


def _arc_line(b: _Block, line: str) -> bool:
    """Settings, notes and summary lines of a strength reduction step with arc-length control (``True`` if read)."""
    m = _ARC_SETTINGS.match(line)
    if m:
        b.arc = b.arc or {}
        tol, ninc, narc, eps = m.groups()
        b.arc.update(
            plateau_tolerance=_real(tol),
            plateau_increments=_int(ninc),
            arc_increments=_int(narc),
            perturbation=_real(eps),
        )
        return True
    m = _ARC_MAX_DISP.match(line)
    if m:
        b.arc = b.arc or {}
        b.arc["max_displacement"] = _real(m.group(1))
        return True
    if _ARC_SUMMARY.match(line):
        b.arc = b.arc or {}
        b.in_summary = True
        b.arc["peak_exceeds_plateau"] = False
        return True
    if not b.in_summary:
        m = _ARC_NOTE.match(line)
        if m and b.arc is not None:
            b.notes.append(m.group("text"))
            return True
        return False
    assert b.arc is not None
    a = b.arc
    if m := _ARC_REASON.match(line):
        a["end_reason"] = m.group("reason")
    elif m := _ARC_ENGAGED.match(line):
        inc, fos, acc, rej = m.groups()
        a.update(
            engaged=True, switch_increment=_int(inc), switch_fos=_real(fos), accepted=_int(acc), rejected=_int(rej)
        )
    elif _ARC_NEVER.match(line):
        a["engaged"] = False
    elif m := _ARC_LAST.match(line):
        a.update(last_fos=_real(m.group(1)), last_max_disp=_real(m.group(2)))
    elif m := _ARC_WINDOWS.match(line):
        u, m1, n1, m2, n2 = m.groups()
        a.update(window_u=_real(u), window_means=(_real(m1), _real(m2)), window_counts=(_int(n1), _int(n2)))
    elif m := _ARC_AGREE.match(line):
        a["windows_agree"] = m.group("no") is None
    elif m := _ARC_ALL.match(line):
        a.update(arc_mean=_real(m.group(2)), arc_min=_real(m.group(3)), arc_max=_real(m.group(4)))
    elif m := _ARC_FIRST.match(line):
        inc, u, fos, lo, hi = m.groups()
        a.update(
            first_plateau_increment=_int(inc), first_plateau_u=_real(u), first_plateau_fos=_real(fos),
            first_plateau_min=_real(lo), first_plateau_max=_real(hi),
        )  # fmt: skip
    elif m := _ARC_END_PLATEAU.match(line):
        u, fos, lo, hi = m.groups()
        a.update(fos_basis="plateau at the end", fos=_real(fos), fos_min=_real(lo), fos_max=_real(hi))
    elif m := _ARC_FIRST_PLATEAU.match(line):
        inc, u, fos, lo, hi = m.groups()
        a.update(fos_basis="first plateau", fos=_real(fos), fos_min=_real(lo), fos_max=_real(hi))
        for key, value in (
            ("first_plateau_increment", _int(inc)), ("first_plateau_u", _real(u)), ("first_plateau_fos", _real(fos)),
            ("first_plateau_min", _real(lo)), ("first_plateau_max", _real(hi)),
        ):  # fmt: skip
            a.setdefault(key, value)
    elif m := _ARC_NO_PLATEAU.match(line):
        a.update(fos_basis="no plateau", fos=_real(m.group(1)), fos_min=_real(m.group(2)), fos_max=_real(m.group(3)))
    elif m := _ARC_NO_PLATEAU_LAST.match(line):
        a.update(fos_basis="last increment", fos=_real(m.group(1)))
    elif m := _ARC_PEAK.match(line):
        a.update(peak_fos=_real(m.group(1)), peak_max_disp=_real(m.group(2)), peak_increment=_int(m.group(3)))
    elif _ARC_PEAK_NOTE.match(line):
        a["peak_exceeds_plateau"] = True
    elif m := _ARC_FOS_ERROR.match(line):
        a["fos_error"] = _real(m.group(1))
    elif m := _ARC_CONSTRAINT.match(line):
        a["constraint_error"] = _real(m.group(1))
    return True


def _parse_row(line: str, step: str, step_type: str, number: int | None) -> StaRow | None:
    if step_type == "EXPLICIT DYNAMIC":
        m = _EXPLICIT.match(line)
        if not m:
            return None
        inc, cpu, tt, st, dt = m.groups()
        return StaRow(
            step, step_type, number, _int(inc), None, _real(tt), _real(st), _real(dt), "", None,
            cpu_time=_real(cpu),
        )  # fmt: skip
    if step_type == "TRANSIENT CRITICAL":
        m = _CRITICAL.match(line)
        if not m:
            return None
        inc, it, tt, st, dt, dtc, el, rej = m.groups()
        return StaRow(
            step, step_type, number, _int(inc), _int(it), _real(tt), _real(st), _real(dt), rej, None,
            dt_crit=_real(dtc), critical_element=_int(el),
        )  # fmt: skip
    if step_type == "REDUCTION":
        m = _ARC_ROW.match(line)
        if m:
            inc, it, a, b, c, ctrl, rej = m.groups()
            return StaRow(
                step, step_type, number, _int(inc), _int(it), None, None, None, rej or "", None,
                fos=_real(a), dfos=_real(b), max_disp=_real(c), control=ctrl,
            )  # fmt: skip
    m = _STANDARD.match(line)
    if not m:
        return None
    inc, it, a, b, c, rej = m.groups()
    if step_type == "REDUCTION":
        return StaRow(
            step, step_type, number, _int(inc), _int(it), None, None, None, rej, None,
            fos=_real(a), dfos=_real(b), max_disp=_real(c),
        )  # fmt: skip
    return StaRow(step, step_type, number, _int(inc), _int(it), _real(a), _real(b), _real(c), rej, None)


def _with_acceptance(rows: list[StaRow], blocks: list[int], info: list[_Block]) -> list[StaRow]:
    # TODO: replace by the solver's own flag once the .sta labels only rejected attempts.
    out: list[StaRow] = []
    for i, r in enumerate(rows):
        accepted: bool | None
        nxt = rows[i + 1] if i + 1 < len(rows) and blocks[i + 1] == blocks[i] else None
        if r.step_type == "REDUCTION" and r.control is not None:
            nxt_last = nxt is not None and (i + 2 >= len(rows) or blocks[i + 2] != blocks[i])
            accepted = _arc_accepted(r, nxt, nxt_last, info[blocks[i]])
        elif r.step_type == "REDUCTION":
            accepted = None
        elif nxt is not None:
            accepted = None if nxt.increment is None or r.increment is None else nxt.increment != r.increment
        elif r.rejection == "" or (r.rejection == _NITER_LABEL and info[blocks[i]].ended):
            accepted = True
        else:
            accepted = None
        out.append(replace(r, accepted=accepted))
    return out


def _arc_accepted(r: StaRow, nxt: StaRow | None, nxt_last: bool, block: _Block) -> bool | None:
    """Acceptance of a row of a strength reduction step with arc-length control (rule of :func:`read_sta`)."""
    reason = str((block.arc or {}).get("end_reason") or "")
    if nxt is None:
        if reason.startswith(_ENDS_ACCEPTED):
            return True
        if reason.startswith(_ENDS_REJECTED):
            return False
    elif nxt.increment is None or r.increment is None:
        return None
    elif nxt.increment == r.increment:
        return False
    elif nxt_last and reason.startswith(_NO_CONVERGENCE):
        return False  # consecutive rejections; the last row carries the number maxinc + 1
    if r.rejection == "":
        return True
    if r.rejection == _NITER_LABEL:
        follows = nxt is not None and r.increment is not None and nxt.increment == r.increment + 1
        return True if follows else None
    return False


_MSG_STEP_RE = re.compile(r"^ {3}Step (?P<n>\d+): (?P<name>.*?)\s*$")
_MSG_RULE = " " * 3 + "=" * 100  # report_convergence_.f90:67


def read_msg_steps(path: str | Path) -> list[tuple[int, str]]:
    """Step numbers and names of the executed steps from a ``.msg`` file, in order.

    Reads the ``Step <n>: <NAME>`` line that follows a rule of 100 ``=`` (report_convergence_.f90:66-68).
    """
    out: list[tuple[int, str]] = []
    previous = ""
    for line in Path(path).read_text(encoding="latin-1").splitlines():
        if previous.rstrip() == _MSG_RULE:
            m = _MSG_STEP_RE.match(line)
            if m:
                out.append((int(m.group("n")), m.group("name")))
        previous = line
    return out
