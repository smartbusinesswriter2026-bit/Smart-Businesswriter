"""WO-2b: add the 32 worksheet templates to `bp.templates`.

Four structures in `src/bp/templates.py` carry a canvas template:

- ``CANVAS_BLOCKS``   the block labels and prompts.
- ``CANVAS_META``     the name, the short name, the catalogue id and the
                      intended and unsupported uses.
- ``CANVAS_PREFIXES`` the short readable id prefix per block.
- ``EXAMPLES``        a worked request on the synthetic case.

The nine templates that had no blocks get their blocks written from the
profile they belong to, so the block labels and prompts are the framework's
own.  The other twenty-three already carry blocks that match their profile
exactly, and those are left alone.

The writer locates each dict with `ast` and splices the new entries in just
before its closing brace, so the file keeps its own layout.

Run from `business_pipeline/`:

    $env:PYTHONPATH="src"; python _wo_apply_templates.py
"""

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _wo_templates import TEMPLATES  # noqa: E402

TARGET = os.path.join(HERE, "src", "bp", "templates.py")
WIDTH = 120


def _q(text):
    """A string literal in the file's house style: double quotes, unless the
    text itself carries one."""
    if '"' not in text:
        return '"%s"' % text
    if "'" not in text:
        return '"%s"' % text
    return "'%s'" % text.replace("\\", "\\\\").replace("'", "\\'")


def _wrap(text, indent, width=WIDTH):
    """A string literal, wrapped into adjacent literals when it is too long.

    The first line carries the literal itself; the continuation lines are
    indented to sit under the opening quote.
    """
    literal = _q(text)
    if len(text) + indent <= width:
        return literal
    words = text.split(" ")
    chunks, current = [], ""
    for word in words:
        candidate = (current + " " + word) if current else word
        if current and len(candidate) + indent > width:
            chunks.append(current)
            current = word
        else:
            current = candidate
    chunks.append(current)
    parts = [_q(chunk + " " if index < len(chunks) - 1 else chunk)
             for index, chunk in enumerate(chunks)]
    return "\n".join([parts[0]] + [" " * indent + part for part in parts[1:]])


def _entry_lines(template, spec):
    """The rendered CANVAS_BLOCKS entry for one template."""
    lines = ['    %s: {' % _q(template)]
    for key, (label, prompt) in spec["blocks"].items():
        label_literal = _q(label)
        prompt_literal = _wrap(prompt, 8 + len(label_literal) + 4)
        lines.append('        %s: (%s, %s),' % (_q(key), label_literal, prompt_literal))
    lines.append("    },")
    return "\n".join(lines)


def _meta_lines(template, spec):
    """The rendered CANVAS_META entry for one template.

    The file writes these values on one line each, so they are written that
    way here.
    """
    meta = spec["meta"]
    registry = "[%s]" % ", ".join(_q(cid) for cid in [spec["catalogue_id"]])
    lines = ['    %s: {' % _q(template)]
    lines.append('        "name": %s, "short": %s, "registry_ids": %s,'
                 % (_q(meta["name"]), _q(meta["short"]), registry))
    lines.append('        "intended_use": %s,' % _q(meta["intended_use"]))
    lines.append('        "unsupported_use": %s,' % _q(meta["unsupported_use"]))
    lines.append('        "extra_help": %s,' % _q(meta["extra_help"]))
    lines.append("    },")
    return "\n".join(lines)


def _prefix_lines(template, spec):
    """The rendered CANVAS_PREFIXES entry for one template.

    The first prefix sits on the line that opens the brace, and the rest are
    aligned under it, which is how the file already writes these.
    """
    head = '    %s: {' % _q(template)
    indent = len(head) + 1
    items = list(spec["prefixes"].items())
    lines, current = [], []
    for key, prefix in items:
        piece = '%s: %s' % (_q(key), _q(prefix))
        if current and len(", ".join(current + [piece])) + indent > WIDTH:
            lines.append(", ".join(current) + ",")
            current = [piece]
        else:
            current.append(piece)
    lines.append(", ".join(current) + "},")
    first, rest = lines[0], lines[1:]
    body = head + first
    for line in rest:
        body += "\n" + " " * indent + line
    return body


def _example_lines(template, spec):
    """The rendered EXAMPLES entry for one template."""
    example = spec["example"]
    lines = ['    %s: {"objective": %s, "method": %s, "inputs": {'
             % (_q(template), _q(example["objective"]), _q(template))]
    lines.append('        "blocks": {')
    blocks = list(example["blocks"].items())
    for index, (key, items) in enumerate(blocks):
        rendered = []
        for item in items:
            parts = ['"text": %s' % _q(item["text"])]
            if "id" in item:
                parts.append('"id": %s' % _q(item["id"]))
            parts.append('"provenance": %s' % _q(item["provenance"]))
            if "materiality" in item:
                parts.append('"materiality": %s' % _q(item["materiality"]))
            rendered.append("{%s}" % ", ".join(parts))
        tail = "," if index < len(blocks) - 1 else ""
        lines.append('            %s: [%s]%s' % (_q(key), ", ".join(rendered), tail))
    lines.append("        }")
    if example.get("links"):
        lines.append('        "links": [%s]' % ", ".join(
            '{"from": %s, "to": %s}' % (_q(link["from"]), _q(link["to"]))
            for link in example["links"]))
    lines.append("}},")
    return "\n".join(lines)


def _find(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                return node.value
    raise KeyError(name)


def _offsets(lines):
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    return starts


def main():
    with open(TARGET, encoding="utf-8", newline="") as stream:
        source = stream.read()
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    starts = _offsets(lines)

    blocks_node = _find(tree, "CANVAS_BLOCKS")
    meta_node = _find(tree, "CANVAS_META")
    prefixes_node = _find(tree, "CANVAS_PREFIXES")
    examples_node = _find(tree, "EXAMPLES")

    existing_blocks = set()
    for key in blocks_node.keys:
        if isinstance(key, ast.Constant):
            existing_blocks.add(key.value)

    blocks_text, meta_text, prefixes_text, examples_text = [], [], [], []
    for template, spec in sorted(TEMPLATES.items()):
        if template not in existing_blocks:
            blocks_text.append(_entry_lines(template, spec))
        meta_text.append(_meta_lines(template, spec))
        prefixes_text.append(_prefix_lines(template, spec))
        examples_text.append(_example_lines(template, spec))

    inserts = [
        (blocks_node, blocks_text),
        (meta_node, meta_text),
        (prefixes_node, prefixes_text),
        (examples_node, examples_text),
    ]
    # Each splice shifts everything after it, so the inserts go in from the
    # end of the file backwards and the offsets stay valid.
    positioned = []
    for node, chunks in inserts:
        if not chunks:
            continue
        # The closing brace of the dict literal: its last character.
        positioned.append((starts[node.end_lineno - 1] + node.end_col_offset - 1, chunks))
    for position, chunks in sorted(positioned, key=lambda item: -item[0]):
        text = "\n" + "\n".join(chunks) + "\n"
        source = source[:position] + text + source[position:]

    with open(TARGET, "w", encoding="utf-8", newline="") as stream:
        stream.write(source)
    print("added %d templates (blocks for %d)"
          % (len(TEMPLATES), len(blocks_text)))


if __name__ == "__main__":
    main()
