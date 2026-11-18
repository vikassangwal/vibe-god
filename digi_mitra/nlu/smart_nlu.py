"""
Digi Mitra NLU (Natural Language Understanding)
Smarts to understand broken language, Hinglish, typos, and Hindi-English mixes.
Works offline with fuzzy matching + regex + local LLM fallback.
"""

import re
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher

class SmartNLU:
    """
    Understands commands even if spelling is wrong or grammar is broken:
    e.g. 'trede analisas kro', 'emitra ka jan adhar bhr do', 'vedio aditing krdo'
    """
    
    INTENT_KEYWORDS = {
        'trading_analysis': [
            'trade', 'trede', 'trd', 'trading', 'analis', 'analisas', 'analysis', 
            'chart', 'chert', 'candlestick', 'nifty', 'banknifty', 'share', 'stock',
            'share market', 'sheyar', 'pattern', 'pertan', 'drov', 'draw'
        ],
        'emitra_service': [
            'emitra', 'e-mitra', 'imita', 'jan aadhaar', 'janadhar', 'aadhar', 'adhar',
            'bonafide', 'mool niwas', 'jati', 'caste', 'certificate', 'praman patra',
            'ration', 'sso', 'rajasthan'
        ],
        'video_edit': [
            'video', 'vedio', 'vdo', 'edit', 'adit', 'aditing', 'editing', 'cut',
            'trim', 'subtitles', 'reel', 'reels', 'shorts', 'crop'
        ],
        'research': [
            'deep research', 'khoj', 'dhoondho', 'khojo', 'deep study'
        ],
        'mandi_farming': [
            'mandi', 'mndy', 'kheti', 'fasal', 'khet', 'rate', 'bhav', 'enam',
            'gehu', 'sarson', 'chana', 'bajra', 'price'
        ],
        'system_status': [
            'status', 'stetus', 'kaise ho', 'chal raha hai', 'free space', 'battery',
            'system', 'cpu', 'memory'
        ]
    }

    def __init__(self, local_llm=None):
        self.llm = local_llm

    def _fuzzy_score(self, word1: str, word2: str) -> float:
        return SequenceMatcher(None, word1.lower(), word2.lower()).ratio()

    def parse_intent(self, text: str) -> Dict[str, Any]:
        text_clean = text.lower().strip()
        words = re.findall(r'\b\w+\b', text_clean)
        
        intent_scores = {intent: 0.0 for intent in self.INTENT_KEYWORDS}
        
        for word in words:
            for intent, keywords in self.INTENT_KEYWORDS.items():
                for kw in keywords:
                    if kw in word or word in kw:
                        intent_scores[intent] += 1.5
                    else:
                        score = self._fuzzy_score(word, kw)
                        if score >= 0.75:
                            intent_scores[intent] += score
        
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent]
        
        # If very low confidence, fallback to general research / ask
        if confidence < 0.8:
            best_intent = 'general_assistance'
            
        return {
            'original_text': text,
            'intent': best_intent,
            'confidence': round(confidence, 2),
            'action_summary': self._get_hindi_summary(best_intent, text)
        }

    def _get_hindi_summary(self, intent: str, query: str) -> str:
        summaries = {
            'trading_analysis': f'Trading & Chart Analysis execute kiya ja raha hai ({query})',
            'emitra_service': f'eMitra / Sarkari Seva task shuru kiya ja raha hai ({query})',
            'video_edit': f'Video Editing task execute kiya ja raha hai ({query})',
            'research': f'Internet & Knowledge Base par Autonomous Research ho rahi hai ({query})',
            'mandi_farming': f'Mandi Bhav aur Fasal status fetch kiya ja raha hai ({query})',
            'system_status': 'Digi Mitra system status report tayyar ki ja rahi hai',
            'general_assistance': f'Digi Mitra aapke command par kaam kar raha hai: {query}'
        }
        return summaries.get(intent, 'Task execute ho raha hai')

