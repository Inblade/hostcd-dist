# hostcd operations runbook

Day-2 procedures for running hostcd in production: backup, restore, upgrade,
HA key distribution, failover and incident response. Paths below match the
sample units in [`deploy/`](../deploy) (`hostcd-server.service`, data dir
`/var/lib/hostcd-server`, env `/etc/hostcd/server.env`). Adjust for your layout.

## What is state, and what is secret

The server keeps everything in its **data dir**:

| file | what it is | lose it and… |
|------|------------|--------------|
| `state.json` (+ `.bak`) | all apps, hosts, clusters, users, sealed secrets | you lose the deployment; the sealed blobs are not in the config export |
| `bootstrap.key` | the data-encryption key that seals SSH keys, kubeconfigs, agent CA, webhook/SCM secrets, the session key | `state.json` becomes undecryptable — **back it up with the state, never separately** |
| `session.key` | legacy local session signing key; superseded by the sealed `SessionKey` in state | only logs everyone out |
| `audit.json` | the audit trail | you lose history |
| `repos/`, `trees/` | git cache | nothing — rebuilt on demand |

The key invariant: **`state.json` and `bootstrap.key` are one unit.** The server
seals a check value into the state and **refuses to start** if the `bootstrap.key`
it loads cannot open it, so a state restored without its matching key fails loudly
instead of coming up unable to decrypt.

With `-vault-addr`, the on-disk `bootstrap.key` is the Vault-wrapped ciphertext;
the plaintext key never touches disk. Back up the wrapped file and make sure the
same Vault Transit key is reachable on restore.

With `-store-dsn` (Postgres), `state.json` lives in the database instead; your
state backup is the DB backup — but `bootstrap.key` is still a local file on each
node and still must be backed up and distributed (see *HA* below).

## Backup

**File backend (single node).** Take a *consistent* snapshot of the whole data
dir. Stop the server briefly, or take a filesystem snapshot (LVM/ZFS/btrfs):

```sh
umask 077                               # archive holds bootstrap.key — keep it private
systemctl stop hostcd-server            # for a guaranteed-consistent copy
tar czf hostcd-$(date +%F).tgz -C /var/lib/hostcd-server .
systemctl start hostcd-server
chmod 600 hostcd-$(date +%F).tgz
```

Do **not** rely on a hot `tar` of the running data dir for a supported backup.
Individual saves are atomic, but a hot archive can still capture files from
different moments: during a `bootstrap.key` rotation the archive can catch
`bootstrap.key`, `bootstrap.key.prev` and the re-sealed `state.json`/`session.key`
mid-swap, which restores to an *undecryptable* state. The `state.json.bak`
fallback only rescues a single corrupt `state.json`; it does not make a
multi-file hot archive consistent. If you cannot stop the server, use a
filesystem snapshot so every file is captured at one instant. (A built-in
`hostcd backup` that takes a consistent snapshot of a live server is tracked as
a follow-up — see *Known gaps*.)

