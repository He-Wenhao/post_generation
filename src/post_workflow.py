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
import asyncio
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

# Optional import for Telegram approval
try:
    from telegram_agent import TelegramApprovalAgent, load_config as load_telegram_config
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    load_telegram_config = None

# Optional import for image generation
try:
    from generate_figure import generate_image, load_config as load_replicate_config
    IMAGE_GEN_AVAILABLE = True
except ImportError:
    IMAGE_GEN_AVAILABLE = False
    generate_image = None
    load_replicate_config = None

# Optional import for local RAG context
try:
    from arxiv_rag import ArxivAbstractRAG
    RAG_AVAILABLE = True
except ImportError:
    ArxivAbstractRAG = None
    RAG_AVAILABLE = False


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
        openrouter_model: str = "openai/gpt-4o-mini",
        telegram_agent: Optional[object] = None
    ):
        """
        Initialize the workflow
        
        Args:
            notion_api_token: Notion API token
            openrouter_api_key: OpenRouter API key
            mastodon_instance_url: Mastodon instance URL
            mastodon_access_token: Mastodon access token
            openrouter_model: Model to use for generation
            telegram_agent: Optional TelegramApprovalAgent instance for Telegram approval
        """
        self.notion_agent = NotionAgent(api_token=notion_api_token)
        self._openrouter_api_key = openrouter_api_key
        self.openrouter_client = OpenRouterClient(
            api_key=openrouter_api_key,
            model=openrouter_model
        )
        self.mastodon_agent = MastodonAgent(
            instance_url=mastodon_instance_url,
            access_token=mastodon_access_token
        )
        self.telegram_agent = telegram_agent
    
    def _extract_keywords(self, description: str) -> List[str]:
        """
        Extract keywords from product description.
        Simple implementation - can be enhanced with NLP libraries.
        
        Args:
            description: Product description text
        
        Returns:
            List of keywords
        """
        import re
        
        # Convert to lowercase
        text = description.lower()
        
        # Remove common stop words (simple list)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'it', 'its', 'they', 'them', 'their', 'there',
            'here', 'where', 'what', 'who', 'which', 'how', 'why', 'when'
        }
        
        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b[a-z]+\b', text)
        
        # Filter out stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Get unique keywords, sorted by frequency
        from collections import Counter
        word_counts = Counter(keywords)
        
        # Return top keywords (most frequent first)
        return [word for word, count in word_counts.most_common(10)]
    
    def run(
        self,
        source_page_id: str,
        mode: str = "post",
        platforms: List[str] = None,
        tone: str = "engaging",
        auto_publish: bool = False,
        mastodon_visibility: str = "public",
        mastodon_spoiler: Optional[str] = None,
        approval_mode: str = "cmd"
    ) -> Dict:
        """
        Run the complete workflow
        
        Args:
            source_page_id: Notion page ID containing product description
            mode: Workflow mode - "post" (generate and publish posts) or "reply" (find and reply to posts)
            platforms: List of platforms (twitter, linkedin, instagram, etc.) - only used in "post" mode
            tone: Tone for posts (engaging, professional, casual, etc.)
            auto_publish: If True, publish without confirmation - used in both "post" and "reply" modes
            mastodon_visibility: Mastodon post visibility (public, unlisted, private, direct)
            mastodon_spoiler: Optional spoiler/content warning text - only used in "post" mode
            approval_mode: Approval method - "cmd" (command line) or "telegram" (Telegram bot)
        
        Returns:
            Dictionary with workflow results
        """
        if mode not in ["post", "reply"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'post' or 'reply'")
        
        if approval_mode not in ["cmd", "telegram"]:
            raise ValueError(f"Invalid approval_mode: {approval_mode}. Must be 'cmd' or 'telegram'")
        
        if approval_mode == "telegram" and not self.telegram_agent:
            raise ValueError("Telegram approval mode requires telegram_agent to be initialized")
        
        if mode == "post":
            return self._run_post_mode(
                source_page_id, platforms or [], tone, 
                auto_publish, mastodon_visibility, mastodon_spoiler, approval_mode
            )
        else:  # mode == "reply"
            return self._run_reply_mode(
                source_page_id, tone, auto_publish, mastodon_visibility, approval_mode
            )
    
    def _run_post_mode(
        self,
        source_page_id: str,
        platforms: List[str],
        tone: str,
        auto_publish: bool,
        mastodon_visibility: str,
        mastodon_spoiler: Optional[str],
        approval_mode: str
    ) -> Dict:
        """
        Run workflow in post mode: generate and publish posts
        
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
        print("🚀 Starting Post Generation Workflow (Mode: POST)")
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

        # Step 1.5: Retrieve RAG context from local arxiv abstracts (optional)
        rag_context = None
        rag_hits = []
        try:
            rag_enabled = os.getenv("RAG_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
            rag_semantic = os.getenv("RAG_SEMANTIC", "0").strip().lower() in {"1", "true", "yes"}
            rag_top_k = int(os.getenv("RAG_TOP_K", "8"))
            rag_max_chars = int(os.getenv("RAG_MAX_CHARS", "4000"))
            rag_embed_model = os.getenv("RAG_EMBED_MODEL", "openai/text-embedding-3-small")

            docs_dir = PROJECT_ROOT / "arxiv-abstracts"
            if rag_enabled and RAG_AVAILABLE and docs_dir.exists() and any(docs_dir.glob("*.md")):
                print("\n📚 Step 1.5: Retrieving RAG context from arxiv-abstracts...")
                rag = ArxivAbstractRAG(
                    project_root=PROJECT_ROOT,
                    openrouter_api_key=self._openrouter_api_key,
                    enable_semantic=rag_semantic,
                    embedding_model=rag_embed_model,
                )
                rag.ensure_index()
                keywords = self._extract_keywords(product_description)
                rag_query = " ".join(keywords[:8]).strip() if keywords else product_description[:300]
                rag_context, rag_hits = rag.retrieve(
                    rag_query,
                    top_k=rag_top_k,
                    max_chars=rag_max_chars,
                )
                if rag_context:
                    print(f"✓ Retrieved RAG context ({len(rag_context)} characters)")
                    # Print which files were retrieved (requested for cmd runs)
                    if approval_mode == "cmd" and rag_hits:
                        seen = set()
                        files = []
                        for h in rag_hits:
                            f = getattr(h, "source_file", None)
                            if f and f not in seen:
                                seen.add(f)
                                files.append(f)
                        if files:
                            print(f"   Retrieved from files ({len(files)}): {', '.join(files)}")
                else:
                    print("ℹ️  No relevant RAG context found (continuing without it)")
        except Exception as e:
            print(f"⚠ RAG retrieval failed (continuing without it): {type(e).__name__}: {e}")
        
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
                tone=tone,
                rag_context=rag_context,
            )
            
            if post:
                generated_posts[platform] = post
                print(f"✓ Generated {platform} post ({len(post)} characters)")
                print(f"   Preview: {post[:100]}...")
            else:
                error = f"Failed to generate post for {platform}"
                print(f"✗ {error}")
                results["errors"].append(error)
        
        if not generated_posts:
            print("\n✗ No posts were generated. Cannot proceed.")
            return results
        
        # Step 2.5: Review and approve/regenerate posts
        print("\n📝 Step 2.5: Review and approve posts...")
        print(f"   Approval mode: {approval_mode}")
        approved_posts = {}
        
        for platform in platforms:
            if platform not in generated_posts:
                continue  # Skip if generation failed
            
            current_post = generated_posts[platform]
            
            while True:
                if approval_mode == "cmd":
                    # Command-line approval
                    print(f"\n{platform.upper()} Post:")
                    print("-" * 60)
                    print(current_post)
                    print("-" * 60)
                    
                    response = input(f"Accept this {platform} post or regenerate? (a/r): ").lower().strip()
                    
                    if response == 'a':
                        # Store post with structure for image attachment
                        approved_posts[platform] = {
                            'content': current_post,
                            'image_path': None
                        }
                        print(f"✓ Accepted {platform} post")
                        break
                    elif response == 'r':
                        print(f"\n   Regenerating {platform} post...")
                        new_post = self.openrouter_client.generate_post(
                            product_description=product_description,
                            platform=platform,
                            tone=tone,
                            rag_context=rag_context,
                        )
                        
                        if new_post:
                            current_post = new_post
                            print(f"✓ Regenerated {platform} post ({len(new_post)} characters)")
                        else:
                            error = f"Failed to regenerate post for {platform}"
                            print(f"✗ {error}")
                            results["errors"].append(error)
                            print("   Keeping previous version. Please try again.")
                    else:
                        print("Invalid input. Please enter 'a' to accept or 'r' to regenerate.")
                
                else:  # approval_mode == "telegram"
                    # Telegram approval with inline regeneration
                    async def regenerate_post():
                        """Async wrapper for post regeneration"""
                        print(f"\n   Regenerating {platform} post...")
                        # Run synchronous generate_post in thread pool
                        loop = asyncio.get_event_loop()
                        new_post = await loop.run_in_executor(
                            None,
                            lambda: self.openrouter_client.generate_post(
                                product_description=product_description,
                                platform=platform,
                                tone=tone,
                                rag_context=rag_context,
                            )
                        )
                        
                        if new_post:
                            print(f"✓ Regenerated {platform} post ({len(new_post)} characters)")
                            return new_post
                        else:
                            error = f"Failed to regenerate post for {platform}"
                            print(f"✗ {error}")
                            results["errors"].append(error)
                            return None
                    
                    decision = asyncio.run(
                        self.telegram_agent.wait_for_post_approval(
                            platform=platform,
                            post_content=current_post,
                            regenerate_callback=regenerate_post
                        )
                    )
                    
                    if decision == "accept":
                        # Get the final content from the agent (may have been regenerated)
                        final_post = self.telegram_agent.final_content or current_post
                        # Store post with structure for image attachment
                        approved_posts[platform] = {
                            'content': final_post,
                            'image_path': None
                        }
                        current_post = final_post  # Update for consistency
                        print(f"✓ Accepted {platform} post via Telegram")
                        break
                    elif decision == "regenerate":
                        # This shouldn't happen if regenerate_callback is used,
                        # but handle it just in case
                        print(f"\n   Regenerating {platform} post (fallback)...")
                        new_post = self.openrouter_client.generate_post(
                            product_description=product_description,
                            platform=platform,
                            tone=tone,
                            rag_context=rag_context,
                        )
                        
                        if new_post:
                            current_post = new_post
                            print(f"✓ Regenerated {platform} post ({len(new_post)} characters)")
                        else:
                            error = f"Failed to regenerate post for {platform}"
                            print(f"✗ {error}")
                            results["errors"].append(error)
                            print("   Keeping previous version. Please try again.")
        
        results["generated_posts"] = approved_posts
        
        if not approved_posts:
            print("\n✗ No posts were approved. Cannot proceed.")
            return results
        
        # Step 2.6: Generate images for approved posts
        if IMAGE_GEN_AVAILABLE and "mastodon" in platforms:
            print("\n🎨 Step 2.6: Generating images for posts...")
            
            # Load replicate config
            replicate_config = {}
            if load_replicate_config:
                replicate_config = load_replicate_config()
            
            for platform in platforms:
                if platform not in approved_posts:
                    continue
                
                post_data = approved_posts[platform]
                post_content = post_data.get('content') if isinstance(post_data, dict) else post_data
                
                if not post_content:
                    continue
                
                try:
                    print(f"\n   Generating image for {platform} post...")
                    print(f"   Using post content as prompt...")
                    
                    # Use post content as prompt for image generation
                    image_result = generate_image(
                        prompt=post_content,
                        config=replicate_config,
                        download=True
                    )
                    
                    if 'file_path' in image_result:
                        # Update approved_posts with image path
                        if isinstance(approved_posts[platform], dict):
                            approved_posts[platform]['image_path'] = image_result['file_path']
                        else:
                            # Convert to dict structure
                            approved_posts[platform] = {
                                'content': approved_posts[platform],
                                'image_path': image_result['file_path']
                            }
                        print(f"✓ Generated and saved image: {image_result['file_path']}")
                    else:
                        print(f"⚠ Image generation completed but file not downloaded")
                        print(f"   Image URL: {image_result.get('url', 'N/A')}")
                except Exception as e:
                    print(f"✗ Failed to generate image for {platform}: {e}")
                    # Continue without image
                    if not isinstance(approved_posts[platform], dict):
                        approved_posts[platform] = {
                            'content': approved_posts[platform],
                            'image_path': None
                        }
        
        # Step 3: Publish to Mastodon (only if "mastodon" is in platforms)
        published_posts = {}
        
        if "mastodon" not in platforms:
            print(f"\nℹ️  Mastodon not in platforms list. Skipping Mastodon publishing.")
        else:
            print(f"\n📱 Step 3: Publishing posts to Mastodon...")
            print(f"   Instance: {self.mastodon_agent.instance_url}")
            print(f"   Visibility: {mastodon_visibility}")
            
            if not auto_publish:
                if approval_mode == "cmd":
                    print("\nApproved posts:")
                    for platform, post_data in approved_posts.items():
                        # Extract post content
                        post_content = post_data.get('content') if isinstance(post_data, dict) else post_data
                        image_path = post_data.get('image_path') if isinstance(post_data, dict) else None
                        
                        print(f"\n{platform.upper()}:")
                        print("-" * 60)
                        print(post_content)
                        if image_path:
                            print(f"\n[Image: {image_path}]")
                        print("-" * 60)
                    
                    response = input("\nPublish all posts to Mastodon? (y/n): ")
                    should_publish = response.lower() == 'y'
                else:  # approval_mode == "telegram"
                    # Telegram approval
                    should_publish = asyncio.run(
                        self.telegram_agent.wait_for_publish_approval(
                            posts=approved_posts
                        )
                    )
                
                if not should_publish:
                    print("Publishing cancelled.")
                    # Continue to show summary even if publishing cancelled
                else:
                    # Only publish if user confirmed
                    for platform, post_data in approved_posts.items():
                        print(f"\n   Publishing {platform} post...")
                        
                        # Extract post content and image path
                        if isinstance(post_data, dict):
                            post_content = post_data.get('content', '')
                            image_path = post_data.get('image_path')
                        else:
                            # Backward compatibility
                            post_content = post_data
                            image_path = None
                        
                        # Upload image if available
                        media_ids = None
                        if image_path and Path(image_path).exists():
                            print(f"   Uploading image: {image_path}")
                            media = self.mastodon_agent.upload_media(
                                file_path=image_path,
                                description=f"Image for {platform} post"
                            )
                            if media:
                                media_ids = [media['id']]
                                print(f"✓ Image uploaded successfully")
                        
                        # Post to Mastodon
                        status = self.mastodon_agent.post_status(
                            content=post_content,
                            visibility=mastodon_visibility,
                            spoiler_text=mastodon_spoiler,
                            media_ids=media_ids
                        )
                        
                        if status:
                            published_posts[platform] = {
                                "status_id": status.get("id"),
                                "url": status.get("url"),
                                "platform": platform
                            }
                            print(f"✓ Published {platform} post")
                            print(f"   URL: {status.get('url')}")
                            
                            # Send confirmation via Telegram if available
                            if self.telegram_agent and approval_mode == "telegram":
                                post_url = status.get('url', 'N/A')
                                confirmation_msg = (
                                    f"✅ Post Published Successfully!\n\n"
                                    f"Platform: {platform.upper()}\n"
                                    f"URL: {post_url}\n\n"
                                )
                                self.telegram_agent.send_confirmation_sync(confirmation_msg)
                        else:
                            error = f"Failed to publish {platform} post"
                            print(f"✗ {error}")
                            results["errors"].append(error)
            else:
                # Auto-publish mode
                for platform, post_data in approved_posts.items():
                    print(f"\n   Publishing {platform} post...")
                    
                    # Extract post content and image path
                    if isinstance(post_data, dict):
                        post_content = post_data.get('content', '')
                        image_path = post_data.get('image_path')
                    else:
                        # Backward compatibility
                        post_content = post_data
                        image_path = None
                    
                    # Upload image if available
                    media_ids = None
                    if image_path and Path(image_path).exists():
                        print(f"   Uploading image: {image_path}")
                        media = self.mastodon_agent.upload_media(
                            file_path=image_path,
                            description=f"Image for {platform} post"
                        )
                        if media:
                            media_ids = [media['id']]
                            print(f"✓ Image uploaded successfully")
                    
                    status = self.mastodon_agent.post_status(
                        content=post_content,
                        visibility=mastodon_visibility,
                        spoiler_text=mastodon_spoiler,
                        media_ids=media_ids
                    )
                    
                    if status:
                        published_posts[platform] = {
                            "status_id": status.get("id"),
                            "url": status.get("url"),
                            "platform": platform
                        }
                        print(f"✓ Published {platform} post")
                        print(f"   URL: {status.get('url')}")
                        
                        # Send confirmation via Telegram if available
                        if self.telegram_agent and approval_mode == "telegram":
                            post_url = status.get('url', 'N/A')
                            confirmation_msg = (
                                f"✅ Post Published Successfully!\n\n"
                                f"Platform: {platform.upper()}\n"
                                f"URL: {post_url}\n\n"
                            )
                            self.telegram_agent.send_confirmation_sync(confirmation_msg)
                    else:
                        error = f"Failed to publish {platform} post"
                        print(f"✗ {error}")
                        results["errors"].append(error)
        
        results["published_posts"] = published_posts
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Workflow Complete!")
        print("=" * 60)
        print(f"Generated posts: {len(approved_posts)}/{len(platforms)}")
        if "mastodon" in platforms:
            print(f"Published posts: {len(published_posts)}/{len(approved_posts)}")
        else:
            print(f"Published posts: 0 (Mastodon not in platforms)")
        
        if results["errors"]:
            print(f"\n⚠️ Errors: {len(results['errors'])}")
            for error in results["errors"]:
                print(f"  - {error}")
        
        return results
    
    def _run_reply_mode(
        self,
        source_page_id: str,
        tone: str,
        auto_publish: bool,
        mastodon_visibility: str,
        approval_mode: str
    ) -> Dict:
        """
        Run workflow in reply mode: find and reply to related posts
        
        Args:
            source_page_id: Notion page ID containing product description
            tone: Tone for replies (engaging, professional, casual, etc.)
            auto_publish: If True, publish without confirmation
            mastodon_visibility: Mastodon reply visibility (public, unlisted, private, direct)
        
        Returns:
            Dictionary with workflow results
        """
        print("=" * 60)
        print("🚀 Starting Auto Reply Workflow (Mode: REPLY)")
        print("=" * 60)
        
        results = {
            "source_page_id": source_page_id,
            "mode": "reply",
            "posted_replies": [],
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
        
        # Step 2: Extract keywords and search for related posts
        print("\n🔍 Step 2: Finding related posts to reply to...")
        
        # Extract keywords from product description
        keywords = self._extract_keywords(product_description)
        print(f"   Extracted keywords: {', '.join(keywords[:3])}...")
        
        # Search for posts using first keyword
        if not keywords:
            error = "Could not extract keywords from product description"
            print(f"✗ {error}")
            results["errors"].append(error)
            return results
        
        search_query = keywords[0]
        print(f"   Searching for posts with keyword: {search_query}")
        
        related_posts = self.mastodon_agent.search_posts(query=search_query, limit=5)
        
        if not related_posts:
            print("ℹ️  No related posts found to reply to")
            return results
        
        print(f"✓ Found {len(related_posts)} related posts")
        
        # Step 3: Generate replies using structured output
        print("\n🤖 Step 3: Generating replies using AI...")
        print(f"   Model: {self.openrouter_client.model}")
        print(f"   Tone: {tone}")
        
        replies = self.openrouter_client.generate_replies_batch(
            product_description=product_description,
            posts=related_posts,
            tone=tone
        )
        
        if not replies:
            error = "Failed to generate replies"
            print(f"✗ {error}")
            results["errors"].append(error)
            return results
        
        print(f"✓ Generated {len(replies)} replies")
        
        # Step 4: Post replies
        print("\n📤 Step 4: Posting replies...")
        print(f"   Visibility: {mastodon_visibility}")
        
        if not auto_publish:
            print(f"   Approval mode: {approval_mode}")
            
            if approval_mode == "cmd":
                print("\nGenerated replies:")
                for i, reply_data in enumerate(replies, 1):
                    post_id = reply_data.get('post_id')
                    reply_text = reply_data.get('reply')
                    original_post = next((p for p in related_posts if str(p.get('id')) == str(post_id)), None)
                    
                    if post_id and reply_text:
                        print(f"\nReply {i} (to post {post_id}):")
                        if original_post:
                            original_content = original_post.get('content', '')[:100]
                            print(f"  Original post: {original_content}...")
                        print("-" * 60)
                        print(reply_text)
                        print("-" * 60)
                
                response = input("\nPost all replies to Mastodon? (y/n): ")
                should_post = response.lower() == 'y'
            else:  # approval_mode == "telegram"
                # Telegram approval
                should_post = asyncio.run(
                    self.telegram_agent.wait_for_replies_approval(
                        replies=replies,
                        related_posts=related_posts
                    )
                )
            
            if not should_post:
                print("Posting cancelled.")
                # Continue to show summary even if posting cancelled
                posted_replies = []
            else:
                # Only post if user confirmed
                posted_replies = []
                for reply_data in replies:
                    post_id = reply_data.get('post_id')
                    reply_text = reply_data.get('reply')
                    
                    if post_id and reply_text:
                        try:
                            reply_status = self.mastodon_agent.reply_to_status(
                                status_id=int(post_id),
                                content=reply_text,
                                visibility=mastodon_visibility
                            )
                            if reply_status:
                                reply_url = reply_status.get('url', 'N/A')
                                posted_replies.append({
                                    'post_id': post_id,
                                    'reply_text': reply_text,
                                    'status_id': reply_status.get('id'),
                                    'url': reply_url
                                })
                                print(f"  ✓ Replied to post {post_id}")
                                
                                # Send confirmation via Telegram if available
                                if self.telegram_agent and approval_mode == "telegram":
                                    confirmation_msg = (
                                        f"✅ Reply Posted Successfully!\n\n"
                                        f"Reply to post: {post_id}\n"
                                        f"URL: {reply_url}\n\n"
                                        f"Reply content:\n{reply_text[:200]}{'...' if len(reply_text) > 200 else ''}"
                                    )
                                    self.telegram_agent.send_confirmation_sync(confirmation_msg)
                        except Exception as e:
                            error = f"Failed to reply to post {post_id}: {e}"
                            print(f"  ✗ {error}")
                            results["errors"].append(error)
        else:
            # Auto-publish mode
            posted_replies = []
            for reply_data in replies:
                post_id = reply_data.get('post_id')
                reply_text = reply_data.get('reply')
                
                if post_id and reply_text:
                    try:
                        reply_status = self.mastodon_agent.reply_to_status(
                            status_id=int(post_id),
                            content=reply_text,
                            visibility=mastodon_visibility
                        )
                        if reply_status:
                            reply_url = reply_status.get('url', 'N/A')
                            posted_replies.append({
                                'post_id': post_id,
                                'reply_text': reply_text,
                                'status_id': reply_status.get('id'),
                                'url': reply_url
                            })
                            print(f"  ✓ Replied to post {post_id}")
                            
                            # Send confirmation via Telegram if available
                            if self.telegram_agent and approval_mode == "telegram":
                                confirmation_msg = (
                                    f"✅ Reply Posted Successfully!\n\n"
                                    f"Reply to post: {post_id}\n"
                                    f"URL: {reply_url}\n\n"
                                    f"Reply content:\n{reply_text[:200]}{'...' if len(reply_text) > 200 else ''}"
                                )
                                self.telegram_agent.send_confirmation_sync(confirmation_msg)
                    except Exception as e:
                        error = f"Failed to reply to post {post_id}: {e}"
                        print(f"  ✗ {error}")
                        results["errors"].append(error)
        
        results["posted_replies"] = posted_replies
        print(f"\n✓ Posted {len(posted_replies)} replies successfully")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Auto Reply Workflow Complete!")
        print("=" * 60)
        print(f"Posted replies: {len(posted_replies)}/{len(replies)}")
        
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
    
    # Check for Telegram trigger
    telegram_trigger = workflow_config.get('telegram_trigger')
    # Handle both null (None) and string "null"
    if telegram_trigger == "null" or telegram_trigger is None:
        telegram_trigger = None
    
    # Load other configs
    notion_config = load_notion_config()
    openrouter_config = load_openrouter_config()
    mastodon_config = load_mastodon_config()
    
    # Load Telegram config if available
    telegram_config = {}
    if load_telegram_config:
        telegram_config = load_telegram_config()
    
    # If telegram_trigger is set, wait for trigger message before proceeding
    if telegram_trigger:
        if not TELEGRAM_AVAILABLE:
            print("Error: Telegram trigger mode requires python-telegram-bot")
            print("Install it with: pip install python-telegram-bot")
            sys.exit(1)
        
        telegram_bot_token = (
            telegram_config.get('bot_token') or
            os.getenv('TELEGRAM_BOT_TOKEN')
        )
        telegram_chat_id = (
            telegram_config.get('chat_id') or
            os.getenv('TELEGRAM_CHAT_ID')
        )
        
        if not telegram_bot_token:
            print("Error: Telegram bot token is required (telegram_trigger is set)")
            print("Set it in .config/telegram_config.json or TELEGRAM_BOT_TOKEN environment variable")
            sys.exit(1)
        
        if not telegram_chat_id:
            print("Error: Telegram chat ID is required (telegram_trigger is set)")
            print("Set it in .config/telegram_config.json or TELEGRAM_CHAT_ID environment variable")
            sys.exit(1)
        
        # Create Telegram agent for trigger listening
        trigger_agent = TelegramApprovalAgent(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id
        )
        
        print("=" * 60)
        print("🔔 Telegram Trigger Mode Enabled")
        print("=" * 60)
        print(f"Waiting for trigger message: '{telegram_trigger}'")
        print("Send this message to the bot to start the workflow...")
        print("=" * 60)
        
        # Wait for trigger message
        trigger_received = trigger_agent.wait_for_trigger_sync(telegram_trigger)
        
        if not trigger_received:
            print("\n✗ Trigger not received. Exiting.")
            sys.exit(0)
        
        print("\n✅ Trigger received! Starting workflow...\n")
    
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
    
    # Get workflow settings
    mode = workflow_config.get('mode', 'post')
    source_page_id = workflow_config.get('source_page_id')
    platforms = workflow_config.get('platforms', ['twitter', 'linkedin', 'instagram'])
    tone = workflow_config.get('tone', 'engaging')
    # Get openrouter_model from openrouter_config.json (not workflow_config.json)
    openrouter_model = (
        openrouter_config.get('model') 
    )
    auto_publish = workflow_config.get('auto_publish', False)
    approval_mode = workflow_config.get('approval_mode', 'cmd')
    
    mastodon_settings = workflow_config.get('mastodon', {})
    mastodon_visibility = mastodon_settings.get('visibility', 'public')
    mastodon_spoiler = mastodon_settings.get('spoiler_text')
    
    # Validate approval_mode
    if approval_mode not in ['cmd', 'telegram']:
        print(f"Error: Invalid approval_mode '{approval_mode}' in workflow_config.json")
        print("approval_mode must be 'cmd' (command line) or 'telegram' (Telegram bot)")
        sys.exit(1)
    
    # Initialize Telegram agent if needed
    telegram_agent = None
    if approval_mode == 'telegram':
        if not TELEGRAM_AVAILABLE:
            print("Error: Telegram approval mode requires python-telegram-bot")
            print("Install it with: pip install python-telegram-bot")
            sys.exit(1)
        
        telegram_bot_token = (
            telegram_config.get('bot_token') or
            os.getenv('TELEGRAM_BOT_TOKEN')
        )
        telegram_chat_id = (
            telegram_config.get('chat_id') or
            os.getenv('TELEGRAM_CHAT_ID')
        )
        
        if not telegram_bot_token:
            print("Error: Telegram bot token is required (approval_mode is 'telegram')")
            print("Set it in .config/telegram_config.json or TELEGRAM_BOT_TOKEN environment variable")
            sys.exit(1)
        
        if not telegram_chat_id:
            print("Error: Telegram chat ID is required (approval_mode is 'telegram')")
            print("Set it in .config/telegram_config.json or TELEGRAM_CHAT_ID environment variable")
            sys.exit(1)
        
        telegram_agent = TelegramApprovalAgent(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id
        )
        print("✓ Telegram agent initialized")
    
    if not source_page_id:
        print("Error: source_page_id is required in workflow_config.json")
        sys.exit(1)
    
    # Validate mode
    if mode not in ['post', 'reply']:
        print(f"Error: Invalid mode '{mode}' in workflow_config.json")
        print("Mode must be 'post' (generate and publish posts) or 'reply' (find and reply to posts)")
        sys.exit(1)
    
    # Check Mastodon credentials based on mode
    if mode == 'reply':
        # Reply mode always requires Mastodon credentials
        if not mastodon_instance_url:
            print("Error: Mastodon instance URL is required (mode is 'reply')")
            print("Set it in .config/mastodon_config.json or MASTODON_INSTANCE_URL environment variable")
            sys.exit(1)
        
        if not mastodon_access_token:
            print("Error: Mastodon access token is required (mode is 'reply')")
            print("Set it in .config/mastodon_config.json or MASTODON_ACCESS_TOKEN environment variable")
            sys.exit(1)
    elif "mastodon" in platforms:
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
            openrouter_model=openrouter_model,
            telegram_agent=telegram_agent
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
            openrouter_model=openrouter_model,
            telegram_agent=telegram_agent
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
    
    # Run workflow based on mode
    results = workflow.run(
        source_page_id=source_page_id,
        mode=mode,
        platforms=platforms if mode == 'post' else [],
        tone=tone,
        auto_publish=auto_publish,
        mastodon_visibility=mastodon_visibility,
        mastodon_spoiler=mastodon_spoiler if mode == 'post' else None,
        approval_mode=approval_mode
    )
    
    # Exit with error code if there were errors
    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
