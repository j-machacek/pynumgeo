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

# For agents

pynumgeo is meant to be used by LLM agents as well as by people. This page lists what an agent needs:
where the facts are, how to get machine-readable output, and a working loop.

## Facts come from the catalogue, not from memory

Do not guess numgeo keywords, options, parameter orders or defaults. Ask the catalogue:

```python
import pynumgeo as ng

spec = ng.catalogue.keyword("*Step")
print([o.name for o in spec.options][:3])
model = ng.catalogue.material_model("mohr-coulomb")
print([p.name for p in model.parameters])
```

```text
['NAME', 'INC', 'NLGEOM']
['E', 'nu', 'c', 'phi', 'psi', 'theta']
```

`ng.catalogue.describe(name)` renders the same facts as text (keywords, `material:<model>`,
`element:<type>`), followed by the page of the numgeo manual where there is one;
`ng.catalogue.suggest(name)` proposes the closest known names for a misspelling. The file `llms.txt`
at the root of the documentation site summarises the API in one page.

## A working loop

1. Build or change a `Deck` with the API (or read an input with `ng.parse`).
2. `ng.validate(deck)`; fix every `error`, read every `warning`.
3. `ng.run(deck, workdir, check_only=True)` lets numgeo itself read the input (fast).
4. `ng.run(deck, workdir)`; act on `res.status` and `res.errors`.
5. Read the results with `ng.open_results(workdir, job)`.

Issues are plain data:

```python
deck = ng.parse_text("*Node\n1, 0., 0.\n2, 1., 0.\n*Element, type=u2-truss\n1, 1, 2\n").deck
issues = ng.validate(deck)
print(issues[0].as_dict())
```

```text
{'id': 'NG-MESH-008', 'severity': 'error', 'message': '1 element(s) have no material (*Solid section), e.g. [1]', 'location': None, 'keyword': None, 'source': 'src/database/database.f90:512-520'}
```

`source` names the numgeo source lines the check mirrors.

## Command line with JSON output

Every command takes `--json` and prints one JSON document. Each document starts with `"pynumgeo"`:
`{"program", "version", "author", "numgeo_version", "numgeo_source_commit"}`, the pynumgeo that wrote it
and the numgeo build it was made for; the table lists the fields that follow. `pynumgeo --version` prints
the version. Exit status: 0 fine, 1 errors found or the run failed, 2 usage error (for example a missing
file).

| command | output |
|---|---|
| `pynumgeo validate model.inp --json` | `{"input", "errors", "issues": [issue, ...]}`, errors first |
| `pynumgeo run model.inp --workdir w --json` | `{"status", "reason", "workdir", "exit_code", "duration", "steps", "errors"}` |
| `pynumgeo run model.inp --check-only --json` | the same, status `INPUT_ACCEPTED` or `FAILED` |
| `pynumgeo info "*Initial conditions" --json` | `{"name", "entries": [entry, ...]}`, the catalogue entries of a keyword (`material:<m>`, `element:<t>` also work) |
| `pynumgeo roundtrip model.inp -o out.inp --json` | `{"input", "equal_after_reading_back", "read_issues", "output"}` |
| `pynumgeo catalogue --json` | numgeo version, source commit and counts (`--list` adds all names) |

## Things that are easy to get wrong

- **Names containing option words.** numgeo finds options by searching for words inside the option
  text: a set named `FindFix` switches on `find`, an amplitude named `VelocityRamp` turns a boundary
  condition into a velocity condition. The validator reports such names (`NG-NAME-002`, `NG-NAME-005`),
  the writer refuses them, and `deck.safe_names()` renames them with all references.
- **Node labels** must be 1..N in the order of definition (`Mesh.add_nodes` does this).
- **Exit status 0** does not mean success; use `RunResult.status`.
- **Units** must be consistent; pynumgeo's examples use m, kN, kPa, t, s.
- **File names** in the input (amplitude tables, initial-condition files) are lower-cased by numgeo;
  keep them lower case and in the job folder.
- **Build profile.** The default validates for the current numgeo developer build; for a public numgeo
  build use `ng.validate(deck, profile=ng.BuildProfile.public_build())`.
