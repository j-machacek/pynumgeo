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
"""Numbers as numgeo reads and writes them.

numgeo reads values with Fortran list-directed input (``read(line, *)``). That accepts more spellings
than Python's ``float``: ``210d6``, ``1.0D-3``, ``1.0+5`` (exponent without letter), ``.5`` and ``5.``.
Result files contain numbers such as ``0.123456-100`` (three-digit exponent without ``E``).

pynumgeo writes reals as Python's shortest round-trip representation, which numgeo reads back
exactly, and never writes ``inf`` or ``nan``.

Examples:
    >>> parse_real("210d6")
    210000000.0
    >>> parse_real("1.0+5")
    100000.0
    >>> parse_real(".5")
    0.5
    >>> format_real(1e-5), format_real(210e6), format_real(-0.0)
    ('1e-05', '210000000.0', '-0.0')
    >>> is_number("FIX")
    False
"""

from __future__ import annotations

import math
import re

__all__ = ["format_int", "format_real", "is_number", "parse_int", "parse_real", "to_token"]

# mantissa: digits with optional point; exponent: [EeDdQq][sign]digits or sign digits
_REAL = re.compile(
    r"""^[+-]?(?:\d+\.?\d*|\.\d+)       # mantissa
        (?:(?:[EeDdQq][+-]?\d+)|(?:[+-]\d+))?$  # exponent with letter, or sign + digits
    """,
    re.VERBOSE,
)
_INT = re.compile(r"^[+-]?\d+$")
_NUMSTART = frozenset("+-.0123456789")
_LETTERS = re.compile(r"[A-DF-Za-df-z]")  # any letter except e/E (float() would accept inf/nan)


def is_number(token: str) -> bool:
    """True if ``token`` is a number in Fortran list-directed syntax (no inf/nan)."""
    return bool(_REAL.match(token.strip()))


def parse_real(token: str) -> float:
    """Parse a real the way Fortran list-directed input does.

    Raises:
        ValueError: if the token is not a Fortran real.
    """
    t = token.strip()
    if not _REAL.match(t):
        raise ValueError(f"not a number: {token!r}")
    t = t.translate(str.maketrans("dDqQ", "eEeE"))
    m = re.match(r"^([+-]?(?:\d+\.?\d*|\.\d+))([+-]\d+)$", t)
    if m:  # exponent given as sign + digits without a letter
        t = f"{m.group(1)}e{m.group(2)}"
    return float(t)


def parse_int(token: str) -> int:
    """Parse an integer (list-directed input; no decimal point allowed).

    Raises:
        ValueError: if the token is not an integer.
    """
    t = token.strip()
    if not _INT.match(t):
        raise ValueError(f"not an integer: {token!r}")
    return int(t)


def format_real(value: float) -> str:
    """Shortest text that numgeo reads back as exactly ``value``.

    Raises:
        ValueError: for inf and nan, which numgeo input must not contain.
    """
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"numgeo input cannot contain {v!r}")
    return repr(v)


def format_int(value: int) -> str:
    """Integer as text."""
    return str(int(value))


def to_token(text: str) -> int | float | str:
    """Data token: ``int`` for integers, ``float`` for reals (Fortran syntax), else the text unchanged.

    This is how the reader turns the fields of a data line into tokens; :class:`~pynumgeo.deck.Keyword`
    applies it to text tokens as well, so that ``"2.0"`` and ``2.0`` are the same token.

    >>> to_token("12"), to_token("0.0d0"), to_token("Soil.all")
    (12, 0.0, 'Soil.all')
    """
    t = text.strip()
    if _INT.match(t):
        return int(t)
    if t[:1] in _NUMSTART and not _LETTERS.search(t):
        try:
            return float(t)
        except ValueError:
            pass
    if is_number(t):
        return parse_real(t)
    return t
