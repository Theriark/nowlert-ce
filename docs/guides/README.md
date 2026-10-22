# Nowlert CE technical use-case guides

These guides show complete, practical event flows using the current Nowlert CE
platform model. They are written for operators evaluating or deploying Nowlert
rather than for historical release compatibility.

Every packaged screenshot has a row in the
[screenshot privacy review](screenshot-privacy.md), which records when it was
last inspected; captures that still showed private account or deployment
details were withdrawn and replaced with written checks. Addresses and site
names in the examples and validation records are anonymized (validation records
use RFC 5737 documentation addresses); substitute your own values.

## Native application notification setup

- [Shared Nowlert route, token and delivery setup](application-notification-setup.md)
- [Checkmk native notifications](checkmk-to-nowlert.md)
- [Semaphore native task results](semaphore-to-nowlert.md)
- [Sonarr](sonarr-to-nowlert.md)
- [Radarr](radarr-to-nowlert.md)
- [Metabase](metabase-to-nowlert.md)
- [GitHub Actions: reference setup, local configuration deferred](../github-actions.md)

These integrations include automated receiver tests. The guides describe native
application tests; live delivery is verified separately when configuring each
installation.

## Email Alerts (mailbox connections)

- [Gmail email alerts: illustrated setup](gmail-email-alerts.md)
- [Microsoft 365 / Outlook email alerts: illustrated setup](microsoft-email-alerts.md)
- [Shared email rules and delivery validation](gmail-microsoft-email-alerts.md)

## Monitoring and infrastructure guides

- [Illustrated infrastructure tutorials and screenshot index](infrastructure-tutorials.md)
- [Grafana Alerting to Nowlert CE](grafana-to-nowlert.md)
- [Prometheus through Alertmanager to Nowlert CE](prometheus-to-nowlert.md)
- [Send Zabbix webhooks to Discord](zabbix-webhook-to-discord.md)
- [Portainer native Alerting to Nowlert and Discord](portainer-to-discord.md)
- [Home Assistant alerts to Nowlert and Discord](home-assistant-to-discord.md)
- [TrueNAS alerts to Nowlert and Discord](truenas-to-discord.md)
- [UniFi Network, Protect and Drive to Discord](unifi-to-discord.md)
- [Collect supported source events before centralized filtering](centralized-event-coverage.md)
- [Route Xen Orchestra alerts through Nowlert CE to Discord](xen-orchestra-to-discord.md)
- [Send Xen Orchestra alerts to Microsoft Teams](xen-orchestra-to-teams.md)
- [Centralise homelab SMTP alerts without mailbox rules](centralise-homelab-smtp-alerts.md)
- [Route Dell iDRAC Redfish events through Nowlert CE](dell-idrac-redfish-routing.md)
- [Connect Supermicro, Dell iDRAC, and HPE iLO: illustrated setup and validation status](hardware-redfish-setup.md)
- [Configure the local HTTPS callback used by the iLO4 tutorial](ilo4-local-tls-listener.md)

## Validation and lifecycle references

- [Controlled integration delivery validation](controlled-integration-validation.md)
- [Problems, recovery and successful operations: notification lifecycle](notification-lifecycle.md)

## Current platform assumptions

These guides describe the current development build that follows the v3.1.6
release (database schema 18) and use the current v3.1.x platform model:

- integrations are built into the image;
- inputs are normalised as SMTP, HTTP, or Redfish, plus Email Alerts mailbox
  connections;
- destinations and routes are managed through the WebUI and stored in the
  platform database;
- destination credentials remain write-only;
- dedicated integration routes are evaluated before fallback routes; and
- `config.yaml` is used for listener/bootstrap/security settings, not for
  recreating legacy WebUI-managed routing or destination YAML.

Validation dates quoted in the guides are historical observations made on the
build available at the time; they are not acceptance evidence for a release.

For authoritative platform behaviour, also see:

- [Integrations and inputs](../integrations-and-inputs.md)
- [Integration setup index](../integrations/README.md)
- [Platform routing](../platform-routing.md)
- [SMTP security](../smtp-security.md)
- [Current configuration model](../current-configuration-model.md)
- [Development after v3.1.6](../releases/post-v3.1.6-development.md)
