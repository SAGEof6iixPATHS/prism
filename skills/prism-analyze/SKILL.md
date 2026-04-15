---
description: Analyze Claude Code session health using PRISM. Use when asked to check token usage, audit CLAUDE.md, understand why sessions are failing, or list projects.
---

# prism-analyze

Analyze Claude Code session health using PRISM.

## When to use
When the user asks to analyze their Claude Code sessions, check token usage,
audit their CLAUDE.md, understand why sessions are failing, list their
projects, or see what PRISM can see.

## Before running

First check if PRISM is installed:
```bash
prism --version
```

If the command is not found, install it first:
```bash
pip install prism-cc
```

Then verify it installed correctly:
```bash
prism --version
```

Once confirmed installed, proceed with the analysis.

## Usage

Run the analysis:
```bash
prism analyze
```

If prism is not installed:
```bash
pip install prism-cc
prism analyze
```

For a specific project:
```bash
prism analyze --project <path>
```

For JSON output (useful for scripting):
```bash
prism analyze --json
```

For CLAUDE.md recommendations:
```bash
prism advise
```

List all projects PRISM can see:
```bash
prism projects
```

This prints each project name, session count, and last-active timestamp.
Use it when the user asks what projects PRISM has data for, or to confirm
that sessions are being recorded.

## What PRISM shows
- Health scores (A-F) across 5 dimensions per project
- Token efficiency: CLAUDE.md re-read costs, compaction frequency
- Tool health: retry loops, edit-revert cycles, consecutive failures
- Context hygiene: compaction loss events, mid-task boundaries
- CLAUDE.md adherence: whether your rules are actually being followed
- Session continuity: resume success rate, truncated sessions

## Output
PRISM prints a health report table and top issues per project.
Run `prism` (no args) to open the interactive TUI dashboard.
Run `prism dashboard` to open the HTML dashboard in your browser.
