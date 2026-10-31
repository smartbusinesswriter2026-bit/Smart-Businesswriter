"""Write the rclone remote that points at the corpus bucket.

Standard library only (C-02). The credentials never go into git and never
appear in a log line: the rclone config file is written under
`corpus-db/build/_secrets/`, which is gitignored, and the secret is printed
nowhere.

Two ways to supply the credential, both accepted by the Cloudflare dashboard:

  * Access Key ID + Secret Access Key  - what the dashboard shows.
  * API token id + API token value    - the S3 access key id is the token id
    and the S3 secret is the SHA-256 of the token value (Cloudflare's own
    recipe for using an API token with an S3 client).

Values are read from the environment first, then from the secrets env file.
"""

import argparse
import hashlib
import os
import sys

DEFAULT_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "_secrets", "rclone_corpus.env")
DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "_secrets", "rclone_corpus.conf")


class CredentialError(Exception):
    """A named gap in the credentials. The message says what is missing."""


def read_env_file(path):
    """Read a KEY=VALUE file. Blank lines and # comments are ignored."""
    values = {}
    if not os.path.isfile(path):
        return values
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def resolve(env_file=None):
    """Find the account id, the access key id and the secret access key."""
    values = {}
    values.update(read_env_file(env_file or DEFAULT_ENV_FILE))
    for key in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
                "R2_API_TOKEN_ID", "R2_API_TOKEN_VALUE", "R2_BUCKET"):
        if os.environ.get(key):
            values[key] = os.environ[key]

    account_id = values.get("R2_ACCOUNT_ID")
    access_key_id = values.get("R2_ACCESS_KEY_ID")
    secret_access_key = values.get("R2_SECRET_ACCESS_KEY")
    token_id = values.get("R2_API_TOKEN_ID")
    token_value = values.get("R2_API_TOKEN_VALUE")

    if not access_key_id and token_id and token_value:
        access_key_id = token_id
        secret_access_key = hashlib.sha256(token_value.encode("utf-8")).hexdigest()

    missing = []
    if not account_id:
        missing.append("R2_ACCOUNT_ID")
    if not access_key_id:
        missing.append("R2_ACCESS_KEY_ID (or R2_API_TOKEN_ID)")
    if not secret_access_key:
        missing.append("R2_SECRET_ACCESS_KEY (or R2_API_TOKEN_VALUE)")
    if missing:
        raise CredentialError(
            "missing credentials: %s. Put them in the environment or in %s. "
            "They are the Access Key ID and Secret Access Key of an R2 API "
            "token scoped to the corpus bucket." % (", ".join(missing), env_file or DEFAULT_ENV_FILE))

    return {
        "account_id": account_id,
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
        "bucket": values.get("R2_BUCKET", "smart-business-writer-corpus"),
    }


def write_config(credentials, path, remote="corpus-r2"):
    """Write the rclone config file for the Cloudflare R2 remote."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    body = (
        "[%s]\n"
        "type = s3\n"
        "provider = Cloudflare\n"
        "access_key_id = %s\n"
        "secret_access_key = %s\n"
        "endpoint = https://%s.r2.cloudflarestorage.com\n"
        "region = auto\n"
        "acl = private\n"
    ) % (remote, credentials["access_key_id"], credentials["secret_access_key"],
         credentials["account_id"])
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    write_parser = sub.add_parser("write", help="write the rclone config file")
    write_parser.add_argument("--env-file", default=DEFAULT_ENV_FILE)
    write_parser.add_argument("--config", default=DEFAULT_CONFIG)
    write_parser.add_argument("--remote", default="corpus-r2")

    describe_parser = sub.add_parser("describe", help="print what is configured")
    describe_parser.add_argument("--env-file", default=DEFAULT_ENV_FILE)

    args = parser.parse_args(argv)
    try:
        if args.command == "write":
            credentials = resolve(args.env_file)
            path = write_config(credentials, args.config, args.remote)
            print("rclone config written: %s" % path)
            print("remote: %s  bucket: %s  account: %s  access key: %s..."
                  % (args.remote, credentials["bucket"], credentials["account_id"],
                     credentials["access_key_id"][:6]))
            return 0
        if args.command == "describe":
            credentials = resolve(args.env_file)
            print(json.dumps({
                "account_id": credentials["account_id"],
                "bucket": credentials["bucket"],
                "access_key_id_prefix": credentials["access_key_id"][:6],
                "secret_present": bool(credentials["secret_access_key"]),
            }, indent=2))
            return 0
    except CredentialError as error:
        print("CREDENTIAL ERROR: %s" % error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    import json
    sys.exit(main())
