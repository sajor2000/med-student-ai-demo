# Requirements

What to install, by feature. **Required** gets you flashcards, quizzes, and
study guides with checked citations. **Optional** features switch on one command each.

| | Component | Needed for | macOS | Windows |
|---|---|---|---|---|
| Required | Agent harness: [Claude Code](https://claude.com/claude-code) **or** [Codex](https://github.com/openai/codex) | running the skills | `curl -fsSL https://claude.ai/install.sh \| bash` (Codex: `npm i -g @openai/codex`) | `irm https://claude.ai/install.ps1 \| iex` (Codex: `npm i -g @openai/codex`) |
| Required | `git` | cloning the repo | `brew install git` | `winget install Git.Git` |
| Required | [`uv`](https://docs.astral.sh/uv/) | every `scripts/*.py` (installs its own Python) | `brew install uv` | `winget install astral-sh.uv` |
| Required | Node 24+ | the PubMed connector (`npx`) | `brew install node` | `winget install OpenJS.NodeJS` |
| Required | PubMed MCP | literature search and citation checking | in `.mcp.json` / `.codex/config.toml`; nothing to install | same, plus the `cmd /c` note below |
| Recommended | Paperclip MCP | `/deepen` full text and cross-paper evidence | sign in once (`/mcp` in Claude Code, `codex mcp login paperclip` in Codex) | same |
| Optional | Anki desktop 23.10+ and AnkiConnect `2055492159` | `/anki-sync` | Anki: Tools > Add-ons > Get Add-ons, code `2055492159`, restart | same |
| Optional | Playwright Chromium | `/visualize`, occlusion cards, the Diagrams tab | `uv run --with playwright playwright install chromium` | same |
| Optional | diagram-design plugin (Claude Code) | `/visualize` rendering | `/plugin marketplace add cathrynlavery/diagram-design`, then `/plugin install diagram-design@diagram-design` | same |
| Optional | OpenRouter key with a spend limit | `/mnemonic-art` | `export OPENROUTER_API_KEY=...` | `$env:OPENROUTER_API_KEY="..."` |
| Optional | NCBI key and email | faster PubMed rate limit | `export NCBI_API_KEY=... NCBI_EMAIL=...` | `$env:NCBI_API_KEY="..."` |

An account for the harness is also needed (Claude Pro/Max or an Anthropic API
account for Claude Code; a ChatGPT plan or API key for Codex).

## Notes by feature

- **PubMed on Windows.** The connector must launch through `cmd`. Claude Code:
  `claude mcp add pubmed --scope local -- cmd /c npx -y @cyanheads/pubmed-mcp-server@2.12.0`.
  Codex: in `.codex/config.toml` set `command = "cmd"` and
  `args = ["/c", "npx", "-y", "@cyanheads/pubmed-mcp-server@2.12.0"]`.
- **`/visualize` in Codex.** The diagram-design plugin is a Claude Code plugin.
  Without it, `/visualize` stops with install instructions; the rest of the loop works.
- **`/mnemonic-art`.** Create the key at openrouter.ai with a **spend limit**. Under
  [openrouter.ai/settings/privacy](https://openrouter.ai/settings/privacy) allow
  image-capable endpoints for your key. The approved prompt goes to a second provider,
  so check your school's AI policy first.
- **`/anki-sync`.** Keep Anki open while syncing. The script talks only to
  `http://127.0.0.1:8765` (loopback).
- **Codex skills on Windows.** `.agents/skills` is a symlink to `.claude/skills`. Git
  needs `core.symlinks=true` (or Developer Mode) to create it. If your clone has a
  plain text file there, run `rmdir /s /q .agents\skills` then
  `mklink /D .agents\skills ..\.claude\skills` in an elevated prompt, or copy the folder.

## Verify your setup

Run from the repo folder. Each line should print a version or a result, not an error.

```bash
git --version
node -v                      # v24 or higher
uv --version
claude --version             # or: codex --version
claude mcp list              # pubmed and paperclip listed (Codex: codex mcp list)
```

```bash
# Optional features
curl -s -X POST http://127.0.0.1:8765 -d '{"action":"version","version":6}'   # Anki open: {"result": 6, "error": null}
uv run --with playwright playwright install --dry-run chromium                 # Chromium known to Playwright
printenv OPENROUTER_API_KEY | wc -c                                            # greater than 1 when set (PowerShell: $env:OPENROUTER_API_KEY.Length)
```

Then run the no-course-files check from the README: `extract`, `check`, `export` on
`sample/` should print a PASS and write `examples/flashcards.html`.
