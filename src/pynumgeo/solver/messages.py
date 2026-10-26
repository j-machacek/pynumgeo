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
"""Attach the solver source location to a message text.

The catalogue's message inventory (``catalogue/data/messages.json``, generated from the numgeo source)
holds one template per error, warning and stop site, e.g. ``"The following material was not defined:
{mdb%section(isection)%mat_name}"`` at ``src/input/read_input.f90:543``. Each template is turned into a
regular expression: ``{...}`` placeholders match any text, the literal text must match with any amount of
white space between words (numgeo splits messages into 70-character chunks, report_.f90:205-238, and
numbers are written with or without leading blanks). A message is matched against every template;
the best match is the one whose severity fits and which has the most literal text. Templates with less
than :data:`MIN_LITERAL` literal characters (e.g. ``{cmdmsg}``) and the templates of the report module
itself (the block markers) are not used.

Messages are sometimes shorter than their template (a console shows only the first line of a two-line
message, a ``.log`` line can be cut): a message that matches no template as a whole is matched against
the leading lines of multi-line templates (at least :data:`MIN_PREFIX_LITERAL` literal characters), and
leading parts of a multi-line message are tried last.

The matched source line is also mapped to the pynumgeo validator rules whose ``source`` covers it.

Examples:
    >>> m = classify("The following material was not defined: NOMAT", "error")
    >>> m.message_id, m.routine
    ('src/input/read_input.f90:543', 'read_input_file')
    >>> classify("this text is not a numgeo message", "error") is None
    True
"""

from __future__ import annotations

import functools
import re
from collections.abc import Sequence
from dataclasses import dataclass

from pynumgeo import catalogue as _cat

__all__ = [
    "MIN_LITERAL",
    "MIN_PREFIX_LITERAL",
    "MessageMatch",
    "classify",
    "normalise_text",
    "rules_for_source",
    "source_ranges",
]

#: Minimum number of literal (non-blank, non-placeholder) characters for a template to be used.
MIN_LITERAL = 6
#: Minimum number of literal characters of the leading lines of a template used for a partial match.
MIN_PREFIX_LITERAL = 16

_PLACEHOLDER = re.compile(r"\{[^{}]*\}")
_WS = re.compile(r"\s+")
_PREFIX = re.compile(r"^\s*(?:->\s*)?(?:ERROR|WARNING)\s*:\s*", re.IGNORECASE)
_WORD = re.compile(r"[^\s]{4,}")
_DELIMITER = re.compile(r"^[-=*~# ]*(?:\*\*\s*)?(?:numgeo\s+)?ERROR\s*(?:\*\*)?[-=*~# ]*$")
_COMPATIBLE = {
    "error": ("error", "fatal-stop"),
    "warning": ("warning",),
    "info": ("info",),
}


@dataclass(frozen=True)
class MessageMatch:
    """The template a message text matches.

    Attributes:
        message_id: catalogue id ``src/...f90:<line>``.
        file: solver source file.
        line: solver source line.
        routine: routine containing the line.
        severity: severity of the template (``error``, ``warning``, ``fatal-stop``, ``info``).
        terminates: whether the solver stops at this site.
        candidates: ids of all equally good templates (identical text written at several sites).
    """

    message_id: str
    file: str
    line: int
    routine: str | None
    severity: str
    terminates: bool | None
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class _Variant:
    regex: re.Pattern[str]
    literal: int
    keys: tuple[str, ...]


@dataclass(frozen=True)
class _Template:
    id: str
    file: str
    line: int
    routine: str | None
    severity: str
    terminates: bool | None
    full: _Variant
    prefixes: tuple[_Variant, ...]  # leading lines of a multi-line template, longest first


def normalise_text(text: str) -> str:
    """Drop delimiter lines (``** numgeo ERROR **``) and a leading ``ERROR:``, collapse white space.

    >>> normalise_text("  ERROR: No valid material\\n   -> Check")
    'No valid material -> Check'
    >>> normalise_text(" \\n** numgeo ERROR **\\n  The AMGCL solver is deactivated\\n** numgeo ERROR **")
    'The AMGCL solver is deactivated'
    """
    kept = "\n".join(ln for ln in text.splitlines() if not _DELIMITER.match(ln.strip()))
    return _WS.sub(" ", _PREFIX.sub("", kept.strip())).strip()


def _compile(template: str) -> _Variant:
    t = normalise_text(template)
    parts: list[str] = []
    literal = 0
    keys: list[str] = []
    pos = 0
    for m in _PLACEHOLDER.finditer(t):
        parts.append(_literal(t[pos : m.start()]))
        parts.append("(?:.*?)")
        literal += len(_WS.sub("", t[pos : m.start()]))
        keys += _WORD.findall(t[pos : m.start()])
        pos = m.end()
    parts.append(_literal(t[pos:]))
    literal += len(_WS.sub("", t[pos:]))
    keys += _WORD.findall(t[pos:])
    rx = re.compile(r"\s*" + "".join(parts) + r"\s*", re.IGNORECASE | re.DOTALL)
    # the longest literal words are used as a cheap pre-filter
    return _Variant(rx, literal, tuple(k.upper() for k in sorted(keys, key=len, reverse=True)[:2]))


