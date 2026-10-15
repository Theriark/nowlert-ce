# Container deployment and release flow

Nowlert CE uses one source commit and one immutable image digest through its
release chain. Development builds the image once; Stage is the final runtime
acceptance gate; Finalize CE Release validates the Stage-approved candidate,
fast-forwards `main`, publishes stable GHCR/Docker Hub aliases, and creates the
annotated tag, GitHub Release, and release evidence. No image rebuild occurs
during promotion or finalization.

The release chain is:

```text
Development -> Stage -> Finalize CE Release
                              |-> main
                              `-> stable aliases + tag + GitHub Release
```

Stage promotion never updates `main`. Finalize CE Release owns the only
Stage -> `main` promotion.

## Local development checkout

Create private configuration outside Git-tracked files:

```bash
cp config/config.example.yaml config/config.yaml
nano config/config.yaml
```

Build and start the local development Compose service:

```bash
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml ps
docker logs --tail 100 nowlert-ce-dev
```

The development Compose definition builds the checked-out source and uses the
development host ports documented in that file.
Set `NOWLERT_UID` and `NOWLERT_GID` in `.env` to the checkout owner's numeric
identity when it differs from the image default `1000:1000`. The development
bind mount hides the image's pre-created writable directories; create `logs`,
`state`, and `external-backups` as that owner before starting.

## Production host preparation

```bash
cp .env.example .env
cp config/config.example.yaml config/config.yaml
mkdir -p logs/emails secrets state external-backups
chmod 600 .env config/config.yaml
chmod 700 logs logs/emails secrets state external-backups
id -u
id -g
```

Set `NOWLERT_UID` and `NOWLERT_GID` in `.env` to the identity that owns the
mounted directories.

Validate and start the production Compose definition:

```bash
docker compose -f compose.production.yaml config
docker compose -f compose.production.yaml pull
docker compose -f compose.production.yaml up -d
docker compose -f compose.production.yaml ps
docker logs --tail 100 nowlert-ce
```

The base production definition runs non-root, drops Linux capabilities,
prevents privilege escalation, uses a read-only root filesystem, and persists
only the explicitly mounted configuration/state/log/backup paths.

Both images also default to UID/GID `1000:1000` when started without Compose.
Fresh Docker named volumes inherit the image's private, owned `config`, `logs`,
`state`, and `external-backups` directories. Bind mounts retain host ownership,
and existing volumes are never recursively changed at startup. Before upgrading
an installation previously run as root, stop Nowlert and take the matched backup
described below. Set `.env` to the intended runtime UID/GID, then repair only
the configured Nowlert paths on the host, for example for default paths and UID
1000 (substitute the actual paths and identity):

```bash
sudo find ./config ./logs ./state ./secrets -xdev \
  -path './state/mounts/*' -prune -o -exec chown --no-dereference 1000:1000 {} +
```

Do not recursively change ownership of a shared backup mount. Grant the runtime
identity access to its dedicated backup directory using the host filesystem or
NFS/SMB server permissions. Keep secret files private and readable by the
runtime identity, including TLS keys and OAuth credentials. Docker-mounted
secrets remain read-only in the container. Changing ownership back to root is
not necessary for rollback; retain the matched data backup and image digest.

The image healthcheck calls `http://127.0.0.1:8080/api/health` every 30 seconds
with a three-second request timeout. Deployments that intentionally change the
HTTP listener, bind address, or disable the API must override the healthcheck
in their deployment definition to match their configuration.

### Host-mounted NAS backups

Mount NFS/SMB on the Docker host, then bind the dedicated NAS backup directory
into Nowlert. In **Backups**, select **Host-mounted NFS** or **Host-mounted SMB**
and enter its path inside the container. Nowlert checks the actual filesystem
type before writing; an ordinary local directory is not a connected NAS target.
Scheduling, connection tests, external snapshot browsing and restore remain in
Nowlert. NAS credentials and mount options belong on the host, never in the app.

For a single NAS share, set `NOWLERT_EXTERNAL_BACKUP_DIR` to its mounted host
directory and use `/nowlert/external-backups` in the WebUI. The compatibility
filename `compose.managed-backups.yaml` now binds this directory without root or
extra capabilities and refuses to create a missing host directory:

