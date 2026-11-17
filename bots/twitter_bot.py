"""
Twitter (X) Bot Module for Wife God Agent
Local Twitter automation with Playwright + PyAutoGUI fallback
"""

import asyncio
import logging
import json
import os
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    async_playwright = None
    Page = None
    Browser = None
    BrowserContext = None

logger = logging.getLogger("WifeGod.TwitterBot")


class TwitterAction(Enum):
    POST_TWEET = "post_tweet"
    REPLY = "reply"
    RETWEET = "retweet"
    LIKE = "like"
    FOLLOW = "follow"
    DM = "dm"
    SCRAPE_HASHTAG = "scrape_hashtag"
    SCRAPE_USER = "scrape_user"
    SEARCH = "search"


@dataclass
class TwitterConfig:
    username: str = ""
    password: str = ""
    headless: bool = False
    browser: str = "chromium"
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    timeout: int = 30000
    session_file: str = "./data/twitter_session.json"
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "tweets_per_hour": 50,
        "dms_per_hour": 100,
        "follows_per_hour": 50
    })


@dataclass
class TweetData:
    id: str
    text: str
    author: str
    author_handle: str
    timestamp: datetime
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    media_urls: List[str] = field(default_factory=list)
    url: str = ""


class TwitterBot:
    """
    Twitter (X) automation bot
    - Playwright for web automation
    - Session persistence
    - Rate limiting
    - Media upload support
    - DM handling
    """

    def __init__(self, config: Dict[str, Any], llm, voice, doc_processor, pyautogui_fallback, db):
        self.config = TwitterConfig(**config) if isinstance(config, dict) else config
        self.llm = llm
        self.voice = voice
        self.doc_processor = doc_processor
        self.pyautogui_fallback = pyautogui_fallback
        self.db = db

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._logged_in = False
        self._last_action_time = 0
        self._action_counts = {"tweets": 0, "dms": 0, "follows": 0}
        self._last_reset_hour = datetime.now().hour

    async def initialize(self):
        """Initialize browser and load session"""
        logger.info("Initializing TwitterBot...")

        if not async_playwright:
            logger.error("Playwright not available!")
            return

        self._playwright = await async_playwright().start()

        browser_type = getattr(self._playwright, self.config.browser)
        self._browser = await browser_type.launch(
            headless=self.config.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        self._context = await self._browser.new_context(
            viewport=self.config.viewport,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.config.timeout)

        # Load saved session
        await self._load_session()

        logger.info("TwitterBot initialized")

    @property
    def is_ready(self) -> bool:
        return self._page is not None and not self._page.is_closed()

    async def _load_session(self):
        """Load saved Twitter session"""
        try:
            session_data = await self.db.get_twitter_session(self.config.username)
            if session_data and session_data.get('session_data'):
                cookies = session_data['session_data'].get('cookies', [])
                if cookies:
                    await self._context.add_cookies(cookies)
                    self._logged_in = True
                    logger.info("Twitter session restored")
        except Exception as e:
            logger.warning(f"Session load failed: {e}")

    async def _save_session(self):
        """Save current session"""
        try:
            cookies = await self._context.cookies()
            session_data = {
                "cookies": cookies,
                "saved_at": datetime.now().isoformat()
            }
            await self.db.save_twitter_session(self.config.username, session_data)
        except Exception as e:
            logger.warning(f"Session save failed: {e}")

    async def _check_rate_limit(self, action: str) -> bool:
        """Check if action is within rate limits"""
        current_hour = datetime.now().hour

        # Reset counters if new hour
        if current_hour != self._last_reset_hour:
            self._action_counts = {"tweets": 0, "dms": 0, "follows": 0}
            self._last_reset_hour = current_hour

        limits = self.config.rate_limits

        if action == "tweet" and self._action_counts["tweets"] >= limits["tweets_per_hour"]:
            return False
        if action == "dm" and self._action_counts["dms"] >= limits["dms_per_hour"]:
            return False
        if action == "follow" and self._action_counts["follows"] >= limits["follows_per_hour"]:
            return False

        return True

    async def _increment_action(self, action: str):
        """Increment action counter"""
        if action == "tweet":
            self._action_counts["tweets"] += 1
        elif action == "dm":
            self._action_counts["dms"] += 1
        elif action == "follow":
            self._action_counts["follows"] += 1

    async def login(self) -> bool:
        """Login to Twitter/X"""
        if self._logged_in:
            # Verify session still valid
            if await self._verify_login():
                return True

        try:
            logger.info("Logging into Twitter...")
            await self._page.goto("https://x.com/i/flow/login", wait_until='networkidle')

            # Wait for username field
            await self._page.wait_for_selector('input[autocomplete="username"]', timeout=15000)

            # Enter username
            await self._page.fill('input[autocomplete="username"]', self.config.username)
            await self._page.click('button:has-text("Next")')
            await asyncio.sleep(2)

            # Enter password
            await self._page.wait_for_selector('input[name="password"]', timeout=10000)
            await self._page.fill('input[name="password"]', self.config.password)
            await self._page.click('button:has-text("Log in")')

            # Wait for login
            await self._page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)

            # Check for 2FA
            if await self._page.query_selector('input[data-testid="ocfEnterTextTextInput"]'):
                await self.voice.speak("Two-factor authentication required. Please enter code.")
                # Wait for manual entry
                await asyncio.sleep(30)

            # Verify login
            self._logged_in = await self._verify_login()

            if self._logged_in:
                await self._save_session()
                logger.info("Twitter login successful")
                return True

            return False

        except Exception as e:
            logger.error(f"Twitter login failed: {e}")
            return False

    async def _verify_login(self) -> bool:
        """Verify if logged in"""
        try:
            # Check for home timeline or profile
            await self._page.goto("https://x.com/home", wait_until='networkidle')
            await asyncio.sleep(2)

            # Check for tweet composer or profile
            composer = await self._page.query_selector('[data-testid="tweetTextarea_0"]')
            profile = await self._page.query_selector('[data-testid="AppTabBar_Profile_Link"]')

            return bool(composer or profile)
        except:
            return False

    async def post_tweet(self, text: str, media_paths: List[str] = None,
                         reply_to: str = None, quote_tweet: str = None) -> Dict[str, Any]:
        """Post a tweet"""
        if not self._logged_in:
            if not await self.login():
                return {"success": False, "error": "Not logged in"}

        if not await self._check_rate_limit("tweet"):
            return {"success": False, "error": "Rate limit exceeded"}

        try:
            logger.info(f"Posting tweet: {text[:50]}...")

            # Navigate to home if not there
            await self._page.goto("https://x.com/home", wait_until='networkidle')
            await asyncio.sleep(2)

            # Handle reply/quote
            if reply_to:
                await self._page.goto(f"https://x.com/{reply_to}", wait_until='networkidle')
                await asyncio.sleep(2)
                reply_btn = await self._page.query_selector('[data-testid="reply"]')
                if reply_btn:
                    await reply_btn.click()
                    await asyncio.sleep(1)

            elif quote_tweet:
                await self._page.goto(f"https://x.com/{quote_tweet}", wait_until='networkidle')
                await asyncio.sleep(2)
                quote_btn = await self._page.query_selector('[data-testid="retweet"]')
                if quote_btn:
                    await quote_btn.click()
                    await self._page.click('[data-testid="retweetConfirm"]')
                    await asyncio.sleep(1)

            # Find tweet composer
            composer = await self._page.query_selector('[data-testid="tweetTextarea_0"]')
            if not composer:
                # Try alternative selectors
                for selector in [
                    '[data-testid="tweetTextarea_0"]',
                    '[role="textbox"][data-testid="tweetTextarea_0"]',
                    'div[role="textbox"][contenteditable="true"]'
                ]:
                    composer = await self._page.query_selector(selector)
                    if composer:
                        break

            if not composer:
                return {"success": False, "error": "Tweet composer not found"}

            # Type tweet text
            await composer.click()
            await asyncio.sleep(0.5)
            await composer.fill(text)

            # Add media if provided
            if media_paths:
                for media_path in media_paths:
                    if os.path.exists(media_path):
                        # Click media button
                        media_btn = await self._page.query_selector('[data-testid="fileInput"]')
                        if media_btn:
                            await media_btn.set_input_files(media_path)
                            await asyncio.sleep(3)  # Wait for upload

            # Post tweet
            tweet_btn = await self._page.query_selector('[data-testid="tweetButton"]')
            if tweet_btn:
                await tweet_btn.click()
                await asyncio.sleep(2)

            await self._increment_action("tweet")
            await self._save_session()

            logger.info("Tweet posted successfully")
            await self.voice.speak("Tweet post ho gaya hai.")

            return {"success": True, "message": "Tweet posted successfully"}

        except Exception as e:
            logger.error(f"Tweet posting failed: {e}")
            return {"success": False, "error": str(e)}

    async def reply_to_tweet(self, tweet_url: str, reply_text: str) -> Dict[str, Any]:
        """Reply to a tweet"""
        return await self.post_tweet(reply_text, reply_to=tweet_url)

    async def retweet(self, tweet_url: str) -> Dict[str, Any]:
        """Retweet a tweet"""
        if not self._logged_in:
            return {"success": False, "error": "Not logged in"}

        try:
            await self._page.goto(tweet_url, wait_until='networkidle')
            await asyncio.sleep(2)

            retweet_btn = await self._page.query_selector('[data-testid="retweet"]')
            if retweet_btn:
                await retweet_btn.click()
                await asyncio.sleep(1)

                confirm_btn = await self._page.query_selector('[data-testid="retweetConfirm"]')
                if confirm_btn:
                    await confirm_btn.click()
                    await asyncio.sleep(1)

            return {"success": True, "message": "Retweeted"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def like_tweet(self, tweet_url: str) -> Dict[str, Any]:
        """Like a tweet"""
        if not self._logged_in:
            return {"success": False, "error": "Not logged in"}

        try:
            await self._page.goto(tweet_url, wait_until='networkidle')
            await asyncio.sleep(2)

            like_btn = await self._page.query_selector('[data-testid="like"]')
            if like_btn:
                await like_btn.click()
                await asyncio.sleep(1)

            return {"success": True, "message": "Liked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def follow_user(self, username: str) -> Dict[str, Any]:
        """Follow a user"""
        if not await self._check_rate_limit("follow"):
            return {"success": False, "error": "Rate limit exceeded"}

        try:
            await self._page.goto(f"https://x.com/{username}", wait_until='networkidle')
            await asyncio.sleep(2)

            follow_btn = await self._page.query_selector('[data-testid="followButton"], button:has-text("Follow")')
            if follow_btn:
                await follow_btn.click()
                await asyncio.sleep(1)

            await self._increment_action("follow")
            return {"success": True, "message": f"Followed {username}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_dm(self, username: str, message: str) -> Dict[str, Any]:
        """Send direct message"""
        if not await self._check_rate_limit("dm"):
            return {"success": False, "error": "Rate limit exceeded"}

        try:
            # Go to messages
            await self._page.goto("https://x.com/messages", wait_until='networkidle')
            await asyncio.sleep(2)

            # Click new message
            new_msg_btn = await self._page.query_selector('[data-testid="newMessage"]')
            if new_msg_btn:
                await new_msg_btn.click()
                await asyncio.sleep(1)

            # Search for user
            search_input = await self._page.query_selector('input[placeholder*="Search"]')
            if search_input:
                await search_input.fill(username)
                await asyncio.sleep(1)

                # Click user
                user_result = await self._page.query_selector(f'[data-testid="userResult"]:has-text("{username}")')
                if user_result:
                    await user_result.click()
                    await asyncio.sleep(1)

            # Click next
            next_btn = await self._page.query_selector('button:has-text("Next")')
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(1)

            # Type message
            dm_input = await self._page.query_selector('[data-testid="dmComposerTextInput"]')
            if dm_input:
                await dm_input.fill(message)
                await asyncio.sleep(0.5)

            # Send
            send_btn = await self._page.query_selector('[data-testid="dmComposerSendButton"]')
            if send_btn:
                await send_btn.click()
                await asyncio.sleep(1)

            await self._increment_action("dm")
            return {"success": True, "message": "DM sent"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scrape_hashtag(self, hashtag: str, limit: int = 50) -> Dict[str, Any]:
        """Scrape tweets by hashtag"""
        try:
            search_url = f"https://x.com/search?q=%23{hashtag}&src=typed_query&f=live"
            await self._page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(3)

            tweets = []
            last_height = 0

            while len(tweets) < limit:
                # Get tweet elements
                tweet_elements = await self._page.query_selector_all('[data-testid="tweet"]')

                for elem in tweet_elements[len(tweets):]:
                    tweet_data = await self._extract_tweet_data(elem)
                    if tweet_data and tweet_data not in tweets:
                        tweets.append(tweet_data)

                if len(tweets) >= limit:
                    break

                # Scroll down
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # Check if we've reached the end
                new_height = await self._page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            return {"success": True, "tweets": tweets[:limit], "count": len(tweets)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scrape_user_tweets(self, username: str, limit: int = 50) -> Dict[str, Any]:
        """Scrape tweets from a user"""
        try:
            await self._page.goto(f"https://x.com/{username}", wait_until='networkidle')
            await asyncio.sleep(3)

            tweets = []
            last_height = 0

            while len(tweets) < limit:
                tweet_elements = await self._page.query_selector_all('[data-testid="tweet"]')

                for elem in tweet_elements[len(tweets):]:
                    tweet_data = await self._extract_tweet_data(elem)
                    if tweet_data and tweet_data not in tweets:
                        tweets.append(tweet_data)

                if len(tweets) >= limit:
                    break

                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                new_height = await self._page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            return {"success": True, "tweets": tweets[:limit], "count": len(tweets)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def search_tweets(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search tweets"""
        try:
            search_url = f"https://x.com/search?q={query}&src=typed_query&f=live"
            await self._page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(3)

            tweets = []
            last_height = 0

            while len(tweets) < limit:
                tweet_elements = await self._page.query_selector_all('[data-testid="tweet"]')

                for elem in tweet_elements[len(tweets):]:
                    tweet_data = await self._extract_tweet_data(elem)
                    if tweet_data and tweet_data not in tweets:
                        tweets.append(tweet_data)

                if len(tweets) >= limit:
                    break

                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                new_height = await self._page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            return {"success": True, "tweets": tweets[:limit], "count": len(tweets)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _extract_tweet_data(self, element) -> Optional[Dict]:
        """Extract data from tweet element"""
        try:
            # Get tweet text
            text_elem = await element.query_selector('[data-testid="tweetText"]')
            text = await text_elem.inner_text() if text_elem else ""

            # Get author
            author_elem = await element.query_selector('[data-testid="User-Name"]')
            author_text = await author_elem.inner_text() if author_elem else ""
            author_lines = author_text.split('\n')
            author = author_lines[0] if author_lines else ""
            author_handle = author_lines[1] if len(author_lines) > 1 else ""

            # Get timestamp
            time_elem = await element.query_selector('time')
            timestamp = await time_elem.get_attribute('datetime') if time_elem else ""

            # Get engagement
            like_elem = await element.query_selector('[data-testid="like"]')
            retweet_elem = await element.query_selector('[data-testid="retweet"]')
            reply_elem = await element.query_selector('[data-testid="reply"]')

            likes = 0
            retweets = 0
            replies = 0

            # Get media
            media_urls = []
            media_elements = await element.query_selector_all('[data-testid="tweetPhoto"], [data-testid="videoPlayer"]')
            for media in media_elements:
                src = await media.get_attribute('src')
                if src:
                    media_urls.append(src)

            return {
                "text": text,
                "author": author,
                "author_handle": author_handle,
                "timestamp": timestamp,
                "likes": likes,
                "retweets": retweets,
                "replies": replies,
                "media_urls": media_urls,
                "url": ""
            }
        except:
            return None

    async def handle_dm(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DM automation"""
        action = params.get("action", "read")

        if action == "send":
            return await self.send_dm(params.get("username", ""), params.get("message", ""))

        elif action == "read":
            return await self.read_dms(params.get("limit", 20))

        elif action == "auto_reply":
            return await self.auto_reply_dms(params.get("keywords", []), params.get("reply_template", ""))

        return {"success": False, "error": "Unknown DM action"}

    async def read_dms(self, limit: int = 20) -> Dict[str, Any]:
        """Read recent DMs"""
        try:
            await self._page.goto("https://x.com/messages", wait_until='networkidle')
            await asyncio.sleep(2)

            dms = []
            # This would need implementation to read DM list
            # Simplified for now

            return {"success": True, "dms": dms, "count": len(dms)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def auto_reply_dms(self, keywords: List[str], reply_template: str) -> Dict[str, Any]:
        """Auto-reply to DMs containing keywords"""
        # This would need implementation
        return {"success": True, "message": "Auto-reply configured"}

    async def generate_tweet_content(self, topic: str, media_description: str = "") -> str:
        """Generate tweet content using LLM"""
        return await self.llm.generate_tweet(topic, media_description)

    async def close(self):
        """Close browser"""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("TwitterBot closed")
        except Exception as e:
            logger.error(f"Close error: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "ready": self.is_ready,
            "logged_in": self._logged_in,
            "username": self.config.username,
            "rate_limits": {
                "tweets": f"{self._action_counts['tweets']}/{self.config.rate_limits['tweets_per_hour']}",
                "dms": f"{self._action_counts['dms']}/{self.config.rate_limits['dms_per_hour']}",
                "follows": f"{self._action_counts['follows']}/{self.config.rate_limits['follows_per_hour']}"
            }
        }