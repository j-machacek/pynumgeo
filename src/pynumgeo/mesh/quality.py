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
"""Element orientation: positive Jacobian at the element centre (pynumgeo rule).

numgeo does not check the orientation of the elements: the check in ``element_jacobian`` is commented out
(``src/fem/fem_element_jacobian.f90:46, 149-154``) and only the u-T elements ask for a cutback when the
determinant is not positive (``src/elements/element_UT_solid_.f90:197-200``). An element with clockwise
nodes (2D) or a mirrored node order (3D) is integrated with a negative volume. pynumgeo therefore requires
``det(dx/dxi) > 0`` at the centre of every 2D and 3D continuum element; in 2D this means the corner nodes
are numbered counter-clockwise (x right, y up). Beams, trusses and shells (triangles and quadrilaterals in a
3D model) are not checked: a shell's node order only defines its normal (faces ``F1``/``F2``).

Examples:
    >>> from pynumgeo.mesh import Mesh
    >>> m = Mesh()
    >>> _ = m.add_nodes([[0, 0], [1, 0], [1, 1], [0, 1]])
    >>> _ = m.add_elements("u4-solid", [[1, 4, 3, 2]])
    >>> inverted_elements(m).tolist()
    [1]
    >>> check_orientation(reoriented(m))
    []
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from pynumgeo import catalogue as _cat
from pynumgeo.mesh.convert import flip_permutation
from pynumgeo.mesh.mesh import ElementBlock, ElementSet, Mesh, NodeSet, Surface
from pynumgeo.mesh.topology import Topology, element_topology

__all__ = [
    "DEGENERATE_RTOL",
    "block_jacobians",
    "check_orientation",
    "degenerate_elements",
    "inverted_elements",
    "reoriented",
]

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

#: relative size of |det J| (to the element's bounding box size ** dim) below which an element is degenerate
DEGENERATE_RTOL = 1.0e-10


def _checked_topology(mesh: Mesh, block: ElementBlock) -> Topology | None:
    """The topology if the block is a 2D/3D continuum block of the model (else None)."""
    try:
        e = _cat.element_type(block.type)
    except KeyError:
        return None
    t = element_topology(block.type)
    if t.dim < 2 or t.dim != e.ndim:  # beams/trusses, shells (2D shape in a 3D element type)
        return None
    return t


def _geometry(mesh: Mesh, block: ElementBlock) -> tuple[Topology, FloatArray] | None:
    """Topology and ``(n_elements, nnodes, dim)`` node coordinates of a checked block."""
    t = _checked_topology(mesh, block)
    if t is None:
        return None
    if block.connectivity.shape[1] != t.nnodes:
        raise ValueError(f"{block.type} needs {t.nnodes} nodes, the block has {block.connectivity.shape[1]}")
    if mesh.coords.shape[1] < t.dim:
        raise ValueError(f"{block.type} is {t.dim}D, the coordinates have {mesh.coords.shape[1]} columns")
    pos = np.full(int(np.max(mesh.node_labels)) + 1 if mesh.node_count else 1, -1, dtype=np.int64)
    pos[mesh.node_labels] = np.arange(mesh.node_count)
    conn = block.connectivity
    if conn.size and (int(np.min(conn)) < 0 or int(np.max(conn)) >= pos.size):
        raise ValueError(f"block {block.type} refers to undefined nodes")
    idx = pos[conn]
    if np.any(idx < 0):
        raise ValueError(f"block {block.type} refers to undefined nodes")
    return t, mesh.coords[:, : t.dim][idx]


def block_jacobians(mesh: Mesh, block: ElementBlock) -> FloatArray | None:
    """``det(dx/dxi)`` at the reference centre of every element of ``block`` (``None`` if not checked).

    Uses numgeo's shape functions of the full node set (mid-side nodes included). For 2D elements the
    first two coordinates are used.
    """
    g = _geometry(mesh, block)
    if g is None:
        return None
    t, x = g
    dn = t.shape_derivatives(t.centroid)  # (dim, nnodes)
    jac = np.einsum("kn,enj->ekj", dn, x)  # J[e, k, j] = d x_j / d xi_k
    return np.asarray(np.linalg.det(jac), dtype=np.float64)


def _classify(mesh: Mesh, block: ElementBlock) -> tuple[IntArray, IntArray] | None:
    """(inverted, degenerate) element labels of a block (None if the block is not checked)."""
    g = _geometry(mesh, block)
    det = block_jacobians(mesh, block)
    if g is None or det is None:
        return None
    t, x = g
    size = np.max(np.ptp(x, axis=1), axis=1) if x.size else np.zeros(0)
    degenerate = np.abs(det) <= DEGENERATE_RTOL * size**t.dim
    inverted = (det < 0) & ~degenerate
    return block.labels[inverted], block.labels[degenerate]


def inverted_elements(mesh: Mesh) -> IntArray:
    """Labels of the checked elements with a negative Jacobian at the centre (degenerate ones excluded)."""
    out = [c[0] for b in mesh.blocks if (c := _classify(mesh, b)) is not None]
    return np.concatenate(out) if out else np.zeros(0, dtype=np.int64)


def degenerate_elements(mesh: Mesh) -> IntArray:
    """Labels of the checked elements whose Jacobian at the centre is (nearly) zero.

    "Nearly": ``|det J| <= DEGENERATE_RTOL * h**dim`` with ``h`` the largest edge of the element's bounding
    box.
    """
    out = [c[1] for b in mesh.blocks if (c := _classify(mesh, b)) is not None]
    return np.concatenate(out) if out else np.zeros(0, dtype=np.int64)


def _examples(labels: IntArray) -> str:
    shown = ", ".join(str(int(x)) for x in labels[:10])
    return shown + (", ..." if labels.size > 10 else "")


def check_orientation(mesh: Mesh) -> list[str]:
    """Problems with the orientation of the 2D/3D continuum elements (empty list = all fine).

    Like :meth:`Mesh.check <pynumgeo.mesh.mesh.Mesh.check>`, one message per element block and kind:
    negative Jacobian at the centre (nodes clockwise in 2D, mirrored in 3D; :func:`reoriented` reverses
    them) and (nearly) zero Jacobian (collapsed elements). Blocks of beams, trusses, shells and of element
    types missing from the catalogue are not checked.
    """
    out: list[str] = []
    for bi, b in enumerate(mesh.blocks):
        c = _classify(mesh, b)
        if c is None:
            continue
        inverted, degenerate = c
        if inverted.size:
            what = "clockwise node order" if element_topology(b.type).dim == 2 else "mirrored node order"
            out.append(
                f"block {bi} ({b.type}): {inverted.size} elements have a negative Jacobian at the centre "
                f"({what}; numgeo integrates a negative volume and does not check this): "
                f"{_examples(inverted)}"
            )
        if degenerate.size:
            out.append(
                f"block {bi} ({b.type}): {degenerate.size} elements are degenerate (Jacobian ~ 0 at the "
                f"centre): {_examples(degenerate)}"
            )
    return out


def reoriented(mesh: Mesh, elements: npt.ArrayLike | None = None) -> Mesh:
    """Copy of ``mesh`` with the node order of ``elements`` reversed (default: :func:`inverted_elements`).

    The reversal mirrors the reference element (:func:`pynumgeo.mesh.convert.flip_permutation`), so corner
    and mid-side nodes stay consistent. Face numbers of these elements change: element-based surfaces that
    refer to them must be rebuilt.
    """
    todo = inverted_elements(mesh) if elements is None else np.asarray(elements, dtype=np.int64).reshape(-1)
    want = {int(x) for x in todo}
    new = Mesh()
    new.node_labels = mesh.node_labels.copy()
    new.coords = mesh.coords.copy()
    for b in mesh.blocks:
        conn = b.connectivity.copy()
        rows = np.array([int(lab) in want for lab in b.labels], dtype=bool)
        if rows.any():
            conn[rows] = conn[rows][:, flip_permutation(element_topology(b.type).name)]
        new.blocks.append(ElementBlock(b.type, b.labels.copy(), conn, list(b.options)))
    new.nsets = [NodeSet(s.name, s.kind, s.members.copy(), list(s.values), s.internal, s.instance) for s in mesh.nsets]
    new.elsets = [
        ElementSet(s.name, s.kind, s.members.copy(), list(s.values), s.internal, s.instance) for s in mesh.elsets
    ]
    new.surfaces = [Surface(s.name, s.type, list(s.rows)) for s in mesh.surfaces]
    return new
