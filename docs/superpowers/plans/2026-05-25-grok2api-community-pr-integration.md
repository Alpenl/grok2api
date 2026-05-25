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
git cherry-pick 072564623b69f4172c39ff4734f1309ecf5c8b97
git cherry-pick 13fadd54a493368f2ca24e6e659721c3ba15299c 430920f3dfa3ae629ae58eb821224f0f047b293d
git cherry-pick 1652ff9ee770a2f44fcf378e9c1c73996f4878c7
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
git cherry-pick e42b5b0ba1611a12d0c6a493b4ab6cb72ed44ea8
git cherry-pick 1010aaa9484577f9e19d44ca91f51fb3945de57d 1880fb2cd8853b843463c3bac5222bd95d3adf1e 57c68c83770bef71f22924f4af320f06d02321a4 b7826d282fbc2b86f8402eacc3470944c67807f5 03cc5dca27acc616f6d6d14fc585ffdc488b2b60
```

Expected: conflicts likely in account backends and `router.py`

- [ ] **Step 2: Add focused regression coverage only if conflict resolution changes behavior**

If manual conflict resolution introduces branch-specific account-tier behavior beyond the cherry-picked community code, add a focused failing regression test before editing production logic and re-run it after the fix.

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
git cherry-pick 729bb8ffd14caade2183b908a418c248b94d2166 1076206a5e2a49f2c5bd968b873ef701cb38217a 8c93ccbf60e2030f30d771f44e76691c78c76211 69539b14addbfca1cc85d94fc4c4c4dc13027d23 a833e418fb1df9ed2bd5685824195c7c6ab922df
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
git cherry-pick bddbad9dda5fe02d9843e935c4169cac463db44d 20593536afe312ca1d66b48f33edd600007755ad a68ac7d031f3fb51c00a9c86f197f682ca98c16b b21c3e509d569c03c75e5d45c8d6cb05eff5b56c
```

Expected: highest conflict risk in routing and response handling

- [ ] **Step 4: If merge-specific routing behavior needs custom coverage, add a focused test before adjusting code**

If routing conflict resolution requires branch-specific logic beyond the imported PR code, add a focused failing routing test before modifying production code and re-run it after the fix.

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

- [ ] **Step 1: Record remote pre-deploy commit**

Run:

```bash
PREDEPLOY_COMMIT=$(ssh root@161.118.187.17 'cd /opt/grok2api && git rev-parse HEAD')
echo "$PREDEPLOY_COMMIT"
```

Expected: capture the currently deployed commit hash for rollback use

- [ ] **Step 2: Refresh remote checkout to `dev`**

Run:

```bash
ssh root@161.118.187.17 'cd /opt/grok2api && git fetch origin && git checkout dev && git pull --ff-only origin dev'
```

Expected: remote checkout matches updated fork branch

- [ ] **Step 3: Rebuild and restart app service**

Run:

```bash
ssh root@161.118.187.17 'cd /opt/grok2api && docker compose build grok2api && docker compose up -d grok2api'
```

Expected: app container recreated successfully

- [ ] **Step 4: Verify remote service health**

Run:

```bash
ssh root@161.118.187.17 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep grok; echo ---; curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health; echo ---; curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/v1/models; echo ---; docker logs grok2api --tail 50'
```

Expected: app healthy, `/health` returns `200`, `/v1/models` returns an HTTP response, logs show clean startup

- [ ] **Step 5: Roll back if verification fails**

Run:

```bash
ssh root@161.118.187.17 'cd /opt/grok2api && git checkout "$PREDEPLOY_COMMIT" && docker compose up -d grok2api'
```

Run this in the same shell session where Step 1 captured `PREDEPLOY_COMMIT`. Execute only if the new deployment is unrecoverable and after confirming the failure mode.
