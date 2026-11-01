"""Call any mcode-tools connector tool with a JSON args file.

Usage: python cf_tool.py <tool_name> <args_json_file>
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

tool = sys.argv[1]
args_file = sys.argv[2]
proc = subprocess.run(
    ["cmd", "/c", "mcode-tools", "connector", "call", tool, "--args-file", args_file],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
)
sys.stdout.write(proc.stdout or "")
if proc.stderr:
    sys.stderr.write(proc.stderr)
sys.exit(proc.returncode)
