# GitHub Actions notifications to Nowlert

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

Assign **GitHub Actions HTTP** and issue a `github_actions`-scoped token. Open
**Repository → Settings → Webhooks → Add webhook** and configure:

- Payload URL: `https://nowlert.example/github/actions?token=YOUR_GITHUB_ACTIONS_TOKEN`
- Content type: `application/json`
- Secret: **the same scoped token** used in that URL.
- SSL verification: enabled.
- Events: select **Workflow runs** and **Workflow jobs** only.
- Active: enabled.

The token authenticates the source scope; GitHub's `X-Hub-Signature-256` is also
verified against the exact request bytes. Missing/incorrect signatures return
401. Do not leave Secret blank. Nowlert acknowledges and records the native
registration ping as a test. Check GitHub Recent Deliveries for HTTP 204, then
run a harmless workflow and check Nowlert's actual destination delivery.

**GitHub must be able to reach the HTTPS callback.** A LAN-only address cannot
receive GitHub-hosted repository webhooks; expose the authenticated endpoint
through your existing HTTPS ingress before configuring this application.

Both workflow and job notifications retain repository, workflow/job name,
branch, commit, actor, run/job ID, action and conclusion. Failures, timeouts,
action-required and startup failures map to error; successes map to success.
Queued/in-progress/cancelled/skipped/neutral states remain available for central
filtering. Selecting both webhook types intentionally generates run and job
notifications; filter by event type if one destination needs only run summaries.
This endpoint rejects unrelated repository-event payloads.

Source: [GitHub webhook events](https://docs.github.com/en/webhooks/webhook-events-and-payloads),
[signature validation](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).
