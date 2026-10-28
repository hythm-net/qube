# Bootstrapping qube from scratch

Everything below is driven by `task` from the repo root. Secrets come from Bitwarden Secrets Manager
(project `qube`, `8cfc9211-…`); nothing secret lives in this repo.

## Prerequisites (outside the repo)

| What | Where / how |
|---|---|
| Tools | `task bws talosctl kubectl helmfile helm kustomize minijinja-cli yq jq zstd curl flux` (the versions Renovate tracks are in the repo; `.mise.toml` only sets env) |
| `BWS_ACCESS_TOKEN` | A Bitwarden **machine account** access token with read access to the `qube` project. Existing tokens cannot be read back; on a new workstation create a new one in the Bitwarden web vault → Secrets Manager → Machine accounts → Access tokens. Export it in the shell (`export BWS_ACCESS_TOKEN=…`), don't pass it only as a task variable. |
| Bitwarden keys | `talos` (the secrets bundle: `MACHINE_CA_*`, `CLUSTER_*`), the bot secret `novyxz` (`e6c289ae-…`: `BOT_APP_ID`, `BOT_APP_INSTALLATION_ID` = the `hythm-net` installation, `BOT_APP_PRIVATE_KEY`, base64-encoded, for the `novyxz` GitHub App), `qubetoken` (the store's own credential), plus the app keys Flux reads later: `actions_runner alertmanager autobrr cloudflare flux grafana lyl prowlarr qui radarr sabnzbd seerr smtp_relay sonarr volsync_template`. `lyl` holds `ELEVENLABS_API_KEY`, `ARCHIVE_DEPLOY_KEY` (the write deploy key of `hythm7/lyl-archive`, an SSH private key) and `GHCR_TOKEN` (a classic token with `read:packages` only: the pull secret of the private `ghcr.io/hythm7/lyl`). |
| GitHub | The repo `hythm-net/qube` with the `novyxz` app installed on the `hythm-net` org (Flux pulls with it; `BOT_APP_INSTALLATION_ID` is that org installation). Repo secrets `BOT_APP_CLIENT_ID` / `BOT_APP_PRIVATE_KEY` only matter for CI, not for bootstrap. |
| DNS (OPNsense) | Host overrides `vore.internal → 10.1.10.10`, `qube.internal → 10.1.20.254` (Cilium VIP), `chthon.internal → 10.1.10.5` (NFS), plus the Unbound query-forward `hythm.net → 10.1.20.253` (k8s-gateway) and overrides `internal.hythm.net → .251`, `external.hythm.net → .252`. `.internal` is the router-owned machine zone and must resolve before the cluster exists; `hythm.net` is the services zone answered by the cluster. |
| Cloudflare | Zone `hythm.net`; the `cloudflare` Bitwarden key holds the API token (DNS edit on the zone) and the tunnel `kube` id/secret; `external.hythm.net` is a hand-made CNAME to the tunnel. |
| NFS | `chthon.internal:/data/@media` and `/data/@backup/kopia` (volsync repository). Exports require reserved ports — never add `noresvport`. |
| Install media | `task talos:generate-iso VERSION=v1.14.2` builds the factory ISO with the repo's schematic (`talos/schematic.yaml.j2`, incl. `nfsrahead`). Boot the node from it; it waits in maintenance mode. |

## Order

```sh
export BWS_ACCESS_TOKEN=…                 # see above
task talos:generate-talosconfig           # talos/talosconfig from the Bitwarden bundle (gitignored)
task bootstrap:cluster                    # = nodes -> talos -> apps, each idempotent:
#   nodes : renders cluster.yaml.j2 + networking + nodes/<n> + <type>.yaml.j2 and applies it --insecure
#           (skips nodes that already answer with "certificate required")
#   talos : talosctl bootstrap until etcd says AlreadyExists, then fetches kubernetes/kubeconfig
#   apps  : points kubectl at the node IP (the VIP only exists once Cilium runs), waits for the node,
#           applies bootstrap/kustomize/apps (namespaces, the BWS token Secret, github-app-auth),
#           applies the CRDs from bootstrap/helmfile/crds.yaml, then syncs bootstrap/helmfile/apps.yaml:
#           cilium (+ VIP/BGP config hook) -> coredns -> cert-manager (+ issuers, Bitwarden SDK cert)
#           -> external-secrets (+ ClusterSecretStore) -> flux-operator -> flux-instance
task talos:renew-talosconfig              # optional: 5-year admin cert instead of the 1-year default
```

From there Flux reconciles `kubernetes/` on its own. Watch with `flux get ks -A` and `flux get hr -A`.

## After bootstrap

- **Data**: every app with the `volsync` component gets a `ReplicationDestination` whose `restore-once`
  trigger fires when it is first created, restoring the PVC from the kopia repository on `chthon`. The app
  Deployment is created at the same time, so if an app comes up with empty state, suspend it and run
  `task volsync:restore NS=<ns> APP=<app>` for that app.
- **Cloudflare / tunnel**: nothing to do; external-dns recreates the `*.hythm.net` CNAMEs.
- **GPU**: if a pod claiming the GPU stays Pending and `kubectl get resourceslices -A` is empty, delete the
  `k8s-gpu-dra-driver` pod once.
- **Talos**: `task talos:apply-node NODE=vore` re-applies config; `task talos:upgrade-node NODE=vore`
  upgrades to the installer image pinned in `talos/cluster.yaml.j2` (uses a powercycle reboot; if
  `talosctl` gives up before the node is Ready it leaves the node cordoned — `kubectl uncordon vore`).
  After changing an `EtcFileConfig` the kubelet keeps the old file until `talosctl service kubelet restart`.
