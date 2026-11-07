import json, base64, urllib.request, zipfile, re
body = b'{"instruction": "Data: Equipment cost 100,000; residual value 10,000; useful life 5 years; straight-line depreciation. Sold on Dec. 31 of Year 3 for 35,000. Required: Compute annual depreciation, accumulated depreciation at sale, gain/loss, and show financial statement effects."}'
req = urllib.request.Request("http://localhost:8021/api/cases/statements", data=body, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
record = json.loads(resp.read())
rid = record["id"]
exp_body = b'{"format": "docx"}'
req2 = urllib.request.Request("http://localhost:8021/api/cases/statements/" + rid + "/explanation", data=exp_body, headers={"Content-Type": "application/json"})
resp2 = urllib.request.urlopen(req2)
data = json.loads(resp2.read())
b = base64.b64decode(data["document"]["data"])
with open("C:/Users/Roderick/AppData/Local/Temp/opencode/explain_final.docx", "wb") as f:
    f.write(b)
z = zipfile.ZipFile("C:/Users/Roderick/AppData/Local/Temp/opencode/explain_final.docx")
xml = z.read("word/document.xml").decode("utf-8")
paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
out = []
for p in paras:
    ts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p)
    line = "".join(ts)
    if line.strip():
        out.append(line)
with open("C:/Users/Roderick/AppData/Local/Temp/opencode/explain_final.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("paragraphs:", len(out))
