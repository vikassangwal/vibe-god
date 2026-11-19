"""
Digi Mitra Sovereign All-Rounder Master Agent (ऑल-राउंडर सुपर-एजेंट)
Controls EVERYTHING on user machine, but strictly gated by Mobile Permission Gate:
1. Screen Control & Desktop Automation
2. eMitra & Government Services
3. WhatsApp Dispatch & Communication
4. Legal & Sarkari Form PDF Generation
5. Live Market & Trading Execution
6. AI Reels & Video Rendering
7. Live Sarkari Yojna & Vacancy Scanning
8. Online Work & File Management
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime


class SovereignAllRounderAgent:
    def __init__(
        self,
        mobile_guardian,
        screen_worker,
        whatsapp_bot,
        form_pdf_gen,
        yojna_radar,
        reels_gen,
        trading_engine,
        llm_engine
    ):
        self.mobile_guardian = mobile_guardian
        self.screen_worker = screen_worker
        self.whatsapp_bot = whatsapp_bot
        self.form_pdf_gen = form_pdf_gen
        self.yojna_radar = yojna_radar
        self.reels_gen = reels_gen
        self.trading_engine = trading_engine
        self.llm_engine = llm_engine

    async def execute_task_with_mobile_gate(
        self,
        task_name: str,
        category: str,
        risk_level: str,
        details: str,
        action_callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gated Execution:
        1. Asks user on mobile phone
        2. Waits for user to tap ALLOW or DENY on their phone
        3. Executes if approved, halts if denied
        """
        # Step 1: Request permission on Mobile
        req = self.mobile_guardian.request_mobile_approval(
            task_name=task_name,
            category=category,
            risk_level=risk_level,
            details=details,
            auto_approve_if_hybrid=True
        )

        # If already auto-approved (e.g. low risk in hybrid mode)
        if req.get("status") == "approved":
            res = await action_callable(*args, **kwargs) if asyncio.iscoroutinefunction(action_callable) else action_callable(*args, **kwargs)
            return {"approved": True, "result": res}

        # Step 2: Wait for mobile approval (up to 45 seconds)
        req_id = req["id"]
        approved = await self.mobile_guardian.wait_for_mobile_approval(req_id, timeout_seconds=45)

        if not approved:
            return {
                "approved": False,
                "error": f"🛑 Task '{task_name}' roka gaya: Mobile se permission nahi mili ya Deny kar diya gaya.",
                "req_id": req_id
            }

        # Step 3: Mobile user allowed it! Execute immediately
        res = await action_callable(*args, **kwargs) if asyncio.iscoroutinefunction(action_callable) else action_callable(*args, **kwargs)
        return {
            "approved": True,
            "message": f"📱 Mobile se permission mil gayi! Task successfully execute ho gaya.",
            "result": res
        }
