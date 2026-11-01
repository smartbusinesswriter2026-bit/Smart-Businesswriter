"""One-off: show the traceback for named failures in a suite log."""
import io
import sys

PATH = "D:\\SMART BUSINESSWRITER\\business_pipeline_v0.12\\business_pipeline\\_full_err.txt"
text = io.open(PATH, encoding="utf-8", errors="replace").read()
lines = text.split("\n")

wanted = sys.argv[1:]
for index, line in enumerate(lines):
    if any(line.startswith("FAIL: %s " % name) or line.startswith("ERROR: %s " % name)
           for name in wanted):
        print("=" * 78)
        for chunk in lines[index:index + 26]:
            print(chunk)
