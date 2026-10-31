"""WO-2a: replace the VRIO unit and voice in the 32 orphan profiles.

The rewrite is done on the *source*, not on the imported object, so the file
keeps its own layout and the diff shows the profile data that changed.  Each
profile constant is located with `ast`, the `unit` and `voice` mappings are
found inside it, and the text span of each mapping is replaced.

The `process` profiles also take the house convention that goes with the
unit field: `sites` None, `providers` None and the retrieval gate that does
not demand a title cue or a title context.  In this codebase those three
always travel with the unit field (48 industry profiles, 19 process profiles
and 1 country profile all agree), so a profile that keeps the industry gate
with a process unit would be the only one of its kind.

Run from `business_pipeline/`:

    $env:PYTHONPATH="src"; python _wo_apply_profiles.py
"""

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _wo_authoring import AUTHORING  # noqa: E402

TARGET = os.path.join(HERE, "src", "bp", "product", "framework_profiles.py")
WIDTH = 116


# ---------------------------------------------------------------- rendering

def _q(value):
    """A Python string literal in the file's own style: single quotes unless the
    text contains an apostrophe, in which case double quotes."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return "None"
    if not isinstance(value, str):
        return repr(value)
    if '"' not in value and "'" in value:
        return '"%s"' % value
    if '"' in value and "'" in value:
        return "'%s'" % value.replace("\\", "\\\\").replace("'", "\\'")
    return "'%s'" % value.replace("\\", "\\\\")


def _chunks(text, width):
    """Split a string into chunks that each fit inside `width`."""
    words = text.split(" ")
    out, current = [], ""
    for word in words:
        candidate = (current + " " + word) if current else word
        if current and len(candidate) > width:
            out.append(current)
            current = word
        else:
            current = candidate
    out.append(current)
    return out


def _value_lines(value, indent, width=WIDTH):
    """The source lines for one mapping value."""
    if not isinstance(value, str):
        return [_q(value)]
    if len(value) + indent <= width:
        return [_q(value)]
    lines = []
    parts = _chunks(value, width - indent - 3)
    for index, part in enumerate(parts):
        text = part + " " if index < len(parts) - 1 else part
        lines.append(_q(text))
    return lines


def render_mapping(key, pairs, base_indent):
    """Render the `{ ... },` body of a mapping, in the file's style.

    The key is left where it is: only the value node is replaced, so the
    rendered text starts at the brace.  The first key sits on the line that
    opens the brace; the rest are aligned under it.  A long string is wrapped
    into adjacent literals, aligned under the opening quote, exactly as the
    file already writes them.
    """
    key_literal = _q(key)
    brace_column = base_indent + len(key_literal) + 2
    first_column = brace_column + 1
    items = list(pairs.items())
    lines = []
    for index, (name, value) in enumerate(items):
        name_literal = _q(name)
        continuation = first_column + len(name_literal) + 2
        parts = _value_lines(value, continuation)
        prefix = " " * first_column
        comma = "" if index == len(items) - 1 else ","
        # The comma closes the *value*, so it goes on the last line of a
        # wrapped string rather than on the first.
        parts[-1] = parts[-1] + comma
        if index == 0:
            lines.append(name_literal + ": " + parts[0])
        else:
            lines.append(prefix + name_literal + ": " + parts[0])
        for extra in parts[1:]:
            lines.append(" " * continuation + extra)
    body = "{" + lines[0]
    for line in lines[1:]:
        body += "\n" + line
    return body + "}"


# ------------------------------------------------------------------- source

def _profile_nodes(tree):
    """template id -> (constant name, the Dict node of the profile)."""
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if isinstance(key, ast.Constant) and key.value == "template":
                out[value.value] = (target.id, node.value)
    return out


def _entry(profile, name):
    """The (key node, value node) of `name` inside a profile Dict node."""
    for key, value in zip(profile.keys, profile.values):
        if isinstance(key, ast.Constant) and key.value == name:
            return key, value
    raise KeyError(name)


def _span(source_lines, node):
    """The (start, end) character offsets of a node in the whole file."""
    starts = []
    offset = 0
    for line in source_lines:
        starts.append(offset)
        offset += len(line)
    begin = starts[node.lineno - 1] + node.col_offset
    end = starts[node.end_lineno - 1] + node.end_col_offset
    return begin, end


def main():
    with open(TARGET, encoding="utf-8", newline="") as stream:
        source = stream.read()
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    profiles = _profile_nodes(tree)

    edits = []
    for template, spec in sorted(AUTHORING.items()):
        if template not in profiles:
            raise SystemExit("no profile constant for %s" % template)
        _, profile = profiles[template]

        _, unit_node = _entry(profile, "unit")
        unit_text = render_mapping("unit", spec["unit"], 1)
        edits.append((*_span(lines, unit_node), unit_text))

        _, voice_node = _entry(profile, "voice")
        voice_text = render_mapping("voice", spec["voice"], 1)
        edits.append((*_span(lines, voice_node), voice_text))

        if spec["field"] == "process":
            # The unit field travels with three other fields in this codebase.
            _, sites_node = _entry(profile, "sites")
            edits.append((*_span(lines, sites_node), "None"))
            _, providers_node = _entry(profile, "providers")
            edits.append((*_span(lines, providers_node), "None"))
            _, gate_node = _entry(profile, "gate")
            gate_text = ("{'require_geography': False, 'title_context': False, "
                         "'title_cue': False}")
            edits.append((*_span(lines, gate_node), gate_text))

    # Apply from the end of the file backwards so earlier offsets stay valid.
    for begin, end, text in sorted(edits, key=lambda edit: -edit[0]):
        source = source[:begin] + text + source[end:]

    with open(TARGET, "w", encoding="utf-8", newline="") as stream:
        stream.write(source)

    print("rewrote %d profiles (%d edits)" % (len(AUTHORING), len(edits)))


if __name__ == "__main__":
    main()
