# Grok2API Community PR Integration Design

## Goal

Integrate all currently open community pull requests from `chenyme/grok2api` into `Alpenl/grok2api`'s `dev` line, resolve cross-PR conflicts, verify the merged result with pragmatic regression checks, and deploy the updated service to the existing Oracle host at `161.118.187.17`.

## Context

As of 2026-05-25, `Alpenl/grok2api:dev` and upstream `chenyme/grok2api:main` both point at commit `64a71f1`. The open upstream PR set to integrate is:

- `#532` Codex CLI / Responses API tool compatibility
- `#542` `console.x.ai` routing for newer Grok model families
- `#545` secure asset URL fetching
- `#549` contributing/security docs
- `#550` admin token pagination/stats/model-pool filtering
- `#551` paid pool recovery on manual quota refresh
- `#555` lite account tier support

## Constraints

- The target branch is `dev` on the user's fork, not upstream.
- The running production deployment is Docker-based on the Oracle host and should remain recoverable.
- The base repository currently has no committed test suite and fails `uv run ruff check .` with pre-existing issues unrelated to this integration.
- Therefore validation must focus on:
  - new tests introduced by merged PRs,
  - targeted smoke checks for changed functionality,
  - successful local Docker build,
  - successful remote container replacement and health check.

## Integration Strategy

Use a dedicated integration branch `integration/community-prs-2026-05-25` created from `origin/dev`.

Apply community PRs in conflict-aware order:

1. `#549` docs only
2. `#545` security fix
3. `#551` paid pool refresh fix
4. `#555` lite tier support
5. `#550` admin token pagination/stats
6. `#532` Codex tool compatibility
7. `#542` `console.x.ai` routing and new-model enablement

This order minimizes conflicts by landing isolated changes first and deferring the heaviest routing/model changes until the repository already contains the prerequisite account-tier and admin-layer updates.

## Conflict Resolution Rules

### OpenAI routing and responses

Files:

- `app/products/openai/router.py`
- `app/products/openai/responses.py`
- `app/products/openai/chat.py`

Policy:

- Preserve `#542`'s model-routing behavior for newer Grok models.
- Re-apply `#532`'s Responses/Codex tool compatibility on top of that behavior.
- Keep request/response API compatibility higher priority than internal code shape.

### Account model and quota behavior

Files:

- `app/control/account/backends/local.py`
- `app/control/account/backends/redis.py`
- `app/control/account/backends/sql.py`
- `app/control/account/quota_defaults.py`
- `app/control/account/models.py`

Policy:

- Preserve `#555`'s explicit `lite` tier semantics.
- Layer `#551`'s paid-pool recovery fix on top of the new tier model.
- Keep admin query support from `#550` intact after conflict resolution.

### Web/admin changes

Files:

- `app/products/web/webui/chat.py`
- `app/products/web/admin/tokens.py`
- `app/statics/admin/account.html`

Policy:

- Maintain the `#550` admin pagination and filtering behavior.
- Preserve any `#542` web chat changes required for routing/model selection.

## Verification Design

Because full greenfield TDD is not possible against a branch with no existing tests and community PR code already authored externally, verification will use these layers:

1. Baseline evidence capture:
   - record current `ruff` failure set,
   - record that the base branch has no tests.
2. Test-first for any manual conflict-resolution logic we write ourselves, where a practical focused test can be added.
3. Execute PR-supplied tests after integration, especially:
   - `tests/test_codex_tools.py`
4. Run focused import/build checks:
   - `uv run pytest -q`
   - targeted API-level smoke tests if tests remain sparse.
5. Build Docker image locally.
6. Push `dev` to GitHub.
7. Update Oracle host checkout/image and restart.
8. Verify:
   - container health,
   - local `/health`,
   - local `/v1/models`,
   - recent logs,
   - new model exposure if available.

## Deployment Design

The remote host already runs:

- app container `grok2api`
- postgres container `grok2api-db`
- compose project in `/opt/grok2api`

Deployment approach:

1. Keep the current running image/container state as rollback baseline.
2. Update `/opt/grok2api` to the new `dev` code.
3. Rebuild with `docker compose build` or pull/build the updated app image in place.
4. Restart only the application container unless compose dependency changes require a wider restart.
5. Validate health and logs immediately.

## Rollback Plan

If any post-deploy check fails:

1. Inspect `docker compose logs grok2api --tail 100`
2. Roll back to the previous app image/container state
3. Restore previous checkout state if config or compose files changed
4. Re-run health checks on `127.0.0.1:8000/health`

## Success Criteria

- All 7 upstream open PRs are represented in the integration branch.
- Conflicts are resolved without dropping intended behavior.
- The integrated branch is pushed to `Alpenl/grok2api:dev`.
- The local Docker build succeeds.
- The production host is updated and the app container is healthy.
- `http://127.0.0.1:8000/health` returns `200` on the server after deployment.
