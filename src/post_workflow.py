#!/usr/bin/env python3
"""
Automated Post Generation Workflow

This script orchestrates the complete workflow:
1. Pull product description from Notion
2. Generate social media posts using AI (OpenRouter)
3. Automatically publish to Mastodon
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict

# Get project root (parent of src directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Import our agents
# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# #region agent log
log_path = PROJECT_ROOT / ".cursor" / "debug.log"
try:
    # Ensure .cursor directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        import json as _json
        from datetime import datetime as _dt
        f.write(_json.dumps({"sessionId":"debug-session","runId":"run3","hypothesisId":"H3","location":"post_workflow.py:22","message":"script start","data":{"script_dir":str(Path(__file__).parent),"project_root":str(PROJECT_ROOT),"sys_path_first":sys.path[0] if sys.path else None,"cwd":os.getcwd(),"python_version":sys.version},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
except Exception as e:
    # Print error so we can see it
    print(f"Debug log init error: {e}", file=sys.stderr)
# #endregion

try:
    from notion_agent import NotionAgent, load_config as load_notion_config
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            import json as _json
            from datetime import datetime as _dt
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run3","hypothesisId":"H3","location":"post_workflow.py:34","message":"notion_agent imported","data":{},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
    except: pass
    # #endregion
except ImportError as e:
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            import json as _json
            from datetime import datetime as _dt
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run3","hypothesisId":"H3","location":"post_workflow.py:34","message":"notion_agent import failed","data":{"error":str(e)},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
    except: pass
    # #endregion
    raise

try:
    from openrouter_client import OpenRouterClient, load_config as load_openrouter_config
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            import json as _json
            from datetime import datetime as _dt
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run3","hypothesisId":"H3","location":"post_workflow.py:36","message":"openrouter_client imported","data":{},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
    except: pass
    # #endregion
except ImportError as e:
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            import json as _json
            from datetime import datetime as _dt
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run3","hypothesisId":"H3","location":"post_workflow.py:36","message":"openrouter_client import failed","data":{"error":str(e)},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
    except: pass
    # #endregion
    raise

try:
    from mastodon_agent import MastodonAgent, load_config as load_mastodon_config
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            import json as _json
            from datetime import datetime as _dt
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run3","hypothesisId":"H3","location":"post_workflow.py:38","message":"mastodon_agent imported","data":{},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
    except: pass
    # #endregion
except ImportError as e:
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            import json as _json
            from datetime import datetime as _dt
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run3","hypothesisId":"H3","location":"post_workflow.py:38","message":"mastodon_agent import failed","data":{"error":str(e)},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
    except: pass
    # #endregion
    raise


def load_workflow_config(config_path: str = ".config/workflow_config.json") -> dict:
    """Load workflow configuration from JSON file"""
    # Resolve config path relative to project root, not CWD
    if not Path(config_path).is_absolute():
        config_file = PROJECT_ROOT / config_path
    else:
        config_file = Path(config_path)
    
    # #region agent log
    try:
        log_path = PROJECT_ROOT / ".cursor" / "debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            import json as _json
            from datetime import datetime as _dt
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H1","location":"post_workflow.py:29","message":"load_workflow_config entry","data":{"config_path":config_path,"project_root":str(PROJECT_ROOT),"resolved_path":str(config_file.resolve()),"exists":config_file.exists(),"cwd":os.getcwd()},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
    except: pass
    # #endregion
    
    if not config_file.exists():
        print(f"Error: Workflow config file not found: {config_file}")
        print(f"Create {config_file} from .config/workflow_config.json.example")
        sys.exit(1)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)


class PostWorkflow:
    """Main workflow orchestrator"""
    
    def __init__(
        self,
        notion_api_token: str,
        openrouter_api_key: str,
        mastodon_instance_url: str,
        mastodon_access_token: str,
        openrouter_model: str = "openai/gpt-4o-mini"
    ):
        """
        Initialize the workflow
        
        Args:
            notion_api_token: Notion API token
            openrouter_api_key: OpenRouter API key
            mastodon_instance_url: Mastodon instance URL
            mastodon_access_token: Mastodon access token
            openrouter_model: Model to use for generation
        """
        self.notion_agent = NotionAgent(api_token=notion_api_token)
        self.openrouter_client = OpenRouterClient(
            api_key=openrouter_api_key,
            model=openrouter_model
        )
        self.mastodon_agent = MastodonAgent(
            instance_url=mastodon_instance_url,
            access_token=mastodon_access_token
        )
    
    def run(
        self,
        source_page_id: str,
        platforms: List[str],
        tone: str = "engaging",
        auto_publish: bool = False,
        mastodon_visibility: str = "public",
        mastodon_spoiler: Optional[str] = None
    ) -> Dict:
        """
        Run the complete workflow
        
        Args:
            source_page_id: Notion page ID containing product description
            platforms: List of platforms (twitter, linkedin, instagram, etc.)
            tone: Tone for posts (engaging, professional, casual, etc.)
            auto_publish: If True, publish without confirmation
            mastodon_visibility: Mastodon post visibility (public, unlisted, private, direct)
            mastodon_spoiler: Optional spoiler/content warning text
        
        Returns:
            Dictionary with workflow results
        """
        print("=" * 60)
        print("🚀 Starting Post Generation Workflow")
        print("=" * 60)
        
        results = {
            "source_page_id": source_page_id,
            "platforms": platforms,
            "generated_posts": {},
            "published_posts": {},
            "errors": []
        }
        
        # Step 1: Fetch product description from Notion
        print("\n📖 Step 1: Fetching product description from Notion...")
        print(f"   Source page ID: {source_page_id}")
        
        product_description = self.notion_agent.fetch_page_content(source_page_id)
        
        if not product_description:
            error = "Failed to fetch product description from Notion"
            print(f"✗ {error}")
            results["errors"].append(error)
            return results
        
        print(f"✓ Successfully fetched product description ({len(product_description)} characters)")
        print(f"\nPreview:")
        print("-" * 60)
        preview = product_description[:200] + "..." if len(product_description) > 200 else product_description
        print(preview)
        print("-" * 60)
        
        # Step 2: Generate posts for each platform
        print(f"\n🤖 Step 2: Generating posts using AI...")
        print(f"   Model: {self.openrouter_client.model}")
        print(f"   Platforms: {', '.join(platforms)}")
        print(f"   Tone: {tone}")
        
        generated_posts = {}
        
        for platform in platforms:
            print(f"\n   Generating {platform} post...")
            post = self.openrouter_client.generate_post(
                product_description=product_description,
                platform=platform,
                tone=tone
            )
            
            if post:
                generated_posts[platform] = post
                print(f"✓ Generated {platform} post ({len(post)} characters)")
                print(f"   Preview: {post[:100]}...")
            else:
                error = f"Failed to generate post for {platform}"
                print(f"✗ {error}")
                results["errors"].append(error)
        
        results["generated_posts"] = generated_posts
        
        if not generated_posts:
            print("\n✗ No posts were generated. Cannot proceed.")
            return results
        
        # Step 3: Publish to Mastodon (only if "mastodon" is in platforms)
        published_posts = {}
        
        if "mastodon" not in platforms:
            print(f"\nℹ️  Mastodon not in platforms list. Skipping Mastodon publishing.")
        else:
            print(f"\n📱 Step 3: Publishing posts to Mastodon...")
            print(f"   Instance: {self.mastodon_agent.instance_url}")
            print(f"   Visibility: {mastodon_visibility}")
            
            if not auto_publish:
                print("\nGenerated posts:")
                for platform, post_content in generated_posts.items():
                    print(f"\n{platform.upper()}:")
                    print("-" * 60)
                    print(post_content)
                    print("-" * 60)
                
                response = input("\nPublish all posts to Mastodon? (y/n): ")
                if response.lower() != 'y':
                    print("Publishing cancelled.")
                    # Continue to show summary even if publishing cancelled
                else:
                    # Only publish if user confirmed
                    for platform, post_content in generated_posts.items():
                        print(f"\n   Publishing {platform} post...")
                        
                        # Post to Mastodon
                        # For Mastodon, we'll post each platform's post as a separate status
                        status = self.mastodon_agent.post_status(
                            content=post_content,
                            visibility=mastodon_visibility,
                            spoiler_text=mastodon_spoiler
                        )
                        
                        if status:
                            published_posts[platform] = {
                                "status_id": status.get("id"),
                                "url": status.get("url"),
                                "platform": platform
                            }
                            print(f"✓ Published {platform} post")
                            print(f"   URL: {status.get('url')}")
                        else:
                            error = f"Failed to publish {platform} post"
                            print(f"✗ {error}")
                            results["errors"].append(error)
            else:
                # Auto-publish mode
                for platform, post_content in generated_posts.items():
                    print(f"\n   Publishing {platform} post...")
                    
                    status = self.mastodon_agent.post_status(
                        content=post_content,
                        visibility=mastodon_visibility,
                        spoiler_text=mastodon_spoiler
                    )
                    
                    if status:
                        published_posts[platform] = {
                            "status_id": status.get("id"),
                            "url": status.get("url"),
                            "platform": platform
                        }
                        print(f"✓ Published {platform} post")
                        print(f"   URL: {status.get('url')}")
                    else:
                        error = f"Failed to publish {platform} post"
                        print(f"✗ {error}")
                        results["errors"].append(error)
        
        results["published_posts"] = published_posts
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Workflow Complete!")
        print("=" * 60)
        print(f"Generated posts: {len(generated_posts)}/{len(platforms)}")
        if "mastodon" in platforms:
            print(f"Published posts: {len(published_posts)}/{len(generated_posts)}")
        else:
            print(f"Published posts: 0 (Mastodon not in platforms)")
        
        if results["errors"]:
            print(f"\n⚠️ Errors: {len(results['errors'])}")
            for error in results["errors"]:
                print(f"  - {error}")
        
        return results


def main():
    # Load workflow config
    workflow_config_path = ".config/workflow_config.json"
    
    # Resolve config path relative to project root
    config_file = PROJECT_ROOT / workflow_config_path
    
    # #region agent log
    try:
        log_path = PROJECT_ROOT / ".cursor" / "debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            import json as _json
            from datetime import datetime as _dt
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run2-post-fix","hypothesisId":"H1,H2","location":"post_workflow.py:220","message":"main entry post-fix","data":{"workflow_config_path":workflow_config_path,"cwd":os.getcwd(),"script_path":str(Path(__file__).resolve()),"project_root":str(PROJECT_ROOT),"resolved_config":str(config_file),"config_exists":config_file.exists()},"timestamp":int(_dt.now().timestamp()*1000)})+'\n')
    except Exception as e:
        print(f"Debug log error: {e}")
    # #endregion
    
    if not config_file.exists():
        print(f"Error: Workflow config file not found: {config_file}")
        print(f"Please create {workflow_config_path} from .config/workflow_config.json.example")
        print("\nExample workflow_config.json:")
        print(json.dumps({
            "source_page_id": "your-notion-page-id",
            "platforms": ["twitter", "linkedin"],
            "tone": "engaging",
            "mastodon": {
                "enabled": True,
                "visibility": "public"
            },
            "auto_publish": False
        }, indent=2))
        sys.exit(1)
    
    workflow_config = load_workflow_config(workflow_config_path)
    
    # Load other configs
    notion_config = load_notion_config()
    openrouter_config = load_openrouter_config()
    mastodon_config = load_mastodon_config()
    
    # Get credentials
    notion_api_token = (
        notion_config.get('api_token') or
        os.getenv('NOTION_API_TOKEN')
    )
    
    openrouter_api_key = (
        openrouter_config.get('api_key') or
        os.getenv('OPENROUTER_API_KEY')
    )
    
    mastodon_instance_url = (
        mastodon_config.get('instance_url') or
        os.getenv('MASTODON_INSTANCE_URL')
    )
    
    mastodon_access_token = (
        mastodon_config.get('access_token') or
        os.getenv('MASTODON_ACCESS_TOKEN')
    )
    
    # Validate credentials
    if not notion_api_token:
        print("Error: Notion API token is required")
        print("Set it in .config/notion_config.json or NOTION_API_TOKEN environment variable")
        sys.exit(1)
    
    if not openrouter_api_key:
        print("Error: OpenRouter API key is required")
        print("Set it in .config/openrouter_config.json or OPENROUTER_API_KEY environment variable")
        sys.exit(1)
    
    # Get workflow settings first (need platforms to check if mastodon is needed)
    source_page_id = workflow_config.get('source_page_id')
    platforms = workflow_config.get('platforms', ['twitter', 'linkedin', 'instagram'])
    tone = workflow_config.get('tone', 'engaging')
    # Get openrouter_model from openrouter_config.json (not workflow_config.json)
    openrouter_model = (
        openrouter_config.get('model') 
    )
    auto_publish = workflow_config.get('auto_publish', False)
    
    mastodon_settings = workflow_config.get('mastodon', {})
    mastodon_visibility = mastodon_settings.get('visibility', 'public')
    mastodon_spoiler = mastodon_settings.get('spoiler_text')
    
    if not source_page_id:
        print("Error: source_page_id is required in workflow_config.json")
        sys.exit(1)
    
    # Check if Mastodon is in platforms - only require credentials if it is
    if "mastodon" in platforms:
        if not mastodon_instance_url:
            print("Error: Mastodon instance URL is required (mastodon is in platforms)")
            print("Set it in .config/mastodon_config.json or MASTODON_INSTANCE_URL environment variable")
            sys.exit(1)
        
        if not mastodon_access_token:
            print("Error: Mastodon access token is required (mastodon is in platforms)")
            print("Set it in .config/mastodon_config.json or MASTODON_ACCESS_TOKEN environment variable")
            sys.exit(1)
    else:
        # Mastodon not in platforms - use defaults if credentials not set
        if not mastodon_instance_url:
            mastodon_instance_url = "https://mastodon.social"  # Default fallback
        if not mastodon_access_token:
            mastodon_access_token = ""  # Empty string - won't be used
        print("ℹ️  Note: 'mastodon' is not in platforms list. Posts will be generated but not published to Mastodon.")
        print("   Add 'mastodon' to the platforms array if you want to publish to Mastodon.\n")
    
    # Initialize workflow
    # Only initialize Mastodon agent if "mastodon" is in platforms
    if "mastodon" in platforms:
        workflow = PostWorkflow(
            notion_api_token=notion_api_token,
            openrouter_api_key=openrouter_api_key,
            mastodon_instance_url=mastodon_instance_url,
            mastodon_access_token=mastodon_access_token,
            openrouter_model=openrouter_model
        )
        
        # Verify credentials (optional check)
        print("Verifying credentials...")
        notion_ok = workflow.notion_agent.verify_credentials()
        openrouter_ok = workflow.openrouter_client.verify_credentials()
        mastodon_ok = workflow.mastodon_agent.verify_credentials()
        
        if not (notion_ok and openrouter_ok and mastodon_ok):
            print("\n✗ Some credentials failed verification. Please check your config files.")
            sys.exit(1)
        
        print("\n✓ All credentials verified successfully!\n")
    else:
        # If Mastodon not in platforms, we don't need Mastodon credentials
        # But we still need a dummy workflow object - let's create it without Mastodon agent
        # Actually, we need to still create the workflow but it won't publish to Mastodon
        # Let me check if we can make Mastodon agent optional... 
        # For now, let's still require it but skip verification
        workflow = PostWorkflow(
            notion_api_token=notion_api_token,
            openrouter_api_key=openrouter_api_key,
            mastodon_instance_url=mastodon_instance_url,
            mastodon_access_token=mastodon_access_token,
            openrouter_model=openrouter_model
        )
        
        # Verify credentials (skip Mastodon if not in platforms)
        print("Verifying credentials...")
        notion_ok = workflow.notion_agent.verify_credentials()
        openrouter_ok = workflow.openrouter_client.verify_credentials()
        # Skip Mastodon verification if not in platforms
        mastodon_ok = True  # Assume OK since we won't publish anyway
        
        if not (notion_ok and openrouter_ok):
            print("\n✗ Some credentials failed verification. Please check your config files.")
            sys.exit(1)
        
        print("\n✓ All credentials verified successfully!\n")
    
    # Run workflow
    results = workflow.run(
        source_page_id=source_page_id,
        platforms=platforms,
        tone=tone,
        auto_publish=auto_publish,
        mastodon_visibility=mastodon_visibility,
        mastodon_spoiler=mastodon_spoiler
    )
    
    # Exit with error code if there were errors
    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
