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
"""Start numgeo for a deck or an input file and judge the outcome.

The job folder is numgeo's working directory: numgeo reads ``<job>.inp`` from it and writes every report
and output file into it (runtime inventory §3). What goes into the folder:

* a :class:`~pynumgeo.deck.Deck` is written as ``<job>.inp`` with :func:`pynumgeo.io.writer.write`;
* an input file is copied as ``<job>.inp``. numgeo resolves ``*Include`` names relative to its working
  directory (input_create_internal_input_.f90:70-97), so includes are resolved relative to the folder
  of the original file and copied **into** ``<job>.inp`` textually, line by line, with numgeo's own rule
  (a line whose upper-cased text before ``**`` contains ``INCLUDE`` is replaced by ``<name>.inp``, the
  text after the first ``=``). The input text is not otherwise changed (no reading and re-writing by
  pynumgeo). Nested includes are an error (numgeo does not nest them). If the input file already is
  ``<workdir>/<job>.inp`` it is used in place. Other files the input refers to (amplitude tables,
  initial stress files, user libraries, restart folders) must be passed with ``files=`` or be in the
  job folder already.

Before the start, the report files of an earlier run of the same job (``.log .sta .msg .conv
.conv.fields`` and the console file) are deleted, so a run that stops before numgeo opens them is not
judged by stale files. numgeo itself deletes ``<job>-out/``, ``<job>-print-out/`` and ``<job>_restart/``.

The process: ``[exe, "inp=<job>", "out=<job>", "ncpus=<n>", *flags]`` in the job folder, ``stdin``
closed (no argument would start the guided mode that reads stdin), stdout and stderr merged into
``<job>.console.log`` (its first line names the pynumgeo version and the command,
:func:`pynumgeo._provenance.console_header`) and streamed line by line to ``on_line``. On POSIX the child
gets the hard limit of the stack size as its soft limit (numgeo needs a large stack: the Windows build
links with a 1 GB stack) and runs in its own session, so a timeout kills the whole process tree (shell
commands, external solvers, submodel runs); on Windows the tree is killed with ``taskkill /T``.

Examples:
    >>> import pathlib, sys, tempfile
    >>> res = run(pathlib.Path("missing.inp"), tempfile.mkdtemp(), executable=sys.executable)
    Traceback (most recent call last):
    ...
    FileNotFoundError: input file missing.inp does not exist
"""

from __future__ import annotations

import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import IO

from pynumgeo._provenance import console_header
from pynumgeo.deck.deck import Deck
from pynumgeo.io.lexer import upper_ascii
from pynumgeo.solver import executable as _exe
from pynumgeo.solver.outcome import RunFacts, judge
from pynumgeo.solver.result import RunResult

__all__ = ["NATIVE_CHECK_FLAG", "POLL_INTERVAL", "prepare_input", "run"]

#: Command-line flag of the native input check (proposed for numgeo, not in its source yet).
NATIVE_CHECK_FLAG = "check-input"
#: Seconds between two looks at the ``.log`` (input check) and the ``.sta`` (``on_sta``).
POLL_INTERVAL = 0.05
#: Seconds an executable with the native input check gets to stop by itself after the marker.
NATIVE_GRACE = 5.0
_REPORT_EXTENSIONS = (".log", ".sta", ".msg", ".conv", ".conv.fields", ".console.log")
_PRE_END = "-> PREPROCESSING *END*"  # src/database/database.f90:1114


