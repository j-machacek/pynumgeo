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
"""Judge the outcome of a numgeo run from its files.

The exit status alone says nothing: ``report%error`` ends with a plain ``stop``
(src/report/report_error_.f90:62), so numgeo exits with 0 after an error unless the executable is built to
exit with status 1; ``-> NUMGEO *END*`` is also written right before the dt < dtmin error
(fem_global_estimate_current_dt_.f90:121-124); a step whose ``inc=`` is exhausted ends silently and
the next step starts (src/main.f90:555). The decision, in this order:

1. ``TIMEOUT`` if the runner killed the process at the time limit.
2. With ``check_only``: ``INPUT_ACCEPTED`` if the ``.log`` reached ``-> PREPROCESSING *END*``
   (database.f90:1114) without an error before it, else ``FAILED`` (input errors) or ``CRASHED``.
3. ``FAILED`` if numgeo reported an error: an error block or ``ERROR:`` line in the ``.log``, the
   ``Calculation stopped`` line in ``.log``/``.sta``/``.msg``/console, an error on the console, an
   unknown command-line argument or a new ``ERROR_Element_elem_<n>.sta`` (element routine failure,
   no ``.log`` entry, e.g. element_U_.f90:476-550).
4. ``CRASHED`` if the process was killed by a signal / OS exception or a Fortran runtime error was
   printed.
5. ``FAILED`` if the exit status is not 0, or the end marker ``-> NUMGEO *END*`` is missing.
6. ``INCOMPLETE`` if a step did not run, did not terminate, or its last accepted step time is not its
   ``t_end`` (from the deck; the ``.sta`` prints 4 significant digits, so the tolerance is relative
   ``1e-3``).
7. ``SUCCESS`` otherwise. New ``ERROR_Material_elem_<n>.sta`` files are warnings only (most material
   routines continue with a cutback).

Example (judging a finished job folder):
    >>> import pathlib, tempfile
    >>> d = pathlib.Path(tempfile.mkdtemp())
    >>> _ = (d / "job.log").write_text("-> NUMGEO *START*\\n-> PREPROCESSING *END* \\n-> NUMGEO *END*\\n")
    >>> _ = (d / "job.sta").write_text("-> Step = S1\\n   Type = STATIC\\n"
    ...     "         1        1        0.5000         0.5000         0.5000  \\n"
    ...     "         2        1         1.000          1.000         0.5000  \\n"
    ...     "   Step sucessfully terminated, Date: 26.10.2026, Time: 15:01: 58\\n-> NUMGEO *END*\\n")
    >>> r = assess(d, "job", exit_code=0)
    >>> r.status, r.steps[0].increments, r.steps[0].t_reached
    (<RunStatus.SUCCESS: 'SUCCESS'>, 2, 1.0)
"""

from __future__ import annotations

import os
import signal
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from pynumgeo.deck.deck import Deck
from pynumgeo.deck.keyword import Keyword
from pynumgeo.solver import logs
from pynumgeo.solver.messages import classify, normalise_text, rules_for_source
from pynumgeo.solver.result import MessageSeverity, Phase, RunResult, RunStatus, SolverMessage, StepReport

__all__ = ["DeckStep", "RunFacts", "assess", "deck_steps", "judge", "restart_step_of"]

#: Default of ``*Step, inc=`` (src/input/read_step_.f90:332).
DEFAULT_MAXINC = 1_000_000
_ELEMENT_DUMP = "ERROR_Element_elem_"
_MATERIAL_DUMP = "ERROR_Material_elem_"
_NTSTATUS = {
    0xC0000005: "access violation",
    0xC00000FD: "stack overflow",
    0xC0000094: "integer division by zero",
    0xC000008E: "floating-point division by zero",
    0xC0000409: "stack buffer overrun",
    0xC000001D: "illegal instruction",
    0xC0000017: "out of memory",
}


@dataclass(frozen=True)
class DeckStep:
    """What the deck says about a step."""

    name: str
    procedure: str  # solver spelling without blanks and '-', e.g. "STATIC", "TRANSIENTCRITICAL"
    t_end: float | None
    maxinc: int
    nocutback: bool


