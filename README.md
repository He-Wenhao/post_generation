# Post Generation Tools for DailyTopArxiv

Automated workflow to pull product descriptions from Notion, generate social media posts using AI (OpenRouter), and automatically publish to Mastodon.

## 🚀 Quick Start

### Configure credentials

   - **Notion**: Create/edit `.config/notion_config.json` with your Notion API token
   - **OpenRouter**: Create/edit `.config/openrouter_config.json` with your OpenRouter API key
   - **Mastodon**: Create/edit `.config/mastodon_config.json` with your Mastodon instance URL and access token
   - **Workflow**: Copy `.config/workflow_config.json.example` to `.config/workflow_config.json` and configure your settings

### Run

```bash
uv run python src/post_workflow.py
```

## 🛠️ Automated Post Generation Workflow

End-to-end automation for generating and publishing social media posts:

- ✅ **Pull from Notion** - Automatically fetch product descriptions from any Notion page
- ✅ **AI Generation** - Generate platform-specific posts using OpenRouter (GPT-4, Claude, etc.)
- ✅ **Multi-Platform** - Generate posts for Twitter, LinkedIn, Instagram, Facebook, and more
- ✅ **Auto-Publish to Mastodon** - Automatically publish generated posts to Mastodon
- ✅ **JSON Configuration** - All settings in `.config/workflow_config.json` - no command-line arguments needed
- ✅ **Customizable** - Control tone, platforms, model selection, and Mastodon visibility