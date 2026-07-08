# `.github` — Agent & Maintainer Customization

This folder configures how AI coding agents (GitHub Copilot / VS Code) and human
contributors work on **Doc Helper AI Agent**. It encodes the project's
conventions so changes stay consistent, deterministic, and safe.

## Contents

```
.github/
├── copilot-instructions.md     # Always-on project guidelines (build, architecture, safety)
├── AGENTS.md                   # This file — guide to the customization folder
├── CODEBASE_MAP.md             # FULL codebase reference: tree + every module + data flows
├── instructions/               # Focused, auto-attached rules (by file pattern or on-demand)
│   ├── codebase-map.instructions.md    # on-demand: points to CODEBASE_MAP.md
│   ├── python.instructions.md          # applyTo: **/*.py
│   ├── agent-workflow.instructions.md  # applyTo: src/.../agent/**
│   ├── tools.instructions.md           # applyTo: src/.../tools/**
│   ├── tests.instructions.md           # applyTo: tests/**
│   └── safety.instructions.md          # on-demand: safety/medical guardrails
├── prompts/                    # Reusable /slash-command task templates
│   ├── add-tool.prompt.md
│   ├── add-classification.prompt.md
│   ├── add-sample-doc.prompt.md
│   └── verify.prompt.md
└── tools/                      # Offline maintenance scripts (smoke test, quality gate)
    ├── smoke_test.py
    ├── check.py
    └── README.md
```

## Understand the whole project first

**[CODEBASE_MAP.md](CODEBASE_MAP.md)** is the single source of truth for how the
codebase is organised: the annotated directory tree, what every file does and the
symbols it exports, the request lifecycle (with diagrams), layering rules, and
change recipes ("where do I edit for X?"). Read it before navigating or extending
the project, and update it whenever you add/rename/remove modules or public
functions.

## How it works

- **`CODEBASE_MAP.md`** is the deep reference for the whole codebase; the
  `codebase-map.instructions.md` file surfaces it on-demand when a task involves
  understanding structure or locating functionality.
- **`copilot-instructions.md`** is loaded automatically for every request in this
  workspace — it carries the essentials (commands, layered architecture, mock-mode
  determinism, and the non-negotiable safety rules).
- **`instructions/*.instructions.md`** attach automatically when you edit files
  matching their `applyTo` glob (e.g. Python style for `**/*.py`), or on-demand via
  their `description` (e.g. the safety guardrails).
- **`prompts/*.prompt.md`** appear as `/`-commands in Copilot Chat for common
  maintenance tasks (add a tool, add a classification, add a doc, verify).
- **`tools/`** holds runnable scripts that validate the app offline.

## Golden rules for any change

1. The app must **run and pass tests offline without an API key** (`uv run pytest`).
2. Respect the one-way layer boundaries (`api → agent → tools → services → infrastructure`).
3. This is **not a medical tool** — never diagnose/prescribe; escalate risk to a
   human with `requires_human=true`.

See [copilot-instructions.md](copilot-instructions.md) for the full guidelines.
