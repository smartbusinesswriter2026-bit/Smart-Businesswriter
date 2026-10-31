"""Report and normalise stray CR characters in a text file (the repo normalises to LF)."""
import sys

path = sys.argv[1]
with open(path, "rb") as handle:
    data = handle.read()

stray = [i for i, byte in enumerate(data) if byte == 13]
print("stray CR bytes:", len(stray))
for i in stray[:5]:
    start = data.rfind(b"\n", 0, i) + 1
    end = data.find(b"\n", i)
    print("  line:", data[start:end].decode("utf-8", "replace")[:120])

if stray and len(stray) <= 4:
    with open(path, "wb") as handle:
        handle.write(data.replace(b"\r\n", b"\n"))
    with open(path, "rb") as handle:
        check = handle.read()
    print("normalised -> CR:", check.count(b"\r"), "LF:", check.count(b"\n"))
