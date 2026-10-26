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
"""pynumgeo — Python API for the finite element code numgeo.

Read, build, validate and write numgeo input decks, run the solver and read its results::

    import pynumgeo as ng

    deck = ng.read("model.inp")              # numgeo input -> Deck (mesh, materials, steps, ...)
    issues = ng.validate(deck)               # what numgeo would reject or read differently
    ng.write(deck, "job/model.inp")          # normal-case, deterministic numgeo input
    res = ng.run(deck, "job", job="model")   # run numgeo, judge the outcome from its logs
    frames = ng.open_results("job", "model").frames()

Everything numgeo-specific (keywords, options, element types, constitutive models, messages) comes from
the catalogue (:mod:`pynumgeo.catalogue`), generated from the numgeo source. Submodules are imported
lazily, so ``import pynumgeo`` stays fast. The functions ``run`` and ``validate`` live in the subpackages
:mod:`pynumgeo.solver` and :mod:`pynumgeo.validation`; the subpackages are named differently from the
functions so that importing one never replaces ``pynumgeo.run`` or ``pynumgeo.validate`` by a module.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from pynumgeo._version import NUMGEO_DOCS_COMMIT, NUMGEO_SOURCE_COMMIT, NUMGEO_VERSION, __version__

if TYPE_CHECKING:  # pragma: no cover
    from pynumgeo import catalogue
    from pynumgeo.deck import Amplitude, Deck, Keyword, Material, Section, Step
    from pynumgeo.io.reader import ReadError, ReadResult, parse, parse_text, read
    from pynumgeo.io.writer import WriteError, write, write_text
    from pynumgeo.issue import Issue
    from pynumgeo.mesh import Mesh
    from pynumgeo.results import open_results
    from pynumgeo.solver import RunResult, RunStatus, run
    from pynumgeo.validation import BuildProfile, validate

__all__ = [
    "NUMGEO_DOCS_COMMIT",
    "NUMGEO_SOURCE_COMMIT",
    "NUMGEO_VERSION",
    "Amplitude",
    "BuildProfile",
    "Deck",
    "Issue",
    "Keyword",
    "Material",
    "Mesh",
    "ReadError",
    "ReadResult",
    "RunResult",
    "RunStatus",
    "Section",
    "Step",
    "WriteError",
    "__version__",
    "catalogue",
    "open_results",
    "parse",
    "parse_text",
    "read",
    "run",
    "validate",
    "write",
    "write_text",
]

_LAZY = {
    "catalogue": ("pynumgeo.catalogue", None),
    "Amplitude": ("pynumgeo.deck", "Amplitude"),
    "Deck": ("pynumgeo.deck", "Deck"),
    "Keyword": ("pynumgeo.deck", "Keyword"),
    "Material": ("pynumgeo.deck", "Material"),
    "Section": ("pynumgeo.deck", "Section"),
    "Step": ("pynumgeo.deck", "Step"),
    "Mesh": ("pynumgeo.mesh", "Mesh"),
    "Issue": ("pynumgeo.issue", "Issue"),
    "ReadError": ("pynumgeo.io.reader", "ReadError"),
    "ReadResult": ("pynumgeo.io.reader", "ReadResult"),
    "parse": ("pynumgeo.io.reader", "parse"),
    "parse_text": ("pynumgeo.io.reader", "parse_text"),
    "read": ("pynumgeo.io.reader", "read"),
    "WriteError": ("pynumgeo.io.writer", "WriteError"),
    "write": ("pynumgeo.io.writer", "write"),
    "write_text": ("pynumgeo.io.writer", "write_text"),
    "BuildProfile": ("pynumgeo.validation", "BuildProfile"),
    "validate": ("pynumgeo.validation", "validate"),
    "run": ("pynumgeo.solver", "run"),
    "RunResult": ("pynumgeo.solver", "RunResult"),
    "RunStatus": ("pynumgeo.solver", "RunStatus"),
    "open_results": ("pynumgeo.results", "open_results"),
}


def __getattr__(name: str) -> Any:
    try:
        mod, attr = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module 'pynumgeo' has no attribute {name!r}") from None
    m = importlib.import_module(mod)
    value = m if attr is None else getattr(m, attr)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
