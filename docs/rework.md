# Rework: 10.1 addressing and the `qube` cluster

One planned session that removes both exceptions in [lore.md](lore.md#exceptions):

1. **E1 moves to the lore's addressing**, `10.<episode>.<vlan>.0/24`, so New York is `10.1.x`
   and untagged `complex` (the switch's VLAN 1) is `10.1.1.0/24`.
2. **The cluster `kube` is rebuilt as `qube`**, with new certificates and the API at `qube.internal`.

Downtime is fine. Losing *access* is the risk: every step here can cut the network, so
this page has to work **without the internet and without Claude**. Keep a copy on the
phone (P2) and read [the safety net](#the-safety-net) before starting.

**Done 2026-10-28**, in one evening (17:00–19:00 for phases A to C). Kept as the record, and
as a template for the next site. What the day added to the plan:

- **`complex` can't open connections to the servers** (only ping). The lifeline needed a
  temporary pass rule from `192.168.0.50` to `necropolis` port 22, added through the API before
  B3 and carried into the new config by the converter (`10.1.1.50`); deleted in E.
- **B3 needs chthon's gateway too.** A second address alone can't answer anything outside its
  own network; the gateway was switched to `10.1.10.1` on quad's console after B4.
- **Ansible saved chthon's network profile without applying it**; the playbook now reapplies it.
- **Talos `shutdown` takes about 3 minutes** (it cordons and drains first).
- **`bootstrap:apps` used the old cluster's kubeconfig entry** (the first in the file) for its
  temporary server override; it now takes the current context's (`--minify`).
- **Paperless's import runs through the image's `document_importer` wrapper** (as the
  paperless user): as root, NFS's root squash refuses the media folder.
- **The router's git backup broke with the restore** (its local repository starts over, so the
  history no longer matches `saves`): force push enabled; the old history is on branch
  `before-rework`.
- **External-dns' records**: `bootstrap/cloudflare-drop-owner.py kube --delete`, recreated within
  a minute as `qube`.

## What changes

| Network | VLAN | Now | New | Router |
|---|---|---|---|---|
| `complex` | untagged (switch VLAN 1) | 192.168.0.0/24 | **10.1.1.0/24** | 10.1.1.1 |
| `necropolis` | 10 | 192.168.10.0/24 | 10.1.10.0/24 | 10.1.10.1 |
| `gloom` | 20 | 192.168.20.0/24 | 10.1.20.0/24 | 10.1.20.1 |
| `house` | 30 | 192.168.30.0/24 | 10.1.30.0/24 | 10.1.30.1 |
| `castle` | 40 | 192.168.40.0/24 | 10.1.40.0/24 | 10.1.40.1 |
| `grotto` | 50 | 192.168.50.0/24 | 10.1.50.0/24 | 10.1.50.1 |
| `ziggurat` | 60 | 192.168.60.0/24 | 10.1.60.0/24 | 10.1.60.1 |
| `base` | WireGuard wg0 | 192.168.80.0/24 | 10.1.80.0/24 | 10.1.80.1 |
| the whole site | — | 192.168.0.0/16 | 10.1.0.0/16 | — |

The last number of every address stays the same. RFC1918 lists (the `PrivateNetworks` alias,
the IDS home net, Unbound's private addresses) keep `192.168.0.0/16`: they mean "any private
network", not this site.

| Host | Now | New |
|---|---|---|
| `slipgate` (router, LAN) | 192.168.0.1 | 10.1.1.1 |
| `teleporter` (switch) | 192.168.0.254 | 10.1.1.254 |
| `quad` (KVM) | 192.168.0.252 | 10.1.1.252 |
| `scrag` (AP) | 192.168.0.199 | 10.1.1.199 |
| `chthon` (NAS) | 192.168.10.5 | 10.1.10.5 |
| `vore` (node) | 192.168.10.10 (and 192.168.30.100 on `house`) | 10.1.10.10 (10.1.30.100) |
| `ranger` | 192.168.40.142, WireGuard 192.168.80.42 | 10.1.40.142, 10.1.80.42 |
| `axe` (phone, WireGuard) | 192.168.80.2 | 10.1.80.2 |
| envoy-direct / internal / external | 192.168.20.250 / .251 / .252 | 10.1.20.250 / .251 / .252 |
| k8s-gateway | 192.168.20.253 | 10.1.20.253 |
| Kubernetes API VIP | `kube.internal` 192.168.20.254 | **`qube.internal`** 10.1.20.254 |
| qbittorrent (VPN path) | 192.168.60.10 | 10.1.60.10 |

Not changing: the VLAN tags, the switch's port layout, the WAN (DHCP from Spectrum), Cloudflare,
`hythm.net`, NordVPN (`arch`, 10.5.0.2), the pod and service ranges (10.244/16, 10.245/16).

## The safety net

**Rules for the day**

1. **Every phase ends at a checkpoint.** If a checkpoint fails and the fix isn't obvious
   within 15 minutes, roll that phase back ([Rollback](#rollback)) instead of pushing on.
2. **The point of no return is C3** (wiping vore). Until then, everything goes back to exactly
   today's state, old cluster included: vore stays powered off and untouched through phase B.
3. **Use IP addresses, not names, during phase B.** The phone hotspot's DNS doesn't know
   `.internal`; the `/etc/hosts` block (P3) covers the names the tools need.

**The lifeline: ranger stays connected to both me and the LAN.** During phase B, ranger
takes its internet from the phone hotspot (Wi-Fi) and is wired into **teleporter port ge1/1**
(the AP's port, `complex` untagged; the AP is unplugged for that hour). The wired link
carries both `192.168.0.50` and `10.1.1.50`, so ranger reaches the router, the switch and
quad on the wire **whatever state the router is in**, and Claude Code keeps working over
the hotspot.

**The console: quad goes where the work is.** There's no screen or keyboard to spare, so
the KVM moves: on `slipgate` for B4, on `chthon` for B5, on `vore` for phase C. Unplug and
replug only its HDMI and USB; **never power-cycle quad during the work** (it keeps its
address only while it stays up).

**If Claude can't be reached:** in the terminal on ranger, `cd ~/development/qube && claude
--continue` resumes this conversation over the hotspot. If ranger itself is the problem,
open the Claude app on the phone (cellular data), open this page on GitHub, and paste the
step you're on.

**Offline kit** (ready after prep):

- this page as a file on the phone (opens in flight mode) and in `~/development/qube` on ranger
- Bitwarden **Password Manager** on the phone with `slipgate-root`, `teleporter-admin`,
  `quad-admin`, `chthon-root` and the BWS token copied in (the phone app works offline;
  Secrets Manager does not)
- in `~/rework/` on ranger *and* on a USB stick: `config-before.xml` (router today),
  `config-after.xml` (router new), the switch export `switch.cfg`, the old `talosconfig.kube`.
  The router files hold its secrets: never in git
- the Talos ISO for the new schematic (P9), on a USB stick or loaded into quad's
  *Virtual Media*

## Prep (days before, nothing changes yet)

- [x] **P1 · Passwords offline.** Copy `slipgate-root`, `teleporter-admin`, `quad-admin`,
  `chthon-root` (Secrets Manager → `rune`) and the BWS token into Password Manager →
  `homelab`. Open them once in the phone app in flight mode. (2026-10-28: the owner knows them by heart.)
- [x] **P2 · This page on the phone.** Save it as a file (GitHub → ⋯ → Download, or print to
  PDF) and open it in flight mode.
- [ ] **P3 · Lifeline dry run.** Phone hotspot on; ranger's Wi-Fi joins it. Note the hotspot's
  subnet (`ip -4 addr`); it must not be `10.1.x` or `192.168.0.x`. Then create the wired
  profile (find the wired device with `nmcli device`):

  ```sh
  sudo nmcli con add type ethernet ifname <eth> con-name lifeline autoconnect no \
    ipv4.method manual ipv4.addresses "192.168.0.50/24,10.1.1.50/24" ipv4.never-default yes \
    ipv4.routes "192.168.10.0/24 192.168.0.1, 10.1.0.0/16 10.1.1.1" ipv6.method disabled
  ```

  Unplug the AP from ge1/1, plug ranger in, `sudo nmcli con up lifeline`, and check
  `ping 192.168.0.1`, `ping 192.168.0.254`, `ping 192.168.0.252`, `ping 192.168.10.5`,
  plus that Claude Code still answers. Then `sudo nmcli con down lifeline` and put the AP
  back. Add this block to ranger's `/etc/hosts`, commented out until phase B:

  ```text
  # rework (phase B): .internal without the router's DNS
  10.1.1.1     slipgate.internal
  10.1.1.254   teleporter.internal
  10.1.1.252   quad.internal
  10.1.10.5    chthon.internal
  10.1.10.10   vore.internal
  10.1.20.254  qube.internal
  ```

- [x] **P4 · Console dry run.** ✔ slipgate (2026-10-28): its keyboard works whenever quad is
  plugged in, but **its HDMI only comes on if quad is attached while it boots**; plugged into
  a running router, the screen stays black. ✔ vore (2026-10-28): Talos's normal reboot uses
  kexec and skips the firmware; `task talos:reboot-node NODE=vore MODE=powercycle` goes
  through it and shows vore's boot menu for 3 s, with **Talos (Reset to maintenance mode)**
  entries and **Reboot Into Firmware Interface**. Put quad back on `chthon`.
- [ ] **P5 · Short DHCP leases (at least a day before).** Router → Services → Dnsmasq → DHCP
  ranges: set the lease time to 600 s on every range, so clients move to the new subnets
  within minutes instead of hours.
- [x] **P6 · chthon accepts both networks.** Its root-password SSH fallback
  (`50-root-password-lan.conf`) matches `192.168.0.0/16,10.1.0.0/16` for the day. Apply it
  with `task hosts:chthon TAGS=users`.
- [x] **P7 · The rework PR** [#546](https://github.com/hythm-net/qube/pull/546), branch
  `feat/rework-qube`, a **draft** until C1: every address in the tables above, `clusterName: qube`, endpoint and
  certSANs `qube.internal`, the region label, `TALOS_SECRET_ID` → the new bundle, chthon's
  `host_vars`, the docs and CLAUDE.md, external-dns' owner id `qube`, and the self-signed CA's
  organization `hythm.net`. Checked: vore's config renders with `talos-qube` and passes
  `talosctl validate`; chthon's dry run changes only its address, gateway, DNS and exports.
- [x] **P8 · New Talos secrets.** `talosctl gen secrets` → the Secrets Manager entry
  `talos-qube` (3289ee3c…) in `qube`, flattened like `talos`. **Keep `talos`** (the old bundle) until the
  new cluster has run for a month.
- [x] **P9 · Talos ISO** `talos/talos-v1.14.5.iso` (`task talos:generate-iso VERSION=v1.14.5`;
  the schematic doesn't change, d56b9441… like vore today). The last fallback for C3: put it
  on a USB stick, or upload it to quad's *Virtual Media* so vore can boot it remotely.
- [x] **P10 · The router's new config.** `hosts/slipgate/rework-config.py` (removed after the
  rework; it's in commit 8698f17) turns `config.xml` into `config-after.xml` with the address
  map above. It leaves RFC1918 lists and the
  history stamps alone and renames the 6 `kube` values (alias, the rule using it, the
  Unbound override, the BGP peer group). Reviewed 2026-10-28: 61 addresses, 6 names. It's
  generated again on the day (A5) so it includes any change since.
- [ ] **P11 · Pick the window.** A daytime weekend slot of about 6 hours, away from the
  nightly jobs (Paperless export 23:30, Immich dump 02:00, backpack 03:30). Tell the house:
  internet off for up to an hour, Wi-Fi may need a reconnect afterwards, apps down until
  the evening.

## Day of

### A · Freeze and back up (about 45 min; the old cluster is still up)

1. **Healthchecks.io:** pause `qube alerting`, `home internet` and `off-site backup`.
2. **Fresh database dumps.** Immich: Administration → Jobs → *Database backup* → run. Paperless:
   `kubectl -n paperless create job --from=cronjob/paperless-exporter rework-export` and wait
   for it to complete. Check that both have today's time in `@photos/backups/` and
   `@documents/export/`.
3. **VolSync, every app:**

   ```sh
   kubectl get replicationsource -A --no-headers | while read ns app _; do
     task volsync:backup NS=$ns APP=$app || echo "FAILED $ns/$app"
   done
   ```

   Any `FAILED` → stop and fix it before going on.
4. **Off-site:** `sudo systemctl start backpack.service` on chthon; wait for it to finish
   (`journalctl -u backpack -n 5`).
5. **Snapshots of today's state.** Router: System → Configuration → Backups → *Download* →
   `~/rework/config-before.xml`, then
   `hosts/slipgate/rework-config.py ~/rework/config-before.xml ~/rework/config-after.xml`
   and read its list of changes (it refuses to write a file with any site address left).
   Switch: export its config → `switch.cfg`. Copy `talos/talosconfig` to `talosconfig.kube`.
   Copy all of it to the USB stick. Tag the repo: `git tag pre-rework && git push origin pre-rework`.
6. **Shut the cluster down:** `talosctl -n 192.168.10.10 shutdown`. vore powers off.

✔ **Checkpoint A:** dumps, export, every VolSync source and backpack are from today; vore is off.

### B · The network (about 1.5 h; fully reversible)

1. **Lifeline on.** ranger's Wi-Fi → hotspot. Unplug the AP from ge1/1, plug ranger in,
   `sudo nmcli con up lifeline`. `ping 192.168.0.1` and `ping 192.168.0.252` answer, Claude answers.
2. **quad → slipgate.** A black screen is normal here: slipgate only turns its HDMI on while
   booting, and the restore in B4 reboots it with quad attached. From then on, **leave quad
   on slipgate until checkpoint B4 passes**: it's the console for [R1](#r1-router).
3. **chthon gets its new address next to the old one** (it can't be reached otherwise once
   the router moves):

   ```sh
   ssh -i ~/.ssh/qube-ops -o IdentitiesOnly=yes claude@192.168.10.5
   sudo nmcli con mod "Wired connection 1" +ipv4.addresses 10.1.10.5/24
   sudo nmcli device reapply enp2s0
   ip -4 addr show enp2s0          # both 192.168.10.5 and 10.1.10.5
   ```

4. **The router switch.** Web UI http://192.168.0.1 → System → Configuration → Backups →
   *Restore* → `config-after.xml` → restore. It reboots (3 to 5 min); quad's screen
   comes on during this boot and ends at a `login:` prompt.

   ✔ **Checkpoint B4** (from ranger):
   - `ping 10.1.1.1` answers and https://10.1.1.1 loads; Interfaces → Overview shows 10.1.x everywhere
   - Interfaces → Diagnostics → Ping `1.1.1.1` from the router works (internet)
   - `dig @10.1.1.1 chthon.internal +short` → `10.1.10.5`; `dig @10.1.1.1 qube.internal +short` → `10.1.20.254`

   Fails → [R1](#r1-router).
5. **chthon on the new address only.** quad → chthon (fallback console). Uncomment the
   `/etc/hosts` block on ranger, `git switch feat/rework-qube`, then:

   ```sh
   ssh -i ~/.ssh/qube-ops -o IdentitiesOnly=yes claude@10.1.10.5 true   # reachable through the new router
   task hosts:chthon TAGS=network,nfs,users
   ```

   ✔ chthon shows only `10.1.10.5` (`ip -4 addr`), `ping -c1 1.1.1.1` works from it, and
   `sudo exportfs -s` lists the 10.1 networks. Fails → [R3](#r3-chthon).
6. **The switch's management address.** http://192.168.0.254 → its IP settings → `10.1.1.254/24`,
   gateway and DNS `10.1.1.1` → save, reconnect at http://10.1.1.254 → save the configuration
   → export it (`switch.cfg`, new). Traffic keeps flowing whatever its own address is.
7. **Back to normal.** AP back into ge1/1, `sudo nmcli con down lifeline`, ranger's Wi-Fi back
   to `castle`, hotspot off, `/etc/hosts` block commented out again.

✔ **Checkpoint B:**
- a phone on `castle` and one on `grotto` get 10.1.x addresses and reach the internet
- ranger gets `10.1.40.142`; `ping slipgate.internal teleporter.internal quad.internal chthon.internal`
- scrag shows `10.1.1.199` in the router's DHCP leases

**Decision:** go on to C, or roll everything back ([R4](#r4-everything-before-c3)) and boot the old cluster.

### C · The cluster `qube` (about 1.5 to 2 h; C3 is the point of no return)

1. **Merge the rework PR** once both checks pass. Flux bootstraps from `main`.
2. **quad → vore, power vore on.** It takes `10.1.10.10` from its DHCP reservation and boots
   the old Talos; Kubernetes won't come up on the new network, which is expected.
   `talosctl --talosconfig talosconfig.kube -e 10.1.10.10 -n 10.1.10.10 version` must answer.
3. **⚠ Wipe vore's cluster state** (the point of no return):

   ```sh
   talosctl --talosconfig talosconfig.kube -e 10.1.10.10 -n 10.1.10.10 reset --graceful=false \
     --system-labels-to-wipe STATE --system-labels-to-wipe EPHEMERAL --reboot
   ```

   On quad, vore comes back in **maintenance mode** at 10.1.10.10. The `local-hostpath`
   volume isn't wiped: the old volumes, including the raw Postgres data, stay on disk as a
   last resort. If the reset command fails, power-cycle vore (power button) while
   watching quad: its boot menu shows for 3 s, so press an arrow key at once and choose
   **Talos (Reset to maintenance mode)**. Only if that fails too, boot the ISO (P9).
4. **Bootstrap:**

   ```sh
   export BWS_ACCESS_TOKEN=$(cat ~/bitwarden/bitwarden-ahla-token)
   task talos:generate-talosconfig      # from talos-qube
   task bootstrap:cluster               # nodes → talos → apps; Flux takes over
   task talos:renew-talosconfig
   ```

✔ **Checkpoint C:**
- `kubectl get nodes`: vore Ready, not cordoned; `talosctl -n vore version` exits 0
- `flux get ks -A` all Ready (give it 20 to 30 min)
- the router's Routing → Diagnostics → BGP shows vore Established
- https://internal.hythm.net answers on the LAN
- `kubectl get resourceslices -A` isn't empty (GPU); if it is, see [cluster troubleshooting](#troubleshooting)

### D · App data (about 1 h)

1. **Config volumes** come back on their own (`restore-once`). Check every app has its
   settings; one that's empty → `task volsync:restore NS=… APP=…`.
2. **Immich database:** set `IMMICH_ALLOW_SETUP: "true"` (a temporary commit), restore
   today's dump from `@photos/backups/` through Immich's maintenance-mode restore, then
   revert the commit straight away (the restore endpoint is public while it's on).
3. **Paperless database:**
   `kubectl -n paperless exec deploy/paperless -- python3 manage.py document_importer /data/nas/export`
4. **Logins:** Pocket ID, Immich, Jellyfin (on a TV too), Paperless, Open WebUI, lyl.
5. **Healthchecks.io:** un-pause the three checks; they turn green within 10 minutes. Gatus is
   all green.
6. **Cloudflare records.** The new external-dns owns records as `qube` and skips the 13 that
   `kube` left (they still work, they just can't be updated). Delete them so it recreates its
   own: `bootstrap/cloudflare-drop-owner.py kube` lists them, `--delete` removes them (you
   run this one: DNS deletes are blocked for Claude). Within a minute `dig +short
   photos.hythm.net @1.1.1.1` answers again.

### E · Finish (about 45 min; can wait a day)

1. **WireGuard peers** (`ranger`, `axe`): Address `10.1.80.x/32`, AllowedIPs `10.1.0.0/16`,
   DNS `10.1.1.1`. Test from the phone on cellular.
2. **UniFi:** the controller on ranger has a new address; set the AP's inform host to it
   (controller settings) or `set-inform` on the AP.
3. **DHCP leases** back to the default.
4. **`saves`:** the router's next commit lands on `main`; commit the new `switch.cfg` on the
   `teleporter` branch.
5. **chthon:** drop `192.168.0.0/16` from the root-password SSH match (P6).
6. **Later:** delete the old volume directories on vore once nothing is missing (a week);
   delete the old `talos` bundle after a month; optionally rename the Cloudflare tunnel `kube`.

## Rollback

### R1 · Router

The router keeps its previous configurations. From ranger on the lifeline, whichever answers
of https://10.1.1.1 or https://192.168.0.1: System → Configuration → **History** → revert to the
revision before the restore, or Backups → Restore → `config-before.xml`. If no web UI answers:
**quad console → `13) Restore a backup`** → pick the newest backup from before today's restore
→ reboot. Last resort: console `1)` to check that `igc1` is LAN, `2)` to set the LAN address.

### R2 · Switch

It keeps switching whatever its management address is. Lost management: try both
192.168.0.254 and 10.1.1.254 from the lifeline. Still nothing: reset it (button, default
address on its label or in the manual) and import `switch.cfg`.

### R3 · chthon

On the quad console, log in as root (`chthon-root`), then put back whichever address is right
for the router's current state:

```sh
nmcli con mod "Wired connection 1" ipv4.addresses 192.168.10.5/24 ipv4.gateway 192.168.10.1 ipv4.dns 192.168.10.1   # old
nmcli con mod "Wired connection 1" ipv4.addresses 10.1.10.5/24 ipv4.gateway 10.1.10.1 ipv4.dns 10.1.10.1           # new
nmcli con up "Wired connection 1"
```

### R4 · Everything (before C3)

R1, then R3 (old line), then R2 if the switch moved. Don't merge the PR (close it if it was).
Power vore on: it gets 192.168.10.10 again and the old cluster comes up as it was. Un-pause
Healthchecks.io and set the DHCP leases back. Nothing is lost.

### R5 · After C3

There's no going back to the old cluster as it was; fix forward. If the new cluster can't
come up at all: put the network back (R4 without vore), revert the merge, and rebuild the old
way from the `pre-rework` tag with the old `talos` bundle ([rebuild.md](rebuild.md) steps 6
and 7). The data is safe throughout: VolSync on chthon, today's dumps, and backpack on R2.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| ranger can't ping 192.168.0.1 or 10.1.1.1 on the wire | lifeline down or cable in the wrong port | `nmcli con up lifeline`; ge1/1 is `complex` untagged; `ip -4 addr` shows .50 twice |
| Router web UI unreachable on both addresses | LAN on the wrong interface | quad console `1)`: `igc1` is LAN; `2)`: LAN 10.1.1.1/24; or R1 |
| Router online, clients aren't | old DHCP leases | reconnect Wi-Fi or reboot the device; check Services → Dnsmasq → Leases |
| Router has no internet | WAN, unrelated to the change | Interfaces → Overview → WAN has an address; power-cycle the modem |
| `.internal` names don't resolve on ranger | hotspot DNS | the `/etc/hosts` block, or `dig @10.1.1.1` |
| chthon unreachable after B5 | address or gateway wrong | quad console, `ip -4 addr`, R3 |
| vore doesn't get 10.1.10.10 | DHCP reservation (MAC 78:55:36:08:3b:c2) or port | the router's leases page; ge1/2 untagged 10 |
| `talosctl`: x509 or certificate errors | wrong talosconfig | old cluster: `talosconfig.kube`; new: `talos/talosconfig` from C4 |
| bootstrap can't find the node | not in maintenance mode | quad shows vore's dashboard; `talosctl -n 10.1.10.10 get disks --insecure` |
| `qube.internal` doesn't answer | the VIP comes from Cilium over BGP | BGP Established on the router? `kubectl -n kube-system get svc kube-vip` |
| BGP not Established | peer addresses | `l3.yaml` peer 10.1.1.1; router neighbor 10.1.10.10 |
| Flux can't pull from GitHub | bot credentials | external-secrets store Ready? `qubetoken` present? |
| GPU pod Pending, no resourceslices | DRA plugin | delete the `k8s-gpu-dra-driver` pod in kube-system |
| An app starts empty | VolSync didn't restore | `task volsync:restore NS=… APP=…` |
| Database restore fails | — | the old Postgres data is still on vore under `/var/mnt/local-hostpath/` (Immich `pvc-bb71f52b…`, Paperless `pvc-976a87a0…`) |
