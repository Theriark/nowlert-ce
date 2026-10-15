# Security hardening and scan review

Run security review against the exact `development` commit and deployed image,
then repeat it for the immutable Stage candidate before release. Default-branch
results can refer to an older released build. Code-quality counts are separate
from security findings; a passing functional suite is not security approval.

## Dependency and build controls

Runtime dependencies are pinned. `urllib3` must be at least 2.8.0 for
[CVE-2026-97687](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77),
[CVE-2026-97688](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g),
and [CVE-2026-97689](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw).
Check the installed image version as well as `requirements.txt`. Static and
runtime reports can describe the same advisory and must not be added as unique
vulnerabilities. Docker GitHub Actions use full commit pins, with the upstream
release series recorded beside each pin. Only the Development image-publishing
job receives package-write permission.

Both container images default to a non-root UID and include an HTTP healthcheck.
Existing volume ownership and deployment-level user/capability overrides must
also be checked; changing Dockerfile defaults does not change those overrides.
See [deployment and ownership migration](deployment.md).

## Error messages and email links

The browser displays bounded, credential-redacted API client-error messages or
fixed recovery guidance. Unexpected exceptions and HTTP 500 diagnostic messages
are not displayed. Resource-list failures identify the affected resource using a
stable error code without returning internal exception text. API status, path,
code and reference remain available as structured diagnostics.

Email provider links are checked in both the backend and browser. Only HTTPS
URLs without embedded credentials are accepted; invalid links have no action.
Links open with `noopener noreferrer`.

## Context-specific scan results

`src/storage/mfa.py` deliberately uses HMAC-SHA1 for the
[RFC 6238 TOTP protocol](https://www.rfc-editor.org/rfc/rfc6238.html).
It is not password hashing or unkeyed SHA1. Changing it would invalidate enrolled
authenticator configurations. The single `datadog/python-weakhash` instance is
annotated with that rationale and covered by RFC timestamp vectors. Recovery
codes use SHA256 and remain independent one-time credentials. No broad SAST
ruleset is disabled.

SMTP protocol tests generate an ephemeral certificate and private key in pytest's
temporary directory, trust that certificate explicitly, and verify its hostname.
No private TLS fixture key is committed or included in either image.

Do not suppress genuine container privileges as a false positive. The optional
managed-backup mount mode and any deployment using it require the explicit
privilege review described in the deployment guide. Host-mounted backup shares
avoid container mount capabilities.

## Release evidence

Keep the candidate SHA, image digest, scan timestamps and reviewed disposition of
each finding together. Verify SMTP TLS, authentication/MFA, actionable validation,
email links, backups, and startup on migrated volumes. Do not call a candidate
security-cleared while dependency findings, unreviewed code alerts or deployment
privilege decisions remain unresolved.
