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
# 13.11.2026, J. Machacek - Initial version
# 14.11.2026, J. Machacek - Data and summary of the numgeo-src of 14.11.2026 (plateau at the end, first plateau)
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""Strength reduction with arc-length control (``*Reduction, arc-length``) and strength reduction of embedded
interfaces (``*Embedded region, interaction, ..., reduction``), uncommitted numgeo-src of 13.11.2026: catalogue,
checks (read_reduction_options, arc_length_initialize, read_embedded_region), messages, ``.sta`` and runner.

The files in ``data/arc-length-reduction`` were written by numgeo (``pruska-no-arc``: 13.11.2026, the others:
14.11.2026, build db7db25b) and shortened: steps before the reduction step with fewer rows, time statistics cut,
``.msg`` reduced to its step headers. ``pruska`` (plateau at the end of the step) and ``wall-int`` (first plateau,
end after consecutive rejections, notes of contact and embedded interfaces) keep only some rows of the reduction
step; ``byun`` (first plateau, rejected arc-length increments) and ``pruska-no-arc`` (the model of ``pruska``
without arc-length control) keep all of them together with the history file numgeo wrote for the step.
"""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
from pathlib import Path

import pytest

import pynumgeo as ng
from conftest import DATA, small_deck
from pynumgeo import catalogue as cat
from pynumgeo.deck import Keyword
from pynumgeo.results import open_results, read_arc_length_summaries, read_sta
from pynumgeo.solver import assess
from pynumgeo.solver.logs import parse_sta, read_lines
from pynumgeo.solver.messages import classify, rules_for_source

ARC = DATA / "arc-length-reduction"
ARC_RULES = ("NG-STEP-132", "NG-STEP-133", "NG-KW-011", "NG-KW-014")


def _reduction_deck(*options, items=(), nocutback: bool = False) -> ng.Deck:
    """small_deck with its step turned into a strength reduction step (*Reduction with ``options``)."""
    d = small_deck()
    st = d.steps[0]
    st.procedure = Keyword.make("*Reduction", options=list(options), data=[[1.0, 0.01, 0.05, 1.0e-4]])
    st.inc = 1000
    st.nocutback = nocutback
    for kw in items:
        st.items.append(kw)
    return d


def _found(deck: ng.Deck, *rules: str) -> list[ng.Issue]:
    return [i for i in ng.validate(deck) if i.id in rules]


# --------------------------------------------------------------------------------------------------------- catalogue
def test_catalogue_reduction_options():
    spec = cat.keyword("*Reduction")
    opts = {o.name: o for o in spec.options}
    assert list(opts) == [
        "ARC-LENGTH", "ARC-INCREMENTS", "MAX-DISPLACEMENT", "PLATEAU-TOLERANCE", "PLATEAU-INCREMENTS", "PERTURBATION",
    ]  # fmt: skip
    assert opts["ARC-LENGTH"].value_type == "flag" and not any(o.required for o in opts.values())
    assert [(o.value_type, o.default) for o in list(opts.values())[1:]] == [
        ("int", 100), ("real", None), ("real", 0.002), ("int", 5), ("real", 0.001),
    ]  # fmt: skip
    for o in opts.values():
        assert o.source is not None and o.source["routine"] == "read_reduction_options"
        assert "uncommitted numgeo-src of 14.11.2026" in o.notes
    assert "arc-length" in cat.describe("*Reduction", with_docs=False)
    page = cat.load().doc_page(spec.doc)
    assert page is not None and "## Arc-length control" in page and "`plateau-increments=<N>`" in page
    proc = next(p for p in cat.load().section("step", "step_procedures") if p["keyword"] == "*REDUCTION")
    assert proc["arc_length"]["defaults"]["ARC-INCREMENTS"] == 100


def test_catalogue_embedded_reduction_and_output():
    variant = next(
        v for v in cat.load().section("interactions", "embedded_region_types") if v["variant"] == "INTERACTION"
    )
    red = next(o for o in variant["options"] if o["name"] == "REDUCTION")
    assert "substring 'REDUCTION'" in red["match"] and variant["defaults"]["reduction"] is False
    page = cat.load().doc_page("docs/reference/embedded-regions/interaction.md")
    assert page is not None and "## Strength reduction of the interface" in page and "[, reduction]" in page
    files = cat.load().section("output", "result_files")
    history = next(f for f in files if "strength-reduction-history" in f["name_pattern"])
    assert "'FoS,max_disp,energy,inc,control'" in history["format"]
    patterns = cat.load().section("runtime", "log_format")["patterns"]
    assert cat.load().section("runtime", "counts")["log_patterns"] == len(patterns)
    names = [p["name"] for p in patterns]
    assert names.index("increment_line") + 1 == names.index("increment_line_arc_length")


@pytest.mark.skipif(not os.environ.get("NUMGEO_SRC"), reason="set NUMGEO_SRC")
@pytest.mark.source
def test_catalogue_anchors_match_the_source():
    """The new entries cite lines of the numgeo-src working tree: their anchors must still match."""
    root = Path(os.environ["NUMGEO_SRC"])
    entries = [o.source for o in cat.keyword("*Reduction").options]
    variant = next(
        v for v in cat.load().section("interactions", "embedded_region_types") if v["variant"] == "INTERACTION"
    )
    entries += [o["source"] for o in variant["options"]]
    entries += [
        m for m in cat.load().messages() if "arc_length" in m["file"] or m["routine"] == "read_reduction_options"
    ]
    for e in entries:
        line = (root / e["file"]).read_text(encoding="latin-1").splitlines()[e["line"] - 1]
        assert hashlib.sha256(line.strip().encode()).hexdigest()[:16] == e["anchor"], e


# ------------------------------------------------------------------------------------------------- *Reduction options
def test_arc_length_options_are_accepted():
    opts = ("arc-length", "arc-increments=50", "max-displacement=0.5", "plateau-tolerance=1e-3", "plateau-increments=3",
            "perturbation=1d-3")  # fmt: skip
    assert _found(_reduction_deck(*opts), *ARC_RULES) == []
    assert _found(_reduction_deck("arc-length"), *ARC_RULES) == []


@pytest.mark.parametrize(
    "option, text",
    [
        ("plateau-increments=1", "plateau-increments=1 must be an integer of at least 2; numgeo stops"),
        ("plateau-increments=1.5", "plateau-increments=1.5 must be an integer of at least 2; numgeo stops"),
        # numgeo accepts digits only for the integer options
        ("plateau-increments=2.9", "plateau-increments=2.9 must be an integer of at least 2; numgeo stops"),
        ("plateau-increments=+3", "plateau-increments=+3 must be an integer of at least 2; numgeo stops"),
        ("arc-increments=1e2", "arc-increments=1e2 must be a positive integer; numgeo stops"),
        ("arc-increments=abc", "arc-increments=abc must be a positive integer; numgeo stops"),
        ("arc-increments=0", "arc-increments=0 must be a positive integer; numgeo stops"),
        ("arc-increments=0.5", "arc-increments=0.5 must be a positive integer; numgeo stops"),
        ("max-displacement=-0.5", "max-displacement=-0.5 must be a positive number"),
        ("max-displacement=large", "max-displacement=large must be a positive number"),
        ("plateau-tolerance=0.0", "plateau-tolerance=0.0 must be a positive number"),
        ("perturbation=0", "perturbation=0 must be a positive number"),
        (
            "max-disp=0.5",
            "unknown option max-disp=0.5 (options: max-displacement=, plateau-tolerance=, "
            "plateau-increments=, arc-increments=, perturbation=)",
        ),
        ("fast", "the option fast needs a value (fast=...)"),
        ("plateau-tolerance=", "the option plateau-tolerance needs a value"),
    ],
)
def test_arc_length_option_errors(option, text):
    found = _found(_reduction_deck("arc-length", option), *ARC_RULES)
    assert len(found) == 1 and found[0].id == "NG-STEP-132" and found[0].severity == "error"
    assert found[0].message.startswith("step Load: *Reduction, arc-length: ") and text in found[0].message


def test_options_without_arc_length_are_ignored():
    # numgeo evaluates the options only together with the exact token arc-length (read_reduction_options)
    found = _found(_reduction_deck("plateau-increments=1"), *ARC_RULES)
    assert [(i.id, i.severity) for i in found] == [("NG-KW-011", "warning")]
    assert found[0].message == (
        "step Load: option 'plateau-increments=1' of *Reduction is ignored by numgeo (src/input/read_step_.f90:357-359)"
    )
    found = _found(_reduction_deck("arc-length=yes", "arc-increments=0"), *ARC_RULES)
    assert [i.id for i in found] == ["NG-KW-011", "NG-KW-011"]
    assert _found(_reduction_deck(), *ARC_RULES) == []


# ------------------------------------------------------------------------------------- *Reduction, arc-length set-up
def _solver(*options) -> Keyword:
    return Keyword.make("*Solver", options=list(options))


@pytest.mark.parametrize(
    "items, nocutback, texts",
    [
        ((_solver("gmres"),), False, ["needs the direct solver Pardiso or MUMPS", "the solver of the step is gmres"]),
        ((_solver("simple"),), False, ["the solver of the step is simple"]),  # one element: SIMPLE is kept
        ((_solver("mumps", "iterative"),), False, ["*Solver, mumps, iterative (reuse of the factorization)"]),
        ((Keyword.make("*Accelerator", options=["type=anderson", "default"]),), False, ["type=anderson"]),
        ((), True, ["nocutback in the *Step line is not supported"]),
    ],
)
def test_arc_length_setup_errors(items, nocutback, texts):
    found = _found(_reduction_deck("arc-length", items=items, nocutback=nocutback), "NG-STEP-133")
    assert len(found) == 1 and found[0].severity == "error"
    assert found[0].message.startswith("step Load: *Reduction, arc-length ")
    for text in texts:
        assert text in found[0].message


@pytest.mark.parametrize(
    "items",
    [
        (),
        (_solver("pardiso"),),
        (_solver("mumps", "device=cpu"),),
        (_solver("pardiso", "iterative", "direct"),),  # the last strategy counts
        (_solver("unknown-solver"),),  # numgeo keeps Pardiso (NG-STEP-122 reports the name)
        (Keyword.make("*Accelerator", options=["type=linear", "default"]),),
    ],
)
def test_arc_length_setup_accepted(items):
    assert _found(_reduction_deck("arc-length", items=items), "NG-STEP-133") == []


def test_setup_is_not_checked_without_arc_length():
    items = (_solver("gmres"), Keyword.make("*Accelerator", options=["type=anderson", "default"]))
    assert _found(_reduction_deck(items=items, nocutback=True), "NG-STEP-132", "NG-STEP-133") == []


def test_arc_length_written_and_read_back():
    d = _reduction_deck("arc-length", ("arc-increments", 50), ("plateau-tolerance", 0.001))
    text = ng.write_text(d)
    assert "*Reduction, arc-length, arc-increments=50, plateau-tolerance=0.001\n1.0, 0.01, 0.05, 0.0001\n" in text
    back = ng.parse_text(text).deck
    assert back.steps[0].procedure == d.steps[0].procedure
    assert _found(back, *ARC_RULES) == []


# ------------------------------------------------------------------------------- *Embedded region, interaction
def _embedded(*options) -> ng.Deck:
    d = small_deck()
    d.keywords.append(
        Keyword.make(
            "*Embedded region",
            options=["interaction", *options],
            data=[["Soil", "Soil", 4.0e4, 1.0e6, 0.0, 28.0, 2.0]],
        )
    )
    return d


def test_embedded_reduction_is_an_option():
    for options in (("type=Mohr-Coulomb", "section=sheet", "reduction"), ("reduction", "type=Mohr-Coulomb")):
        assert _found(_embedded(*options), "NG-CONT-118", "NG-CONT-119") == []


@pytest.mark.parametrize("option", ["reduction=no", "noreduction", "name=reduction-layer"])
def test_embedded_words_with_reduction(option):
    found = _found(_embedded("type=Mohr-Coulomb", option), "NG-CONT-119")
    assert len(found) == 1 and found[0].severity == "error"
    assert f"option {option.lower()!r} contains 'reduction', which numgeo reads as the option reduction" in (
        found[0].message
    )


def test_embedded_other_options_unchanged():
    assert [i.message for i in _found(_embedded("type=Mohr-Coulomb", "fast"), "NG-CONT-119")] == [
        "*Embedded region, interaction: unknown option 'fast' (numgeo ignores it)"
    ]


def test_embedded_reduction_written_and_read_back():
    d = _embedded("type=Mohr-Coulomb", "section=sheet", "reduction")
    text = ng.write_text(d)
    assert "*Embedded region, interaction, type=mohr-coulomb, section=sheet, reduction\n" in text
    back = ng.parse_text(text).deck
    assert back.keywords[-1] == d.keywords[-1]


# --------------------------------------------------------------------------------------------------------- messages
@pytest.mark.parametrize(
    "text, rule",
    [
        (
            "The option FAST of the *REDUCTION, ARC-LENGTH command in step SAFETY needs a value (FAST=...).",
            "NG-STEP-132",
        ),
        (
            "PLATEAU-INCREMENTS of the *REDUCTION, ARC-LENGTH command in step SAFETY has to be an integer of at "
            "least 2: 1",
            "NG-STEP-132",
        ),
        (
            "Unknown option MAX-DISP of the *REDUCTION, ARC-LENGTH command in step SAFETY. Options: MAX-DISPLACEMENT=, "
            "PLATEAU-TOLERANCE=, PLATEAU-INCREMENTS=, ARC-INCREMENTS=, PERTURBATION=",
            "NG-STEP-132",
        ),
        (
            "The arc-length control of the strength reduction (*Reduction, arc-length) in step SAFETY needs the direct "
            "solver Pardiso or MUMPS (*Solver, Pardiso | MUMPS). The solver of the step is GMRES.",
            "NG-STEP-133",
        ),
        (
            "The arc-length control of the strength reduction (*Reduction, arc-length) in step SAFETY rejects and "
            "repeats increments; NOCUTBACK in the *Step command is not supported.",
            "NG-STEP-133",
        ),
    ],
)
def test_numgeo_messages(text, rule):
    m = classify(text, "error")
    assert m is not None and m.terminates
    assert rule in rules_for_source(m.file, m.line, m.candidates)


# -------------------------------------------------------------------------------------------------------------- .sta
def _history(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return [{k: v.strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def test_sta_rows_of_arc_length_control_match_the_history_file():
    rows = [r for r in read_sta(ARC / "byun/byun-2019.sta") if r.step_type == "REDUCTION"]
    assert len(rows) == 179 and {r.control for r in rows} == {"F", "A"}
    assert all(r.accepted is not None for r in rows)
    history = _history(ARC / "byun/step3-strength-reduction-history.csv")  # numgeo: the accepted increments
    accepted = [r for r in rows if r.accepted]
    assert [(r.increment, r.control) for r in accepted] == [(int(h["inc"]), h["control"]) for h in history]
    for r, h in zip(accepted, history, strict=True):
        assert r.fos == pytest.approx(float(h["FoS"]), rel=6e-4)  # g11.4 in the .sta
    s = read_arc_length_summaries(ARC / "byun/byun-2019.sta")[0]
    assert sum(r.control == "A" and r.accepted for r in rows) == s.accepted == 100
    assert sum(r.control == "A" and r.accepted is False for r in rows) == s.rejected == 68
    assert sum(r.rejection == "rejected (arc-length)" for r in rows) == 35
    first_a = next(r for r in rows if r.control == "A")
    assert first_a.increment == s.switch_increment == 10


def test_sta_summary_first_plateau():
    # the windows at the end of the step do not agree: the factor of safety is the first plateau
    (s,) = read_arc_length_summaries(ARC / "byun/byun-2019.sta")
    assert (s.engaged, s.switch_increment, s.switch_fos, s.accepted, s.rejected) == (True, 10, 1.4, 100, 68)
    assert (s.window_means, s.window_counts, s.windows_agree) == ((1.413374, 1.40657), (29, 44), False)
    assert (s.first_plateau_increment, s.first_plateau_u) == (96, 0.02307)
    assert (s.first_plateau_fos, s.first_plateau_min, s.first_plateau_max) == (1.413235, 1.396295, 1.424258)
    assert (s.fos_basis, s.fos, s.fos_min, s.fos_max) == ("first plateau", 1.413235, 1.396295, 1.424258)
    assert (s.peak_fos, s.peak_max_disp, s.peak_increment, s.peak_exceeds_plateau) == (1.424258, 0.010996, 61, True)


def test_sta_summary_plateau_at_the_end():
    (s,) = read_arc_length_summaries(ARC / "pruska/pruska-2009-case1.sta")
    assert (s.step, s.step_number) == ("STEP2", None)
    assert (s.plateau_tolerance, s.plateau_increments, s.arc_increments, s.perturbation) == (0.002, 5, 100, 0.001)
    assert s.max_displacement is None and s.notes == ()
    assert s.end_reason == "arc-increments = 100 arc-length increments accepted"
    assert (s.engaged, s.switch_increment, s.switch_fos, s.accepted, s.rejected) == (True, 9, 1.216667, 100, 0)
    assert (s.last_fos, s.last_max_disp) == (1.222219, 375.26)
    assert (s.window_u, s.window_means, s.window_counts, s.windows_agree) == (
        375.26, (1.2222, 1.222214), (10, 10), True,
    )  # fmt: skip
    assert (s.arc_mean, s.arc_min, s.arc_max) == (1.221417, 1.217224, 1.222219)
    assert (s.first_plateau_increment, s.first_plateau_u, s.first_plateau_fos) == (29, 1.5706, 1.219633)
    assert (s.first_plateau_min, s.first_plateau_max) == (1.217224, 1.22088)
    assert (s.fos_basis, s.fos, s.fos_min, s.fos_max) == ("plateau at the end", 1.222207, 1.22219, 1.222219)
    assert (s.peak_fos, s.peak_max_disp, s.peak_increment, s.peak_exceeds_plateau) == (1.222219, 375.26, 108, False)
    assert (s.fos_error, s.constraint_error) == (1.885e-09, 8.554e-15)
    rows = [r for r in read_sta(ARC / "pruska/pruska-2009-case1.sta") if r.step_type == "REDUCTION"]
    assert [(r.increment, r.control, r.accepted) for r in rows[7:12]] == [
        (8, "F", False), (8, "F", True), (9, "F", False), (9, "F", False), (9, "A", True),
    ]  # fmt: skip
    assert rows[-1].accepted is True  # arc-increments: the step ends after an accepted increment


def test_sta_end_after_consecutive_rejections():
    path = ARC / "wall-int/fos-interfaces-arc.sta"
    (s,) = read_arc_length_summaries(path)
    assert s.end_reason == "no convergence under arc-length control (10 consecutive rejections)"
    assert (s.arc_increments, s.accepted, s.rejected) == (200, 117, 91)
    assert len(s.notes) == 2 and s.notes[0].startswith("contact interactions with *Contact options, reduction")
    assert s.notes[1].startswith("embedded interfaces with *Embedded region, interaction, reduction enter the pseudo")
    assert (s.fos_basis, s.fos, s.first_plateau_increment) == ("first plateau", 2.192122, 75)
    rows = read_sta(path)
    assert [(r.increment, r.control, r.accepted) for r in rows[:5]] == [
        (26, "F", True), (27, "F", False), (27, "F", False), (27, "A", True), (28, "A", True),
    ]  # fmt: skip
    # numgeo's history file ends with increment 143; increment 144 is rejected 9 times, the 10th rejection ends the
    # step with the number maxinc + 1 = 1001
    assert [(r.increment, r.accepted) for r in rows[-11:]] == [(143, True)] + [(144, False)] * 9 + [(1001, False)]


def test_sta_summary_without_plateau(tmp_path):
    f = tmp_path / "job.sta"
    f.write_text(
        "-> Step = SAFETY\n   Type = REDUCTION\n"
        "        60        4         2.356         0.1822E-02      2.204        A\n"
        "   Strength reduction with arc-length control\n"
        "   End of the step: arc-increments = 1 arc-length increments accepted\n"
        "   The windows at the end of the step do not agree within plateau-tolerance (or hold fewer than "
        "plateau-increments increments).\n"
        "   Factor of safety (no plateau; mean over the windows at the end of the step):  2.442746  (min  2.356032, "
        "max  2.484315)\n"
        "   Peak FoS of the step:                     2.484315   (max. |u-u_0| =  7.7025E+00, increment 159)\n"
        "   Step sucessfully terminated, Date: 14.11.2026, Time: 00:10: 56\n"
    )
    (s,) = read_arc_length_summaries(f)
    assert (s.fos_basis, s.fos, s.fos_min, s.fos_max, s.windows_agree) == (
        "no plateau", 2.442746, 2.356032, 2.484315, False,
    )  # fmt: skip
    assert (s.first_plateau_increment, s.peak_exceeds_plateau, s.peak_increment) == (None, False, 159)


def test_sta_without_arc_length_is_unchanged():
    path = ARC / "pruska-no-arc/pruska-2009-case1.sta"
    rows = read_sta(path)
    reduction = [r for r in rows if r.step_type == "REDUCTION"]
    assert len(reduction) == 20 and all(r.control is None and r.accepted is None for r in reduction)
    assert reduction[-1].increment == 10001 and reduction[-1].rejection == "rejected (divergence)"
    assert all(r.accepted for r in rows if r.step_type == "STATIC")
    assert read_arc_length_summaries(path) == []
    assert list(_history(ARC / "pruska-no-arc/step2-strength-reduction-history.csv")[0]) == [
        "FoS",
        "max_disp",
        "energy",
    ]


_STA = """-> Step = SAFETY
   Type = REDUCTION
   -
   Arc-length control of the factor of safety (*Reduction, arc-length): plateau-tolerance = 2.00E-03, \
