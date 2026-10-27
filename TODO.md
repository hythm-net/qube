# Manual follow-ups (qube migration, 2026-09-29)

## Post-cutover
- [x] **OPNsense**: Unbound query-forward `hythm.net → 192.168.20.253`; host overrides `internal.hythm.net → 192.168.20.251`, `external.hythm.net → 192.168.20.252`; delete the `ahla.show` forward zone + `internal/external.ahla.show` overrides
- [x] **GitHub webhook** on hythm-net/qube (moved with the repo) → `https://flux-webhook.hythm.net/hook/<receiver path>`
- [ ] **Clients**: repoint Jellyfin apps / bookmarks `play.ahla.show → play.hythm.net`; Seerr Application URL → `requests.hythm.net`; Wizarr server URL → `join.hythm.net`
- [x] **Cloudflare (ahla.show)**: cluster-owned records deleted (only the apex A remains); let the domain lapse
- [x] **Bitwarden SM**: retired keys deleted (`ahlatoken`, `ahla_*`, `ahlabot`, `chatwoot`, `lldap`, `authelia`, `wizarr_stripe_bridge`, `cloudnative_pg`, `*_4k`). Still present but unreferenced — decide later: `bitwarden`, `domains`, `eweka`, `nzbfinder`, `nzbgeek`, `home_assistant`, `paperless`, `pushover`, `slskd`, `sops`
- [ ] **GitHub org `ahlanet`**: `website`, `wizarr-stripe-bridge`, `marketing` archived ✔; still to do in the web UI: uninstall `ahlabot` (https://github.com/organizations/ahlanet/settings/installations/125666771), then delete or leave the org

- [x] **Kubernetes**: orphaned `ahla-*-tls` secrets deleted
- [ ] **GitHub**: delete the unused `qube-runner` GitHub App in the web UI (https://github.com/settings/apps/qube-runner/advanced) — `novyxz` covers the runner
- [x] **Renovate catch-up**: done 2026-09-30 — Talos v1.14.2, Kubernetes v1.37.1, all charts/containers current (kube-prometheus-stack 88.2.0 waits on its weekly schedule)
- [ ] **Upstream pass**: review the last ~3 months of buroa/home-ops and onedr0p/home-ops (workflows, presets, apps); check the DRA driver upstream for a fix to ResourceSlices vanishing after a plugin restart

## Watch-list (no action now)
- `home-selfsigned-ca` subject organization still says `ahla.show` — cosmetic; changing it re-issues the CA and every chained cert (incl. Bitwarden SDK TLS)
- `talos/talosconfig` admin cert now valid to 2031-09-29 (re-minted 2026-09-29 after the 1-year default expired; see `talosctl config info`)
- kopiur (buroa's volsync replacement) — blocked on CSI snapshot support; re-evaluate if storage ever moves off openebs-hostpath
- spegel — only worth it if a second node is added
- Renovate on GitHub-hosted runners is capped at 2 000 min/month on the personal plan; move to renovate-operator in-cluster if the 4-hourly cron still bites
