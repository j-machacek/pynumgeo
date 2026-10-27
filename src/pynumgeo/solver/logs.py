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
"""Parsers for numgeo's report files (``.log``, ``.sta``, ``.msg``) and console output.

Only what decides the outcome of a run is parsed; the formats are those of the source:

``.log``
    banner with ``Version: ...`` (report_construct_.f90:68), ``-> NUMGEO *START*``
    (report_start_end.f90:56), ``-> PREPROCESSING *END*`` (database.f90:1114, flushed :1117),
    ``-> NUMGEO *END*`` (report_start_end.f90:149; also written right before the dt < dtmin error,
    fem_global_estimate_current_dt_.f90:121-124), error blocks ``-> ERROR:`` / message / blank /
    ``-> ERROR: Calculation stopped due to an error! :-(`` (report_error_.f90:39-43), warning blocks
    ``-> WARNING:`` / message / blank (report_warning_.f90:39-42); messages are written in chunks of
    70 characters indented by 3 blanks, every chunk but the last ending with an inserted ``-``
    (report_.f90:205-238). Errors of ``complete_database`` are written directly as ``  ERROR: ...``
    without the closing line (database.f90:506-1809), ``thermal_error`` writes its own ``-> ERROR:``
    block (database.f90:1295-1301), the workload report writes ``Warning: ...`` lines
    (src/workload/workload_.f90:345-352).

``.sta``
    per step ``-> Step = <NAME>`` (report_statistics.f90:71), ``Type = ...`` (:73-115), the increment
    table with one line per attempt (format2 ``(4x,I6,6x,I3,7x,g11.4,4x,g11.4,4x,g11.4,2x,A)``, :207;
    transient critical adds two columns, :210; explicit dynamic ``(1x,I7,5x,g11.4,2x,g11.4,2x,g11.4,
    3x,g11.4)`` only every 60 s CPU, :208, :295), ``rejected (<reason>)`` on rejected attempts (:214-230),
    ``Step sucessfully terminated, Date: ...`` (sic, :139) and ``Total number of iterations  = <n>``
    (:142).

Examples:
    >>> log = parse_log(["-> NUMGEO *START*", " ", "-> ERROR:", "   The following material was not defin-",
    ...     "   ed: NOMAT", " ", "-> ERROR: Calculation stopped due to an error! :-("], "job.log")
    >>> log.messages[0].text, log.abnormal_end, log.end_marker
    ('The following material was not defined: NOMAT', True, False)
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pynumgeo._provenance import CONSOLE_MARK

__all__ = [
    "MAX_CONSOLE_MESSAGES",
    "ConsoleInfo",
    "LogInfo",
    "RawMessage",
    "StaAttempt",
    "StaInfo",
    "StaStep",
    "fortran_float",
    "isclose_time",
    "parse_console",
    "parse_log",
    "parse_sta",
    "read_lines",
    "scan_error_lines",
]

# ----------------------------------------------------------------------------- markers (source lines)
_START = re.compile(r"^-> NUMGEO \*START\*\s*$")  # src/report/report_start_end.f90:56
_END = re.compile(r"^-> NUMGEO \*END\*\s*$")  # src/report/report_start_end.f90:149, :223
_PRE_END = re.compile(r"^-> PREPROCESSING \*END\*\s*$")  # src/database/database.f90:1114
_ERROR_BLOCK = re.compile(r"^-> ERROR:\s*$")  # src/report/report_error_.f90:40; src/database/database.f90:1296
_WARNING_BLOCK = re.compile(r"^-> WARNING:\s*$")  # src/report/report_warning_.f90:40; src/database/database.f90:2418
_ABNORMAL = re.compile(r"->\s*ERROR: Calculation stopped due to an error!")  # src/report/report_error_.f90:43,47,51,60
_SEE_LOG = re.compile(r"^\s*See the \*\.log file for more information\.?\s*$")  # src/report/report_error_.f90:48,52,61
_DIRECT_ERROR = re.compile(r"^(?P<indent>\s*)ERROR:\s?(?P<text>.*)$")  # src/database/database.f90:506-1809
_DIRECT_WARNING = re.compile(r"^\s*Warning:\s*(?P<text>\S.*)$")  # src/workload/workload_.f90:345-352
_ANY_ERROR = re.compile(r"->\s*ERROR\b|^\s*ERROR:")  # runtime.json termination.recommended_success_test
_VERSION = re.compile(r"^\s*\|\s+Version:\s+(?P<version>.+?)\s+\|\s*$")  # src/report/report_construct_.f90:68
_NATIVE_CHECK = re.compile(r"Input check completed")  # check-input flag proposed for numgeo
_COUNTS = re.compile(
    r"^\s{3}(?P<n>\d+) (?P<what>parts|nodes|elements|node sets|surfaces|steps|sections|material definitions|"
    r"soil-water-retention curve definitions) have been identified\s*$"
)  # src/input/read_input.f90:167-182
_TOTAL_TIME = re.compile(
    r"^\s*Total (?:CPU|wall-clock) time =\s*(?P<s>\S+)\s*seconds\s*$"
)  # src/report/report_start_end.f90:152

_STEP_START = re.compile(r"^-> Step = (?P<name>.*?)\s*$")  # src/report/report_statistics.f90:71
_STEP_TYPE = re.compile(r"^\s{3}Type = (?P<type>[A-Z ]+?)\s*$")  # src/report/report_statistics.f90:73-115
_STEP_SOLVER = re.compile(r"^\s{3}Solver = (?P<solver>.*?)\s*$")  # src/report/report_statistics.f90:129
_STEP_END = re.compile(r"^\s*Step suc+es+ful+y terminated")  # src/report/report_statistics.f90:139 ('sucessfully')
_STEP_ITERS = re.compile(r"^\s*Total number of iterations\s*=\s*(?P<n>\d+)")  # src/report/report_statistics.f90:142
_TIME_STATS = re.compile(r"^-> Time Statistics\s*$")  # src/report/report_start_end.f90:159
_STA_DISABLED = re.compile(
    r"Convergence report in the statistic \(sta\) file was deactivated"
)  # src/report/report_start_end.f90:91
_INC = re.compile(
    r"^\s+(?P<inc>\d+|\*+)\s+(?P<iters>\d+|\*+)\s+(?P<total>\S+)\s+(?P<step>\S+)\s+(?P<dt>\S+)"
    r"(?:\s+(?P<dtcrit>\S+)\s+(?P<elem>-?\d+|\*+))?"
    r"(?:\s+rejected \((?P<reason>.*)\))?\s*$"
)  # src/report/report_statistics.f90:207 (format2), :210 (format5)
_INC_EXPLICIT = re.compile(
    r"^\s*(?P<inc>\d+|\*+)\s+(?P<cpu>\S+)\s+(?P<total>\S+)\s+(?P<step>\S+)\s+(?P<dt>\S+)\s*$"
)  # src/report/report_statistics.f90:208 (format3)

# console only (no .log): source lines of the messages, severity
_CONSOLE_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"^Data file not found: "), "error", "src/input/read_command_prompt_.f90:260"),
    (re.compile(r"^INCLUDE file not found: "), "error", "src/input/input_create_internal_input_.f90:76"),
    (re.compile(r"^Invalid number of CPUs requested: "), "error", "src/input/read_command_prompt_.f90:219"),
    (
        re.compile(r"^Invalid number of assembly partitions requested: "),
        "error",
        "src/input/read_command_prompt_.f90:232",
    ),
    (
        re.compile(r"^Requested \d+ OpenMP threads, but the runtime limit is "),
        "warning",
        "src/input/read_command_prompt_.f90:226",
    ),
    (re.compile(r"^Unknown input parameter: "), "error", "src/input/read_command_prompt_.f90:136"),
    (re.compile(r"^Unable to open report file: "), "error", "src/report/report_construct_.f90:135"),
)
_CRASH = re.compile(
    r"Program received signal|Fortran runtime error|forrtl:\s*(?:severe|error)|Segmentation fault|"
    r"segmentation violation|access violation|stack overflow|Killed\s*$|Aborted\s*$|"
    r"double free or corruption|malloc\(\)|Illegal instruction|Floating point exception",
    re.IGNORECASE,
)
_ERROR_DELIMITER = re.compile(
    r"^[-=*~# ]*(?:\*\*\s*)?(?:numgeo\s+)?ERROR\s*(?:\*\*)?[-=*~# ]*$"
)  # src/solver/solver.f90:244-249
_CONSOLE_ERROR = re.compile(r"^(?:ERROR|Error)\b\s*(?:[:(=,]|in\b)")  # e.g. src/tools/lookup_table_1D_.f90:63
_CONSOLE_WARNING = re.compile(r"^(?:WARNING|Warning)\b\s*[:(,]")
#: Console messages kept per severity (the rest is counted in ``ConsoleInfo.suppressed``).
MAX_CONSOLE_MESSAGES = 50
_STOP_CODE = re.compile(r"^\s*(?:ERROR )?STOP\s+(?P<code>.+?)\s*$")  # gfortran/ifx print the stop code
_BACKTRACE = re.compile(r"^\s*(?:#\d+\s+0x|at\s+\S+:\d+\s*$|Error termination\. Backtrace:|Backtrace for this error)")
#: Words of which every console line that :func:`parse_console` reads contains at least one (searched in the
#: line in lower case): lines without them are skipped without the patterns above (a material routine can print
#: millions of lines; a search with ``re.IGNORECASE`` would take as long as the patterns).
_CONSOLE_WORDS = re.compile(
    r"error|warning|version|stop|input check|not found|invalid|requested|unknown|unable|signal|fortran|forrtl|"
    r"segmentation|violation|overflow|killed|aborted|double free|malloc|illegal|floating point"
)


@dataclass(frozen=True)
class RawMessage:
    """A message as found in an output file (before classification)."""

    severity: str  # "error" | "warning" | "info"
    text: str
    origin: str  # "<file>:<line>"
    phase: str | None = None  # "input" | "analysis" | None
    runtime: bool = False
    source: str | None = None  # known source line for console-only messages


@dataclass
class LogInfo:
    """What the ``.log`` says."""

    exists: bool = False
    version: str | None = None
    started: bool = False
    preprocessing_end: bool = False
    end_marker: bool = False
    end_before_error: bool = False  # end marker followed by an error (dt < dtmin)
    abnormal_end: bool = False
    native_check: bool = False
    counts: dict[str, int] = field(default_factory=dict)
    total_time: float | None = None
    messages: list[RawMessage] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class StaAttempt:
    """One line of the increment table (one attempt)."""

    inc: int | None
    iterations: int | None
    total_time: float | None
    step_time: float | None
    dt: float | None
    rejected: str | None
    line: int


@dataclass
class StaStep:
    """One step block of the ``.sta``."""

    name: str
    type: str | None = None
    solver: str | None = None
    attempts: list[StaAttempt] = field(default_factory=list)
    terminated: bool = False
    iterations: int | None = None

    def accepted(self, *, maxinc: int | None = None, nocutback: bool = False) -> list[StaAttempt]:
        """The accepted attempts.

        An attempt is rejected when the next line repeats its increment number (iinc is only advanced
        without a cutback, src/main.f90:574-579). For the last line: accepted if it carries no
        ``rejected`` label; a ``rejected (niter > maxiter)`` label is also printed for increments
        accepted at the last iteration (report_statistics.f90:216) - such a last line counts as
        accepted when the step terminated and either NOCUTBACK is set or its increment number does not
        exceed ``maxinc`` (a rejected attempt ends the increment loop only once ``iinc > maxinc``,
        main.f90:555). In a strength reduction step the FoS logic sets the counter to ``maxinc + 1``
        to end the step (src/database/step_ty_.f90:345), so there only the label decides.
        """
        if self.type == "REDUCTION":
            return [a for a in self.attempts if a.rejected is None]
        out: list[StaAttempt] = []
        n = len(self.attempts)
        for i, a in enumerate(self.attempts):
            if i + 1 < n:
                nxt = self.attempts[i + 1]
                same_known = a.inc is not None and nxt.inc is not None
                ok = nxt.inc != a.inc if same_known else a.rejected is None
            elif a.rejected is None:
                ok = True
            elif self.terminated and a.rejected == "niter > maxiter":
                ok = nocutback or (maxinc is not None and a.inc is not None and a.inc <= maxinc)
            else:
                ok = False
            if ok:
                out.append(a)
        return out


@dataclass
class StaInfo:
    """What the ``.sta`` says."""

    exists: bool = False
    steps: list[StaStep] = field(default_factory=list)
    end_marker: bool = False
    abnormal_end: bool = False
    increments_disabled: bool = False
    error_lines: list[RawMessage] = field(default_factory=list)


@dataclass
class ConsoleInfo:
    """What the console (stdout + stderr) says."""

    version: str | None = None
    messages: list[RawMessage] = field(default_factory=list)
    abnormal_end: bool = False
    native_check: bool = False
    unknown_parameters: list[str] = field(default_factory=list)
    suppressed: dict[str, int] = field(default_factory=dict)


# ----------------------------------------------------------------------------- helpers
def read_lines(path: Path) -> Iterator[str]:
    """Lines of a text file without line ends (bytes decoded as UTF-8, undecodable bytes replaced)."""
    with path.open("r", encoding="utf-8", errors="replace", newline=None) as fh:
        for ln in fh:
            yield ln.rstrip("\r\n")


_FORTRAN_EXP = re.compile(r"^([+-]?\d*\.?\d*)([+-]\d{3,})$")


def fortran_float(text: str) -> float | None:
    """A real written by Fortran (``0.5000E-01``, ``1.000``, ``0.1000-100``, ``NaN``); ``None`` for ``***``.

    >>> fortran_float("0.5000E-01"), fortran_float("0.1000-100"), fortran_float("**********")
    (0.05, 1e-101, None)
    """
    t = text.strip()
    if not t or set(t) == {"*"}:
        return None
    try:
        return float(t.replace("D", "E").replace("d", "e"))
    except ValueError:
        m = _FORTRAN_EXP.match(t)
        if m:
            try:
                return float(f"{m.group(1)}E{m.group(2)}")
            except ValueError:
                return None
        return None


def _int(text: str | None) -> int | None:
    if text is None or not text.strip().isdigit():
        return None
    return int(text)


def _join_chunks(lines: list[str]) -> str:
    """Undo the 70-character chunking of report_.f90:205-238 (3 blanks indent, ``-`` appended)."""
    parts: list[str] = []
    for i, ln in enumerate(lines):
        body = ln[3:] if ln.startswith("   ") else ln.lstrip(" ")
        if i + 1 < len(lines) and body.endswith("-"):
            parts.append(body[:-1])
        else:
            parts.append(body + ("\n" if i + 1 < len(lines) else ""))
    return "".join(parts).strip()


# ----------------------------------------------------------------------------- .log
def parse_log(lines: Iterable[str], name: str = "job.log") -> LogInfo:
    """Parse the lines of a ``.log`` file (see the module docstring)."""
    info = LogInfo(exists=True)
    buf = list(lines)
    phase = "input"
    i = 0
    n = len(buf)
    while i < n:
        ln = buf[i]
        if info.version is None:
            m = _VERSION.match(ln)
            if m:
                info.version = m.group("version")
        if _START.match(ln):
            info.started = True
        elif _PRE_END.match(ln):
            info.preprocessing_end = True
            phase = "analysis"
        elif _END.match(ln):
            info.end_marker = True
        elif _ABNORMAL.search(ln):
            info.abnormal_end = True
        elif _NATIVE_CHECK.search(ln):
            info.native_check = True
        elif (m := _COUNTS.match(ln)) is not None:
            info.counts[m.group("what")] = int(m.group("n"))
        elif (m := _TOTAL_TIME.match(ln)) is not None:
            info.total_time = fortran_float(m.group("s"))
        elif _ERROR_BLOCK.match(ln) or _WARNING_BLOCK.match(ln):
            sev = "error" if _ERROR_BLOCK.match(ln) else "warning"
            j = i + 1
            body: list[str] = []
            while j < n and buf[j].strip() and not _ABNORMAL.search(buf[j]) and len(body) < 200:
                body.append(buf[j])
                j += 1
            if sev == "error" and info.end_marker:
                info.end_before_error = True
            info.messages.append(RawMessage(sev, _join_chunks(body), f"{name}:{i + 1}", phase))
            i = j
            continue
        elif (m := _DIRECT_ERROR.match(ln)) is not None and not ln.lstrip().startswith("->"):
            j, text = _direct_block(buf, i, m)
            info.messages.append(RawMessage("error", text, f"{name}:{i + 1}", phase))
            i = j
            continue
        elif (m := _DIRECT_WARNING.match(ln)) is not None:
            info.messages.append(RawMessage("warning", m.group("text").strip(), f"{name}:{i + 1}", phase))
        i += 1
    return info


def _direct_block(buf: list[str], i: int, m: re.Match[str], prefix: str = "ERROR: ") -> tuple[int, str]:
    """``ERROR: text`` plus continuation lines (deeper indented; after a bare ``ERROR:``: any non-blank)."""
    indent = len(m.group("indent"))
    head = m.group("text").rstrip()
    lines = [(prefix + head).rstrip()]
    j = i + 1
    while j < len(buf) and j - i <= 20:
        nxt = buf[j]
        if not nxt.strip() or nxt.startswith("->") or _DIRECT_ERROR.match(nxt):
            break
        lead = len(nxt) - len(nxt.lstrip(" "))
        if head and lead <= indent:
            break
        if not head and lead < indent:
            break
        lines.append(nxt.strip())
        j += 1
    return j, "\n".join(lines)


# ----------------------------------------------------------------------------- .sta
def parse_sta(lines: Iterable[str], name: str = "job.sta") -> StaInfo:
    """Parse the lines of a ``.sta`` file (see the module docstring)."""
    info = StaInfo(exists=True)
    cur: StaStep | None = None
    for no, ln in enumerate(lines, start=1):
        if (m := _STEP_START.match(ln)) is not None:
            cur = StaStep(name=m.group("name").strip())
            info.steps.append(cur)
            continue
        if _END.match(ln):
            info.end_marker = True
            cur = None
            continue
        if _TIME_STATS.match(ln):
            cur = None
            continue
        if _ABNORMAL.search(ln):
            info.abnormal_end = True
            continue
        if _STA_DISABLED.search(ln):
            info.increments_disabled = True
            continue
        if _SEE_LOG.match(ln):
            continue
        if _ANY_ERROR.search(ln):
            info.error_lines.append(RawMessage("error", ln.strip(), f"{name}:{no}"))
            continue
        if cur is None:
            continue
        if (m := _STEP_TYPE.match(ln)) is not None and cur.type is None:
            cur.type = m.group("type").strip()
        elif (m := _STEP_SOLVER.match(ln)) is not None and cur.solver is None:
            cur.solver = m.group("solver")
        elif _STEP_END.match(ln):
            cur.terminated = True
        elif (m := _STEP_ITERS.match(ln)) is not None:
            cur.iterations = int(m.group("n"))
        elif cur.type == "EXPLICIT DYNAMIC" and (m := _INC_EXPLICIT.match(ln)) is not None:
            cur.attempts.append(
                StaAttempt(
                    inc=_int(m.group("inc")),
                    iterations=None,
                    total_time=fortran_float(m.group("total")),
                    step_time=fortran_float(m.group("step")),
                    dt=fortran_float(m.group("dt")),
                    rejected=None,
                    line=no,
                )
            )
        elif (m := _INC.match(ln)) is not None:
            cur.attempts.append(
                StaAttempt(
                    inc=_int(m.group("inc")),
                    iterations=_int(m.group("iters")),
                    total_time=fortran_float(m.group("total")),
                    step_time=fortran_float(m.group("step")),
                    dt=fortran_float(m.group("dt")),
                    rejected=m.group("reason"),
                    line=no,
                )
            )
    return info


def scan_error_lines(lines: Iterable[str], name: str) -> tuple[bool, list[RawMessage]]:
    """Error markers of a ``.msg`` file: (generic abnormal end found, other error lines)."""
    abnormal = False
    other: list[RawMessage] = []
    for no, ln in enumerate(lines, start=1):
        if "ERROR" not in ln:
            continue
        if _ABNORMAL.search(ln):
            abnormal = True
        elif _ANY_ERROR.search(ln):
            other.append(RawMessage("error", ln.strip(), f"{name}:{no}"))
    return abnormal, other


# ----------------------------------------------------------------------------- console
def parse_console(lines: Iterable[str], name: str = "console") -> ConsoleInfo:
    """Parse the console output (stdout and stderr merged).

    The first line of a console log written by pynumgeo (:func:`pynumgeo._provenance.console_header`) is
    skipped. Recognised: the banner version, the closing line of ``report%error`` (report_error_.f90:60-61), the
    console-only messages of the start-up (:data:`_CONSOLE_PATTERNS`), Fortran runtime and OS crash
    messages, ``STOP``/``ERROR STOP`` codes with text, error blocks between delimiter lines
    (``-------- ERROR --------``, ``** numgeo ERROR **``, e.g. solver.f90:244-249), and lines starting
    with ``ERROR``/``Error`` (errors written directly, e.g. ``ERROR: transform_traction, ...``,
    load_library.f90) or ``WARNING``/``Warning``. At most :data:`MAX_CONSOLE_MESSAGES` messages per
    severity are kept (material routines can print one per integration point); the rest are counted.
    """
    info = ConsoleInfo()
    buf = [ln.rstrip() for ln in lines]
    counts = {"error": 0, "warning": 0}

    def add(m: RawMessage) -> None:
        k = "warning" if m.severity == "warning" else "error"
        counts[k] += 1
        if counts[k] <= MAX_CONSOLE_MESSAGES or m.runtime:
            info.messages.append(m)
        else:
            info.suppressed[k] = info.suppressed.get(k, 0) + 1

    i = 0
    n = len(buf)
    while i < n:
        ln = buf[i]
        if not _CONSOLE_WORDS.search(ln.lower()):  # no pattern below can match (each needs one of the words)
            i += 1
            continue
        s = ln.strip()
        j = i + 1
        if not s or (i == 0 and ln.startswith(CONSOLE_MARK)):  # empty, or the line pynumgeo writes first
            pass
        elif info.version is None and (m := _VERSION.match(ln)) is not None:
            info.version = m.group("version")
        elif _ABNORMAL.search(ln):
            info.abnormal_end = True
        elif _SEE_LOG.match(ln) or s.startswith('-> WARNING: See the "*.log"-file') or _BACKTRACE.match(ln):
            pass
        elif _NATIVE_CHECK.search(ln):
            info.native_check = True
        elif (hit := next(((sev, src) for rx, sev, src in _CONSOLE_PATTERNS if rx.match(s)), None)) is not None:
            if s.startswith("Unknown input parameter: "):
                info.unknown_parameters.append(s.split(":", 1)[1].strip())
                # skip the help text that follows (read_command_prompt_.f90:137-147)
                while j < n and buf[j].strip() and buf[j].strip().startswith(("Use ", "Or ", "...")):
                    j += 1
                text = s
            else:
                j = _console_block_end(buf, i)
                text = "\n".join(x.strip() for x in buf[i:j])
            add(RawMessage(hit[0], text, f"{name}:{i + 1}", None, False, hit[1]))
        elif _CRASH.search(ln):
            j = _console_block_end(buf, i)
            text = "\n".join(x.strip() for x in buf[i:j] if not _BACKTRACE.match(x))
            add(RawMessage("error", text, f"{name}:{i + 1}", None, True))
        elif (m := _STOP_CODE.match(ln)) is not None:
            code = m.group("code").strip().strip("'\"")
            if re.search(r"[A-Za-z]", code):
                add(RawMessage("error", code, f"{name}:{i + 1}"))
        elif _ERROR_DELIMITER.match(s):
            body: list[str] = []
            while j < n and not _ERROR_DELIMITER.match(buf[j].strip()) and len(body) < 15:
                if _STOP_CODE.match(buf[j]) or _ABNORMAL.search(buf[j]):
                    break
                if buf[j].strip():
                    body.append(buf[j].strip())
                j += 1
            if j < n and _ERROR_DELIMITER.match(buf[j].strip()):
                j += 1
            add(RawMessage("error", "\n".join(body) or s, f"{name}:{i + 1}"))
        elif (m := _DIRECT_ERROR.match(ln)) is not None:
            j, text = _direct_block(buf, i, m)
            add(RawMessage("error", text, f"{name}:{i + 1}"))
        elif _CONSOLE_ERROR.match(s):
            m2 = re.match(r"^(?P<indent>\s*)(?P<text>.*)$", ln)
            assert m2 is not None
            j, text = _direct_block(buf, i, m2, prefix="")
            add(RawMessage("error", text, f"{name}:{i + 1}"))
        elif _CONSOLE_WARNING.match(s):
            add(RawMessage("warning", s, f"{name}:{i + 1}"))
        i = j
    return info


def _console_block_end(buf: list[str], i: int) -> int:
    j = i + 1
    while j < len(buf) and buf[j].strip() and j - i < 10 and not _BACKTRACE.match(buf[j]):
        if any(rx.match(buf[j].strip()) for rx, _, _ in _CONSOLE_PATTERNS) or _DIRECT_ERROR.match(buf[j]):
            break
        j += 1
    return j


def isclose_time(a: float, b: float) -> bool:
    """Equality of a step time from the ``.sta`` (4 significant digits) with an end time from the deck."""
    return math.isclose(a, b, rel_tol=1e-3, abs_tol=1e-12)
