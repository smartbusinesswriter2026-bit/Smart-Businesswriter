"""Print the suite count exactly as tests/test_docs_sync.py counts it (QA tool).

The gate runs `python -m unittest tests.test_docs_sync` from the app folder, where
``sys.path`` holds the app folder and ``src``.  A plain ``python qa/_count.py``
puts ``qa/`` first instead, which shadows a module during discovery and loses
cases — this tool first read 2878 where the gate read 2880 because of exactly
that.  So the script rebuilds the gate's context and then counts.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path = [item for item in sys.path if os.path.abspath(item or ".") != HERE]
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

print("SUITE_COUNT", unittest.TestLoader().discover(start_dir="tests").countTestCases())
