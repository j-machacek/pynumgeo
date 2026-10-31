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

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/pynumgeo-logo-dark.svg">
    <img src="docs/assets/pynumgeo-logo.svg" alt="pynumgeo" height="80">
  </picture>
</p>

# pynumgeo

[PyPI](https://pypi.org/project/pynumgeo/) ·
[Documentation](https://j-machacek.github.io/pynumgeo/) ·
[numgeo](https://www.numgeo.de) ·
[numgeo documentation](https://j-machacek.github.io/numgeo/)

Python API for the finite element code [numgeo](https://www.numgeo.de): the object model of a numgeo
input deck, reading and writing input files, validation against what the solver accepts, running the
solver, and reading its results — headless, on Windows and Linux.

```python
import pynumgeo as ng

deck = ng.read("model.inp")              # numgeo input -> Deck (mesh, materials, steps, ...)
issues = ng.validate(deck)               # what numgeo would reject or read differently
ng.write(deck, "job/model.inp")          # normal-case, deterministic numgeo input
res = ng.run(deck, "job", job="model")   # run numgeo, judge the outcome from its report files
frames = ng.open_results("job", "model").frames()
```

```console
pip install --pre pynumgeo               # Python 3.11+; runtime dependencies: numpy, pydantic 2
pynumgeo validate model.inp              # every command also has --json
pynumgeo run model.inp --workdir runs/m1
pynumgeo info "*Initial conditions"
pynumgeo --version
```

The [documentation](https://j-machacek.github.io/pynumgeo/) is built with [Zensical](https://zensical.org)
from `docs/` (`pip install -e ".[docs]"`, then `zensical serve`); `docs/llms.txt` is a one-page summary for
agents.

pynumgeo `2026.2.0.dev4` is a pre-release (hence `pip install --pre`) built against the numgeo developer
source `834564ed` (`numgeo2026-v2`), with `*Model change, friction` of `60fca8b5` and the Concrete model (`*Mechanical = Concrete`) of the numgeo developer source of 31.10.2026; `2026.2.0` will be released together with numgeo2026-v2. Every input file it writes starts with a header that names the
pynumgeo version, its author and the numgeo build it was written for.

Author: Jan Machacek. Licence: BSD-3-Clause (`LICENSE`). The numgeo reference texts bundled with the
package are covered by the numgeo copyright notice in `NOTICE`.
