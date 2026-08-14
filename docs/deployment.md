# Container deployment and release flow

Nowlert CE uses one source commit and one immutable image digest through its
release chain. Development builds the image once; Stage and Production
Reference promote that digest without rebuilding; release finalization tags the
same source commit; stable registry aliases copy the approved digest without
building from the tag.

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

v3.1.1 keeps schema 9, so upgrading from v3.1.0 does not require a database
migration. A matched backup is still required for safe rollback after state has
changed.

---

# Repository environment model

The release branches represent approved source state:

| Branch | Meaning |
|---|---|
| `development` | cumulative active work; CI builds/deploys the Development candidate |
| `stage` | exact source commit approved by the Stage promotion gate |
| `main` | exact Stage-approved source after explicit fast-forward; required for Production Reference/release |

The desired invariant before Production Reference is:

```text
development SHA == stage SHA == main SHA == image source SHA
```

The runtime image is additionally pinned by immutable digest.

## Development

A push to `development` runs CI. After the test job passes, the Development
image workflow builds/publishes the candidate and deploys that exact digest to
Development.

Record from the successful Development run:

```text
SOURCE_COMMIT=<40-char development SHA>
FINAL_IMAGE=ghcr.io/theriark/nowlert-ce@sha256:<digest>
DEVELOPMENT_RUN_ID=<run id>
```

Do not replace the immutable digest with a mutable tag for later promotions.

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
6. advances the `stage` branch to the approved source SHA.

No rebuild is performed.

Example CLI:

```bash
gh workflow run promote-stage.yml \
  --repo Theriark/nowlert-ce \
  --ref development \
  -f ce_image="$FINAL_IMAGE" \
  -f source_commit="$SOURCE_COMMIT" \
  -f change_reference="v3.1.1"
```

After success, record:

```text
STAGE_PROMOTION_RUN_ID=<successful Promote CE to Stage run id>
```

## Fast-forward `main`

Production Reference is intentionally blocked until `main` and `stage` point to
the same approved source commit.

Verify Stage is strictly ahead/identical and fast-forward only:

```bash
SOURCE_COMMIT="$(gh api \
  repos/Theriark/nowlert-ce/git/ref/heads/stage \
  --jq '.object.sha')"

MAIN_SHA="$(gh api \
  repos/Theriark/nowlert-ce/git/ref/heads/main \
  --jq '.object.sha')"

gh api \
  "repos/Theriark/nowlert-ce/compare/${MAIN_SHA}...${SOURCE_COMMIT}" \
  --jq '{status,ahead_by,behind_by}'
```

Only when the compare result is a fast-forward-safe state, move `main` without
force:

```bash
gh api --method PATCH \
  repos/Theriark/nowlert-ce/git/refs/heads/main \
  -f sha="$SOURCE_COMMIT" \
  -F force=false
```

Re-read both refs and require equality before continuing.

## Production Reference

Production Reference must be dispatched from `main`.

Inputs:

- `ce_image` — Stage-approved immutable image;
- `source_commit` — source SHA; and
- `stage_promotion_run` — successful Stage promotion run ID or URL.

The workflow requires:

```text
source_commit == main == stage
```

It also verifies the exact image is currently approved in Stage, verifies the
Stage desired-state ledger/evidence, reruns the full network-isolated gate,
deploys the same digest to Production Reference, runs a passive live smoke, and
records the Production Reference desired state.

Example CLI:

```bash
gh workflow run promote-production-reference.yml \
  --repo Theriark/nowlert-ce \
  --ref main \
  -f ce_image="$FINAL_IMAGE" \
  -f source_commit="$SOURCE_COMMIT" \
  -f stage_promotion_run="$STAGE_PROMOTION_RUN_ID"
```

Record the successful run ID:

```text
PRODUCTION_REFERENCE_RUN_ID=<run id>
```

## Release finalization

Release finalization runs from `main` and creates the annotated version tag and
GitHub Release on that exact commit. It does not deploy or rebuild the image.

Inputs include the source commit, final immutable image, Development/Stage/
Production Reference evidence run IDs, and human-readable release notes.

Example for v3.1.1:

```bash
gh workflow run finalize-release.yml \
  --repo Theriark/nowlert-ce \
  --ref main \
  -f version="v3.1.1" \
  -f final_image="$FINAL_IMAGE" \
  -f source_commit="$SOURCE_COMMIT" \
  -f development_run_id="$DEVELOPMENT_RUN_ID" \
  -f stage_promotion_run_id="$STAGE_PROMOTION_RUN_ID" \
  -f production_reference_run_id="$PRODUCTION_REFERENCE_RUN_ID" \
  -f release_notes="Nowlert CE v3.1.1 QA and immutable promotion hardening"
```

The workflow refuses an existing tag/release, verifies current `main`, verifies
the live Production Reference digest, validates promotion evidence, writes the
release ledger record, creates the annotated tag/GitHub Release, and uploads
release evidence.

## Stable production image aliases

After the release tag exists, run **Docker Release Aliases** from `main`:

```bash
gh workflow run docker-release.yml \
  --repo Theriark/nowlert-ce \
  --ref main \
  -f tag="v3.1.1" \
  -f final_image="$FINAL_IMAGE"
```

This workflow uses registry-copy tooling to publish:

```text
ghcr.io/theriark/nowlert-ce:3.1.1
ghcr.io/theriark/nowlert-ce:latest
docker.io/theriark/nowlert-ce:3.1.1
docker.io/theriark/nowlert-ce:latest
```

All aliases must resolve to the approved Production Reference digest. **No
image rebuild is performed from the release tag.**

For Community Edition this stable registry publication is the production
release boundary. There is no additional CE Dokploy `Production` deployment
workflow after Production Reference; operators consume the released stable
image from GHCR/Docker Hub.

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

If Stage or Production Reference fails, stop the release. Do not move forward
with the tag or stable aliases. Promotion workflows contain bounded rollback
handling for failed live gates where a previous image is available.

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
- the Development/Stage/Production Reference source SHA and immutable digest.
