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
"""Console output: the word filter of :func:`pynumgeo.solver.logs.parse_console` skips only lines that no
pattern reads, and a long console of a material routine is read quickly."""

from __future__ import annotations

import re
import time

import pytest

from pynumgeo.solver import logs

# one line (or block) for every branch of parse_console, mixed into lines that no pattern reads
MESSAGES = [
    "pynumgeo 0.1 (Python API for numgeo by Jan Machacek): console output of numgeo inp=job",
    "   |   Version:   numgeo2026-v2 (Oct 26 2026)   |",
    "-> ERROR: Calculation stopped due to an error! :-(",
    "   See the *.log file for more information.",
    "Input check completed",
    "Data file not found: table.txt",
    "INCLUDE file not found: mesh.inp",
    "Invalid number of CPUs requested: 0",
    "Invalid number of assembly partitions requested: -1",
    "Requested 64 OpenMP threads, but the runtime limit is 8",
    "Unknown input parameter: foo=1",
    "   Use inp=<name> ...",
    "Unable to open report file: job.log",
    "Program received signal SIGSEGV: Segmentation fault - invalid memory reference.",
    "Backtrace for this error:",
    "#0  0x7f0a in ???",
    "forrtl: severe (174): SIGSEGV, segmentation fault occurred",
    "Fortran runtime error: End of file",
    "stack overflow",
    "Killed",
    "Aborted",
    "double free or corruption (out)",
    "malloc(): corrupted top size",
    "Illegal instruction",
    "Floating point exception",
    "ERROR STOP Lookup table out of range",
    "STOP 1",
    "-------- ERROR --------",
    "   matrix is singular",
    "-------- ERROR --------",
    "  ERROR: transform_traction, unknown surface",
    "     continued text of the error",
    "Error in umat: negative void ratio",
    "WARNING: element 12 distorted",
    "Warning, small pivot",
]
NOISE = [
    " material routine: substep 12, error estimate 1.0e-4, ok",  # contains 'error' but no pattern
    "   increment 5 iteration 3 rhs 1.2e-05",
    "",
    "   ",
    "assembling 12000 elements",
    "  stopping criterion reached",
]


def _all_lines(monkeypatch: pytest.MonkeyPatch | None, lines: list[str]) -> logs.ConsoleInfo:
    if monkeypatch is not None:  # without the filter: every line goes through the patterns
        monkeypatch.setattr(logs, "_CONSOLE_WORDS", re.compile(""))
    return logs.parse_console(lines, "console")


@pytest.mark.parametrize("seed", range(5))
def test_word_filter_reads_as_without_it(monkeypatch: pytest.MonkeyPatch, seed: int) -> None:
    import random

    rng = random.Random(seed)
    lines = []
    for message in MESSAGES:
        lines += rng.sample(NOISE, k=rng.randint(0, len(NOISE)))
        lines.append(message)
    filtered = logs.parse_console(lines, "console")
    plain = _all_lines(monkeypatch, lines)
    assert filtered == plain
    assert len(filtered.messages) >= 15 and filtered.version and filtered.abnormal_end and filtered.native_check


def test_every_message_line_contains_a_word() -> None:
    # not: the lines parse_console passes over and the lines after the first line of a block
    skipped = ("pynumgeo ", "   See the", "#0", "   Use", "   matrix", "     continued")
    for message in MESSAGES:
        if message.strip() and not message.startswith(skipped):
            assert logs._CONSOLE_WORDS.search(message.lower()), message


def test_long_console_is_read_quickly(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [" material routine: substep 12, estimate 1.0e-4, ok"] * 100_000 + ["Error in umat: negative void ratio"]
    start = time.perf_counter()
    info = logs.parse_console(lines, "console")
    filtered = time.perf_counter() - start
    assert [m.text for m in info.messages] == ["Error in umat: negative void ratio"]
    start = time.perf_counter()
    assert _all_lines(monkeypatch, lines) == info
    assert filtered < 0.5 * (time.perf_counter() - start)  # about 5 times faster