def run(
    deck_or_path: Deck | str | os.PathLike[str],
    workdir: str | os.PathLike[str],
    job: str = "job",
    executable: str | os.PathLike[str] | None = None,
    ncpus: int = 1,
    timeout: float | None = None,
    check_only: bool = False,
    flags: Iterable[str] = (),
    env: Mapping[str, str | None] | None = None,
    on_line: Callable[[str], None] | None = None,
    *,
    native_check: bool = False,
    files: Iterable[str | os.PathLike[str]] = (),
    on_sta: Callable[[str], None] | None = None,
) -> RunResult:
    """Run numgeo and judge the outcome.

    Args:
        deck_or_path: a :class:`~pynumgeo.deck.Deck` or the path of an input file (see module docstring).
        workdir: job folder (created if missing); numgeo's working directory.
        job: job name, used as ``inp=`` and ``out=`` (letters, digits, ``_``, ``-``).
        executable: the numgeo executable; default ``NUMGEO_EXE``, then ``numgeo`` on ``PATH``
            (:func:`~pynumgeo.solver.locate_executable`).
        ncpus: number of threads (``ncpus=``; ``OMP_NUM_THREADS`` is set to the same value).
        timeout: seconds after which the process tree is killed (status ``TIMEOUT``); ``None``: no limit.
        check_only: only check the input: stop numgeo as soon as the ``.log`` shows
            ``-> PREPROCESSING *END*`` (input read and model database built, database.f90:1114) and
            report ``INPUT_ACCEPTED`` (or ``FAILED`` with the input errors). Errors of the remaining
            setup (constraints, embedded regions, output initialisation) are not reached.
        flags: further numgeo flags (:data:`~pynumgeo.solver.executable.KNOWN_FLAGS`, ``oldjob=<job>``,
            ``assembly-partitions=<n>``).
        env: environment variables for numgeo (``None`` as value removes one). Precedence: ``env`` >
            ``OMP_NUM_THREADS=<ncpus>`` and ``OMP_STACKSIZE=64M`` (only if unset) > inherited environment;
            deviations are reported in ``result.notes``.
        on_line: called with every console line (stdout and stderr) while numgeo runs.
        native_check: with ``check_only``, also pass ``check-input`` so that an executable that knows
            the flag stops by itself after the input phase. An executable without it prints "Unknown input
            parameter" and starts the analysis; pynumgeo then stops it at the same point.
        files: further files copied into the job folder before the run (same base name).
        on_sta: called with every new line of ``<job>.sta`` (one line per increment attempt) while
            numgeo runs.

    Returns:
        The :class:`~pynumgeo.solver.RunResult`.

    Raises:
        ValueError: invalid job name, flag or ``ncpus``.
        FileNotFoundError: the input file, an include or one of ``files`` does not exist.
        ExecutableNotFoundError: no numgeo executable.
    """
    _exe.check_job_name(job)
    flag_list = _exe.check_flags(flags)
    if any(f.lower() == f"oldjob={job}".lower() for f in flag_list):
        # <out>_restart is deleted when the new job initialises its restart output (restart_.f90:104-112,
        # main.f90:259-261) before <oldjob>_restart is read (main.f90:488-497)
        raise ValueError(f"oldjob= must name another job than job={job!r}")
    if not isinstance(ncpus, int) or isinstance(ncpus, bool) or ncpus < 1:
        raise ValueError(f"ncpus must be an integer >= 1, got {ncpus!r}")
    if timeout is not None and timeout <= 0:
        raise ValueError(f"timeout must be positive, got {timeout!r}")
    exe = _exe.locate_executable(executable)
    wd = Path(workdir).resolve()

    if isinstance(deck_or_path, Deck):
        deck: Deck | None = deck_or_path
        wd.mkdir(parents=True, exist_ok=True)
        notes = _clean_reports(wd, job)
        from pynumgeo.io.writer import write

        write(deck_or_path, wd / f"{job}.inp")
    else:
        src = Path(deck_or_path)
        if not src.is_file():
            raise FileNotFoundError(f"input file {src} does not exist")
        wd.mkdir(parents=True, exist_ok=True)
        notes = _clean_reports(wd, job)
        notes += prepare_input(src, wd, job)
        deck, read_note = _read_deck(wd / f"{job}.inp")
        if read_note:
            notes.append(read_note)
    for f in files:
        fp = Path(f)
        if not fp.is_file():
            raise FileNotFoundError(f"file {fp} (files=) does not exist")
        if fp.resolve() != (wd / fp.name).resolve():
            shutil.copy2(fp, wd / fp.name)
    notes += _licence(exe, wd)
    for d in (f"{job}-out", f"{job}-print-out", f"{job}_restart"):
        if (wd / d).exists():
            notes.append(f"numgeo deletes the existing folder {d}/ of an earlier run at the start")

    environment = _exe.build_environment(ncpus, env)
    notes += environment.notes
    args = list(flag_list)
    if check_only and native_check:
        args.append(NATIVE_CHECK_FLAG)
    cmd = _exe.command(exe, job, ncpus, args)
    before = _snapshot(wd)
    facts = RunFacts(
        command=cmd,
        timeout=timeout,
        check_only=check_only,
        native_check=check_only and native_check,
        flags=flag_list,
        before=before,
        notes=notes,
    )
    _execute(cmd, wd, job, environment.variables, facts, on_line, on_sta)
    return judge(wd, job, deck, facts)


