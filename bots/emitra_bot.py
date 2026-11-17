"""
eMitra Bot Module for Wife God Agent
Rajasthan SSO automation with Playwright + PyAutoGUI fallback
"""

import asyncio
import logging
import json
import base64
import os
import tempfile
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

logger = logging.getLogger("WifeGod.eMitraBot")


class ServiceStatus(Enum):
    PENDING = "pending"
    LOGGING_IN = "logging_in"
    NAVIGATING = "navigating"
    FILLING_FORM = "filling_form"
    UPLOADING_DOCS = "uploading_docs"
    PAYMENT = "payment"
    DOWNLOADING_RECEIPT = "downloading_receipt"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EmiteConfig:
    sso_url: str = "https://sso.rajasthan.gov.in"
    portal_url: str = "https://emitra.rajasthan.gov.in"
    username: str = ""
    password: str = ""
    headless: bool = False
    browser: str = "chromium"
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    timeout: int = 30000
    services: Dict[str, Any] = field(default_factory=dict)


class eMitraBot:
    """
    eMitra (Rajasthan SSO) automation bot
    - Playwright for web automation
    - PyAutoGUI fallback for tricky elements
    - Human-in-the-loop for CAPTCHA/OTP
    """

    def __init__(self, config: Dict[str, Any], llm, voice, doc_processor, captcha_solver, pyautogui_fallback, db):
        self.config = EmiteConfig(**config) if isinstance(config, dict) else config
        self.llm = llm
        self.voice = voice
        self.doc_processor = doc_processor
        self.captcha_solver = captcha_solver
        self.pyautogui_fallback = pyautogui_fallback
        self.db = db

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._logged_in = False
        self._current_service = ""
        self._status = ServiceStatus.PENDING

    async def initialize(self):
        """Initialize browser"""
        logger.info("Initializing eMitraBot...")

        if not async_playwright:
            logger.error("Playwright not available!")
            return

        self._playwright = await async_playwright().start()

        # Launch browser
        browser_type = getattr(self._playwright, self.config.browser)
        self._browser = await browser_type.launch(
            headless=self.config.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        self._context = await self._browser.new_context(
            viewport=self.config.viewport,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.config.timeout)

        logger.info("eMitraBot initialized")

    @property
    def is_ready(self) -> bool:
        return self._page is not None and not self._page.is_closed()

    async def execute_service(self, service_name: str, documents: List[str],
                              user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute eMitra service end-to-end"""
        self._current_service = service_name
        self._status = ServiceStatus.PENDING

        task_id = f"emitra_{datetime.now().timestamp()}"

        try:
            logger.info(f"Starting eMitra service: {service_name}")

            # Step 1: Login to SSO
            await self.voice.speak("SSO portal par login kar raha hoon.")
            self._status = ServiceStatus.LOGGING_IN
            login_success = await self._login_sso()

            if not login_success:
                return {"success": False, "error": "SSO login failed"}

            # Step 2: Navigate to service
            await self.voice.speak(f"{service_name} service khol raha hoon.")
            self._status = ServiceStatus.NAVIGATING
            nav_success = await self._navigate_to_service(service_name)

            if not nav_success:
                return {"success": False, "error": f"Failed to navigate to {service_name}"}

            # Step 3: Process and prepare documents
            await self.voice.speak("Documents process kar raha hoon.")
            processed_docs = await self._process_documents(documents, service_name)

            # Step 4: Fill form
            await self.voice.speak("Form bhar raha hoon.")
            self._status = ServiceStatus.FILLING_FORM
            form_success = await self._fill_form(service_name, user_data)

            if not form_success:
                return {"success": False, "error": "Form filling failed"}

            # Step 5: Upload documents
            await self.voice.speak("Documents upload kar raha hoon.")
            self._status = ServiceStatus.UPLOADING_DOCS
            upload_success = await self._upload_documents(processed_docs)

            if not upload_success:
                return {"success": False, "error": "Document upload failed"}

            # Step 6: Handle payment
            self._status = ServiceStatus.PAYMENT
            payment_success = await self._handle_payment()

            if not payment_success:
                return {"success": False, "error": "Payment failed"}

            # Step 7: Download receipt
            self._status = ServiceStatus.DOWNLOADING_RECEIPT
            receipt_path = await self._download_receipt(service_name)

            self._status = ServiceStatus.COMPLETED
            await self.voice.speak("Aapka kaam ho gaya hai. Receipt save kar li gayi hai.")

            return {
                "success": True,
                "service": service_name,
                "receipt_path": receipt_path,
                "message": "Service completed successfully"
            }

        except Exception as e:
            self._status = ServiceStatus.FAILED
            logger.error(f"Service execution failed: {e}")
            await self.voice.speak(f"Error: {str(e)[:100]}")
            return {"success": False, "error": str(e)}

    async def _login_sso(self) -> bool:
        """Login to Rajasthan SSO"""
        try:
            await self._page.goto(self.config.sso_url, wait_until='networkidle')

            # Check if already logged in
            if await self._is_logged_in():
                logger.info("Already logged in")
                return True

            # Wait for login form
            await self._page.wait_for_selector('input[name="username"], input[id="username"]', timeout=10000)

            # Fill credentials
            await self._page.fill('input[name="username"], input[id="username"]', self.config.username)
            await self._page.fill('input[name="password"], input[id="password"]', self.config.password)

            # Handle CAPTCHA
            captcha_solved = await self._handle_captcha()
            if not captcha_solved:
                return False

            # Click login
            await self._page.click('button[type="submit"], input[type="submit"], button:has-text("Login")')
            await self._page.wait_for_load_state('networkidle')

            # Verify login
            await asyncio.sleep(2)
            return await self._is_logged_in()

        except Exception as e:
            logger.error(f"SSO login failed: {e}")
            return False

    async def _is_logged_in(self) -> bool:
        """Check if logged in"""
        try:
            # Check for user profile or logout button
            logout_btn = await self._page.query_selector('a:has-text("Logout"), button:has-text("Logout")')
            profile = await self._page.query_selector('.user-profile, .username, [class*="user"]')
            return bool(logout_btn or profile)
        except:
            return False

    async def _handle_captcha(self) -> bool:
        """Handle CAPTCHA on login page"""
        try:
            # Find captcha image
            captcha_img = await self._page.query_selector('img[src*="captcha"], img[id*="captcha"], img[class*="captcha"]')
            if not captcha_img:
                logger.info("No CAPTCHA found")
                return True

            # Get captcha image
            captcha_src = await captcha_img.get_attribute('src')
            if not captcha_src:
                return False

            # Download captcha image
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(captcha_src) as resp:
                    if resp.status == 200:
                        captcha_bytes = await resp.read()

            # Solve captcha
            from modules.captcha_solver import CaptchaType
            result = await self.captcha_solver.solve_from_bytes(captcha_bytes)

            if result.success:
                # Find captcha input and fill
                captcha_input = await self._page.query_selector('input[name*="captcha"], input[id*="captcha"]')
                if captcha_input:
                    await captcha_input.fill(result.answer)
                    return True

            # Fallback to human
            await self.voice.speak("CAPTCHA solve nahi hua. Please manually enter.")
            # Wait for manual entry (would need implementation)
            return False

        except Exception as e:
            logger.error(f"Captcha handling failed: {e}")
            return False

    async def _navigate_to_service(self, service_name: str) -> bool:
        """Navigate to eMitra service"""
        try:
            # Get service config
            service_config = self.config.services.get(service_name, {})
            service_url = service_config.get('url', '')

            if not service_url:
                # Try to find service on portal
                await self._page.goto(self.config.portal_url, wait_until='networkidle')

                # Search for service
                search_result = await self._search_service(service_name)
                if not search_result:
                    return False
            else:
                full_url = self.config.portal_url + service_url
                await self._page.goto(full_url, wait_until='networkidle')

            # Wait for service page to load
            await self._page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)

            return True

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False

    async def _search_service(self, service_name: str) -> bool:
        """Search for service on portal"""
        try:
            # Look for search box
            search_box = await self._page.query_selector('input[type="search"], input[placeholder*="search" i]')
            if search_box:
                await search_box.fill(service_name)
                await self._page.keyboard.press('Enter')
                await asyncio.sleep(2)

                # Click on service link
                service_link = await self._page.query_selector(f'a:has-text("{service_name}")')
                if service_link:
                    await service_link.click()
                    return True
            return False
        except Exception as e:
            logger.error(f"Service search failed: {e}")
            return False

    async def _process_documents(self, documents: List[str], service_name: str) -> List[Dict]:
        """Process documents for service"""
        processed = []

        for doc_path in documents:
            try:
                # Get required doc type from service config
                service_config = self.config.services.get(self._current_service, {})
                required_docs = service_config.get('documents', [])

                # Validate each document
                for doc_type in required_docs:
                    validation = await self.doc_processor.validate_document(doc_path, doc_type)
                    if validation.get("valid"):
                        processed.append({
                            "path": doc_path,
                            "type": doc_type,
                            "valid": True
                        })
                    else:
                        await self.voice.speak(f"Document {doc_type} valid nahi hai: {validation.get('error')}")

            except Exception as e:
                logger.error(f"Document processing failed: {e}")

        return processed

    async def _fill_form(self, service_name: str, user_data: Dict[str, Any]) -> bool:
        """Fill service form"""
        try:
            # Get form fields
            form_fields = await self._get_form_fields()

            if not form_fields:
                # Try to extract from page
                form_fields = await self._extract_form_fields()

            # Map user data to form fields using LLM
            mapping = await self.llm.map_to_form_fields(user_data, form_fields)

            # Fill each field
            for field_label, value in mapping.items():
                if value:
                    success = await self._fill_field(field_label, value)
                    if not success:
                        # Try PyAutoGUI fallback
                        await self._fallback_fill_field(field_label, value)

            return True

        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            return False

    async def _get_form_fields(self) -> List[str]:
        """Get form field labels from page"""
        try:
            labels = await self._page.query_selector_all('label')
            fields = []
            for label in labels:
                text = await label.inner_text()
                if text.strip():
                    fields.append(text.strip())
            return fields
        except:
            return []

    async def _extract_form_fields(self) -> List[str]:
        """Extract form fields using PyAutoGUI fallback"""
        if self.pyautogui_fallback.is_ready():
            # Take screenshot and analyze
            # This would use template matching to find form fields
            pass
        return []

    async def _fill_field(self, field_label: str, value: str) -> bool:
        """Fill a form field by label"""
        try:
            # Try multiple selectors
            selectors = [
                f'input[aria-label*="{field_label}" i]',
                f'input[placeholder*="{field_label}" i]',
                f'input[name*="{field_label.lower()}"]',
                f'select[aria-label*="{field_label}" i]',
                f'textarea[aria-label*="{field_label}" i]',
                f'input[id*="{field_label.lower()}"]',
            ]

            for selector in selectors:
                element = await self._page.query_selector(selector)
                if element:
                    await element.fill(value)
                    return True

            # Try by label text
            label = await self._page.query_selector(f'label:has-text("{field_label}")')
            if label:
                input_id = await label.get_attribute('for')
                if input_id:
                    input_elem = await self._page.query_selector(f'#{input_id}')
                    if input_elem:
                        await input_elem.fill(value)
                        return True

            return False

        except Exception as e:
            logger.error(f"Field fill failed: {e}")
            return False

    async def _fallback_fill_field(self, field_label: str, value: str) -> bool:
        """Use PyAutoGUI to fill field"""
        if not self.pyautogui_fallback.is_ready():
            return False

        # Try to find field by template
        template_name = f"field_{field_label.lower().replace(' ', '_')}"
        if self.pyautogui_fallback.click_template(f"field_{field_label.lower()}"):
            time.sleep(0.2)
            self.pyautogui_fallback.type_in_field(value)
            return True

        return False

    async def _upload_documents(self, documents: List[Dict]) -> bool:
        """Upload processed documents"""
        try:
            for doc in documents:
                if not doc.get("valid"):
                    continue

                file_path = doc.get("processed_path") or doc.get("path")
                if not file_path or not os.path.exists(file_path):
                    continue

                # Find file input
                file_input = await self._page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(file_path)
                    await asyncio.sleep(1)

                    # Wait for upload
                    await self._wait_for_upload()

            return True
        except Exception as e:
            logger.error(f"Document upload failed: {e}")
            return False

    async def _wait_for_upload(self):
        """Wait for file upload to complete"""
        try:
            # Wait for upload progress to disappear
            await self._page.wait_for_selector('.upload-progress, .loading', state='hidden', timeout=30000)
        except:
            await asyncio.sleep(2)

    async def _handle_payment(self) -> bool:
        """Handle payment process"""
        try:
            # Check for payment button
            pay_btn = await self._page.query_selector('button:has-text("Pay"), button:has-text("Payment"), a:has-text("Pay")')
            if pay_btn:
                await pay_btn.click()
                await self._page.wait_for_load_state('networkidle')

                # Handle payment gateway
                # This would need specific implementation per gateway
                await self.voice.speak("Payment gateway khula hai. Payment complete karein.")

                # Wait for payment completion
                await self.voice.speak("Payment complete hone ka wait kar raha hoon.")
                await asyncio.sleep(5)

                return True

            return True  # No payment needed
        except Exception as e:
            logger.error(f"Payment handling failed: {e}")
            return False

    async def _download_receipt(self, service_name: str) -> Optional[str]:
        """Download receipt PDF"""
        try:
            # Look for download/print button
            download_btn = await self._page.query_selector(
                'button:has-text("Download"), button:has-text("Receipt"), button:has-text("Print"), a:has-text("Download")'
            )

            if download_btn:
                # Set up download handler
                async with self._page.expect_download() as download_info:
                    await download_btn.click()

                download = await download_info.value
                receipt_path = f"./output/receipt_{self._current_service}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                await download.save_as(receipt_path)

                # Log receipt in database
                await self.db.save_receipt({
                    "id": f"rcpt_{datetime.now().timestamp()}",
                    "task_id": f"emitra_{datetime.now().timestamp()}",
                    "service": service_name,
                    "amount": 0,  # Would extract from page
                    "receipt_path": receipt_path,
                    "downloaded_at": datetime.now()
                })

                return receipt_path

            return None
        except Exception as e:
            logger.error(f"Receipt download failed: {e}")
            return None

    async def close(self):
        """Close browser"""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("eMitraBot closed")
        except Exception as e:
            logger.error(f"Close error: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "ready": self.is_ready,
            "logged_in": self._logged_in,
            "current_service": self._current_service,
            "status": self._status.value
        }