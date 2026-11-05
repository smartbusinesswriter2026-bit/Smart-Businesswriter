src = open("web/index.html", encoding="utf-8").read()

old = '''    act("Explanation file", function () {
      fetch("/api/cases/statements/" + record.id + "/replay", {method: "POST"})
        .then(function (answer) { return answer.json(); })
        .then(function (body) {
          host.appendChild(el("p", "muted", body.ok ? "Replay matches: the record reproduces exactly."
            : "Replay drifted: " + JSON.stringify(body)));
        });
    });'''

new = '''    act("Explanation file", function () {
      fetch("/api/cases/statements/" + record.id + "/explanation", {method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({format: "docx"})})
        .then(function (answer) { return answer.json(); })
        .then(function (body) {
          if (body.document && body.document.data) {
            var binary = atob(body.document.data), bytes = new Uint8Array(binary.length);
            for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            var url = URL.createObjectURL(new Blob([bytes], {type: body.document.mime}));
            var link = document.createElement("a");
            link.href = url; link.download = body.document.filename;
            document.body.appendChild(link); link.click();
            setTimeout(function () { URL.revokeObjectURL(url); link.remove(); }, 0);
            host.appendChild(el("p", "muted", "Explanation downloaded: " + body.document.filename));
          } else {
            host.appendChild(el("p", "muted", (body.error) || "No explanation available."));
          }
        });
    });'''

assert old in src, "old pattern not found"
src = src.replace(old, new, 1)
open("web/index.html", "w", encoding="utf-8").write(src)
print("patched frontend")
