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
# 15.11.2026, J. Machacek - Only a line starting with *Include is an include; lines that are too long stop
#                           numgeo instead of being truncated (numgeo-src aa15af6, 23530eb)
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""Emulation of numgeo's preprocessing of an input file.

numgeo first copies the input file into an internal file (``<job>_internal.inp``) and parses only that
copy (``src/input/input_create_internal_input_.f90``). The rules, reproduced here one by one:

1. Every physical line is read into 1024 characters. A line that fills them and has no ``**`` in them stops
   numgeo with an error (:70-74, :225-239). If the 1024th character is a blank, the characters behind it are
   not read and numgeo has no message (quirk ``line-cut``).
2.``**`` starts a comment anywhere in a line; blank lines are dropped (:76-81, :147-170).
3. A line that starts with ``*INCLUDE`` (after leading blanks, any case) is an include: the text after the
   first ``=`` (leading and trailing blanks removed) plus ``.inp`` is copied in; includes are not nested
   (:83-111).
4. Lines are upper-cased (ASCII letters only) (:144).
5. All blanks are deleted, except between the first and the last ``$`` of a line (:172-177).
6. A comma at the end of a line is removed (:179-186).
7. A line that is then longer than 256 characters stops numgeo with an error (:188-194).
8. The line ``*AMPLITUDE,NAME=DEFAULT,TYPE=RAMP`` is prepended (:67).

The line numbers are those of the numgeo-src of 31.10.2026 (commits aa15af6 and 23530eb). Before, a line was
an include if it contained the word INCLUDE anywhere, and lines were cut after 256 characters without a message.

Every resulting :class:`Line` keeps the solver's text (``text``), the same text without upper-casing
(``cased``, used to keep the user's spelling of names) and its source position. Deviations from what a
careful user would expect (lines that are too long, tabs, nested includes) are reported as :class:`Quirk`
objects, never silently corrected.

Examples:
    >>> pre = preprocess_text("*Step, name = Load 1  ** first step\\n*Static\\n0.1, 1., 1e-5, 1.,\\n")
    >>> [ln.text for ln in pre.lines][1:]
    ['*STEP,NAME=LOAD1', '*STATIC', '0.1,1.,1E-5,1.']
    >>> pre.lines[1].cased
    '*Step,name=Load1'
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "DEFAULT_AMPLITUDE_LINE",
    "MAX_LINE",
    "MAX_RAW_LINE",
    "Line",
    "Preprocessed",
    "Quirk",
    "SourcePos",
    "preprocess",
    "preprocess_text",
    "upper_ascii",
]

#: Longest line of the internal input file (``len_line``): a line without blanks and comments.
MAX_LINE = 256
#: Longest physical line, blanks and comments included (``len_line_raw - 1``).
MAX_RAW_LINE = 1023
#: Line that numgeo prepends to every internal input file.
DEFAULT_AMPLITUDE_LINE = "*AMPLITUDE,NAME=DEFAULT,TYPE=RAMP"

_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def upper_ascii(text: str) -> str:
    """Upper-case ASCII letters only, like numgeo's ``convert_to_uppercase``.

    >>> upper_ascii("Grün-1")
    'GRüN-1'
    """
    return text.translate(_UPPER)


@dataclass(frozen=True)
class SourcePos:
    """Position of a physical line: file and 1-based line number."""

    file: str
    line: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}"


@dataclass(frozen=True)
class Line:
    """One line of the internal input file as numgeo sees it.

    Attributes:
        text: upper-cased text with blanks removed (what the solver parses).
        cased: the same text without upper-casing (same length as ``text``).
        pos: source position, ``None`` for the prepended default amplitude.
        raw: the physical line as read (its first 1024 characters).
    """

    text: str
    cased: str
    pos: SourcePos | None
    raw: str

    @property
    def is_keyword(self) -> bool:
        """True if the line starts with ``*``."""
        return self.text.startswith("*")


@dataclass(frozen=True)
class Quirk:
    """Something in the input that numgeo treats differently than a reader might expect."""

    code: str
    message: str
    pos: SourcePos | None = None
    severity: str = "warning"  # "error": numgeo stops

    def __str__(self) -> str:
        where = f"{self.pos}: " if self.pos else ""
        return f"{where}{self.code}: {self.message}"


@dataclass
class Preprocessed:
    """Result of :func:`preprocess`: the internal lines plus everything worth reporting."""

    lines: list[Line]
    quirks: list[Quirk] = field(default_factory=list)
    includes: list[Path] = field(default_factory=list)

    @property
    def internal_text(self) -> str:
        """The internal file numgeo would write (``<job>_internal.inp``)."""
        return "".join(ln.text + "\n" for ln in self.lines)


IncludeResolver = Callable[[str], tuple[str, str]]
"""Maps an include name (text after ``=``) to ``(display name, file content)``."""


def _read_text(path: Path) -> str:
    # numgeo reads bytes; latin-1 maps every byte to one character, so lengths and truncation match.
    return path.read_bytes().decode("latin-1")


def _physical_lines(text: str) -> list[str]:
    # Fortran formatted reads end a record at LF; a CR before it is dropped by the Windows runtime.
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]


def _strip_comment(s: str) -> str:
    pos = s.find("**")
    return s[:pos] if pos >= 0 else s


def _delete_blanks(cased: str) -> str:
    """numgeo's ``delete_character`` / ``delete_character_except`` for blanks (``$`` segments kept)."""
    up = cased.rstrip(" ")
    i1 = up.find("$")
    if i1 < 0:
        return up.replace(" ", "")
    i2 = up.rfind("$")
    out = []
    for i, ch in enumerate(up):
        if i1 <= i < i2:
            continue
        if i == i2:
            out.append(up[i1 : i2 + 1])
        elif ch != " ":
            out.append(ch)
    return "".join(out)