def _literal(s: str) -> str:
    words = s.split()
    if not words:
        return r"\s*"
    return r"\s*" + r"\s*".join(re.escape(w) for w in words) + r"\s*"


@functools.cache
def _templates() -> tuple[_Template, ...]:
    out: list[_Template] = []
    for m in _cat.load().messages():
        t = m.get("template")
        if not t or str(m.get("file", "")).startswith("src/report/"):
            continue
        full = _compile(str(t))
        if full.literal < MIN_LITERAL:
            continue
        lines = [ln for ln in str(t).splitlines() if ln.strip()]
        prefixes = [_compile("\n".join(lines[:k])) for k in range(len(lines) - 1, 0, -1)]
        out.append(
            _Template(
                id=str(m["id"]),
                file=str(m["file"]),
                line=int(m["line"]),
                routine=m.get("routine"),
                severity=str(m.get("severity")),
                terminates=m.get("terminates"),
                full=full,
                prefixes=tuple(p for p in prefixes if p.literal >= MIN_PREFIX_LITERAL),
            )
        )
    return tuple(out)


def classify(text: str, severity: str | None = None) -> MessageMatch | None:
    """Find the message template that ``text`` was produced from.

    Args:
        text: message as written by numgeo (chunks joined; a leading ``ERROR:`` is ignored).
        severity: severity seen in the output (``error`` / ``warning`` / ``info``); templates of a
            compatible severity are preferred.

    Returns:
        The best match, or ``None`` if no template matches (see the module docstring for partial
        matches).
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    found = _classify_one(normalise_text(text), severity, partial=False)
    if found is None:
        found = _classify_one(normalise_text(text), severity, partial=True)
    for n in range(len(lines) - 1, 0, -1):
        if found is not None:
            break
        found = _classify_one(normalise_text("\n".join(lines[:n])), severity, partial=False)
    return found


def _classify_one(norm: str, severity: str | None, *, partial: bool) -> MessageMatch | None:
    if not norm:
        return None
    up = norm.upper()
    compatible = _COMPATIBLE.get(severity or "", ())
    best: list[tuple[tuple[int, int], _Template]] = []
    for t in _templates():
        for v in t.prefixes if partial else (t.full,):
            if any(k not in up for k in v.keys) or v.regex.fullmatch(norm) is None:
                continue
            best.append(((1 if t.severity in compatible else 0, v.literal), t))
            break
    if not best:
        return None
    top = max(s for s, _ in best)
    winners = [t for s, t in best if s == top]
    w = winners[0]
    return MessageMatch(
        message_id=w.id,
        file=w.file,
        line=w.line,
        routine=w.routine,
        severity=w.severity,
        terminates=w.terminates,
        candidates=tuple(t.id for t in winners),
    )


# ----------------------------------------------------------------------------- validator rules
_SRC_RANGE = re.compile(r"(src/[^\s:;,()]+\.f90):([0-9][0-9,\-\s]*)")


def source_ranges(source: str | None) -> list[tuple[str, int, int]]:
    """``(file, first, last)`` line ranges cited in a rule's ``source`` text.

    >>> for r in source_ranges("src/a.f90:93-154; src/b.f90:539-546,560"):
    ...     print(r)
    ('src/a.f90', 93, 154)
    ('src/b.f90', 539, 546)
    ('src/b.f90', 560, 560)
    >>> source_ranges("src/input/read_material_.f90")
    []
    """
    out: list[tuple[str, int, int]] = []
    for m in _SRC_RANGE.finditer(source or ""):
        for part in m.group(2).split(","):
            a, _, b = part.strip().partition("-")
            if not a.strip().isdigit():
                continue
            lo = int(a)
            hi = int(b) if b.strip().isdigit() else lo
            out.append((m.group(1), lo, hi))
    return out


@functools.cache
def _rule_index() -> tuple[tuple[str, int, int, str], ...]:
    try:
        from pynumgeo.validation import rules as _rules  # noqa: F401  (registers the rules)
        from pynumgeo.validation.engine import rules
    except ImportError:  # pragma: no cover - the validator is part of the package
        return ()
    return tuple((f, lo, hi, r.id) for r in rules() for f, lo, hi in source_ranges(r.source))


def rules_for_source(file: str, line: int, candidates: Sequence[str] = ()) -> tuple[str, ...]:
    """Validator rule ids whose ``source`` (``src/...f90:<a>-<b>``) covers ``file:line`` or a candidate.

    Only rules that cite line numbers are considered (a rule citing a whole file is too vague).
    """
    sites = {(file, line)}
    for c in candidates:
        f, _, ln = c.rpartition(":")
        if ln.isdigit():
            sites.add((f, int(ln)))
    ids = {rid for f, lo, hi, rid in _rule_index() for sf, sl in sites if f == sf and lo <= sl <= hi}
    return tuple(sorted(ids))
