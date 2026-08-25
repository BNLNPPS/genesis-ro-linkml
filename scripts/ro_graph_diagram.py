#!/usr/bin/env python3
"""
ro_graph_diagram.py

Render the provenance graph described by a Genesis Research Object instance
file (e.g. ro/RO_mockup_star_oo200rff.yml) as a diagram, in either Mermaid
flowchart syntax or Graphviz DOT syntax.

This visualizes *instance data* -- the actual research objects and the
uses/used_by/produces/produced_by edges between them -- as opposed to
LinkML's own `gen-erdiagram` / `gen-doc` generators, which visualize the
*schema* (ro/RO.yml's classes and slots), not specific object instances.

Usage:
    python3 scripts/ro_graph_diagram.py ro/RO_mockup_star_oo200rff.yml
    python3 scripts/ro_graph_diagram.py ro/RO_mockup_star_oo200rff.yml -f dot -o graph.dot
    python3 scripts/ro_graph_diagram.py ro/RO_mockup_star_oo200rff.yml -t "STAR O+O 200 GeV RFF provenance"

See scripts/README.md for rendering instructions.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("This script requires PyYAML. Install it with:\n    pip install pyyaml")

# ----------------------------------------------------------------------
# Styling: one (css_class, fill_color, border_color) tuple per object_type.
# Applies to both Mermaid (classDef) and Graphviz (fillcolor/color) output.
# ----------------------------------------------------------------------
STYLES: dict[str, tuple[str, str, str]] = {
    "Dataset": ("dataset", "#cfe8ff", "#2b6cb0"),
    "Analysis": ("analysis", "#ffe8cc", "#c05621"),
    "Calibration": ("calibration", "#e6ffed", "#2f855a"),
    "DataArtifact": ("dataartifact", "#fff5cc", "#b7791f"),
    "Software": ("software", "#f0e6ff", "#6b46c1"),
    "Workflow": ("workflow", "#e6f7ff", "#0987a0"),
    "Publication": ("publication", "#ffe6f0", "#b83280"),
}
DEFAULT_STYLE = ("other", "#f5f5f5", "#666666")
EXTERNAL_STYLE = ("external", "#f0f0f0", "#999999")

GENERIC_LABELS = {"uses", "used_by", "produces", "produced_by"}


def truncate(text: str, width: int = 60) -> str:
    """Collapse whitespace and shorten text to `width` characters."""
    text = " ".join((text or "").split())
    if len(text) > width:
        return text[: width - 1].rstrip() + "…"
    return text


def load_research_objects(path: Path) -> list[dict[str, Any]]:
    """Load a research-object instance file and return its list of records.

    Accepts the `research_objects:` wrapper used by this repo's instance
    files (matching RO.yml's ResearchObjectCollection), a bare top-level
    list, or a dict with a single list-valued key.
    """
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("research_objects"), list):
            return data["research_objects"]
        list_valued = [v for v in data.values() if isinstance(v, list)]
        if len(list_valued) == 1:
            return list_valued[0]
    raise ValueError(
        f"Could not find a list of research objects in {path}. "
        "Expected a top-level `research_objects:` list."
    )


def node_key(id_field: dict[str, Any] | None) -> str | None:
    """The value half of a typed Identifier is used as the node's key."""
    if not id_field:
        return None
    value = id_field.get("value")
    return str(value) if value is not None else None


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str], str] = {}  # (src_key, dst_key) -> label

    def add_node(self, key: str, name: str | None, object_type: str | None) -> None:
        existing = self.nodes.get(key)
        if existing and existing.get("known"):
            return
        self.nodes[key] = {
            "name": name or key,
            "object_type": object_type,
            "known": object_type is not None,
        }

    def add_edge(self, src: str, dst: str, label: str | None) -> None:
        if not src or not dst:
            return
        label = (label or "").strip()
        key = (src, dst)
        current = self.edges.get(key)
        # Prefer a specific role string over a generic relation name, and
        # avoid clobbering an already-specific label with a generic one.
        if current is None:
            self.edges[key] = label
        elif current in GENERIC_LABELS and label and label not in GENERIC_LABELS:
            self.edges[key] = label


def build_graph(records: list[dict[str, Any]]) -> Graph:
    g = Graph()

    # Pass 1: register every record actually defined in this file.
    for rec in records:
        key = node_key(rec.get("id"))
        if key is not None:
            g.add_node(key, rec.get("name"), rec.get("object_type"))

    # Pass 2: derive edges. Both directions of a relationship (e.g. A.uses B
    # and B.used_by A) collapse onto the same (src, dst) edge key, so a file
    # that declares both sides -- like RO_mockup_star_oo200rff.yml does --
    # doesn't produce doubled-up arrows.
    for rec in records:
        key = node_key(rec.get("id"))
        if key is None:
            continue

        for ref in rec.get("uses") or []:
            target = node_key(ref.get("identifier"))
            if target:
                g.add_node(target, None, None)
                g.add_edge(target, key, ref.get("role") or "uses")

        for ref in rec.get("used_by") or []:
            target = node_key(ref.get("identifier"))
            if target:
                g.add_node(target, None, None)
                g.add_edge(key, target, ref.get("role") or "used_by")

        for ref in rec.get("produces") or []:
            target = node_key(ref.get("identifier"))
            if target:
                g.add_node(target, None, None)
                g.add_edge(key, target, ref.get("role") or "produces")

        produced_by = rec.get("produced_by")
        if produced_by:
            target = node_key(produced_by.get("identifier"))
            if target:
                g.add_node(target, None, None)
                g.add_edge(target, key, produced_by.get("role") or "produced_by")

    return g


