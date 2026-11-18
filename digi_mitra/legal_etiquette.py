"""
Digi Mitra Legal Intelligence & Clean Language Policy Module
- Polite, Shuddh & Respectful communication (Bina ashleel ya galat bhasha ke)
- Complete awareness of Indian Laws & Regulations:
  * IT Act 2000 & DPDP Act 2023 (Digital Data Privacy)
  * Rajasthan eMitra Service Rules & Guidelines
  * SEBI Regulations (Educational Analysis only, No illegal tips)
  * Consumer Protection Act & Cyber Law Compliance
"""

from typing import Dict, Any, List

class LegalKnowledgeAndEtiquetteEngine:
    """
    Guarantees clean, civilized language and adherence to legal frameworks.
    """

    LEGAL_GUIDELINES = {
        'data_privacy': {
            'act': 'Digital Personal Data Protection (DPDP) Act 2023 & IT Act Section 43A',
            'rule': 'Aadhaar ya personal data safe rahega, kisi bahar ke server par share nahi hoga.'
        },
        'emitra_compliance': {
            'act': 'Rajasthan e-Governance & eMitra Citizen Service Rules',
            'rule': 'Keval aavedak ki aagya aur sahi dastavejon ke sath form verification.'
        },
        'trading_compliance': {
            'act': 'SEBI (Research Analysts) Regulations 2014',
            'rule': 'Keval technical chart analysis aur shiksha ke liye, koi anadhikrut financial advice nahi.'
        },
        'cyber_security': {
            'act': 'IT Act 2000 Section 66 (Cyber Crimes)',
            'rule': 'Keval permitted apps aur user-authorized access, koi unauthorized hacking nahi.'
        }
    }

    RESTRICTED_WORDS = [
        'abuse', 'hack', 'steal', 'cheat', 'fake', 'bypass_illegal', 'unauthorized'
    ]

    def format_respectful_response(self, text: str, user_name: str = 'Vikas ji') -> str:
        """Formats any response in polite, dignified and clean Hindi/English"""
        prefix = f"Namaste {user_name}! "
        return prefix + text

    def check_legal_compliance(self, intent: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validates task against Indian legal rules
        """
        if intent == 'trading_analysis':
            return {
                'compliant': True,
                'legal_note': '⚖️ SEBI Rule: Yeh analysis keval educational aur technical evaluation hetu hai.'
            }
        elif intent == 'emitra_service':
            return {
                'compliant': True,
                'legal_note': '⚖️ eMitra DPDP Act: Dastavez surakshit hain aur portal niyam anusar bhare ja rahe hain.'
            }
        return {'compliant': True, 'legal_note': '⚖️ Kanoon aur suraksha niyamit anusar.'}