```bash
docker compose -f compose.production.yaml -f compose.managed-backups.yaml up -d
```

Use the host's normal persistent mount configuration with `nosuid,nodev,noexec`
and access restricted to the Nowlert runtime UID/GID. Keep SMB credential files
root-owned, mode `0600`, and reference them from the host mount configuration.
Bind mounts must be configured on every eligible Swarm node; pin a service to
the prepared node until those mounts are provisioned elsewhere.

To migrate existing WebUI-managed targets without losing schedules or archives:

1. Stop backup jobs and take a matched state/config/secret backup.
2. Record each target ID, current container path and share subdirectory. Mount
   the same share on the host; keep all existing archive files in place.
3. Bind that host share to the target's existing container mount path. For SMB,
   retain the existing path-inside-share metadata so archives remain discoverable.
   Keeping the target ID and path also preserves schedules and restore references.
4. Repair only local application volume ownership as described above. Grant the
   NAS directory access for the runtime identity through host/server permissions;
   do not recursively chown the share.
5. Remove runtime root-user and added-capability overrides, deploy the non-root
   image, then test each target, create a backup, browse old snapshots, and restore
   a disposable snapshot. Verify a disconnected mount reports an error.

The app retains legacy target metadata for migration but never uses old NAS
passwords to mount anything. Legacy `managed_mounts: true` is normalized to false.
Removing a target does not unmount or delete its host share or existing archives.

### Email Alerts OAuth applications

Nowlert CE uses a per-installation OAuth model. Each self-hosted operator
registers its own Google and/or Microsoft application for its own Nowlert URL.
Theriark does not ship a shared OAuth client secret in source code or in the
container image.

Mailbox users never provide OAuth application credentials. The operator
configures the application once and mounts the client secret into the
container's secret boundary.

Configure public application values in `.env`:

```dotenv
NOWLERT_EMAIL_GMAIL_CLIENT_ID=<your-google-client-id>
NOWLERT_EMAIL_GMAIL_CLIENT_SECRET_FILE=/run/secrets/nowlert_email_gmail_client_secret
NOWLERT_EMAIL_MICROSOFT_CLIENT_ID=<your-entra-client-id>
NOWLERT_EMAIL_MICROSOFT_TENANT_ID=<your-directory-tenant-id>
NOWLERT_EMAIL_MICROSOFT_CLIENT_SECRET_FILE=/run/secrets/nowlert_email_microsoft_client_secret
```

Store only the secret values in the host secret directory:

```text
./secrets/nowlert_email_gmail_client_secret
./secrets/nowlert_email_microsoft_client_secret
```

The production Compose definition already mounts `NOWLERT_SECRETS_DIR`
read-only at `/run/secrets`. Docker Swarm/Portainer operators may instead
attach Docker secrets using the same in-container filenames.

The application resolves each client secret in this order:

1. the explicit `NOWLERT_EMAIL_*_CLIENT_SECRET_FILE` path;
2. the conventional `/run/secrets/nowlert_email_*_client_secret` file; then
3. the legacy `NOWLERT_EMAIL_*_CLIENT_SECRET` environment variable.

The environment-variable secret form remains supported for upgrades, but it is
not the recommended deployment model because environment values are easier to
expose through container inspection and diagnostics.

By default the OAuth redirect URI is derived from `webui.public_url` as
`<public_url>/ui/`. The exact same URI must be registered in the operator's
Google OAuth or Microsoft Entra application. It can be overridden for both
providers with `NOWLERT_EMAIL_OAUTH_REDIRECT_URI`, or independently with
`NOWLERT_EMAIL_GMAIL_REDIRECT_URI` and
`NOWLERT_EMAIL_MICROSOFT_REDIRECT_URI`.

Example for a self-hosted instance at `https://nowlert.example.com`:

```text
Authorized redirect URI:
https://nowlert.example.com/ui/
```

The instance-level client secret is never copied into mailbox records. Mailbox
records retain only owner-scoped OAuth state/access/refresh tokens. Existing
mailboxes created before this model remain readable for compatibility.

## Portainer stacks

Use absolute host paths in `.env`, for example:

