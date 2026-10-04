# Screenshot privacy review

The tutorial and documentation image collection was reviewed on 4 October 2026.
The review covered all 97 raster assets under `docs/images`, including the logo,
legacy examples, integration setup pages, email setup, and delivery evidence.

Private details were replaced with opaque masks in 83 screenshots. The masks
cover account names, email addresses, profile portraits, private domains and
network addresses, deployment/device identifiers, and unrelated personal folder
listings. The Gmail and Microsoft images were redacted from the original captures
using the same local method; they are not AI reconstructions.

Masked screenshots are saved as lossless PNGs without embedded metadata. Decoded
pixels outside every mask were checked against the original capture and remain
identical. The review combined visual inspection with OCR on the original and
enlarged images; OCR is a supporting check, not a substitute for visual review.

Written tutorials and attached JSON/HTML validation records also use anonymized
site names and documentation addresses in `192.0.2.0/24`. These addresses are
examples, not endpoints readers should connect to. Recorded HTTP statuses,
event states, timestamps and validation limitations retain their original meaning.

Before adding or replacing a screenshot:

1. Inspect the full image, including browser/account chrome, sidebars, messages,
   logs, callback URLs, personal folders and profile pictures.
2. Cover private data with solid opaque masks. Never rely on blur or a password
   input alone to sanitize an exported image.
3. Export a flattened image without metadata, inspect it again at readable size,
   and update its tutorial links.
4. Keep raw captures and credential-bearing configuration outside the repository.
5. Review captions so synthetic tests are not described as native delivery proof.

This update sanitizes the current files. Earlier committed screenshots remain in
Git history; it does not rewrite repository history or remove cached copies.