def _num(v: object) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def deck_steps(deck: Deck) -> list[DeckStep]:
    """End time and increment limit of every step (src/input/read_step_.f90:355-623).

    ``t_end`` is the second value of the procedure's data line (``*Static``, ``*Transient``,
    ``*Transient-critical``, ``*Dynamic``, ``*Explicit dynamic``), 1.0 for ``*Geostatic`` (:369-372) and
    ``None`` for ``*Reduction`` (its "time" counts increments, :415-418).
    """
    out: list[DeckStep] = []
    for s in deck.steps:
        proc = _procedure_key(s.procedure)
        t_end: float | None
        if proc == "GEOSTATIC":
            t_end = 1.0
        elif proc == "REDUCTION":
            t_end = None
        else:
            row = s.procedure.data[0] if s.procedure.data else []
            t_end = _num(row[1]) if len(row) >= 2 else None
        maxinc = int(s.inc) if s.inc is not None else DEFAULT_MAXINC
        if proc.startswith("EXPLICITDYNAMIC"):
            maxinc = max(maxinc, DEFAULT_MAXINC)  # read_step_.f90:501-504
        out.append(DeckStep(s.name, proc, t_end, maxinc, bool(s.nocutback)))
    return out


def _procedure_key(kw: Keyword) -> str:
    return kw.keyword.lstrip("*").replace("-", "").replace(" ", "").upper()


def _name_key(name: str) -> str:
    return name.upper().replace(" ", "")


@dataclass
class RunFacts:
    """Everything the runner knows besides the files (filled by :func:`pynumgeo.solver.run`)."""

    exit_code: int | None = None
    duration: float = 0.0
    command: list[str] = field(default_factory=list)
    timed_out: bool = False
    timeout: float | None = None
    check_only: bool = False
    native_check: bool = False
    stopped_by_runner: bool = False
    flags: Sequence[str] = ()
    console_lines: list[str] | None = None
    before: dict[Path, tuple[int, int]] | None = None
    notes: list[str] = field(default_factory=list)


def assess(
    workdir: str | os.PathLike[str],
    job: str = "job",
    deck: Deck | None = None,
    *,
    exit_code: int | None = None,
    flags: Sequence[str] = (),
    check_only: bool = False,
    console: str | os.PathLike[str] | None = None,
) -> RunResult:
    """Judge a numgeo job folder that has already run (e.g. started outside pynumgeo).

    Without a deck, the step end times are not checked. Without ``exit_code``, the exit status is not
    checked. Dump files ``ERROR_*_elem_*.sta`` count regardless of their age (the start time of the run is
    unknown).

    Args:
        workdir: the job folder.
        job: job name (``out=``).
        deck: the deck that was run (for the end time of each step).
        exit_code: exit status of numgeo, if known.
        flags: command-line flags that were used (``oldjob=``, ``no-sta``).
        check_only: judge as an input check (``INPUT_ACCEPTED``).
        console: file with the console output (stdout and stderr); default ``<job>.console.log`` (written
            by :func:`pynumgeo.solver.run`), not read if missing.
    """
    wd = Path(workdir)
    con = Path(console) if console is not None else wd / f"{job}.console.log"
    facts = RunFacts(
        exit_code=exit_code,
        flags=list(flags),
        check_only=check_only,
        console_lines=list(logs.read_lines(con)) if con.is_file() else None,
    )
    return judge(wd, job, deck, facts)


