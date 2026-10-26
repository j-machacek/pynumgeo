# Solver

```numgeo 
*Solver, <solver name> [, <solver options>]
``` 

This command is used to specify the solver to be used to solve the system of equations of the current step. As default, the `Pardiso` solver is used. The following solvers can be selected:

- `<solver name>`

    Use this keyword to specify the strategy for solving the system of equations. numgeo offers direct solvers as well as iterative solvers.

    * Direct solvers: [PARDISO](#pardiso), [MUMPS](#mumps) (also [on the GPU](#mumps-on-the-gpu)), [cuDSS](#cudss) (on the GPU), [Simple solver](#simple-solver), [Diagonal solver](#diagonal-solver)
    * Iterative solvers:
        * [Reuse of the factorization](#reuse-of-the-factorization) of the direct solvers (`*Solver, Pardiso, iterative`, `*Solver, MUMPS, iterative` and `*Solver, cuDSS, iterative`)
        * [GMRES](#gmres) with an incomplete factorization as preconditioner
        * [AMGCL](#amgcl): algebraic multigrid on the processor or on a graphics card, for large three-dimensional models
        * [LIS library](#lis-solver-library): GMRES, FGMRES, BiCGStab, ...
    * [External solvers](#external-solver): Use this option to interface external solvers to numgeo.

    In addition you have the option to [deactivate the solver](#deactivate-solver).

The coupled [u-T solid formulation](../theory/elements/thermoelastic-solids.md#weak-form-and-tangent) requires an unsymmetric equation system. The default PARDISO solver supports this system.

The solver is the first argument of the command. An unknown solver name is reported with a warning in the `.log` file and the default solver is used.

---

## Direct solvers

### PARDISO

```numgeo
*Solver, Pardiso [, iterative] [, tol=<tolerance>] [, max_iter=<iterations>]
```

PARDISO is a thread-safe and memory efficient software for solving large sparse symmetric and unsymmetric linear systems of equations on shared-memory and distributed-memory multiprocessors [@Coninck2016,Kourounis2018]. We interface the oneMKL PARDISO implementation. PARDISO is the default solver (no need to enable it using `*Solver, Pardiso`)

The options `iterative`, `tol` and `max_iter` are described in [Reuse of the factorization](#reuse-of-the-factorization).

### MUMPS

```numgeo
*Solver, MUMPS [, device=cpu | gpu] [, iterative] [, tol=<tolerance>] [, max_iter=<iterations>]
```

MUMPS - the MUltifrontal Massively Parallel sparse direct Solver (Amestoy et al. 2001[@amestoy2001] and Amestoy et al. 2006[@amestoy2006]). numgeo ships with a shared-memory (OpenMP enabled, MPI disabled) version. For an MPI-parallelised version see the [External solver](#external-solver) feature. To enable MUMPS in a step, use `*Solver, Mumps`.

`device=cpu` is the default. With `device=gpu`, a numgeo executable built with MUMPS 5.9 GPU support can offload parts of the numerical factorization to a graphics card. The Windows integration uses one NVIDIA CUDA device and cuBLASXt; it needs a compatible NVIDIA driver and the CUDA/cuBLAS runtime libraries distributed with that executable. It does not use AMGCL's OpenCL backend.

!!! note "GPU architecture and portability"

    The standard Windows GPU build uses **CUDA 13.0.2**, which requires an NVIDIA **Turing GPU (compute capability 7.5) or newer** and a CUDA-13-compatible NVIDIA driver (**R580 family or newer**, with support for the particular GPU). Maxwell, Pascal and Volta are excluded by CUDA 13's library support; updating the driver alone does not enable them. They need a separately validated build using an older compatible CUDA SDK. See [NVIDIA's release notes](https://docs.nvidia.com/cuda/archive/13.0.2/cuda-toolkit-release-notes/index.html) and [driver compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).

    The executable is not bound to the build workstation or its GPU model. Copy the complete `build-scripts\win\numgeo-gpu` directory, including its DLLs, to another compatible Windows x64 workstation. GPU drivers must be installed on that machine; a compiler or CUDA toolkit is not needed. All CPU solvers remain available without a GPU. AMD and Intel GPUs cannot use the MUMPS CUDA backend, but may support AMGCL's independent OpenCL 1.2 backend if they provide double precision. The CUDA/Turing restriction does not apply to AMGCL OpenCL.

At the start of each step numgeo checks that a CUDA device and cuBLASXt can be initialized. If the check fails, or the executable was built without MUMPS GPU support, it warns in the `.log` file and uses MUMPS on the CPU. The setting applies to the current step only. `ncpus` still controls CPU work when the GPU is enabled. The first visible CUDA device is used; `CUDA_VISIBLE_DEVICES` can restrict the devices before launching numgeo.

The `.sta` file reports the requested and selected device, the number of factorizations, the number that performed GPU work, and the accumulated `gpu_flops` and `gpu_seconds`. A selected GPU can perform no work for small matrices: check for positive `gpu_flops` and `gpu_factorizations` before treating a run as GPU accelerated. The [large-model tutorial](../tutorial/advanced/large-models.md#mumps-on-the-gpu) explains the output and compares CPU and GPU runs.

The options `iterative`, `tol` and `max_iter` are described in [Reuse of the factorization](#reuse-of-the-factorization).

They can be combined with `device=gpu`, for example `*Solver, MUMPS, device=gpu, iterative`. Reusing a factorization reduces the number of factorizations available for GPU offloading; measure this strategy separately from the default direct solution.

The analysis of the matrix (ordering and symbolic factorization) is performed once per step. Equations without stiffness and without load (e.g. degrees of freedom to which no active element contributes) do not terminate the analysis; the corresponding unknown is zero, as with PARDISO.

#### MUMPS on the GPU

```numgeo
*Solver, MUMPS, device=gpu
*Solver, MUMPS, iterative, device=gpu
```

With `device=gpu` MUMPS (version 5.9, control parameter `ICNTL(51)`) offloads work of the numerical factorization to an NVIDIA graphics card (CUDA, cuBLAS): the dense operations on the large frontal matrices are performed on the GPU, small frontal matrices remain on the CPU. The solution is the same as with `device=cpu` up to rounding.

Requirements:

* the GPU version of numgeo (`numgeo-gpu`, which contains the CUDA libraries next to `numgeo.exe`). The CPU version contains no CUDA code; with it, `device=gpu` falls back to the CPU. A CUDA toolkit is not needed on the workstation.
* an NVIDIA GPU of the Turing generation (compute capability 7.5) or newer, e.g. Turing, Ampere, Ada, Hopper, Blackwell, with a driver for CUDA 13 (R580 family or newer). Maxwell, Pascal and Volta GPUs are not supported by the CUDA 13 libraries of numgeo; a newer driver does not change this. Graphics cards of AMD and Intel cannot be used by MUMPS.

numgeo uses the first visible NVIDIA GPU (CUDA device 0). Another GPU is selected with the environment variable `CUDA_VISIBLE_DEVICES` before numgeo is started, e.g. `set CUDA_VISIBLE_DEVICES=1` on Windows. At the start of the step numgeo tests the GPU (device, compute capability, memory allocation, cuBLAS) and writes the result to the `.log` file:

```
MUMPS device: GPU; NVIDIA RTX PRO 4000 Blackwell (CUDA device 0)
```

If no usable GPU is found (CPU version of numgeo, no NVIDIA GPU, GPU older than Turing, driver too old, GPU not accessible), the reason is reported with a warning and the step is solved on the CPU, e.g.

```
MUMPS device=gpu: CPU fallback; no usable CUDA device: no visible NVIDIA GPU
```

At the end of each step the statistics file (`.sta`) reports the requested and the selected device and the work done on the GPU:

```
MUMPS device: requested=GPU selected=GPU
MUMPS statistics: factorizations=17 gpu_factorizations=17 gpu_flops= 1.2345678901234567E+012 gpu_seconds= 4.5678901234567890E+000
```

`gpu_factorizations` is the number of factorizations with work on the GPU, `gpu_flops` and `gpu_seconds` are the floating point operations and the time on the GPU summed over the factorizations of the step (`RINFOG(22)` and `RINFOG(23)` of MUMPS). With `selected=GPU` and `gpu_flops = 0` no frontal matrix was large enough for the GPU: the model is too small to benefit.

Notes:

* Whether the GPU is faster than the CPU depends on the size of the frontal matrices (large three-dimensional models) and on the double precision performance of the graphics card. Compare the time of the solver (`solving process` in the time statistics of the `.sta` file) of a few increments with `device=cpu` and `device=gpu` for your model.
* A successful test at the start of the step does not guarantee that the frontal matrices fit into the memory of the graphics card.
* With [`iterative`](#reuse-of-the-factorization) the GPU is used for the factorizations; the GMRES iterations in between use the existing factors.
* The direct solver which solves the systems for which [GMRES](#gmres) does not converge runs on the CPU, also if it is MUMPS.
* `device=` is an option of MUMPS only; `*Solver, Pardiso, device=gpu` is refused with an error message. The direct solver which runs completely on the GPU is [cuDSS](#cudss).

### cuDSS

```numgeo
*Solver, cuDSS [, iterative] [, tol=<tolerance>] [, max_iter=<iterations>] [, fallback=pardiso|mumps|no]
```

cuDSS is the sparse direct solver of NVIDIA for graphics cards (version 1.0, CUDA 13). numgeo passes the matrix of the system in the same form as to PARDISO (real, unsymmetric) and uses the settings of its PARDISO interface: the analysis (nested dissection ordering, symbolic factorization, matching and scaling computed from the first matrix of the step) is performed once per step, the numerical factorization of every matrix and the solution with two steps of iterative refinement are performed on the GPU. Pivots are exchanged within the blocks (supernodes) of the factorization; pivots which are too small are replaced by a small value (pivot perturbation, 10$^{-13}$), as with PARDISO. The solution is not checked: as for the other direct solvers, the [convergence criteria](../theory/solution-method/convergence-criteria.md) decide on the increment.

- `iterative`, `tol`, `max_iter`: [reuse of the factorization](#reuse-of-the-factorization). GMRES runs on the processor; its preconditioner is the substitution with the factors on the GPU.

- `fallback = pardiso | mumps | no`: direct solver on the processor for the systems which cuDSS does not solve. Default: PARDISO (MUMPS in a version of numgeo without PARDISO).

Requirements: the GPU version of numgeo (`numgeo-gpu`, which contains `cudss64_1.dll` and the CUDA libraries next to `numgeo.exe`) and an NVIDIA GPU of the Turing generation (compute capability 7.5) or newer with a driver for CUDA 13 (R580 family or newer), as for [MUMPS on the GPU](#mumps-on-the-gpu). A CUDA toolkit is not needed on the workstation. numgeo uses the first visible NVIDIA GPU (CUDA device 0, `CUDA_VISIBLE_DEVICES`). At the start of the step the GPU is tested and reported in the `.log` file:

```
cuDSS device: GPU; <name of the GPU> (CUDA device 0, compute capability <major>.<minor>, <memory> GB)
```

Memory of the graphics card: the factors of a large three-dimensional model may not fit into the memory of the graphics card. After the analysis numgeo compares the memory which cuDSS estimates for the factorization with the free memory of the GPU; if it does not fit, the factors are kept in the memory of the computer and cuDSS moves parts of them to the GPU while it factorizes and solves (hybrid memory mode of cuDSS, `hybrid_memory=1` in the statistics file). The hybrid memory mode is slower than a factorization in the memory of the GPU, but it allows models of the size which PARDISO and MUMPS can solve in the memory of the computer.

Without a usable GPU (CPU version of numgeo, no NVIDIA GPU, GPU older than Turing, driver too old, GPU not accessible) the systems of the step are solved with the direct solver of `fallback` on the processor, with a warning in the `.log` file:

```
Solver cuDSS: no usable GPU (no usable CUDA device: no visible NVIDIA GPU). The systems of this step are solved with the direct solver Pardiso on the CPU.
```

If cuDSS fails during the step (e.g. not even the hybrid memory mode fits, or an error of the GPU), the system is analysed and factorized once more with the current matrix; if it fails again, this and all further systems of the step are solved with the direct solver of `fallback`, again with a warning. With `fallback=no` the analysis stops if there is no usable GPU, and a failure of cuDSS during the step repeats the increment with a smaller time increment.

At the end of each step the statistics file (`.sta`) reports the device, the work of cuDSS and the systems solved by the fallback:

```
cuDSS device: requested=GPU selected=GPU; <name of the GPU> (CUDA device 0, compute capability <major>.<minor>, <memory> GB)
cuDSS statistics: analyses=<a> factorizations=<f> solutions=<s> fallback_systems=<n> fallback=Pardiso hybrid_memory=0
cuDSS times: analysis=<t> s factorization=<t> s solution=<t> s
cuDSS factors: lu_nnz=<l> flops=<o> pivots=<p> peak_device_memory=<m> GB device_memory=<m> GB
```

* `analyses`, `factorizations`, `solutions`: number of analyses, numerical factorizations and solutions (substitutions) of cuDSS in the step; `fallback_systems`: systems solved with the direct solver `fallback` on the processor; `hybrid_memory=1`: the last analysis uses the hybrid memory mode.
* `cuDSS times`: total time of the analyses, factorizations and solutions of the step.
* `cuDSS factors` (last factorization): nonzero entries of the factors, floating point operations of the factorization, number of pivots reported by cuDSS, memory of the graphics card which cuDSS estimates for the factorization and total memory of the graphics card.

If cuDSS did not factorize in the step (no usable GPU, or fallback from the first system on) only the first two lines are written; without usable GPU `selected=CPU` is followed by the reason.

Notes:

* The double precision performance of workstation graphics cards (e.g. NVIDIA RTX 4000 Ada, RTX PRO 4000 Blackwell) is a small fraction of their single precision performance. Whether cuDSS is faster than PARDISO on the processor of the same workstation depends on the model and the hardware; compare the time of the solver (`solving process` in the `.sta` file) of a few increments for your model.
* cuDSS compiles some of its kernels for the GPU when the first matrix of an analysis is analysed (once per run of numgeo).
* The results of cuDSS are not bitwise reproducible from run to run (parallel summation on the GPU); differences are of the size of the rounding errors of the solution.
* The analysis (ordering) runs on one processor core.

### Singular systems of equations

A direct solver returns a result for every matrix which is not exactly singular. If a part of the model has no sufficient support, the system of equations is singular and the result is of no use as a correction: it contains a rigid body motion of arbitrary size of this part. Typical cases are a wall, pile or foundation which is held by contact only and whose contact points have all opened in the current iteration, and missing boundary conditions.

The solutions of PARDISO and MUMPS are not checked. Whether an increment is accepted is decided by the [convergence criteria](../theory/solution-method/convergence-criteria.md) of the Newton-Raphson iteration: if the following iterations restore the support (e.g. the contact closes again), the increment converges; otherwise it does not converge and is repeated with a smaller time increment.

Both solvers count the pivots of the factorization which are too small: MUMPS the null pivots (the corresponding unknown is set to zero), PARDISO the perturbed pivots. Equations without stiffness and without load (e.g. the nodes of inactive elements) give such pivots in every factorization of the step. If a factorization has more of them than the first factorization of the step, a note is written to the message file (`.msg`):

```
Solver note: MUMPS: 82 null pivots in the factorization (80 in the first factorization of the step). A part of the model may have no sufficient support (boundary conditions, contact).
```

The note is for information only; the solution is used. If an increment with such notes does not converge, check the boundary conditions and the contact of the model (initial contact state, parts which are held by contact only).

If PARDISO reports a zero pivot (PARDISO error -4), the analysis of the matrix is repeated with the current matrix and the system is factorized again. If the error persists, the increment is repeated with a smaller time increment. The message file (`.msg`) then reports

```
Equilibrium iteration 3 of 24
Overall equilibrium: NOT EVALUATED - no solution of the system of equations
Solver note: Pardiso did not deliver a solution of the system of equations: zero pivot in the numerical factorization (Pardiso error -4). The matrix is singular: a part of the model has no sufficient support (boundary conditions, contact).
Solver note: The increment will be retried with a smaller time increment.
```

and the statistics file (`.sta`) marks the increment as `rejected (linear solver)`. Other errors of PARDISO and MUMPS terminate the analysis with an error message. See the [Theory Manual](../theory/solution-method/linear-solver.md#singular-systems-of-equations) for details.

### Reuse of the factorization

```numgeo
*Solver, Pardiso, iterative [, tol=<tolerance>] [, max_iter=<iterations>]
*Solver, MUMPS, iterative [, tol=<tolerance>] [, max_iter=<iterations>]
*Solver, cuDSS, iterative [, tol=<tolerance>] [, max_iter=<iterations>]
```

The numerical factorization of the matrix is by far the most expensive part of a direct solution of three-dimensional models. With the option `iterative` the factorization of a matrix is kept and reused for the systems of the following iterations and increments of the step: these systems are solved with the GMRES method, preconditioned with the existing factors. As long as the matrix has changed little, GMRES converges in a few iterations, each of which costs a forward and backward substitution instead of a factorization. numgeo measures the times and factorizes the current matrix again as soon as this is cheaper, or if GMRES does not converge.

The option does not change the Newton-Raphson iteration (it is not a modified Newton method): every system is solved with its current tangent matrix, to the tolerance `tol` of its residual.

- `iterative`: activates the reuse of the factorization. Without it (or with `direct`) every system is factorized.

- `tol = <tolerance>`: tolerance of the relative residual of GMRES. Default: `tol = 1e-8`. The residual norm is weighted such that all equations (equilibrium and continuity) contribute independently of their units, see the [Theory Manual](../theory/solution-method/linear-solver.md#reuse-of-the-factorization).

- `max_iter = <iterations>`: maximum number of GMRES iterations per system. Default: `max_iter = 30`. If GMRES has not converged after `max_iter` iterations, or earlier if its convergence rate shows that it will not, the matrix is factorized.

At the end of each step the statistics file reports the number of systems, factorizations and GMRES iterations:

```
Linear solver: 78 systems of equations, 13 factorizations, 421 GMRES iterations
```

When to use it: for three-dimensional models, the larger the better. The time saved is that of the factorizations which are avoided; for models with a few 10 000 equations, for plane models and for slice models (one element thick) a factorization costs little more than a few substitutions, and the option brings nothing (but costs nothing either). The memory is that of the direct solver. Measured reductions of the time of the solver with MUMPS (two threads):

| Model | Equations | Systems | Factorizations | Time of the solver |
|-------|-----------|---------|----------------|--------------------|
| Footing on saturated soil, coupled (pore water pressure), Mohr-Coulomb, linear hexahedra | 119 000 | 133 | 5 | -91 % |
| Monopile, hypoplasticity, contact, linear hexahedra | 17 000 | 78 | 13 | -45 % |
| Monopile, solid wall of quadratic elements, Mohr-Coulomb, frictional contact | 53 000 | 90 | 40 | -16 % |
| as before, finer mesh (first loading increment) | 175 000 | 17 | 8 | -36 % |
| Flood protection wall (slice model), coupled (pore water pressure), contact | 16 000 | 347 | 287 | none |

!!! note

    The decision when to factorize depends on measured times. Two runs of the same analysis may therefore factorize different systems; the solutions of the systems agree within the tolerance `tol` but are not identical to the last digit. For the results of an analysis this is a difference like a rounding difference: it remains of the size of `tol` where the Newton-Raphson iteration converges fast (relative differences of the field output below 10$^{-6}$ for the footing and the flood protection wall of the table), and it can grow up to the convergence tolerances of the Newton-Raphson iteration in analyses which are sensitive to rounding (contact states which change from iteration to iteration, loose convergence tolerances, states close to failure). Use the default (direct) solution where bitwise reproducible results are required.

### Simple solver

A very basic (simple) implementation of a direct solver using serial forward substitution. Should only be used for very small systems, e.g. single-element tests. Compared to MUMPS or PARDISO, the overhead is little but efficiency for medium to large systems is drastically worse. To enable the simple solver in a step use `*Solver, simple`.

For models with more than 10 elements, the solver is automatically changed to `Pardiso` and a warning is issued.

### Diagonal solver

A simple implementation of a direct solver for strictly diagonal matrices such as used in explicit dynamics with mass lumping. To enable the diagonal solver in a step, use `*Solver, diagonal`.

---

## Iterative solvers:

!!! warning ""

    Most numgeo calculations feature highly-nonlinear materials with only approximated Jacobians, frictional contacts with opening and closing contact surfaces, coupled two-phase or three-phase flow simulations. The arising linearised systems of equations are notoriously difficult to solve iteratively: no general-purpose preconditioner is reliable for all of them. The direct solvers remain the recommended choice. The options which can be used safely are the [reuse of the factorization](#reuse-of-the-factorization) of the direct solvers (faster, same memory), the solver [GMRES](#gmres) (less memory for large soil-dominated models) and the solver [AMGCL](#amgcl) (large three-dimensional models, also on a graphics card); all fall back to the direct solution of a system for which the iteration does not converge. Any help in providing reliable and efficient iterative solvers is welcome - please get in touch with us!

    An iterative solver which does not converge does not return its last iterate as solution: the increment is repeated with a smaller time increment (`rejected (linear solver)` in the statistics file).

### GMRES

```numgeo
*Solver, GMRES [, droptol=<drop tolerance>] [, fill=<fill factor>] [, restart=<restart>] [, max_iter=<iterations>] [, tol=<tolerance>] [, fallback=pardiso|mumps|no]
```

Restarted GMRES (Saad and Schultz 1986[@saad1986]) preconditioned with an incomplete LU factorization with dual threshold, ILUT (Saad 1994[@saad1994]). The matrix is equilibrated (row and column scaling) and reordered (reverse Cuthill-McKee) before the incomplete factorization; both steps are essential for the badly scaled matrices of coupled analyses. The incomplete factors are reused for the following systems of the step as long as this is cheaper than a new incomplete factorization. See the [Theory Manual](../theory/solution-method/linear-solver.md#iterative-solution-with-an-incomplete-factorization).

The purpose of the solver is to save memory: the complete factors of a direct solver need 10 to 50 times the memory of the matrix for three-dimensional models, the incomplete factors about one to three times. As long as the memory of the direct solver is available, the direct solvers with [reuse of the factorization](#reuse-of-the-factorization) are faster. Measured for a footing on saturated soil (coupled, Mohr-Coulomb, linear hexahedra, two threads):

| Equations | Solver | Peak memory | Time of the solver |
|-----------|--------|-------------|--------------------|
| 119 000 | `MUMPS` | 3.7 GB | 1618 s |
| 119 000 | `MUMPS, iterative` | 3.7 GB | 144 s |
| 119 000 | `GMRES` | 1.4 GB | 313 s |
| 364 500 | `GMRES` | 4.5 GB | 1984 s |

- `droptol = <drop tolerance>`: entries of the factors below `droptol` times the norm of their row are dropped. Default: `droptol = 1e-3`. Smaller values give a more accurate preconditioner (fewer iterations) which needs more memory and time to compute.

- `fill = <fill factor>`: in every row of the factors at most `fill` times the number of entries of the row of the matrix are kept. Default: `fill = 3`. The memory of the factors is bounded by about `fill` times the memory of the matrix.

- `restart = <restart>`: dimension of the Krylov subspace, i.e. number of iterations after which GMRES is restarted. Default: `restart = 100`. GMRES stores `restart` vectors of the size of the system. With an incomplete factorization GMRES typically converges slowly for a number of iterations and fast afterwards; a restart which is too small prevents convergence.

- `max_iter = <iterations>`: maximum number of iterations per system. Default: `max_iter = 300`.

- `tol = <tolerance>`: tolerance of the relative (weighted) residual. Default: `tol = 1e-8`.

Scope and fallback: an incomplete factorization works for models which are dominated by the soil (continuum elements with or without pore pressure degrees of freedom, non-linear constitutive models, contact). It does not work for thin and stiff structures discretised with continuum elements in frictional contact with the soil, e.g. a steel pile wall of quadratic solid elements. A system for which GMRES does not converge within `max_iter` iterations is solved with the direct solver of the version (PARDISO, otherwise MUMPS); the following systems are then solved directly without a further attempt (1, 2, 4, ... up to 32 systems for consecutive failures). The analysis therefore does not depend on the convergence of GMRES, but the direct solver needs its memory when it is called. The first such system of a step is reported with a warning in the `.log` file, and the statistics file reports at the end of each step:

```
Linear solver: 30 systems of equations, 26 incomplete factorizations, 3720 GMRES iterations, 0 systems solved with the direct solver (Pardiso)
```

If most systems of a step are solved with the direct solver, select the direct solver for this model.

Example:

`*Solver, GMRES` (default settings)  
`*Solver, GMRES, droptol=1e-4, fill=5` (more accurate preconditioner)  
`*Solver, GMRES, fallback=mumps` (MUMPS for the systems for which GMRES does not converge)

### AMGCL

```numgeo
*Solver, AMGCL [, device=cpu|gpu] [, tol=<tolerance>] [, max_iter=<iterations>] [, restart=<restart>] [, fallback=pardiso|mumps|no]
```

FGMRES (Saad 1993[@saad1993]) preconditioned with algebraic multigrid (AMG) of the library AMGCL (Demidov 2019[@demidov2019], Demidov 2020[@demidov2020]), on the processor (`device=cpu`, OpenMP) or on a graphics card (`device=gpu`, OpenCL through VexCL, Demidov et al. 2013[@demidov2013]). The solver is meant for large three-dimensional models, from a few 100 000 to a few million equations, whose complete factors do not fit into the memory of a workstation or take too long to compute. The library is part of the numgeo executable; no further file is needed, also not for the GPU.

- `device = cpu | gpu`: where the iteration runs. Default: `device = cpu`. With `gpu` the multigrid hierarchy is built on the processor and moved to the first graphics card with double precision support (the one with the most memory if there are several); the Krylov iteration and the smoothers run on the graphics card. If no such card is found (no OpenCL driver, a card without double precision), or if the estimated memory of the setup exceeds the memory of the card, the processor is used and a warning is written to the `.log` file.

- `tol = <tolerance>`: tolerance of the relative weighted residual, as for [GMRES](#gmres). Default: `tol = 1e-8`.

- `max_iter = <iterations>`: maximum number of FGMRES iterations per system. Default: `max_iter = 300`.

- `restart = <restart>`: dimension of the Krylov subspace of FGMRES. Default: `restart = 50`. FGMRES stores two vectors of the size of the system per iteration of a cycle; on the graphics card this is a large part of the memory.

- `fallback = pardiso | mumps | no`: the direct solver for a system for which AMGCL does not deliver a solution, see below. Default: PARDISO (MUMPS in a version of numgeo without PARDISO). With `no` such a system has no solution and the increment is repeated with a smaller time increment (for models which are too large for a direct solver).

A stiff structure in contact with the soil is not an option of `*Solver`: it is named in its material assignment with [`*Assign material, ..., amgcl=direct`](assign_material.md), see the direct set below.

**Preconditioner.** numgeo determines the role of every equation from the nodes and elements of the model and chooses the preconditioner by a fixed rule; there is nothing to tune:

| Equations of the system | Preconditioner |
|-------------------------|----------------|
| displacements of soil nodes | AMG with the dofs of a node as one block (3 x 3 in 3D, 2 x 2 in 2D), plain aggregation, Chebyshev smoother |
| displacements and pore water pressure or temperature | Schur pressure correction: displacements as above, pore water pressure or temperature with scalar AMG (smoothed aggregation, SPAI-0) |
| displacements and a direct set | Schur complement preconditioner in block triangular form: direct set solved directly (LU), soil by three FGMRES iterations with block AMG |
| displacements, pore water pressure or temperature at every soil node and a direct set | the same with 4 x 4 blocks (3 x 3 in 2D) |
| pore water pressure or temperature only | scalar AMG (smoothed aggregation, SPAI-0) |

A soil node is a node whose degrees of freedom are exactly `U1 U2 [U3]`, `U1 U2 [U3] PW` or `U1 U2 [U3] TT`; the pore water pressure of a node with `PW` only (flow elements) and the temperature of a node with `TT` only are treated as those of a soil node. The temperature of the [u-T elements](element/elements-ut.md) is treated like the pore water pressure: its block of the matrix (heat conduction and heat capacity) is solved with scalar AMG, the coupling with the displacements by the Schur pressure correction. This holds for the mixed and the equal-order u-T elements: both have the degree of freedom `TT` at every node (the mixed elements interpolate it at the nodes which are not corner nodes). All other degrees of freedom (rotations of beam and shell nodes, pore air pressure, ...) and all degrees of freedom of the nodes of the structure form the **direct set**. A thin and stiff structure in soft soil, e.g. a steel pile or wall of solid elements in contact with the soil, defeats the multigrid of the soil (iteration counts above 300); solved directly, it leaves the soil to the multigrid.

**The structure** is named in the material assignment: the elements of every [`*Assign material`](assign_material.md) with the option `amgcl=direct` and their nodes are the structure. numgeo does not guess it, neither from the matrix nor from the materials. Which element sets to assign with `amgcl=direct`:

- **a structure of solid elements in contact with the soil** (pile, wall, footing or lining which is held by a contact pair): all its element sets, also those without a contact surface (pile head, cap, a stiffer section). A part of the structure left out defeats the multigrid as the whole structure would;
- **a structure connected to the soil by shared nodes**: optional. AMGCL converges also without, with more iterations (a concrete pile in soil, 500 times stiffer than the soil: 56 instead of 15 iterations per system, median);
- **the soil**: never. Beams, shells and other structural elements need nothing: their degrees of freedom are in the direct set anyway.

```numgeo
*Assign material, elset=Soil, material=Sand
*Assign material, elset=Pile, material=Steel, amgcl=direct
*Assign material, elset=Pile-Head, material=Steel-Stiff, amgcl=direct
```

The direct set is factorized on the processor in every setup; it is limited to 100 000 equations (a screw pile with 32 130 equations: about 2.5 s per setup). At the first system of every step the `.log` file states the size of the direct set and the material assignments which form it. If the model has contact pairs but no assignment with `amgcl=direct`, a warning is written to the `.log` file. A structure which is not named gives no wrong result: AMGCL does not converge for its systems, and they are solved with the direct solver of the fallback, which costs time and memory.

**Fallback.** A system for which AMGCL does not converge within `max_iter` iterations, whose setup fails (e.g. a singular system) or for which the rule has no preconditioner (e.g. a direct set together with pore water pressure at some soil nodes only) is solved with the direct solver chosen with `fallback` (default PARDISO, otherwise MUMPS), including the [check of its solution](#check-of-the-solution). The direct solver is set up only when it is needed first; a step in which AMGCL solves every system does not allocate it. As for [GMRES](#gmres), the following systems are then solved directly without a further attempt (1, 2, 4, ... up to 32 systems for consecutive failures); if the rule has no preconditioner, all systems of the step are solved directly. The first such system of a step is reported with a warning in the `.log` file. Every solution of AMGCL is checked independently: its weighted residual must not exceed ten times `tol`.

At the end of each step the statistics file reports:

```
Linear solver AMGCL: 124 systems of equations, 124 setups (124 on the GPU), 3336 FGMRES iterations (at most 37 per system), 0 systems solved with the direct solver (Pardiso)
  time of the setups 359.68 s, of the solutions 153.89 s, largest preconditioner 1.10 GB
  equations: 260940 soil displacements, 0 pore pressures, 32130 in the direct set (amgcl=direct: PFAHLSCHAFT.PS_STEIF (STEEL_STIFF), PFAHLSCHAFT.PS_NORMAL (STEEL_NORMAL))
  last setup: GPU; displacements and direct set: Schur complement, block triangular, blocks 3x3, direct set 32130 equations
```

(a screw pile in sand with contact on the shaft and the helices, defined in a part `Pfahlschaft`: the material assignments of the shaft, which carries the contact surfaces, and of the stiffer pile head, which has none, are marked with `amgcl=direct`; the direct solver of the fallback, not needed here, would have been PARDISO).

**When to use it.** For three-dimensional models above about 200 000 equations, and on a graphics card. Measured per system on a workstation with 32 cores (AMD Threadripper PRO 9975WX) and an NVIDIA RTX PRO 4000 Blackwell (24 GB); time of the direct solver, or setup + solution of AMGCL (median of the analysis); memory: peak of the numgeo process, and the preconditioner on the graphics card:

| Model | Equations | Iterations | PARDISO | AMGCL, processor | AMGCL, graphics card |
|-------|-----------|------------|---------|------------------|----------------------|
| Footing, hypoplastic sand | 285 099 | 44 to 58 | 17.9 s, 11.6 GB | 0.4 + 3.4 s, 3.1 GB | 0.6 + 0.6 s, 3.3 GB + 0.6 GB |
| Footing, saturated sand (u-p), geostatic step | 380 132 | 56 | 43.5 s, 20.1 GB | 0.7 + 7.1 s, 5.4 GB | 1.0 + 1.3 s, 6.1 GB + 1.6 GB |
| Screw pile with contact (direct set: 32 130) | 293 070 | 10 to 37 | 7.8 s, 10.2 GB | 2.4 + 2.8 s | 2.5 + 1.1 s, 3.6 GB + 1.1 GB |
| Box pile with contact (direct set: 16 632) | 414 678 | 52 to 90 | about 50 s, 18.1 GB | - | 2.9 + 4.0 s, 6.8 GB + 2.2 GB |
| Footing, geostatic step | 1 075 275 | 72 to 73 | 303.5 s, 63.9 GB  | 1.2 + 19.7 s, 11.8 GB | 1.7 + 3.1 s, 12.6 GB + 2.4 GB |
| Footing, geostatic step | 2 193 075 | 85 to 88 | does not fit (about 160 GB) | - | 3.7 + 7.3 s, 25.6 GB + 5.0 GB |
| Heated pile in soil, temperature (u-T), pile of soil material | 380 132 | 33 to 66 | 46.6 s, 20.6 GB | 0.7 + 5.1 s, 6.4 GB | 1.1 + 0.9 s, 6.7 GB + 1.8 GB |
| Heated concrete pile in soil (u-T, direct set: 704) | 380 132 | 13 to 22 | 41.4 s, 20.6 GB | 0.8 + 5.7 s, 6.7 GB | 1.1 + 0.9 s, 7.2 GB + 2.0 GB |

The setup is repeated for every system; with a direct set it is mostly the factorization of the structure on the processor. The Newton-Raphson iteration is that of the direct solver: the footings took the same increments and iterations as with PARDISO, the loading step of the screw pile the same 15 increments with 109 instead of 110 iterations; the results agree within the tolerance of the Newton-Raphson iteration (largest difference of the reaction forces of the footing with 285 099 equations: 3 · 10$^{-4}$ of the largest value). In linear analyses (e.g. thermal elasticity) every increment takes one Newton-Raphson iteration more than with a direct solver: the direct solution is accepted after the first iteration by the absolute residual criterion, the solution of AMGCL with its residual of the order of `tol` is not (heated pile: 30 instead of 20 systems; the analysis took 87 s on the graphics card and 843 s with PARDISO).

For smaller models and for plane models the direct solvers are faster: a plane model needs many more AMG iterations (a static system of 547 000 equations: 437 iterations, MUMPS solves it in seconds), and below about 100 000 equations a factorization takes less than a second (25 000 equations: 0.13 s with PARDISO, 0.03 + 0.06 s with AMGCL on the processor, 0.06 + 0.11 s on the graphics card). See also the tutorial [Large models: PARDISO, GMRES and AMGCL](../tutorial/advanced/large-models.md).

Limits: degrees of freedom other than displacements, pore water pressure and temperature (unsaturated analyses with pore air pressure, models of structural elements) go to the direct set or, if it is too large, to the direct solver; nothing is gained for such models. The setup of the preconditioner is repeated for every system (no reuse over the Newton-Raphson iterations). GPU: an OpenCL 1.2 driver with double precision is required (NVIDIA: the regular graphics driver; no CUDA installation is needed). The first system of an analysis on the GPU takes about 0.3 s longer (the driver compiles the kernels). See the [Theory Manual](../theory/solution-method/linear-solver.md#algebraic-multigrid-amgcl).

Example:

`*Solver, AMGCL` (processor, default settings)  
`*Solver, AMGCL, device=gpu` (graphics card)  
`*Solver, AMGCL, device=gpu, fallback=mumps` (graphics card; MUMPS for the systems which AMGCL does not solve)

### LIS solver library

LIS (Library of Iterative Solvers for linear systems, Pujii et al. (2005)[@pujii2005], Katekemori et al. (2005)[@kotakemori2005a], Katekemori et al. (2008)[@kotakemori2008a], Nishida (2010)[@nishida2010a]) is a parallel software library for solving discretized linear equations and eigenvalue problems that arise in the numerical solution of partial differential equations using iterative methods.

!!! note "Preprocessing"

    Note that before each solve with LIS we preprocess the s.o.e. using [MUMPS](#mumps) to permute the matrix to a zero-free diagonal perform matrix scaling.

The keyword to activate the `LIS` solver reads:

`*Solver, LIS = <iterative solver options>`

The sub-keyword `<iterative solver options>` is used to define the iterative solver and the preconditioner. Unlike the usual numgeo convention, this command requires the definition of a string following the LIS-convention. Be careful, blanks do matter! Available solvers and preconditioners as well as their LIS-options are depicted in Figure 5.3 and Figure 5.4. The following example displays how to define a GMRES solver with the standard restart value (40). As a preconditioner, an incomplete LU factorisation with a fill in level of 2:

`*Solver, LIS=$-i gmres -p ilu -ilu fill 2$`

If the options contain no tolerance (`-tol`), numgeo sets `-tol 1.0e-6`. If the solver of the LIS library does not converge, the increment is repeated with a smaller time increment.

The LIS library gives access to more than 20 different iterative solvers and 10 preconditioners. A summary is given in the following tables:

* Solvers:

    | Solver         | Option                  | Auxiliary Options                                  |
    |----------------|-------------------------|----------------------------------------------------|
    | CG             | `-i {cg|1}`             |                                                    |
    | BiCG           | `-i {bicg|2}`           |                                                    |
    | CGS            | `-i {cgs|3}`            |                                                    |
    | BiCGSTAB       | `-i {bicgstab|4}`       |                                                    |
    | BiCGSTAB(l)    | `-i {bicgstabl|5}`      | `-ell [2]` — The degree *l*                        |
    | GPBiCG         | `-i {gpbicg|6}`         |                                                    |
    | TFQMR          | `-i {tfqmr|7}`          |                                                    |
    | Orthomin(m)    | `-i {orthomin|8}`       | `-restart [40]` — The restart value *m*            |
    | GMRES(m)       | `-i {gmres|9}`          | `-restart [40]` — The restart value *m*            |
    | Jacobi         | `-i {jacobi|10}`        |                                                    |
    | Gauss-Seidel   | `-i {gs|11}`            |                                                    |
    | SOR            | `-i {sor|12}`           | `-omega [1.9]` — The relaxation coefficient ω (0 < ω < 2) |
    | BiCGSafe       | `-i {bicgsafe|13}`      |                                                    |
    | CR             | `-i {cr|14}`            |                                                    |
    | BiCR           | `-i {bicr|15}`          |                                                    |
    | CRS            | `-i {crs|16}`           |                                                    |
    | BiCRSTAB       | `-i {bicrstab|17}`      |                                                    |
    | GPBiCR         | `-i {gpbicr|18}`        |                                                    |
    | BiCRSafe       | `-i {bicrsafe|19}`      |                                                    |
    | FGMRES(m)      | `-i {fgmres|20}`        | `-restart [40]` — The restart value *m*            |
    | IDR(s)         | `-i {idrs|21}`          | `-irestart [2]` — The restart value *s*            |
    | IDR(1)         | `-i {idr1|22}`          |                                                    |
    | MINRES         | `-i {minres|23}`        |                                                    |
    | COCG           | `-i {cocg|24}`          |                                                    |
    | COCR           | `-i {cocr|25}`          |                                                    |

* Preconditioners

    | Preconditioner        | Option            | Auxiliary Options                                                                                                      |
    |-----------------------|-------------------|------------------------------------------------------------------------------------------------------------------------|
    | None                  | `-p {none|0}`     |                                                                                                                        |
    | Jacobi                | `-p {jacobi|1}`   |                                                                                                                        |
    | ILU(k)                | `-p {ilu|2}`      | `-ilu_fill [0]` — The fill level *k*                                                                                   |
    | SSOR                  | `-p {ssor|3}`     | `-ssor_omega [1.0]` — The relaxation coefficient ω (0 < ω < 2)                                                         |
    | Hybrid                | `-p {hybrid|4}`   | `-hybrid_i [sor]` — The linear solver<br>`-hybrid_maxiter [25]` — The maximum number of iterations<br>`-hybrid_tol [1.0e-3]` — The convergence    tolerance<br>`-hybrid_omega [1.5]` — The relaxation coefficient ω of the SOR (0 < ω < 2)<br>`-hybrid_ell [2]` — The degree *l* of the BiCGSTAB(l)<br>`-hybrid_restart [40]` — The restart values of the GMRES and  Orthomin |
    | I+S                   | `-p {is|5}`       | `-is_alpha [1.0]` — The parameter α of *I + αS(m)*<br>`-is_m [3]` — The parameter *m* of *I + αS(m)*                     |
    | SAINV                 | `-p {sainv|6}`    | `-sainv_drop [0.05]` — The drop criterion                                                                              |
    | SA-AMG                | `-p {saamg|7}`    | `-saamg_unsym [false]` — Select the unsymmetric version (matrix must be symmetric)<br>`-saamg_theta [0.05\|0.12]` — The drop criterion \( a_{ij}^2 \leq \theta^2 |a_{ii}| \,|a_{jj}| \) (symmetric or unsymmetric) |
    | Crout ILU             | `-p {iluc|8}`     | `-iluc_drop [0.05]` — The drop criterion<br>`-iluc_rate [5.0]` — The ratio of the maximum fill-in                       |
    | ILUT                  | `-p {ilut|9}`     |                                                                                                                        |
    | Additive Schwarz      | `-adds true`      | `-adds_iter [1]` — The number of iterations                                                                            |

* Additional settings:

    | Option               | Description                                                                                                                                    |
    |----------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
    | `-maxiter [1000]`    | The maximum number of iterations                                                                                                               |
    | `-tol [1.0e-12]`     | The convergence tolerance *tol*                                                                                                                |
    | `-tol_w [1.0]`       | The convergence tolerance *tol_w*                                                                                                              |
    | `-print [0]`         | The output of the residual history:<br>`-print {none\|0}` — None<br>`-print {mem\|1}` — Save the residual history<br>`-print {out\|2}` — Output to standard output<br>`-print {all\|3}` —  Save the residual history and output it to standard output |
    | `-scale [0]`         | The scaling (result overwrites the original matrix and vectors):<br>`-scale {none\|0}` — No scaling<br>`-scale {jacobi\|1}` — Jacobi scaling \(D^{-1}Ax = D^{-1}b\), where \(D\) is the    diagonal of \(A\)<br>`-scale {symm_diag\|2}` — Diagonal scaling \(D^{-1/2}AD^{-1/2}x = D^{-1/2}b\), where \(D^{-1/2}\) has \(1/\sqrt{a_{ii}}\) on the diagonal |
    | `-initx_zeros [1]`   | The behaviour of the initial vector \(x_0\):<br>`-initx_zeros {false\|0}` — Components given by argument `x` in `lis_solve()`<br>`-initx_zeros {true\|1}` — All components set to 0 |
    | `-conv_cond [0]`     | The convergence condition:<br>`-conv_cond {nrm2_r\|0}` — \(\|b - Ax\|_2 \le tol \cdot \|b - Ax_0\|_2\)<br>`-conv_cond {nrm2_b\|1}` — \(\|b - Ax\|_2 \le tol \cdot \|b\|_2\)<br>`-conv_cond     {nrm1_b\|2}` — \(\|b - Ax\|_1 \le tol_w \cdot \|b\|_1 + tol\) |
    | `-omp_num_threads t` | Number of threads (*t* represents the maximum number of threads)                                                                               |
    | `-storage [0]`       | The matrix storage format                                                                                                                       |
    | `-storage_block [2]` | The block size of the BSR and BSC formats                                                                                                       |
    | `-f [0]`             | Precision of the linear solver:<br>`-f {double\|0}` — Double precision<br>`-f {quad\|1}` — Double-double (quadruple) precision                  |

---

## External solver

Use this option to interface external solvers to numgeo. For the external solver, an additional executable is required. This executable has to be placed in the same directory as the numgeo executable.

```numgeo 
*Solver, external, exe=$executable name$ [mpi=<n processors> omp=<n threads> oneAPI arg=$....$]
``` 
The (sub)keywords are as follows:

- `external`: tells numgeo to use an external executable to solve the linear system.

- `exe=$executable name$`: specify the name of the external executable including file ending.

- `[mpi=<n processors>]`: specify the number of processors to be used. Notice that:

    - for `mpi=1`, the use of mpi is disabled and the external executable is launched using `./executable name`. This is the default.

    - for `mpi=n` (with n $>$ 1), the executable is launched using `mpirun -n executable name`

- `[omp=<n threads>]`: specify the number of (omp) threads to be used. Notice that:

    - for `[omp=1]`, the use of omp is disabled. This is the default.

    - for `[omp=n]` (with n $>$ 1), the executable is launched using `export OMP_NUM_THREADS=n`

- `[oneAPI]`: if present, the oneAPI environment will be initialised before launching the external program

- `[arg=$....$]`: additional arguments that will be passed to the external program. These values are solver/program dependent.

**Example 1:** Use the AMGCL library to solve the system of equations. For this, an external program `numgeo-amgcl.exe` is called. Only openMP threading with 16 threads is used. As additional options we use a `Ruiz` scaling of the matrix. The outputname of the simulation was set to `sim-example-1`. The numgeo reads:

`*Solver, external, exe=$numgeo-amgcl.exe$, omp=16, arg=$-s ruiz -nomp 16$`

which produces the following command line call

```shell
set OMP_NUM_THREADS=16
.\numgeo-amgcl.exe -f sim-example-1 -s ruiz -nomp 16
```

Mind the `-f sim-example-1`. Regardless of any optional arguments `[arg=$....$]` provided in the input file, numgeo always passes as a first argument the filename of the current simulation starting with a `-f`.

!!! note "Existing interfaces to external solvers"

    Interfaces to some external solvers have already been developed and can be freely downloaded from <https://github.com/j-machacek/numgeo-external-solvers>:

    - `numgeo-mumps-mpi`: MPI version of the [MUMPS](#mumps) solver

    - `numgeo-ilupack`

    - `numgeo-pastix`

Example:  
`*Solver, external, exe=$numgeo-mumps-mpi$, mpi=4, omp=2`

The files which numgeo writes for the external solver (`numgeo-ext-lhs-<job>.numgeo`, ...) are rewritten for every system of equations.

---

## Deactivate solver

Use this option to omit using a solver. However, be aware that in this case the system of equation is not solved at all, i.e. no improvement to the initial guess will be calculated (see [Theory Manual](../theory/solution-method/index.md)). This option should best be used in combination with `maxiter=0` (see [*Step](./step/index.md) definition). Be aware of the consequences! To deactivate the solving stage in a step of your analysis, use `*Solver, None`

---
