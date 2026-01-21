#!/usr/bin/env python3
"""
Notion API Agent for DailyTopArxiv

This script allows you to upload content from markdown files to Notion pages.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, List

try:
    from notion_client import Client
except ImportError:
    print("Error: notion-client library not found. Install it with:")
    print("  uv sync")
    print("  or: pip install notion-client")
    sys.exit(1)


class NotionAgent:
    """Agent for interacting with Notion API"""
    
    def __init__(self, api_token: str):
        """
        Initialize Notion client
        
        Args:
            api_token: Your Notion integration token
        """
        self.client = Client(auth=api_token)
    
    def verify_credentials(self, test_page_id: Optional[str] = None) -> bool:
        """
        Verify that credentials are valid and optionally test page access
        
        Args:
            test_page_id: Optional page ID to test access to
        """
        try:
            # Try to list users to verify token
            users = self.client.users.list()
            print(f"✓ Connected to Notion successfully!")
            if users.get("results"):
                user = users["results"][0]
                print(f"  User: {user.get('name', 'Unknown')}")
            
            # Test page access if provided
            if test_page_id:
                print(f"\nTesting access to page: {test_page_id}")
                try:
                    # Format page ID (remove hyphens if present, then add them back in correct format)
                    formatted_id = self.format_page_id(test_page_id)
                    page = self.client.pages.retrieve(page_id=formatted_id)
                    print(f"✓ Page accessible!")
                    print(f"  Title: {self.get_page_title(page)}")
                    print(f"  URL: {page.get('url', 'N/A')}")
                    return True
                except Exception as e:
                    print(f"✗ Cannot access page: {e}")
                    print(f"\nTroubleshooting:")
                    print(f"  1. Make sure the page is shared with your integration")
                    print(f"  2. Go to the page → '...' → 'Connections' → Add your integration")
                    print(f"  3. Verify the page ID is correct (32 characters)")
                    print(f"  4. Try copying the page ID from the Notion URL")
                    return False
            
            return True
        except Exception as e:
            print(f"✗ Failed to verify credentials: {e}")
            return False
    
    def format_page_id(self, page_id: str) -> str:
        """
        Format Notion page ID to standard format (with hyphens)
        
        Notion page IDs should be in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        """
        # Remove any existing hyphens and whitespace
        clean_id = page_id.replace('-', '').replace(' ', '')
        
        # Add hyphens in the correct positions
        if len(clean_id) == 32:
            return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
        return page_id  # Return as-is if not 32 chars
    
    def get_page_title(self, page: Dict) -> str:
        """Extract page title from Notion page object"""
        props = page.get('properties', {})
        for prop_name, prop_value in props.items():
            if prop_value.get('type') == 'title':
                title_array = prop_value.get('title', [])
                if title_array:
                    return title_array[0].get('plain_text', 'Untitled')
        return 'Untitled'
    
    def read_markdown_file(self, file_path: str) -> str:
        """Read content from a markdown file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return path.read_text(encoding='utf-8').strip()
    
    def markdown_to_notion_blocks(self, markdown: str) -> List[Dict]:
        """
        Convert markdown to Notion blocks
        
        This is a simple converter. For more complex markdown, consider using
        a library like markdown-to-notion or md2notion.
        """
        blocks = []
        lines = markdown.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Headers
            if line.startswith('# '):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]
                    }
                })
            elif line.startswith('### '):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:].strip()}}]
                    }
                })
            # Bullet lists
            elif line.startswith('- ') or line.startswith('* '):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]
                    }
                })
            # Numbered lists
            elif line[0].isdigit() and '. ' in line[:5]:
                content = line.split('. ', 1)[1] if '. ' in line else line
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": content.strip()}}]
                    }
                })
            # Code blocks
            elif line.startswith('```'):
                # Skip code block markers for now (would need multi-line handling)
                continue
            # Regular paragraphs
            else:
                # Remove markdown formatting for simple text
                text = line.replace('**', '').replace('*', '').replace('`', '')
                if text:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        }
                    })
        
        return blocks
    
    def create_page(self, parent_id: str, title: str, content: str) -> Dict:
        """
        Create a new Notion page with markdown content
        
        Args:
            parent_id: The parent page or database ID
            title: Page title
            content: Markdown content to convert to blocks
        
        Returns:
            The created page dict
        """
        try:
            # Format the parent ID
            formatted_parent_id = self.format_page_id(parent_id)
            
            # Convert markdown to blocks
            blocks = self.markdown_to_notion_blocks(content)
            
            # Create the page
            page = self.client.pages.create(
                parent={"page_id": formatted_parent_id},
                properties={
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                },
                children=blocks
            )
            
            print(f"✓ Created page: {title}")
            print(f"  URL: {page.get('url', 'N/A')}")
            return page
        except Exception as e:
            print(f"✗ Failed to create page: {e}")
            return None
    
    def append_to_page(self, page_id: str, content: str) -> bool:
        """
        Append content to an existing Notion page
        
        Args:
            page_id: The page ID to append to
            content: Markdown content to append
        """
        try:
            # Format the page ID
            formatted_page_id = self.format_page_id(page_id)
            blocks = self.markdown_to_notion_blocks(content)
            
            self.client.blocks.children.append(
                block_id=formatted_page_id,
                children=blocks
            )
            
            print(f"✓ Appended content to page")
            return True
        except Exception as e:
            print(f"✗ Failed to append content: {e}")
            return False
    
    def fetch_page_content(self, page_id: str) -> Optional[str]:
        """
        Fetch content from a Notion page and convert to plain text
        
        Args:
            page_id: The page ID to fetch content from
        
        Returns:
            Plain text content of the page
        """
        try:
            formatted_page_id = self.format_page_id(page_id)
            
            # Get page info
            page = self.client.pages.retrieve(page_id=formatted_page_id)
            
            # Get all blocks (handle pagination)
            all_blocks = []
            cursor = None
            
            while True:
                response = self.client.blocks.children.list(
                    block_id=formatted_page_id,
                    start_cursor=cursor
                )
                all_blocks.extend(response.get("results", []))
                cursor = response.get("next_cursor")
                if not cursor:
                    break
            
            # Convert blocks to text
            content_parts = []
            
            for block in all_blocks:
                block_type = block.get("type")
                block_content = block.get(block_type, {})
                rich_text = block_content.get("rich_text", [])
                
                if rich_text:
                    # Extract text from rich_text array
                    text_content = "".join([rt.get("plain_text", "") for rt in rich_text])
                    if text_content:
                        # Add appropriate markdown formatting based on block type
                        if block_type == "heading_1":
                            content_parts.append(f"# {text_content}\n")
                        elif block_type == "heading_2":
                            content_parts.append(f"## {text_content}\n")
                        elif block_type == "heading_3":
                            content_parts.append(f"### {text_content}\n")
                        elif block_type == "bulleted_list_item":
                            content_parts.append(f"- {text_content}\n")
                        elif block_type == "numbered_list_item":
                            content_parts.append(f"1. {text_content}\n")
                        else:
                            content_parts.append(f"{text_content}\n")
            
            return "".join(content_parts).strip()
        except Exception as e:
            print(f"✗ Failed to fetch page content: {e}")
            return None
    
    def update_page(self, page_id: str, title: Optional[str] = None, content: Optional[str] = None) -> bool:
        """
        Update an existing Notion page
        
        Args:
            page_id: The page ID to update
            title: New title (optional)
            content: New content to replace (optional)
        """
        try:
            # Format the page ID
            formatted_page_id = self.format_page_id(page_id)
            
            # Update title if provided
            if title:
                self.client.pages.update(
                    page_id=formatted_page_id,
                    properties={
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": title
                                    }
                                }
                            ]
                        }
                    }
                )
            
            # Replace content if provided
            if content:
                # First, get existing blocks and delete them
                blocks = self.client.blocks.children.list(block_id=formatted_page_id)
                for block in blocks.get("results", []):
                    try:
                        self.client.blocks.delete(block_id=block["id"])
                    except:
                        pass  # Some blocks can't be deleted
                
                # Add new content
                new_blocks = self.markdown_to_notion_blocks(content)
                self.client.blocks.children.append(
                    block_id=formatted_page_id,
                    children=new_blocks
                )
            
            print(f"✓ Updated page")
            return True
        except Exception as e:
            print(f"✗ Failed to update page: {e}")
            return False


