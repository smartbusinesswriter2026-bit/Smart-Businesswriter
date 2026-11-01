"""Thin wrapper: run a Cloudflare connector tool with a JS code string.

Usage:  python cf_call.py <tool_name> <code_file> [account_id]
Reads the JS async-arrow function from <code_file>, wraps it in the tool's
JSON argument envelope, and calls the connector through mcode-tools.
"""
import json
import subprocess
import sys

tool = sys.argv[1]
code = open(sys.argv[2], "r", encoding="utf-8").read()
args = {"code": code}
if len(sys.argv) > 3 and sys.argv[3]:
    args["account_id"] = sys.argv[3]
args_file = sys.argv[2] + ".args.json"
with open(args_file, "w", encoding="utf-8") as handle:
    json.dump(args, handle)
proc = subprocess.run(
    ["cmd", "/c", "mcode-tools", "connector", "call", tool, "--args-file", args_file],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
)
sys.stdout.write(proc.stdout or "")
if proc.stderr:
    sys.stderr.write(proc.stderr)
sys.exit(proc.returncode)
