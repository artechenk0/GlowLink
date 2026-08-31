---
name: documentation-editor
description: Draft, review, and revise every project text: documentation, README files, skills, UI and CLI copy, and messages. Use whenever a task creates or changes text; do not use for code-only changes.
---

# Project Text Editor

Use this skill for every text change in the repository: documentation, README files, skills,
UI labels and messages, CLI help and output, comments, changelog entries, and contribution
guidance. Read `docs/standards/writing.md` first; it is the shared writing policy for people and
agent environments.

Keep text accurate, concise, and appropriate for its reader. Treat code, tests, CLI help, and
verified hardware-test records as sources of truth. Do not invent device support, commands,
protocol details, or test results.

## Choose the request mode

- **Draft:** Inspect the relevant implementation and existing text, then add the smallest
  complete text that answers the reader's need.
- **Review:** Report factual inaccuracies, missing information, and readability suggestions;
  do not edit unless asked.
- **Revise:** Preserve correct project terminology and make the smallest change that improves
  accuracy, structure, examples, or clarity.

## Project conventions

- Put user-facing project documentation in `docs/`; keep README content focused on orientation,
  installation, and common workflows.
- Use Markdown headings in a logical hierarchy. Prefer short paragraphs, task-oriented steps,
  and fenced examples that can be copied unchanged. Keep UI and CLI text direct and actionable.
- Keep commands suitable for PowerShell and use the repository virtual environment from `app/`
  (`.venv\\Scripts\\python.exe`), not a global `python` command.
- When a change affects CLI behaviour, BLE/protocol behaviour, compatibility, or user workflow,
  update the corresponding documentation in the same change.
- Hardware claims require reproducible evidence. Record new manual device results under
  `docs/hardware-tests/` and summarize verified compatibility in
  `docs/device-compatibility.md`.

## Accuracy check before delivery

Verify file paths, command names, options, defaults, version claims, and UI or CLI behaviour
against the repository. State clearly when a statement is an assumption or still needs a
hardware run.
