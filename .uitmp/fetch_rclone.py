"""Download the rclone portable build for Windows and verify its published SHA-256.

The binary is a build-time/operations tool (C-02): it is never imported by the
pipeline runtime. It is installed under corpus-db/build/tools/ so the corpus
build stays self-contained, and it is gitignored.
"""
import hashlib
import os
import shutil
import sys
import urllib.request
import zipfile

TOOLS = r"D:\SMART BUSINESSWRITER\corpus-db\build\tools"


def fetch(url, attempts=4):
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "corpus-r2-setup"})
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except Exception as error:  # the CDN 404s intermittently; retry
            last = error
            print("  fetch attempt %d failed for %s: %s" % (attempt + 1, url, error))
    raise last


def main():
    os.makedirs(TOOLS, exist_ok=True)
    version_raw = fetch("https://downloads.rclone.org/version.txt").decode("ascii", "replace")
    match = __import__("re").search(r"v(\d+\.\d+\.\d+)", version_raw)
    if not match:
        raise SystemExit("could not read a version from version.txt: %r" % version_raw[:200])
    version = match.group(1)
    print("latest rclone version:", version)

    archive_name = "rclone-v%s-windows-amd64.zip" % version
    archive_path = os.path.join(TOOLS, archive_name)
    sums_path = os.path.join(TOOLS, "SHA256SUMS")
    archive_url = "https://downloads.rclone.org/v%s/%s" % (version, archive_name)
    sums_url = "https://downloads.rclone.org/v%s/SHA256SUMS" % version
    print("archive url:", archive_url)

    if not os.path.exists(archive_path) or os.path.getsize(archive_path) < 1024:
        with open(archive_path, "wb") as handle:
            handle.write(fetch(archive_url))
    with open(sums_path, "wb") as handle:
        handle.write(fetch(sums_url))

    expected = None
    with open(sums_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if archive_name in line and line.strip().split(" ")[0]:
                expected = line.strip().split()[0].lower()
                break
    digest = hashlib.sha256()
    with open(archive_path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest()
    print("published sha256:", expected)
    print("computed  sha256:", actual)
    if not expected or expected != actual:
        raise SystemExit("CHECKSUM MISMATCH - refusing to install")

    destination = os.path.join(TOOLS, "rclone-%s" % version)
    os.makedirs(destination, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)
    exe = None
    for root, _dirs, files in os.walk(destination):
        if "rclone.exe" in files:
            exe = os.path.join(root, "rclone.exe")
            break
    print("installed:", exe)
    shutil.copyfile(exe, os.path.join(TOOLS, "rclone.exe"))
    print("stable path:", os.path.join(TOOLS, "rclone.exe"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