# ----------------------------------------------------------------------------- input
def prepare_input(src: Path, workdir: Path, job: str) -> list[str]:
    """Put ``src`` into ``workdir`` as ``<job>.inp`` with its includes inlined (see module docstring).

    Returns:
        Notes for the result (e.g. which includes were inlined).

    Raises:
        FileNotFoundError: an include file is missing (numgeo would stop with "INCLUDE file not found",
            input_create_internal_input_.f90:74-79).
        ValueError: an include file contains an include (numgeo does not nest includes).
    """
    target = workdir / f"{job}.inp"
    if target.exists() and target.resolve() == src.resolve():
        return []
    data = src.read_bytes().decode("latin-1")  # bytes kept exactly: latin-1 maps each byte to one character
    out: list[str] = []
    inlined: list[str] = []
    for no, raw in enumerate(_split_keep(data), start=1):
        name = _include_name(raw)
        if name is None:
            out.append(raw)
            continue
        inc = src.parent / f"{name}.inp"
        if not inc.is_file():
            raise FileNotFoundError(
                f"{src}:{no}: INCLUDE file not found: {inc} (numgeo stops; every line whose text before '**' "
                "contains INCLUDE is an include for numgeo, input_create_internal_input_.f90:71)"
            )
        content = inc.read_bytes().decode("latin-1")
        for ino, iraw in enumerate(_split_keep(content), start=1):
            if _include_name(iraw) is not None:
                raise ValueError(f"{inc}:{ino}: nested include; numgeo does not nest includes")
            out.append(iraw if iraw.endswith("\n") else iraw + "\n")
        inlined.append(f"{name}.inp")
    target.write_bytes("".join(out).encode("latin-1"))
    if inlined:
        return [f"includes inlined into {target.name}: {', '.join(inlined)}"]
    return []


def _split_keep(text: str) -> list[str]:
    """Lines with their ``\\n`` (a Fortran record ends at LF only; ``str.splitlines`` would also split at
    other control characters)."""
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _include_name(raw: str) -> str | None:
    """numgeo's include test: 256 characters, comment cut at ``**``, ``INCLUDE`` anywhere (case-insensitive).

    The name is the text after the first ``=`` (src/input/input_create_internal_input_.f90:58-74), with
    blanks removed at both ends like :func:`pynumgeo.io.lexer.preprocess` does.
    """
    line = raw.rstrip("\r\n")[:256]
    pos = line.find("**")
    if pos >= 0:
        line = line[:pos]
    if not line.strip() or "INCLUDE" not in upper_ascii(line):
        return None
    eq = line.find("=")
    return line[eq + 1 :].strip(" ") if eq >= 0 else ""


def _read_deck(path: Path) -> tuple[Deck | None, str | None]:
    """The deck of the job file for the end times of the steps (pynumgeo's reader)."""
    from pynumgeo.io.reader import parse

    try:
        return parse(path).deck, None
    except Exception as exc:  # the reader is not needed to run; its failure only limits the checks
        return (
            None,
            f"pynumgeo could not read {path.name} ({type(exc).__name__}: {exc}); step end times not checked",
        )


def _clean_reports(workdir: Path, job: str) -> list[str]:
    removed = []
    for ext in _REPORT_EXTENSIONS:
        p = workdir / f"{job}{ext}"
        if p.is_file():
            p.unlink()
            removed.append(p.name)
    return [f"removed report files of an earlier run: {', '.join(removed)}"] if removed else []


def _licence(exe: Path, workdir: Path) -> list[str]:
    """Public builds read ``numgeo.lic`` from the working directory (src/tools/license_.f90:90)."""
    lic = exe.parent / "numgeo.lic"
    if lic.is_file() and not (workdir / "numgeo.lic").exists():
        shutil.copy2(lic, workdir / "numgeo.lic")
        return ["numgeo.lic copied from the folder of the executable into the job folder (license_.f90:90)"]
    return []


def _snapshot(workdir: Path) -> dict[Path, tuple[int, int]]:
    out: dict[Path, tuple[int, int]] = {}
    for root, _dirs, names in os.walk(workdir):
        for n in names:
            p = Path(root, n)
            try:
                st = p.stat()
            except OSError:
                continue
            out[p.resolve()] = (st.st_mtime_ns, st.st_size)
    return out


# ----------------------------------------------------------------------------- process
def _raise_stack_limit() -> None:  # pragma: no cover - runs in the child process
    try:
        import resource

        _soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
    except (ImportError, OSError, ValueError):
        pass


