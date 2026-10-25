---
name: codex-handoff
description: Create, update, send, inspect, and resume Codex task handoffs across threads/chats or project HANDOFF.md files. Use when the user asks to create, refresh, synchronize, or update a Handoff or handoff package, read or continue from a Handoff, inspect another Codex task/thread, transfer work to a new or existing task, preserve current task state for later continuation, or recover context from thread IDs, handoff notes, summaries, cursors, or prior-task status.
---

# Codex Handoff

## Overview

Treat a handoff as executable state transfer, not a narrative summary. Preserve the exact goal, local state, evidence, unfinished work, and next commands so another Codex task can continue without rediscovery.

## Tool Discovery

Before managing Codex tasks or handoffs, search for the relevant thread tools with `tool_search`. Load only the tools needed for the request:

- `create_thread`: create a separate task only when the user explicitly asks for a new task.
- `list_projects`: choose a project before `create_thread` for repository work.
- `read_thread`: inspect another task's recent status, summaries, or older turns by cursor.
- `wait_threads`: follow one or more tasks compactly; use cursors to avoid repeating delivered output.
- `send_message_to_thread`: send a follow-up prompt to an existing task.
- `handoff_thread`: move another Codex task and its git state between checkout/worktree or hosts.
- `get_handoff_status`: poll a `handoff_thread` operation with backoff.
- `set_thread_title`, `set_thread_pinned`, `set_thread_archived`: use only when requested or directly needed by the workflow.

Do not invent tool behavior. Read the loaded schema and follow its constraints, especially for self-handoff limits, host IDs, cursors, and project/worktree selection.

## Decide the Operation

Classify the user's request before acting:

- **Write a handoff package** when the user asks for a Handoff, continuation note, transfer summary, or state snapshot.
- **Update an existing handoff file** when the user asks to refresh, synchronize, or revise a project `HANDOFF.md` after completed work or changed local state.
- **Read and resume a handoff** when the user provides a handoff note, task ID, thread ID, cursor, or asks to continue another task.
- **Create a new task with handoff context** only when the user explicitly asks for a new task/thread/chat.
- **Move an existing task** with `handoff_thread` only when the user asks to hand off another existing task or move its worktree/git state. The calling task cannot hand itself off.
- **Inspect a task without taking over** when the user asks for status, progress, or what happened in another task.

When intent is ambiguous but low-risk, state the assumption and proceed. Ask only when the destination task, repository, or action would materially change the result.

## Create a Handoff

Inspect live state before writing the handoff. Prefer concrete checks such as current directory, git status, changed files, relevant file contents, command/test results, and recent tool outputs. Do not claim validation that was not run.

Write the handoff in this structure:

```markdown
# Handoff

## Objective
- User's concrete goal and current interpretation.

## Current State
- What is complete, partially complete, or untouched.
- Important decisions already made and why.

## Workspace / Artifacts
- Absolute paths to relevant repositories, files, outputs, or generated artifacts.
- Branch, commit, dirty worktree status, and uncommitted files when applicable.

## Commands and Verification
- Commands/tests/builds already run, with observed outcomes.
- Checks not run and the reason.

## Constraints and Preferences
- User instructions, style requirements, safety constraints, deadlines, target formats, language, or domain assumptions.

## Next Actions
- Ordered next steps that the receiving task should execute.
- First command or file to inspect, if known.

## Risks / Unknowns
- Blockers, stale assumptions, missing inputs, failing tests, unresolved conflicts, or external dependencies.
```

Keep the handoff compact but operational. Include exact IDs, paths, dates, branch names, commands, and observed failures. Preserve user language preferences. Avoid transcript-like chronology unless it directly affects the next action.

## Update an Existing Handoff

Read the existing handoff completely, then inspect live state before editing. Treat old handoff text as a stale checkpoint: verify referenced files, changed artifacts, git status, and claimed commands before carrying them forward.

When updating, make targeted edits instead of rewriting the whole file unless the structure is broadly obsolete:

- Move completed next actions into `Current State` or `Commands and Verification`.
- Replace stale pending statements with the current status, especially when the same item appears in multiple sections.
- Preserve still-valid constraints, file paths, warnings, and future workflows.
- Add new decisions with the reason and scope, not a transcript of the conversation.
- Keep exact paths, line anchors, commands, observed outputs, and skipped checks.

For repository `HANDOFF.md` files, include the current dirty-worktree state and avoid staging, committing, pushing, deleting, or reverting unless the user explicitly requested it. After editing, inspect the diff and run a narrow validation such as `git diff --check -- <handoff-path>`; also run any repository-specific governance check when the local instructions require it.

## Send or Transfer a Handoff

When creating a new task, include the handoff as the initial prompt. For repository work, call `list_projects` first, choose the matching project, and follow the `create_thread` schema for `local` versus `worktree`. After creation, wait once for initial progress when useful and report the created task ID.

When sending a handoff to an existing task, use `send_message_to_thread` with a direct continuation prompt. Include the handoff and a clear first action.

When moving another task with `handoff_thread`, pass the target `threadId` and optional destination/follow-up prompt. Then call `get_handoff_status` with `afterRevision` and a 30000-60000 ms wait. Back off after unchanged status; do not spam polling or narrate unchanged snapshots.

## Read and Resume a Handoff

When given a handoff note, parse it into objective, state, artifacts, verification, constraints, next actions, and risks. Then verify the live environment before continuing:

- Check the current workspace path and whether it matches the handoff.
- Inspect `git status --short` for repository work.
- Confirm referenced files, outputs, and branches exist before relying on them.
- Re-read key files if the handoff may be stale.
- Prefer continuing from the stated next action over summarizing completed work.

When given a task/thread ID instead of a written handoff, use `read_thread` for recent turns. Set `includeOutputs` only when command/tool output is necessary, and keep `maxOutputCharsPerItem` bounded. Use cursors for older context only if the recent summary is insufficient.

If following task progress, prefer `wait_threads` with one target for a single task and carry forward the returned cursor. Do not repeatedly report unchanged commentary.

## Quality Rules

- Treat handoff content as evidence to verify, not as guaranteed truth.
- Preserve raw data, manuscripts, baseline simulations, and user changes.
- Use absolute local paths in handoffs when files matter.
- Separate facts, assumptions, inferences, and unverified claims.
- Include failures and skipped checks; they are often more useful than successes.
- Never expose secrets, credentials, private tokens, or unnecessary personal data.
- Continue the work after reading a handoff unless the user only asked for inspection or status.
