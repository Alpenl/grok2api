# Grok2API Community PR Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate upstream community PRs `#532`, `#542`, `#545`, `#549`, `#550`, `#551`, and `#555` into `Alpenl/grok2api:dev`, verify the merged result, and deploy it to the Oracle host.

**Architecture:** Work on an isolated integration branch from `origin/dev`, land PRs in conflict-aware order, add focused regression coverage only for custom merge logic, and validate pragmatically with new tests, Docker build, and remote health checks because the repository has no meaningful baseline test suite.

**Tech Stack:** Git, GitHub PR refs, Python 3.13, uv, FastAPI, Docker Compose, SSH

---

### Task 1: Capture baseline and planning artifacts

**Files:**
- Create: `docs/superpowers/specs/2026-05-25-grok2api-community-pr-integration-design.md`
- Create: `docs/superpowers/plans/2026-05-25-grok2api-community-pr-integration.md`

- [ ] **Step 1: Record baseline validation evidence**

Run: `uv run ruff check .`
Expected: fail with pre-existing upstream lint issues

- [ ] **Step 2: Record baseline test state**

Run: `uv run pytest -q`
Expected: `no tests ran`

- [ ] **Step 3: Commit planning artifacts**

```bash
git add docs/superpowers/specs/2026-05-25-grok2api-community-pr-integration-design.md \
        docs/superpowers/plans/2026-05-25-grok2api-community-pr-integration.md
git commit -m "docs: add community PR integration design and plan"
```

### Task 2: Land low-risk PRs without behavior conflicts

**Files:**
- Modify: `CONTRIBUTING.md`
- Modify: `app/dataplane/reverse/transport/asset_upload.py`
- Modify: `app/control/account/quota_defaults.py`
- Modify: `app/control/account/refresh.py`

- [ ] **Step 1: Cherry-pick docs and low-risk fixes**

Run:

```bash
git cherry-pick <PR549_COMMITS>
git cherry-pick <PR545_COMMITS>
git cherry-pick <PR551_COMMITS>
```

Expected: apply cleanly or with trivial conflict resolution

- [ ] **Step 2: Run focused regression checks**

Run:

```bash
uv run python -m compileall app
```

Expected: all touched modules compile

- [ ] **Step 3: Commit any manual conflict resolution**

```bash
git add -A
git commit -m "fix: resolve low-risk community PR conflicts"
```

Only if manual conflict resolution was required.

### Task 3: Integrate account-tier and admin-layer changes

**Files:**
- Modify: `app/control/account/backends/local.py`
- Modify: `app/control/account/backends/redis.py`
- Modify: `app/control/account/backends/sql.py`
- Modify: `app/control/account/models.py`
- Modify: `app/control/account/quota_defaults.py`
- Modify: `app/control/account/scheduler.py`
- Modify: `app/control/model/enums.py`
- Modify: `app/control/model/spec.py`
- Modify: `app/control/account/commands.py`
- Modify: `app/control/account/repository.py`
- Modify: `app/dataplane/account/__init__.py`
- Modify: `app/dataplane/shared/enums.py`
- Modify: `app/products/openai/router.py`
- Modify: `app/products/web/admin/tokens.py`
- Modify: `app/products/web/webui/chat.py`
- Modify: `app/statics/admin/account.html`

- [ ] **Step 1: Cherry-pick `#555` then `#550`**

Run:

```bash
git cherry-pick <PR555_COMMITS>
git cherry-pick <PR550_COMMITS>
```

Expected: conflicts likely in account backends and `router.py`

- [ ] **Step 2: Add focused regression coverage only if conflict resolution changes behavior**

Suggested target file:

```python
# tests/test_account_tiers_merge.py
def test_placeholder():
    assert True
```

If a real merge-specific branch is introduced, replace the placeholder with a concrete failing test before code changes.

- [ ] **Step 3: Verify imports and targeted behavior**

Run:

```bash
uv run python -m compileall app
```

Expected: compile succeeds after conflict resolution

- [ ] **Step 4: Commit manual resolutions**

```bash
git add -A
git commit -m "feat: integrate account tier and admin community changes"
```

