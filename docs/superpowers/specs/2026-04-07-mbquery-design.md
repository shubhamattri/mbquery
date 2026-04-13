# mbquery — The Ultimate Metabase CLI

**Date:** 2026-04-07
**Author:** Shubham Attri
**Repo:** github.com/shubhamattri/mbquery
**License:** MIT

---

## 1. Purpose

A Python CLI tool that lets you query Metabase from the terminal using raw SQL or natural language. Also works as an MCP server for AI agents and as an importable Python library.

**Why this exists:** No existing tool combines CLI + NL→SQL + MCP server. The closest competitors are:
- `mb-cli` (Go) — SQL only, no NL, no MCP
- `metabase-cli` (npm) — SQL only, no NL, no MCP
- `metabase-api` (Python) — library only, no CLI, no NL
- Various MCP servers — AI-only, no human CLI

mbquery is all of these in one `pip install`.

---

## 2. Target Audience

1. **Developers/data teams** who have Metabase but want CLI access for scripting, automation, CI/CD
2. **AI agents/LLMs** via MCP server mode — Claude, Cursor, Copilot, etc.
3. **Python developers** who want a Metabase library for their scripts

---

## 3. Architecture

```
src/mbquery/
├── cli/                     # Typer CLI commands
│   ├── app.py               # Root Typer app + global flags
│   ├── query.py             # `mbquery query` (SQL)
│   ├── ask.py               # `mbquery ask` (NL → SQL)
│   ├── schema.py            # `mbquery schema` (browse DB/tables/fields)
│   ├── card.py              # `mbquery card` (list/run saved questions)
│   ├── dashboard.py         # `mbquery dashboard` (list/show/run)
│   ├── search.py            # `mbquery search`
│   └── config_cmd.py        # `mbquery config` (profiles, setup wizard)
├── core/                    # Business logic (shared by CLI + MCP + library)
│   ├── client.py            # HTTP client (auth, retry, session mgmt)
│   ├── database.py          # Database/table/field operations
│   ├── cards.py             # Card operations
│   ├── dashboards.py        # Dashboard operations
│   ├── queries.py           # SQL execution + NL→SQL orchestration
│   ├── search.py            # Search operations
│   └── schema_cache.py      # Schema auto-discovery + caching
├── ai/                      # Pluggable LLM layer
│   ├── base.py              # Abstract LLMProvider interface
│   ├── openai_compat.py     # OpenAI-compatible (OpenAI, Ollama, vLLM, Anthropic, etc.)
│   ├── gemini.py            # Google Gemini (different API format)
│   └── prompt.py            # NL→SQL prompt builder (schema-aware)
├── mcp/                     # MCP server mode
│   └── server.py            # MCP tools + resources
├── config/                  # Config management
│   ├── store.py             # Profile CRUD
│   └── models.py            # Config dataclasses
├── formatters/              # Output formatting
│   ├── table.py             # Rich table (default for TTY)
│   ├── csv_fmt.py           # CSV
│   ├── json_fmt.py          # JSON / JSONL
│   ├── markdown.py          # Markdown table
│   └── redact.py            # PII redaction
└── utils/
    ├── resolve.py           # Name-or-ID resolution
    └── tty.py               # TTY detection for auto-format
```

**Key design principle:** `core/` is the shared brain. CLI, MCP, and library all use it. Zero coupling between layers.

---

## 4. Commands

### 4.1 Query (SQL)

```bash
mbquery query "SELECT COUNT(*) FROM users"
mbquery query --file query.sql
mbquery query --db prod "SELECT ..."
```

### 4.2 Ask (Natural Language → SQL)

```bash
mbquery ask "how many users signed up last week"
mbquery ask "top 10 customers by revenue" --show-sql
```

`--show-sql` prints the generated SQL before executing so users can verify/learn.

Auto-detects SQL vs NL: if input starts with SELECT/INSERT/UPDATE/DELETE/WITH/CREATE/ALTER/DROP/EXPLAIN/SHOW, it's treated as SQL. Otherwise NL.

### 4.3 Schema Browsing

```bash
mbquery schema databases
mbquery schema tables
mbquery schema tables --db 2
mbquery schema fields users
mbquery schema refresh
```

### 4.4 Saved Cards

```bash
mbquery card list
mbquery card run 42
mbquery card run "Monthly Revenue"      # Name-or-ID resolution
mbquery card run 42 --param "date=2026-01-01"
```

### 4.5 Dashboards

```bash
mbquery dashboard list
mbquery dashboard show 15
mbquery dashboard run 15
```

### 4.6 Search

```bash
mbquery search "revenue"
mbquery search "revenue" --type card
```

### 4.7 Config

