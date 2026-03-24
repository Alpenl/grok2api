# Chat Refusal Token Marking Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mark the current token when upstream chat returns a refusal message while preserving the original response to the client.

**Architecture:** Add refusal detection in the chat processors, then persist refusal metadata on the active token through `TokenManager` without changing retry behavior, status, or returned payloads. Reuse existing token `tags` and `last_fail_reason` fields to avoid schema expansion.

**Tech Stack:** Python, asyncio, existing Grok chat processors, token manager persistence

---

### Task 1: Add refusal-tracking tests

**Files:**
- Modify: `tests/test_openai_usage.py`

- [ ] **Step 1: Write failing tests for collect and stream refusal tracking**
- [ ] **Step 2: Run targeted tests to verify failure**

### Task 2: Add token refusal marking support

**Files:**
- Modify: `app/services/token/manager.py`

- [ ] **Step 1: Add a token manager method that records refusal tag and reason without changing token status**
- [ ] **Step 2: Keep persistence on existing state-save path**

### Task 3: Detect refusals in chat processors

**Files:**
- Modify: `app/services/grok/services/chat.py`

- [ ] **Step 1: Add refusal detection helpers**
- [ ] **Step 2: Trigger refusal marking in non-stream collect flow**
- [ ] **Step 3: Trigger refusal marking in stream flow while preserving visible output**

### Task 4: Verify and ship on dev

**Files:**
- Modify: `tests/test_openai_usage.py`
- Modify: `app/services/grok/services/chat.py`
- Modify: `app/services/token/manager.py`

- [ ] **Step 1: Run targeted tests**
- [ ] **Step 2: Run related regression tests**
- [ ] **Step 3: Commit current workspace changes on `dev`**
- [ ] **Step 4: Push `dev` to `origin/dev`**
