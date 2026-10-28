"""Small load probe for a running workbench (standard library only).

    python scripts/bench.py --url http://127.0.0.1:8000 --requests 500 --concurrency 16

It measures GET /api/health, GET /api/methods and GET /api/cases/subjects, which read state without
creating sessions, printing requests/second and the p50/p95 latency for each. It is a capacity probe,
not a benchmark of the computation; a run still spawns the sandbox per request.
"""

import argparse
import json
import statistics
import sys
import threading
import time
import urllib.request

PATHS = ("/api/health", "/api/methods", "/api/cases/subjects")


def _get(base, path):
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(base + path, timeout=30) as response:
            body = response.read()
            json.loads(body)
        return time.perf_counter() - started, None
    except Exception as error:  # noqa: BLE001 - the probe reports any failure
        return time.perf_counter() - started, repr(error)


def main():
    parser = argparse.ArgumentParser(description="Probe a running workbench")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    print("probing %s with %d requests at concurrency %d" % (base, args.requests, args.concurrency))
    failed_total = 0
    for path in PATHS:
        durations, errors, lock = [], [], threading.Lock()

        def worker():
            nonlocal failed_total
            for _ in range(args.requests // args.concurrency):
                elapsed, error = _get(base, path)
                with lock:
                    durations.append(elapsed)
                    if error:
                        errors.append(error)

        started = time.perf_counter()
        threads = [threading.Thread(target=worker) for _ in range(args.concurrency)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        wall = time.perf_counter() - started
        failed_total += len(errors)
        durations.sort()
        p50 = durations[len(durations) // 2] * 1000 if durations else 0
        p95 = durations[min(len(durations) - 1, int(len(durations) * 0.95))] * 1000 if durations else 0
        rate = len(durations) / wall if wall else 0
        print("%-24s %7.1f req/s  p50 %6.1f ms  p95 %6.1f ms  errors %d"
              % (path, rate, p50, p95, len(errors)))
        if errors:
            print("  first error: " + errors[0])
    return 1 if failed_total else 0


if __name__ == "__main__":
    sys.exit(main())
