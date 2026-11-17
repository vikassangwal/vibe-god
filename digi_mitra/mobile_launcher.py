\"\"\"
Digi Mitra Mobile Deep-Link & Auto-Open App Controller
- Automatically launches permitted apps on Mobile devices via native OS intent / URL schemes:
  * Zerodha / Trading: kite://, groww://, tradingview://
  * Social/Gov: twitter://, whatsapp:// (only with explicit permission)
  * System tools: tel:, mailto:, sms:
- Strictly enforces permission check & flashes High Security Alert before opening
\"\"\"

from typing import Dict, Any

class MobileAppLauncherEngine:
    def __init__(self, permission_mgr):
        self.permission_mgr = permission_mgr
        self.app_schemes = {
            'tradingview': 'https://in.tradingview.com/chart/',
            'groww': 'groww://',
            'zerodha': 'kite://',
            'chrome': 'googlechrome://',
            'emitra': 'https://sso.rajasthan.gov.in',
            'whatsapp': 'whatsapp://send'
        }

    def prepare_mobile_launch(self, app_name: str) -> Dict[str, Any]:
        app_clean = app_name.lower().strip()
        scheme_url = self.app_schemes.get(app_clean, f'{app_clean}://')

        # Check permission
        allowed = self.permission_mgr.is_app_allowed(app_clean)

        if not allowed:
            return {
                'can_open': False,
                'app_name': app_name,
                'alert': f'🚨 HIGH SECURITY ALERT: {app_name.upper()} ko mobile par auto-open karne ki permission nahi hai!',
                'instruction': 'Kripya dashboard mein App Permission ON karein.'
            }

        return {
            'can_open': True,
            'app_name': app_name,
            'scheme_url': scheme_url,
            'alert': f'🔔 NOTICE: {app_name.upper()} aapki permission se phone par auto-open ho raha hai.',
            'message': f'Mobile par {app_name.upper()} launch kiya ja raha hai...'
        }
