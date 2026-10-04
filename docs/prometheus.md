# Prometheus Alertmanager

Nowlert CE receives Prometheus alerts through Alertmanager's generic webhook
receiver. The integration source is `prometheus`; the native endpoint is:

`POST /prometheus/alerts`

Alertmanager groups remain one Nowlert event and continue through the normal
Nowlert filtering and routing pipeline.

## Authentication

Issue a Nowlert application token scoped to `prometheus`. Configure
Alertmanager's `http_config.authorization` with type `Bearer` and a private
`credentials_file`. Keep `send_resolved: true`. Do not put credentials in the
webhook URL or commit the token file.

The [native setup tutorial](guides/prometheus-to-nowlert.md) includes the
configuration and verified firing/recovery delivery records.

## Normalization

- `resolved` becomes a successful/resolved Nowlert event.
- Critical, error, fatal, and emergency firing severities become failures.
- Warning firing severity becomes a warning.
- Info, information, and notice firing severities become informational.
- Missing or unrecognized firing severity remains a warning rather than being
  promoted to critical.

Severity, instance, service, job, namespace, pod, and node are optional labels.
Missing optional labels therefore do not invalidate an otherwise valid
Alertmanager version 4 webhook.

Grouped Alertmanager notifications produce one Nowlert event with member
details retained in metadata. Classic and Modern cards expose a compact group
summary, target context, timing, and useful Alertmanager, Prometheus, and
runbook links when they are supplied.
