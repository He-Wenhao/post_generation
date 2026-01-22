#!/bin/bash
# Generate configuration file templates from .example files

set -e  # Exit on error

PROJECT_DIR="${PROJECT_DIR:-$HOME/post_generation}"
CONFIG_DIR="$PROJECT_DIR/.config"

echo "📝 Generating configuration file templates..."

# Check if config directory exists
if [ ! -d "$CONFIG_DIR" ]; then
    echo "Creating .config directory..."
    mkdir -p "$CONFIG_DIR"
fi

# Copy all .example files to actual config files (if they don't exist)
for example_file in "$CONFIG_DIR"/*.example; do
    if [ -f "$example_file" ]; then
        config_file="${example_file%.example}"
        if [ ! -f "$config_file" ]; then
            echo "Creating $config_file from template..."
            cp "$example_file" "$config_file"
            echo "  ⚠️  Please edit $config_file with your actual credentials"
        else
            echo "  ✓ $config_file already exists (skipping)"
        fi
    fi
done

echo ""
echo "✅ Configuration templates generated!"
echo ""
echo "⚠️  Important: Edit the following files with your actual credentials:"
echo "   - $CONFIG_DIR/notion_config.json"
echo "   - $CONFIG_DIR/openrouter_config.json"
echo "   - $CONFIG_DIR/mastodon_config.json"
echo "   - $CONFIG_DIR/telegram_config.json (if using Telegram)"
echo "   - $CONFIG_DIR/replicate_config.json (if using image generation)"
echo "   - $CONFIG_DIR/workflow_config.json"
