<div align="center">

<img src="qube-logo.png" align="center" width="175px" height="175px"/>

### qube

_Home lab on Kubernetes — managed with Flux, Renovate, and GitHub Actions_

</div>

<div align="center">

[![Talos](https://kromgo.hythm.net/badges/talos_version)](https://talos.dev)&nbsp;&nbsp;
[![Kubernetes](https://kromgo.hythm.net/badges/kubernetes_version)](https://kubernetes.io)&nbsp;&nbsp;
[![Flux](https://kromgo.hythm.net/badges/flux_version)](https://fluxcd.io)&nbsp;&nbsp;

</div>

<div align="center">

[![Age](https://kromgo.hythm.net/badges/cluster_birth_age)](https://github.com/home-operations/kromgo)&nbsp;&nbsp;
[![Uptime](https://kromgo.hythm.net/badges/cluster_uptime_age)](https://github.com/home-operations/kromgo)&nbsp;&nbsp;
[![Nodes](https://kromgo.hythm.net/badges/cluster_node_count)](https://github.com/home-operations/kromgo)&nbsp;&nbsp;
[![Pods](https://kromgo.hythm.net/badges/cluster_pod_count)](https://github.com/home-operations/kromgo)&nbsp;&nbsp;

</div>

<div align="center">

[![CPU](https://kromgo.hythm.net/badges/cluster_cpu_usage)](https://github.com/home-operations/kromgo)&nbsp;&nbsp;
[![Memory](https://kromgo.hythm.net/badges/cluster_memory_usage)](https://github.com/home-operations/kromgo)&nbsp;&nbsp;

</div>

<div align="center">

[![Alerts](https://kromgo.hythm.net/badges/cluster_alert_count)](https://github.com/home-operations/kromgo)

</div>

---

## Overview

Single-node [Talos Linux](https://talos.dev) cluster running the home lab. Media stack:
[Jellyfin](https://jellyfin.org) (AMD GPU transcoding via DRA), the *arr stack,
[Seerr](https://github.com/seerr-team/seerr) for requests, and
[Wizarr](https://github.com/wizarrrr/wizarr) for invites. Everything is
reconciled from this repository by [Flux](https://fluxcd.io); dependencies are
updated by [Renovate](https://renovatebot.com). Machines, VLANs and tunnels are named
after Quake; the scheme is in [docs/lore.md](docs/lore.md).

## Repository layout

```
📁 bootstrap     # helmfile + kustomize used once to bring the cluster up
📁 docs          # lore.md: the Quake naming scheme
📁 kubernetes
  📁 apps        # one directory per namespace, one Flux Kustomization per app
  📁 components  # reusable kustomize components (volsync, alerts, namespace, …)
  📁 flux        # flux-operator cluster definition and OCI repositories
📁 talos         # machine configuration templates (minijinja)
```

## Bootstrap from scratch

Prerequisites (tools, the Bitwarden machine token, which Bitwarden keys must exist, the OPNsense
overrides) are listed in [`bootstrap/README.md`](bootstrap/README.md). Every step below is idempotent
and can be re-run.

```sh
# 0. secrets: a Bitwarden Secrets Manager machine-account token for the `qube` project
export BWS_ACCESS_TOKEN=…

# 1. install media: factory ISO built from talos/schematic.yaml.j2 (kernel args + extensions);
#    write it to a USB stick, boot the node, leave it in maintenance mode
task talos:generate-iso VERSION=v1.14.2

# 2. client credentials: talos/talosconfig (gitignored) minted from the Bitwarden `talos` bundle
task talos:generate-talosconfig

# 3. the cluster, end to end — or run the three stages one at a time:
task bootstrap:cluster
#    task bootstrap:nodes   # render cluster/controlplane/networking/node templates with the Bitwarden
#                           # secrets and apply them --insecure (skips nodes already configured)
#    task bootstrap:talos   # talosctl bootstrap (retries until etcd says AlreadyExists) + kubeconfig
#    task bootstrap:apps    # namespaces + BWS token + github-app-auth, CRDs, then helmfile:
#                           # cilium → coredns → cert-manager → external-secrets → flux-operator → flux-instance

# 4. optional: replace the 1-year admin cert with a 5-year one, issued through the running node
task talos:renew-talosconfig

# 5. Flux takes over from here
task kubernetes:reconcile
flux get ks -A && flux get hr -A
```

After bootstrap, apps that carry the `volsync` component restore their PVC from the kopia repository
on `chthon` automatically (`restore-once`); if one comes up empty, run
`task volsync:restore NS=<ns> APP=<app>`. Day-2 Talos operations are `task talos:apply-node NODE=vore`
and `task talos:upgrade-node NODE=vore`.

## Core components

- **[Cilium](https://cilium.io)** — networking, BGP, and LoadBalancer IPAM
- **[Envoy Gateway](https://gateway.envoyproxy.io)** — internal + external Gateway API ingress for `hythm.net`
- **[cloudflared](https://github.com/cloudflare/cloudflared)** — public entry via Cloudflare Tunnel
- **[external-dns](https://github.com/kubernetes-sigs/external-dns)** / **[k8s-gateway](https://github.com/k8s-gateway/k8s_gateway)** — public and LAN DNS
- **[external-secrets](https://external-secrets.io)** — secrets from Bitwarden Secrets Manager
- **[OpenEBS](https://openebs.io)** + **[VolSync](https://volsync.readthedocs.io)** — local storage with kopia-backed backups
- **[kube-prometheus-stack](https://github.com/prometheus-community/helm-charts)** + **[Gatus](https://gatus.io)** — monitoring and status

## Thanks

Patterns and inspiration from [onedr0p/home-ops](https://github.com/onedr0p/home-ops),
[buroa/home-ops](https://github.com/buroa/home-ops) and the
[home-operations](https://github.com/home-operations) community.
