#!/usr/bin/env bash
# Launches the PubMed MCP server with Node 24+. Version 2.12.0 starts on Node 22 but every
# tool call then fails with "Promise.try is not a function", so we find a new enough node first.
# Overrides: PUBMED_MCP_NODE (path to a node binary), PUBMED_MCP_CMD (command to exec; for tests).
set -u

node_major() { "$1" -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/'; }

candidates=()
[ -n "${PUBMED_MCP_NODE:-}" ] && candidates+=("$PUBMED_MCP_NODE")
if p=$(command -v node 2>/dev/null); then candidates+=("$p"); fi
candidates+=(/opt/homebrew/bin/node /usr/local/bin/node)

found=""
for c in "${candidates[@]}"; do
  [ -x "$c" ] || continue
  major=$(node_major "$c")
  case "$major" in ''|*[!0-9]*) continue ;; esac
  if [ "$major" -ge 24 ]; then found="$c"; break; fi
done

if [ -z "$found" ]; then
  echo "PubMed connector needs Node 24+; install it (brew install node / nodejs.org)" >&2
  exit 1
fi

export PATH="$(dirname "$found"):$PATH"
if [ -n "${PUBMED_MCP_CMD:-}" ]; then
  exec "$PUBMED_MCP_CMD" "$@"
fi
exec npx -y @cyanheads/pubmed-mcp-server@2.12.0 "$@"
