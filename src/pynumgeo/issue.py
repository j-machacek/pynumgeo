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
"""Issues reported by the reader and the validator.

Examples:
    >>> i = Issue("NG-MESH-001", "error", "node labels must be 1..n", location="model.inp:3")
    >>> str(i)
    'NG-MESH-001 error  model.inp:3  node labels must be 1..n'
    >>> i.as_dict()["severity"]
    'error'
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

__all__ = ["Issue", "Severity", "has_errors"]

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Issue:
    """One finding.

    Attributes:
        id: rule id, e.g. ``NG-STEP-003`` (stable; documented in the validator).
        severity: ``error`` (numgeo fails or computes something else than intended), ``warning``,
            ``info``.
        message: what is wrong and what to do.
        location: ``file:line`` or an object path such as ``steps[0].items[2]``.
        keyword: the keyword concerned, if any.
        source: solver source location of the behaviour the rule mirrors (``src/...:line``).
    """

    id: str
    severity: Severity
    message: str
    location: str | None = None
    keyword: str | None = None
    source: str | None = None

    def __str__(self) -> str:
        parts = [self.id, self.severity]
        if self.location:
            parts.append(" " + self.location)
        parts.append(" " + self.message)
        return " ".join(parts)

    def as_dict(self) -> dict[str, Any]:
        """Plain dict (for ``--json`` output)."""
        return asdict(self)


def has_errors(issues: list[Issue]) -> bool:
    """True if any issue has severity ``error``."""
    return any(i.severity == "error" for i in issues)