```dotenv
NOWLERT_CONFIG_DIR=/docker/nowlert-ce/config
NOWLERT_LOG_DIR=/docker/nowlert-ce/logs
NOWLERT_SECRETS_DIR=/docker/nowlert-ce/secrets
NOWLERT_STATE_DIR=/docker/nowlert-ce/state
NOWLERT_EXTERNAL_BACKUP_DIR=/mnt/nowlert-backups
```

Pin a versioned image for production rather than relying only on `latest`.

## Persistent recovery boundary

Before an upgrade, keep a matched backup of:

- `config`;
- `state`;
- external `secrets`, when used;
- the deployment definition; and
- the currently running image reference/digest.

Current development uses database schema **17** and migrates supported older
state transactionally. A matched backup is required for safe rollback after
state has changed; do not start an older image against a newer live database.

---

# Repository environment model

The release branches represent approved source state:

| Branch | Meaning |
|---|---|
| `development` | cumulative active work; CI builds/deploys the Development candidate |
| `stage` | exact source commit approved by the final runtime acceptance gate |
| `main` | exact source of the last successfully finalized public release |

Before release finalization, the required invariant is:

```text
development SHA == stage SHA == image source SHA
```

`main` may intentionally lag behind Stage until Finalize CE Release succeeds.
After finalization, `main` equals the released Stage-approved source commit.
The runtime image is additionally pinned by immutable digest.

## Development

A push to `development` runs Continuous Integration. After the CI test/build job
passes, the same Continuous Integration workflow directly builds and publishes
the Development candidate and deploys the resulting immutable digest to CE
Development. There is no standalone Development Image workflow.

Continuous Integration does not run for ordinary pushes to `main`; `main` is a
release result, not another test environment.

Record from the successful development Continuous Integration run:

```text
SOURCE_COMMIT=<40-char development SHA>
FINAL_IMAGE=ghcr.io/theriark/nowlert-ce@sha256:<digest>
DEVELOPMENT_RUN_ID=<successful development Continuous Integration run id>
```

Do not replace the immutable digest with a mutable tag for later promotions.

CE Development receives Datadog unified service identity and Runtime SCA during
the same Dokploy deployment:

```text
DD_SERVICE=nowlert-ce
DD_ENV=development
DD_VERSION=<40-char development SHA>
NOWLERT_DDTRACE_ENABLED=true
DD_APPSEC_SCA_ENABLED=true
DD_IAST_ENABLED=true
DD_AGENT_HOST=datadog-agent
DD_TRACE_AGENT_PORT=8126
```

The production image ships the pinned Datadog Python tracer, but `start.sh`
wraps Nowlert with `ddtrace-run` only when `NOWLERT_DDTRACE_ENABLED=true`.
Continuous Integration sets that activation flag only for CE Development, so
the same image keeps the normal `python3 main.py` startup unless another
environment explicitly opts in. Runtime SCA and Python IAST are both enabled
for CE Development; Stage and public release environments remain opted out.

The deployment helper preserves unrelated Dokploy environment variables and
verifies the Datadog identity, Runtime SCA, IAST, and Agent transport settings
after the deployment is healthy. CE Development explicitly connects to the dedicated Datadog Agent
through the private `dokploy-network` service alias `datadog-agent` on trace
port `8126`; the Agent does not publish that port on the host. Stage and public
release environments are not opted into this Development-only runtime-security
transport contract.

## Stage

Stage promotion is manually dispatched from `development` with:

- `ce_image` — the exact Development immutable image;
- `source_commit` — the exact source SHA that built it; and
- `change_reference` — issue/release reference.

The workflow:

1. requires the source commit to equal current `development`;
2. runs the full test gate in a network-isolated namespace;
3. deploys the exact digest to Stage;
4. runs a passive notification-silent live smoke;
5. records desired state in the release ledger; and
6. advances only the `stage` branch to the approved source SHA using a guarded
   fast-forward-only ref update with propagation-safe verification.

Stage promotion never reads, advances, or otherwise modifies `main`. No rebuild
is performed. A successful Stage promotion is the final runtime acceptance
decision for the candidate.

Example CLI:

```bash
gh workflow run promote-stage.yml \
  --repo Theriark/nowlert-ce \
  --ref development \
  -f ce_image="$FINAL_IMAGE" \
  -f source_commit="$SOURCE_COMMIT" \
  -f change_reference="v3.1.6"
```

