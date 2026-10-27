# chthon

The NAS (the boss of Episode 1, see [docs/lore.md](../../docs/lore.md)): a Beelink ME Pro
(Intel N150) on `necropolis`, 192.168.10.5, running openSUSE Leap 16. Its data lives on a
btrfs RAID10 over two NVMe drives; every top-level subvolume is mounted and exported on its
own to the cluster.

## What the playbook covers

| Tag | What |
|---|---|
| `base` | hostname, timezone, packages, the MediaTek Wi-Fi/Bluetooth blacklist |
| `network` | the static address on `necropolis` (NetworkManager) |
| `users` | `hythm` in `wheel`, the `claude` automation account (key + passwordless sudo), root's password login from the LAN and WireGuard only |
| `storage` | the subvolume mounts (`/etc/fstab`), their owners and modes, the directories the cluster writes to |
| `nfs` | `/etc/exports` |
| `snapper` | timelines for `@photos` and `@documents` |
| `monitoring` | `smartctl_exporter` (pinned release; Renovate bumps it) |
| `services` | everything that must be enabled and running |

Settings live in [host_vars/chthon.yaml](host_vars/chthon.yaml).

## Run

```sh
task hosts:chthon CHECK=true     # dry run: --check --diff, changes nothing
task hosts:chthon                # apply
task hosts:chthon TAGS=nfs       # one part only
```

Ansible runs through `uvx` at a pinned version, so nothing is installed system-wide. It
connects as `claude` with `~/.ssh/qube-ops` (override with `SSH_KEY=`).

## Rebuilding from bare metal

The playbook starts from a fresh openSUSE Leap 16 install. Before it can run:

1. Install Leap 16 on `nvme0n1` (the OS disk only; leave `nvme1n1`/`nvme2n1` alone). Set the
   hostname `chthon`, create the user `hythm`, and set the root password from Bitwarden
   `homelab`/`chthon-root`.
2. Give it 192.168.10.5 (or let the playbook's `network` tag do it from a temporary DHCP
   address), and allow SSH.
3. Create the `claude` account with the key from `host_vars` (or run the first pass as
   `hythm`: `task hosts:chthon -- -u hythm -k -K`).

Then `task hosts:chthon`. **The data array is not created by the playbook.** An OS reinstall
doesn't touch it: the mounts find it by its UUID and everything is back. Only on brand-new
drives create it first:

```sh
mkfs.btrfs -L data -d raid10 -m raid10 /dev/nvme1n1 /dev/nvme2n1   # raid10 over two devices
mount /dev/nvme1n1 /mnt
btrfs subvolume create /mnt/@media      # and @apps @backup @photos @documents
umount /mnt                             # then set data_uuid in host_vars
```

Snapshots are not backups. Off-site copies of `@photos` and `@documents` are still to do.

## Not managed

- Package updates: `sudo zypper patch` (twice) and `sudo zypper up`, then reboot. Cockpit's
  update page fails on Leap 16.
- btrfsmaintenance (monthly scrub, weekly balance of `/`) and smartd keep their openSUSE
  defaults.
- The root snapper config comes with the installer.
