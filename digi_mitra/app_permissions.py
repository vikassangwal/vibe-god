"""
Digi Mitra Permission & App Access Control Manager
Ensures Digi Mitra can ONLY access and control apps explicitly permitted by the user.
Zero unauthorized app access.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

class AppPermissionManager:
    def __init__(self, config_path: str = './data/app_permissions.json'):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.permissions = self._load_permissions()

    def _load_permissions(self) -> Dict[str, bool]:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default: strict explicit whitelist
        default_perms = {
            'chrome': True,
            'tradingview': True,
            'zerodha': False,
            'groww': False,
            'emitra': True,
            'calculator': True,
            'notepad': True,
            'whatsapp': False,
            'gallery': False,
            'system_settings': False
        }
        self._save_permissions(default_perms)
        return default_perms

    def _save_permissions(self, perms: Dict[str, bool]):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(perms, f, indent=2)
        except Exception:
            pass

    def is_app_allowed(self, app_name: str) -> bool:
        """Check if an app has explicit permission to be accessed/controlled"""
        app_lower = app_name.lower().strip()
        for allowed_app, is_allowed in self.permissions.items():
            if allowed_app in app_lower or app_lower in allowed_app:
                return is_allowed
        # Default deny if not in whitelist
        return False

    SENSITIVE_HIGH_RISK_APPS = ['whatsapp', 'gallery', 'photos', 'system_settings', 'passwords', 'banking']

    def is_sensitive_app(self, app_name: str) -> bool:
        """Returns True if app is extremely sensitive (WhatsApp, Gallery, Passwords)"""
        name = app_name.lower()
        return any(s in name for s in self.SENSITIVE_HIGH_RISK_APPS)

    def request_access_with_security_alert(self, app_name: str) -> Dict[str, Any]:
        """
        If app is sensitive, issues a prominent SECURITY ALERT requiring explicit user confirmation.
        """
        name = app_name.lower().strip()
        is_sensitive = self.is_sensitive_app(name)
        allowed = self.is_app_allowed(name)

        if not allowed:
            return {
                'allowed': False,
                'requires_user_override': True,
                'security_alert': f'âš ï¸ HIGH SECURITY ALERT: {app_name.upper()} ek private/sanvedansheel app hai! Yeh by-default blocked hai.',
                'prompt': f'Kya aap sach mein Digi Mitra ko {app_name.upper()} access karne ki anumati dena chahte hain? (Security Alert)'
            }

        return {
            'allowed': True,
            'security_alert': f'ðŸ”” NOTICE: {app_name.upper()} aapki anugya (permission) se use kiya ja raha hai.',
            'requires_user_override': False
        }

    def set_permission(self, app_name: str, allow: bool):
        """Allow or revoke permission for an app"""
        self.permissions[app_name.lower().strip()] = allow
        self._save_permissions(self.permissions)

    def get_all_permissions(self) -> Dict[str, bool]:
        return self.permissions

