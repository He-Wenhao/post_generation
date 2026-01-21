#!/usr/bin/env python3
"""
Mastodon Posting Agent for DailyTopArxiv

This script allows you to post content from post_scripts folder to Mastodon.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict

try:
    from mastodon import Mastodon
except ImportError:
    print("Error: mastodon library not found. Install it with:")
    print("  pip install Mastodon.py")
    sys.exit(1)


class MastodonAgent:
    """Agent for posting to Mastodon"""
    
    def __init__(self, instance_url: str, access_token: str, 
                 client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None):
        """
        Initialize Mastodon client
        
        Args:
            instance_url: Your Mastodon instance URL (e.g., https://mastodon.social)
            access_token: Your access token
            client_id: Optional client ID (for future use)
            client_secret: Optional client secret (for future use)
        """
        self.instance_url = instance_url.rstrip('/')
        self.mastodon = Mastodon(
            access_token=access_token,
            api_base_url=self.instance_url
        )
    
    def verify_credentials(self) -> bool:
        """Verify that credentials are valid"""
        try:
            account = self.mastodon.account_verify_credentials()
            print(f"✓ Connected as: @{account['username']}@{account['acct'].split('@')[-1] if '@' in account['acct'] else ''}")
            return True
        except Exception as e:
            print(f"✗ Failed to verify credentials: {e}")
            return False
    
    def read_post_file(self, file_path: str) -> str:
        """Read content from a markdown post file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Post file not found: {file_path}")
        
        content = path.read_text(encoding='utf-8').strip()
        
        # Remove markdown formatting that might not work well on Mastodon
        # Keep basic formatting but clean up
        return content
    
    def post_status(self, content: str, visibility: str = 'public', 
                   spoiler_text: Optional[str] = None) -> dict:
        """
        Post a status to Mastodon
        
        Args:
            content: The status content (max 500 characters for most instances)
            visibility: 'public', 'unlisted', 'private', or 'direct'
            spoiler_text: Optional content warning text
        
        Returns:
            The created status dict
        """
        # Mastodon character limit is typically 500, but can vary
        max_length = 500
        
        if len(content) > max_length:
            print(f"⚠ Warning: Content is {len(content)} characters, max is {max_length}")
            print("Content will be truncated or you may need to split into a thread.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return None
        
        try:
            status = self.mastodon.status_post(
                content,
                visibility=visibility,
                spoiler_text=spoiler_text
            )
            print(f"✓ Posted successfully! Status ID: {status['id']}")
            print(f"  URL: {status['url']}")
            return status
        except Exception as e:
            print(f"✗ Failed to post: {e}")
            return None
    
    def reply_to_status(self, status_id: int, content: str, 
                       visibility: str = 'public') -> Optional[dict]:
        """
        Reply to a status on Mastodon
        
        Args:
            status_id: ID of the status to reply to
            content: Reply content
            visibility: 'public', 'unlisted', 'private', or 'direct'
        
        Returns:
            The created reply status dict, or None if failed
        """
        try:
            reply = self.mastodon.status_post(
                content,
                in_reply_to_id=status_id,
                visibility=visibility
            )
            print(f"✓ Replied successfully! Reply ID: {reply['id']}")
            print(f"  URL: {reply['url']}")
            return reply
        except Exception as e:
            print(f"✗ Failed to reply: {e}")
            return None
    
    def post_thread(self, posts: list, visibility: str = 'public') -> list:
        """
        Post a thread (multiple connected statuses)
        
        Args:
            posts: List of post content strings
            visibility: Visibility setting for all posts
        
        Returns:
            List of created status dicts
        """
        statuses = []
        in_reply_to_id = None
        
        for i, post_content in enumerate(posts, 1):
            print(f"\nPosting thread part {i}/{len(posts)}...")
            
            # Add thread indicator if not first post
            if in_reply_to_id:
                # Some instances prefer numbering, some don't
                # You can customize this
                pass
            
            try:
                status = self.mastodon.status_post(
                    post_content,
                    visibility=visibility,
                    in_reply_to_id=in_reply_to_id
                )
                statuses.append(status)
                in_reply_to_id = status['id']
                print(f"✓ Posted part {i}")
            except Exception as e:
                print(f"✗ Failed to post part {i}: {e}")
                break
        
        return statuses
    
    def split_thread_content(self, content: str, max_length: int = 450) -> list:
        """
        Split long content into thread parts
        
        Args:
            content: The content to split
            max_length: Max characters per part (leaving room for numbering)
        
        Returns:
            List of content parts
        """
        # Split by lines first, then by sentences if needed
        lines = content.split('\n')
        parts = []
        current_part = ""
        
        for line in lines:
            # If adding this line would exceed limit, start new part
            if len(current_part) + len(line) + 1 > max_length and current_part:
                parts.append(current_part.strip())
                current_part = line + "\n"
            else:
                current_part += line + "\n"
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    def search_posts(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search for posts on Mastodon related to a keyword
        
        Args:
            query: Search query (keyword or hashtag)
            limit: Maximum number of posts to return (default: 5)
        
        Returns:
            List of post dictionaries
        """
        try:
            # Search for posts using Mastodon search API
            # Try different parameter combinations based on Mastodon.py version
            try:
                # Try with type and limit parameters (newer versions)
                results = self.mastodon.search(q=query, type='statuses', limit=limit * 2)
            except (TypeError, KeyError) as e:
                # If type parameter not supported, try without it
                try:
                    results = self.mastodon.search(q=query, limit=limit * 2)
                except TypeError:
                    # If limit also not supported, use minimal parameters
                    results = self.mastodon.search(q=query)
            
            # Handle both dict and AttribAccessDict return types
            if hasattr(results, 'statuses'):
                statuses = results.statuses
            elif hasattr(results, 'get'):
                statuses = results.get('statuses', [])
            else:
                statuses = []
            
            if not statuses:
                print(f"ℹ No posts found for query: {query}")
                return []
            
            # Filter to get most recent posts
            # Remove duplicates and sort by creation time
            seen_ids = set()
            unique_statuses = []
            for status in statuses:
                if status['id'] not in seen_ids:
                    seen_ids.add(status['id'])
                    unique_statuses.append(status)
            
            # Sort by creation time (most recent first)
            unique_statuses.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Return top limit posts
            return unique_statuses[:limit]
        except Exception as e:
            print(f"✗ Failed to search posts: {e}")
            return []
    
    def reply_to_status(self, status_id: int, content: str, 
                       visibility: str = 'public') -> Optional[Dict]:
        """
        Reply to a status on Mastodon
        
        Args:
            status_id: ID of the status to reply to
            content: Reply content (max 500 characters)
            visibility: 'public', 'unlisted', 'private', or 'direct'
        
        Returns:
            The created reply status dict, or None if failed
        """
        # Mastodon character limit is typically 500
        max_length = 500
        
        if len(content) > max_length:
            print(f"⚠ Warning: Reply content is {len(content)} characters, max is {max_length}")
            # Truncate at word boundary
            content = content[:max_length].rsplit(' ', 1)[0] + '...'
        
        try:
            reply = self.mastodon.status_post(
                content,
                in_reply_to_id=status_id,
                visibility=visibility
            )
            print(f"✓ Replied successfully! Reply ID: {reply['id']}")
            print(f"  URL: {reply['url']}")
            return reply
        except Exception as e:
            print(f"✗ Failed to reply: {e}")
            return None


def load_config(config_path: str = ".config/mastodon_config.json") -> dict:
    """Load Mastodon configuration from JSON file"""
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


def save_config(config: dict, config_path: str = "mastodon_config.json"):
    """Save Mastodon configuration to JSON file"""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"✓ Configuration saved to {config_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Post content to Mastodon from post_scripts folder"
    )
    parser.add_argument(
        'post_file',
        nargs='?',
        help='Path to post file (e.g., post_scripts/twitter_option1.md)'
    )
    parser.add_argument(
        '--instance',
        help='Mastodon instance URL (e.g., https://mastodon.social)'
    )
    parser.add_argument(
        '--access-token',
        help='Mastodon access token'
    )
    parser.add_argument(
        '--config',
        default='.config/mastodon_config.json',
        help='Path to config file (default: .config/mastodon_config.json)'
    )
    parser.add_argument(
        '--visibility',
        choices=['public', 'unlisted', 'private', 'direct'],
        default='public',
        help='Post visibility (default: public)'
    )
    parser.add_argument(
        '--spoiler',
        help='Content warning/spoiler text'
    )
    parser.add_argument(
        '--list-posts',
        action='store_true',
        help='List available post files'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify credentials only'
    )
    parser.add_argument(
        '--thread',
        action='store_true',
        help='Post as thread if content is long'
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Get instance URL
    instance_url = args.instance or config.get('instance_url') or os.getenv('MASTODON_INSTANCE_URL')
    if not instance_url:
        instance_url = input("Enter your Mastodon instance URL (e.g., https://mastodon.social): ").strip()
        if not instance_url:
            print("Error: Instance URL is required")
            sys.exit(1)
        config['instance_url'] = instance_url
        save_config(config, args.config)
    
    # Get access token
    access_token = args.access_token or config.get('access_token') or os.getenv('MASTODON_ACCESS_TOKEN')
    if not access_token:
        print("Error: Access token is required")
        print("You can provide it via:")
        print("  --access-token argument")
        print("  MASTODON_ACCESS_TOKEN environment variable")
        print("  .config/mastodon_config.json file")
        sys.exit(1)
    
    # Initialize agent
    agent = MastodonAgent(
        instance_url=instance_url,
        access_token=access_token,
        client_id=config.get('client_id'),
        client_secret=config.get('client_secret')
    )
    
    # Verify credentials
    if not agent.verify_credentials():
        sys.exit(1)
    
    if args.verify:
        print("✓ Credentials verified successfully!")
        return
    
    # List available posts
    if args.list_posts:
        post_scripts_dir = Path("post_scripts")
        if post_scripts_dir.exists():
            print("\nAvailable post files:")
            for post_file in sorted(post_scripts_dir.glob("*.md")):
                print(f"  - {post_file}")
        else:
            print("post_scripts directory not found")
        return
    
    # Post content
    if not args.post_file:
        print("Error: Post file is required")
        print("Use --list-posts to see available files")
        sys.exit(1)
    
    try:
        content = agent.read_post_file(args.post_file)
        print(f"\nContent to post ({len(content)} characters):")
        print("-" * 50)
        print(content[:200] + "..." if len(content) > 200 else content)
        print("-" * 50)
        
        # Check if we should post as thread
        if args.thread or len(content) > 450:
            parts = agent.split_thread_content(content)
            if len(parts) > 1:
                print(f"\nContent will be split into {len(parts)} parts")
                response = input("Post as thread? (y/n): ")
                if response.lower() == 'y':
                    agent.post_thread(parts, visibility=args.visibility)
                    return
        
        # Post single status
        response = input("\nPost this content? (y/n): ")
        if response.lower() == 'y':
            agent.post_status(
                content,
                visibility=args.visibility,
                spoiler_text=args.spoiler
            )
        else:
            print("Cancelled.")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
