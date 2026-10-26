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
"""Result types of :func:`pynumgeo.solver.run`: status, step reports and solver messages.

Examples:
    >>> r = RunResult(status=RunStatus.SUCCESS, reason="ok", workdir=Path("."), job="job")
    >>> r.ok, r.status == "SUCCESS", r.errors
    (True, True, [])
    >>> s = StepReport(index=1, name="LOAD", t_end=1.0, t_reached=1.0, increments=20, cutbacks=0,
    ...                started=True, terminated=True, completed=True)
    >>> s.as_dict()["completed"]
    True
"""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "MessageSeverity",
    "Phase",
    "RunFailedError",
    "RunResult",
    "RunStatus",
    "SolverMessage",
    "StepReport",
]

MessageSeverity = Literal["error", "warning", "info"]
#: Phase of a ``.log`` message: before or after ``-> PREPROCESSING *END*``; ``None`` if not from the ``.log``.
Phase = Literal["input", "analysis"] | None


class RunStatus(enum.StrEnum):
    """Outcome of a numgeo run (compares equal to its name, e.g. ``status == "SUCCESS"``)."""

    #: exit status 0, end marker, no error, every step reached its end time.
    SUCCESS = "SUCCESS"
    #: numgeo reported an error (or exited with a non-zero status, or stopped without its end marker).
    FAILED = "FAILED"
    #: numgeo ended normally but a step did not reach its end time (e.g. ``inc=`` exhausted, which numgeo
    #: does not report, src/main.f90:555) or a step was not run.
    INCOMPLETE = "INCOMPLETE"
    #: the time limit was reached and the process tree was killed.
    TIMEOUT = "TIMEOUT"
    #: the process died abnormally (signal, Fortran runtime error, OS exception) without a numgeo error.
    CRASHED = "CRASHED"
    #: ``check_only=True``: the input was read and the model database built (``-> PREPROCESSING *END*``).
    INPUT_ACCEPTED = "INPUT_ACCEPTED"


@dataclass(frozen=True)
class SolverMessage:
    """An error, warning or note found in the report files, the console or a dump file.

    Attributes:
        severity: ``error``, ``warning`` or ``info``.
        text: the message text (70-character chunks of the ``.log`` joined again, report_.f90:205-238).
        origin: where it was found, ``<file>:<line>`` (``console:<line>`` for the console).
        file: numgeo source file of the matching message template (``src/...f90``), if matched.
        line: line of that source file.
        routine: routine of that source line.
        message_id: id of the template in the catalogue's message inventory (``src/...f90:<line>``).
        candidates: ids of all equally good templates (the same text is written at several places).
        rule_ids: pynumgeo validator rules whose ``source`` covers the matched source line.
        phase: ``input`` (before ``-> PREPROCESSING *END*`` in the ``.log``), ``analysis`` (after it),
            ``None`` (not from the ``.log``).
        runtime: the message comes from the Fortran runtime or the operating system (crash), not from
            numgeo's own code.
        count: how often the identical message was written (repetitions are listed once, at the first
            origin).
    """

    severity: MessageSeverity
    text: str
    origin: str
    file: str | None = None
    line: int | None = None
    routine: str | None = None
    message_id: str | None = None
    candidates: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    phase: Phase = None
    runtime: bool = False
    count: int = 1

    @property
    def source(self) -> str | None:
        """``file:line`` of the solver source, if the message was matched."""
        if self.file is None:
            return None
        return f"{self.file}:{self.line}" if self.line is not None else self.file

    def __str__(self) -> str:
        where = f" [{self.source}]" if self.source else ""
        times = f" ({self.count} times)" if self.count > 1 else ""
        return f"{self.severity}: {self.text} ({self.origin}){where}{times}"

    def as_dict(self) -> dict[str, Any]:
        """Plain dict (JSON-serialisable)."""
        d = asdict(self)
        d["candidates"] = list(self.candidates)
        d["rule_ids"] = list(self.rule_ids)
        return d


