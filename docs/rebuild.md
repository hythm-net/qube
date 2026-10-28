# Rebuild

How to bring the homelab back from bare hardware, in order: each layer needs the one before
it (the router gives every other machine its network, DNS and DHCP; the cluster needs
chthon's storage). Names are explained in [lore.md](lore.md).

| Lost | Start at |
|---|---|
| everything (fire, theft, new hardware) | [0](#0-what-you-need-first), then every step |
| the router | [1](#1-slipgate-the-router) |
| the switch | [2](#2-teleporter-the-switch) |
| the NAS's OS disk (data drives fine) | [5](#5-chthon-the-nas): the array comes back by UUID |
| the Kubernetes node | [6](#6-vore-the-cluster), then [7](#7-app-data) |

## 0. What you need first

- **Bitwarden.** Your master password opens the personal vault, which holds the Secrets
  Manager machine-account token. That token opens the two projects everything else needs:
  - `qube`: the cluster (Talos bundle `talos`, the `novyxz` bot, every app's keys)
  - `rune`: the master keys for everything outside it (`slipgate-root`, `chthon-root`, `teleporter-admin`,
    `quad-admin`, the OPNsense API key `opnsense`, `saves-deploy-key`, `opnsense-heartbeat`)
- **GitHub**, account `hythm7`, which owns the org `hythm-net`:
  - `hythm-net/qube`: this repo
  - `hythm-net/saves` (private): the router's `config.xml` history on `main`, the switch
    export on the `teleporter` branch
- **A USB stick**, and `quad` (the KVM) or a screen and keyboard for consoles.

## 1. slipgate: the router

1. Install the current OPNsense. At the console, assign `igc0` as WAN and `igc1` as LAN.
2. Open the web UI on the LAN (default 192.168.1.1). Go to **System → Configuration →
   Backups → Restore** and upload `config.xml` from the latest commit in `hythm-net/saves`.
   It reboots with everything:
   - the VLANs `complex` … `ziggurat`
   - the firewall and NAT rules, and the DHCP reservations
   - Unbound: the `hythm.net` forward to k8s-gateway and the `.internal` overrides
   - WireGuard `base` and `arch` (to `nord`, with the kill switch)
   - FRR (BGP with vore), DDNS for `hythm.net`, SNMP
   - Monit's Healthchecks.io heartbeat, and `os-git-backup` with its cron job
3. **System → Firmware → Plugins**: reinstall any missing plugins if OPNsense offers to.
4. Check:
   - the internet works
   - `dig +short hythm.net @1.1.1.1` shows the new WAN address (DDNS)
   - the Healthchecks.io check **home internet** is green
   - a new commit lands in `saves` within the hour

## 2. teleporter: the switch

Factory-reset it, log in (`teleporter-admin`), and import `teleporter/switch.cfg` from the
`teleporter` branch of `saves`. Without an export, configure it from the port table in
[hosts/teleporter](../hosts/teleporter/README.md), which holds every setting that matters.
Then check with `hosts/teleporter/portmap.py`.

## 3. scrag: Wi-Fi

The UniFi controller runs on `ranger` (the `unifi` alias). Adopt the U7 Pro from it. Its
SSIDs use VLANs 40 (`castle`), 50 (`grotto`, guests) and 60 (`ziggurat`), which ge1/1
carries tagged.

## 4. quad: the KVM

It gets 10.1.1.252 from its DHCP reservation. Login: `quad-admin`. On 2026-10-27 its
keyboard stayed dead while chthon hung early in boot, and worked after a power cycle.

## 5. chthon: the NAS

Follow [hosts/chthon](../hosts/chthon/README.md): install openSUSE Leap 16 on the OS disk
only, then `task hosts:chthon`. **An OS reinstall doesn't touch the data array**: the mounts
find it by UUID and every share is back. Only on new data drives do you create the array
(also described there) and pull the data back from `backpack` (below) before step 6.

### From the off-site copy (`backpack` on R2)

With the playbook applied (it installs kopia and `/etc/backpack/env`), as root on chthon:

```sh
set -a; . /etc/backpack/env; set +a
S3="--bucket=$BACKPACK_BUCKET --endpoint=$BACKPACK_ENDPOINT --region=auto"
# app configs: put the VolSync repository back where the cluster expects it
KOPIA_PASSWORD=$VOLSYNC_KOPIA_PASSWORD kopia repository connect s3 $S3 --prefix=volsync/ --config-file=/tmp/v.config
KOPIA_PASSWORD=$VOLSYNC_KOPIA_PASSWORD kopia repository sync-to filesystem --path=/data/@backup/kopia --config-file=/tmp/v.config
chown -R hythm:hythm /data/@backup/kopia
# photos and documents: newest snapshot of each into its subvolume
KOPIA_PASSWORD=$FILES_KOPIA_PASSWORD kopia repository connect s3 $S3 --prefix=files/ --config-file=/tmp/f.config
KOPIA_PASSWORD=$FILES_KOPIA_PASSWORD kopia snapshot list --all --config-file=/tmp/f.config
KOPIA_PASSWORD=$FILES_KOPIA_PASSWORD kopia snapshot restore <snapshot-id> /data/@photos --config-file=/tmp/f.config   # and @documents
```

Check that all four export paths are up (`exportfs -s`).

## 6. vore: the cluster

Follow the README's [Bootstrap from scratch](../README.md#bootstrap-from-scratch) and
[bootstrap/README.md](../bootstrap/README.md). In short:

```sh
export BWS_ACCESS_TOKEN=…                  # from the personal vault
task talos:generate-iso VERSION=…          # USB stick, boot vore into maintenance mode
task talos:generate-talosconfig
task bootstrap:cluster                      # nodes → talos → apps; Flux takes over
task talos:renew-talosconfig                # 5-year admin cert
```

Then check:
- after the reboot, the GPU device listing exists (`kubectl get resourceslices -A`)
- the node isn't left cordoned (`NodeCordoned` alerts after 30 minutes)

## 7. App data

| Data | Lives on | Comes back |
|---|---|---|
| media, photos, documents | chthon `@media`, `@photos`, `@documents` (NFS) | by themselves once chthon exports them |
| app config volumes (`volsync` component) | kopia repository on chthon `@backup/kopia` | automatically on first start (`restore-once`); if an app comes up empty: `task volsync:restore NS=… APP=…` |
| **Immich database** | nightly dump 02:00 in `@photos/backups/` | **by hand**: the CNPG cluster starts empty. Restore the newest `immich-db-backup-*.sql.gz` with Immich's database-restore procedure |
| **Paperless database** | nightly export 23:30 in `@documents/export/` | **by hand**: the CNPG cluster starts empty. Run `document_importer` on the export |

## 8. Done when

- Healthchecks.io: **qube alerting** and **home internet** are both green
- Gatus is all green; Flux reports every Kustomization and HelmRelease ready
- `NodeRebooted` has fired and resolved; nothing else is firing
- `task hosts:chthon CHECK=true` reports `changed=0`

## Known gaps

- **The off-site copy isn't immutable.** `backpack` on R2 has no lock (R2 can't lock what
  kopia needs to rewrite), so someone controlling chthon could delete it. A locked second
  copy (Backblaze B2 with Object Lock, or a box at another site) would close that. `@media`
  isn't copied off-site on purpose: it can be re-downloaded.
- The switch export in `saves` is a snapshot from 2026-10-27: re-export after changing the switch.
- The UniFi controller's own backup lives on `ranger`. Keep a copy of its autobackup.
