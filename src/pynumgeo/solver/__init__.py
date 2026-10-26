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
"""Run numgeo and judge the outcome.

:func:`run` writes or copies the input into a job folder, starts numgeo there
(``numgeo inp=<job> out=<job> ncpus=<n>``), streams the console and decides from the report files
whether the run succeeded (:class:`RunStatus`): numgeo's exit status is 0 after most errors
(``report%error`` ends with a plain ``stop``, src/report/report_error_.f90:62), so
pynumgeo reads the ``.log``, ``.sta``, ``.msg``, the console and the dump files, and checks that every
step reached its end time (a step whose ``inc=`` is exhausted ends silently, src/main.f90:555).
:func:`assess` judges a job folder that has already run.

Example (needs numgeo; ``NUMGEO_EXE`` or ``numgeo`` on ``PATH``)::

    from pynumgeo.solver import run
    res = run("model.inp", "runs/beam", job="beam", ncpus=2, timeout=600, on_line=print)
    print(res.status, res.reason)
    for s in res.steps:
        print(s.name, s.t_reached, "/", s.t_end, s.increments, "increments", s.cutbacks, "cutbacks")
    for m in res.errors:
        print(m.text, m.message_id)    # e.g. src/input/read_input.f90:543

    res = run(deck, "runs/check", check_only=True)   # INPUT_ACCEPTED or FAILED with the input errors

Examples:
    >>> from pynumgeo.solver import RunStatus
    >>> [s.value for s in RunStatus]
    ['SUCCESS', 'FAILED', 'INCOMPLETE', 'TIMEOUT', 'CRASHED', 'INPUT_ACCEPTED']
"""

from pynumgeo.solver.executable import (
    ENV_VARIABLE,
    KNOWN_FLAGS,
    ExecutableNotFoundError,
    check_flags,
    check_job_name,
    locate_executable,
)
from pynumgeo.solver.messages import MessageMatch, classify
from pynumgeo.solver.outcome import assess
from pynumgeo.solver.result import RunFailedError, RunResult, RunStatus, SolverMessage, StepReport
from pynumgeo.solver.runner import NATIVE_CHECK_FLAG, run

__all__ = [
    "ENV_VARIABLE",
    "KNOWN_FLAGS",
    "NATIVE_CHECK_FLAG",
    "ExecutableNotFoundError",
    "MessageMatch",
    "RunFailedError",
    "RunResult",
    "RunStatus",
    "SolverMessage",
    "StepReport",
    "assess",
    "check_flags",
    "check_job_name",
    "classify",
    "locate_executable",
    "run",
]