def style_for(node: dict[str, Any]) -> tuple[str, str, str]:
    if not node.get("known"):
        return EXTERNAL_STYLE
    return STYLES.get(node.get("object_type"), DEFAULT_STYLE)


def node_label_lines(key: str, node: dict[str, Any]) -> list[str]:
    lines = [truncate(key, 40), truncate(node["name"], 50)]
    if node.get("object_type"):
        lines.append(f"[{node['object_type']}]")
    elif not node.get("known"):
        lines.append("[external / unresolved]")
    return lines


# ----------------------------------------------------------------------
# Mermaid output
# ----------------------------------------------------------------------

def mermaid_id(raw: str) -> str:
    ident = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    if not ident or ident[0].isdigit():
        ident = "n_" + ident
    return ident


def esc_mermaid(text: str) -> str:
    return text.replace('"', "&quot;")


def to_mermaid(g: Graph, title: str | None, direction: str) -> str:
    ids = {key: mermaid_id(key) for key in g.nodes}
    lines: list[str] = []
    if title:
        lines.append(f"%% {title}")
    lines.append(f"flowchart {direction}")

    used_classes: set[str] = set()
    for key, node in g.nodes.items():
        css_class, _, _ = style_for(node)
        used_classes.add(css_class)
        label = "<br/>".join(esc_mermaid(x) for x in node_label_lines(key, node))
        lines.append(f'    {ids[key]}["{label}"]:::{css_class}')

    for (src, dst), label in g.edges.items():
        if label:
            arrow = f'-->|"{esc_mermaid(truncate(label, 50))}"|'
        else:
            arrow = "-->"
        lines.append(f"    {ids[src]} {arrow} {ids[dst]}")

    for css_class in sorted(used_classes):
        match = next((v for v in STYLES.values() if v[0] == css_class), None)
        if match is None:
            match = EXTERNAL_STYLE if css_class == "external" else DEFAULT_STYLE
        _, fill, border = match
        lines.append(f"    classDef {css_class} fill:{fill},stroke:{border},color:#1a1a1a;")

    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------
# Graphviz DOT output
# ----------------------------------------------------------------------

def esc_dot(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def to_dot(g: Graph, title: str | None, direction: str) -> str:
    rankdir = {"TD": "TB", "TB": "TB", "LR": "LR", "RL": "RL", "BT": "BT"}.get(direction, "TB")
    lines = ["digraph provenance {"]
    if title:
        lines.append(f'    labelloc="t"; label="{esc_dot(title)}";')
    lines.append(f"    rankdir={rankdir};")
    lines.append('    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];')
    lines.append('    edge [fontname="Helvetica", fontsize=9];')

    for key, node in g.nodes.items():
        _, fill, border = style_for(node)
        # Escape each line *before* joining, so the literal `\n` separator
        # (Graphviz's own line-break marker inside a label) isn't itself
        # escaped into a visible backslash-n by esc_dot.
        label = "\\n".join(esc_dot(line) for line in node_label_lines(key, node))
        lines.append(f'    "{esc_dot(key)}" [label="{label}", fillcolor="{fill}", color="{border}"];')

    for (src, dst), label in g.edges.items():
        attr = f' [label="{esc_dot(truncate(label, 50))}"]' if label else ""
        lines.append(f'    "{esc_dot(src)}" -> "{esc_dot(dst)}"{attr};')

    lines.append("}")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a Genesis Research Object instance graph as a Mermaid or Graphviz diagram."
    )
    parser.add_argument("input", type=Path, help="Path to a research-object instance YAML file")
    parser.add_argument(
        "-f", "--format", choices=["mermaid", "dot"], default="mermaid",
        help="Output diagram format (default: mermaid)",
    )
    parser.add_argument("-o", "--output", type=Path, help="Write output to this file instead of stdout")
    parser.add_argument("-t", "--title", help="Optional diagram title")
    parser.add_argument(
        "-d", "--direction", choices=["TD", "TB", "LR", "RL", "BT"], default="TB",
        help="Layout direction (default: TB, top-to-bottom)",
    )
    args = parser.parse_args()

    records = load_research_objects(args.input)
    graph = build_graph(records)

    if args.format == "mermaid":
        output = to_mermaid(graph, args.title, args.direction)
    else:
        output = to_dot(graph, args.title, args.direction)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(
            f"Wrote {args.format} diagram ({len(graph.nodes)} nodes, "
            f"{len(graph.edges)} edges) to {args.output}"
        )
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
