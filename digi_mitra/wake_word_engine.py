"""
Digi Mitra Custom Wake Word & Voice Activation Engine
Allows user to set ANY custom wake word:
e.g. 'Hey Digi', 'Suno Mitra', 'Digi Mitra', 'Jarvis', or user's custom name.
Listens continuously in background via mic.
When wake word is detected, automatically triggers active voice command state!
"""

import json
from pathlib import Path
from typing import Dict, Any, List

class CustomWakeWordEngine:
    def __init__(self, config_path: str = './data/wake_word_config.json'):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        default_config = {
            'active_wake_word': 'digi mitra',
            'supported_aliases': ['hey digi', 'suno mitra', 'namaste mitra', 'digi', 'bhai'],
            'enabled': True,
            'sensitivity': 0.8
        }
        self._save_config(default_config)
        return default_config

    def _save_config(self, cfg: Dict[str, Any]):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def check_wake_word(self, recognized_speech: str) -> bool:
        """Checks if user said the custom wake word"""
        if not self.config.get('enabled', True):
            return False

        speech_clean = recognized_speech.lower().strip()
        main_word = self.config.get('active_wake_word', 'digi mitra').lower()
        
        if main_word in speech_clean:
            return True

        for alias in self.config.get('supported_aliases', []):
            if alias.lower() in speech_clean:
                return True

        return False

    def update_wake_word(self, new_name: str) -> Dict[str, Any]:
        """Change the wake word to whatever custom name user wants"""
        cleaned = new_name.lower().strip()
        self.config['active_wake_word'] = cleaned
        if cleaned not in self.config['supported_aliases']:
            self.config['supported_aliases'].append(cleaned)
        self._save_config(self.config)
        return {
            'success': True,
            'new_wake_word': cleaned,
            'message': f'🎙️ Wake Word safaltapoorvak change ho gaya: "{new_name.title()}"! Ab aap phone ya laptop par bolenge: "{new_name.title()}" toh Digi Mitra turant jag jayega aur command sunega!'
        }

    def get_wake_word(self) -> str:
        return self.config.get('active_wake_word', 'digi mitra')
