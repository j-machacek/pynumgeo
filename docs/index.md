<!--
=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
                                               pynumgeo
                             Python API for the finite element code numgeo
                                    Copyright (C) 2026 Jan Machacek
=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~

Author: Jan Machacek

pynumgeo writes, checks and runs numgeo input files and reads numgeo results. It follows the
development of numgeo: new developments in the numgeo source code are taken over into the API, and a
CI pipeline tests every change.

License: BSD-3-Clause, see LICENSE.
=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
-->

# pynumgeo

pynumgeo is the Python API of the finite element code [numgeo](https://www.numgeo.de). It reads and
writes numgeo input files, checks them against what the solver accepts, runs the solver and reads its
results. It runs headless on Windows and Linux and serves the numgeo FreeCAD workbench, scripts,
notebooks and LLM agents.

```python
import pynumgeo as ng

deck = ng.read("model.inp")              # numgeo input -> Deck (mesh, materials, steps, ...)
issues = ng.validate(deck)               # what numgeo would reject or read differently
ng.write(deck, "job/model.inp")          # normal-case, deterministic numgeo input
res = ng.run(deck, "job", job="model")   # run numgeo, judge the outcome from its report files
frames = ng.open_results("job", "model").frames()
```

## What it gives you

- **One object model of a numgeo input deck** ([`Deck`](api/deck.md)): mesh (numpy arrays), sets and
  surfaces, materials, sections, amplitudes, steps. Keywords without a typed model are kept as generic
  [`Keyword`](api/deck.md) objects, so nothing is lost.
- **A reader that reads like numgeo.** It emulates numgeo's preprocessing (includes, comments, blanks,
  upper-casing) and its option matching, including the quirks, and reports every place where an input
  relies on one ([concepts](concepts.md#the-reader-reads-like-numgeo)).
- **A writer that writes safe, readable input**: normal case (`*Step, name=Load`), one canonical form
  per construct, byte-identical output for the same deck.
- **A validator** with 165 rules, each with a stable id (`NG-<AREA>-<nnn>`) and the solver source it
  mirrors.
- **A runner** that judges a run from numgeo's `.log`, `.sta`, `.msg` and console output (numgeo's exit
  status is 0 also after an error) and classifies the solver's messages.
- **Result readers** for the VTK output (`.pvd`/`.vtm`/`.vtu`), print files and the `.sta` file.
- **A catalogue** of keywords, options, element types, constitutive models and messages, generated
  from the numgeo source, with `describe()` for humans and agents.
- **A command line** (`pynumgeo validate|run|info|roundtrip|catalogue`) with `--json` output.

## Ground truth

The numgeo Fortran source is the ground truth. Everything numgeo-specific in pynumgeo comes from the
catalogue, which is generated from the source and records where each fact comes from. Where the
documentation and the source differ, pynumgeo follows the source.

## Versions

pynumgeo follows the numgeo release it is built for: version `2026.2.x` is built against the current
numgeo developer source and is released with the next numgeo release. `pynumgeo --version` names the
numgeo build and source commit it was made for; every input file it writes carries the same in its
header.

## Status

Pre-release.
