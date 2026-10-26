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
"""Version of pynumgeo and of the numgeo source it was derived from.

pynumgeo follows the numgeo version: numgeo ``numgeo2026-v2`` corresponds to pynumgeo ``2026.2.x``
(``.devN`` until it is released together with numgeo).
"""

__version__ = "2026.2.0.dev0"

#: numgeo version string this pynumgeo was derived from (console banner of the solver).
NUMGEO_VERSION = "numgeo2026-v2"
#: numgeo-src commit the catalogue was generated from.
NUMGEO_SOURCE_COMMIT = "834564ed77c2aa9ce5f6cdeabc03293c331520af"
#: numgeo documentation commit the bundled reference pages come from.
NUMGEO_DOCS_COMMIT = "eceee9749a1f0e47ff9aeedd50131707c4d7290a"
