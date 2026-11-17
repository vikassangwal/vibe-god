"""
Local LLM Interface for Wife God Agent
Communicates with Ollama API running on localhost:11434
"""

import asyncio
import aiohttp
import json
import logging
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("WifeGod.LLM")


@dataclass
class LLMResponse:
    content: str
    model: str
    done: bool
    tokens_used: int = 0


class LocalLLM:
    """
    Interface to local Ollama LLM
    Supports: Llama-3, Qwen, Mistral, etc.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:8b"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_url = f"{self.base_url}/api"
        self.session: Optional[aiohttp.ClientSession] = None
        self._system_prompts = self._load_system_prompts()

    async def initialize(self):
        """Initialize HTTP session"""
        timeout = aiohttp.ClientTimeout(total=120)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info(f"LocalLLM initialized with model: {self.model}")

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m['name'] for m in data.get('models', [])]
                    return self.model in models
                return False
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def _load_system_prompts(self) -> Dict[str, str]:
        """Load system prompts for different tasks"""
        return {
            "document_extraction": """You are an expert document processor for Indian government documents (eMitra/Rajasthan SSO).
Extract structured data from raw OCR text of Indian documents (Aadhaar, Marksheets, Certificates, etc.).
Return ONLY valid JSON with these fields:
{
  "document_type": "aadhaar|marksheet|income_certificate|caste_certificate|domicile|birth_certificate|death_certificate|marriage_certificate|pension|ration_card|land_record|other",
  "name": "Full name as written",
  "father_name": "Father's/Husband's name",
  "mother_name": "Mother's name",
  "dob": "DD/MM/YYYY",
  "gender": "Male|Female|Other",
  "address": "Full address",
  "pincode": "6-digit pincode",
  "phone": "10-digit mobile",
  "email": "email if present",
  "aadhaar_number": "12-digit Aadhaar (masked: XXXX XXXX 1234)",
  "document_number": "Certificate/Registration number",
  "issuing_authority": "Who issued it",
  "issue_date": "DD/MM/YYYY",
  "additional_fields": {}
}
If a field is not found, use null. Be precise with Indian document formats.""",

            "tweet_generation": """You are a Twitter (X) content creator for an Indian user.
Generate engaging tweets in Hindi/Hinglish/English based on the topic.
Rules:
- Max 280 characters
- Use relevant hashtags (max 3)
- Tone: Professional yet relatable
- Include emojis where appropriate
- If media is mentioned, reference it naturally
Return ONLY the tweet text.""",

            "form_mapping": """You are an expert at mapping extracted document data to eMitra form fields.
Given extracted document data and a list of form field labels, map the data to the correct fields.
Return JSON mapping: {"field_label": "value"}
Handle variations in field labels (Hindi/English).
If data not available, use null.""",

            "captcha_solver": """You are a CAPTCHA solver for Indian government portals.
Analyze the CAPTCHA image description and provide the solution.
Common types: Simple math (2+3), text recognition (distorted letters), slider puzzles.
Return ONLY the answer (number or text).""",

            "tweet_reply": """You are managing a Twitter account for an Indian user.
Generate appropriate replies to tweets/DMs.
Tone: Helpful, polite, professional.
Language: Match the incoming message (Hindi/Hinglish/English).
Keep responses concise (under 280 chars).""",

            "voice_command": """You are Wife God, a voice-controlled AI assistant for eMitra and Twitter automation.
