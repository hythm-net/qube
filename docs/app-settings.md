# Settings made inside apps

Flux deploys each app from Git; what an app keeps inside itself (its admin pages, its database)
comes back from that app's backup, the same way for every app ([rebuild.md §7](rebuild.md#7-app-data)).
No per-app scripts: this page is the record of what was set by hand and why. Change a setting in
the app, then change its line here in the same breath.

The one tool is Pocket ID's [`bootstrap.py`](../kubernetes/apps/pocket-id/pocket-id/bootstrap.py):
it wires the Pocket ID side of every app's sign-in (clients, groups, secrets from Bitwarden) and
sends new family members their sign-in link. It's the hub, not one app's restore.

## Jellyfin

Restored with its config volume (VolSync).

| Setting | Value | Why |
|---|---|---|
| Plugin | SSO Authentication 4.0.0.4 (repository `https://raw.githubusercontent.com/9p4/jellyfin-plugin-sso/manifest-release/manifest.json`) | sign-in through Pocket ID |
| SSO provider `pocket-id` | endpoint `https://id.hythm.net`, client `jellyfin`, secret Bitwarden `qube`/`pocket-id` `JELLYFIN_CLIENT_SECRET`; roles `family`, `friends`; admin role `admins`; all libraries; role claim `groups` (scope `groups`); username claim `preferred_username`; default provider Jellyfin's own; scheme override `https` | only Pocket ID's family and friends get in. After each SSO sign-in the account goes back to Jellyfin's normal provider, so local passwords keep working |
| Login disclaimer (Branding) | `<form action="https://jellyfin.hythm.net/sso/OID/start/pocket-id"><button class="raised block emby-button button-submit">Sign in with Pocket ID</button></form>` | the button on the login page |
| Custom CSS (Branding) | `.loginDisclaimer, .loginDisclaimer form { display: block; width: 100%; }` `.loginDisclaimer form button { width: 100%; margin: 0; }` | the button as wide as Quick Connect's |
| Quick Connect | on | TVs and Moonfin can't do SSO: they sign in with a code |
| Networking: known proxies | `10.244.0.0/16` | Envoy's pods: Jellyfin reads the viewer's address from `X-Forwarded-For` (the gateways are `externalTrafficPolicy: Local`). Without it every viewer looks local |
| Networking: LAN networks | `10.1.0.0/16`, `10.244.0.0/16` | home VLANs and WireGuard, and pods calling the Service directly |
| Playback: remote bitrate limit | 8 Mbps | the home upload is ~23 Mbps (Spectrum, 2026-11-14), shared by everyone watching from outside |
| Transcoding: hardware acceleration | none (CPU) | the GPU decodes and encodes, but the VAAPI scaler fails on gfx1151 with Mesa 25.0.7 (`si_vpe_construct_blt`) and libplacebo tone mapping too. Not solved yet |

Networking changes need a restart. Check: `/System/Endpoint` from a pod gives `IsInNetwork: true`,
and with `X-Forwarded-For: 8.8.8.8` `false`.

## Paperless

Restored from the nightly export (users, groups, permissions, workflows and UI settings are in it).

| Setting | Value | Why |
|---|---|---|
| Group `family` | add/change/delete/view on documents, tags, correspondents, document types, storage paths, custom fields (and their values), notes, saved views (and rules), share links (and bundles), mail accounts, mail rules, UI settings; change/view tasks; view processed mail, history, users, groups | one archive the family shares. Nothing of the admin's: editing users or groups, workflows, app config. Pocket ID sign-ups join it (`PAPERLESS_SOCIAL_ACCOUNT_DEFAULT_GROUPS` in the HelmRelease) |
| Workflow "Share with family" | on Document Added; assign view and edit to group `family` | every new document, whoever adds it, is the family's |
| `hythm`'s default permissions (Settings → Permissions) | view and edit: group `family` | tags and the like made in the web UI are shared too (documents are the workflow's). `hythm` is a superuser and sees the rest |

## Immich

Restored from the nightly database dump (`system_metadata`).

| Setting | Value | Why |
|---|---|---|
| OAuth | issuer `https://id.hythm.net`, client `immich`, secret Bitwarden `qube`/`pocket-id` `IMMICH_CLIENT_SECRET`, scope `openid email profile`, auto-register on, auto-launch off, mobile redirect override off, button "Sign in with Pocket ID" | sign-in through Pocket ID. A first sign-in links an existing account with the same email |
| Video transcoding: hardware acceleration | VAAPI | the GPU through an `adminAccess` claim |
| Storage template | on, `{{y}}/{{MM}}/{{dd}}/{{filename}}` | originals on chthon sorted by date |
| Machine learning | defaults (smart search, faces, OCR, duplicates) | the default smart-search model is English-first |

## Seerr

Restored with its config volume (VolSync).

| Setting | Value | Why |
|---|---|---|
| 4K server entries | the same radarr/sonarr services, with the 2160p profiles and the roots `/media/movies`, `/media/shows` | 4K is a quality profile, not separate instances; profiles come from recyclarr (Git) |

## Not listed

Open WebUI is set by environment in its HelmRelease, Grafana by grafana-operator, the *arr quality
profiles by recyclarr: they're in Git already. Any other app here keeps whatever its own setup left
(indexers, download clients and the like) and comes back with its volume; when something is set by
hand on purpose, it gets a section here.
