"""
Digi Mitra History & Lifelong Experience Learning Engine
- Stores every conversation, task, result and feedback
- Analyzes past experiences to self-improve and learn:
  * What succeeded vs what failed
  * User preferences and habits
  * Best ways to answer and execute tasks
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class HistoryLearningEngine:
    def __init__(self, history_file: str = './data/chat_history_memory.json'):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def record_interaction(self, user_msg: str, bot_reply: str, intent: str, feedback: str = 'neutral'):
        """Save interaction permanently into lifelong history"""
        entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': user_msg,
            'reply': bot_reply,
            'intent': intent,
            'feedback': feedback
        }
        self.history.append(entry)
        self._save_history()

    def extract_learnings(self) -> Dict[str, Any]:
        """
        Inspects past history to extract insights & habits
        """
        total_interactions = len(self.history)
        intents_count = {}
        for item in self.history:
            intent = item.get('intent', 'general')
            intents_count[intent] = intents_count.get(intent, 0) + 1

        top_interests = sorted(intents_count.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            'total_conversations_remembered': total_interactions,
            'top_interests': [f'{k} ({v} baar)' for k, v in top_interests],
            'learned_summary': f'Digi Mitra ne pichli {total_interactions} baatcheeton se aapki aadat aur pasand ko yaad rakha hai.'
        }

    def get_recent_history(self, limit: int = 15) -> List[Dict[str, Any]]:
        return self.history[-limit:]