**Encrypt and protect the archive.** It contains `bootstrap.key`, i.e. the keys
to every sealed secret (SSH keys, kubeconfigs, agent CA, webhook/SCM secrets). A
plaintext `.tgz` on a shared or offsite disk exposes all of them. Store it
encrypted and off the running host — for example with [age](https://age-encryption.org):

```sh
umask 077
tar czf - -C /var/lib/hostcd-server . | age -r age1yourrecipient... \
  > hostcd-$(date +%F).tgz.age
```

…or hand the archive to a KMS/SOPS pipeline or the client's existing encrypted
backup system. Never keep an unencrypted copy on a multi-user host.

**Postgres backend.** Back up the database and every node's `bootstrap.key`:

```sh
umask 077
pg_dump "$HOSTCD_STORE_DSN" > hostcd-db-$(date +%F).sql
cp /var/lib/hostcd-server/bootstrap.key bootstrap.key.backup   # same on every replica
chmod 600 hostcd-db-$(date +%F).sql bootstrap.key.backup
```

Encrypt both the dump and the key copies the same way — the dump holds the same
sealed secrets, and the keys decrypt them.

## Restore

1. Install the same (or newer — see *Upgrade*) `hostcd-server` binary.
2. Put the data back **key first**: restore `bootstrap.key` (and `session.key` if
   you keep it), then `state.json` — or just untar the whole archive.
   - Postgres: `psql "$HOSTCD_STORE_DSN" < hostcd-db-YYYY-MM-DD.sql`, and place the
     backed-up `bootstrap.key` in the node's data dir.
3. Start the server. If it logs *"bootstrap.key does not match the stored state"*,
   the key and the state are from different deployments — restore the matching
   `bootstrap.key`. The server will not run until they agree.
4. Confirm: `curl -fsS localhost:8080/healthz`, sign in, check the Fleet tab.

This whole backup → destroy → restore path (plus the mismatched-key refusal in
step 3) is exercised on every push by
[`reliability/backup-restore.sh`](../reliability/backup-restore.sh), a local
disaster-recovery drill that verifies the archive's checksum, restores into a
fresh data dir, and confirms the committed state is back and its sealed secrets
still decrypt — so "restore works" is a tested property, not a documented hope.

## Upgrade

hostcd keeps backward-compatible state, so an upgrade is a binary swap:

```sh
# back up first (above)
install -m0755 hostcd-server /usr/local/bin/hostcd-server
systemctl restart hostcd-server
```

- **Postgres schema** is migrated automatically and idempotently on start
  (versioned, advisory-locked so simultaneous replicas don't collide). A database
  from an older hostcd with no version table is adopted at the baseline.
- **Rollback:** stop, reinstall the previous binary, and — only if the newer
  version wrote state the old one can't read — restore the pre-upgrade `state.json`.
  Take the backup before every upgrade so this is available.
- **HA:** restart one replica at a time behind the load balancer; the leader lease
  moves on its own. Do not run mixed versions longer than a rollout window.

## High availability

Several replicas share state — either a `-ha` lease over a shared `-data`
filesystem, or (preferred) `-store-dsn` Postgres with per-node data dirs. On
Postgres, set `-advertise-url` on each node so a standby forwards writes to the
leader instead of 503-ing.

**Every replica must have the same `bootstrap.key`.** The database/state is
shared but the data dir is not, and the sealed secrets only open with the key
that sealed them. Mount the key from one secret (Kubernetes Secret, etc.) or copy
it to each node. The session key is sealed into the shared state, so replicas
accept each other's login cookies automatically — only `bootstrap.key` needs
hand-distribution. A replica started without the shared key refuses to run (the
check value above), so a misconfiguration is caught immediately, not in
production. Sealing-key **rotation** is a single-node, cluster-stopped operation
(`POST /api/admin/rotate-sealing-key`, refused under `-ha`).

**Failover** is automatic: the leader lease (a file under `-ha`, the
`hostcd_leader` row on Postgres) expires and a standby takes over within a lease
interval. Nothing to do by hand; a `/healthz`-driven load balancer keeps sending
writes to whichever node is serving.

## Incident response

- **Suspected agent-token leak on a host:** *Revoke* it (host row → *Revoke*, or
  `POST /api/hosts/{name}/revoke`). The agent is cut off immediately — its own
  token and the shared token are both refused — while the host's config and app
  assignments are kept. *Reinstall* over SSH issues a fresh token and clears the
  flag. Revocation is audited.
- **Suspected session/cookie compromise:** *Users → Sign out* a user
  (`POST /api/users/{name}/revoke-sessions`) invalidates all their sessions; an
  admin password reset does the same automatically.
- **Suspected sealing-key compromise:** rotate it (single node, cluster stopped),
  then rotate the upstream credentials that were sealed (SSH keys, kubeconfigs).
- **A cluster provisions Ready but cross-node pods can't talk:** almost always a
  blocked inter-node port (most often the CNI VXLAN UDP port). See the network
  prerequisites in the README's *Clusters* section.

## Scale and limits

hostcd keeps the whole state in memory and writes it as one document, so the two
costs that grow with fleet size are the full-document **save** (every mutation
rewrites it) and the **read roll-ups** (the hosts list and the fleet dashboard,
both O(hosts × apps), computed under the global lock). The harness
`TestFleetScale` measures them — run it to re-check on your hardware:

```sh
HOSTCD_SCALE=1 go test ./internal/control/ -run TestFleetScale -v -timeout 20m
# optional: HOSTCD_SCALE_SIZES="1000,5000,10000"
```

Indicative numbers from a dev laptop (apps = 200, every app selecting every host
— a worst case for the roll-up loops):

| hosts | full save | `GET /api/hosts` | `GET /api/fleet` | state.json |
|------:|----------:|-----------------:|-----------------:|-----------:|
| 1,000 | 2 ms | 33 ms | 19 ms | 0.6 MB |
| 5,000 | 9 ms | 162 ms | 90 ms | 2.4 MB |
| 10,000 | 16 ms | 324 ms | 187 ms | 4.7 MB |
| 25,000 | 41 ms | 829 ms | 557 ms | 12 MB |

Reading it: **writes stay cheap and linear** (41 ms to rewrite the whole document
at 25k hosts) — fine, because mutations are human/CI-paced, not high-frequency.
The **read roll-ups are the ceiling**: they are O(hosts × apps) and hold the
global lock while they run, so past ~10–15k hosts they slow *and* a roll-up can
briefly stall mutations. hostcd is comfortable to about **10k hosts** per instance
on modest hardware. (The fleet roll-up used to sort the host set once per app;
that sort was removed, roughly halving `GET /api/fleet`. The hosts list is now the
heavier of the two and is still O(hosts × apps) by nature.)

If you outgrow that: cut the number of broad-selector apps (the roll-up cost is
hosts × matching apps), lean on the git webhook (it already refreshes only the
apps whose repo changed, not the whole fleet), and — the natural shard — run one
hostcd per region/failure-domain rather than one global instance. A single
process is not meant to be the control plane for every host you own.

## Network prerequisites

Provisioning kubeadm clusters requires inter-node ports to be open in your cloud
firewall / security group **before** you provision — hostcd cannot open them, and
kubeadm will reach `Ready` even when overlay traffic is blocked. The full list is
in the README's *Clusters (provision Kubernetes over SSH)* section.

## Subscription licensing

hostcd is **open-core** (see `LICENSING.md`). The **core** — server, agent, web
UI and git-driven host config — is free and needs no license. A set of
**Enterprise features** require a license that grants them:

| Feature key    | Capability |
|----------------|------------|
| `sso`          | SAML 2.0 and OIDC single sign-on |
| `ha`           | Postgres-backed active/standby HA (`-ha`/`-store-dsn`) |
| `scim`         | SCIM 2.0 provisioning (`-scim-token`) |
| `vault`        | Vault Transit sealing (`-vault-*`) |

hostcd verifies a **license token** offline against a built-in ed25519 public
key — there is no phone-home, so an air-gapped deployment works the same. The
license carries a feature list. **Enforcement fails closed**: if an Enterprise
feature is configured but no valid license grants it, the server **refuses to
start** and names the feature. With no license the deployment runs as the
**Community** edition — every *core* feature works; no Enterprise feature does.

Operate it from **Settings → Subscription**: paste a token to install or renew
it, or remove it to fall back to Community. A token can also be supplied at
startup with `-license-key` (env `HOSTCD_LICENSE_KEY`); a license installed
through the UI takes precedence so a renewal survives restarts without a flag
change. (A feature gate is evaluated at startup, so a token that *enables* a
feature must be present via `-license-key`/embedded at boot, not only installed
later through the UI.)

A subscription keeps working for a **grace period** (default 14 days,
`-license-grace`) past its expiry; tier features keep working through the grace
window and go dormant once it lapses. A lapse **never** blocks the control plane
or core writes — there is no global write-lock — so pasting a current token in
the UI restores the features at any time.

#### Recovering an Enterprise feature after a lapse

Every Enterprise feature is gated at **runtime** by the live entitlement, so a
lapse **never stops the server** — it starts and keeps your state reachable, and
you re-enable the feature by installing a current token, with no restart:

- **HA and Vault** hold or unseal your data: on a lapse the server starts
  degraded, logs a warning, and your state stays reachable.
- **SSO and SCIM** start **disabled** (a warning in the log): SSO login behaves
  as "not configured" and the SCIM endpoint returns `404`, while **local admin
  login always works**, so you are never locked out of the UI.

Recover by either:

1. install a current token in **Settings → License** (no restart) — or pass it in
   `-license-key` (env `HOSTCD_LICENSE_KEY`) on the next start; or
2. for a lapse of a few days, rely on the 14-day grace window, which keeps the
   feature running while you renew.

Removing the feature's configuration flags is optional — the server no longer
requires it to boot.

### Issuing licenses (maintainer)

The signing **private key never lives in the repo** — and the public key is not
committed either; it is injected at build time. Use the maintainer CLI:

```sh
make license-tool                       # builds ./bin/hostcd-license
./bin/hostcd-license keygen -out hostcd-license.key   # writes the private key (0600), prints the public key
```

Keep `hostcd-license.key` offline. Build the commercial server with the printed
public key baked in (no source edit, no committed key — `embeddedLicensePubKey`
is a `var`, set via `-ldflags -X`):

```sh
make build-commercial LICENSE_PUBKEY=<public key from keygen>
```

Sign a customer token with the private key, then hand the token to the customer:

```sh
./bin/hostcd-license sign -key hostcd-license.key \
  -licensee "Acme Inc" -plan business -seats 25 -days 365 -features ha,sso
./bin/hostcd-license verify -token <token> -key hostcd-license.key   # sanity check
```

To grant the **extended Team trial** (the email-gated second phase, after the
automatic 14-day trial), mint a `trial`-plan token — it carries the Team trial
features and nothing else, and the server caps it to those regardless:

```sh
./bin/hostcd-license trial -key hostcd-license.key -licensee "Acme Inc" -days 30
```

A token is `base64url(payloadJSON) + "." + base64url(ed25519-signature-over-
payloadJSON)`; the payload is `{id, licensee, plan, seats, features, issuedAt,
expiresAt}` with RFC3339 times. Operators verify any token without the private
key — install it on **Settings → Subscription** and the status shows there. For
testing, override the verification key at runtime with `-license-pubkey` instead
of rebuilding.

## Known gaps

- **Built-in consistent backup.** There is no `hostcd backup` command yet that
  takes a consistent snapshot of a *live* server. Until there is, a supported
  file-backend backup requires a brief stop or a filesystem snapshot (see
  *Backup*). A hot `tar` of the running data dir is not a supported backup.
- **Backup encryption is the operator's responsibility.** hostcd does not yet
  encrypt the archive itself; wrap it with age/SOPS/KMS or your backup system.