```bash
mbquery config init                    # Interactive setup wizard
mbquery config add prod --url ... --api-key ...
mbquery config list
mbquery config switch staging
mbquery config set-llm                 # Interactive LLM setup
mbquery config set-hints users "plan_type values are 'free', 'pro', 'enterprise'"
```

### 4.8 MCP Server

```bash
mbquery serve                          # Start MCP server (stdio)
```

### 4.9 Global Flags

```bash
--format table|csv|json|jsonl|markdown
--profile prod
--db 2
--limit 100
--no-redact
--verbose
--fields "id,name,email"
```

TTY auto-detection: `table` format for interactive terminal, `json` when piped.

---

## 5. AI/LLM Plugin System

### 5.1 Abstract Interface

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate_sql(self, prompt: str) -> str:
        """Send NL→SQL prompt, return raw SQL string."""
        pass
```

One method. Implement it, you have a new provider.

### 5.2 Built-in Providers

| Provider | Covers | Config |
|----------|--------|--------|
| `openai_compat` | OpenAI, Azure, Anthropic, Ollama, vLLM, LiteLLM | `base_url` + `api_key` + `model` |
| `gemini` | Google Gemini | `api_key` + `model` |

### 5.3 NL→SQL Prompt Builder

The prompt is built dynamically from three sources:

1. **Auto-discovered schema** — cached from Metabase's `/api/database/{id}/metadata` endpoint. Table names, column names, column types.
2. **User hints** — from `~/.config/mbquery/hints.yaml`. Business context the schema can't tell you (e.g., "status values are 'pending', 'completed', 'refunded'").
3. **Query history** (optional) — last 10 successful NL→SQL pairs stored locally for few-shot examples.

### 5.4 Fallback Behavior

- No LLM configured → `mbquery ask` tells you to run `mbquery config set-llm`
- LLM call fails → shows error, suggests `mbquery query` with raw SQL
- `--show-sql` always available for transparency

---

## 6. Interactive Setup Wizard

```
$ mbquery config init

  Welcome to mbquery! Let's set up your first profile.

  Metabase URL: https://metabase.example.com
  Auth method:
    ❯ 1. API Key (recommended)
      2. Email + Password

  API Key: mb_xxx
  Default database ID (optional): 2
  Profile name [default]: prod

  ✅ Profile 'prod' saved. Testing connection...
  ✅ Connected as: John Doe (john@example.com)

  Set up AI-powered natural language queries? [Y/n]: y

  Choose your LLM provider:
    ❯ 1. OpenAI (GPT-4o, GPT-4o-mini)
      2. Google Gemini (Gemini 2.0 Flash — free tier available)
      3. Anthropic Claude (via OpenAI-compatible)
      4. Ollama (local, free, no API key needed)
      5. Other OpenAI-compatible endpoint
      6. Skip for now

  > 2

  Choose model:
    ❯ 1. gemini-2.0-flash (recommended — fast, cheap)
      2. gemini-2.5-pro (best quality, slower)
      3. Custom model name

  > 1

  Gemini API Key (get one free at ai.google.dev): AIza...

  ✅ Testing LLM connection... works!
  ✅ Pulling schema for NL→SQL... 42 tables, 387 columns cached.

  You're ready! Try:
    mbquery ask "how many users signed up last week"
```

Key UX:
- Numbered menus for provider + model (no typing provider names)
- Popular models pre-listed with recommendations per provider
- "Custom model name" option for power users
- Ollama auto-detects local server at localhost:11434
- Skip option — LLM is optional, SQL always works
- Instant validation — tests both Metabase + LLM before finishing
- Same interactive flow via `mbquery config set-llm` to change providers later

---

## 7. Config, Auth & PII Redaction

### 7.1 Config Location

```
~/.config/mbquery/
├── config.yaml          # Profiles + LLM config + defaults
├── schema_cache/        # Auto-discovered schemas (per profile)
│   ├── prod.json
│   └── staging.json
└── hints.yaml           # User schema hints
```

### 7.2 config.yaml Structure

```yaml
active_profile: prod
defaults:
  format: table
  limit: 100
  redact_pii: true

profiles:
  prod:
    url: https://metabase.example.com
    auth:
      method: api-key
      api_key: mb_xxx
    default_db: 2
  staging:
    url: https://staging.metabase.com
    auth:
      method: session
      email: user@example.com
      password: xxx
    default_db: 1

llm:
  provider: openai
  model: gpt-4o
  api_key: sk-xxx
  base_url: null
