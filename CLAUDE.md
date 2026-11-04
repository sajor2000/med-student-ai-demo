@AGENTS.md

## Claude Code

- Skills are slash commands from `.claude/skills/` (`/ingest`, `/flashcards`, ...). `/visualize`, `/mnemonic-art`, `/anki-sync`, `/vignette`, `/teach-back` run only when typed.
- `.mcp.json` declares PubMed (stdio, `npx`) and Paperclip (HTTP, sign in with `/mcp`). Approve both when asked.
- `.claude/settings.json` pre-approves the five `uv run scripts/...` commands and the PubMed and Paperclip tools. Everything else asks.
