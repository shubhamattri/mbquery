# mbquery

The ultimate Metabase CLI — SQL queries, natural language queries, and MCP server in one tool.

## Install

Install straight from the repo:

```bash
pip install "git+https://github.com/shubhamattri/mbquery.git"
```

To upgrade to the latest version, force a reinstall:

```bash
pip install --upgrade --force-reinstall "git+https://github.com/shubhamattri/mbquery.git"
```

For MCP server support:

```bash
pip install "mbquery[mcp] @ git+https://github.com/shubhamattri/mbquery.git"
```

> Not on PyPI yet — `pip install mbquery` won't work until it's published.

### First-time login (Google SSO profiles)

`mbquery` authenticates against Metabase's Google OAuth client, which is a
**Web-type** client and therefore requires the OAuth **client secret** at login.
Metabase never exposes the secret, so you must enter it once — get it from
whoever set up mbquery for your team (e.g. a shared 1Password entry), then:

```bash
mbquery login   # paste the Client Secret when prompted
```

## Quick Start

```bash
# Set up your first profile
mbquery config init

# Run SQL queries
mbquery query "SELECT COUNT(*) FROM users"

# Ask in natural language
mbquery ask "how many users signed up last week"

# Browse schema
mbquery schema tables
mbquery schema fields users

# Run saved questions
mbquery card list
mbquery card run 42

# Search
mbquery search "revenue"
```

## Features

- **SQL queries** — Run any SQL against Metabase from your terminal
- **Natural language** — Ask questions in plain English, get SQL + results
- **Pluggable AI** — OpenAI, Gemini, Ollama, or any OpenAI-compatible endpoint
- **Schema discovery** — Auto-pulls your database schema for accurate NL→SQL
- **6 output formats** — Table, CSV, JSON, JSONL, Markdown
- **PII redaction** — Automatically masks sensitive columns (on by default)
- **Multi-profile** — Switch between prod, staging, dev instances
- **MCP server** — Let AI agents query your Metabase
- **Python library** — `from mbquery.core.client import MetabaseClient`

## Output Formats

```bash
mbquery query "SELECT * FROM users LIMIT 5" --format table
mbquery query "SELECT * FROM users LIMIT 5" --format csv
mbquery query "SELECT * FROM users LIMIT 5" --format json
mbquery query "SELECT * FROM users LIMIT 5" --format jsonl
mbquery query "SELECT * FROM users LIMIT 5" --format markdown
```

## Natural Language Queries

```bash
mbquery config set-llm
mbquery ask "top 10 customers by revenue"
mbquery ask "how many orders last month" --show-sql
```

Supports: OpenAI, Google Gemini, Anthropic Claude, Ollama (local), any OpenAI-compatible API.

## Multi-Profile

```bash
mbquery config add prod --url https://metabase.example.com --api-key mb_xxx
mbquery config add staging --url https://staging.metabase.com --api-key mb_yyy
mbquery config switch staging
mbquery config list
```

## MCP Server

```bash
mbquery serve
```

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "mbquery": {
      "command": "mbquery",
      "args": ["serve"]
    }
  }
}
```

## Schema Hints

```bash
mbquery config set-hints users "plan_type values are 'free', 'pro', 'enterprise'"
mbquery config set-hints orders "status values are 'pending', 'completed', 'refunded'"
```

## Environment Variables

```
MBQUERY_URL=https://metabase.example.com
MBQUERY_API_KEY=mb_xxx
MBQUERY_DEFAULT_DB=2
```

LLM config via env vars coming in v0.2.

## License

MIT