```

File permissions: `0600` on config.yaml (contains credentials).

### 7.3 Auth Resolution Order

1. `--profile` flag → use that profile
2. `MBQUERY_URL` + `MBQUERY_API_KEY` env vars → ephemeral profile (CI/CD)
3. Active profile from config.yaml

### 7.4 Env Var Overrides

Every config value has an env var counterpart:

```
MBQUERY_URL, MBQUERY_API_KEY, MBQUERY_DEFAULT_DB,
MBQUERY_LLM_PROVIDER, MBQUERY_LLM_API_KEY, MBQUERY_LLM_MODEL,
MBQUERY_LLM_BASE_URL, MBQUERY_FORMAT, MBQUERY_REDACT_PII
```

Precedence: flags > env vars > config.yaml.

### 7.5 PII Redaction

Inspired by mb-cli, improved:

1. After query executes, fetch field metadata from Metabase API (cached)
2. Check each column's `semantic_type` against PII list: `type/Email`, `type/Name`, `type/Phone`, `type/Address`, `type/Birthdate`, `type/City`, `type/State`, `type/ZipCode`, `type/Country`, `type/Latitude`, `type/Longitude`, `type/AvatarURL`
3. For native SQL queries (no semantic types in response), enrich from cached field metadata
4. Replace PII column values with `[REDACTED]`
5. Default ON — disable with `--no-redact`
6. Exports with redaction show warning but are not blocked (users are adults)

---

## 8. MCP Server Mode

### 8.1 Tools (10)

| Tool | Description |
|------|-------------|
| `query` | Execute raw SQL (write-blocking by default) |
| `ask` | Natural language → SQL → execute |
| `list_databases` | List all databases |
| `list_tables` | List tables in a database |
| `get_table_schema` | Get columns/types for a table |
| `run_card` | Execute a saved question |
| `list_cards` | List saved questions |
| `list_dashboards` | List dashboards |
| `search` | Search across Metabase |
| `get_schema_context` | Return full schema + hints for AI self-serve |

All tools are read-only by default. INSERT/UPDATE/DELETE/DROP blocked at the MCP layer.

### 8.2 Design Choices (from jerichosequitin)

- Response optimization — strip unnecessary fields (90% token reduction)
- Schema/list caching with configurable TTL (default 10 min)
- Tool annotations: `readOnlyHint`, `idempotentHint` on every tool

### 8.3 MCP Resources

```
metabase://database/{id}
metabase://table/{id}
metabase://card/{id}
metabase://dashboard/{id}
```

### 8.4 Integration

Uses same `~/.config/mbquery/config.yaml`. No separate config.

Claude Desktop config:
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

---

## 9. Packaging & Distribution

### 9.1 Install

```bash
pip install mbquery          # Core CLI + library
pip install mbquery[mcp]     # + MCP server dependencies
pip install mbquery[all]     # Everything
```

### 9.2 Dependencies

| Package | Purpose | Required |
|---------|---------|:--------:|
| `typer` | CLI framework | ✅ |
| `rich` | Pretty tables, progress | ✅ |
| `httpx` | HTTP client (async + sync) | ✅ |
| `pyyaml` | Config files | ✅ |
| `mcp` | MCP server SDK | optional |

### 9.3 Build System

- `pyproject.toml` with `hatchling`
- Python 3.10+
- `ruff` for linting/formatting
- `pytest` for tests

### 9.4 Entry Point

```toml
[project.scripts]
mbquery = "mbquery.cli.app:main"
```

### 9.5 GitHub CI

- `test.yml` — runs pytest on PR
- `publish.yml` — publishes to PyPI on git tag (v0.1.0, etc.)

---

## 10. Features Inherited From Competitors

| Source | Feature |
|--------|---------|
| **mb-cli** (Go) | PII redaction (default on), `--fields` column filtering, name-or-ID resolution, TTY auto-format, structured errors |
| **metabase-cli** (npm) | Multi-profile system, `--file` for SQL files, native export (bypass row limits), env var auth for CI/CD, safe mode |
| **metabase-api** (Python) | Auto session renewal, name-or-ID everywhere, async support |
| **MCP servers** | Response optimization, caching with TTL, read-only mode, MCP tools + resources |
| **Original mbquery** | NL→SQL, auto-detect SQL vs NL, schema-aware prompts, `--show-sql` |

---

## 11. What's NOT in v1

Explicitly out of scope for first release:
- Write operations (create/update/delete cards, dashboards, collections)
- User/permission management
- Dashboard composition (adding cards to dashboards)
- Alerting/subscriptions
- Keyring integration for password storage
- Shell completions (fish/zsh/bash)
- Plugin system for custom formatters

These can be added in v2+ if there's demand.

---

## 12. Success Criteria

v1 is done when:
- `pip install mbquery` works
- `mbquery config init` walks through interactive setup
- `mbquery query "SELECT 1"` returns results
- `mbquery ask "count all users"` generates + executes SQL
- `mbquery serve` starts a working MCP server
- All 6 output formats work
- PII redaction works
- Multi-profile switching works
- Published on PyPI
- README with examples
- CI running tests on PR
