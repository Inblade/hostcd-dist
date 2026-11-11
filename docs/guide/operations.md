# hostcd — operations (day two)

## Upgrades

hostcd upgrades server-first: upgrade `hostcd-server`, then the agents. The protocol is version-compatible across a release, so a newer server speaks to older agents during a rollout. Re-running the installer swaps the binary and restarts the unit.

Upgrade an agent by re-running the agent install (or swapping the verified binary and `systemctl restart hostcd-agent`); the token in `/etc/hostcd/agent.env` is preserved, so there is no re-enrolment.

## Per-host agent tokens (SSH-less hosts)

Install-over-SSH mints a per-host token automatically, so each Linux host authenticates with its own token and can be revoked on its own. A host with no SSH path — a Windows agent, or an air-gapped host — enrols with the shared token instead. From **v0.3.17** you can move it onto a per-host token: mint one with `POST /api/hosts/{name}/token` (admin), set it in the agent's config, and restart the agent. The token is returned once and the host's previous token stops working immediately, so set it promptly. Once every host has a per-host token you can retire the shared token. For the exact Windows (RDP) steps see the Windows guide.

## One-click self-update (opt-in)

Because the server runs unprivileged it cannot replace its own binary, so one-click update is **off by default**. Enable it at install time with `HOSTCD_SELF_UPDATE=1` (cosign must be installed on the host — it is mandatory for the unattended root updater). This adds:

- a root `hostcd-update.service` oneshot that re-runs the signed installer;
- a root `hostcd-update.path` unit that starts it when the server writes a trigger file;
- `HOSTCD_UPDATE_COMMAND` in `server.env`.

With it enabled, the UI shows the running version in the sidebar, a **What's new** panel with the release notes, and an **Update now** button. Clicking it pins the latest tag, verifies the installer's cosign provenance and checksum, swaps the binary, and restarts — the UI waits and reloads on the new version. The manual install command stays available either way.

## Backup and restore

Use two layers together.

**In-app export.** The **Backup** screen exports the full declarative state (applications, hosts, projects, users, settings) to a file and restores from one; the Recovery screen shows when the last export ran. This file carries no secrets, so it is safe to store anywhere — but on its own it cannot unseal sealed data (SSH keys, webhook and audit-sink secrets).

**Filesystem snapshot (full recovery).** To stand a control plane back up exactly as it was — sealed secrets included — back up the data directory and the seal key together:

- `state.json` — the full state
- `bootstrap.key` — the AES-256-GCM seal key. **Without it the sealed secrets cannot be decrypted.**
- `session.key`, `audit.json` — session signing and the audit trail
- `server.env` and your TLS cert/key — to restart with the same identity

Because that key decrypts everything, treat the snapshot like a secret: keep it `0600`, encrypt it in transit and at rest, and store it **off-box** — a snapshot that lives only on the server it protects does not survive losing that server.

An hourly systemd timer whose service does a copy-then-tar of the files above into a root-`0600` tarball (rotating the newest N) gives a point-in-time backup; replicate it off-box on the same cadence. The file store persists on every mutation, so each snapshot is internally consistent and the **RPO equals the snapshot interval** (hourly → ≤ 1 h).

**Restore** onto a fresh or rebuilt host: install the same server version, drop the backed-up `state.json` + `bootstrap.key` (and `session.key`, `audit.json`) into the data directory, restore `server.env` and TLS, then start the server. It comes up with every application, host, user, project, webhook and audit sink intact, and the seal key decrypts the sealed secrets. On a small fleet this **RTO is a few seconds**. The `backup-restore` CI job exercises the seal round-trip on every build, and you can rehearse recovery safely by restoring into a throwaway data directory and starting a second server on a loopback port (no TLS, no `-agent-dist`) — no agent can reach it, so nothing is applied.

## High availability (Enterprise)

With the Postgres backend, run multiple servers: reads are served anywhere and writes go through an elected leader (writes from a standby are forwarded). The Recovery screen shows HA and leadership status.

## Metrics

`/metrics` exposes Prometheus metrics (host online/offline counts, app sync state, and more). On an untrusted network protect it with `-metrics-token`; the Security screen flags when it is open.

## A typical change

1. Commit a manifest change to the app's Git folder and push.
2. hostcd shows the app **Out of sync** with a diff (the preview).
3. For a gated (approval-required) app, one admin requests the sync and a different admin approves; otherwise it applies on sync or automatically.
4. The rollout runs host by host; the result is recorded in history and sent to any webhook and audit sink.
5. If something is wrong, **roll back** to the previous revision from the UI.

Next: [overview](overview.md) · [concepts](concepts.md) · [security](security.md).
