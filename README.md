# Genesis QCD datasheet project: Research Object Architecture

## About

This repository supports experimentation with Reasearch Objects,
being developed as a tool to advance the Genesis QCD data project.
One of the goals is to leverage existing standards and tools, such
as [LinkML](https://linkml.io/).

The folder **ro** contains sample YAML data intended for experimentation.

## Tools

One of the advantages of frameworks like _LinkML_ is that they are
supported by corresponding software ecosystems. In case of _LinkML_,
one such toolkit is the Python **linkml** package. The package offers
useful functionality, such as:
* programmatic inheritance in the OO sense,
effectively subclassing YAML-described schemas according to an algorithm.
* automatic generation of coresponding Python classes
* SQL/SQLAlchemy interface
* GraphQL

What is exceptionally useful is automatic validation of schemas
provided by _linkml_, e.g.
```bash
linkml-validate -s ro/RO.yml ro/RO_mockup_star_oo200rff.yml
```


## Misc

The _misc_ folder keep supporing material, not typically used
as a context.
