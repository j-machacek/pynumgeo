# Minimum pressure:

```numgeo 
*Material, ...
*Min pressure
<minimum pressure>
``` 

This parameter is used to correct small effective pressures in case
barotropic constitutive models are used. Set this pressure to the
minimum allowed pressure (mechanical sign convention, i.e. give a
negative value). This parameter should be set for the following
materials:

| **Model** | **Reference** |
|---|---|
| Hypoplasticity + Intergranular Strain | [Hypoplasticity + IGS](./mechanical/hypoplasticity_igs.md) |
| Hypoplasticity + Intergranular Strain Anisotropy | [Hypoplasticity + ISA](./mechanical/hypoplasticity_isa.md) |
| Sanisand | [Sanisand](./mechanical/sanisand.md) |
| Modified Cam Clay | [Modified Cam Clay](./mechanical/modified-cam-clay.md) |
| Anisotropic Viscous ISA | [AVISA](./mechanical/avisa.md) |
| High Cycle Accumulation model for sand (coupled with Hypoplasticity + Intergranular Strain or Sanisand) | [HCA-Sand](./mechanical/hca-sand.md) |
| High Cycle Accumulation model for clay | [HCA-Clay](./mechanical/hca-clay.md) |
