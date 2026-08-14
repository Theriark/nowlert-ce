# Notification presentation contract

Nowlert v3.1.1 uses shared presentation rules so integrations render
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

Do not add the removed legacy `presentation` YAML section to a fresh v3.1.1
configuration.

## Microsoft Teams hierarchy

Every integration supplies normalized data to the shared Teams renderer:

1. Header: `device • event`, with device/status icons, severity-aware title
   color, and the integration image at the top right.
2. Context: `integration • state • source area`.
3. Message: one emphasized event body.
4. Metrics: Severity, Category, and Event time when available.
5. Details: optional icon-labelled integration-specific facts.
6. Optional integration-specific sections/actions.
7. `Theriark • Nowlert v<version>` footer.

The normalized model lives in `src/formatters/teams_common.py`. New Teams
formatters inherit the shared formatter/model and keep source parsing outside
the renderer.

Teams uses public HTTPS image URLs. The default asset root is the repository's
`main/assets/icons` path. Controlled preview/mirrored installations may use the
`NOWLERT_TEAMS_ICON_BASE_URL` compatibility override, which must be a valid
credential-free HTTPS URL.

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
