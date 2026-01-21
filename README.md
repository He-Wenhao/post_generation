# Post Generation Tools for DailyTopArxiv

Automated workflow to pull product descriptions from Notion, generate social media posts using AI (OpenRouter), and automatically publish to Mastodon. Supports two modes: **Post Mode** (generate and publish posts) and **Reply Mode** (find and reply to related posts).

## 🚀 Quick Start

### Configure credentials

1. **Notion**: Create/edit `.config/notion_config.json` with your Notion API token
2. **OpenRouter**: Create/edit `.config/openrouter_config.json` with your OpenRouter API key and model
3. **Mastodon**: Create/edit `.config/mastodon_config.json` with your Mastodon instance URL and access token
4. **Workflow**: Copy `.config/workflow_config.json.example` to `.config/workflow_config.json` and configure your settings

### Run

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
