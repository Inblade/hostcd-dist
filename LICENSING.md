# hostcd licensing & editions

hostcd is **open-core**. The Community core is licensed under the **Business
Source License 1.1** (see [`LICENSE`](LICENSE)), which converts to Apache-2.0 on
its change date. The **Enterprise modules** (SSO/SCIM, Postgres HA, Vault sealing)
are a separate commercial component gated by a signed license key and are **not**
part of the BSL-licensed work.

The public release in this repository ships signed binaries with keyless cosign
provenance and an SBOM you can verify independently (see the **Verify** section of
the [README](README.md)). The core source repository is not public today; it will
be published before GA.

**Editions, pricing, trial and grace windows, host limits, feature ownership and
lapse behaviour are documented authoritatively on the website:**

- Editions & pricing: <https://hostcd.dev/#editions>
- Licensing FAQ: <https://hostcd.dev/#faq>

This file is a pointer so the reference in `LICENSE` resolves; it intentionally
does not restate prices, which are maintained in one place on the website.
