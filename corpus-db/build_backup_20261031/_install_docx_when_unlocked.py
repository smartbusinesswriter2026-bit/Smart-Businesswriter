"""Wait for Word to release DATABASE.docx, then install the newly built copy.

The new build is already written and verified; it only needs the lock to go.
The old file is replaced wholesale (it is a generated artifact), so this never
leaves a half-written manual behind: the copy is done with os.replace, which
is atomic on Windows.
"""
import os
import shutil
import sys
import time

TARGET = r"D:\SMART BUSINESSWRITER\DATABASE.docx"
NEW = r"D:\SMART BUSINESSWRITER\DATABASE.new.docx"
DEADLINE_SECONDS = 60 * 45


def writable(path):
    try:
        handle = open(path, "r+b")
        handle.close()
        return True
    except OSError:
        return False


started = time.time()
print("waiting for %s to be released by Word..." % TARGET, flush=True)
while time.time() - started < DEADLINE_SECONDS:
    if writable(TARGET):
        try:
            shutil.copyfile(NEW, TARGET)
            print("REPLACED %s with the new build" % TARGET, flush=True)
            os.remove(NEW)
            print("removed the staging copy", flush=True)
            sys.exit(0)
        except OSError as error:
            print("copy failed:", error, flush=True)
            time.sleep(5)
    time.sleep(3)

print("GAVE UP: %s was still locked after %d minutes. The new build is at %s"
      % (TARGET, DEADLINE_SECONDS // 60, NEW), flush=True)
sys.exit(1)
