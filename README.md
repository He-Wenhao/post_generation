# Post Generation Tools for DailyTopArxiv

🤖 **AI-Powered Social Media Automation** - Automatically generate engaging posts from Notion content using advanced AI models

🎨 **AI Image Generation** - Create stunning visuals for your posts with Flux model

📱 **Multi-Platform Publishing** - Seamlessly publish to Mastodon with images attached

🔔 **Telegram Integration** - Remote approval and on-demand triggering via Telegram bot

✨ **Smart Reply Mode** - Automatically find and engage with relevant posts on Mastodon

🎯 **Human-in-the-Loop** - Full control with approval workflows before publishing

## 🚀 Quick Start

### Configure credentials

1. **Notion**: Create/edit `.config/notion_config.json` with your Notion API token
2. **OpenRouter**: Create/edit `.config/openrouter_config.json` with your OpenRouter API key and model
3. **Mastodon**: Create/edit `.config/mastodon_config.json` with your Mastodon instance URL and access token
4. **Telegram** (optional, for approval/trigger): Create/edit `.config/telegram_config.json` with your bot token and chat ID
5. **Replicate** (optional, for image generation): Create/edit `.config/replicate_config.json` with your API key
6. **Workflow**: Copy `.config/workflow_config.json.example` to `.config/workflow_config.json` and configure your settings

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
- ✅ **Image Generation** - Automatically generate images using Replicate's Flux model based on post content
- ✅ **Multi-Platform** - Generate posts for Twitter, LinkedIn, Instagram, Facebook, and more
- ✅ **Auto-Publish to Mastodon** - Automatically publish generated posts with images to Mastodon
- ✅ **Human Approval** - Review and approve/regenerate posts before publishing (cmd or Telegram)
- ✅ **JSON Configuration** - All settings in `.config/workflow_config.json` - no command-line arguments needed
- ✅ **Customizable** - Control tone, platforms, model selection, and Mastodon visibility

### Reply Mode (`"mode": "reply"`)

Automated engagement with related posts on Mastodon:

- ✅ **Keyword Extraction** - Automatically extract keywords from your product description
- ✅ **Post Discovery** - Search for the 5 most recent posts related to your business
- ✅ **Batch Reply Generation** - Use structured outputs to generate all replies at once
- ✅ **Auto-Reply** - Automatically post replies to relevant posts on Mastodon
- ✅ **Smart Matching** - Find posts that relate to your business using extracted keywords
- ✅ **Human Approval** - Review and approve replies before posting (cmd or Telegram)

## 📱 Approval Modes

The workflow supports two approval modes for reviewing content before publishing:

### Command-Line Approval (`"approval_mode": "cmd"`)

- Review posts/replies in the terminal
- Accept or regenerate each post individually
- Final confirmation before publishing
- Simple and straightforward

### Telegram Approval (`"approval_mode": "telegram"`)

- Receive approval requests via Telegram bot
- Interactive buttons for Accept/Regenerate
- Review from anywhere via Telegram
- Inline regeneration - regenerate posts directly from Telegram
- Confirmation messages after successful publishing

**Setup:**
1. Create a Telegram bot with [@BotFather](https://t.me/BotFather)
2. Get your chat ID
3. Configure `.config/telegram_config.json` with bot token and chat ID
4. Set `"approval_mode": "telegram"` in workflow config

## 🔔 Telegram Trigger Mode

Start the workflow on-demand via Telegram messages:

- Set `"telegram_trigger": "post_mastodon"` in workflow config
- Program waits for the exact trigger message before starting
- Ignore all other messages while waiting
- Perfect for scheduled or manual execution

**Example:**
```json
{
  "telegram_trigger": "post_mastodon"  // Wait for this message
}
```

Or set to `null` to start immediately (default behavior).

## 🎨 Image Generation

Automatically generate images for your posts:

- **AI-Powered** - Uses Replicate's Flux model to generate images
- **Post-Based Prompts** - Uses your post content as the image generation prompt
- **Auto-Download** - Images saved to `.images/` folder as PNG files
- **Auto-Attach** - Images automatically attached to Mastodon posts
- **Optional** - Only generates if Replicate is configured

**Setup:**
1. Get Replicate API key from [replicate.com](https://replicate.com)
2. Configure `.config/replicate_config.json` with your API key
3. Images are generated automatically after post approval

## ⚙️ Configuration

### Workflow Config (`workflow_config.json`)

```json
{
  "mode": "post",                    // "post" or "reply"
  "source_page_id": "your-page-id",
  "platforms": ["mastodon"],
  "tone": "engaging",
  "auto_publish": false,            // Skip final approval if true
  "approval_mode": "cmd",           // "cmd" or "telegram"
  "telegram_trigger": null,          // null or trigger message (e.g., "post_mastodon")
  "mastodon": {
    "enabled": true,
    "visibility": "public",
    "spoiler_text": null
  }
}
```

### Key Settings:

- **`mode`**: `"post"` (generate posts) or `"reply"` (find and reply)
- **`approval_mode`**: `"cmd"` (terminal) or `"telegram"` (Telegram bot)
- **`telegram_trigger`**: `null` (start immediately) or message string (wait for trigger)
- **`auto_publish`**: `false` (ask for approval) or `true` (publish automatically)