After success, record:

```text
STAGE_PROMOTION_RUN_ID=<successful Promote CE to Stage run id>
```

At this point stop. `main` must still represent the previous finalized release.
Do not fast-forward `main` manually.

## Release finalization

Finalize CE Release is manually dispatched from the Stage-approved branch and
completes the public CE release. It does not deploy or rebuild the application.
The finalizer requires `source_commit == stage`, proves current `main` can
fast-forward to that source without force, verifies the requested tag matches
`src/version.py`, requires the matching release notes and QA checklist, verifies
the immutable image is the Stage-approved runtime image, and validates the
successful Development Continuous Integration and Stage promotion evidence.

After all Stage/evidence checks pass, the finalizer advances `main` to the exact
Stage-approved source with `force=false`, waits for ref propagation, and verifies
the result. Only Finalize CE Release performs this Stage -> `main` promotion.
Because normal CI is not triggered by pushes to `main`, this does not start a
second redundant Continuous Integration run.

Inputs include the source commit, final immutable image, development Continuous
Integration run ID, Stage promotion run ID, and human-readable release notes.

Example for v3.1.6:

```bash
gh workflow run finalize-release.yml \
  --repo Theriark/nowlert-ce \
  --ref stage \
  -f version="v3.1.6" \
  -f final_image="$FINAL_IMAGE" \
  -f source_commit="$SOURCE_COMMIT" \
  -f development_run_id="$DEVELOPMENT_RUN_ID" \
  -f stage_promotion_run_id="$STAGE_PROMOTION_RUN_ID" \
  -f release_notes="Nowlert CE v3.1.6 release automation consolidation"
```

The workflow refuses an existing tag/release, verifies current Stage matches the
requested source, verifies the live Stage digest and Stage ledger, validates the
promotion evidence, and verifies `main` is fast-forward-safe. It then advances
`main` and publishes/verifies all four stable aliases from the already-approved
immutable digest:

```text
ghcr.io/theriark/nowlert-ce:3.1.6
ghcr.io/theriark/nowlert-ce:latest
docker.io/theriark/nowlert-ce:3.1.6
docker.io/theriark/nowlert-ce:latest
```

Every alias must resolve to the approved Stage digest. After registry
verification, the workflow creates the annotated tag and GitHub Release, writes
the release ledger record, and uploads the release evidence. There is **no image
rebuild** and no second Docker-alias workflow to run.

For Community Edition this stable registry publication is the production
release boundary. There is no additional CE Dokploy `Production` deployment
workflow; operators consume the released stable image from GHCR/Docker Hub.

## Watching workflow runs from CLI

List recent runs:

```bash
gh run list --repo Theriark/nowlert-ce --limit 20
```

Watch a known run and return non-zero on failure:

```bash
gh run watch "$RUN_ID" \
  --repo Theriark/nowlert-ce \
  --exit-status
```

Inspect run summary/jobs:

```bash
gh run view "$RUN_ID" --repo Theriark/nowlert-ce
gh run view "$RUN_ID" --repo Theriark/nowlert-ce --log-failed
```

## Rollback

### Before stable publication

If Stage fails, stop the release. Do not move `main` and do not run Finalize CE
Release. The Stage promotion workflow contains bounded rollback handling for
failed live gates where a previous image is available.

If Stage passes but release finalization has not started, `main` remains on the
previous finalized release by design.

### After stable publication

A source rollback and a state rollback are separate decisions:

1. identify the last known-good version and digest;
2. determine whether private state changed incompatibly;
3. if required, restore the matched pre-upgrade state/config/secret backup;
4. pin the known-good version/digest; and
5. verify health/login/routing/delivery before restoring traffic.

Never point an older image at a database schema it cannot open.

## Documentation/release consistency

Before finalization, verify all of the following describe the same candidate:

- `src/version.py`;
- `.env.example`;
- `compose.production.yaml`;
- `README.md`;
- `DOCKERHUB_README.md`;
- `CHANGELOG.md`;
- current release notes/QA checklist;
- screenshots; and
- the Development/Stage source SHA and immutable digest.

After finalization, verify `main` equals that exact released source SHA.
