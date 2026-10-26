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
"""Command line: ``pynumgeo validate|run|info|roundtrip|catalogue``.

Every command has ``--json`` for machine-readable output (agents, CI); each JSON report carries the
pynumgeo version and author under ``"pynumgeo"`` (:func:`pynumgeo._provenance.provenance`). ``pynumgeo
--version`` prints the version. Exit codes: 0 = fine, 1 = issues found or the run failed, 2 = usage error.

Examples::

    pynumgeo validate model.inp            # reader + validator issues, exit 1 on errors
    pynumgeo run model.inp --workdir runs/m1 --ncpus 4
    pynumgeo run model.inp --check-only    # input accepted by numgeo?
    pynumgeo info "*Initial conditions"     # keyword reference (source facts + docs page)
    pynumgeo info material:mohr-coulomb
    pynumgeo roundtrip model.inp -o model-normal-case.inp
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

__all__ = ["main"]


def _report(**fields: Any) -> dict[str, Any]:
    """A JSON report: the provenance of pynumgeo first, then ``fields``."""
    from pynumgeo._provenance import provenance

    return {"pynumgeo": provenance(), **fields}


def _print(obj: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, indent=1, default=str))
    elif isinstance(obj, str):
        print(obj)
    else:
        print(json.dumps(obj, indent=1, default=str))


def _cmd_validate(a: argparse.Namespace) -> int:
    from pynumgeo.io.reader import parse
    from pynumgeo.validation import BuildProfile, validate

    res = parse(a.input)
    profile = BuildProfile.public_build() if a.profile == "public" else BuildProfile.full()
    order = {"error": 0, "warning": 1, "info": 2}
    issues = sorted(res.issues + validate(res.deck, profile=profile), key=lambda i: order.get(i.severity, 3))
    errors = sum(i.severity == "error" for i in issues)
    if a.json:
        _print(_report(input=a.input, errors=errors, issues=[i.as_dict() for i in issues]), True)
    else:
        for i in issues:
            if a.all or i.severity != "info":
                print(i)
        print(f"{errors} error(s), {sum(i.severity == 'warning' for i in issues)} warning(s)")
    return 1 if errors else 0


def _cmd_run(a: argparse.Namespace) -> int:
    from pynumgeo.solver import run

    workdir = a.workdir or str(Path(a.input).with_suffix("")) + "-run"
    res = run(
        a.input,
        workdir,
        job=a.job,
        executable=a.exe,
        ncpus=a.ncpus,
        timeout=a.timeout,
        check_only=a.check_only,
        on_line=None if a.json or a.quiet else print,
    )
    if a.json:
        _print(
            _report(
                status=res.status.value,
                reason=res.reason,
                workdir=str(res.workdir),
                exit_code=res.exit_code,
                duration=res.duration,
                steps=[s.__dict__ for s in res.steps],
                errors=[m.text for m in res.messages if m.severity == "error"],
            ),
            True,
        )
    else:
        print(f"{res.status.value}: {res.reason}")
    return 0 if res.ok else 1


def _cmd_info(a: argparse.Namespace) -> int:
    from pynumgeo import catalogue

    try:
        text = catalogue.describe(a.name, with_docs=not a.no_docs)
    except KeyError as e:
        print(str(e).strip("\"'"), file=sys.stderr)
        return 1
    if a.json:
        cat = catalogue.load()
        n = a.name
        if n.lower().startswith("material:"):
            entries = [cat.material_model(n.split(":", 1)[1]).raw]
        elif n.lower().startswith("element:"):
            entries = [cat.element_type(n.split(":", 1)[1]).raw]
        else:
            entries = [e.raw for e in cat.keyword_entries(n)]
        _print(_report(name=n, entries=entries), True)
    else:
        print(text)
    return 0


def _cmd_roundtrip(a: argparse.Namespace) -> int:
    from pynumgeo.io.reader import parse, parse_text
    from pynumgeo.io.writer import write_text

    res = parse(a.input)
    text = write_text(res.deck)
    again = parse_text(text, name=a.output or "<written>")
    same = again.deck == res.deck
    if a.output:
        Path(a.output).write_text(text, encoding="utf-8", newline="\n")
    report = _report(
        input=a.input,
        equal_after_reading_back=same,
        read_issues=[i.as_dict() for i in res.issues],
        output=a.output,
    )
    if a.json:
        _print(report, True)
    else:
        if not a.output:
            sys.stdout.write(text)
        print(f"read back equal: {same}", file=sys.stderr)
    return 0 if same else 1


def _cmd_catalogue(a: argparse.Namespace) -> int:
    from pynumgeo import catalogue
    from pynumgeo._version import NUMGEO_VERSION

    cat = catalogue.load()
    info = _report(
        numgeo_version=NUMGEO_VERSION,
        source_commit=cat.source_commit,
        docs_commit=cat.docs_commit,
        keywords=len(cat.keywords),
        element_types=len(cat.element_types),
        material_models=len(cat.material_models),
        messages=len(cat.messages()),
    )
    if a.list:
        info["keyword_list"] = sorted({k.display for k in cat.keywords})
        info["material_model_list"] = sorted(m.name.lower() for m in cat.material_models)
        info["element_type_list"] = sorted(e.name.lower() for e in cat.element_types)
    _print(info, a.json or True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """The argument parser (exposed for the documentation)."""
    from pynumgeo._provenance import AUTHOR
    from pynumgeo._version import NUMGEO_SOURCE_COMMIT, NUMGEO_VERSION, __version__

    p = argparse.ArgumentParser(prog="pynumgeo", description="Python API for the finite element code numgeo")
    p.add_argument(
        "--version",
        action="version",
        version=f"pynumgeo {__version__} by {AUTHOR} ({NUMGEO_VERSION}, numgeo source {NUMGEO_SOURCE_COMMIT[:8]})",
    )
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="read an input file and report everything numgeo would reject")
    v.add_argument("input")
    v.add_argument("--profile", choices=["full", "public"], default="full", help="numgeo build (default: full)")
    v.add_argument("--all", action="store_true", help="also show infos")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=_cmd_validate)

    r = sub.add_parser("run", help="run numgeo on an input file and judge the outcome")
    r.add_argument("input")
    r.add_argument("--workdir", help="job folder (default: <input>-run)")
    r.add_argument("--job", default="job", help="job name (inp=/out=), default 'job'")
    r.add_argument("--exe", help="numgeo executable (default: NUMGEO_EXE, then PATH)")
    r.add_argument("--ncpus", type=int, default=1)
    r.add_argument("--timeout", type=float)
    r.add_argument("--check-only", action="store_true", help="stop after numgeo's input phase")
    r.add_argument("--quiet", action="store_true", help="do not echo the console")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=_cmd_run)

    i = sub.add_parser("info", help="describe a keyword, material:<model> or element:<type>")
    i.add_argument("name")
    i.add_argument("--no-docs", action="store_true", help="without the bundled documentation page")
    i.add_argument("--json", action="store_true")
    i.set_defaults(func=_cmd_info)

    t = sub.add_parser("roundtrip", help="read and write an input file (normal-case, deterministic)")
    t.add_argument("input")
    t.add_argument("-o", "--output", help="write the result here instead of stdout")
    t.add_argument("--json", action="store_true")
    t.set_defaults(func=_cmd_roundtrip)

    c = sub.add_parser("catalogue", help="catalogue summary (source commit, counts)")
    c.add_argument("--list", action="store_true", help="also list keywords, models and element types")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=_cmd_catalogue)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the ``pynumgeo`` command."""
    p = build_parser()
    a = p.parse_args(argv)
    try:
        return int(a.func(a))
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
