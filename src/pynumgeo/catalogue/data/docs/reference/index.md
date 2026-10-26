# Reference

The authors acknowledge that naming conventions and input style formats for **numgeo** are based on those used by Abaqus[^1], a proprietary, general purpose finite element code.

The **numgeo** input file consists of two sections: a model-definition section describing the geometry and boundary conditions of the problem, and one or more [step definitions](./step/index.md) defining the loads:

<div align="center">
    <b>input_file_name.inp</b>
    <br><br>
    <div style="border: 1px solid; padding: 15px;">
        <span style="color:red;">**</span> Add a short description of the problem.<br>
        <span style="color:red;">**</span> This has no effect on the output<br>
        <span style="color:red;">**</span> and only serves for identification<br><br>
        
        <div style="background-color: grey; color: white; padding: 40px; text-align: center;">
            Model definition
        </div>
        <br>
        <div style="background-color: grey; color: white; padding: 40px; text-align: center;">
            Step definition(s)
        </div>
        <br>
        <span style="color:red;">*</span> End Input<br><br>
    </div>
</div>

All input is preceded by keywords, which all start with an asterisk (<span style="color:red;">*</span>), indicating the kind of data that follows. Detailed information on every keyword is given in the subsequent sections. The following provides a brief description of the [model-definition](#model-definition) section. Step commands are documented under [Step](./step/index.md).

!!! note "Upper vs lower case"

    The **numgeo** input file is **case-insensitive** - use upper and lower cases as you wish.

!!! note "Blanks and tab stops"

    **Blanks** are ignored in the **numgeo** input file - use them to clarify your input file as you wish. Caution:  **tab stops** are not automatically translated to blanks and **should always be avoided**.

!!! note "Comments"

    Use **comments** and **blank lines** to clarify your input file - both will be ignored by **numgeo**. **Comments** start with <span style="color:red;">**</span> and can be placed at the beginning of a line or somewhere within a line: 

    * Example 1:
    
        <span style="color:red;"> ** This is a line comment. The entire line will be ignored.</span>

    * Example 2:

        *Amplitude, name=name1, type=tabular <span style="color:red;"> ** This is an inline comment after a valid keyword </span>

## Model definition 

The model definition Section starts at the beginning of the file and ends at the occurrence of the first <span style="color:red;">*step</span> statement.

The first statement of the model definition is the <span style="color:red;">*node</span> statement (see [Node](./node.md)), followed by the node definitions.

Next, the elements are defined using the <span style="color:red;">*element</span> keyword (see [Element](./element/index.md)), listing for each element its type, which nodes belong to it, and in what order. Multiple <span style="color:red;">*node</span> and <span style="color:red;">*element</span> statements are possible.

Nodes and elements can be grouped into sets using the keywords <span style="color:red;">*nset</span> (see [Nset](./nset.md)) and <span style="color:red;">*elset</span> (see [Elset](./elset.md)), respectively.

Next, a material and other properties are assigned to an element set using <span style="color:red;">*solid section</span> (see [Assign material](./assign_material.md)). The assigned properties then have to be defined; in this example, a material is defined using the <span style="color:red;">*material</span> keyword. Other properties, such as soil-water-retention curves, may follow. See [Material](./material/index.md) for details.

The <span style="color:red;">*Amplitude</span> keyword is optional. Initial conditions depend on the analysis; u-T solid elements require an explicit [initial temperature](./initial-conditions/temperature.md). More details are given under [Amplitude](./amplitude.md) and [Initial conditions](./initial-conditions/index.md).

Boundary conditions (<span style="color:red;">*Boundary</span>, see [Boundary conditions](./boundary-conditions/boundary.md)) may be omitted from the model-definition section, but must then be given in the first step definition.

<div style="border: 1px solid black; padding: 15px;">
    <span style="color:red;">*Node</span><br>
    n1, x1, y1, z1<br>
    n2, x2, y2, z2<br>
    &hellip;<br>
    <span style="color:red;">*Element, type = ...</span><br>
    e1, n1, n2, n3, ...<br>
    &hellip;<br>
    <span style="color:red;">*Nset, name = ...</span><br>
    &hellip;<br>
    <span style="color:red;">*Elset, name = ...</span><br>
    &hellip;<br>
    <span style="color:red;">*Solid Section, ...</span><br>
    &hellip;<br>
    <span style="color:red;">*Material, name = ...</span><br>
    &hellip;<br>
    <span style="color:red;">[Other property definitions]</span><br>
    &hellip;<br>
    <span style="color:red;">*Amplitude, name = ...</span><br>
    &hellip;<br>
    <span style="color:red;">*Initial conditions, ...</span><br>
    &hellip;<br>
    <span style="color:red;">*Boundary</span>
</div>

<h2>Model definitions using parts and instances</h2>

<div style="display: flex;">
  <div style="width: 35%;">
    <div style="border: 1px solid black; padding: 10px;">
      <span style="color: red;">*Part, name = ...</span><br>
      <span style="color: red;">*Node</span><br>
      n<sub>1</sub>, x<sub>1</sub>, y<sub>1</sub>, z<sub>1</sub><br>
      n<sub>2</sub>, x<sub>2</sub>, y<sub>2</sub>, z<sub>2</sub><br>
      &vellip;<br>
      <span style="color: red;">*Element, type = ...</span><br>
      e<sub>1</sub>, n<sub>1</sub>, n<sub>2</sub>, n<sub>3</sub>, ...<br>
      &vellip;<br>
      <span style="color: red;">*Nset, name = ...</span><br>
      &vellip;<br>
      <span style="color: red;">*Elset, name = ...</span><br>
      &vellip;<br>
      <span style="color: red;">*Solid section, ...</span><br>
      &vellip;<br>
      <span style="color: red;">*End part</span><br>
      **<br>
      ** - - - - Add a second part - - - -<br>
      **<br>
      <span style="color: red;">*Assembly, name = ...</span><br>
      <span style="color: red;">*Instance, name = ..., part = ...</span><br>
      x<sub>1</sub>, y<sub>1</sub>, z<sub>1</sub><br>
      x<sub>1</sub>, y<sub>1</sub>, z<sub>1</sub>, x<sub>2</sub>, y<sub>2</sub>, z<sub>2</sub>, &theta;<br>
      &vellip;<br>
      <span style="color: red;">*End Instance</span><br>
      **<br>
      ** - - - - Add a second instance - - - -<br>
      **<br>
      <span style="color: red;">*End Assembly</span><br>
    </div>
  </div>

  <div style="width: 5%;"></div>

  <div style="width: 60%;">
    <p>For models with different geometrical instances, a subdivision into parts is often beneficial.</p>
    
    <p>A part definition is started using the <span style="color: red;">*Part</span> statement. Each part is assigned a name. Within the part definition section, nodes, elements, sets and solid sections can be defined. The part definition is closed using the <span style="color: red;">*End part</span> statement. The number of defined parts is not restricted.</p>
    
    <p>Once parts have been defined, an assembly is defined using <span style="color: red;">*Assembly</span>. Again, the assembly is given a name. Within the assembly, instances are defined. Instances refer to the previously defined parts <span style="color: red;">Part = ...</span>. The nodes of an instance can be moved by definition of a vector x<sub>1</sub>, y<sub>1</sub>, z<sub>1</sub> in the line following the instance definition. They can also be rotated around the vector which is formed by the line connecting x<sub>1</sub>, y<sub>1</sub>, z<sub>1</sub> and x<sub>2</sub>, y<sub>2</sub>, z<sub>2</sub> by the angle &theta;. Each defined part has to be defined as an instance in the assembly.</p>
    <p>The assembly is finished using the <span style="color: red;">*End assembly</span> statement.</p>
    <p>Sets that have been defined in the part section can be used in the step definition if the name of the instance is added with a point before the set name, e.g. instance-1.set-1.</p>
    <p>Note that no 'internal' set definition exists. Thus, every set defined in the assembly can be used in the step environment. Note in addition that it is prohibited to have the same set name twice even if they are defined in different parts.</p>
  </div>
</div>

[^1]: For more information visit: https://www.3ds.com/de/produkte-und-services/simulia/produkte/abaqus/
