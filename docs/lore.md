# Lore

The homelab is named after **Quake** (1996). Quake is the code name of the enemy that comes
through the slipgates; the Ranger fights it. Here, `quake` is the hostile outside (the
internet), `slipgate` is the gate between it and home, and everything behind the gate is
named after the game's places, monsters and items.

## The hierarchy

| Quake | Network | In use |
|---|---|---|
| Quake, the enemy | the internet (WAN) | `quake` |
| An **episode** | a **site** | E1 Dimension of the Doomed = New York |
| An episode's **maps** | that site's **VLANs** | see [Episode 1](#episode-1-dimension-of-the-doomed-new-york) |
| **Slipgate**: takes you *between* levels | the **router** (between networks and sites) | `slipgate` |
| **Teleporter**: moves you *within* a level | the **switch** | `teleporter` |
| Level **exits** (arch, rune gate, exit gate) | **tunnels out** | `arch` (to the VPN provider) |
| **Deathmatch** maps: players join from outside | **remote-access** networks | `base` |
| **Monsters** | **servers** | `vore`, `chthon` |
| **Bosses** | one-of-a-kind central servers | `chthon` (the NAS) |
| **Flying** monsters | **wireless** gear | `scrag` |
| **Rottweilers**, the guard dogs | **cameras** (on `house`) | *(reserved: `rottweiler`)* |
| **Power-ups** | appliances | `quad` |
| **Ranger**, the player | the owner's workstation | `ranger` |
| The Ranger's **weapons** | the owner's other devices | `axe` (phone) |
| The **START** hub (links every episode) | a future central hub between sites | *(reserved: `start`)* |
| **Runes**: the keys collected to reach the end | the vault of master keys outside the cluster (Bitwarden project) | `rune` (next to the cluster's own project `qube`) |

## Episode 1: Dimension of the Doomed (New York)

VLANs are E1 maps, chosen for what the map is like, not its number: the name is the place,
the tag is the role ([rule 9](#rules)).

| VLAN | Tag | Subnet | Quake map | Carries |
|---|---|---|---|---|
| `complex` | untagged | 10.1.1.0/24 | E1M1 The Slipgate Complex | network gear: slipgate, teleporter, scrag, quad |
| `necropolis` | 10 | 10.1.10.0/24 | E1M3 The Necropolis | servers: vore, chthon |
| `gloom` | 20 | 10.1.20.0/24 | E1M5 Gloom Keep | services: every address something is served from (today the Kubernetes API VIP and the Cilium LoadBalancer pool `gloom`) |
| `house` | 30 | 10.1.30.0/24 | E1M7 The House of Chthon | IoT: DNS and internet only |
| `castle` | 40 | 10.1.40.0/24 | E1M2 Castle of the Damned | trusted clients (ranger) |
| `grotto` | 50 | 10.1.50.0/24 | E1M4 The Grisly Grotto | guests: DNS and internet only |
| `ziggurat` | 60 | 10.1.60.0/24 | E1M8 Ziggurat Vertigo (the secret level) | VPN egress: policy-routed through `arch`, with a kill switch |
| `base` | WireGuard wg0 | 10.1.80.0/24 | DM3 The Abandoned Base | remote access (peers `ranger`, `axe`) |
| *`door`* | — | — | E1M6 The Door to Chthon | reserved (e.g. a storage VLAN) |

Why these maps (an episode has only so many, so it's the best fit, not a perfect one):
- `complex`: the very first level, where you come in; the gear everything else hangs off.
- `necropolis`: underground and guarded; the servers are the core and sit deepest.
- `castle`: the owner's fort, holding their own devices.
- `ziggurat`: the secret level; what goes through it leaves hidden, through the VPN.
- `house`: the house's things: IoT.
- `gloom`: murky from outside; you only find a service if you know its address or ask DNS.
- `grotto`: the one left over, and it starts with G, like guests.

### Hosts and gear

| Name | What | Address |
|---|---|---|
| `slipgate` | OPNsense router/firewall; WireGuard endpoint `slipgate.hythm.net` | 10.1.1.1 |
| `teleporter` | switch (SL520S-5T1XS) | 10.1.1.254 |
| `scrag` | UniFi U7 Pro access point | 10.1.1.199 |
| `quad` | GL.iNet KVM-over-IP | 10.1.1.252 |
| `chthon` | NAS (openSUSE, btrfs RAID10, NFS) | 10.1.10.5 |
| `vore` | the Kubernetes node (Talos) | 10.1.10.10 |
| `qube` | Kubernetes API VIP (`qube.internal`) | 10.1.20.254 |
| `ranger` | the owner's workstation | 10.1.40.142 / 10.1.80.42 |
| `arch` → `nord` | WireGuard wg1 (local end) to NordVPN (remote end) | 10.5.0.2 |

`shambler` (10.1.10.7) is retired and reserved for the next node.

## Rules

1. **Lore names network identities**: hosts, VLANs, tunnels, devices, and the cluster's
   attachments to them (vore's VLAN links and Multus networks `house`/`ziggurat`, the
   LoadBalancer pool `gloom`, the BGP peer `slipgate`). Software inside Kubernetes keeps
   plain names (namespaces, apps, the envoy gateways), and so do alerts.
2. **Only owned things get Quake names.** Third-party endpoints keep their real names:
   `nord`, Spectrum, Cloudflare.
3. **The first of a kind gets the family's main name; more come from the same family.** No
   numbering (`teleporter2`).
4. **Servers are unique across all episodes**: a monster is an individual. Gear roles
   (`slipgate`, `teleporter`, …) may repeat per site, told apart by the site zone. Monsters
   that stand for gear are gear: flying ones for wireless (`scrag`), guard dogs for cameras
   (`rottweiler`).
5. **Sites get a DNS zone** once a second one exists: `<name>.<episode>.internal`, with E1 =
   `doomed`, E2 = `magic`, E3 = `nether`, E4 = `elder`. Each site searches its own zone
   first, so `ssh teleporter` stays local.
6. **Subnets never overlap between sites.** Every episode uses `10.<episode>.<vlan>.0/24`
   (E1 = `10.1.x`; the untagged network counts as VLAN 1, so `complex` is `10.1.1.0/24`).
   `10.0.x` stays free for the `start` hub.
7. **Firewall aliases:** lowercase = one named thing (`vore`, `chthon`); CamelCase = a group or
   role (`KubeNodes`, `KubeDirect`, `PrivateNetworks`).
8. **The zone stays `.internal`.** It is reserved by ICANN for private use and is baked into
   Talos' certificates; `.quake` would also make home the enemy's realm.
9. **The VLAN tag is the role, the same at every site**: untagged = network gear, 10 servers,
   20 services, 30 IoT, 40 trusted clients, 50 guests, 60 VPN egress, 80 remote access. Each
   episode names them after its own maps (E1's fort `castle` is 40, so E2's `citadel` would be
   too), so `10.<episode>.40.x` is someone's own device at any site and firewall rules carry
   over. A new role takes a free ten (70, 90).

## Name pools

| Family | In use | Next |
|---|---|---|
| Switches (move within a level) | `teleporter` | `lift`, `train`, `push` |
| Wireless (flying) | `scrag` | `wrath`, `overlord` (mission-pack flyers) |
| Cameras (guard dogs) | — | `rottweiler` |
| Servers (monsters) | `vore` | `shambler` (reserved), `ogre`, `fiend`, `knight`, `enforcer`, `grunt`, `zombie`, `spawn` |
| Bosses | `chthon` | `shub` |
| Appliances (power-ups) | `quad` | `pent`, `ring`, `biosuit` |
| Owner's devices (weapons) | `axe` | `shotgun`, `nailgun`, `perforator`, `thunderbolt` |
| Remote access (deathmatch maps) | `base` | `cistern` (e.g. family devices), `darkzone` |
| Tunnels out (exits) | `arch` | `runegate` (e.g. an E1↔E2 site link) |
| E2 VLANs (Realm of Black Magic) | — | `installation`, `citadel` (the fort, like `castle`), `crypt`, `ebon`, `wizard`, `dismal`, `underearth` (secret) |

## Exceptions

- The Cloudflare tunnel is still named `kube` (a third-party object; renaming means a new
  tunnel and repointing `external.hythm.net`).
