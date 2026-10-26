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
"""What pynumgeo writes into every file it creates: program, version and author.

* Input files start with a banner of numgeo comment lines (``**``), in the style of the numgeo source
  files: :func:`input_file_header`. numgeo cuts every line at ``**``, so the banner is not read.
* The console log of a run (``<job>.console.log``) starts with :func:`console_header`; the console
  parser skips that line.
* The JSON reports of the command line carry :func:`provenance` under the key ``"pynumgeo"``.

The creation date is not written: the same deck always gives the same file.

Examples:
    >>> print("\\n".join(input_file_header()))  # doctest: +ELLIPSIS
    ** =~~=~~=...=~=~
    ...numgeo input file
    ...Created with pynumgeo ..., the Python API for numgeo by Jan Machacek
    ...Written for numgeo... (numgeo source ...)
    ** =~~=~~=...=~=~
"""

from __future__ import annotations

from pynumgeo._version import NUMGEO_SOURCE_COMMIT, NUMGEO_VERSION, __version__

__all__ = ["AUTHOR", "BANNER", "CONSOLE_MARK", "console_header", "input_file_header", "provenance"]

#: The author of pynumgeo.
AUTHOR = "Jan Machacek"
#: Banner line of the numgeo source files (103 characters).
BANNER = "=~~" * 33 + "=~=~"
#: Start of the first line of a console log written by pynumgeo.
CONSOLE_MARK = "pynumgeo "


def _centre(text: str) -> str:
    return " " * max((len(BANNER) - len(text)) // 2, 0) + text


def input_file_header() -> list[str]:
    """The comment lines at the top of every input file pynumgeo writes (each at most 106 characters)."""
    lines = [
        BANNER,
        _centre("numgeo input file"),
        _centre(f"Created with pynumgeo {__version__}, the Python API for numgeo by {AUTHOR}"),
        _centre(f"Written for {NUMGEO_VERSION} (numgeo source {NUMGEO_SOURCE_COMMIT[:8]})"),
        BANNER,
    ]
    return [f"** {ln}" for ln in lines]


def console_header(command: list[str]) -> str:
    """The first line of ``<job>.console.log``: who recorded it, and the command that started numgeo."""
    return f"{CONSOLE_MARK}{__version__} (Python API for numgeo by {AUTHOR}): console output of {' '.join(command)}"


def provenance() -> dict[str, str]:
    """Program, version and author, plus the numgeo build pynumgeo was written for (JSON reports)."""
    return {
        "program": "pynumgeo",
        "version": __version__,
        "author": AUTHOR,
        "numgeo_version": NUMGEO_VERSION,
        "numgeo_source_commit": NUMGEO_SOURCE_COMMIT,
    }
