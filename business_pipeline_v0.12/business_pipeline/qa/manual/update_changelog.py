path = 'docs/CHANGELOG.md'
with open(path, encoding='utf-8', errors='replace') as f:
    content = f.read()
old = '  - **Not moved.** No method, preset, input, check, computed number or frozen-core entry changed;'
new = '''  - **The Economics shelf is quieter.** The top-of-shelf lookup panel drops "(retrieved, not verified)" from its heading and the World Bank introductory paragraph. The tiles section drops its section header ("The tiles"), its explanatory paragraph, every "Before you start:" line, every "Calculators: supply the figures..." line, and every tile topic description. The tile headings themselves remain as clickable cards; only the surrounding instructional text is gone. Nothing in `src/bp/product/subjects.py`, the baked snapshots, or any frozen-core entry changed.

'''
new += old
if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('CHANGELOG updated')
else:
    print('Pattern not found in CHANGELOG')