def _popen(cmd: list[str], workdir: Path, env: dict[str, str]) -> subprocess.Popen[bytes]:
    if os.name == "nt":  # pragma: no cover - Windows
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.Popen(
            cmd,
            cwd=workdir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
    return subprocess.Popen(
        cmd,
        cwd=workdir,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        preexec_fn=_raise_stack_limit,
    )


def _kill_tree(proc: subprocess.Popen[bytes], grace: float = 2.0) -> None:
    """Terminate the process and everything it started (TERM, then KILL after ``grace`` seconds)."""
    if proc.poll() is not None and os.name == "nt":  # pragma: no cover - Windows
        return
    if os.name == "nt":  # pragma: no cover - Windows
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)
        return
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 5.0)):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=wait)
            # the group may outlive the leader: make sure nothing is left
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return
        except subprocess.TimeoutExpired:
            continue
        return


def _reader(stream: IO[bytes], q: queue.Queue[bytes | None]) -> None:
    try:
        for chunk in iter(stream.readline, b""):
            q.put(chunk)
    finally:
        q.put(None)


class _Tail:
    """Incremental reader of a growing text file (complete lines only)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.pos = 0
        self.rest = b""

    def lines(self) -> list[str]:
        try:
            with self.path.open("rb") as fh:
                fh.seek(self.pos)
                data = fh.read()
        except OSError:
            return []
        if not data:
            return []
        self.pos += len(data)
        data = self.rest + data
        parts = data.split(b"\n")
        self.rest = parts.pop()
        return [p.decode("utf-8", "replace").rstrip("\r") for p in parts]


def _execute(
    cmd: list[str],
    workdir: Path,
    job: str,
    env: dict[str, str],
    facts: RunFacts,
    on_line: Callable[[str], None] | None,
    on_sta: Callable[[str], None] | None,
) -> None:
    console_path = workdir / f"{job}.console.log"
    log_tail = _Tail(workdir / f"{job}.log")
    sta_tail = _Tail(workdir / f"{job}.sta")
    lines: list[str] = []
    q: queue.Queue[bytes | None] = queue.Queue()
    start = time.monotonic()
    proc = _popen(cmd, workdir, env)
    assert proc.stdout is not None
    t = threading.Thread(target=_reader, args=(proc.stdout, q), daemon=True)
    t.start()
    eof = False
    exited_at: float | None = None
    pre_end_at: float | None = None
    try:
        with console_path.open("w", encoding="utf-8", newline="\n") as console:
            console.write(console_header(cmd) + "\n")
            while True:
                try:
                    item = q.get(timeout=POLL_INTERVAL)
                except queue.Empty:
                    item = b""
                batch = [item]
                while True:  # drain what is there
                    try:
                        batch.append(q.get_nowait())
                    except queue.Empty:
                        break
                for chunk in batch:
                    if chunk is None:
                        eof = True
                    elif chunk:
                        line = chunk.decode("utf-8", "replace").rstrip("\r\n")
                        lines.append(line)
                        console.write(line.rstrip() + "\n")
                        if on_line is not None:
                            on_line(line)
                console.flush()
                if on_sta is not None:
                    for ln in sta_tail.lines():
                        on_sta(ln)
                if facts.check_only and not facts.stopped_by_runner and proc.poll() is None:
                    if pre_end_at is None and any(ln.startswith(_PRE_END) for ln in log_tail.lines()):
                        pre_end_at = time.monotonic()
                    # an executable that knows check-input stops by itself right after the marker: give it a moment
                    native = facts.native_check and not any(
                        "Unknown input parameter" in ln and NATIVE_CHECK_FLAG in ln for ln in lines[:40]
                    )
                    if pre_end_at is not None and (not native or time.monotonic() - pre_end_at > NATIVE_GRACE):
                        _kill_tree(proc)
                        facts.stopped_by_runner = True
                if (
                    facts.timeout is not None
                    and not facts.timed_out
                    and proc.poll() is None
                    and time.monotonic() - start > facts.timeout
                ):
                    _kill_tree(proc)
                    facts.timed_out = True
                if proc.poll() is not None:
                    if eof:
                        break
                    # stdout may be held open by a grandchild: wait a moment for the rest, then stop
                    exited_at = exited_at or time.monotonic()
                    if time.monotonic() - exited_at > 2.0:
                        break
    except BaseException:
        _kill_tree(proc)
        raise
    finally:
        if proc.poll() is None or not eof:
            # still running, or a process numgeo started still holds the console open: end the tree
            _kill_tree(proc)
    if not eof:
        facts.notes.append("processes started by numgeo were still running after it ended; they were killed")
    if on_sta is not None:
        for ln in sta_tail.lines():
            on_sta(ln)
    facts.exit_code = proc.wait()
    facts.duration = time.monotonic() - start
    facts.console_lines = lines
