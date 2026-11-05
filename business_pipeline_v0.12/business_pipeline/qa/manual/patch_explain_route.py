p = "src/bp/product/statements.py"
text = open(p, encoding="utf-8").read()

old = '    return 404, {"error": "unknown statements route"}'
new = '''    if len(segments) == 2 and segments[1] == "explanation":
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on an explanation"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        if not record.get("solved"):
            return 422, {"error": "this record has no solution to explain: " + str(record.get("refusal"))}
        fmt = (body or {}).get("format", "docx") if isinstance(body, dict) else "docx"
        try:
            title, sections = explain(record)
            import base64
            from . import docx as docx_export
            data = docx_export.render_bytes(title, sections, mono=False)
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = "explanation-" + str(record.get("id")) + ".docx"
            return 200, {"format": "docx", "explanation": {"title": title},
                          "document": {"filename": filename, "mime": mime,
                                        "data": base64.b64encode(data).decode("ascii")}}
        except Exception as error:
            return 500, {"error": "explanation failed: " + str(error)[:200]}

    return 404, {"error": "unknown statements route"}'''

assert old in text, "old not found"
text = text.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(text)
print("patched")
