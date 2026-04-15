---
description: Generate the PRISM HTML dashboard. Use when asked to show a dashboard, generate a health report, or visualize session data.
---

# prism-dashboard

Generate a self-contained HTML dashboard of all project health scores.

## When to use
When the user asks to see a dashboard, generate a health report,
visualize their session data, or open the PRISM dashboard.

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

Once confirmed installed, proceed with the dashboard command.

## Usage

Generate the dashboard without opening a browser:
```bash
prism dashboard --no-open
```

The dashboard is written to `~/.claude/prism/dashboard.html`. Tell the
user the exact path so they can open it in their browser.

On most systems this is:
- macOS/Linux: `~/.claude/prism/dashboard.html`
- Windows: `C:\Users\<username>\.claude\prism\dashboard.html`

## What the dashboard shows
- Fleet-level health grade across all projects
- One card per project with overall grade and 5 dimension scores
- Click any project card to expand and see detailed issues
- Top issues list per project
- Advisor recommendations per project
- Grade distribution chart across all projects
- Most common issues across the fleet

## Notes
- The HTML file is fully self-contained. No server required. It works
  as a file:// URL in any browser.
- The dashboard regenerates every time `prism analyze` or
  `prism dashboard` runs. Reload the browser page after a new analysis.
- No data leaves the machine. The dashboard reads from local session
  files only.