plateau-increments = 5, arc-increments = 100, perturbation = 1.00E-03
   Arc-length increments: Jacobian of the input factorized in every iteration, force tolerance of the step, at most \
60 iterations
   End of the step at the largest displacement max-displacement = 5.0000E-01
     Inc  Equil. Iters          FoS          dFoS   Max. |u-u_0|    Ctrl
        11       60         1.411         0.6850E-02     0.2700E-02    A  rejected (niter > maxiter)
        12       10         1.415         0.4123E-02     0.3007E-02    A
        13       60         1.413        -0.2463E-02     0.3322E-02    A  rejected (niter > maxiter)
{last}
   -------------------------------------------------------------------------
   Strength reduction with arc-length control
   End of the step: {reason}
   Arc-length control engaged at increment 10 (last converged FoS   1.400000); 2 increments accepted and 2 rejected \
under arc-length control
   -------------------------------------------------------------------------
   Step sucessfully terminated, Date: 14.11.2026, Time: 00:12: 21
"""


@pytest.mark.parametrize(
    "last, reason, third, expected",
    [
        ("        14        5         1.413         0.1E-02     0.5000      A",
         "largest displacement reached max-displacement", True, True),
        # consecutive rejections: the row before the last one (number maxinc + 1) is rejected as well
        ("     10001       60         1.413         0.1E-02     0.3322E-02    A  rejected (niter > maxiter)",
         "no convergence under arc-length control (10 consecutive rejections)", False, False),
        ("     10001       60         1.413         0.1E-02     0.3322E-02    A  rejected (niter > maxiter)",
         "maximum number of increments of the step (INC)", None, None),
        ("        14       60         1.413         0.1E-02     0.3400E-02    A  rejected (niter > maxiter)",
         "maximum number of increments of the step (INC)", True, None),
        ("        14        5         1.413         0.1E-02     0.3400E-02    A",
         "maximum number of increments of the step (INC)", True, True),
    ],
)  # fmt: skip
def test_sta_acceptance_of_the_last_rows(tmp_path, last, reason, third, expected):
    f = tmp_path / "job.sta"
    f.write_text(_STA.replace("{last}", last).replace("{reason}", reason))
    rows = read_sta(f)
    # niter label: accepted if the next row is the next increment
    assert [r.accepted for r in rows] == [True, True, third, expected]
    (s,) = read_arc_length_summaries(f)
    assert (s.engaged, s.switch_increment, s.switch_fos, s.max_displacement, s.end_reason, s.notes) == (
        True, 10, 1.4, 0.5, reason, (),
    )  # fmt: skip


def test_sta_arc_length_never_engaged(tmp_path):
    f = tmp_path / "job.sta"
    f.write_text(
        "-> Step = SAFETY\n   Type = REDUCTION\n"
        "         1        2         1.000         0.5000E-01     0.2750E-04    F\n"
        "         2        9         1.050         0.5000E-01     0.2533E+08    F  rejected (divergence)\n"
        "     10001        9         1.017         0.1667E-01     0.3841E+09    F  rejected (divergence)\n"
        "   Strength reduction with arc-length control\n"
        "   End of the step: FoS control: dFoS below dFoS_min\n"
        "   Arc-length control was never engaged (no rejected increment with a usable secant of the last converged "
        "increment); the step ran under FoS control only.\n"
        "   FoS of the last accepted increment:        1.000000   (max. |u-u_0| =  2.7501E-05)\n"
        "   Step sucessfully terminated, Date: 14.11.2026, Time: 00:12: 21\n"
    )
    assert [r.accepted for r in read_sta(f)] == [True, False, False]
    (s,) = read_arc_length_summaries(f)
    assert (s.engaged, s.accepted, s.last_fos, s.fos, s.fos_basis) == (False, None, 1.0, None, None)


def test_results_api_with_step_numbers(tmp_path):
    for name in ("byun-2019.sta", "byun-2019.msg"):
        shutil.copy(ARC / "byun" / name, tmp_path / name)
    res = open_results(tmp_path, "byun-2019")
    (s,) = res.arc_length_summaries()
    assert (s.step, s.step_number, s.fos_basis, s.fos, s.first_plateau_increment) == (
        "STEP3", 3, "first plateau", 1.413235, 96,
    )  # fmt: skip
    assert {r.step_number for r in res.sta() if r.control is not None} == {3}


# ------------------------------------------------------------------------------------------------------------ runner
def test_runner_reads_the_rows_and_the_summary(tmp_path):
    info = parse_sta(read_lines(ARC / "byun/byun-2019.sta"), "byun-2019.sta")
    step = info.steps[-1]
    assert step.type == "REDUCTION" and len(step.attempts) == 179
    assert {a.control for a in step.attempts} == {"F", "A"}
    assert [a.inc for a in step.accepted()] == [
        int(h["inc"]) for h in _history(ARC / "byun/step3-strength-reduction-history.csv")
    ]
    assert step.summary[0] == "Strength reduction with arc-length control" and step.terminated
    shutil.copy(ARC / "byun/byun-2019.sta", tmp_path / "job.sta")
    (tmp_path / "job.log").write_text("-> NUMGEO *START*\n-> PREPROCESSING *END* \n-> NUMGEO *END*\n")
    report = assess(tmp_path, "job", exit_code=0).steps[-1]
    assert (report.increments, report.cutbacks, report.completed) == (109, 70, True)
    assert report.note == (
        "strength reduction with arc-length control: end of the step: arc-increments = 100 arc-length increments "
        "accepted; factor of safety (first plateau, increment 96, u = 2.3070E-02; the windows at the end of the step "
        "do not agree): 1.413235 (min 1.396295, max 1.424258); last FoS = 1.404"
    )
    shutil.copy(ARC / "pruska/pruska-2009-case1.sta", tmp_path / "job.sta")
    assert "factor of safety (plateau at the end of the step, u = 3.7526E+02; mean over its windows): 1.222207" in (
        assess(tmp_path, "job", exit_code=0).steps[-1].note or ""
    )


def test_runner_note_without_arc_length_unchanged(tmp_path):
    shutil.copy(ARC / "pruska-no-arc/pruska-2009-case1.sta", tmp_path / "job.sta")
    (tmp_path / "job.log").write_text("-> NUMGEO *START*\n-> PREPROCESSING *END* \n-> NUMGEO *END*\n")
    report = assess(tmp_path, "job", exit_code=0).steps[-1]
    assert report.note == "strength reduction: last FoS = 1.222"  # as before 13.11.2026
    assert (report.increments, report.cutbacks) == (13, 7)
