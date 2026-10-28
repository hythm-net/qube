#!/usr/bin/env python3
"""Delete the Cloudflare records an external-dns owner left behind, so a renamed owner can recreate them.

external-dns (registry=txt) only touches records whose ownership TXT names its own owner id.
After `--txt-owner-id` changes (kube -> qube with the rework, docs/rework.md D6), the old
records stay and the new owner skips them. This lists every record the old owner's TXTs
name, plus those TXTs; `--delete` removes them, and external-dns recreates them within a
minute. Records no TXT names (external.hythm.net, direct.hythm.net, mail, the apex) are
never touched.

    export BWS_ACCESS_TOKEN=…
    bootstrap/cloudflare-drop-owner.py kube              # dry run: what would go
    bootstrap/cloudflare-drop-owner.py kube --delete
"""
import argparse
import json
import re
import subprocess
import urllib.request

PROJECT = "8cfc9211-d42e-45af-a73f-1e52d95c417b"  # Bitwarden qube
ZONE = "hythm.net"
API = "https://api.cloudflare.com/client/v4"


def api(token: str, path: str, method: str = "GET") -> dict:
    req = urllib.request.Request(f"{API}{path}", method=method, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("owner", help="the old --txt-owner-id, e.g. kube")
    p.add_argument("--delete", action="store_true", help="delete instead of listing")
    args = p.parse_args()

    secrets = json.loads(subprocess.run(["bws", "secret", "list", PROJECT, "-o", "json"],
                                        check=True, capture_output=True, text=True).stdout)
    token = json.loads(next(s["value"] for s in secrets if s["key"] == "cloudflare"))["CLOUDFLARE_API_TOKEN"]
    zone = api(token, f"/zones?name={ZONE}")["result"][0]["id"]
    records = api(token, f"/zones/{zone}/dns_records?per_page=1000")["result"]

    owned = [r for r in records if r["type"] == "TXT" and f"external-dns/owner={args.owner}" in r["content"]]
    prefix = re.compile(rf"^{re.escape(args.owner)}\.[a-z]+-")
    hosts = {prefix.sub("", r["name"]) for r in owned}
    targets = [r for r in records if r["type"] != "TXT" and r["name"] in hosts]

    for r in sorted(targets, key=lambda r: r["name"]) + sorted(owned, key=lambda r: r["name"]):
        print(f"{'deleting' if args.delete else 'would delete'} {r['type']:5} {r['name']}"
              + (f" -> {r['content']}" if r["type"] != "TXT" else ""))
        if args.delete:
            api(token, f"/zones/{zone}/dns_records/{r['id']}", method="DELETE")
    print(f"{len(targets)} records and {len(owned)} ownership TXTs owned by {args.owner} in {ZONE}"
          + ("" if args.delete else " (dry run; add --delete)"))


if __name__ == "__main__":
    main()