# ----------------------------------------------------------------------------- the decision
def judge(workdir: Path, job: str, deck: Deck | None, facts: RunFacts) -> RunResult:
    """Build the :class:`RunResult` from the files in ``workdir`` and the runner's ``facts``."""
    notes = list(facts.notes)
    log_p, sta_p, msg_p = (workdir / f"{job}{ext}" for ext in (".log", ".sta", ".msg"))
    log = logs.parse_log(logs.read_lines(log_p), log_p.name) if log_p.is_file() else logs.LogInfo()
    sta = logs.parse_sta(logs.read_lines(sta_p), sta_p.name) if sta_p.is_file() else logs.StaInfo()
    msg_abnormal, msg_errors = (
        logs.scan_error_lines(logs.read_lines(msg_p), msg_p.name) if msg_p.is_file() else (False, [])
    )
    console = logs.parse_console(facts.console_lines or [], "console")

    raw: list[logs.RawMessage] = [*log.messages, *sta.error_lines, *msg_errors]
    seen = {normalise_text(m.text) for m in raw}
    native_unsupported = False
    for m in console.messages:
        if m.text.startswith("Unknown input parameter: check-input") and facts.native_check:
            native_unsupported = True
            continue
        key = normalise_text(m.text)
        if key in seen:
            continue
        seen.add(key)
        raw.append(m)
    for sev, k in console.suppressed.items():
        notes.append(f"{k} further console {sev}s not listed (more than {logs.MAX_CONSOLE_MESSAGES})")
    if native_unsupported:
        notes.append(
            "the executable does not know 'check-input'; the input check stopped the process at "
            "-> PREPROCESSING *END* instead"
        )

    dumps_e, dumps_m = _dump_files(workdir, facts)
    for p in dumps_e:
        raw.append(logs.RawMessage("error", _dump_text(p, "element"), p.name))
    for p in dumps_m:
        raw.append(logs.RawMessage("warning", _dump_text(p, "material"), p.name))

    messages = _collapse([_solver_message(m) for m in raw])
    any_abnormal = log.abnormal_end or sta.abnormal_end or msg_abnormal or console.abnormal_end
    if any_abnormal and not any(m.severity == "error" and not m.runtime for m in messages):
        where = [
            n
            for n, f in (
                ("log", log.abnormal_end),
                ("sta", sta.abnormal_end),
                ("msg", msg_abnormal),
                ("console", console.abnormal_end),
            )
            if f
        ]
        messages.append(
            SolverMessage(
                "error",
                "Calculation stopped due to an error! :-( (no message text found)",
                "/".join(where),
                file="src/report/report_error_.f90",
                line=43,
                routine="report_error",
            )
        )

    steps, step_notes = _steps(deck, sta, facts.flags, log)
    notes += step_notes
    version = log.version or console.version
    status, reason = _decide(facts, log, sta, messages, steps)
    if status in (RunStatus.SUCCESS, RunStatus.INPUT_ACCEPTED, RunStatus.INCOMPLETE):
        w = [m for m in messages if m.severity == "warning"]
        total = sum(m.count for m in w)
        if w:
            reason += f" ({total} warning{'s' if total > 1 else ''}"
            reason += f", {len(w)} different)" if total > len(w) else ")"
    tail = (facts.console_lines or [])[-200:]
    return RunResult(
        status=status,
        reason=reason,
        workdir=workdir,
        job=job,
        exit_code=facts.exit_code,
        duration=facts.duration,
        command=list(facts.command),
        steps=steps,
        messages=messages,
        files=_changed_files(workdir, facts),
        version=version,
        notes=notes,
        console_tail=tail,
    )


