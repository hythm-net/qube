#!/usr/bin/env python3
"""Turn slipgate's config.xml into the rework's version (docs/rework.md P10 and A5).

Text-level, so everything else in the file stays byte for byte:
- this site's addresses 192.168.<v>.<h> -> 10.1.<v or 1>.<h> (complex 0 -> 1, VLANs 10..60,
  WireGuard base 80); 192.168.0.0/16 means "any private network" (PrivateNetworks, the IDS
  home net, Unbound's private addresses) and stays
- the name `kube` -> `qube` where it is a whole value (alias, the rule using it, the Unbound
  override, the BGP peer group)
- <created>/<updated> stamps (who changed what, from where) are history and stay

The output holds the router's secrets: keep it out of git (~/rework/).

    hosts/slipgate/rework-config.py ~/rework/config-before.xml ~/rework/config-after.xml
"""
import re
import sys
import xml.etree.ElementTree as ET

SITE = re.compile(r"(?<![\d.])192\.168\.(0|10|20|30|40|50|60|80)\.(\d{1,3})(?![\d])(?!/16)")
STAMPS = re.compile(r"<(created|updated)>.*?</\1>", re.S)
NAME = re.compile(r">kube<")
SECRETISH = re.compile(r"key|secret|pass|psk|token|hash|cert|crt", re.I)


def remap(text: str) -> tuple[str, int]:
    return SITE.subn(lambda m: f"10.1.{'1' if m.group(1) == '0' else m.group(1)}.{m.group(2)}", text)


def main(src: str, dst: str) -> None:
    old = open(src).read()
    # keep the stamps aside so the address map never touches them
    stamps: list[str] = []
    body = STAMPS.sub(lambda m: stamps.append(m.group(0)) or f"\0{len(stamps) - 1}\0", old)
    body, addresses = remap(body)
    body, names = NAME.subn(">qube<", body)
    new = re.sub(r"\0(\d+)\0", lambda m: stamps[int(m.group(1))], body)

    ET.fromstring(new)  # still well-formed
    left = SITE.findall(STAMPS.sub("", new))
    assert not left, f"site addresses left over: {left}"
    assert names == 6, f"expected 6 kube values, found {names}"

    open(dst, "w").write(new)
    print(f"{addresses} addresses remapped, {names} kube -> qube, {len(stamps)} stamps kept")
    for a, b in zip(old.splitlines(), new.splitlines()):
        if a != b:
            shown = "(line with a secret-looking tag, not shown)" if SECRETISH.search(a) else f"{a.strip()}  ->  {b.strip()}"
            print("  " + shown)


if __name__ == "__main__":
    main(*sys.argv[1:3])
