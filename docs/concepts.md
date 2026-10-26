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

# Concepts

## Two layers: syntax and deck

pynumgeo reads an input file in two steps.

1. **Syntax** ([`pynumgeo.io.lexer`](api/io.md), [`pynumgeo.io.syntax`](api/io.md)): numgeo's
   preprocessing is emulated line by line, and the lines are grouped into keyword blocks
   (`KeywordBlock`: keyword, options, data lines, child blocks, source position).
2. **Deck** ([`pynumgeo.deck`](api/deck.md), [`pynumgeo.mesh`](api/mesh.md)): the blocks are
   interpreted as numgeo interprets them: a `Mesh` (numpy arrays of coordinates and connectivity, node
   and element sets, surfaces), materials, sections, amplitudes and steps. Keywords pynumgeo has no
   typed model for stay generic `Keyword` objects (keyword, options, data, children), so nothing is
   lost.

Decks compare by meaning: `deck_a == deck_b` ignores source positions, the spelling case of keywords
and options, and `1` versus `1.0`.

```python
import pynumgeo as ng

a = ng.parse_text("*Node\n1, 0., 0.\n2, 1., 0.\n*Element, type=u2-truss\n1, 1, 2\n").deck
b = ng.parse_text("*NODE\n1,0.0,0.0\n2,1,0\n*ELEMENT,TYPE=U2-TRUSS\n1,1,2\n").deck
print(a == b)
```

```text
True
```

## The reader reads like numgeo

numgeo copies the input into an internal file before it parses it
(`src/input/input_create_internal_input_.f90`). pynumgeo emulates every rule: lines are read into 256
characters, `**` starts a comment, every line containing the word `INCLUDE` is an include, ASCII letters
are upper-cased, blanks are removed (except between `$` signs), a trailing comma is dropped, and the
line `*AMPLITUDE,NAME=DEFAULT,TYPE=RAMP` is prepended.

numgeo finds options by searching for words inside the option text. A set named `FindFix` therefore
switches on the `find` option, and numgeo reads the members as the coordinates of a point. The reader
does the same and reports it:

```python
text = "*Node\n1, 0., 0.\n2, 1., 0.\n*Nset, nset=FindFix\n1, 2\n"
result = ng.parse_text(text, name="model.inp")
print(result.issues[0])
print(result.deck.mesh.nset("FindFix").kind)
```

```text
NG-READ-NAME-001 warning  model.inp:4  option 'nset=FindFix' is also read as find (numgeo matches option words inside the text)
find
```

Reader issues have ids `NG-READ-*`; `parse` returns them with the deck, `read` raises `ReadError` if
one of them is an error.

## Node and element labels

numgeo uses the members of node sets as positions in its node array. Node labels must therefore be
1..N in the order of definition; with other labels numgeo computes wrong results or stops. The validator
reports such meshes (`NG-MESH-*`), and `Mesh.renumbered()` returns a copy numbered 1..N together with
the maps from the old labels.

## Writing: normal case and one canonical form

The writer emits one canonical form per construct, in normal case: keywords in sentence case as in the
numgeo manual (`*Initial conditions`, `*Solid section`), option keys and words in lower case, names in
the spelling of the deck (`*Nset, nset=Top`). numgeo upper-cases every line, so the spelling does not
change the meaning. Reals are written with Python's shortest exact representation (`repr`), so a value
survives writing and reading unchanged. No line is longer than 256 characters; element records that
would be longer are split over two lines, as numgeo allows. The same deck gives the same bytes on every
platform.

Parts and instances are read into one flat model; their sets are named `<instance>.<set>`, as numgeo
names them internally. The writer refuses names that numgeo would read as options (`WriteError`); this
happens for such sets when the instance name contains an option word (`SoilInstance.All` contains
`instance`). `deck.safe_names()` renames every such name together with all references and returns the
mapping (`{"SoilInstance.All": "SoilInst.All"}`); numgeo then names its print files after the new names.

## Validation

`ng.validate(deck)` runs every registered rule and returns `Issue` objects, sorted errors first:

| field | meaning |
|---|---|
| `id` | stable rule id, `NG-<AREA>-<nnn>` (`MESH`, `NAME`, `REF`, `MAT`, `STEP`, `BC`, `LOAD`, `IC`, `CONT`, `OUT`, `AMPL`, `KW`) |
| `severity` | `error` (numgeo stops, or reads the input differently from what it says), `warning`, `info` |
| `message` | what is wrong, in the words of the input |
| `location` | `file:line` when the deck was read from a file |
| `source` | the numgeo source lines the rule mirrors |

```python
from pynumgeo.validation import rules

r = {x.id: x for x in rules()}["NG-STEP-128"]
print(r.severity, "|", r.title, "|", r.source)
```

```text
warning | a step should have a *Boundary | src/input/read_step_.f90:3192,3202; src/soe/soe_apply_boundary_conditions_.f90:92
```

The validator targets a numgeo build. The default, `BuildProfile.full()`, is the current developer
build; `BuildProfile.public_build()` is a build with `public_version = .true.`, which rejects the
non-public constitutive and contact models.

## Running numgeo and judging the outcome

numgeo returns exit status 0 also after an error. `ng.run` therefore decides the outcome from the report
files: the end markers of the `.log`, the step blocks of the `.sta` (was every step completed?), the
error and warning messages of `.log`, `.msg` and the console. Each solver message is matched against
the message inventory of the catalogue, so `RunResult.errors` names the source line that wrote it.

| status | meaning |
|---|---|
| `SUCCESS` | end marker written, no error, every step reached its end time |
| `FAILED` | numgeo reported an error (or stopped without its end marker) |
| `INCOMPLETE` | no error, but a step did not reach its end time (for example `inc=` was used up, which numgeo does not report) or was not run |
| `TIMEOUT` | the time limit was reached and the process was stopped |
| `CRASHED` | the process died abnormally (signal, Fortran runtime error) without a numgeo error |
| `INPUT_ACCEPTED` | `check_only=True`: numgeo read the input and built the model |

## Results

`ng.open_results(workdir, job)` gives access to the VTK frames (`frames()`, with point and cell data as
numpy arrays), the print files (`print_series()`, one time series per set member) and the `.sta` rows.
Column names of print files are built in numgeo's data order; where numgeo's header disagrees with the
data, the reader says so in `issues`.

## The catalogue

Everything numgeo-specific - keywords and their options and data lines, element types, constitutive
models and their parameters, output variables, messages, units - comes from the catalogue
([`pynumgeo.catalogue`](api/catalogue.md)). It is generated from the numgeo source; every entry
records the source lines it comes from, and an anchor (a hash of the source line) shows when numgeo has
changed. `describe()` renders an entry
for people and agents, together with the page of the numgeo manual where there is one.

## Units

numgeo has no unit system of its own; the values must be consistent. pynumgeo's examples and defaults
use metres, kilonewtons, kilopascals, tonnes and seconds (m, kN, kPa, t, s). 38 constants inside numgeo
presuppose a unit system (for example the bulk modulus of the solid grains in some saturated u-p
elements, `15e6`, i.e. 15 GPa in kPa); the catalogue lists them with their source lines under `units`.
