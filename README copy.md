# Post Generation Tools for DailyTopArxiv

Automated workflow system for content generation and social media publishing. Orchestrates Notion API, OpenRouter AI models, and Mastodon API to generate and publish platform-specific social media content. Implements two operational modes: **Post Mode** (content generation and publishing) and **Reply Mode** (automated engagement via keyword-based post discovery and reply generation).

## Architecture

### System Components

```
┌─────────────────┐
│  post_workflow   │  ← Main orchestrator (PostWorkflow class)
│     (CLI)        │
└────────┬─────────┘
         │
    ┌────┴────┬──────────────┬─────────────┐
    │         │              │             │
┌───▼───┐ ┌──▼──────┐  ┌────▼──────┐ ┌───▼──────┐
│Notion │ │OpenRouter│  │ Mastodon  │ │Workflow  │
│ Agent │ │  Client  │  │  Agent    │ │  Config  │
└───┬───┘ └──┬──────┘  └────┬──────┘ └──────────┘
    │        │              │
    │        │              │
┌───▼───┐ ┌──▼──────┐  ┌────▼──────┐
│Notion │ │OpenRouter│  │Mastodon.py│
│  API  │ │   API   │  │  Library  │
└───────┘ └─────────┘  └───────────┘
```

### Data Flow

**Post Mode:**
1. `NotionAgent.fetch_page_content()` → Retrieves markdown content from Notion page
2. `OpenRouterClient.generate_post()` → Generates platform-specific content via HTTP POST to `/chat/completions`
3. `MastodonAgent.post_status()` → Publishes via Mastodon.py library to `/api/v1/statuses`

**Reply Mode:**
1. `NotionAgent.fetch_page_content()` → Retrieves source content
2. `PostWorkflow._extract_keywords()` → Regex-based keyword extraction with stop-word filtering
3. `MastodonAgent.search_posts()` → Queries Mastodon `/api/v2/search` endpoint
4. `OpenRouterClient.generate_replies_batch()` → Batch generation using structured outputs (JSON schema)
5. `MastodonAgent.reply_to_status()` → Posts replies via `/api/v1/statuses` with `in_reply_to_id`

## Technical Implementation

### Dependencies

- **Python**: >=3.8
- **Mastodon.py**: >=1.8.0 (Mastodon API client)
- **notion-client**: >=2.2.1 (Notion API v1 client)
- **requests**: >=2.31.0 (HTTP client for OpenRouter)

### Core Classes

#### `PostWorkflow`
- **Location**: `src/post_workflow.py`
- **Responsibilities**: Workflow orchestration, mode routing, keyword extraction
- **Key Methods**:
  - `run()`: Main entry point, routes to `_run_post_mode()` or `_run_reply_mode()`
  - `_extract_keywords()`: Implements regex-based keyword extraction with stop-word filtering and frequency counting

#### `NotionAgent`
- **Location**: `src/notion_agent.py`
- **API**: Notion API v1 (`notion_client.Client`)
- **Key Methods**:
  - `fetch_page_content(page_id)`: Retrieves page blocks, converts to markdown
  - `verify_credentials()`: Validates API token via `/users` endpoint

#### `OpenRouterClient`
- **Location**: `src/openrouter_client.py`
- **API**: OpenRouter API v1 (`https://openrouter.ai/api/v1`)
- **Endpoints**:
  - `POST /chat/completions`: Single post generation
  - `POST /chat/completions` (with structured outputs): Batch reply generation
- **Platform Limits**: Enforced character limits per platform (Twitter: 280, Mastodon: 500, etc.)
- **Key Methods**:
  - `generate_post()`: Single platform post generation
  - `generate_replies_batch()`: Batch reply generation using JSON schema structured outputs

#### `MastodonAgent`
- **Location**: `src/mastodon_agent.py`
- **Library**: Mastodon.py (wrapper for Mastodon REST API)
- **Endpoints**:
  - `POST /api/v1/statuses`: Status creation
  - `GET /api/v2/search`: Post search
  - `GET /api/v1/accounts/verify_credentials`: Credential verification
- **Key Methods**:
  - `post_status()`: Publishes status with visibility and spoiler text support
  - `search_posts()`: Searches public timeline with query and limit parameters
  - `reply_to_status()`: Creates reply with `in_reply_to_id` parameter

## Configuration

### Configuration Files

All configuration files are located in `.config/` directory:

1. **`notion_config.json`**
   ```json
   {
     "api_token": "secret_..."
   }
   ```

2. **`openrouter_config.json`**
   ```json
   {
     "api_key": "sk-or-v1-...",
     "model": "openai/gpt-4o-mini"
   }
   ```

3. **`mastodon_config.json`**
   ```json
   {
     "instance_url": "https://mastodon.social",
     "access_token": "..."
   }
   ```

4. **`workflow_config.json`** (required)
   ```json
   {
     "mode": "post",
     "source_page_id": "uuid",
     "platforms": ["twitter", "linkedin", "instagram"],
     "tone": "engaging",
     "mastodon": {
       "enabled": true,
       "visibility": "public",
       "spoiler_text": null
     },
     "auto_publish": false
   }
   ```

### Environment Variables

All configuration values can be overridden via environment variables:
- `NOTION_API_TOKEN`
- `OPENROUTER_API_KEY`
- `MASTODON_INSTANCE_URL`
- `MASTODON_ACCESS_TOKEN`

## 🚀 Quick Start

Configuration loading follows this precedence:
1. Environment variables (highest priority)
2. JSON config files
3. Default values (lowest priority)

## Usage

### Execution

```bash
uv run python src/post_workflow.py
```

The workflow will run based on the `mode` setting in `.config/workflow_config.json`.

## 🛠️ Features

### Post Mode (`"mode": "post"`)

End-to-end automation for generating and publishing social media posts:

- ✅ **Pull from Notion** - Automatically fetch product descriptions from any Notion page
- ✅ **AI Generation** - Generate platform-specific posts using OpenRouter (GPT-4, Claude, etc.)
- ✅ **Multi-Platform** - Generate posts for Twitter, LinkedIn, Instagram, Facebook, and more
- ✅ **Auto-Publish to Mastodon** - Automatically publish generated posts to Mastodon
- ✅ **JSON Configuration** - All settings in `.config/workflow_config.json` - no command-line arguments needed
- ✅ **Customizable** - Control tone, platforms, model selection, and Mastodon visibility

### Reply Mode (`"mode": "reply"`)

Automated engagement with related posts on Mastodon:

- ✅ **Keyword Extraction** - Automatically extract keywords from your product description
- ✅ **Post Discovery** - Search for the 5 most recent posts related to your business
- ✅ **Batch Reply Generation** - Use structured outputs to generate all replies at once
- ✅ **Auto-Reply** - Automatically post replies to relevant posts on Mastodon
- ✅ **Smart Matching** - Find posts that relate to your business using extracted keywords
