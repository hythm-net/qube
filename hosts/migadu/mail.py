#!/usr/bin/env python3
"""hythm.net's mail on Migadu, set up through its admin API; idempotent.

- the owner's mailbox `haytham.elganiny@` (made by hand; its name is only the login) and the address
  given out, `me@hythm.net`, an alias into it (decided 2026-10-29: it needs no spelling when said
  aloud, only the domain does)
- wildcard sending on the mailbox, so mail can go out as me@ and any per-service address
- rewrite `me.*` → the mailbox: per-service addresses like `me.netflix@hythm.net` work without
  setup; random guesses (info@, sales@) still bounce

The API login is Bitwarden `rune`/`migadu` (MIGADU_USER, MIGADU_API_KEY); nothing secret is printed.

    export BWS_ACCESS_TOKEN=…
    hosts/migadu/mail.py --show   # what's there, changes nothing
    hosts/migadu/mail.py
"""
import argparse
import base64
import json
import subprocess
import time
import urllib.error
import urllib.request

PROJECT = "b05890fc-97d9-4e5f-a734-b4ea00486b4f"  # Bitwarden rune
DOMAIN = "hythm.net"
API = f"https://api.migadu.com/v1/domains/{DOMAIN}"
MAILBOX, ADDRESS = "haytham.elganiny", "me"
REWRITE = {"name": "me-per-service", "local_part_rule": f"{ADDRESS}.*", "destinations": f"{MAILBOX}@{DOMAIN}"}


def login() -> str:
    out = subprocess.run(["bws", "secret", "list", PROJECT, "-o", "json"], check=True, capture_output=True, text=True).stdout
    s = json.loads(next(x["value"] for x in json.loads(out) if x["key"] == "migadu"))
    return base64.b64encode(f'{s["MIGADU_USER"]}:{s["MIGADU_API_KEY"]}'.encode()).decode()


class Api:
    def __init__(self, auth: str):
        self.auth = auth

    def __call__(self, path: str, method: str = "GET", body=None):
        time.sleep(1)  # Migadu blocked the home IP for a while after ~15 quick calls (2026-10-29)
        req = urllib.request.Request(f"{API}{path}", method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": f"Basic {self.auth}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")


def show(api: Api) -> None:
    for m in api("/mailboxes")["mailboxes"]:
        print(f"mailbox {m['address']}: {m['name']!r}, send={m['may_send']} receive={m['may_receive']}"
              f" wildcard_sender={m.get('wildcard_sender')}")
    for a in api("/aliases")["address_aliases"]:
        print(f"alias {a['address']} → {a['destinations']}")
    for r in api("/rewrites")["rewrites"]:
        print(f"rewrite {r['name']}: {r['local_part_rule']} → {r['destinations']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--show", action="store_true", help="list mailboxes, aliases and rewrites; change nothing")
    args = p.parse_args()
    api = Api(login())
    if args.show:
        show(api)
        return

    if MAILBOX not in {m["local_part"] for m in api("/mailboxes")["mailboxes"]}:
        raise SystemExit(f"no mailbox {MAILBOX}@{DOMAIN}: it holds the owner's mail, so it's made by hand, not here")
    aliases = {a["local_part"]: a for a in api("/aliases")["address_aliases"]}
    if ADDRESS not in aliases:
        api("/aliases", "POST", {"local_part": ADDRESS, "destinations": f"{MAILBOX}@{DOMAIN}"})
    elif aliases[ADDRESS]["destinations"] != [f"{MAILBOX}@{DOMAIN}"]:
        api(f"/aliases/{ADDRESS}", "PUT", {"destinations": f"{MAILBOX}@{DOMAIN}"})
    if not api(f"/mailboxes/{MAILBOX}").get("wildcard_sender"):
        api(f"/mailboxes/{MAILBOX}", "PUT", {"wildcard_sender": True})
    if not api(f"/mailboxes/{MAILBOX}").get("wildcard_sender"):
        raise SystemExit("Migadu didn't take wildcard_sender through the API: turn on Wildcard Sending for the mailbox in its admin")

    rewrites = {r["name"]: r for r in api("/rewrites")["rewrites"]}
    if REWRITE["name"] not in rewrites:
        api("/rewrites", "POST", REWRITE)
    elif (rewrites[REWRITE["name"]]["local_part_rule"], rewrites[REWRITE["name"]]["destinations"]) != \
            (REWRITE["local_part_rule"], [REWRITE["destinations"]]):
        api(f"/rewrites/{REWRITE['name']}", "PUT", REWRITE)
    show(api)


if __name__ == "__main__":
    main()
