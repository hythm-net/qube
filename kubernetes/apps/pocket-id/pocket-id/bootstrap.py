#!/usr/bin/env python3
"""Pocket ID's configuration through its API, idempotent: run it after any fresh start or data loss.

- groups family / friends / admins, with the admin `hythm` in family and admins
- one OIDC client per app, with a fixed id, its callback URLs and the groups allowed to use it
- each client's secret is the one in Bitwarden (`qube`/`pocket-id`, *_CLIENT_SECRET), and only that one
- email through the cluster's smtp-relay as noreply@hythm.net: admins can email a sign-in link, and
  everyone gets a mail when they sign in from a browser Pocket ID doesn't recognize. Signing in by
  emailed code from the login page stays off: the passkey is the only way in on your own.

Passkeys can't be set up from here: `--login-link USER` prints a one-time sign-in link (1h) to
register one, and `--email-link USER` mails it to the user instead (24h). Nothing secret is printed
otherwise.

    export BWS_ACCESS_TOKEN=…
    kubernetes/apps/pocket-id/pocket-id/bootstrap.py
    kubernetes/apps/pocket-id/pocket-id/bootstrap.py --login-link hythm
    kubernetes/apps/pocket-id/pocket-id/bootstrap.py --email-link Lolla

v2.19 lost every client, group and passkey on the upgrade from v2.18 (2026-10-21; found 10-28).
"""
import argparse
import json
import subprocess
import urllib.error
import urllib.request

PROJECT = "8cfc9211-d42e-45af-a73f-1e52d95c417b"  # Bitwarden qube
API = "https://id.hythm.net/api"
ADMIN = "hythm"
GROUPS = {"family": "Family", "friends": "Friends", "admins": "Admins"}
ADMIN_GROUPS = ["family", "admins"]
# id: (name, Bitwarden key of its secret, allowed groups, callback URLs)
CLIENTS = {
    "immich": ("Immich", "IMMICH_CLIENT_SECRET", ["family"], [
        "https://photos.hythm.net/auth/login", "https://photos.hythm.net/user-settings", "app.immich:///oauth-callback"]),
    "paperless": ("Paperless", "PAPERLESS_CLIENT_SECRET", ["family"], [
        "https://documents.hythm.net/accounts/oidc/pocket-id/login/callback/"]),
    "open-webui": ("Chat", "OPEN_WEBUI_CLIENT_SECRET", ["family"], ["https://chat.hythm.net/oauth/oidc/callback"]),
    "grafana": ("Grafana", "GRAFANA_CLIENT_SECRET", ["admins"], ["https://grafana.hythm.net/login/generic_oauth"]),
    "jellyfin": ("Jellyfin", "JELLYFIN_CLIENT_SECRET", ["family", "friends"], [
        "https://jellyfin.hythm.net/sso/OID/redirect/pocket-id"]),
}
# smtp-relay accepts mail from the cluster without a login (maddy, no TLS inside the cluster) and
# sends it on through Migadu, where its identity noreply@hythm.net may only send as itself
EMAIL = {
    "smtpHost": "smtp-relay.networking.svc.cluster.local",
    "smtpPort": "25",
    "smtpFrom": "noreply@hythm.net",
    "smtpUser": "",
    "smtpPassword": "",
    "smtpTls": "none",
    "smtpSkipCertVerify": "false",
    "emailOneTimeAccessAsAdminEnabled": "true",
    "emailOneTimeAccessAsUnauthenticatedEnabled": "false",
    "emailLoginNotificationMode": "browserRecognition",
    "emailApiKeyExpirationEnabled": "true",
}


def secrets() -> dict:
    out = subprocess.run(["bws", "secret", "list", PROJECT, "-o", "json"], check=True, capture_output=True, text=True).stdout
    return json.loads(next(s["value"] for s in json.loads(out) if s["key"] == "pocket-id"))


class Api:
    def __init__(self, key: str):
        self.key = key

    def __call__(self, path: str, method: str = "GET", body=None):
        req = urllib.request.Request(f"{API}{path}", method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"X-API-Key": self.key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            data = r.read()
        return json.loads(data) if data else None

    def exists(self, path: str) -> bool:
        try:
            self(path)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise


def user_id(api: Api, username: str) -> str:
    return next(u["id"] for u in api(f"/users?search={username}")["data"] if u["username"] == username)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    links = p.add_mutually_exclusive_group()
    links.add_argument("--login-link", metavar="USER", help="print a one-time sign-in link for USER instead")
    links.add_argument("--email-link", metavar="USER", help="email USER a one-time sign-in link (24h) instead")
    args = p.parse_args()
    s = secrets()
    api = Api(s["STATIC_API_KEY"])

    if args.login_link:
        token = api(f"/users/{user_id(api, args.login_link)}/one-time-access-token", "POST", {"ttl": "1h"})["token"]
        print(f"https://id.hythm.net/lc/{token}")
        return
    if args.email_link:
        api(f"/users/{user_id(api, args.email_link)}/one-time-access-email", "POST", {"ttl": "24h"})
        print(f"emailed {args.email_link} a sign-in link (24h)")
        return

    config = {c["key"]: c["value"] for c in api("/application-configuration/all")}
    if any(config.get(k) != v for k, v in EMAIL.items()):
        api("/application-configuration", "PUT", {**config, **EMAIL})
    print(f"email: {EMAIL['smtpFrom']} via {EMAIL['smtpHost']}, sign-in alerts: {EMAIL['emailLoginNotificationMode']}")

    groups = {g["name"]: g["id"] for g in api("/user-groups?pagination%5Blimit%5D=100")["data"]}
    for name, friendly in GROUPS.items():
        if name not in groups:
            groups[name] = api("/user-groups", "POST", {"name": name, "friendlyName": friendly})["id"]
    admin = user_id(api, ADMIN)
    for name in ADMIN_GROUPS:
        members = {u["id"] for u in api(f"/user-groups/{groups[name]}")["users"]} | {admin}
        api(f"/user-groups/{groups[name]}/users", "PUT", {"userIds": sorted(members)})
    print("groups:", ", ".join(f"{n} ({len(api(f'/user-groups/{i}')['users'])} members)" for n, i in groups.items()))

    for cid, (name, skey, allowed, callbacks) in CLIENTS.items():
        body = {"name": name, "callbackURLs": callbacks, "isGroupRestricted": True, "pkceEnabled": False, "isPublic": False}
        if api.exists(f"/oidc/clients/{cid}"):
            api(f"/oidc/clients/{cid}", "PUT", body)
        else:
            api("/oidc/clients", "POST", {**body, "id": cid})
        want = s[skey]
        existing = api(f"/oidc/clients/{cid}/secrets")
        if not any(x["prefix"] == want[:4] for x in existing):
            api(f"/oidc/clients/{cid}/secrets", "POST", {"secret": want})
        for x in api(f"/oidc/clients/{cid}/secrets"):  # a new client also gets a generated secret: drop it
            if x["prefix"] != want[:4]:
                api(f"/oidc/clients/{cid}/secrets/{x['id']}", "DELETE")
        api(f"/oidc/clients/{cid}/allowed-user-groups", "PUT", {"userGroupIds": [groups[g] for g in allowed]})
        print(f"client {cid}: groups {allowed}, {len(api(f'/oidc/clients/{cid}/secrets'))} secret, {len(callbacks)} callbacks")


if __name__ == "__main__":
    main()
