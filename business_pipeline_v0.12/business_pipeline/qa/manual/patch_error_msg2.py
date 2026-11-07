src = open("web/index.html", encoding="utf-8").read()
lines = src.splitlines()

# Replace lines 10196-10200 (0-based: 10195-10199)
old_block = lines[10195:10200]
new_block = [
    '        host.innerHTML = banner("blocked", "This problem needs a different shape",',
    '          "<div>" + esc(result.body.error || "The instruction could not be read.") + "</div>" +',
    '          "<p class=\\"muted\\" style=\\"margin:8px 0 0\\">Suggestions:</p>" +',
    '          "<ul class=\\"muted\\" style=\\"margin:4px 0 8px 20px\\">" +',
    '          "<li>State the problem as a trial balance: one account per line with its balance " +',
    '          "(e.g. &ldquo;Cash 5,000&rdquo; or &ldquo;Capital 5,000 Cr&rdquo;).</li>" +',
    '          "<li>Or state it as labelled figures: &ldquo;Data: direct materials 50,000; direct labour 40,000. " +',
    '          "Required: create a cost of goods manufactured schedule.&rdquo;</li>" +',
    '          "<li>Or break a long transaction list into smaller groups of entries.</li>" +',
    '          "<li>Press <strong>Use an example</strong> to see the shape the tile reads.</li>" +',
    '          "</ul>");',
]

# Verify the old block matches
assert "host.innerHTML = banner(\"blocked\", \"The tile could not read this\"" in lines[10195], repr(lines[10195])
lines[10195:10200] = new_block
open("web/index.html", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("patched frontend error message")
