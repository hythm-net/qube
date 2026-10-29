# chthon

The NAS (the boss of Episode 1, see [docs/lore.md](../../docs/lore.md)): a Beelink ME Pro
(Intel N150) on `necropolis`, 10.1.10.5, running openSUSE Leap 16. Its data lives on a
btrfs RAID10 over two NVMe drives; every top-level subvolume is mounted and exported on its
own to the cluster.

## What the playbook covers

| Tag | What |
|---|---|
| `base` | hostname, timezone, packages, the MediaTek Wi-Fi/Bluetooth card off: drivers blocked, the card asleep (wired only, saves power) |
| `network` | the static address on `necropolis` (NetworkManager) |
| `users` | `hythm` in `wheel`, the `claude` automation account (key + passwordless sudo), root's password login from the LAN and WireGuard only |
| `storage` | the subvolume mounts (`/etc/fstab`), their owners and modes, the directories the cluster writes to |
| `nfs` | `/etc/exports` |
| `snapper` | timelines for `@photos`, `@documents` and `@mail` |
| `monitoring` | `smartctl_exporter` (pinned release; Renovate bumps it) |
| `backpack` | the nightly off-site copy to the R2 bucket `backpack` (see below) |
| `services` | everything that must be enabled and running |

Settings live in [host_vars/chthon.yaml](host_vars/chthon.yaml).

## Run

```sh
task hosts:chthon CHECK=true     # dry run: --check --diff, changes nothing
task hosts:chthon                # apply
task hosts:chthon TAGS=nfs       # one part only
```

Ansible runs through `uvx` at a pinned version, so nothing is installed system-wide. It
connects as `claude` with `~/.ssh/qube-ops` (override with `SSH_KEY=`). The `backpack` tag
reads its credentials from Bitwarden, so `BWS_ACCESS_TOKEN` must be exported.

## backpack: the off-site copy

`backpack.timer` runs [files/backpack.sh](files/backpack.sh) nightly at 03:30, after
Paperless' export (23:30) and Immich's database dump (02:00). First it pulls `me@hythm.net`
from Migadu into `@mail` (Maildir, with `mbsync` and the read-only login `backup@hythm.net`,
`rune`/`mail-backup`). That copy only grows: mail deleted on Migadu stays. Then it copies to the
R2 bucket `backpack`:

| Prefix | What | Encrypted with |
|---|---|---|
| `volsync/` | the VolSync kopia repository (`@backup/kopia`), mirrored blob for blob | VolSync's password (`qube`/`volsync_template`) |
| `files/` | `@photos`, `@documents` and `@mail`, from read-only btrfs snapshots; keeps 3 latest, 7 daily, 4 weekly, 12 monthly | its own password (`rune`/`backpack`, also in the personal vault) |

Each run pings the Healthchecks.io check **off-site backup** (`/start`, then success or
`/fail`), so a missed or failed night pages. Run it by hand with `systemctl start
backpack` and follow it with `journalctl -fu backpack`.

R2 has no S3 Object Lock and its bucket locks would block kopia's overwrites and garbage
deletes, so the copy isn't immutable: the only key that can write it lives on chthon,
scoped to this bucket.

## Rebuilding from bare metal

The playbook starts from a fresh openSUSE Leap 16 install. Before it can run:

1. Install Leap 16 on `nvme0n1` (the OS disk only; leave `nvme1n1`/`nvme2n1` alone). Set the
   hostname `chthon`, create the user `hythm`, and set the root password from Bitwarden
   `rune`/`chthon-root`.
2. Give it 10.1.10.5 (or let the playbook's `network` tag do it from a temporary DHCP
   address), and allow SSH.
3. Create the `claude` account with the key from `host_vars` (or run the first pass as
   `hythm`: `task hosts:chthon -- -u hythm -k -K`).

Then `task hosts:chthon`. **The data array is not created by the playbook.** An OS reinstall
doesn't touch it: the mounts find it by its UUID and everything is back. Only on brand-new
drives create it first:

```sh
mkfs.btrfs -L data -d raid10 -m raid10 /dev/nvme1n1 /dev/nvme2n1   # raid10 over two devices
mount /dev/nvme1n1 /mnt
btrfs subvolume create /mnt/@media      # and @backup @photos @documents @mail
umount /mnt                             # then set data_uuid in host_vars
```

Snapshots are not backups. Off-site copies of `@photos` and `@documents` are still to do.

## Not managed

- Package updates: `sudo zypper patch` (twice) and `sudo zypper up`, then reboot. Cockpit's
  update page fails on Leap 16.
- btrfsmaintenance (monthly scrub, weekly balance of `/`) and smartd keep their openSUSE
  defaults.
- The root snapper config comes with the installer.
