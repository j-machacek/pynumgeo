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

# Quickstart

The examples on this page run as shown; the ones that start numgeo need the executable (see
[installation](install.md#the-numgeo-executable)).

## Build a deck

A one-element cantilever beam (numgeo benchmark `beam-slender-1elem`): two nodes, one `u2-beam`
element, clamped at node 1 and loaded at node 2.

```python
import pynumgeo as ng

deck = ng.Deck()
deck.mesh.add_nodes([[0.0, 0.0], [0.2, 0.0]])          # labels 1, 2
deck.mesh.add_elements("u2-beam", [[1, 2]])
deck.mesh.add_nset("Fix", [1])
deck.mesh.add_nset("Load", [2])
deck.mesh.add_nset("Nodes", [1, 2])
deck.mesh.add_elset("All", [1])

beam = ng.Material(name="Beam", phases=1)
beam.add("*Beam properties", data=[[1e-4, 210e6, 80.77e6, 8.33e-10, 8.33e-10, 16.67e-10, 0.8333, 0.8333]])
beam.add("*Density", data=[[1.0]])
deck.materials.append(beam)
deck.assign("All", "Beam")                             # *Solid section, elset=All, material=Beam

deck.amplitudes.append(ng.Amplitude(name="Loading", type="tabular", data=[[0.0, 0.0], [1.0, 1.0]]))
step = ng.Step(name="Loading", inc=1000000, procedure=ng.Keyword.make("*Static", data=[[0.05, 1.0, 0.05, 0.05]]))
step.add("*Boundary", data=[["Fix", "u1", 0.0], ["Fix", "u2", 0.0], ["Fix", "r3", 0.0]])
step.add("*Cload", options=[("amplitude", "Loading")], data=[["Load", 2, -1.0]])
step.add("*Output", options=["print"], children=[ng.Keyword.make("*Nodeoutput", options=[("nset", "Load")], data=[["U"]])])
step.add("*Output", options=["field", "vtk"], children=[ng.Keyword.make("*Nodeoutput", options=[("nset", "Nodes")], data=[["U"]])])
deck.steps.append(step)
```

Node and element labels are 1..N in the order of definition; numgeo requires this (node-set members
are used as array positions). `add_nodes` and `add_elements` number them for you.

Keywords, options and data lines are spelled as in the numgeo manual, in any case; pynumgeo normalises
them. What a keyword accepts is in the catalogue:

```python
print(ng.catalogue.describe("*Static", with_docs=False))
```

```text
*Static   (context: step-procedure; area: step)
  data: dt0, t_end, dtmin, dtmax   [narg == 4 (get_num_arguments, 384-389)]
  notes: Sets calc%static (382).
```

Constitutive models take their parameters by name or in order, checked against the catalogue:

```python
sand = ng.Material(name="Sand", phases=1)
sand.set_mechanical("mohr-coulomb", {"E": 1e5, "nu": 0.3, "c": 1.0, "phi": 0.5236, "psi": 0.0, "theta": 29.0})
print(ng.catalogue.describe("material:mohr-coulomb", with_docs=False).splitlines()[0])
```

```text
*Mechanical = mohr-coulomb  (6 parameters)
```

## Validate

```python
issues = ng.validate(deck)
assert not [i for i in issues if i.severity == "error"]
for issue in issues:
    print(issue)            # id, severity, location, message
```

Every issue has a stable id (`NG-STEP-128`, ...). `ng.validate(deck, profile=ng.BuildProfile.public_build())`
checks for a numgeo build with `public_version = .true.`; the default is the current developer build.

## Write

```python
text = ng.write_text(deck)
print(text.splitlines()[5:8])
assert ng.parse_text(text).deck == deck                # reading the output back gives the same deck
```

```text
['*Node', '1, 0.0, 0.0', '2, 0.2, 0.0']
```

The writer uses normal case (`*Beam properties`, `*Step, name=Loading`), never all capitals; numgeo
upper-cases every line itself. `ng.write(deck, "job/beam.inp")` writes the file.

Every input file pynumgeo writes starts with a header of numgeo comment lines (numgeo does not read them)
that names the program, its version and author, and the numgeo build it was written for:

```python
print("\n".join(text.splitlines()[:5]))
```

```text
** =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
**                                            numgeo input file
**             Created with pynumgeo 2026.2.0.dev3, the Python API for numgeo by Jan Machacek
**                           Written for numgeo2026-v2 (numgeo source 834564ed)
** =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
```

`deck.comments` are written below it; `ng.write(deck, path, header=False)` leaves the header and the
comments out. The creation date is not written, so the same deck always gives the same file. The console
log of a run (`<job>.console.log`) starts with a line naming the pynumgeo version and the command, and
every `--json` report of the command line carries the version under `"pynumgeo"`; `pynumgeo --version`
prints it.

## Read

```python
import pathlib, tempfile

folder = pathlib.Path(tempfile.mkdtemp())
ng.write(deck, folder / "beam.inp")
result = ng.parse(folder / "beam.inp")                  # deck + reader issues; raises only for missing files
print(result.ok, [str(i) for i in result.issues])
deck2 = ng.read(folder / "beam.inp")                    # raises ng.ReadError if the reader finds errors
print(deck2.summary()["mesh"]["elements"])
```

```text
True []
{'u2-beam': 1}
```

`parse` reports what numgeo would do differently from what the text suggests, for example an option
word inside a name (`*Nset, nset=FindFix` switches the `find` option on in numgeo).

## Run

numgeo is found through `executable=`, the environment variable `NUMGEO_EXE` or the `PATH`.

```python
# needs numgeo
res = ng.run(deck, folder / "run", job="beam", timeout=300)
print(res.status, res.reason)
assert res.status == ng.RunStatus.SUCCESS
```

`res.status` is one of `SUCCESS`, `FAILED`, `INCOMPLETE` (a step ran out of increments), `TIMEOUT`,
`CRASHED` and `INPUT_ACCEPTED` (with `check_only=True`). The decision is taken from numgeo's report
files; `res.errors` lists the solver's error messages with the source line that wrote them.

## Results

```python
# needs numgeo
results = ng.open_results(folder / "run", "beam")
tip = results.print_series("Load", "node", 2)
print(round(float(tip.column("U2")[-1]), 6))
frames = results.frames()
u = frames[-1].point_data("Displacement")              # numpy array, one row per node
```

```text
-0.015274
```

## Command line

```console
$ pynumgeo validate model.inp            # reader + validator issues, exit status 1 on errors
$ pynumgeo run model.inp --workdir runs/m1 --ncpus 4
$ pynumgeo info "*Initial conditions"     # keyword reference: source facts and the manual page
$ pynumgeo roundtrip model.inp -o model-normal-case.inp
```

Every command has `--json`; see [for agents](for-agents.md).
