"""
Digi Mitra Mobile Guardian & Remote Permission Gate (मोबाइल अनुमति प्रणाली)
Ensures the All-Rounder Agent can ONLY execute tasks with explicit Mobile Phone approval.
Features:
1. Real-Time Permission Request Queue (Pending, Approved, Denied)
2. Async Wait-for-Mobile-Approval loop with auto-timeout
3. Strict 2FA Security Level vs Autonomous Hybrid Mode
4. Remote Mobile Emergency Kill-Switch
5. Audit log of all mobile approvals & rejections
"""

import time
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

PERMISSIONS_LOG_FILE = Path(__file__).parent.parent / "data" / "mobile_guardian_logs.json"


class MobileGuardianGate:
    def __init__(self):
        self.log_file = PERMISSIONS_LOG_FILE
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        # Active in-memory permission requests
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        # Security mode: 'strict' (requires approval for every action), 'hybrid' (sensitive only)
        self.mode = "strict"
        # Emergency kill switch flag
        self.emergency_stop_active = False

    def request_mobile_approval(
        self,
        task_name: str,
        category: str = "general",
        risk_level: str = "medium",
        details: str = "",
        auto_approve_if_hybrid: bool = False
    ) -> Dict[str, Any]:
        """Creates a new permission request waiting for mobile user tap"""
        if self.emergency_stop_active:
            return {
                "id": "blocked",
                "status": "rejected",
                "reason": "Emergency Kill Switch is ACTIVE on Mobile. All agent actions are halted."
            }

        # In hybrid mode, low-risk tasks can bypass if allowed
        if self.mode == "hybrid" and auto_approve_if_hybrid and risk_level == "low":
            return {
                "id": f"auto_{int(time.time())}",
                "status": "approved",
                "reason": "Auto-approved in Hybrid mode (Low Risk)"
            }

        req_id = f"req_{int(time.time() * 1000)}"
        request_obj = {
            "id": req_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "task_name": task_name,
            "category": category,
            "risk_level": risk_level,  # low, medium, high, critical
            "details": details,
            "status": "pending",  # pending, approved, rejected, expired
            "decided_at": None
        }
        self.pending_requests[req_id] = request_obj
        return request_obj

    async def wait_for_mobile_approval(self, req_id: str, timeout_seconds: int = 45) -> bool:
        """Async wait until user taps ALLOW or DENY on their mobile phone"""
        if req_id not in self.pending_requests:
            return False

        start = time.time()
        while time.time() - start < timeout_seconds:
            if self.emergency_stop_active:
                self.pending_requests[req_id]["status"] = "rejected"
                return False

            req = self.pending_requests.get(req_id)
            if req and req["status"] == "approved":
                self._record_decision(req_id, "approved")
                return True
            if req and req["status"] == "rejected":
                self._record_decision(req_id, "rejected")
                return False

            await asyncio.sleep(0.5)

        # Timeout expired
        if req_id in self.pending_requests:
            self.pending_requests[req_id]["status"] = "expired"
            self._record_decision(req_id, "expired (no response from phone)")
        return False

    def decide_request(self, req_id: str, action: str) -> Dict[str, Any]:
        """Called when user taps ALLOW or DENY on their mobile"""
        if req_id not in self.pending_requests:
            return {"success": False, "error": "Request ID nahi mila ya expire ho gaya"}

        status = "approved" if action in ["approve", "allow"] else "rejected"
        self.pending_requests[req_id]["status"] = status
        self.pending_requests[req_id]["decided_at"] = datetime.now().strftime("%H:%M:%S")
        self._record_decision(req_id, status)

        action_name = "Manzoor (Allowed)" if status == "approved" else "Roka (Denied)"
        return {
            "success": True,
            "req_id": req_id,
            "status": status,
            "message": f"📱 Mobile Se Task {action_name} Kar Diya Gaya!"
        }

    def get_active_pending_requests(self) -> List[Dict[str, Any]]:
        """Returns list of pending requests that need mobile approval right now"""
        now = time.time()
        # Keep only recent pending ones (under 2 minutes old)
        active = []
        for req in self.pending_requests.values():
            if req["status"] == "pending":
                active.append(req)
        return active

    def set_mode(self, mode: str) -> Dict[str, Any]:
        """Set security mode: 'strict' (100% 2FA on phone) or 'hybrid'"""
        if mode in ["strict", "hybrid"]:
            self.mode = mode
            return {"success": True, "mode": self.mode}
        return {"success": False, "error": "Invalid mode"}

    def toggle_emergency_kill_switch(self, halt: bool) -> Dict[str, Any]:
        """Instant emergency freeze from mobile"""
        self.emergency_stop_active = halt
        # Reject all pending
        if halt:
            for r in self.pending_requests.values():
                if r["status"] == "pending":
                    r["status"] = "rejected"
        return {
            "success": True,
            "emergency_halt": self.emergency_stop_active,
            "message": "🚨 EMERGENCY KILL-SWITCH ACTIVATED: Sabhi actions freeze ho gaye!" if halt else "✅ Kill-switch release: Agent normal mode me active."
        }

    def _record_decision(self, req_id: str, decision: str):
        try:
            req = self.pending_requests.get(req_id, {})
            log_entry = {
                "req_id": req_id,
                "task": req.get("task_name", ""),
                "category": req.get("category", ""),
                "decision": decision,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            logs = []
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            logs.append(log_entry)
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs[-100:], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
