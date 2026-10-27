#!/usr/bin/env python3
"""Print teleporter's port map from SNMP: per port, the learned MACs (named from known
devices), the untagged VLAN (PVID) and the tagged VLANs. Read-only.

Usage: hosts/teleporter/portmap.py [switch] [community]   (defaults: teleporter.internal, public)
"""
import subprocess
import sys

SWITCH = sys.argv[1] if len(sys.argv) > 1 else "teleporter.internal"
COMMUNITY = sys.argv[2] if len(sys.argv) > 2 else "public"

# MACs of named devices (docs/lore.md); random (locally administered) MACs are pods or phones
KNOWN = {
    "78:55:36:05:33:0b": "slipgate",
    "78:55:36:08:3b:c2": "vore",
    "78:55:36:07:fe:23": "chthon",
    "84:78:48:fe:d5:5c": "scrag",
    "94:83:c4:c4:93:ed": "quad",
    "fc:b0:de:ac:c2:4d": "ranger",
}
VLAN_NAMES = {1: "complex", 10: "necropolis", 20: "gloom", 30: "house", 40: "castle", 50: "grotto", 60: "ziggurat"}


def walk(oid):
    out = subprocess.run(
        ["snmpbulkwalk", "-v2c", "-c", COMMUNITY, "-On", "-Oq", SWITCH, oid],
        capture_output=True, text=True, check=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        key, _, value = line.partition(" ")
        rows.append((key[len(oid) + 2:], value.strip().strip('"')))
    return rows


def ports_in(bitmap):
    octets = [int(b, 16) for b in bitmap.split()]
    return {i * 8 + bit + 1 for i, o in enumerate(octets) for bit in range(8) if o & (0x80 >> bit)}


names = dict(walk("1.3.6.1.2.1.31.1.1.1.1"))                    # ifIndex -> ifName
oper = dict(walk("1.3.6.1.2.1.2.2.1.8"))                         # ifIndex -> up/down
bp_if = dict(walk("1.3.6.1.2.1.17.1.4.1.2"))                     # bridge port -> ifIndex
pvid = {int(k): int(v) for k, v in walk("1.3.6.1.2.1.17.7.1.4.5.1.1")}
egress = {int(k): ports_in(v) for k, v in walk("1.3.6.1.2.1.17.7.1.4.3.1.2")}
untagged = {int(k): ports_in(v) for k, v in walk("1.3.6.1.2.1.17.7.1.4.3.1.4")}

macs = {}
for key, port in walk("1.3.6.1.2.1.17.7.1.2.2.1.2"):            # [fdb id.]mac -> bridge port
    mac = ":".join(f"{int(o):02x}" for o in key.split(".")[-6:])   # this switch omits the fdb id
    if mac in KNOWN:
        label = KNOWN[mac]
    elif int(mac[:2], 16) & 0x02:
        label = "random MAC"
    else:
        label = mac
    macs.setdefault(int(port), set()).add(label)


def vlan(v):
    return f"{v} {VLAN_NAMES.get(v, '')}".strip()


print("| Port | Link | Devices | Untagged | Tagged |")
print("|---|---|---|---|---|")
for bp in sorted(int(p) for p in bp_if):
    ifindex = bp_if[str(bp)]
    tagged = [v for v in sorted(egress) if bp in egress[v] and bp not in untagged.get(v, set())]
    seen = macs.get(bp, set())
    devices = ", ".join(sorted(seen - {"random MAC"}) + (["random MACs"] if "random MAC" in seen else [])) or "—"
    print(f"| {names.get(ifindex, ifindex)} | {oper.get(ifindex, '?')} | {devices} | "
          f"{vlan(pvid[bp])} | {', '.join(vlan(v) for v in tagged) or '—'} |")
