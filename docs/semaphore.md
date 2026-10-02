# Semaphore notifications to Nowlert

Semaphore task notifications report automation results, including Terraform,
Ansible and other task templates executed by Semaphore. This integration does
not poll Terraform state or run a monitoring agent.

## Configure Nowlert first

1. Upgrade to a development image containing this integration. Fresh accounts
   receive its built-in routes; existing accounts seeded by earlier images get
   the new routes on upgrade. Existing assignments and filtering are preserved.
2. Create or edit your destination and assign this application's built-in route.
   Enable the destination and route. Leave source severity/status restrictions
   empty initially so every notification emitted by the application can arrive.
3. For HTTP, issue a source-scoped token in Settings. Give it only this
   application's source and the required event rate. Use HTTPS for callbacks.
4. Configure the application's notification settings as described below.
5. Send its native test and check Nowlert Delivery history, source identity,
   destination result and the actual notification received. A local fixture test
   does not establish that your application is connected.
6. Apply noise suppression in Nowlert Filtering, using event/status and the
   application-specific fields. Keep the upstream notification triggers broad.

## Native task notifications over HTTP

Assign **Semaphore HTTP** and create a `semaphore`-scoped token. In Semaphore's
notification settings, use its **Slack** notification provider with this URL:

```text
https://nowlert.example/semaphore/events?token=YOUR_SEMAPHORE_TOKEN
```

Nowlert accepts Semaphore's built-in Slack-format message directly; a Slack
workspace is not required. Keep the default message template. Enable the
notification channel for each intended project and template/schedule. Do not
suppress successful or failed results if you want central filtering to decide.
Provider configuration/UI differs by Semaphore version; older installations use
server configuration plus the project's Allow alerts option. Newer versions
also provide project alerts and Send test message.

The receiver accepts the native `attachments` entries containing `Task:` and
`execution #..., status: ...`. It exposes template, actor, version, run ID,
status and severity to central filtering. Waiting/running/stopped states are
retained rather than silently treated as failures.

## SMTP alternative

Assign **Semaphore SMTP**. Point Semaphore's native email settings at the
Nowlert SMTP listener (normally port 8025), using the TLS/authentication policy
configured on that listener. Use `semaphore@nowlert.local` as the recipient, or
include Semaphore in the configured sender identity. Enable email alerts and
project alerts. Nowlert recognizes the stock Task ... with template ... has
failed message and reports the template/run ID as an automation failure.

**Semaphore's stock SMTP template reports failures only.** Use its Slack
notification provider for broader task-result coverage. Do not claim SMTP
success coverage. Custom message templates need to retain the native identifying
fields; arbitrary Slack messages are rejected.

Sources: [Semaphore alerts](https://semaphoreui.com/docs/user-guide/alerts),
[native Slack template](https://github.com/semaphoreui/semaphore/blob/develop/services/tasks/templates/slack.tmpl),
[native email template](https://github.com/semaphoreui/semaphore/blob/develop/services/tasks/templates/email.tmpl).
