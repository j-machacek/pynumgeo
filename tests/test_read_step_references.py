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
# 20.11.2026, J. Machacek - Initial version
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""References to ``src/input/read_step_.f90``: one line numbering, that of numgeo-src 1f48283.

* the messages of the file have distinct ids, are listed in the order of their lines and lead to the rules that mirror
  their routine, not to rules on other routines;
* every reference ``{file, line, anchor}`` of the catalogue and every message of the file matches the source
  (``NUMGEO_SRC``).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from pynumgeo import catalogue as cat
from pynumgeo.solver.messages import rules_for_source

FILE = "src/input/read_step_.f90"


def _messages() -> list[dict]:
    return [m for m in cat.load().messages() if m["file"] == FILE]


def _references() -> list[dict]:
    """Every ``{file, line, anchor}`` of the catalogue that cites the file."""
    found: list[dict] = []

    def collect(node) -> None:
        if isinstance(node, dict):
            if {"anchor", "file", "line"} <= set(node) and node["file"] == FILE:
                found.append(node)
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    collect(cat.load().data)
    return found


def test_message_ids_are_distinct_and_ordered():
    messages = _messages()
    assert len(messages) == 189
    lines = [m["line"] for m in messages]
    assert lines == sorted(set(lines))
    assert all(m["id"] == f"{FILE}:{m['line']}" for m in messages)


def test_messages_lead_to_the_rules_of_their_routine():
    """Each rule cites the lines of the routine it mirrors: a message of another routine must not lie in them."""
    rules: dict[str, set[tuple[str, ...]]] = {}
    for m in _messages():
        rules.setdefault(m["routine"], set()).add(rules_for_source(m["file"], m["line"]))
    assert rules["read_pfem_remeshing_options"] == rules["check_pfem_remeshing_definition"] == {("NG-STEP-134",)}
    assert rules["read_reduction_options"] == {("NG-STEP-132",)}
    assert rules["read_nonlocal_options"] == rules["read_direct_solver_options"] == {()}
    assert rules["read_submodel_options"] == {(), ("NG-STEP-115",)}


@pytest.mark.skipif(not os.environ.get("NUMGEO_SRC"), reason="set NUMGEO_SRC")
@pytest.mark.source
def test_references_match_the_source():
    """All entries of read_step_.f90 cite lines of numgeo-src 1f48283: their anchors must match it."""
    source = (Path(os.environ["NUMGEO_SRC"]) / FILE).read_text(encoding="latin-1").splitlines()
    references, messages = _references(), _messages()
    assert len(references) == 304
    for e in references + messages:
        assert hashlib.sha256(source[e["line"] - 1].strip().encode()).hexdigest()[:16] == e["anchor"], e
