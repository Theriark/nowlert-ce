# Nowlert CE technical use-case guides

These guides show complete, practical event flows using the current Nowlert CE
platform model. They are written for operators evaluating or deploying Nowlert
rather than for historical release compatibility.

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

## Guides

- [Illustrated infrastructure tutorials and screenshot index](infrastructure-tutorials.md)
- [Gmail email alerts: illustrated setup](gmail-email-alerts.md)
- [Microsoft 365 / Outlook email alerts: illustrated setup](microsoft-email-alerts.md)
- [Shared email rules and delivery validation](gmail-microsoft-email-alerts.md)
- [Portainer native Alerting to Nowlert and Discord](portainer-to-discord.md)
- [Home Assistant alerts to Nowlert and Discord](home-assistant-to-discord.md)
- [TrueNAS alerts to Nowlert and Discord](truenas-to-discord.md)
- [Collect supported source events before centralized filtering](centralized-event-coverage.md)
- [Route Xen Orchestra alerts through Nowlert CE to Discord](xen-orchestra-to-discord.md)
- [Send Xen Orchestra alerts to Microsoft Teams](xen-orchestra-to-teams.md)
- [Centralise homelab SMTP alerts without mailbox rules](centralise-homelab-smtp-alerts.md)
- [Route Dell iDRAC Redfish events through Nowlert CE](dell-idrac-redfish-routing.md)
- [Connect Supermicro, Dell iDRAC, and HPE iLO: illustrated setup and validation status](hardware-redfish-setup.md)
- [Configure the local HTTPS callback used by the iLO4 tutorial](ilo4-local-tls-listener.md)
- [Send Zabbix webhooks to Discord](zabbix-webhook-to-discord.md)

## Current platform assumptions

These guides are part of the v3.1.6 documentation candidate and use the current
v3.1.x platform model:

- integrations are built into the image;
- inputs are normalised as SMTP, HTTP, or Redfish;
- destinations and routes are managed through the WebUI and stored in the
  platform database;
- destination credentials remain write-only;
- dedicated integration routes are evaluated before fallback routes; and
- `config.yaml` is used for listener/bootstrap/security settings, not for
  recreating legacy WebUI-managed routing or destination YAML.

For authoritative platform behaviour, also see:

- [Integrations and inputs](../integrations-and-inputs.md)
- [Integration setup index](../integrations/README.md)
- [Platform routing](../platform-routing.md)
- [SMTP security](../smtp-security.md)
- [Current configuration model](../current-configuration-model.md)
