# hostcd — operations (day two)

## Upgrades

hostcd upgrades server-first: upgrade `hostcd-server`, then the agents. The protocol is version-compatible across a release, so a newer server speaks to older agents during a rollout. Re-running the installer swaps the binary and restarts the unit.

Upgrade an agent by re-running the agent install (or swapping the verified binary and `systemctl restart hostcd-agent`); the token in `/etc/hostcd/agent.env` is preserved, so there is no re-enrolment.

## One-click self-update (opt-in)

Because the server runs unprivileged it cannot replace its own binary, so one-click update is **off by default**. Enable it at install time with `HOSTCD_SELF_UPDATE=1` (cosign must be installed on the host — it is mandatory for the unattended root updater). This adds:

- a root `hostcd-update.service` oneshot that re-runs the signed installer;
- a root `hostcd-update.path` unit that starts it when the server writes a trigger file;
- `HOSTCD_UPDATE_COMMAND` in `server.env`.

With it enabled, the UI shows the running version in the sidebar, a **What's new** panel with the release notes, and an **Update now** button. Clicking it pins the latest tag, verifies the installer's cosign provenance and checksum, swaps the binary, and restarts — the UI waits and reloads on the new version. The manual install command stays available either way.

## Backup and restore

The **Backup** screen exports the full server state (applications, hosts, projects, users, settings) to a file, and restores from one. Keep a periodic export; the Recovery screen shows when the last export ran.

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
