# Initial conditions, Type=state variables

```numgeo 
*Initial conditions, Type=state variables , <option>
<element set>, <ic parameter 1>, ..., <ic parameter n>
```

Specify the initial values of arbitrary state variables (needed by more advanced constitutive models) at the integration points of an element set `<element set name>`. Use one of the following `options`:

* [Default](#default)
* [Spatial data](#spatial-data) - to provide the initial values as spatial tabular data stored in a text file
* [User](#user) - to initialise the state variables using a user defined subroutine
* [Fluctuation](#fluctuation) - to define a spatially varying field of initial values

!!! warning ""

    The element set `<element set name>` must have been previously used to define a solid section (or used in the `*Assign material` keyword).

---

## Default

Use this option to specify the initial `<value>` of an arbitrary state variable `<state variable name>`. The command line takes the following form:

```
*Initial Conditions, Type = state variables, default
<element set name>, <state variable name>, <value>
```

Example:

```
*Initial Conditions, Type = state variables, default 
layer-1, void_ratio, 0.9
```

---

## Spatial data

Use this option to specify the initial `<value>`s of an arbitrary state variable `<state variable name>` for all integration points of element set `<element set name>` by means of comma separated spatial data. The data consists of a set of spatial positions and associated initial values. Assignment of the given spatial data to the integration points is performed by means of a nearest neighbour search. 

The command line takes the following form:

```
*Initial Conditions, Type = state variables, *-data
<element set name>, <state variable name>, <file name>
```

The following options are available:

- `x-data`, `y-data` or `z-data` (only for 3D simulations)

    The spatial location of the initial values only depends on one coordinate, `x`, `y` or `z`. Only this coordinate will be considered in the nearest neighbour search, e.g. by specifying `y-data`, only the y-coordinate of the integrations points will be used to identify the nearest point from the data given in the text file. The text file is expected to be formatted as follows:

    ```
    1 npoints, <number of spatial points>
    2 descriptive header line, will be ignored by numgeo
    3 coordinate(1) value(1)
    4 coordinate(2) value(2)
    5 coordinate(3) value(3)
    6 ... ...
    ```

    where `<number of spatial points>` in line `1` is the number of spatial points describing the initial field. Data is separated by a `blank` or `tab`. The first number in each line denotes the line number in the file and is not (!) part of an actual text file.

- `xy-data` (only for 2D simulations)

    The spatial location of the initial values only depends on all directions of space, i.e. x- and y-coordinates for `xy-data`. The euclidean distance between the integration points and the spatial points from the text file will be considered in the nearest neighbour search. The text file is expected to be formatted as follows:

    ```
    1 npoints, <number of spatial points>
    2 descriptive header line, will be ignored by numgeo
    3 x-coordinate(1) y-coordinate(1) value(1)
    4 x-coordinate(2) y-coordinate(2) value(2)
    5 x-coordinate(3) y-coordinate(3) value(3)
    6 ... ... ...
    ```

    Data is separated by a `blank` or `tab`. The first number in each line denotes the line number in the file and is not (!) part of an actual text file.

- `xyz-data` (only for 3D simulations) 

    Same as `xy-data` but for 3D models, thus considering x-, y- and z-coordinates. The text file is expected to be formatted as follows:

    ```
    1 npoints, <number of spatial points>
    2 descriptive header line, will be ignored by numgeo
    3 x-coordinate(1) y-coordinate(1) z-coordinate(1) value(1)
    4 x-coordinate(2) y-coordinate(2) z-coordinate(2) value(2)
    5 x-coordinate(3) y-coordinate(3) z-coordinate(3) value(3)
    6 ..., ..., ..., ...
    ```

    Data is separated by a `blank` or `tab`. The first number in each line denotes the line number in the file and is not (!) part of an actual text file.

Example:

```
*Initial Conditions, Type = state variables, xy-data
layer-1, void_ratio, random-field-e.txt
```

with a text file `random-field-e.txt` with the following content:

```
1 npoints, 12078
2 X1 X2 phi
3 8.33333e-02 3.33333e-01 2.51899e+01
4 8.33333e-02 8.33333e-02 2.50735e+01
5 3.33333e-01 8.33333e-02 2.51069e+01
6 ... ... ...
12080 3.64465e+01 8.39160e+00 2.16472e+01
```

---

## User

Use this option to specify the use of a user-defined subroutine to define the initial value of arbitrary state variables described further [here](../user/index.md).

```
*Initial Conditions, Type = state variables, user
<element set name>
```

Example:

```
*Initial Conditions, Type = state variables, default
layer-1
```

---

## Fluctuation

Use this option to specify a spatially fluctuating but correlated distribution using Markov's algorithm in an isotropic fashion. A range of the state variable has to be defined using `<value max>` and `<value min>`. In addition, one or multiple values for `<correlation length>` are to be given, which defines the zone of which values are correlated. The correlation length should be at least larger than the distances of the integration
points in order to be active. The correlation length has the unit of length. If multiple values for `<correlation length>` are provided they are interpreted as `<correlation length in x - direction>,  <correlation length in y - direction>, <correlation length in z - direction>`.

```
*Initial Conditions, Type = state variables, fluctuation
<element set name>, <state variable name>, <value max>, <value min>, <correlation length>, [ <correlation length in y - direction>, <correlation length in z - direction>]
```
 
<p align="center" markdown>
  <img src="./images/void_ratio_bucket_fluc.png" alt="figure 1" width="100%"/>
  <em> Figure 1. Effect of `<correlation length>` in defining a spatially fluctuating initial field of `void_ratio` being the void ratio used by the constitutive model variants </em>
</p>

The influence of `<correlation length>` is demonstrated in Fig. 1. The following definition was used to generate the last field:
  
```
*Initial Conditions, Type = state variables, fluctuation
layer-1, void_ratio, 0.9, 0.6, 0.005
```

Note that the elements have a size of only 0.002 m in this model for why the value of the correlation length is rather low.


<p align="center" markdown>
  <img src="./images/void_ratio_strip_foundation_fluc_ly10_lx.png" alt="figure 2" width="100%"/>
  <em> Figure 2. Effect of different values of `<correlation length>` in x- and y-direction in defining a spatially fluctuating initial field of `void_ratio`. The right side depicts a ten-times larger value in y-direction.  </em>
</p>

The influence of different values of `<correlation length>` in x- and y-direction is demonstrated in Fig. 2. The following definition was used to generate the last field:

```
*Initial Conditions, Type = state variables, fluctuation
layer-1, void_ratio, 0.9, 0.6, 1, 10
```
