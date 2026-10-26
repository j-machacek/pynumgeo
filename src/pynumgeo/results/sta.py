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
EXPLICIT DYNAMIC       inc, CPU time, total time, step time, dt (first increment, then   :208, :298
                       after each minute of CPU time) ``(1x,I7,5x,g11.4,...)``
TRANSIENT CRITICAL     inc, iterations, total time, step time, dt, critical dt,          :210, :307
                       critical element, rejection text
=====================  ===============================================================  ============

Times have 4 significant digits (``g11.4``). Overflowing integer fields (``***``) are read as ``None``.
The rejection texts are set in :213-229; ``rejected (niter > maxiter)`` is also printed for
attempts that converged in the last allowed iteration, so :attr:`StaRow.accepted` follows the
rule given in :func:`read_sta`.

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
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from pynumgeo.results._fortran import parse_result_real

__all__ = ["StaRow", "read_msg_steps", "read_sta"]

_STEP_RE = re.compile(r"^-> Step = (?P<name>.*?)\s*$")
_TYPE_RE = re.compile(r"^\s+Type = (?P<type>[A-Z ]+?)\s*$")
_END_RE = re.compile(r"^\s+Step sucessfully terminated")  # spelling as written, report_statistics.f90:139
_STOP_RE = re.compile(r"^-> (Time Statistics|NUMGEO \*END\*)")
_INT = r"(\d+|\*+)"
_NUM = r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[EeDd]?[-+]?\d+)?|NaN|[-+]?Infinity|\*+)"
_STANDARD = re.compile(rf"^\s+{_INT}\s+{_INT}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s*(.*?)\s*$")
_EXPLICIT = re.compile(rf"^\s+{_INT}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s*$")
_CRITICAL = re.compile(rf"^\s+{_INT}\s+{_INT}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+{_INT}\s*(.*?)\s*$")
_NITER_LABEL = "rejected (niter > maxiter)"


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
            does not tell (strength reduction rows; a labelled last attempt of an unfinished step).
        fos, dfos, max_disp: factor of safety, its increment and max. ``|u - u_0|`` (REDUCTION only).
        cpu_time: CPU time of the step (EXPLICIT DYNAMIC only).
        dt_crit, critical_element: critical time increment and element (TRANSIENT CRITICAL only).
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


def _int(token: str) -> int | None:
    return None if token.startswith("*") else int(token)


def _real(token: str) -> float | None:
    return None if token.startswith("*") else parse_result_real(token)


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
      (``src/database/step_ty_.f90:330-440``).
    """
    p = Path(path)
    rows: list[StaRow] = []
    step: str | None = None
    step_type = ""
    block = -1
    blocks_ended: set[int] = set()
    row_blocks: list[int] = []
    for k, line in enumerate(p.read_text(encoding="latin-1").splitlines(), start=1):
        m = _STEP_RE.match(line)
        if m:
            step, step_type, block = m.group("name"), "", block + 1
            continue
        if _STOP_RE.match(line):
            step = None
            continue
        if step is None:
            continue
        mt = _TYPE_RE.match(line)
        if mt and not step_type:
            step_type = mt.group("type")
            continue
        if _END_RE.match(line):
            blocks_ended.add(block)
            continue
        number = step_numbers[block] if step_numbers is not None and block < len(step_numbers) else None
        try:
            row = _parse_row(line, step, step_type, number)
        except ValueError as exc:
            raise ValueError(f"{p}:{k}: {exc}") from None
        if row is not None:
            rows.append(row)
            row_blocks.append(block)
    return _with_acceptance(rows, row_blocks, blocks_ended)


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


def _with_acceptance(rows: list[StaRow], blocks: list[int], ended: set[int]) -> list[StaRow]:
    # TODO: replace by the solver's own flag once the .sta labels only rejected attempts.
    out: list[StaRow] = []
    for i, r in enumerate(rows):
        accepted: bool | None
        if r.step_type == "REDUCTION":
            accepted = None
        elif i + 1 < len(rows) and blocks[i + 1] == blocks[i]:
            nxt = rows[i + 1].increment
            accepted = None if nxt is None or r.increment is None else nxt != r.increment
        elif r.rejection == "" or (r.rejection == _NITER_LABEL and blocks[i] in ended):
            accepted = True
        else:
            accepted = None
        out.append(replace(r, accepted=accepted))
    return out


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