def load_config(config_path: str = ".config/notion_config.json") -> dict:
    """Load Notion configuration from JSON file"""
    # Resolve relative to project root (parent of src)
    if not Path(config_path).is_absolute():
        project_root = Path(__file__).resolve().parent.parent
        config_file = project_root / config_path
    else:
        config_file = Path(config_path)
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(config: dict, config_path: str = ".config/notion_config.json"):
    """Save Notion configuration to JSON file"""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"✓ Configuration saved to {config_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload content to Notion from markdown files"
    )
    parser.add_argument(
        'file',
        nargs='?',
        help='Path to markdown file to upload'
    )
    parser.add_argument(
        '--api-token',
        help='Notion API token'
    )
    parser.add_argument(
        '--config',
        default='.config/notion_config.json',
        help='Path to config file (default: .config/notion_config.json)'
    )
    parser.add_argument(
        '--parent-id',
        help='Parent page or database ID (required for creating pages)'
    )
    parser.add_argument(
        '--page-id',
        help='Existing page ID (for updating/appending)'
    )
    parser.add_argument(
        '--title',
        help='Page title (default: filename)'
    )
    parser.add_argument(
        '--append',
        action='store_true',
        help='Append content to existing page instead of creating new'
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update existing page (replace content)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify credentials only'
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Get API token
    api_token = args.api_token or config.get('api_token') or os.getenv('NOTION_API_TOKEN')
    if not api_token:
        print("Error: Notion API token is required")
        print("You can provide it via:")
        print("  --api-token argument")
        print("  NOTION_API_TOKEN environment variable")
        print("  .config/notion_config.json file")
        print("\nGet your token from: https://www.notion.so/my-integrations")
        sys.exit(1)
    
    # Initialize agent
    agent = NotionAgent(api_token=api_token)
    
    # Get default_parent_id for testing
    default_parent_id = config.get('default_parent_id')
    
    # Verify credentials (and test page access if default_parent_id is set)
    if not agent.verify_credentials(test_page_id=default_parent_id if args.verify else None):
        sys.exit(1)
    
    if args.verify:
        if default_parent_id:
            print("\n✓ All checks passed! You're ready to upload content.")
        else:
            print("\n✓ Credentials verified successfully!")
            print("  Tip: Set 'default_parent_id' in .config/notion_config.json to test page access")
        return
    
    # Upload content
    if not args.file:
        print("Error: Markdown file is required")
        print("Usage: python notion_agent.py <file.md> --parent-id <parent_id>")
        sys.exit(1)
    
    try:
        content = agent.read_markdown_file(args.file)
        title = args.title or Path(args.file).stem.replace('_', ' ').title()
        
        print(f"\nContent to upload ({len(content)} characters):")
        print("-" * 50)
        print(content[:200] + "..." if len(content) > 200 else content)
        print("-" * 50)
        
        if args.update and args.page_id:
            # Update existing page
            response = input(f"\nUpdate page {args.page_id}? (y/n): ")
            if response.lower() == 'y':
                agent.update_page(args.page_id, title=title, content=content)
        elif args.append and args.page_id:
            # Append to existing page
            response = input(f"\nAppend to page {args.page_id}? (y/n): ")
            if response.lower() == 'y':
                agent.append_to_page(args.page_id, content)
        else:
            # Try to use default_parent_id from config
            parent_id = args.parent_id or config.get('default_parent_id')
            
            if parent_id:
                # Create new page
                response = input(f"\nCreate new page '{title}' in parent {parent_id}? (y/n): ")
                if response.lower() == 'y':
                    agent.create_page(parent_id, title, content)
            else:
                print("\nError: Need either --parent-id (to create) or --page-id (to update/append)")
                print("You can also set 'default_parent_id' in notion_config.json")
                print("\nUsage examples:")
                print("  python notion_agent.py file.md --parent-id <parent_id>")
                print("  python notion_agent.py file.md --page-id <page_id> --append")
                print("  python notion_agent.py file.md --page-id <page_id> --update")
                print("\nOr set default_parent_id in .config/notion_config.json to skip --parent-id")
                sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
