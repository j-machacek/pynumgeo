# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#                                                pynumgeo
#                              Python API for the finite element code numgeo
#                                     Copyright (C) 2026 Jan Machacek
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#
# Author: Jan Machacek (with help of Claude Opus 5.5)
#
# pynumgeo writes, checks and runs numgeo input files and reads numgeo results. It follows the
# development of numgeo: new developments in the numgeo source code are taken over into the API, and a
# CI pipeline tests every change.
#
# License: BSD-3-Clause, see LICENSE.
#
# History
# 03.11.2026, J. Machacek - Initial version (with help of Claude Opus 5.5)
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""The bundled reference pages (``catalogue/data/docs``): index and the names the public catalogue omits."""

from __future__ import annotations

import hashlib
import json
import re
from importlib import resources

from pynumgeo import catalogue as cat

_DATA = resources.files("pynumgeo.catalogue").joinpath("data")
# private-name hashes that the bundle contains as part of a public name (title of hardening_soil_MN.md)
_ACCEPTED = frozenset({"d06d3ec798ac8a68b47a"})


def _pages() -> dict[str, str]:
    root = _DATA.joinpath("docs")
    out: dict[str, str] = {}

    def walk(node, prefix: str) -> None:
        for child in node.iterdir():
            if child.is_dir():
                walk(child, f"{prefix}{child.name}/")
            elif child.name.endswith(".md"):
                out[f"{prefix}{child.name}"] = child.read_text(encoding="utf-8")

    walk(root, "")
    return out


def test_index_lists_every_page_with_its_title():
    pages = _pages()
    index = json.loads(_DATA.joinpath("docs_index.json").read_text(encoding="utf-8"))
    assert sorted(index) == sorted(pages)
    for rel, text in pages.items():
        heading = next((m.group(1).strip() for m in (re.match(r"^# (.+)$", ln) for ln in text.splitlines()) if m), rel)
        assert index[rel] == heading, rel


def test_no_private_names():
    c = cat.load()
    public = {cat.normalise_name(m.name) for m in c.material_models}
    public |= {cat.normalise_name(e.name) for e in c.element_types}
    public |= {cat.normalise_name(k.keyword.lstrip("*")) for k in c.keywords}
    found = set()
    for rel, text in _pages().items():
        for token in set(re.findall(r"[\w-]+", text)):
            for v in {token, token.replace("_", "-"), token.replace("-", "_")}:
                h = hashlib.sha256(cat.normalise_name(v).encode()).hexdigest()[:20]
                if c.is_private_name(v) and cat.normalise_name(v) not in public and h not in _ACCEPTED:
                    found.add((rel, h))
    assert not found