Only if manual conflict resolution was required.

### Task 4: Integrate API compatibility and new-model routing

**Files:**
- Modify: `app/dataplane/reverse/protocol/tool_prompt.py`
- Create: `app/products/openai/_codex_tools.py`
- Modify: `app/products/openai/chat.py`
- Modify: `app/products/openai/responses.py`
- Modify: `app/products/openai/router.py`
- Modify: `app/products/anthropic/messages.py`
- Modify: `app/products/web/webui/chat.py`
- Modify: `app/control/account/invalid_credentials.py`
- Modify: `app/control/account/state_machine.py`
- Modify: `app/control/model/registry.py`
- Modify: `app/control/model/spec.py`
- Modify: `app/dataplane/reverse/planner.py`
- Create: `app/dataplane/reverse/protocol/xai_console.py`
- Modify: `app/dataplane/reverse/runtime/endpoint_table.py`
- Create: `tests/__init__.py`
- Create: `tests/test_codex_tools.py`

- [ ] **Step 1: Cherry-pick `#532`**

Run:

```bash
git cherry-pick <PR532_COMMITS>
```

Expected: may touch `responses.py` and `router.py`, but should be manageable before `#542`

- [ ] **Step 2: Run the new failing/passing regression test from PR `#532`**

Run:

```bash
uv run pytest -q tests/test_codex_tools.py
```

Expected: pass after `#532` is integrated

- [ ] **Step 3: Cherry-pick `#542`**

Run:

```bash
git cherry-pick <PR542_COMMITS>
```

Expected: highest conflict risk in routing and response handling

- [ ] **Step 4: If merge-specific routing behavior needs custom coverage, add a focused test before adjusting code**

Suggested target:

```python
# tests/test_console_xai_routing_merge.py
def test_placeholder():
    assert True
```

Replace with a real failing test if custom merge logic is necessary.

- [ ] **Step 5: Re-run focused test suite**

Run:

```bash
uv run pytest -q
uv run python -m compileall app
```

Expected: tests pass and app compiles

- [ ] **Step 6: Commit manual resolutions**

```bash
git add -A
git commit -m "feat: integrate routing and API compatibility community changes"
```

Only if manual conflict resolution was required.

### Task 5: Final local verification and push to dev

**Files:**
- Modify: whichever files changed during integration

- [ ] **Step 1: Inspect final diff**

Run:

```bash
git status --short
git log --oneline --decorate -n 20
```

Expected: only intended integration changes remain

- [ ] **Step 2: Build Docker image locally**

Run:

```bash
docker build -t grok2api:community-prs-2026-05-25 .
```

Expected: successful image build

- [ ] **Step 3: Push integrated branch to `dev`**

Run:

```bash
git push origin HEAD:dev
```

Expected: remote `dev` updated

### Task 6: Deploy updated dev branch to Oracle host

**Files:**
- Remote checkout: `/opt/grok2api`
- Remote compose: `/opt/grok2api/docker-compose.yml`

- [ ] **Step 1: Refresh remote checkout to `dev`**

Run:

```bash
ssh root@161.118.187.17 'cd /opt/grok2api && git fetch origin && git checkout dev && git pull --ff-only origin dev'
```

Expected: remote checkout matches updated fork branch

- [ ] **Step 2: Rebuild and restart app service**

Run:

```bash
ssh root@161.118.187.17 'cd /opt/grok2api && docker compose build grok2api && docker compose up -d grok2api'
```

Expected: app container recreated successfully

- [ ] **Step 3: Verify remote service health**

Run:

```bash
ssh root@161.118.187.17 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep grok; echo ---; curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health; echo ---; curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/v1/models; echo ---; docker logs grok2api --tail 50'
```

Expected: app healthy, `/health` returns `200`, `/v1/models` returns an HTTP response, logs show clean startup

- [ ] **Step 4: Roll back if verification fails**

Run:

```bash
ssh root@161.118.187.17 'cd /opt/grok2api && git checkout <known_good_commit> && docker compose up -d grok2api'
```

Use only if the new deployment is unrecoverable and after confirming the failure mode.