def _decide(
    facts: RunFacts,
    log: logs.LogInfo,
    sta: logs.StaInfo,
    messages: list[SolverMessage],
    steps: list[StepReport],
) -> tuple[RunStatus, str]:
    errors = [m for m in messages if m.severity == "error" and not m.runtime]
    crashes = [m for m in messages if m.runtime]
    signal_text = _signal_text(facts.exit_code)

    if facts.timed_out:
        why = f"no result within the time limit of {facts.timeout:g} s; the process tree was killed"
        if errors:
            why += f"; last error: {_short(errors[-1])}"
        return RunStatus.TIMEOUT, why

    if facts.check_only:
        input_errors = (
            [m for m in errors if m.phase in ("input", None)]
            if not log.preprocessing_end
            else [m for m in errors if m.phase == "input"]
        )
        if log.preprocessing_end and not input_errors:
            how = (
                "stopped by pynumgeo"
                if facts.stopped_by_runner
                else ("numgeo check-input" if (log.native_check or facts.native_check) else "process ended")
            )
            why = (
                "numgeo read the input and built the model database (-> PREPROCESSING *END*, "
                f"src/database/database.f90:1114); {how}"
            )
            late = [m for m in errors if m.phase == "analysis"]
            if late:
                why += f"; the analysis had started and reported: {_short(late[0])}"
            return RunStatus.INPUT_ACCEPTED, why
        if input_errors:
            return RunStatus.FAILED, f"input rejected: {_short(input_errors[0])}"
        if crashes or signal_text:
            return RunStatus.CRASHED, _crash_reason(crashes, signal_text, facts.exit_code)
        return RunStatus.FAILED, (
            "numgeo ended before the end of the input phase (-> PREPROCESSING *END*) without an error message"
            f"{_exit_suffix(facts.exit_code)}"
        )

    if errors:
        first = errors[0]
        why = _short(first)
        if log.end_before_error:
            why += " (the end marker -> NUMGEO *END* written before this error does not mean success)"
        if len(errors) > 1:
            why += f" (+{len(errors) - 1} more error{'s' if len(errors) > 2 else ''})"
        return RunStatus.FAILED, why
    if crashes or signal_text:
        return RunStatus.CRASHED, _crash_reason(crashes, signal_text, facts.exit_code)
    if facts.exit_code not in (0, None):
        return RunStatus.FAILED, f"numgeo exited with status {facts.exit_code} without an error message"
    if not log.end_marker:
        if not log.exists:
            return RunStatus.FAILED, "numgeo stopped before writing the .log file, without an error message"
        return RunStatus.FAILED, (
            "numgeo stopped without the end marker (-> NUMGEO *END*) and without an error message"
        )

    open_steps = [s for s in steps if not s.completed and not s.skipped]
    if open_steps:
        s = open_steps[0]
        why = f"step {s.index} ({s.name}): {s.note or 'not completed'}"
        if len(open_steps) > 1:
            why += f" (+{len(open_steps) - 1} more step{'s' if len(open_steps) > 2 else ''} not completed)"
        return RunStatus.INCOMPLETE, why
    n = len([s for s in steps if not s.skipped])
    return RunStatus.SUCCESS, f"numgeo completed {n} step{'s' if n != 1 else ''}"


def _short(m: SolverMessage) -> str:
    text = " ".join(m.text.split())
    if len(text) > 300:
        text = text[:297] + "..."
    where = f", {m.source}" if m.source else ""
    return f"{text} ({m.origin}{where})"


def _exit_suffix(code: int | None) -> str:
    return "" if code in (0, None) else f"; exit status {code}"


def _signal_text(code: int | None) -> str | None:
    if code is None:
        return None
    if -128 < code < 0 and os.name != "nt":  # POSIX: -N = killed by signal N
        try:
            return f"killed by signal {signal.Signals(-code).name}"
        except ValueError:
            return f"killed by signal {-code}"
    u = code & 0xFFFFFFFF
    if u >= 0xC0000000:
        return f"Windows exception 0x{u:08X}" + (f" ({_NTSTATUS[u]})" if u in _NTSTATUS else "")
    return None


def _crash_reason(crashes: list[SolverMessage], signal_text: str | None, code: int | None) -> str:
    parts = []
    if signal_text:
        parts.append(
            f"numgeo was {signal_text}" if signal_text.startswith("killed") else f"numgeo ended with a {signal_text}"
        )
    if crashes:
        parts.append(_short(crashes[0]))
    if not parts:
        parts.append(f"numgeo ended abnormally{_exit_suffix(code)}")
    return "; ".join(parts)


# ----------------------------------------------------------------------------- messages
def _solver_message(m: logs.RawMessage) -> SolverMessage:
    hit = None if m.runtime else classify(m.text, m.severity)
    text = m.text
    if text.startswith("ERROR: "):
        text = text[len("ERROR: ") :]
    if hit is not None:
        return SolverMessage(
            severity=_severity(m.severity),
            text=text,
            origin=m.origin,
            file=hit.file,
            line=hit.line,
            routine=hit.routine,
            message_id=hit.message_id,
            candidates=hit.candidates if len(hit.candidates) > 1 else (),
            rule_ids=rules_for_source(hit.file, hit.line, hit.candidates),
            phase=_phase(m.phase),
            runtime=m.runtime,
        )
    file = line = None
    if m.source:
        f, _, ln = m.source.rpartition(":")
        file, line = f, int(ln)
    return SolverMessage(
        severity=_severity(m.severity),
        text=text,
        origin=m.origin,
        file=file,
        line=line,
        phase=_phase(m.phase),
        runtime=m.runtime,
    )