@dataclass(frozen=True)
class StepReport:
    """What happened in one step of the deck.

    Attributes:
        index: 1-based position of the step in the deck (in the ``.sta`` if the deck is unknown).
        name: step name (as written in the ``.sta``: upper case, blanks removed).
        t_end: end time of the step from the deck (``None`` if unknown or not a time, e.g. ``*Reduction``).
        t_reached: step time of the last accepted increment from the ``.sta`` (4 significant digits,
            ``g11.4``, report_statistics.f90:207); ``None`` if not reported.
        increments: accepted increments.
        cutbacks: rejected attempts (a rejected attempt is followed by a line with the same increment
            number, src/main.f90:574-579).
        started: the step block exists in the ``.sta`` (``-> Step = ...``, report_statistics.f90:71).
        terminated: the ``.sta`` has ``Step sucessfully terminated`` for it (report_statistics.f90:139);
            numgeo prints it also when ``inc=`` was exhausted before ``t_end``.
        completed: terminated and (where verifiable) ``t_reached`` equals ``t_end`` (relative tolerance
            ``1e-3``, the ``.sta`` prints 4 significant digits).
        iterations: total number of equilibrium iterations (``Total number of iterations``).
        procedure: ``STATIC``, ``TRANSIENT``, ... (``Type =`` line of the ``.sta``, else the deck).
        skipped: not run in this job (restart with ``oldjob=`` continues after it).
        note: why the step is not complete, or what could not be verified.
    """

    index: int
    name: str | None
    t_end: float | None
    t_reached: float | None
    increments: int | None
    cutbacks: int | None
    started: bool
    terminated: bool
    completed: bool
    iterations: int | None = None
    procedure: str | None = None
    skipped: bool = False
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Plain dict (JSON-serialisable)."""
        return asdict(self)


@dataclass
class RunResult:
    """Outcome of :func:`pynumgeo.solver.run` (or :func:`pynumgeo.solver.assess` for an existing job folder).

    Attributes:
        status: see :class:`RunStatus`.
        reason: human-readable explanation of the status.
        workdir: job folder (numgeo's working directory).
        job: job name (``inp=`` and ``out=``).
        exit_code: exit status of the process (negative: killed by that signal, POSIX); ``None`` if unknown.
        duration: wall-clock seconds of the run.
        command: the command line that was started.
        steps: one report per step of the deck.
        messages: errors, warnings and notes of numgeo (in file order: ``.log``, ``.sta``, ``.msg``,
            console, dump files).
        files: files created or changed by the run (absolute paths, sorted).
        version: numgeo version from the banner (``numgeo2026-v2 (Oct 26 2026)``).
        notes: remarks of the runner (environment, fallbacks, what could not be verified).
        console_tail: the last lines of the console output (stdout and stderr).
    """

    status: RunStatus
    reason: str
    workdir: Path
    job: str
    exit_code: int | None = None
    duration: float = 0.0
    command: list[str] = field(default_factory=list)
    steps: list[StepReport] = field(default_factory=list)
    messages: list[SolverMessage] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    version: str | None = None
    notes: list[str] = field(default_factory=list)
    console_tail: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True for ``SUCCESS`` and ``INPUT_ACCEPTED``."""
        return self.status in (RunStatus.SUCCESS, RunStatus.INPUT_ACCEPTED)

    @property
    def log_path(self) -> Path:
        """``<workdir>/<job>.log`` (may not exist if numgeo stopped before opening it)."""
        return self.workdir / f"{self.job}.log"

    @property
    def sta_path(self) -> Path:
        """``<workdir>/<job>.sta``."""
        return self.workdir / f"{self.job}.sta"

    @property
    def msg_path(self) -> Path:
        """``<workdir>/<job>.msg``."""
        return self.workdir / f"{self.job}.msg"

    @property
    def console_path(self) -> Path:
        """``<workdir>/<job>.console.log``: stdout and stderr of the run, written by pynumgeo."""
        return self.workdir / f"{self.job}.console.log"

    @property
    def errors(self) -> list[SolverMessage]:
        """Messages with severity ``error``."""
        return [m for m in self.messages if m.severity == "error"]

    @property
    def warnings(self) -> list[SolverMessage]:
        """Messages with severity ``warning``."""
        return [m for m in self.messages if m.severity == "warning"]

    def raise_for_status(self) -> RunResult:
        """Raise :class:`RunFailedError` unless :attr:`ok`; return ``self`` otherwise."""
        if not self.ok:
            raise RunFailedError(self)
        return self

    def summary(self) -> dict[str, Any]:
        """JSON-serialisable summary (for agents and ``--json`` output)."""
        return {
            "status": str(self.status),
            "reason": self.reason,
            "job": self.job,
            "workdir": str(self.workdir),
            "exit_code": self.exit_code,
            "duration": round(self.duration, 3),
            "version": self.version,
            "command": list(self.command),
            "steps": [s.as_dict() for s in self.steps],
            "messages": [m.as_dict() for m in self.messages],
            "notes": list(self.notes),
            "log": str(self.log_path),
        }

    def __str__(self) -> str:
        return f"{self.status}: {self.reason}"


class RunFailedError(RuntimeError):
    """Raised by :meth:`RunResult.raise_for_status`; the result is in ``.result``."""

    def __init__(self, result: RunResult) -> None:
        self.result = result
        super().__init__(f"numgeo job {result.job!r} in {result.workdir}: {result.status}: {result.reason}")
