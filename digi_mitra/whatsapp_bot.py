"""
Digi Mitra WhatsApp Automation Bot (100% Free - No Paid Meta API needed)
Capabilities:
- Generates 1-click WhatsApp web & mobile direct dispatch links (wa.me)
- Desktop auto-typing & dispatch via PyAutoGUI & default browser
- Pre-built templates: eMitra Receipts, Mandi Rates, Trading Alerts, Legal Invoices
- Delivery history & contact management
"""

import os
import urllib.parse
import webbrowser
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None


class WhatsAppAutomationBot:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_dir / "whatsapp_sent_logs.json"

    def clean_phone_number(self, phone: str) -> str:
        """Formats phone number into international digits without + or spaces"""
        digits = "".join([c for c in phone if c.isdigit()])
        if len(digits) == 10:
            return "91" + digits  # Default India country code
        if digits.startswith("0") and len(digits) == 11:
            return "91" + digits[1:]
        return digits

    def create_whatsapp_url(self, phone: str, message: str) -> str:
        """Creates official WhatsApp Click-to-Chat deep link"""
        clean_phone = self.clean_phone_number(phone)
        encoded_msg = urllib.parse.quote(message)
        return f"https://wa.me/{clean_phone}?text={encoded_msg}"

    def send_via_browser(self, phone: str, message: str, auto_press_enter: bool = False) -> Dict[str, Any]:
        """
        Opens WhatsApp with pre-filled message.
        If auto_press_enter is True, waits for load and simulates Enter.
        """
        clean_phone = self.clean_phone_number(phone)
        url = self.create_whatsapp_url(clean_phone, message)

        try:
            webbrowser.open(url)
            if auto_press_enter and pyautogui:
                # Give browser time to load WhatsApp Web
                time.sleep(4.0)
                pyautogui.press('enter')

            self._log_sent(clean_phone, message, "BROWSER_DISPATCH")
            return {
                "success": True,
                "phone": clean_phone,
                "whatsapp_url": url,
                "message": f"📱 WhatsApp chat open kar diya gaya hai (+{clean_phone}) ke liye!"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "whatsapp_url": url}

    def format_template(self, template_type: str, data: Dict[str, Any]) -> str:
        """Builds customized Hinglish WhatsApp message templates"""
        now_str = datetime.now().strftime("%d/%m/%Y, %I:%M %p")

        if template_type == "emitra_receipt":
            return (
                f"🏛️ *DIGI MITRA — eMitra Service Acknowledgment*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Grahak:* {data.get('customer_name', 'Vikas ji')}\n"
                f"📋 *Service:* {data.get('service_name', 'Jan Aadhaar / Caste Certificate')}\n"
                f"🔢 *Token/Ref No:* {data.get('token_no', 'RAJE-2026-88491')}\n"
                f"💰 *Fee Paid:* ₹{data.get('amount', '50')}\n"
                f"📅 *Tarikh:* {now_str}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"✅ *Status:* Successfully Portal Par Process Ho Gaya!\n"
                f"🙏 Dhanyawad! Digi Mitra Sovereign Services."
            )

        elif template_type == "mandi_rates":
            return (
                f"🌾 *DIGI MITRA — Mandi Live Bhav Update*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📍 *Mandi:* {data.get('mandi', 'Jaipur / Kota APMC')}\n"
                f"📅 *Tarikh:* {now_str}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"• Sarson (Mustard): ₹5,850 - ₹6,100 / Qtl\n"
                f"• Gehun (Wheat): ₹2,450 - ₹2,620 / Qtl\n"
                f"• Chana (Gram): ₹5,900 - ₹6,150 / Qtl\n"
                f"• Guar Seed: ₹5,300 - ₹5,480 / Qtl\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💡 *Bhav Trend:* Steady to Strong Demand!"
            )

        elif template_type == "trading_alert":
            return (
                f"📈 *DIGI MITRA — Live Trade & Market Signal*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Asset:* {data.get('symbol', 'NIFTY 50')}\n"
                f"🎯 *Signal:* {data.get('signal', 'BULLISH REVERSAL')}\n"
                f"💵 *Level:* ₹{data.get('price', '24,500')}\n"
                f"🛑 *Stop-Loss:* ₹{data.get('sl', '24,350')}\n"
                f"🎯 *Target:* ₹{data.get('target', '24,800')}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚖️ *Disclaimer:* For Educational & Analysis Purpose."
            )

        else:
            return f"👑 *Digi Mitra Notice:*\n{data.get('custom_text', 'Hello from Digi Mitra AI Agent!')}\n\n📅 {now_str}"

    def _log_sent(self, phone: str, text: str, method: str):
        import json
        logs = []
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []
        logs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "phone": phone,
            "snippet": text[:80],
            "method": method
        })
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs[-50:], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
