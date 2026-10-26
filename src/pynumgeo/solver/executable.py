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
"""Executable, command line and environment of a numgeo run.

numgeo reads its arguments with a substring search for fixed lower- or upper-case literals in a fixed
order, first match wins (src/input/read_command_prompt_.f90:96-148); unknown arguments only print a help
text and the run continues (:135-148). pynumgeo therefore passes only literals it knows, one per
argument: ``inp=<job> out=<job> ncpus=<n>`` plus the flags below.

Examples:
    >>> check_job_name("footing_1")
    'footing_1'
    >>> command("/opt/numgeo/numgeo", "job", 2, ["no-msg"])
    ['/opt/numgeo/numgeo', 'inp=job', 'out=job', 'ncpus=2', 'no-msg']
    >>> env = build_environment(4, None, base={"PATH": "/bin"})
    >>> env.variables["OMP_NUM_THREADS"], env.variables["OMP_STACKSIZE"], env.notes
    ('4', '64M', [])
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "ENV_VARIABLE",
    "KNOWN_FLAGS",
    "ExecutableNotFoundError",
    "RunEnvironment",
    "build_environment",
    "check_flags",
    "check_job_name",
    "command",
    "locate_executable",
]

#: Environment variable naming the numgeo executable.
ENV_VARIABLE = "NUMGEO_EXE"

#: Flags numgeo understands (src/input/read_command_prompt_.f90:116-134), with what they do.
#: ``check-memory`` is accepted by numgeo but has no effect.
KNOWN_FLAGS: dict[str, str] = {
    "check-sets": "check members of node and element sets (read_set_.f90:446)",
    "check-material": "error for the first element without a material (read_input.f90:560-594)",
    "check-memory": "accepted, no effect",
    "no-msg": "no convergence report in the .msg, no .conv records (main.f90:460,851,861)",
    "no-sta": "no increment lines in the .sta (main.f90:915); step end times cannot be verified",
    "diagnostics": "<out>-embedded-*.res diagnostic files",
    "debug": "developer trace, consistency checks, element dump + stop instead of a cutback",
}
#: Flags with a value (``key=value``).
_VALUE_FLAGS = ("oldjob=", "assembly-partitions=")

_JOB = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]*")
_RESERVED = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(10)} | {f"lpt{i}" for i in range(10)}


class ExecutableNotFoundError(FileNotFoundError):
    """No numgeo executable could be found."""


def locate_executable(executable: str | os.PathLike[str] | None = None) -> Path:
    """Find the numgeo executable.

    Order: the argument, the environment variable ``NUMGEO_EXE``, then ``numgeo`` (``numgeo.exe``
    on Windows) on ``PATH``. A name without a path in the argument or in ``NUMGEO_EXE`` is looked up on
    ``PATH``.

    Args:
        executable: path or name of the executable.

    Returns:
        Absolute path of an existing executable file.

    Raises:
        ExecutableNotFoundError: nothing found, or the given file does not exist or is not executable.
    """
    if executable is not None:
        return _resolve(str(executable), "the executable argument")
    env = os.environ.get(ENV_VARIABLE)
    if env:
        return _resolve(env, f"the environment variable {ENV_VARIABLE}")
    for name in ("numgeo", "numgeo.exe"):
        hit = shutil.which(name)
        if hit:
            return Path(hit).resolve()
    raise ExecutableNotFoundError(
        "numgeo executable not found: pass executable=..., set the environment variable "
        f"{ENV_VARIABLE} to the full path of numgeo (numgeo.exe on Windows), or put it on PATH"
    )


def _resolve(value: str, what: str) -> Path:
    p = Path(value).expanduser()
    if p.is_file():
        if not os.access(p, os.X_OK):
            raise ExecutableNotFoundError(f"{p} (from {what}) is not executable")
        return p.resolve()
    if p.is_dir():
        for name in ("numgeo", "numgeo.exe"):
            if (p / name).is_file():
                return _resolve(str(p / name), what)
        raise ExecutableNotFoundError(f"{p} (from {what}) is a folder without numgeo / numgeo.exe")
    if os.sep not in value and (os.altsep is None or os.altsep not in value):
        hit = shutil.which(value)
        if hit:
            return Path(hit).resolve()
    raise ExecutableNotFoundError(f"numgeo executable {value!r} (from {what}) does not exist")


def check_job_name(job: str) -> str:
    """Return ``job`` if numgeo can use it as ``inp=``/``out=`` name, else raise :class:`ValueError`.

    Allowed: letters, digits, ``_`` and ``-``, not starting with ``-``, not a Windows device name.
    A ``.`` makes numgeo cut the name (``.INP`` test, read_command_prompt_.f90:155-161), a path
    breaks the VTK output, blanks and shell characters break the unquoted ``rm -rf <out>-out``
    (VTK_type.f90:1041-1048); a leading ``-`` would be read as an option of ``rm``.

    >>> check_job_name("my job")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: job name 'my job' is not allowed: use letters, digits, '_' and '-' only ...
    """
    if not isinstance(job, str) or _JOB.fullmatch(job) is None:
        raise ValueError(
            f"job name {job!r} is not allowed: use letters, digits, '_' and '-' only "
            "(no path, no '.', no blanks; not starting with '-')"
        )
    if job.lower() in _RESERVED:
        raise ValueError(f"job name {job!r} is a reserved device name on Windows")
    return job


def check_flags(flags: Iterable[str]) -> list[str]:
    """Validate extra command-line flags and return them as a list.

    Known flags: :data:`KNOWN_FLAGS`, ``oldjob=<job name>`` (restart, main.f90:493-497) and
    ``assembly-partitions=<integer >= 0>``. ``inp=``, ``out=`` and ``ncpus=`` are set by
    :func:`pynumgeo.solver.run`; ``check-input`` is requested with ``check_only=True, native_check=True``.

    Raises:
        ValueError: unknown or malformed flag.
    """
    out: list[str] = []
    for f in flags:
        if not isinstance(f, str):
            raise ValueError(f"flag {f!r} is not a string")
        if f in KNOWN_FLAGS:
            out.append(f)
            continue
        key, eq, value = f.partition("=")
        if eq and key + "=" in _VALUE_FLAGS:
            if key == "oldjob":
                check_job_name(value)
            elif not (value.isdigit()):
                raise ValueError(f"flag {f!r}: assembly-partitions needs an integer >= 0")
            out.append(f)
            continue
        if key in ("inp", "out", "ncpus"):
            raise ValueError(f"flag {f!r}: {key}= is set by run() (job=..., ncpus=...)")
        if f == "check-input":
            raise ValueError("flag 'check-input': use run(..., check_only=True, native_check=True)")
        known = sorted([*KNOWN_FLAGS, "oldjob=<job>", "assembly-partitions=<n>"])
        raise ValueError(f"unknown numgeo flag {f!r}; known flags: {', '.join(known)}")
    return out


def command(executable: str | os.PathLike[str], job: str, ncpus: int, flags: Iterable[str] = ()) -> list[str]:
    """The command line ``[exe, "inp=<job>", "out=<job>", "ncpus=<n>", *flags]``."""
    return [str(executable), f"inp={job}", f"out={job}", f"ncpus={int(ncpus)}", *flags]


@dataclass
class RunEnvironment:
    """Environment of the child process plus remarks for the result."""

    variables: dict[str, str]
    notes: list[str] = field(default_factory=list)


#: OpenMP stack size used when none is set (numgeo README; the benchmark runner uses the same).
DEFAULT_OMP_STACKSIZE = "64M"


def build_environment(
    ncpus: int,
    env: Mapping[str, str | None] | None,
    base: Mapping[str, str] | None = None,
) -> RunEnvironment:
    """Environment for the numgeo process.

    Precedence (highest first):

    1. ``env`` (the ``env=`` argument of :func:`pynumgeo.solver.run`); a value ``None`` removes a variable.
    2. pynumgeo's settings: ``OMP_NUM_THREADS=<ncpus>``; ``OMP_STACKSIZE=64M`` only if it is not set.
    3. The inherited environment (``base``, default ``os.environ``).

    ``OMP_NUM_THREADS`` from ``env`` is kept even if it differs from ``ncpus`` (numgeo's own threads
    follow ``ncpus=``, read_command_prompt_.f90:240-241); an inherited value that differs is replaced.
    Both cases are reported in ``notes``.
    """
    variables = dict(os.environ if base is None else base)
    notes: list[str] = []
    n = str(int(ncpus))
    inherited = variables.get("OMP_NUM_THREADS")
    if inherited is not None and inherited != n and not (env and "OMP_NUM_THREADS" in env):
        notes.append(f"inherited OMP_NUM_THREADS={inherited} replaced by {n} (ncpus)")
    variables["OMP_NUM_THREADS"] = n
    variables.setdefault("OMP_STACKSIZE", DEFAULT_OMP_STACKSIZE)
    for k, v in (env or {}).items():
        if v is None:
            variables.pop(k, None)
        else:
            variables[k] = str(v)
    given = (env or {}).get("OMP_NUM_THREADS")
    if given is not None and str(given) != n:
        notes.append(
            f"OMP_NUM_THREADS={given} from env differs from ncpus={n}; numgeo uses ncpus= for its own "
            "threads (read_command_prompt_.f90:240-241)"
        )
    return RunEnvironment(variables, notes)
