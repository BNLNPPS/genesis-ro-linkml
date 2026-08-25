# scripts/

Utility scripts for this repository. Not part of the LinkML schema itself.

## ro_graph_diagram.py

Renders the *instance* provenance graph described by a Genesis Research
Object data file (e.g. `ro/RO_mockup_star_oo200rff.yml`) as a diagram — the
actual objects (Datasets, Analyses, Calibrations, ...) and the
`uses` / `used_by` / `produces` / `produced_by` edges between them.

This complements LinkML's own `gen-erdiagram` / `gen-doc` generators, which
visualize the *schema* (`ro/RO.yml`'s classes and slots) rather than specific
object instances. There's no LinkML built-in for drawing a particular
instance graph like this one, which is why this script exists.

### Requirements

```
pip install pyyaml
```

### Usage

Mermaid (default), printed to stdout:

```
python3 scripts/ro_graph_diagram.py ro/RO_mockup_star_oo200rff.yml
```

Graphviz DOT, written to a file:

```
python3 scripts/ro_graph_diagram.py ro/RO_mockup_star_oo200rff.yml -f dot -o graph.dot
```

With a title and left-to-right layout:

```
python3 scripts/ro_graph_diagram.py ro/RO_mockup_star_oo200rff.yml \
    -t "STAR O+O 200 GeV RFF provenance" -d LR -o graph.mmd
```

Options:

| Flag | Description | Default |
|---|---|---|
| `-f`, `--format` | `mermaid` or `dot` | `mermaid` |
| `-o`, `--output` | Write to a file instead of stdout | stdout |
| `-t`, `--title` | Optional diagram title | none |
| `-d`, `--direction` | Layout direction: `TD`/`TB`, `LR`, `RL`, `BT` | `TB` |

### Rendering the output

- **Mermaid**: paste into the [Mermaid Live Editor](https://mermaid.live/), a
  GitHub Markdown fenced &#96;&#96;&#96;mermaid code block, or an MkDocs/Sphinx site.
- **DOT**: render locally with Graphviz, e.g.
  `dot -Tsvg graph.dot -o graph.svg` or `dot -Tpng graph.dot -o graph.png`.

Other examples:
```bash
dot -Tsvg graph.dot -o graph.svg
dot -Tpng graph.dot -o graph.png
dot -Tpdf graph.dot -o graph.pdf
```



### How it works

Each research object becomes one node, colored by its `object_type`
(Dataset, Analysis, Calibration, DataArtifact, Software, Workflow,
Publication). Edges are derived from the `uses` / `used_by` / `produces` /
`produced_by` fields on each record; both directions of a relationship
(e.g. `A.uses B` and `B.used_by A`) collapse onto a single edge so the
diagram doesn't double up arrows, and a specific `role` string is preferred
over the generic relation name when both are available.

Any identifier referenced by an edge but not itself present in the file
(i.e. something outside this graph) is still drawn, shaded gray and labeled
"external / unresolved", rather than silently dropped.

### Known limitation

Not yet tested end-to-end in this environment (the sandbox used to develop
it had no working shell). The logic was traced by hand against
`ro/RO_mockup_star_oo200rff.yml`, but it's worth running once locally and
skimming the output before relying on it.