Parse voice commands and return structured intent.
Return JSON: {"intent": "emitra_service|twitter_post|twitter_scrape|doc_process|status", "params": {...}, "confidence": 0.9}"""
        }

    async def generate(self, prompt: str, system_prompt: str = None,
                       temperature: float = 0.1, max_tokens: int = 4096,
                       stream: bool = False) -> LLMResponse:
        """Generate response from LLM"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        try:
            async with self.session.post(
                f"{self.api_url}/chat",
                json=payload
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.error(f"Ollama error: {error}")
                    return LLMResponse(content="", model=self.model, done=False)

                if stream:
                    # Handle streaming
                    content = ""
                    async for line in resp.content:
                        if line:
                            data = json.loads(line)
                            if 'message' in data:
                                content += data['message'].get('content', '')
                            if data.get('done', False):
                                break
                        return LLMResponse(content=content, model=self.model, done=True)
                else:
                    data = await resp.json()
                    content = data.get('message', {}).get('content', '')
                    return LLMResponse(
                        content=content,
                        model=data.get('model', self.model),
                        done=data.get('done', True),
                        tokens_used=data.get('eval_count', 0)
                    )
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return LLMResponse(content="", model=self.model, done=False)

    # High-level methods for specific tasks

    async def extract_document_data(self, ocr_text: str, document_hint: str = "") -> Dict[str, Any]:
        """Extract structured data from OCR text"""
        prompt = f"""Extract structured data from this Indian document OCR text.

Document hint: {document_hint}

OCR Text:
{ocr_text}

Return ONLY valid JSON as specified in system prompt."""

        response = await self.generate(
            prompt=prompt,
            system_prompt=self._system_prompts["document_extraction"],
            temperature=0.05,
            max_tokens=2048
        )

        return self._parse_json_response(response.content)

    async def generate_tweet(self, topic: str, media_description: str = "",
                             language: str = "hinglish", tone: str = "professional") -> str:
        """Generate tweet content"""
        prompt = f"""Generate a tweet about: {topic}

Media: {media_description if media_description else "None"}
Language: {topic}
Tone: {tone}

Return ONLY the tweet text (max 280 chars)."""

        response = await self.generate(
            prompt=prompt,
            system_prompt=self._system_prompts["tweet_generation"],
            temperature=0.7,
            max_tokens=256
        )

        # Clean and validate tweet
        tweet = response.content.strip()
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        return tweet

    async def map_to_form_fields(self, extracted_data: Dict, form_fields: List[str]) -> Dict[str, str]:
        """Map extracted data to form fields"""
        prompt = f"""Map the extracted document data to these form fields:

Extracted Data:
{json.dumps(extracted_data, ensure_ascii=False, indent=2)}

Form Fields:
{json.dumps(form_fields, ensure_ascii=False)}

Return JSON mapping: {{"field_label": "value"}}"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=self._system_prompts["form_mapping"],
            temperature=0.05,
            max_tokens=2048
        )

        return self._parse_json_response(response.content) or {}

    async def solve_captcha(self, captcha_description: str) -> str:
        """Solve CAPTCHA from description"""
        prompt = f"""Solve this CAPTCHA:
{captcha_description}

Return ONLY the answer (number or text)."""

        response = await self.generate(
            prompt=prompt,
            system_prompt=self._system_prompts["captcha_solver"],
            temperature=0.0,
            max_tokens=64
        )

        return response.content.strip()

    async def generate_tweet_reply(self, incoming_text: str, context: str = "") -> str:
        """Generate reply to tweet/DM"""
        prompt = f"""Generate a reply to this tweet/DM:

Incoming: {incoming_text}
Context: {context}

Generate appropriate reply in matching language."""

        response = await self.generate(
            prompt=prompt,
            system_prompt=self._system_prompts["tweet_reply"],
            temperature=0.5,
            max_tokens=256
        )

        return response.content.strip()

    async def parse_voice_command(self, voice_text: str) -> Dict[str, Any]:
        """Parse voice command into structured intent"""
        prompt = f"""Parse this voice command into structured intent:

Voice: "{voice_text}"

Return JSON: {{"intent": "emitra_service|twitter_post|twitter_scrape|doc_process|status", "params": {{...}}, "confidence": 0.9}}"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=self._system_prompts["voice_command"],
            temperature=0.1,
            max_tokens=512
        )

        return self._parse_json_response(response.content) or {
            "intent": "unknown",
            "params": {},
            "confidence": 0.0
        }

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """Parse JSON from LLM response"""
        try:
            # Try direct parse
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown/code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass

            # Try to find JSON-like structure
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass

            logger.warning(f"Failed to parse JSON from: {content[:200]}")
            return None