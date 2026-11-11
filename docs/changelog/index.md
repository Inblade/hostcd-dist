# Changelog

All notable changes to hostcd are documented here. This project uses date-based
`vMAJOR.MINOR.PATCH` tags; security releases are called out explicitly.

## [0.3.18] — 2026-11-11
### Added
- **Read-only mode** (`-read-only`) — the server refuses every mutating request
  with a clean JSON `403` and advertises `readOnly:true` in the session, while the
  UI gates its write controls (the "New folder" button and other mutations are
  hidden for a read-only session). The agent poll is a token-authed `POST` outside
  the session-auth wrapper, so agents keep reconciling. Two companion flags shape
  the read-only banner: `-read-only-note` sets the reset-cadence sentence and
  `-read-only-link` renders a "Learn more →" link. This is what powers the public
  anonymous demo.
### Security
- **Toolchain bumped to Go 1.26.11** — picks up the `net/http` fix for
  GO-2026-6859.
- **Fresh installs authenticate `/metrics` by default** — `install.sh` now
  generates a `HOSTCD_METRICS_TOKEN` on first install, so a new server requires a
  bearer token to scrape metrics (remove the line in `server.env` to open it on a
  trusted network). A server started manually without the token still leaves
  `/metrics` open, as documented in the threat model.
- **The release fails if a required artifact is missing** — including the Windows
  agent — so `sha256sum -c` can no longer verify a release green while an artifact
  that silently failed to build is simply absent from `SHA256SUMS`.
### Fixed
- The modal/drawer scrim is now a neutral black, so it visibly dims the content
  behind it on the dark theme (it previously matched the dark page background and
  dimmed nothing).
- Truncated commit messages in the UI now show the full message in a tooltip.
### Docs
- Backup/restore runbook with explicit RPO/RTO in the operations guide; an RDP
  runbook for moving an SSH-less Windows agent to a per-host token; a top-level
  `ROADMAP.md` (now/next/later); a repo `CLAUDE.md`; and a roadmap-wording fix
  (approval gates / notifications / audit export are Team, not Enterprise).

## [0.3.17] — 2026-11-10
### Added
- **Mint a per-host agent token for an existing host** — `POST /api/hosts/{name}/token`
  (admin-only, audited). Per-host tokens were previously minted only by
  install-over-SSH, so a host with no SSH path (a Windows agent, or an air-gapped
  host) could not be moved off the shared enrolment token. The new endpoint mints
  a fresh per-host token, clears any revocation, persists the new digest **before**
  returning it, and returns the plaintext once — paste it into the agent's config
  and restart. It also rotates an existing per-host token. Minting invalidates the
  host's previous token immediately, so the agent is briefly offline until it is
  reconfigured with the new token.

## [0.3.16] — 2026-11-09 — reliability & HA hardening
### Security
- **Fixed a reload-path panic (DoS):** a config reload that produced a nil
  result set could panic the server; reload is now nil-safe.
- **`/metrics` no longer holds a lock across network I/O** — the snapshot is
  taken under the lock and written without it, closing a lock-contention/DoS
  window. (Operators on a public address should still set `-metrics-token`;
  `/metrics` is unauthenticated by default.)
### Changed (HA — Enterprise preview)
- Leader election now **demotes fail-closed** on a failed lease acquire/renew
  instead of keeping leadership until a later success (removes an unbounded
  split-brain window); `pgElector.release` errors are surfaced, not swallowed.
- A standby **reloads its cache after a LISTEN reconnect**, so a `NOTIFY` missed
  during a connection outage is still caught.
- Write-forwarding to the leader trusts system roots plus a configurable
  `-peer-ca` / `HOSTCD_PEER_CA` bundle (fixes self-signed peer TLS; never skips
  verification, fails closed) and retries once against a fresh leader URL when
  nothing has been written yet; an undeliverable forward returns `503` +
  `Retry-After` rather than a hard `502`.
- HA remains an **Enterprise preview** pending a multi-day two-node soak.
### Fixed
- The server **refuses a server-side install from a stale `-agent-dist`**
  (prevents a silent agent downgrade) and warns at startup on a version mismatch.
### Added
- `deploy/install.sh` can **auto-populate `-agent-dist`** with cosign/SHA256SUMS-
  verified agents in lockstep with the server version (opt-in via
  `HOSTCD_AGENT_DIST`; platforms via `HOSTCD_AGENT_DIST_PLATFORMS`), re-staged on
  every install/upgrade. The host drawer now shows server / hosted-dist /
  installed agent versions and flags drift.
### Internal
- Test coverage for `Package`/`Service.Apply`, engine `Run`/`Trigger`/`Snapshot`,
  the git source, and license removal; an HA fault suite (partition fail-closed
  demote, LISTEN-reconnect re-signal). CI now fails (not skips) Postgres tests
  when its DSN is missing, adds an embedded-key SSO end-to-end check, and the
  RUSTSEC-2024-0429 glib ignore self-expires once glib reaches ≥ 0.20.

## [0.3.15] — 2026-11-08 — security release
### Security
- **High:** fixed an app-destination **label-scope bypass** — a per-host agent
  token could read another scope's secret-bearing manifest by reporting crafted
  labels. Destination matching now uses admin-assigned labels only (frozen after
  enrolment; clears persist across restart/HA). Upgrade is recommended.
- **Medium:** `GET /api/audit` is now admin-only (was readable by scoped viewers).
- **Low:** `GET /api/events` (SSE) no longer leaks out-of-scope resource names to
  scoped viewers.
- Hardening: resource exec sinks reject option-injection in
  package/service/user/group names.
- Desktop: `tokio` → 1.54.1; `cargo-audit` now runs in required CI.
### Added
- Windows agent `hostcd-agent-windows-amd64.exe` published in releases (late beta;
  `package`/`file`/`service`). See `docs/WINDOWS.md`.
- UI: view and edit a host's admin-assigned targeting labels.
### Fixed
- Documentation consistency (pricing/trial wording); self-contained public
  release notes.

## [0.3.14] — 2026-11-07
### Security
- Bumped `golang.org/x/oauth2` to v0.27.0 (CVE-2025-22868).
### Changed
- Licensing docs reconciled to monthly pricing and the honest source-availability
  status; added CI docs-consistency and site-consistency guards.
