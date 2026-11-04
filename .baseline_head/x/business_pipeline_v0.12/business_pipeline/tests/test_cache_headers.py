"""Every response must refuse to be cached.

`server.py` computes every response from the checkout on disk, so a cached copy is
always stale and - worse - looks current. CHANGELOG 0.69 claimed the server sent
`Cache-Control: no-store` / `Pragma: no-cache`; it did not, and during the 0.73
catalogue correction a browser kept serving the old catalogue from its cache after
the server had been restarted with corrected data.

This is the trap: it fails on a server that sends neither header.
"""

import os
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import server  # noqa: E402


class CacheHeadersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _headers(self, path):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path))
        with urllib.request.urlopen(req, timeout=20) as r:
            return {k.lower(): v for k, v in r.headers.items()}

    def test_the_workbench_document_is_not_cacheable(self):
        h = self._headers("/")
        self.assertEqual(h.get("cache-control"), "no-store",
                         "the workbench page must not be cached; an old copy looks current")
        self.assertEqual(h.get("pragma"), "no-cache")

    def test_api_responses_are_not_cacheable(self):
        h = self._headers("/api/health")
        self.assertEqual(h.get("cache-control"), "no-store",
                         "API data is recomputed per request and must not be cached")
        self.assertEqual(h.get("pragma"), "no-cache")


if __name__ == "__main__":
    unittest.main()
