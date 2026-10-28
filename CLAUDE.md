# qube

Personal homelab on Kubernetes. Single-node Talos cluster (`vore`), reconciled from this repo by Flux, kept current by Renovate. Media stack (Jellyfin, *arr, Seerr, Wizarr) today; personal apps later.

## Layout

```
bootstrap/     helmfile + kustomize used once to bring the cluster up (needs BWS_ACCESS_TOKEN)
kubernetes/
  apps/        one dir per namespace, one Flux Kustomization per app (ks.yaml + app/…)
  components/  reusable kustomize components (volsync, alerts, namespace, …)
  flux/        flux-operator cluster definition + OCI repositories
talos/         machineconfig templates (minijinja) — cluster name `qube`, endpoint qube.internal
.taskfiles/    task targets (bootstrap, talos, kubernetes, volsync, github)
```

## Facts that matter

| | |
|---|---|
| GitHub | Org **`hythm-net`** (moved from `hythm7` 2026-10-27): `hythm-net/qube` (public: it holds deployments only) and the private `hythm-net/saves` (device config snapshots: OPNsense `os-git-backup`). A personal app keeps its code, image and secret values private: lyl's code is `hythm7/lyl`, its image `ghcr.io/hythm7/lyl` (decided 2026-10-05). Bot for Flux git auth, Renovate, workflows and the ARC runner: **`novyxz`** (App ID 2075588, public app, installed on `hythm7` and on `hythm-net`: installation 175773767, which Flux and the runner use). |
| Domain | **`hythm.net`**, hardcoded everywhere (no domain variables). Wildcard cert `hythm-net-tls` via cert-manager DNS01 (Cloudflare). The zone also carries mail records (Migadu/SES/Resend) and the apex A — never route the apex through the tunnel. |
| Ingress | Envoy Gateway: `envoy-external` (10.1.20.252, behind Cloudflare tunnel `kube`) and `envoy-internal` (10.1.20.251). `external.hythm.net` is a **hand-made** proxied CNAME to the tunnel; external-dns only manages HTTPRoute hostnames. |
| LAN DNS | k8s-gateway on 10.1.20.253 serves `hythm.net` with `fallthrough` + `forward . 1.1.1.1` (nodes resolve via OPNsense → loop otherwise). OPNsense Unbound forwards `hythm.net` there; host overrides `internal`/`external.hythm.net` win locally. |
| Secrets | Bitwarden Secrets Manager via external-secrets (`ClusterSecretStore bitwarden-secrets-manager`, project `8cfc9211…`). The store's own credential is the `qubetoken` key; its ExternalSecret is `creationPolicy: Orphan` on purpose — if the store shows `InvalidProviderConfig`, that Secret is missing. |
| GPU | AMD via DRA (`k8s-gpu-dra-driver`, DeviceClass `gpu.amd.com`). If a GPU pod is Pending with "cannot allocate all claims" and `kubectl get resourceslices -A` is empty, delete the kubelet-plugin pod. |
| CI | Flate diffs on PRs; Renovate every 4h (hosted Actions minutes are free for the public repo). Local check: `FLATE_PATH=$PWD/kubernetes/flux/cluster flate diff ks|hr`. |
| Upstream | Patterns follow buroa/home-ops and onedr0p/home-ops; translate (Jellyfin not Plex, Bitwarden not 1Password, openebs+volsync not rook-ceph). |

## Conventions

- Commits: conventional (`feat(namespace): …`, `fix(container): …`); PRs merged with rebase; `task github:pr:merge:all` merges open `novyxz` PRs.
- `kubeconfig`/`talosconfig` live in-repo (gitignored) and are wired by `.mise.toml`.
- Media apps keep their existing "Ahla" artwork/branding inside their own databases; that is intentional.
