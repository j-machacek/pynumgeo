# Mechanical - Mechanical constitutive model

```numgeo 
*Material, ... 
... 
*Mechanical = <mechanical model> 
<parameter 1>, ... , <parameter n> 
...
``` 

Set this parameter equal to the mechanical model to be used for the calculation of stresses. The subsequent lines `<parameter 1>, ... , <parameter n>` depend on the model chosen. This parameter is mandatory. The different "mechanical" models available in numgeo are summarised in the table below and described in the subsections accessible through the links in the table or the navigation bar on the left.

**Model** | **Section** 
---|---
[Linear Elasticity](./linear_elasticity.md) | Linear elastic model
[Thermal elasticity](./thermal_elasticity.md) | Isotropic linear thermoelasticity with an explicit temperature history
[Barotropic Elasticity](./barotropic_elasticity.md) | Barotropic (stress dependent) and pyknotropic (void ratio dependent) elastic model
[Bathytropic Elasticity](./bathytropic-elasticity.md) | Bathytropic (depth dependent) elastic model
[Bingham](./bingham.md) | Elasto-viscoplastic model with a yield stress and a plastic viscosity (Bingham fluid)
[Matsuoka Nakai](./matsuoka_nakai.md) | Linear elastic - perfectly plastic model with Matsuoka-Nakai yield and failure criterion
[Mohr-Coulomb](./mohr_coulomb.md) | Linear elastic - perfectly plastic model with Mohr-Coulomb yield and failure criterion available in two different implementations 
**Advanced constitutive models** | 
[AVHP](./avhp.md) | Anisotropic Visco-Hypoplasticity (AVHP) as proposed by Niemunis & Grandas (2009)[@NiemunisGrandas09]
[AVISA](./avisa.md) | Anisotropic Viscous ISA model after Tafili & Triantafyllidis (2020)[@Tafili20b]
[BC-HYPO-IGS-SF](./bc-hypo-igs-sf.md) | Bio-Cemented Hypoplasticity + Intergranular Strain + Semi-Fluidized State and Fabric Change Effects
[Hardening soil (MN)](./hardening_soil_MN.md) | Hardening soil model with Matsuoka–Nakai (MN) failure surface
[Hardening soil (MN) Bricks](./hardening_soil_MN_bricks.md) | Hardening soil model with Matsuoka–Nakai (MN) failure surface and small strain (Bricks) extension
[Hypo-Clay](./hypo-clay.md) | Hypoplastic constitutive model for clays proposed by Masin (2005)[@masin2005]
[Hypoplasticity + Generalized Intergranular Strain](./hypoplasticity_gis.md) | Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with generalized intergranular strain anisotropy extension (Mugele et al. (2024)[@mugele2024])
[Hypoplasticity + Intergranular Strain](./hypoplasticity_igs.md) | Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with intergranular strain extension (Niemunis and Herle, 1997)[@niemunis1997]
[Hypoplasticity + Intergranular Strain Anisotropy](./hypoplasticity_isa.md) | Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with intergranular strain anisotropy extension (Fuentes et al., 2020)[@fuentes2020]
[Hypoplasticity + ISA-SF](./hypoplasticity_isa-sf.md) | Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with intergranular strain anisotropy (ISA) and semi-fluidized state (SF) extension (Tafili et al., 2024)[@tafili2024hypoplastic]
[Sanisand](./sanisand.md) | Critical state compatible bounding surface plasticity model according to Dafalias & Manzari (2004)[@dafalias2004] available in two different implementations
[Sanisand-F](./sanisand_f.md) | Extension of the Sanisand model[@dafalias2004] to incorporate effects of fabric by Petalas et al (2019)[@petalas2020]
[Sanisand-MSf](./sanisand_msf.md) | Extension of the Sanisand model[@dafalias2004] to incorporate effects of memory surface and semi-fluidized states according to Yang et al. (2022)[@yang2022]
[Ta-Ger](./ta-ger.md) | Elastoplastic sand model based on the Ta-Ger formulation of Tasiopoulou and Gerolymos [@tasiopoulou2016,@tasiopoulou2016a]
**High-cycle accumulation models** | 
[HCA for Sand](./hca-sand.md) | High-Cycle Accumulation (HCA) model for sand as proposed by Niemunis et al. (2005)[@NiemunisWichtmann05_model]. The current implementation allows coupling with the following models: Hypo-IGS, Hypo-ISA, Sanisand, Linear Elasticity

---

## References

