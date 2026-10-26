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
"""Voigt vectors from numgeo results as 3x3 tensors, with the component order and shear made explicit.

numgeo stores stresses and strains in the Voigt order ``[11, 22, 33, 12, 13, 23]``
(``src/fem/fem_deformation_matrix_.f90:150-165``); print files use this order. The 6-component VTK arrays
``Stress``, ``Strain``, ``Stress-PhEl``, ``Stress-PhVis`` are reordered to VTK's ``[11, 22, 33, 12, 23, 13]``
(``map_to_vtk``, ``src/output/VTK_write_stress_.f90:271``, ``src/output/VTK_write_strain_.f90:257``).
Strains carry **engineering** shear components gamma = 2 epsilon in both; readers return them
unchanged and this function halves them only when asked to.

Examples:
    >>> import numpy as np
    >>> t = voigt_to_tensor(np.array([1.0, 2.0, 3.0, 0.4, 0.5, 0.6]), order="vtk", engineering_shear=True)
    >>> t.tolist()
    [[1.0, 0.2, 0.3], [0.2, 2.0, 0.25], [0.3, 0.25, 3.0]]
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import numpy.typing as npt

__all__ = ["VoigtOrder", "voigt_to_tensor"]

VoigtOrder = Literal["numgeo", "vtk"]

#: (i, j) of the six Voigt components.
_ORDERS: dict[str, tuple[tuple[int, int], ...]] = {
    "numgeo": ((0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)),
    "vtk": ((0, 0), (1, 1), (2, 2), (0, 1), (1, 2), (0, 2)),
}


def voigt_to_tensor(values: npt.ArrayLike, *, order: VoigtOrder, engineering_shear: bool) -> npt.NDArray[np.float64]:
    """Symmetric 3x3 tensors from Voigt vectors.

    Args:
        values: shape ``(..., 6)``.
        order: ``"numgeo"`` (print files, ``[11, 22, 33, 12, 13, 23]``) or ``"vtk"`` (VTK tensor arrays,
            ``[11, 22, 33, 12, 23, 13]``).
        engineering_shear: ``True`` for numgeo strains (shear components are gamma = 2 epsilon and are
            halved), ``False`` for stresses.

    Returns:
        Array of shape ``(..., 3, 3)``.

    Raises:
        ValueError: if the last axis does not have 6 components or ``order`` is unknown.
    """
    v = np.asarray(values, dtype=np.float64)
    if v.shape[-1:] != (6,):
        raise ValueError(f"expected 6 Voigt components in the last axis, got shape {v.shape}")
    if order not in _ORDERS:
        raise ValueError(f"unknown Voigt order {order!r}; use 'numgeo' or 'vtk'")
    out = np.zeros((*v.shape[:-1], 3, 3))
    for k, (i, j) in enumerate(_ORDERS[order]):
        x = v[..., k] * (0.5 if engineering_shear and i != j else 1.0)
        out[..., i, j] = x
        out[..., j, i] = x
    return out
