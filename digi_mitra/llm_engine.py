"""
Digi Mitra Multi-Provider LLM & Cloud API Engine
Supports:
- Google Gemini (Gemini 2.0 / 1.5 Flash)
- Groq (Llama 3.3 70B, Mixtral) - Ultra Fast & Free Tier
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic Claude (Claude 3.5 Sonnet / Haiku)
- OpenRouter (DeepSeek R1/V3, Llama 3)
- Local Ollama (Self-hosted models)
- Local Offline Mode (Graceful fallback)
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import httpx

CONFIG_FILE = Path(__file__).parent.parent / "data" / "api_config.json"

DEFAULT_SYSTEM_PROMPT = (
    "Aap 'Digi Mitra' (डिजी मित्र) hain — Vikas ji ke personal, sovereign AI super-agent aur desi dost. "
    "Aap Hindi, Hinglish aur English me naturally baat karte hain. "
    "Aapka vyavahar hamesha madadgar, tez, thoda desi/dostana aur sammanit (respectful) hota hai. "
    "User ke sawalon ke direct, accurate aur behtareen answers dein. "
    "Robotic baatein mat karein, real human saathi ki tarah guide karein."
)

DEFAULT_CONFIG: Dict[str, Any] = {
    "active_provider": "local",
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "providers": {
        "gemini": {
            "name": "Google Gemini",
            "api_key": "",
            "model": "gemini-1.5-flash",
            "available_models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]
        },
        "groq": {
            "name": "Groq (Super Fast & Free)",
            "api_key": "",
            "model": "llama-3.3-70b-versatile",
            "available_models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
        },
        "openai": {
            "name": "OpenAI",
            "api_key": "",
            "model": "gpt-4o-mini",
            "available_models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        },
        "anthropic": {
            "name": "Anthropic Claude",
            "api_key": "",
            "model": "claude-3-5-haiku-20241022",
            "available_models": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"]
        },
        "openrouter": {
            "name": "OpenRouter",
            "api_key": "",
            "model": "deepseek/deepseek-chat",
            "available_models": ["deepseek/deepseek-chat", "meta-llama/llama-3.3-70b-instruct", "google/gemini-flash-1.5"]
        },
        "ollama": {
            "name": "Ollama (Local Server)",
            "url": "http://localhost:11434",
            "model": "llama3:8b",
            "available_models": ["llama3:8b", "mistral:latest", "qwen2.5:latest"]
        }
    }
}


class LLMEngine:
    def __init__(self):
        self.config_path = CONFIG_FILE
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or initialize with defaults"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(cfg)
                    return merged
        except Exception as e:
            print(f"[LLMEngine] Warning: Could not load config: {e}")

        cfg = DEFAULT_CONFIG.copy()
        if os.environ.get("GEMINI_API_KEY"):
            cfg["providers"]["gemini"]["api_key"] = os.environ["GEMINI_API_KEY"]
            cfg["active_provider"] = "gemini"
        elif os.environ.get("GROQ_API_KEY"):
            cfg["providers"]["groq"]["api_key"] = os.environ["GROQ_API_KEY"]
            cfg["active_provider"] = "groq"
        elif os.environ.get("OPENAI_API_KEY"):
            cfg["providers"]["openai"]["api_key"] = os.environ["OPENAI_API_KEY"]
            cfg["active_provider"] = "openai"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            cfg["providers"]["anthropic"]["api_key"] = os.environ["ANTHROPIC_API_KEY"]

        self._save_to_disk(cfg)
        return cfg

    def _save_to_disk(self, cfg: Dict[str, Any]):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[LLMEngine] Error saving config: {e}")

    def get_public_config(self) -> Dict[str, Any]:
        """Returns config with masked API keys for secure frontend display"""
        pub = json.loads(json.dumps(self.config))
        for p_key, p_data in pub.get("providers", {}).items():
            raw_key = p_data.get("api_key", "")
            if raw_key:
                if len(raw_key) > 8:
                    masked = raw_key[:4] + "••••••••" + raw_key[-4:]
                else:
                    masked = "••••••••"
                p_data["api_key_masked"] = masked
                p_data["has_key"] = True
            else:
                p_data["api_key_masked"] = ""
                p_data["has_key"] = False
            p_data.pop("api_key", None)
        return pub

    def update_provider_config(self, provider: str, api_key: Optional[str] = None, model: Optional[str] = None, set_active: bool = False) -> Dict[str, Any]:
        """Update provider API key and model"""
        if provider not in self.config.get("providers", {}) and provider != "local":
            return {"success": False, "message": f"Unknown provider: {provider}"}

        if provider != "local":
            p_entry = self.config["providers"][provider]
            if api_key is not None and api_key.strip():
                p_entry["api_key"] = api_key.strip()
            if model is not None and model.strip():
                p_entry["model"] = model.strip()

        if set_active:
            self.config["active_provider"] = provider

        self._save_to_disk(self.config)
        return {
            "success": True,
            "message": f"{provider.upper()} configuration save ho gayi hai!",
            "active_provider": self.config["active_provider"]
        }

    def set_active_provider(self, provider: str) -> Dict[str, Any]:
        if provider not in self.config.get("providers", {}) and provider != "local":
            return {"success": False, "message": f"Invalid provider: {provider}"}
        self.config["active_provider"] = provider
        self._save_to_disk(self.config)
        return {"success": True, "active_provider": provider}

    def get_effective_key(self, provider: str) -> str:
        """Fetch API key from config or environment"""
        key = self.config.get("providers", {}).get(provider, {}).get("api_key", "").strip()
        if key:
            return key
        env_map = {
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        env_var = env_map.get(provider)
        if env_var and os.environ.get(env_var):
            return os.environ[env_var]
        return ""

    async def test_connection(self, provider: str, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Test API connection with a lightweight prompt"""
        test_key = api_key.strip() if api_key and api_key.strip() else self.get_effective_key(provider)
        if not test_key and provider not in ["local", "ollama"]:
            return {"success": False, "error": "API Key khali hai! Kripya valid key darj karein."}

        p_info = self.config.get("providers", {}).get(provider, {})
        test_model = model or p_info.get("model", "")
        start_time = time.time()

        try:
            if provider == "gemini":
                reply = await self._call_gemini(test_key, test_model, "Batao kya aap active ho? Ek line me answer do.", max_tokens=60)
            elif provider == "groq":
                reply = await self._call_groq(test_key, test_model, "Batao kya aap active ho? Ek line me answer do.", max_tokens=60)
            elif provider == "openai":
                reply = await self._call_openai(test_key, test_model, "Batao kya aap active ho? Ek line me answer do.", max_tokens=60)
            elif provider == "anthropic":
                reply = await self._call_anthropic(test_key, test_model, "Batao kya aap active ho? Ek line me answer do.", max_tokens=60)
            elif provider == "openrouter":
                reply = await self._call_openrouter(test_key, test_model, "Batao kya aap active ho? Ek line me answer do.", max_tokens=60)
            elif provider == "ollama":
                url = p_info.get("url", "http://localhost:11434")
                reply = await self._call_ollama(url, test_model, "Hello", max_tokens=30)
            elif provider == "local":
                return {"success": True, "message": "Local Offline Brain active hai (Rule & Knowledge based).", "latency_ms": 1}
            else:
                return {"success": False, "error": f"Unsupported provider: {provider}"}

            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "success": True,
                "message": f"Connection verified successfully! ({latency_ms}ms)",
                "sample_response": reply.strip(),
                "latency_ms": latency_ms
            }
        except Exception as e:
            return {"success": False, "error": f"API Error: {str(e)}"}

    async def generate_response(self, user_msg: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Generate response using the active provider. Returns None if provider is local or fails."""
        active = self.config.get("active_provider", "local")
        if active == "local":
            return None

        p_info = self.config.get("providers", {}).get(active, {})
        api_key = self.get_effective_key(active)
        model = p_info.get("model", "")

        if not api_key and active not in ["local", "ollama"]:
            return None

        system_prompt = self.config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

        try:
            if active == "gemini":
                return await self._call_gemini(api_key, model, user_msg, system_prompt=system_prompt)
            elif active == "groq":
                return await self._call_groq(api_key, model, user_msg, system_prompt=system_prompt, history=conversation_history)
            elif active == "openai":
                return await self._call_openai(api_key, model, user_msg, system_prompt=system_prompt, history=conversation_history)
            elif active == "anthropic":
                return await self._call_anthropic(api_key, model, user_msg, system_prompt=system_prompt)
            elif active == "openrouter":
                return await self._call_openrouter(api_key, model, user_msg, system_prompt=system_prompt, history=conversation_history)
            elif active == "ollama":
                url = p_info.get("url", "http://localhost:11434")
                return await self._call_ollama(url, model, user_msg, system_prompt=system_prompt)
        except Exception as e:
            print(f"[LLMEngine] Error calling {active}: {e}")
            return None

        return None

    # ------------------ PROVIDER IMPLEMENTATIONS ------------------

    async def _call_gemini(self, api_key: str, model: str, prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise Exception(f"Gemini API status {resp.status_code}: {resp.text}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise Exception("Empty response from Gemini")
            return candidates[0]["content"]["parts"][0]["text"]

    async def _call_groq(self, api_key: str, model: str, prompt: str, system_prompt: str = "", history: Optional[List[Dict[str, str]]] = None, max_tokens: int = 1024) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            for h in history[-4:]:
                messages.append(h)
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise Exception(f"Groq API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_openai(self, api_key: str, model: str, prompt: str, system_prompt: str = "", history: Optional[List[Dict[str, str]]] = None, max_tokens: int = 1024) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            for h in history[-4:]:
                messages.append(h)
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise Exception(f"OpenAI API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, api_key: str, model: str, prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise Exception(f"Anthropic API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["content"][0]["text"]

    async def _call_openrouter(self, api_key: str, model: str, prompt: str, system_prompt: str = "", history: Optional[List[Dict[str, str]]] = None, max_tokens: int = 1024) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            for h in history[-4:]:
                messages.append(h)
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Digi Mitra"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise Exception(f"OpenRouter API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_ollama(self, url: str, model: str, prompt: str, system_prompt: str = "", max_tokens: int = 512) -> str:
        endpoint = f"{url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7
            }
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(endpoint, json=payload)
            if resp.status_code != 200:
                raise Exception(f"Ollama server returned {resp.status_code}: {resp.text}")
            return resp.json().get("response", "")
