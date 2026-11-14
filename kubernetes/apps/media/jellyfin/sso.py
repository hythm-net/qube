#!/usr/bin/env python3
"""Jellyfin sign-in through Pocket ID (9p4 SSO plugin), set up through Jellyfin's API; idempotent.

- installs the SSO Authentication plugin from its repository (restarting Jellyfin once)
- provider `pocket-id`: Pocket ID client `jellyfin` (kubernetes/apps/pocket-id/pocket-id/bootstrap.py),
  groups family/friends may sign in, admins become Jellyfin admins, usernames from Pocket ID;
  after each SSO sign-in the account goes back to Jellyfin's normal provider, so passwords keep working
- a "Sign in with Pocket ID" button on the login page, and Quick Connect on (TV apps can't do SSO)
- remote streams capped at 8 Mbps, transcoded on the GPU: the home upload is ~23 Mbps, shared by
  everyone watching from outside. Jellyfin sees each viewer's own address through Envoy (a trusted
  proxy), so home and WireGuard keep full quality (restarts Jellyfin when those settings change)

Keys come from Bitwarden (qube/jellyfin JELLYFIN_API_KEY, qube/pocket-id JELLYFIN_CLIENT_SECRET);
nothing secret is printed.

    export BWS_ACCESS_TOKEN=…
    kubernetes/apps/media/jellyfin/sso.py
"""
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

PROJECT = "8cfc9211-d42e-45af-a73f-1e52d95c417b"  # Bitwarden qube
JELLYFIN = "https://jellyfin.hythm.net"
PROVIDER = "pocket-id"
REPO = {"Name": "SSO Authentication",
        "Url": "https://raw.githubusercontent.com/9p4/jellyfin-plugin-sso/manifest-release/manifest.json", "Enabled": True}
PLUGIN, GUID, VERSION = "SSO Authentication", "505ce9d1-d916-42fa-86ca-673ef241d7df", "4.0.0.4"
DEFAULT_AUTH = "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider"
# envoy (pods) is a trusted proxy: its X-Forwarded-For carries the viewer's address (ETP Local).
# Home VLANs and WireGuard are 10.1.0.0/16; pods talking to the Service directly are local too.
NETWORK = {"KnownProxies": ["10.244.0.0/16"], "LocalNetworkSubnets": ["10.1.0.0/16", "10.244.0.0/16"]}
REMOTE_BITRATE = 8_000_000  # bits/s per stream, outside the local networks
BUTTON = (f'<form action="{JELLYFIN}/sso/OID/start/{PROVIDER}">'
          '<button class="raised block emby-button button-submit">Sign in with Pocket ID</button></form>')
# the login message sits in .readOnlyContent with the Quick Connect and Forgot Password buttons:
# fill that width like they do
BUTTON_CSS = (".loginDisclaimer, .loginDisclaimer form { display: block; width: 100%; }\n"
              ".loginDisclaimer form button { width: 100%; margin: 0; }")


def bitwarden() -> dict:
    out = subprocess.run(["bws", "secret", "list", PROJECT, "-o", "json"], check=True, capture_output=True, text=True).stdout
    return {s["key"]: json.loads(s["value"]) for s in json.loads(out) if s["key"] in ("jellyfin", "pocket-id")}


class Api:
    def __init__(self, key: str):
        self.key = key

    def __call__(self, path: str, method: str = "GET", body=None):
        req = urllib.request.Request(f"{JELLYFIN}{path}", method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": f'MediaBrowser Token="{self.key}"',
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        return json.loads(data) if data and data[:1] in (b"{", b"[", b'"') else None


def wait_for_jellyfin(api: Api) -> None:
    time.sleep(10)
    for _ in range(60):
        try:
            api("/System/Info")
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(5)
    raise SystemExit("Jellyfin didn't come back within 5 minutes")


def main() -> None:
    bw = bitwarden()
    api = Api(bw["jellyfin"]["JELLYFIN_API_KEY"])
    print("Jellyfin", api("/System/Info")["Version"])

    repos = api("/Repositories")
    if not any(r["Url"] == REPO["Url"] for r in repos):
        api("/Repositories", "POST", repos + [REPO])
        print("added the plugin repository")

    # the plugin registers as "SSO-Auth", not its package name: match by GUID
    def find_plugin():
        return next((p for p in api("/Plugins") if p["Id"].replace("-", "") == GUID.replace("-", "")), None)

    if find_plugin() is None:
        q = urllib.parse.urlencode({"assemblyGuid": GUID, "version": VERSION, "repositoryUrl": REPO["Url"]})
        api(f"/Packages/Installed/{urllib.parse.quote(PLUGIN)}?{q}", "POST")
        print(f"installing {PLUGIN} {VERSION}, restarting Jellyfin")
        time.sleep(15)
        api("/System/Restart", "POST")
        wait_for_jellyfin(api)
    p = find_plugin()
    print(f"plugin {p['Name']} {p['Version']}: {p['Status']}")

    api(f"/sso/OID/Add/{PROVIDER}", "POST", {
        "oidEndpoint": "https://id.hythm.net",
        "oidClientId": "jellyfin",
        "oidSecret": bw["pocket-id"]["JELLYFIN_CLIENT_SECRET"],
        "enabled": True,
        "enableAuthorization": True,
        "enableAllFolders": True,
        "enabledFolders": [],
        "roles": ["family", "friends"],
        "adminRoles": ["admins"],
        "enableFolderRoles": False,
        "folderRoleMapping": [],
        "roleClaim": "groups",
        "oidScopes": ["groups"],
        "defaultUsernameClaim": "preferred_username",
        "defaultProvider": DEFAULT_AUTH,
        "schemeOverride": "https",
    })
    cfg = api("/sso/OID/Get")[PROVIDER]
    print(f"provider {PROVIDER}: enabled={cfg['Enabled']} roles={cfg['Roles']} admins={cfg['AdminRoles']}")

    # the login page shows only the button (the old Ahla greeting is gone for good)
    branding = api("/System/Configuration/branding")
    if branding.get("LoginDisclaimer") != BUTTON or branding.get("CustomCss") != BUTTON_CSS:
        api("/System/Configuration/branding", "POST", {**branding, "LoginDisclaimer": BUTTON, "CustomCss": BUTTON_CSS})
    print("login page: Sign in with Pocket ID")

    system = api("/System/Configuration")
    want = {"QuickConnectAvailable": True, "RemoteClientBitrateLimit": REMOTE_BITRATE}
    if any(system.get(k) != v for k, v in want.items()):
        api("/System/Configuration", "POST", {**system, **want})
    print(f"Quick Connect: on; remote streams up to {REMOTE_BITRATE / 1e6:g} Mbps")

    # read once at startup: a change needs a restart (it ends whatever is playing)
    network = api("/System/Configuration/network")
    if any(network.get(k) != v for k, v in NETWORK.items()):
        api("/System/Configuration/network", "POST", {**network, **NETWORK})
        print("network settings changed, restarting Jellyfin")
        api("/System/Restart", "POST")
        wait_for_jellyfin(api)
    print(f"proxies {NETWORK['KnownProxies']}, local {NETWORK['LocalNetworkSubnets']}")


if __name__ == "__main__":
    main()
