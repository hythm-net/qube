#!/usr/bin/env python3
"""hythm.net's mail on Migadu, set up through its admin API; idempotent.

- the owner's mailbox `haytham.elganiny@` (made by hand) and the address given out, `me@hythm.net`
  (decided 2026-10-29: it needs no spelling when said aloud, only the domain does). me@ is an
  identity on the mailbox that logs in with the mailbox's password, so mail apps sign in as me@
  and send as me@ (with an alias they sent as the mailbox's own address)
- wildcard sending on the mailbox, so mail can go out as me@ and any per-service address
- rewrite `me.*` → the mailbox: per-service addresses like `me.netflix@hythm.net` work without
  setup; random guesses (info@, sales@) still bounce

Not managed here: the identity noreply@hythm.net on admin@, the cluster smtp-relay's login. Its
password lives only in Bitwarden qube/smtp_relay (made 2026-10-29).

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
MAILBOX, ADDRESS, NAME = "haytham.elganiny", "me", "Haytham Elganiny"
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
    for i in api(f"/mailboxes/{MAILBOX}/identities")["identities"]:
        print(f"identity {i['address']} on {MAILBOX}@: password_use={i['password_use']} imap={i['may_access_imap']}")
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
    if ADDRESS in {a["local_part"] for a in api("/aliases")["address_aliases"]}:
        raise SystemExit(f"{ADDRESS}@{DOMAIN} is an alias: delete it, it's an identity now (an alias can't be signed in as)")
    identities = {i["local_part"]: i for i in api(f"/mailboxes/{MAILBOX}/identities")["identities"]}
    if ADDRESS not in identities:
        api(f"/mailboxes/{MAILBOX}/identities", "POST", {"name": NAME, "local_part": ADDRESS, "password_use": "mailbox"})
    elif identities[ADDRESS]["password_use"] != "mailbox":
        api(f"/mailboxes/{MAILBOX}/identities/{ADDRESS}", "PUT", {"password_use": "mailbox"})
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
