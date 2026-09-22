# Notification presentation contract

Nowlert v3.1.2 uses shared presentation rules so integrations render
consistently across Discord and Microsoft Teams without duplicating product
logic in each formatter.

## Event time

The event source owns the visible timestamp.

- Use the timestamp emitted by the source machine or service.
- Convert timezone-aware source timestamps and epoch instants to the selected
  Nowlert display timezone before presentation.
- Treat a source timestamp without timezone information as an already-local wall
  clock; do not reinterpret it as UTC.
- Do not append UTC or numeric offset suffixes to the final card timestamp.
- Render recognized timestamps using the user's selected 12/24-hour preference.
- If no source timestamp exists, omit Event time rather than substituting the
  Nowlert receipt time.

Regional timezone and clock-format preferences are managed through the current
platform Settings UI/database model. The container `TZ` value remains the
runtime fallback when no explicit platform preference is available.

Do not add the removed legacy `presentation` YAML section to a fresh v3.1.2
configuration.

## Microsoft Teams hierarchy

Teams **Modern Card** reuses the exact Discord Modern image renderer instead of
maintaining a second Teams-specific visual implementation. The rendered card
therefore keeps the same dark grid, gold frame, lifecycle-colored rail/glow,
integration artwork, status badge, report title, summary strip, neutral detail
panels, outcome panels, dynamic content height, and
`Nowlert CE • Modern Card` footer.

The Teams transport wraps that rendered PNG in a minimal Adaptive Card 1.4
`Image` element. The image is normalized only to Teams' supported image bounds;
its layout/content is not rebuilt with native Teams text containers.

Because Teams workflow payloads are JSON-only and remain bounded to 28 KiB,
Nowlert does not embed the full PNG as Base64. When `webui.public_url` is a
credential-free public HTTPS address, the rendered image is stored below
`platform.state_dir/teams-modern-cards` under an unguessable immutable token
and exposed through `/ui/teams-modern-cards/<token>.png`. The cache retains
images for 90 days and removes expired entries opportunistically as new cards
are published.

If a public HTTPS WebUI address is not configured or the image cache is not
writable, Modern delivery falls back to the native Teams renderer rather than
dropping the notification. Teams Classic remains a separate renderer and is not
changed by Modern image parity.

The native Teams formatters remain available for that compatibility fallback
and for their existing presentation tests. Static product artwork still uses
the public HTTPS icon mapping and `NOWLERT_TEAMS_ICON_BASE_URL` compatibility
override.

## Discord hierarchy

Every integration supplies normalized data to the shared Discord Components V2
renderer:

1. Header: `device • event`, device/status icons, severity-aware accent, and
   official integration thumbnail.
2. Context: `integration • state • source area`.
3. Responsive separator plus the highlighted event message.
4. Compact Severity, Category, and Event time metrics.
5. Responsive separator plus optional integration details.
6. Final separator and one-line Nowlert version footer.

Discord controls separator width at render time, so rules remain responsive on
desktop/mobile. The shared renderer budgets component/text limits and removes
lower-priority optional facts before essential title/context/event/metrics/footer
content.

Discord product artwork is served from packaged assets and uploaded through the
output adapter rather than depending on a runtime external image host. Internal
asset references use the `nowlert-asset://` contract and are resolved before
transport.

### Discord Modern image cards

Discord Modern images use the Xen Orchestra visual components across all
integrations, including generic and internal notifications: a dark grid and
gold frame, a status-colored rail and glow, packaged integration artwork,
status badge, report title, metadata strip, neutral detail panels, colored
outcome panels, and the `Nowlert CE • Modern Card` footer. Success is green,
failure is red, warning is amber, and information/skipped is blue.

The image layout measures content before drawing. Badges, titles, source
context, field labels, values, VM names, and reasons wrap at readable font
sizes; they are not reduced or ellipsized to fit a fixed box. Panels and card
height grow for longer content and contract for shorter events. Compact panels
can share a row, while dense content gets full width. Short Xen Orchestra
success entries can use three columns; mixed outcomes retain every reported
success, failure, and skipped VM.

Non-Xen-Orchestra images reuse the sanitized Classic presentation content and
preserve integration-specific labels and details. This layout is exclusive to
Discord Modern: Classic cards and other destination formats are unaffected.
Discord controls the displayed attachment dimensions; the larger type is part
of the image itself, not merely a higher-resolution copy of small text.

## Missing and identifier values

Optional facts whose source value is missing or represented by `-`, `—`, `N/A`,
`None`, or `null` are omitted. Zero remains a meaningful value.

Identifiers/acronyms such as `PVE-01`, `VMID`, `CPU`, or `NVR` retain meaningful
source casing instead of being blindly title-cased.

## Status semantics

The shared renderer maps normalized state/severity to an icon plus destination
color. Text/icons always carry the semantic meaning so color is not the only
signal.

| State family | Icon | Teams color | Discord color |
|---|---:|---|---|
| Critical, disaster, failure | 🚨 | Attention | Red |
| Warning, degraded, average | ⚠️ | Warning | Orange |
| Resolved, recovered, success | ✅ | Good | Green |
| Information or unknown | ℹ️ | Accent | Blue |

The current state wins over historical severity: a recovered critical event is
shown as recovered, while an informational state carrying a critical severity
can still be rendered as critical when no resolved state is present.

## Integration artwork

Normalized 256 px transparent PNGs are packaged under `assets/icons/`.
Product-specific artwork should come from an official vendor source or source
repository. Record provenance/mechanical transformations in
`assets/icons/README.md`; do not introduce generated initials or lookalike
artwork as a product logo.

Discord may use padded variants under `assets/icons/discord/` so visually wide
or large marks remain balanced without distorting the official artwork.

## Payload safety

Shared presentation helpers sanitize credential-like text before delivery,
including bearer values, password/secret/token assignments, Discord webhook
credentials, and sensitive query-token forms.

Presentation must never turn a destination credential, Event API token, session
value, private webhook URL, or secret-file path into visible card content.

Microsoft Teams payload size is bounded before transport; over-budget messages
fail safely instead of being sent with unbounded content. Discord similarly
budgets optional facts/components to preserve the essential event context.

## Extending presentation

A new integration should:

1. normalize source-specific data in its parser;
2. reuse the shared Discord/Teams model/hierarchy;
3. add only source-specific optional facts/actions;
4. provide official packaged artwork;
5. preserve credential sanitization and payload budgets; and
6. add regression tests for missing values, status semantics, timestamps,
   artwork, and platform limits.

See [platform-outputs.md](platform-outputs.md) for destination transport rules
and [platform-routing.md](platform-routing.md) for route/delivery semantics.