def _collapse(messages: list[SolverMessage]) -> list[SolverMessage]:
    """Identical messages (same severity, text and template) once, with their number of occurrences."""
    out: dict[tuple[str, str, str | None, bool], SolverMessage] = {}
    for m in messages:
        key = (m.severity, normalise_text(m.text), m.message_id, m.runtime)
        first = out.get(key)
        out[key] = m if first is None else replace(first, count=first.count + 1)
    return list(out.values())


def _severity(s: str) -> MessageSeverity:
    return "warning" if s == "warning" else "info" if s == "info" else "error"


def _phase(p: str | None) -> Phase:
    return "input" if p == "input" else "analysis" if p == "analysis" else None


# ----------------------------------------------------------------------------- steps
def _steps(
    deck: Deck | None, sta: logs.StaInfo, flags: Iterable[str], log: logs.LogInfo
) -> tuple[list[StepReport], list[str]]:
    notes: list[str] = []
    flags = list(flags)
    dsteps = deck_steps(deck) if deck is not None else None
    blocks = sta.steps
    restart_step = restart_step_of(deck) if deck is not None else None
    restart = restart_step is not None or any(f.startswith("oldjob=") for f in flags)
    no_sta = sta.increments_disabled or "no-sta" in flags

    if dsteps is None:
        reports = [_step_report(i + 1, b, None, no_sta) for i, b in enumerate(blocks)]
        expected = log.counts.get("steps")
        if expected is not None and expected > len(blocks):
            reports += [_not_run(k + 1, None, None, None) for k in range(len(blocks), expected)]
        notes.append("deck unknown: step end times were not checked")
        return reports, notes

    offset = _align(dsteps, blocks, restart, restart_step)
    if offset is None:
        offset = 0
        if blocks:
            notes.append("the step names in the .sta do not match the deck; steps were matched by position")
    reports = []
    for k, ds in enumerate(dsteps):
        if k < offset:
            reports.append(
                _not_run(
                    k + 1,
                    ds,
                    "not run in this job: the restart (*Restart read / oldjob=) continues after it",
                    True,
                )
            )
        elif k - offset < len(blocks):
            reports.append(_step_report(k + 1, blocks[k - offset], ds, no_sta))
        else:
            reports.append(_not_run(k + 1, ds, "not started", False))
    for b in blocks[len(dsteps) - offset :]:
        notes.append(f"the .sta has a step {b.name!r} that is not in the deck")
    return reports, notes


def _not_run(index: int, ds: DeckStep | None, note: str | None, skipped: bool | None) -> StepReport:
    """A step without a block in the ``.sta``: skipped by a restart, or never started."""
    return StepReport(
        index=index,
        name=_name_key(ds.name) if ds else None,
        t_end=ds.t_end if ds else None,
        t_reached=None,
        increments=None,
        cutbacks=None,
        started=False,
        terminated=False,
        completed=bool(skipped),
        procedure=ds.procedure if ds else None,
        skipped=bool(skipped),
        note=note or "not started",
    )


def restart_step_of(deck: Deck) -> int | None:
    """``N`` of ``*Restart read, step=N`` / ``*Pfem read, step=N``: steps 1..N are not run
    (src/input/scanning_for_numbers_.f90:300-312, src/main.f90:316); 0 if the keyword has no number."""
    for kw in deck.keywords:
        if kw.keyword in ("*RESTARTREAD", "*PFEMREAD"):
            v = kw.option("STEP")
            try:
                return int(float(v)) if v is not None else 0
            except ValueError:
                return 0
    return None


def _align(dsteps: list[DeckStep], blocks: list[logs.StaStep], restart: bool, restart_step: int | None) -> int | None:
    names = [_name_key(d.name) for d in dsteps]
    got = [_name_key(b.name) for b in blocks]
    offsets = list(range(0, len(names) - len(got) + 1)) if restart else [0]
    if restart_step and restart_step in offsets:
        offsets.insert(0, restart_step)
    for off in offsets:
        if off + len(got) <= len(names) and names[off : off + len(got)] == got:
            return off
    return None


