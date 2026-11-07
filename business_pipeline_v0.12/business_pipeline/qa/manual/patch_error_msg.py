# Fix the unprofessional error message in the frontend
src = open("web/index.html", encoding="utf-8").read()

old = '''if (result.status === 400) {
/* The backend's own reason is shown, in its words: it knows why it refused and the page
must not paraphrase a refusal it does not own.  The shape the tile reads is added
under it, because a refusal the student cannot act on is a dead end. */
host.innerHTML = banner("blocked", "The tile could not read this",
"<div>" + esc(result.body.error || "The instruction could not be read.") + "</div>" +
"<p class=\\"muted\\" style=\\"margin:8px 0 0\\">The tile reads one trial balance for one period, " +
"one account per line, as &ldquo;Cash 5,000&rdquo; or &ldquo;Capital 5,000 Cr&rdquo;. " +
"Press <strong>Use an example</strong> to see the shape it reads.</p>");
return;
}'''

new = '''if (result.status === 400) {
/* The backend's own reason is shown, in its words.  A refusal is not a failure of the
student's input; it is the system declining to guess.  Suggestions are offered so the
student can restate the problem in a form the tile can read. */
var msg = result.body.error || "The instruction could not be read.";
host.innerHTML = banner("blocked", "This problem needs a different shape",
"<div>" + esc(msg) + "</div>" +
"<p class=\\"muted\\" style=\\"margin:8px 0 0\\">Suggestions:</p>" +
"<ul class=\\"muted\\" style=\\"margin:4px 0 8px 20px\\">" +
"<li>State the problem as a trial balance: one account per line with its balance " +
"(e.g. &ldquo;Cash 5,000&rdquo; or &ldquo;Capital 5,000 Cr&rdquo;).</li>" +
"<li>Or state it as labelled figures: &ldquo;Data: direct materials 50,000; direct labour 40,000. " +
"Required: create a cost of goods manufactured schedule.&rdquo;</li>" +
"<li>Or break a long transaction list into smaller groups of entries.</li>" +
"<li>Press <strong>Use an example</strong> to see the shape the tile reads.</li>" +
"</ul>");
return;
}'''

assert old in src, "old pattern not found"
src = src.replace(old, new, 1)
open("web/index.html", "w", encoding="utf-8").write(src)
print("patched frontend")
