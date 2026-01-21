#!/usr/bin/env python3
"""
OpenRouter API Client for AI-powered post generation

This module provides a client for generating social media posts using OpenRouter's AI models.
"""

import os
import sys
import json
import re
from typing import Optional, Dict, List
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


class OpenRouterClient:
    """Client for interacting with OpenRouter API"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    # Platform-specific character limits
    PLATFORM_LIMITS = {
        "mastodon": 500,
        "twitter": 280,
        "instagram": 2200,
        "linkedin": 3000,
        "facebook": 5000
    }
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        """
        Initialize OpenRouter client
        
        Args:
            api_key: Your OpenRouter API key
            model: Model identifier (default: openai/gpt-4o-mini)
        """
        if requests is None:
            raise ImportError(
                "requests library not found. Install it with:\n"
                "  uv sync\n"
                "  or: pip install requests"
            )
        
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/dailytoparxiv/post_generation",
            "X-Title": "Post Generation Tool"
        }
    
    def _extract_post_from_markers(self, content: str) -> Optional[str]:
        """
        Extract post content from between XML-style marker tags (<POST_START> and <POST_END>).
        This is the primary extraction method based on explicit markers.
        
        Supports multiple marker formats:
        - XML-style tags: <POST_START>content<POST_END>
        - Legacy format: =========================\ncontent\n=========================
        
        Args:
            content: Content that may contain marked post
            
        Returns:
            Extracted post content, or None if markers not found
        """
        if not content:
            return None
        
        # Primary method: XML-style tags (<POST_START> and <POST_END>)
        # Handle both single-line and multi-line formats
        patterns = [
            # Multi-line format: <POST_START>\ncontent\n<POST_END>
            r'<POST_START>\s*\n(.*?)\n\s*<POST_END>',
            # Single-line format: <POST_START>content<POST_END>
            r'<POST_START>(.*?)<POST_END>',
            # Case-insensitive variants
            r'<post_start>\s*\n(.*?)\n\s*<post_end>',
            r'<post_start>(.*?)<post_end>',
            # Legacy format: =========================\ncontent\n=========================
            r'={10,}\s*\n(.*?)\n\s*={10,}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    # Clean up any remaining marker artifacts
                    extracted = self._remove_marker_artifacts(extracted)
                    return extracted
        
        # Fallback: Try to remove any marker lines that might be present
        # This handles cases where markers are mixed with content
        cleaned = self._remove_marker_artifacts(content)
        if cleaned != content:
            return cleaned
        
        return None
    
    def _remove_marker_artifacts(self, content: str) -> str:
        """
        Remove any marker artifacts from content (tags, equal signs, etc.)
        
        Args:
            content: Content that may contain marker artifacts
            
        Returns:
            Cleaned content without marker artifacts
        """
        if not content:
            return ""
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip XML-style marker tags
            if re.match(r'^<POST_(START|END)>$', stripped, re.IGNORECASE):
                continue
            # Skip lines that are just equal signs (legacy markers)
            if re.match(r'^={10,}$', stripped):
                continue
            # Remove marker tags if they appear inline with content
            line = re.sub(r'<POST_(START|END)>', '', line, flags=re.IGNORECASE)
            # Remove trailing/leading equal signs that might be decorative
            line = re.sub(r'^={3,}\s+|\s+={3,}$', '', line)
            cleaned_lines.append(line)
        
        cleaned = '\n'.join(cleaned_lines).strip()
        
        # Remove any remaining marker patterns from the entire content
        cleaned = re.sub(r'<POST_(START|END)>', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n\s*={10,}\s*\n', '\n', cleaned)
        
        return cleaned
    
    def _extract_post_from_reasoning(self, reasoning: str) -> str:
        """
        Extract the actual post content from reasoning field.
        Reasoning models often include their reasoning process - we want just the final post.
        
        Args:
            reasoning: The reasoning field content
            
        Returns:
            Extracted post content
        """
        if not reasoning:
            return ""
        
        # First try to extract from markers
        marked_content = self._extract_post_from_markers(reasoning)
        if marked_content:
            return marked_content
        
        # Try to find patterns that indicate where the actual post starts
        patterns = [
            r"(?:Here'?s the (?:post|social media post)[:])",
            r"(?:Generated (?:post|social media post)[:])",
            r"(?:Post[:])",
            r"(?:Social media post[:])",
            r"(?:The (?:post|social media post) (?:is|would be)[:])",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, reasoning, re.IGNORECASE)
            if match:
                extracted = reasoning[match.end():].strip()
                # Remove any remaining prompt-like text
                extracted = re.sub(
                    r'^(?:Product Description|Requirements|Platform|Tone|Based on).*?(\n|$)',
                    '',
                    extracted,
                    flags=re.IGNORECASE | re.MULTILINE
                )
                if extracted:
                    return extracted
        
        # If no pattern found, try to find the last substantial paragraph
        parts = re.split(r'\n\n+|\n(?=[A-Z][a-z])', reasoning)
        for part in reversed(parts):
            part = part.strip()
            # Skip if it looks like part of the prompt or reasoning
            if part and not re.search(
                r'^(Product Description|Requirements|Platform|Tone|Based on|I (?:will|need|should|can))',
                part,
                re.IGNORECASE
            ):
                # Check if it looks like actual post content
                if 50 < len(part) < 2000:
                    return part
        
        # Fallback: return the reasoning as-is
        return reasoning.strip()
    
    def _clean_content(self, content: str) -> str:
        """
        Clean up content by removing prompt artifacts.
        
        Args:
            content: Raw content to clean
            
        Returns:
            Cleaned content
        """
        if not content:
            return ""
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip lines that look like prompt parts
            if not re.search(
                r'^(Product Description|Requirements|Platform|Tone|Maximum length|Based on the following|Generate the social media post)',
                line,
                re.IGNORECASE
            ):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _enforce_length_limit(self, content: str, platform: str) -> str:
        """
        Enforce platform-specific length limits.
        
        Args:
            content: Content to limit
            platform: Platform name
            
        Returns:
            Content truncated to platform limit if necessary
        """
        platform_key = platform.lower()
        max_len = self.PLATFORM_LIMITS.get(platform_key)
        
        if max_len and len(content) > max_len:
            # Truncate at word boundary
            truncated = content[:max_len].rsplit(' ', 1)[0]
            # Add ellipsis only if we actually truncated
            if len(content) > len(truncated):
                return truncated + '...'
            return truncated
        
        return content
    
    def generate_post(
        self,
        product_description: str,
        platform: str = "general",
        tone: str = "engaging",
        max_length: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate a social media post from a product description
        
        Args:
            product_description: The product description to base the post on
            platform: Target platform (twitter, linkedin, instagram, etc.)
            tone: Post tone (engaging, professional, casual, etc.)
            max_length: Maximum length in characters (optional)
        
        Returns:
            Generated post content
        """
        if not product_description:
            print(f"✗ Error: product_description is empty or None for {platform}")
            return None
        
        # Build platform-specific prompts
        platform_prompts = {
            "twitter": "Write a Twitter/X post (max 280 characters, engaging and concise)",
            "linkedin": "Write a LinkedIn post (professional, longer-form, engaging)",
            "instagram": "Write an Instagram caption (visual-friendly, engaging, use emojis sparingly)",
            "facebook": "Write a Facebook post (friendly, engaging, conversational)",
            "mastodon": "Write a Mastodon post (similar to Twitter but up to 500 characters, engaging and community-focused)",
            "general": "Write a social media post (engaging and well-structured)"
        }
        
        platform_prompt = platform_prompts.get(platform.lower(), platform_prompts["general"])
        
        # Build the full prompt
        prompt = f"""Based on the following product description, generate a social media post.

Product Description:
{product_description}

Requirements:
- Platform: {platform_prompt}
- Tone: {tone}
{f"- Maximum length: {max_length} characters" if max_length else ""}
- Make it engaging and compelling
- Include a clear call-to-action
- Use appropriate formatting (hashtags for Twitter/Instagram, but not LinkedIn)
- Keep it authentic and natural

IMPORTANT: Place your generated post content between XML-style tags, like this:

<POST_START>
[Your post content here]
<POST_END>

Generate the social media post:"""

        request_data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            #"max_tokens": 500 if max_length is None else min(max_length // 2, 500),
            # Disable reasoning mode - exclude reasoning field from response
            # This prevents models from returning reasoning/breakdown instead of content
            #"reasoning": {
            #    "exclude": True
            #}
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=request_data,
                timeout=30
            )
            
            if response.status_code >= 400:
                print(f"✗ API returned error status {response.status_code}")
                try:
                    error_body = response.json()
                    print(f"  Error details: {error_body}")
                except:
                    print(f"  Response text: {response.text[:200]}")
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the generated text
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0]["message"]
                content = message.get("content", "")
                
                # If content is empty, check reasoning field (some reasoning models use it)
                if not content:
                    reasoning = message.get("reasoning", "")
                    if reasoning:
                        print(f"✗ reasoning mode for {platform}")
                        content = self._extract_post_from_reasoning(reasoning)
                
                if not content:
                    refusal = message.get("refusal", "")
                    if refusal:
                        print(f"✗ API refused to generate content for {platform}: {refusal[:200]}")
                    else:
                        print(f"✗ API returned empty content for {platform}")
                    return None
                
                # First try to extract from markers (primary extraction method)
                marked_content = self._extract_post_from_markers(content)
                if marked_content:
                    content = marked_content
                else:
                    # Fallback to cleaning if no markers found
                    # Also try to remove any marker artifacts that might be present
                    content = self._clean_content(content)
                    content = self._remove_marker_artifacts(content)
                
                # Enforce length limit
                content = self._enforce_length_limit(content, platform)
                
                if not content:
                    print(f"✗ Content became empty after cleaning for {platform}")
                    return None
                
                return content
            else:
                print(f"✗ Unexpected response format: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to generate post for {platform}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"  Error details: {error_detail}")
                except:
                    print(f"  Status code: {e.response.status_code}")
                    if hasattr(e.response, 'text'):
                        print(f"  Response text: {e.response.text[:200]}")
            return None
        except Exception as e:
            print(f"✗ Unexpected error generating post for {platform}: {type(e).__name__}: {e}")
            import traceback
            print(f"  Traceback:\n{traceback.format_exc()}")
            return None
    
    def verify_credentials(self) -> bool:
        """
        Verify that API credentials are valid
        
        Returns:
            True if credentials are valid
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/models",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            print(f"✓ Connected to OpenRouter successfully!")
            print(f"  Using model: {self.model}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to verify credentials: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    print("  Error: Invalid API key")
                    print("  Get your API key from: https://openrouter.ai/keys")
                else:
                    print(f"  Status code: {e.response.status_code}")
            return False


def load_config(config_path: str = ".config/openrouter_config.json") -> dict:
    """Load OpenRouter configuration from JSON file"""
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


def save_config(config: dict, config_path: str = ".config/openrouter_config.json"):
    """Save OpenRouter configuration to JSON file"""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"✓ Configuration saved to {config_path}")


if __name__ == "__main__":
    # Simple test/demo
    import argparse
    
    parser = argparse.ArgumentParser(description="Test OpenRouter client")
    parser.add_argument('--api-key', help='OpenRouter API key')
    parser.add_argument('--config', default='.config/openrouter_config.json', help='Config file path')
    parser.add_argument('--verify', action='store_true', help='Verify credentials only')
    parser.add_argument('--model', default='openai/gpt-4o-mini', help='Model to use')
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    api_key = args.api_key or config.get('api_key') or os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("Error: OpenRouter API key is required")
        print("You can provide it via:")
        print("  --api-key argument")
        print("  OPENROUTER_API_KEY environment variable")
        print("  .config/openrouter_config.json file")
        print("\nGet your API key from: https://openrouter.ai/keys")
        sys.exit(1)
    
    client = OpenRouterClient(api_key=api_key, model=args.model)
    
    if args.verify:
        if not client.verify_credentials():
            sys.exit(1)
        print("\n✓ All checks passed!")
    else:
        # Demo generation
        test_description = "DailyTopArxiv is a personalized academic paper feed that makes discovering research papers as easy as scrolling TikTok. Swipe through papers, get personalized recommendations, and stay up-to-date with the latest research."
        print("Generating test post...")
        post = client.generate_post(test_description, platform="twitter", tone="engaging")
        if post:
            print("\nGenerated post:")
            print("-" * 50)
            print(post)
            print("-" * 50)
