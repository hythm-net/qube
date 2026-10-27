# teleporter

The switch (moves traffic *within* a level, see [docs/lore.md](../../docs/lore.md)): an
SL520S-5T1XS on `complex`, 192.168.0.254. Login: Bitwarden `homelab`/`teleporter-admin`.

## Port map

Read from the switch over SNMP on 2026-10-27 with [portmap.py](portmap.py), which matches
learned MACs against the known devices:

| Port | Link | Devices | Untagged | Tagged |
|---|---|---|---|---|
| ge1/1 | up | `scrag` (U7 Pro AP) and its Wi-Fi clients (`ranger`, phones) | 1 complex | 40 castle, 50 grotto, 60 ziggurat |
| ge1/2 | up | `vore` (and pod macvlans) | 10 necropolis | 30 house, 60 ziggurat |
| ge1/3 | up | `chthon` | 10 necropolis | — |
| ge1/4 | up | `quad` (KVM) | 1 complex | — |
| ge1/5 | up | `slipgate` (uplink to the router) | 1 complex | 10, 20, 30, 40, 50, 60 |
| xe1/6 | down | — (SFP+) | 1 complex | — |

- `gloom` (20) only reaches the router: LoadBalancer IPs get to vore through BGP, not as a
  VLAN on its wire.
- `vore` carries `house` (30) and `ziggurat` (60) tagged for Multus macvlans (IoT and the
  qbittorrent VPN path).
- The AP carries `castle`, `grotto` and `ziggurat` for its SSIDs. `house` is not on it yet:
  IoT on Wi-Fi needs VLAN 30 tagged on ge1/1 and an SSID in UniFi.

Check after recabling, and update the table if it changed:

```sh
hosts/teleporter/portmap.py            # SNMP v2c, community public (read-only)
```

New devices show up as raw MACs until they are added to `KNOWN` in the script.

## Configuration backup

The switch has no API for its configuration, so after changing it: **web UI → export the
configuration**, then commit the file to the private repo `hythm-net/saves` under
`teleporter/` (never here: it holds the admin password hash). Restoring is the same file
through the web UI's import.

To rebuild it by hand instead, the table above is the whole configuration that matters:
the VLANs 1/10/20/30/40/50/60, each port's untagged VLAN and tagged set, plus the
management address 192.168.0.254/24 and SNMP v2c read-only.
