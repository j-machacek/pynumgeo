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
"""Numbers in numgeo result files (Fortran formatted output).

numgeo writes reals with ``E``/``G`` edit descriptors and list-directed output. Besides what Python's
``float`` reads, these contain

* a 3-digit exponent without ``E``: ``0.123457-100`` (``E15.6``/``G14.6`` with ``|exponent| > 99``);
* no leading zero: ``.100000000E+01`` (``E14.9`` time column of the print files,
  ``src/output/print_type.f90:387,449``);
* ``NaN``/``Infinity``/``-Infinity`` for non-finite values (gfortran and ifx spelling).

A field filled with ``*`` (Fortran overflow) is not a number and raises :class:`ValueError`.

Examples:
    >>> parse_result_real("0.123456-100")
    1.23456e-101
    >>> parse_result_real(".100000000E+01"), parse_result_real("-Infinity")
    (1.0, -inf)
    >>> parse_result_reals(["1.0", "0.5-100", "NaN"]).tolist()
    [1.0, 5e-101, nan]
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from pynumgeo.io.numbers import parse_real

__all__ = ["parse_result_real", "parse_result_reals"]

_NONFINITE = {
    "nan": float("nan"),
    "+nan": float("nan"),
    "-nan": float("nan"),
    "inf": float("inf"),
    "+inf": float("inf"),
    "infinity": float("inf"),
    "+infinity": float("inf"),
    "-inf": float("-inf"),
    "-infinity": float("-inf"),
}


def parse_result_real(token: str) -> float:
    """Parse one real written by numgeo (see the module docstring).

    Raises:
        ValueError: if the token is not a number (e.g. a Fortran overflow field ``*****``).
    """
    t = token.strip()
    special = _NONFINITE.get(t.lower())
    if special is not None:
        return special
    return parse_real(t)


def parse_result_reals(tokens: Sequence[str]) -> npt.NDArray[np.float64]:
    """Parse many reals; fast path through numpy, exact Fortran fallback per token.

    Raises:
        ValueError: naming the first token that is not a number.
    """
    try:
        return np.array(tokens, dtype=np.float64)
    except ValueError:
        pass
    out = np.empty(len(tokens), dtype=np.float64)
    for i, tok in enumerate(tokens):
        try:
            out[i] = parse_result_real(tok)
        except ValueError:
            raise ValueError(f"not a number: {tok!r} (value {i + 1} of {len(tokens)})") from None
    return out
