#!/usr/bin/env python3
"""
Telegram Agent for Human-in-the-Loop Approval

This module provides functions for sending approval requests to Telegram
and waiting for human responses via interactive buttons.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime

try:
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CallbackQueryHandler, ContextTypes
    from telegram import Update
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    # Create dummy classes to prevent errors when module is imported but not used
    Bot = None
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None
    Application = None
    CallbackQueryHandler = None
    ContextTypes = None
    Update = None

# Get project root (parent of src directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(config_path: str = ".config/telegram_config.json") -> dict:
    """Load Telegram configuration from JSON file"""
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


class TelegramApprovalAgent:
    """Agent for handling Telegram-based approvals"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize the Telegram approval agent
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        if not TELEGRAM_AVAILABLE:
            raise ImportError(
                "python-telegram-bot is not installed. "
                "Install it with: pip install python-telegram-bot "
                "or: uv add python-telegram-bot"
            )
        
        self.bot_token = bot_token
        self.chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
        self.bot = Bot(token=bot_token)
        self.app = None
        self.decision_result = None
        self.decision_event = None
        self.final_content = None  # Store final approved/regenerated content
    
    async def _cleanup_app(self):
        """Clean up the Telegram application"""
        if self.app:
            try:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
            except Exception as e:
                print(f"Warning: Error cleaning up Telegram app: {e}")
            finally:
                self.app = None
    
    async def wait_for_post_approval(
        self, 
        platform: str, 
        post_content: str,
        regenerate_callback=None,
        timeout: int = 300
    ) -> str:
        """
        Send a post for approval and wait for human decision.
        Supports regeneration by calling regenerate_callback when regenerate is clicked.
        
        Args:
            platform: Platform name (e.g., "twitter", "linkedin")
            post_content: The post content to approve
            regenerate_callback: Optional async function to call when regenerate is clicked.
                                 Should return new post content, or None to keep current.
            timeout: Maximum time to wait in seconds (default: 5 minutes)
        
        Returns:
            'accept' or 'regenerate'
        """
        current_content = post_content
        message_id = None
        
        async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle button clicks from Telegram"""
            nonlocal current_content, message_id
            
            query = update.callback_query
            await query.answer()
            
            decision = query.data
            
            if decision == "accept":
                self.decision_result = "accept"
                self.final_content = current_content  # Store final content
                await query.edit_message_text(
                    f"✅ ACCEPTED\n\n"
                    f"Platform: {platform.upper()}\n"
                    f"Post:\n{current_content}"
                )
                self.decision_event.set()
            
            elif decision == "regenerate":
                # Show regenerating message
                await query.edit_message_text(
                    f"🔄 REGENERATING\n\n"
                    f"Platform: {platform.upper()}\n"
                    f"Please wait..."
                )
                
                # Call regenerate callback if provided
                if regenerate_callback:
                    try:
                        new_content = await regenerate_callback()
                        if new_content:
                            current_content = new_content
                            
                            # Update message with new content
                            message_text = (
                                f"📝 Post for Approval (Regenerated)\n\n"
                                f"Platform: {platform.upper()}\n"
                                f"Characters: {len(current_content)}\n\n"
                                f"{current_content}"
                            )
                            
                            keyboard = InlineKeyboardMarkup([
                                [
                                    InlineKeyboardButton("✅ Accept", callback_data="accept"),
                                    InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
                                ]
                            ])
                            
                            await query.edit_message_text(
                                text=message_text,
                                reply_markup=keyboard
                            )
                        else:
                            # Regeneration failed, restore keyboard with current content
                            message_text = (
                                f"⚠️ Regeneration failed. Keeping previous version.\n\n"
                                f"Platform: {platform.upper()}\n"
                                f"Characters: {len(current_content)}\n\n"
                                f"{current_content}"
                            )
                            keyboard = InlineKeyboardMarkup([
                                [
                                    InlineKeyboardButton("✅ Accept", callback_data="accept"),
                                    InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
                                ]
                            ])
                            await query.edit_message_text(
                                text=message_text,
                                reply_markup=keyboard
                            )
                    except Exception as e:
                        print(f"✗ Error during regeneration: {e}")
                        # Restore keyboard with current content after error
                        message_text = (
                            f"⚠️ Error during regeneration: {str(e)}\n\n"
                            f"Platform: {platform.upper()}\n"
                            f"Characters: {len(current_content)}\n\n"
                            f"{current_content}"
                        )
                        keyboard = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("✅ Accept", callback_data="accept"),
                                InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
                            ]
                        ])
                        await query.edit_message_text(
                            text=message_text,
                            reply_markup=keyboard
                        )
                else:
                    # No callback, just return regenerate signal
                    self.decision_result = "regenerate"
                    self.decision_event.set()
        
        # Create keyboard with Accept/Regenerate buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data="accept"),
                InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
            ]
        ])
        
        # Send the post with buttons
        message_text = (
            f"📝 Post for Approval\n\n"
            f"Platform: {platform.upper()}\n"
            f"Characters: {len(current_content)}\n\n"
            f"{current_content}"
        )
        
        try:
            # Create a fresh bot instance to avoid event loop issues
            fresh_bot = Bot(token=self.bot_token)
            sent_message = await fresh_bot.send_message(
                chat_id=self.chat_id,
                text=message_text,
                reply_markup=keyboard,
            )
            message_id = sent_message.message_id
            print(f"📱 Sent {platform} post to Telegram. Waiting for approval...")
        except Exception as e:
            print(f"✗ Failed to send message to Telegram: {e}")
            print("⚠️ Defaulting to accept due to error (post will be approved).")
            return "accept"  # Default to accept on error for post approval
        
        # Set up the listener
        self.decision_result = None
        self.decision_event = asyncio.Event()
        
        self.app = Application.builder().token(self.bot_token).build()
        self.app.add_handler(CallbackQueryHandler(handle_decision))
        
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            # Wait for decision with timeout
            try:
                await asyncio.wait_for(self.decision_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print(f"⏱️ Timeout waiting for approval. Defaulting to accept.")
                self.decision_result = "accept"
        finally:
            await self._cleanup_app()
        
        return self.decision_result or "accept"
    
    async def wait_for_replies_approval(
        self,
        replies: List[Dict],
        related_posts: List[Dict],
        timeout: int = 600
    ) -> bool:
        """
        Send all replies for approval and wait for human decision.
        
        Args:
            replies: List of reply dicts with 'post_id' and 'reply' keys
            related_posts: List of original posts for context
            timeout: Maximum time to wait in seconds (default: 10 minutes)
        
        Returns:
            True if approved, False if rejected
        """
        self.decision_result = None
        self.decision_event = asyncio.Event()
        
        async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle button clicks from Telegram"""
            query = update.callback_query
            await query.answer()
            
            decision = query.data
            self.decision_result = (decision == "approve")
            
            if decision == "approve":
                await query.edit_message_text(
                    f"✅ APPROVED\n\n"
                    f"All {len(replies)} replies will be posted."
                )
            else:
                await query.edit_message_text(
                    f"❌ REJECTED\n\n"
                    f"Replies will not be posted."
                )
            
            self.decision_event.set()
        
        # Build message with all replies
        message_lines = [f"📝 Replies for Approval ({len(replies)} total)\n"]
        
        for i, reply_data in enumerate(replies, 1):
            post_id = reply_data.get('post_id')
            reply_text = reply_data.get('reply')
            original_post = next(
                (p for p in related_posts if str(p.get('id')) == str(post_id)), 
                None
            )
            
            message_lines.append(f"\n{'='*50}")
            message_lines.append(f"Reply {i} (to post {post_id}):")
            if original_post:
                original_content = original_post.get('content', '')[:150]
                message_lines.append(f"Original: {original_content}...")
            message_lines.append(f"\n{reply_text}")
        
        message_text = "\n".join(message_lines)
        
        # Telegram has a 4096 character limit, truncate if needed
        if len(message_text) > 4000:
            message_text = message_text[:3900] + "\n\n... (truncated)"
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve All", callback_data="approve"),
                InlineKeyboardButton("❌ Reject All", callback_data="reject"),
            ]
        ])
        
        try:
            # Create a fresh bot instance to avoid event loop issues
            fresh_bot = Bot(token=self.bot_token)
            await fresh_bot.send_message(
                chat_id=self.chat_id,
                text=message_text,
                reply_markup=keyboard,
            )
            print(f"📱 Sent {len(replies)} replies to Telegram. Waiting for approval...")
        except Exception as e:
            print(f"✗ Failed to send message to Telegram: {e}")
            print("⚠️ Defaulting to NOT approve due to error (replies will not be posted).")
            return False  # Default to NOT approve on error (safer)
        
        # Set up the listener
        self.app = Application.builder().token(self.bot_token).build()
        self.app.add_handler(CallbackQueryHandler(handle_decision))
        
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            # Wait for decision with timeout
            try:
                await asyncio.wait_for(self.decision_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print(f"⏱️ Timeout waiting for approval. Defaulting to NOT approve (safer).")
                self.decision_result = False
        finally:
            await self._cleanup_app()
        
        return self.decision_result if self.decision_result is not None else False
    
    async def wait_for_publish_approval(
        self,
        posts: Dict[str, str],
        timeout: int = 300
    ) -> bool:
        """
        Send all approved posts for final publish confirmation.
        
        Args:
            posts: Dictionary mapping platform to post content
            timeout: Maximum time to wait in seconds (default: 5 minutes)
        
        Returns:
            True if approved for publishing, False otherwise
        """
        self.decision_result = None
        self.decision_event = asyncio.Event()
        
        async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle button clicks from Telegram"""
            query = update.callback_query
            await query.answer()
            
            decision = query.data
            self.decision_result = (decision == "publish")
            
            if decision == "publish":
                await query.edit_message_text(
                    f"✅ PUBLISHING\n\n"
                    f"All {len(posts)} posts will be published to Mastodon."
                )
            else:
                await query.edit_message_text(
                    f"❌ CANCELLED\n\n"
                    f"Posts will not be published."
                )
            
            self.decision_event.set()
        
        # Build message with all posts
        message_lines = [f"📤 Publish to Mastodon? ({len(posts)} posts)\n"]
        
        for platform, post_content in posts.items():
            message_lines.append(f"\n{'='*50}")
            message_lines.append(f"{platform.upper()}:")
            message_lines.append(f"{post_content}")
        
        message_text = "\n".join(message_lines)
        
        # Telegram has a 4096 character limit, truncate if needed
        if len(message_text) > 4000:
            message_text = message_text[:3900] + "\n\n... (truncated)"
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Publish All", callback_data="publish"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
            ]
        ])
        
        try:
            # Create a fresh bot instance to avoid event loop issues
            fresh_bot = Bot(token=self.bot_token)
            await fresh_bot.send_message(
                chat_id=self.chat_id,
                text=message_text,
                reply_markup=keyboard,
            )
            print(f"📱 Sent publish confirmation to Telegram. Waiting for approval...")
        except Exception as e:
            print(f"✗ Failed to send message to Telegram: {e}")
            print("⚠️ Publishing cancelled due to error.")
            return False  # Default to NOT publish on error (safer)
        
        # Set up the listener
        self.app = Application.builder().token(self.bot_token).build()
        self.app.add_handler(CallbackQueryHandler(handle_decision))
        
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            # Wait for decision with timeout
            try:
                await asyncio.wait_for(self.decision_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print(f"⏱️ Timeout waiting for approval. Defaulting to NOT publish (safer).")
                self.decision_result = False
        finally:
            await self._cleanup_app()
        
        return self.decision_result if self.decision_result is not None else False
    
    async def send_confirmation(
        self,
        message: str
    ) -> bool:
        """
        Send a confirmation message to Telegram.
        
        Args:
            message: The confirmation message to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create a fresh bot instance to avoid event loop issues
            fresh_bot = Bot(token=self.bot_token)
            await fresh_bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
            return True
        except Exception as e:
            print(f"✗ Failed to send confirmation to Telegram: {e}")
            return False
    
    def send_confirmation_sync(
        self,
        message: str
    ) -> bool:
        """
        Synchronous wrapper for send_confirmation.
        Creates a new event loop to avoid conflicts with closed loops.
        
        Args:
            message: The confirmation message to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create a new event loop for this operation
            # This avoids conflicts with previously closed event loops
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.send_confirmation(message))
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"✗ Failed to send confirmation to Telegram: {e}")
            return False


def verify_credentials(bot_token: str, chat_id: str) -> bool:
    """
    Verify Telegram credentials by sending a test message
    
    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
    
    Returns:
        True if credentials are valid, False otherwise
    """
    async def _verify():
        try:
            bot = Bot(token=bot_token)
            chat_id_int = int(chat_id) if isinstance(chat_id, str) else chat_id
            await bot.send_message(
                chat_id=chat_id_int,
                text="✅ Telegram bot credentials verified!"
            )
            return True
        except Exception as e:
            print(f"✗ Telegram verification failed: {e}")
            return False
    
    try:
        return asyncio.run(_verify())
    except Exception as e:
        print(f"✗ Telegram verification error: {e}")
        return False
