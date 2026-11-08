# hostcd — public distribution

This is the **public distribution channel** for hostcd: the landing page and the
signed release binaries. hostcd keeps Linux servers reconciled to Git (drift
detection, previewed change, safe rollout) without inbound agent ports or
Kubernetes. The Community core is licensed under the Business Source License 1.1
(it converts to Apache-2.0 on its change date); the **source repository will be
published before GA**.

- **Landing page:** https://hostcd.dev
- **Releases (binaries, `install.sh`, `SHA256SUMS`, cosign bundle, SBOM):** see the
  [Releases](https://github.com/Inblade/hostcd-dist/releases) tab.

## Install (Linux)

The installer needs root, and it must be told to fetch binaries from this mirror
(the `HOSTCD_RELEASE_BASE` goes to the installer, not to `curl`):

```sh
curl -fsSL https://github.com/Inblade/hostcd-dist/releases/latest/download/install.sh \
  | sudo env HOSTCD_RELEASE_BASE=https://github.com/Inblade/hostcd-dist/releases/latest/download sh -s -- server
```

Swap `server` for `agent https://<control-plane> <TOKEN>` to enroll a managed host.
This pins the latest release; to pin a specific version, replace `latest/download` with `download/vX.Y.Z` in both URLs.

## Verify

Releases are **built and signed in the source repository** and mirrored here
unchanged, so they stay independently verifiable: the cosign signature pins the
`Inblade/hostcd` release workflow identity regardless of this download mirror.

```sh
cosign verify-blob SHA256SUMS \
  --bundle SHA256SUMS.cosign.bundle \
  --certificate-identity-regexp '^https://github.com/Inblade/hostcd/\.github/workflows/release\.yml@refs/tags/v.+$' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
sha256sum -c SHA256SUMS
```

## Windows agent (late beta)

The managed **host** can run Windows Server (amd64); the control plane itself is
Linux. Each release publishes `hostcd-agent-windows-amd64.exe` next to the Linux
binaries, under the same signed `SHA256SUMS` + cosign bundle and SBOM. It is a
**late-beta** target — validated live on Windows Server 2025 (`package` via
winget/Chocolatey, `file`, `service` via the Windows SCM); continuous drift/soak
and a native service wrapper are not yet proven.

Pull-based, so no inbound port to the Windows host. Download + verify, then enroll
(PowerShell **as Administrator**):

```powershell
$base = "https://github.com/Inblade/hostcd-dist/releases/latest/download"
Invoke-WebRequest "$base/hostcd-agent-windows-amd64.exe" -OutFile hostcd-agent.exe
Invoke-WebRequest "$base/SHA256SUMS" -OutFile SHA256SUMS
$want = (Select-String -Path SHA256SUMS -Pattern 'hostcd-agent-windows-amd64\.exe$').Line.Split(' ')[0]
$got  = (Get-FileHash hostcd-agent.exe -Algorithm SHA256).Hash.ToLower()
if ($got -ne $want) { throw "checksum mismatch — refusing to run" }
```

Run `hostcd-agent.exe` pointing at your control plane, or install it as a SYSTEM
scheduled task with the agent's own bootstrap (`windows-bootstrap.ps1`). The
Windows agent requires an **https** control-plane URL (http only for loopback) so
the enrolment token and the binary are never sent in the clear.
