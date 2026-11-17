# Wife God eMitra + Twitter Automation Agent

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Beta-yellow.svg)
![Local](https://img.shields.io/badge/100%25-Local-brightgreen.svg)

> **Wife God** - A fully autonomous, 100% locally-hosted AI agent for eMitra (Rajasthan SSO) services and Twitter (X) operations. Zero cloud dependencies, complete privacy.

## 🎯 Overview

Wife God is a sovereign AI agent that runs entirely on your local machine. It automates:
- **eMitra (Rajasthan SSO) Services**: Aadhaar enrollment, certificates, pension schemes, land records, etc.
- **Twitter (X) Operations**: Posting, replying, DMs, scraping, analytics
- **Document Processing**: OCR, compression, PDF generation for government portals
- **Voice Interface**: Hindi/English TTS + STT for hands-free operation

**Key Philosophy**: *Your data never leaves your machine. No cloud APIs. Complete autonomy.*

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      WIFE GOD AGENT                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Voice     │  │   Local     │  │  Document   │             │
│  │   Comm      │  │   LLM       │  │  Processor  │             │
│  │  (TTS/STT)  │  │  (Ollama)   │  │  (OCR/PDF)  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                    │
│         └────────────────┼────────────────┘                    │
│                          ▼                                     │
│              ┌───────────────────────┐                         │
│              │   Central Controller  │                         │
│              │    (main.py)          │                         │
│              └───────────┬───────────┘                         │
│                           │                                     │
│          ┌────────────────┼────────────────┐                   │
│          ▼                ▼                ▼                   │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│  │  eMitra Bot   │ │ Twitter Bot   │ │  SQLite DB    │       │
│  │ (Playwright)  │ │ (Playwright)  │ │  (Local)      │       │
│  └───────┬───────┘ └───────┬───────┘ └───────────────┘       │
│           │                 │                                 │
│           ▼                 ▼                                 │
│  ┌───────────────────────────────────────┐                   │
│  │      PyAutoGUI Fallback + OpenCV      │                   │
│  │    (System-level automation backup)   │                   │
│  └───────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🏛️ eMitra (Rajasthan SSO) Automation
- **SSO Login**: Automated login with CAPTCHA handling
- **Service Navigation**: Auto-discovery and navigation to services
- **Form Filling**: Intelligent field mapping via local LLM
- **Document Upload**: Auto-compression to portal size limits
- **Payment Handling**: Gateway integration with manual approval
- **Receipt Download**: Auto-save receipts locally

**Supported Services**:
- Aadhaar Enrollment/Update
- Caste/Income/Domicile Certificates
- Birth/Death/Marriage Certificates
- Pension Schemes
- Ration Card Services
- Land Records (Khatauni/Khasra)

### 🐦 Twitter (X) Automation
- **Tweet Posting**: Text + media with LLM-generated content
- **Replies/Retweets/Likes**: Full engagement automation
- **DM Management**: Send, read, auto-reply with keywords
- **Scraping**: Hashtag, user, and search-based tweet collection
- **Rate Limiting**: Built-in hourly limits compliance
- **Session Persistence**: Encrypted cookie storage

### 📄 Document Processing
- **Offline OCR**: EasyOCR + Tesseract (Hindi + English)
- **Smart Compression**: Binary search to exact byte limits
- **PDF Generation**: Auto-convert for portal requirements
- **Validation**: Pre-upload checks for size/readability

### 🎙️ Voice Interface
- **TTS**: pyttsx3 (offline Hindi/English)
- **STT**: faster-whisper (local, no cloud)
- **VAD**: Voice activity detection for natural conversation
- **Human-in-the-Loop**: OTP/document requests via voice

### 🛡️ Security & Privacy
- **100% Local**: No external API calls (except OAuth portals)
- **Encrypted Sessions**: SQLite + Fernet encryption
- **Financial Firewall**: No automated payment execution
- **Audit Logs**: Complete action trail in SQLite

---

## 🚀 Quick Start

### Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Core runtime |
| Ollama | Latest | Local LLM (Llama-3/Qwen) |
| Tesseract | 5.x | OCR engine |
| Chrome/Chromium | Latest | Playwright browser |

### Installation

```bash
# 1. Clone/navigate to project
cd wife_god_emitter

# 2. Install system dependencies (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install -y \
    tesseract-ocr tesseract-ocr-hin \
    libgl1-mesa-glx \
    portaudio19-dev \
    chromium-browser

# 3. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3:8b  # or qwen:7b, mistral:7b

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Install Playwright browsers
playwright install chromium

# 6. Configure
cp config.json.example config.json
# Edit config.json with your credentials

# 6. Run
python -m main
```

### Configuration

Edit `config.json`:

```json
{
  "ollama": {
    "url": "http://localhost:11434",
    "model": "llama3:8b"
  },
  "emitra": {
    "username": "your_sso_username",
    "password": "your_sso_password"
  },
  "twitter": {
    "username": "your_twitter_handle",
    "password": "your_twitter_password"
  },
  "voice": {
    "tts_engine": "pyttsx3",
    "stt_engine": "whisper",
    "whisper_model": "base"
  }
}
```

---

## 💻 Usage

### Interactive Mode (Voice + CLI)
```bash
python -m main
# Speak commands like:
# "Aadhaar card ka form bhar do"
# "Twitter pe tweet karo: Hello world"
# "Mera status batao"
```

### API Mode (Programmatic)
```python
from main import WifeGodAgent

async def example():
    agent = WifeGodAgent("config.json")
    await agent.initialize()

    # eMitra service
    result = await agent.request_emitra_service(
        service_name="caste_certificate",
        documents=["aadhaar.jpg", "photo.jpg"],
        user_data={"name": "Vikas", "father_name": "Ram"}
    )

    # Twitter post
    result = await agent.post_tweet(
        text="Hello from Wife God! 🤖",
        media_paths=["photo.jpg"]
    )

    # Scrape hashtag
    tweets = await agent.scrape_hashtag("Rajasthan", limit=20)

    await agent.shutdown()
```

### Voice Commands
| Command | Action |
|---------|--------|
| "Aadhaar form bhar do" | Start Aadhaar service |
| "Caste certificate chahiye" | Caste certificate service |
| "Twitter pe tweet karo" | Post tweet |
| "Hashtag Rajasthan search karo" | Scrape #Rajasthan |
| "Mera status batao" | System status |
| "Ruko" / "Stop" | Emergency stop |

---

## 📁 Project Structure

```
wife_god_emitter/
├── main.py                    # Entry point
├── config.json                # Configuration
├── pyproject.toml             # Package config
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
├── README.md                  # This file
│
├── core/
│   ├── config.py              # Configuration management
│   ├── database.py            # SQLite operations
│   ├── local_llm.py           # Ollama interface
│   └── voice.py               # TTS/STT
│
├── modules/
│   ├── doc_processor.py       # OCR, compression, PDF
│   ├── captcha_solver.py      # OpenCV + human fallback
│   └── pyautogui_fallback.py  # System-level automation
│
├── bots/
│   ├── emitra_bot.py          # eMitra automation
│   └── twitter_bot.py         # Twitter/X automation
│
├── scripts/
│   └── setup.py               # Auto-installer
│
├── data/                      # SQLite DB, sessions
├── input_documents/           # Drop files here for auto-processing
├── output/                    # Receipts, processed docs
├── temp/                      # Temporary files
└── models/                    # Captcha model (optional)
```

---

## 🔧 Advanced Configuration

### Document Size Limits (eMitra Portal)
| Document Type | Max Size | Format |
|---------------|----------|--------|
| Signature     | 50 KB    | JPG/PNG |
| Photo         | 100 KB   | JPG/PNG |
| Aadhaar       | 200 KB   | JPG/PDF |
| Documents     | 500 KB   | JPG/PDF |

### Rate Limits (Twitter)
| Action | Hourly Limit |
|--------|--------------|
| Tweets | 50 |
| DMs    | 100 |
| Follows | 50 |

### Voice Settings
```json
{
  "voice": {
    "tts_rate": 150,
    "tts_volume": 0.9,
    "whisper_model": "base",  // tiny, base, small, medium, large
    "language": "hi",
    "vad_threshold": 0.5
  }
}
```

---

## 🛠️ Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Format
black .

# Lint
ruff check .

# Type check
mypy .
```

### Adding New eMitra Services
1. Add service config in `config.json` under `emitra.services`
2. Define required documents
3. Add form field mappings if needed
4. Test with `python -m main --service <name>`

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Ollama not found | `ollama serve` in separate terminal |
| Playwright browser missing | `playwright install chromium` |
| Tesseract not found | Install tesseract-ocr + hindi language pack |
| Audio not working | Check portaudio: `sudo apt install portaudio19-dev` |
| GPU OOM | Use smaller model: `ollama pull llama3:8b-q4` |

### Logs
```bash
tail -f wife_god.log
```

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## ⚠️ Disclaimer

This software is for educational and personal automation purposes. Users are responsible for:
- Complying with portal Terms of Service
- Data privacy compliance (DPDP Act, IT Act)
- Rate limit adherence
- Ethical use of automation

**Use responsibly. Automate ethically.**

---

## 🙏 Acknowledgments

- **Ollama** for local LLM serving
- **Playwright** for reliable web automation
- **EasyOCR/Tesseract** for offline OCR
- **faster-whisper** for local STT
- **PyAutoGUI** for system-level fallback

---

**Built with ❤️ for Digital India**

*Wife God - Your Sovereign Local AI Assistant*