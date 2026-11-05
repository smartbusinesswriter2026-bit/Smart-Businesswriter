#!/usr/bin/env python
"""Local product server launcher (Phase 2b).

Single local install/run path for the frozen core + product layer:

    python scripts/serve.py                 # http://127.0.0.1:8000
    python scripts/serve.py --port 8765
    python scripts/serve.py --no-sandbox    # development only
    python scripts/serve.py --check         # print the resolved configuration and exit

Environment it understands (documented in README.md):
    BP_CASES_DIR    case store directory (default <repo>/cases)
    BP_STATE_DIR    logs/backups (default <repo>/state)
    BP_REQUEST_LOG  request log path; "" disables it
    BP_SOURCE_ENV   source credentials file (default <repo>/Backend/.env)
    BP_LLM_PROVIDER / BP_LLM_MODEL / provider API key - optional model assistance (off by default)

The launcher adds `<repo>/src` to sys.path, so it works from a clean checkout
without installing anything.  It prints the URL and the health/log locations
and serves until interrupted.
"""

import json
import os
import sys


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse(argv):
    options = {"host": "127.0.0.1", "port": 8000, "sandbox": True, "check": False}
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ("--host", "--port"):
            if index + 1 >= len(argv):
                raise SystemExit("missing value for %s" % argument)
            value = argv[index + 1]
            if argument == "--port":
                try:
                    options["port"] = int(value)
                except ValueError:
                    raise SystemExit("--port needs an integer")
            else:
                options["host"] = value
            index += 2
            continue
        if argument == "--no-sandbox":
            options["sandbox"] = False
            index += 1
            continue
        if argument == "--check":
            options["check"] = True
            index += 1
            continue
        if argument in ("-h", "--help"):
            print(__doc__)
            raise SystemExit(0)
        raise SystemExit("unknown argument %r (try --help)" % argument)
    return options


def main(argv=None):
    options = _parse(sys.argv[1:] if argv is None else argv)
    root = _project_root()
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from bp.product import ops   # noqa: E402  (product layer only: health/log/state paths)
    from bp.product import source_env   # noqa: E402  (loads only the two search keys)
    web = source_env.load_web_credentials()
    config = {"format": "bp-launcher/1", "host": options["host"], "port": options["port"],
              "sandbox": options["sandbox"], "project_root": root,
              "case_store": str(ops.case_store.cases_dir()), "state_dir": str(ops.state_dir()),
              "request_log": str(ops.request_log_path()) if ops.request_log_path() else None,
              "web_search": {"order": ["opengo", "deepseek", "brave", "firecrawl"],
                             "opengo": web["opengo"], "deepseek": web["deepseek"],
                             "brave": web["brave"],
                             "firecrawl": web["firecrawl"] or web["firecrawl_keyless"],
                             "credentials_from": web["path"], "loaded": web["loaded"]},
              "model": {"provider": "opencode-go", "model": web["model"],
                        "prose_model": web["prose_model"],
                        "configured": web["opengo_key"]},
              "academic_search": {"semantic_scholar": web["semantic_scholar"]},
              "market_data": {"alpha_vantage": web.get("alpha_vantage", False),
                              "massive": web.get("massive", False),
                              "note": "institutional keys from Backend/.env, shared by every user"},
              "python": sys.version.split()[0]}
    if options["check"]:
        print(json.dumps(config, indent=2))
        return 0
    from bp import server   # noqa: E402  (the frozen core server, imported only when serving)
    server._load_local_keys()
    try:
        server.serve(options["port"], host=options["host"], sandbox=options["sandbox"])
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
