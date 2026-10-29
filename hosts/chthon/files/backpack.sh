#!/usr/bin/env bash
# backpack: chthon's nightly off-site copy to the R2 bucket `backpack` (docs/rebuild.md).
#   volsync/  the VolSync kopia repository, mirrored blob for blob (already encrypted)
#   files/    a kopia repository of @photos, @documents and @mail (read-only snapshots, own password)
# Before that it pulls me@hythm.net's mail from Migadu into @mail.
# Settings and credentials come from /etc/backpack/env (EnvironmentFile of backpack.service).
set -euo pipefail

export KOPIA_CHECK_FOR_UPDATES=false
STATE=/var/lib/backpack
CACHE=/var/cache/backpack            # one subdirectory per repository, never shared
STAGING=/data/@backup/.backpack      # same btrfs filesystem as the sources
S3=(--bucket="$BACKPACK_BUCKET" --endpoint="$BACKPACK_ENDPOINT" --region=auto)

ping_hc() { [ -n "${BACKPACK_HEALTHCHECK_URL:-}" ] && curl -fsS -m 10 --retry 3 -o /dev/null "${BACKPACK_HEALTHCHECK_URL}$1" || true; }
cleanup() {
  local snap
  for snap in "$STAGING"/*; do
    if [ -d "$snap" ]; then btrfs subvolume delete "$snap" >/dev/null; fi
  done
}
trap 'cleanup; ping_hc /fail' ERR
ping_hc /start
mkdir -p "$STATE" "$STAGING"
cleanup

# 0. Mail: every folder of me@hythm.net into @mail, as Maildir. It only adds: mail deleted on
#    Migadu stays here (/etc/backpack/mbsyncrc: Sync Pull, Expunge None, Remove None). It runs
#    first so tonight's @mail snapshot below has it; a failure fails the whole run (and alerts).
mkdir -p /data/@mail/me
mbsync --config /etc/backpack/mbsyncrc --all --quiet

# 1. App configs: mirror the VolSync repository. This client never owns it, so it never
#    runs maintenance on it; VolSync's KopiaMaintenance does.
VOLSYNC=(--config-file="$STATE/volsync.config")
if ! KOPIA_PASSWORD="$VOLSYNC_KOPIA_PASSWORD" kopia "${VOLSYNC[@]}" repository status >/dev/null 2>&1; then
  KOPIA_PASSWORD="$VOLSYNC_KOPIA_PASSWORD" kopia "${VOLSYNC[@]}" \
    repository connect filesystem --path=/data/@backup/kopia --readonly \
    --cache-directory="$CACHE/volsync" >/dev/null
fi
KOPIA_PASSWORD="$VOLSYNC_KOPIA_PASSWORD" kopia "${VOLSYNC[@]}" \
  repository sync-to s3 "${S3[@]}" --prefix=volsync/ --delete --parallel=4 --no-progress

# 2. Photos and documents: a fixed path per source, so kopia keeps one history per source.
export KOPIA_PASSWORD="$FILES_KOPIA_PASSWORD"
FILES=(--config-file="$STATE/files.config")
if ! kopia "${FILES[@]}" repository status >/dev/null 2>&1; then
  if ! out=$(kopia "${FILES[@]}" repository connect s3 "${S3[@]}" --prefix=files/ \
             --cache-directory="$CACHE/files" 2>&1); then
    case "$out" in
      *"not initialized"*) kopia "${FILES[@]}" repository create s3 "${S3[@]}" --prefix=files/ \
                            --cache-directory="$CACHE/files" ;;
      *) echo "$out" >&2; false ;;
    esac
  fi
fi
kopia "${FILES[@]}" policy set --global \
  --keep-latest="$BACKPACK_KEEP_LATEST" --keep-hourly=0 --keep-daily="$BACKPACK_KEEP_DAILY" \
  --keep-weekly="$BACKPACK_KEEP_WEEKLY" --keep-monthly="$BACKPACK_KEEP_MONTHLY" --keep-annual=0 >/dev/null
# this client owns the files repository, so kopia runs its scheduled maintenance itself after
# each snapshot (quick hourly, full every 24h)
kopia "${FILES[@]}" maintenance set --owner=me >/dev/null

for src in $BACKPACK_SOURCES; do
  name=$(basename "$src")                                   # @photos, @documents
  btrfs subvolume snapshot -r "$src" "$STAGING/$name" >/dev/null
  kopia "${FILES[@]}" snapshot create "$STAGING/$name" --no-progress --description="$src"
  btrfs subvolume delete "$STAGING/$name" >/dev/null
done

ping_hc ""
