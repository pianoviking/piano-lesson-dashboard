# Project rules

## Tool use
- Use OpenCode's actual built-in tools. Never invent tool names or APIs.
- Use the built-in shell tool for terminal commands. Do not wrap shell commands in JavaScript unless the task explicitly requires JavaScript.
- If a tool is unavailable or fails, report that accurately. Do not repeatedly retry through invented interfaces.

## Development workflow
- Inspect relevant files before editing them.
- Make the smallest change that solves the current task.
- After editing, run the relevant tests or checks using the actual shell tool.
- Report the commands run and their real results. Never claim a test passed unless it ran successfully.
- If a test fails, inspect the traceback and fix the underlying cause rather than guessing.
- Show a concise summary of changes and any remaining limitations.
- Work in stages. Present a plan and wait for approval before beginning a new implementation stage.

## Project specification
- Treat `PROJECT.md` as the source of truth for product requirements and intended behavior.
- Treat this file as persistent development rules, not a replacement for the full specification.
- Flag ambiguities or contradictions rather than silently inventing requirements or dropping existing ones.

## Google Docs integration
- Keep the initial implementation read-only until explicitly asked to implement writing.
- Never print, expose, commit, or log OAuth credentials or tokens.
- Use official Google API documentation when uncertain about response structures or scopes.
- Test against dummy documents before using real student documents.
- Preserve existing document content and formatting; do not invent API behavior.
- Never modify real student documents without explicit approval.

## Scope control
- Do not perform unrelated refactors or change dependencies without explaining why.
- If blocked, state the exact blocker and ask for the minimum information needed.
