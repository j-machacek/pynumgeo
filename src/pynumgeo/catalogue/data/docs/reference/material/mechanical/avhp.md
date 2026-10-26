# Anisotropic visco-hypoplasticity (AVHP)

Anisotropic Visco-Hypoplasticity (AVHP) as proposed by Niemunis & Grandas (2009)[@NiemunisGrandas09]. The numgeo keyword reads:

```numgeo 
*Mechanical = AVHP
e_0(p=100) (-), lambda (-), kappa (-), I_v (-), D_r (-), varphi_c [rad], C_1 (-), C_2 (-)
C_3 (-), K^w(F/A)
```

!!! Info
    The AVHP model[@NiemunisGrandas09] was developed and originally implemented by A. Niemunis, C. Grandas and F. Prada. For allowing us to incorporate the model in numgeo, we sincerely thank them.