def _drop_trailing_comma(s: str) -> str:
    pos = s.rfind(",")
    if pos >= 0 and s[pos + 1 : pos + 6].strip(" ") == "":
        return s[:pos]
    return s


def _internal(raw: str, pos: SourcePos | None, quirks: list[Quirk]) -> Line | None:
    """``write_internal_input`` for one physical line (read into at most 1024 characters)."""
    cased = _strip_comment(raw)
    if cased.strip(" ") == "":
        return None
    if "\t" in cased:
        quirks.append(Quirk("tab", "tab characters are not blanks for numgeo and stay in the line", pos))
    cased = _drop_trailing_comma(_delete_blanks(cased))
    if len(cased) > MAX_LINE:
        quirks.append(
            Quirk(
                "line-too-long",
                f"line has {len(cased)} characters without blanks and comments, the maximum is {MAX_LINE}; numgeo "
                "stops. Split the data over several lines",
                pos,
                "error",
            )
        )
    return Line(text=upper_ascii(cased), cased=cased, pos=pos, raw=raw)


def _is_include(body: str) -> bool:
    """A line (without its comment) that starts with ``*INCLUDE`` after leading blanks, in any case."""
    return upper_ascii(body).lstrip(" ").startswith("*INCLUDE")


def _truncate(raw: str, pos: SourcePos, quirks: list[Quirk]) -> str:
    """The first 1024 characters of a physical line (``check_raw_line_length``): numgeo stops if the line fills
    them without a ``**``; with a ``**`` the rest is taken as part of the comment. If the 1024th character is a
    blank, numgeo has no message: data behind it is not read."""
    buffer = raw[: MAX_RAW_LINE + 1]
    if "**" in buffer:
        return buffer
    if len(buffer.rstrip(" ")) > MAX_RAW_LINE:
        quirks.append(
            Quirk(
                "line-too-long",
                f"line has at least {MAX_RAW_LINE + 1} characters (blanks and comments included), the maximum is "
                f"{MAX_RAW_LINE}; numgeo stops. Split the data over several lines",
                pos,
                "error",
            )
        )
    elif _strip_comment(raw[MAX_RAW_LINE + 1 :]).strip(" ") != "":
        quirks.append(
            Quirk(
                "line-cut",
                f"numgeo reads the first {MAX_RAW_LINE + 1} characters of a line only: the data behind them is "
                "ignored without a message. Split the data over several lines",
                pos,
            )
        )
    return buffer


def preprocess_text(
    text: str,
    name: str = "<string>",
    include_resolver: IncludeResolver | None = None,
) -> Preprocessed:
    """Preprocess input text like numgeo (see module docstring).

    Args:
        text: content of the master input file.
        name: file name used in source positions.
        include_resolver: returns ``(display name, content)`` for an include name; without it,
            includes raise :class:`FileNotFoundError`.
    """
    quirks: list[Quirk] = []
    lines: list[Line] = [Line(DEFAULT_AMPLITUDE_LINE, DEFAULT_AMPLITUDE_LINE, None, DEFAULT_AMPLITUDE_LINE)]
    includes: list[Path] = []
    for i, raw0 in enumerate(_physical_lines(text), start=1):
        pos = SourcePos(name, i)
        raw = _truncate(raw0, pos, quirks)
        body = _strip_comment(raw)
        if body.strip(" ") == "":
            continue
        if _is_include(body):
            eq = body.find("=")
            inc = body[eq + 1 :].strip(" ") if eq >= 0 else ""
            if include_resolver is None:
                raise FileNotFoundError(f"{pos}: include {inc!r} cannot be resolved without a file path")
            try:
                shown, content = include_resolver(inc)
            except FileNotFoundError as e:
                raise FileNotFoundError(f"{pos}: {e}") from None
            includes.append(Path(shown))
            for j, iraw0 in enumerate(_physical_lines(content), start=1):
                ipos = SourcePos(shown, j)
                iraw = _truncate(iraw0, ipos, quirks)
                if iraw.strip(" ") == "":
                    continue
                if _is_include(_strip_comment(iraw)):
                    quirks.append(
                        Quirk(
                            "nested-include",
                            "includes are not nested: numgeo copies this line verbatim",
                            ipos,
                        )
                    )
                ln = _internal(iraw, ipos, quirks)
                if ln is not None:
                    lines.append(ln)
            continue
        ln = _internal(raw, pos, quirks)
        if ln is not None:
            lines.append(ln)
    return Preprocessed(lines=lines, quirks=quirks, includes=includes)


def preprocess(path: str | os.PathLike[str], workdir: str | os.PathLike[str] | None = None) -> Preprocessed:
    """Preprocess an input file like numgeo.

    Args:
        path: the master ``.inp`` file.
        workdir: folder in which numgeo would run (include names are relative to it). Defaults to the
            folder of ``path`` — the way pynumgeo runs jobs.

    Raises:
        FileNotFoundError: if the file or an include is missing (numgeo stops in that case too).
    """
    p = Path(path)
    base = Path(workdir) if workdir is not None else p.parent

    def resolve(inc: str) -> tuple[str, str]:
        f = base / (inc + ".inp")
        if not f.is_file():
            raise FileNotFoundError(f"INCLUDE file not found: {f} (numgeo stops)")
        return str(f), _read_text(f)

    return preprocess_text(_read_text(p), name=str(p), include_resolver=resolve)
