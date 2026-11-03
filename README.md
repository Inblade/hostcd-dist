# hostcd — public distribution

This is the **public distribution channel** for [hostcd](https://github.com/Inblade/hostcd): the
landing page and the signed release binaries. The source lives in the main repository
(BSL 1.1, source-available).

- **Landing page:** https://inblade.github.io/hostcd-dist/
- **Releases (binaries, `install.sh`, `SHA256SUMS`, cosign bundle, SBOM):** see the
  [Releases](https://github.com/Inblade/hostcd-dist/releases) tab.

## Install

```sh
# Pin the released version; binaries + units come from one release.
HOSTCD_RELEASE_BASE=https://github.com/Inblade/hostcd-dist/releases/download/<tag> \
  curl -fsSL https://github.com/Inblade/hostcd-dist/releases/download/<tag>/install.sh | sh -s -- server
```

Releases are **built and signed in the private source repository** and mirrored here
unchanged, so they stay independently verifiable: the cosign signature pins the
`Inblade/hostcd` release workflow identity regardless of this download mirror.

```sh
cosign verify-blob SHA256SUMS \
  --bundle SHA256SUMS.cosign.bundle \
  --certificate-identity-regexp '^https://github.com/Inblade/hostcd/\.github/workflows/release\.yml@refs/tags/v.+$' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
sha256sum -c SHA256SUMS
```