def _step_report(index: int, b: logs.StaStep, ds: DeckStep | None, no_sta: bool) -> StepReport:
    proc = b.type or (ds.procedure if ds else None)
    maxinc = ds.maxinc if ds else DEFAULT_MAXINC
    accepted = b.accepted(maxinc=maxinc, nocutback=ds.nocutback if ds else False)
    increments: int | None = len(accepted)
    cutbacks: int | None = len(b.attempts) - len(accepted)
    t_reached = accepted[-1].step_time if accepted else None
    t_end = ds.t_end if ds else None
    note: str | None = None
    explicit = (proc or "").replace(" ", "").startswith("EXPLICITDYNAMIC")
    reduction = (proc or "").replace(" ", "") == "REDUCTION"

    if no_sta:
        increments = cutbacks = None
        t_reached = None
        completed = b.terminated
        note = "no increment lines in the .sta (no-sta): the step end time was not verified"
    elif explicit:
        increments = accepted[-1].inc if accepted else None
        cutbacks = None
        completed = b.terminated
        note = (
            "explicit dynamic: the .sta reports an increment only every 60 s CPU time "
            "(report_statistics.f90:295); t_reached is a lower bound, the end time was not verified"
        )
    elif reduction:
        fos = accepted[-1].total_time if accepted else None
        t_reached = None
        completed = b.terminated
        note = f"strength reduction: last FoS = {fos:g}" if fos is not None else "strength reduction"
    elif t_end is None:
        completed = b.terminated
        if completed:
            note = "end time unknown (deck unknown): only the step end line was checked"
    else:
        reached = t_reached is not None and logs.isclose_time(t_reached, t_end)
        completed = b.terminated and reached
        if not b.terminated:
            at = f" at step time {t_reached:g}" if t_reached is not None else ""
            note = f"did not terminate{at} (t_end {t_end:g}, {increments} increments, {cutbacks} cutbacks)"
        elif not reached:
            at = f"{t_reached:g}" if t_reached is not None else "0"
            note = f"ended at step time {at} of t_end {t_end:g} after {increments} increments"
            if ds is not None and increments is not None and increments >= ds.maxinc:
                note += (
                    f": the maximum number of increments (inc={ds.maxinc}) was exhausted; numgeo continues "
                    "without a message (src/main.f90:555)"
                )
    return StepReport(
        index=index,
        name=b.name,
        t_end=t_end,
        t_reached=t_reached,
        increments=increments,
        cutbacks=cutbacks,
        started=True,
        terminated=b.terminated,
        completed=completed,
        iterations=b.iterations,
        procedure=proc,
        note=note,
    )


# ----------------------------------------------------------------------------- files
def _dump_files(workdir: Path, facts: RunFacts) -> tuple[list[Path], list[Path]]:
    elem: list[Path] = []
    mat: list[Path] = []
    try:
        entries = sorted(workdir.iterdir())
    except OSError:
        return elem, mat
    for p in entries:
        if not p.name.endswith(".sta") or not p.is_file():
            continue
        if not (p.name.startswith(_ELEMENT_DUMP) or p.name.startswith(_MATERIAL_DUMP)):
            continue
        if facts.before is not None:
            st = p.stat()
            if facts.before.get(p.resolve()) == (st.st_mtime_ns, st.st_size):
                continue
        (elem if p.name.startswith(_ELEMENT_DUMP) else mat).append(p)
    return elem, mat


def _dump_text(p: Path, kind: str) -> str:
    head: list[str] = []
    try:
        for i, ln in enumerate(logs.read_lines(p)):
            s = ln.strip()
            if s.startswith(("TIME:", "LOCATION:")) or (i < 3 and s and not s.startswith("=")):
                head.append(s)
            if i > 12:
                break
    except OSError:
        pass
    what = "element routine failure (the run stops)" if kind == "element" else "material routine failure"
    return f"numgeo wrote {p.name}: {what}" + (f"; {'; '.join(head)}" if head else "")


def _changed_files(workdir: Path, facts: RunFacts) -> list[Path]:
    out: list[Path] = []
    if not workdir.is_dir():
        return out
    for root, _dirs, files in os.walk(workdir):
        for f in files:
            p = Path(root, f)
            try:
                st = p.stat()
            except OSError:
                continue
            if facts.before is not None and facts.before.get(p.resolve()) == (st.st_mtime_ns, st.st_size):
                continue
            out.append(p.resolve())
    return sorted(out)
