# Wife God eMitra + Twitter Automation Agent - Project Summary

## Overview
**Wife God** is a 100% locally-hosted, fully autonomous AI agent for eMitra (Rajasthan SSO) services and Twitter (X) operations. Built entirely with local components - no external cloud APIs required.

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

## 📦 Core Modules

| Module | File | Description |
|--------|------|-------------|
| **Config** | `core/config.py` | Configuration management with YAML/JSON support |
| **Database** | `core/database.py` | SQLite operations with async support |
| **Local LLM** | `core/local_llm.py` | Ollama interface (Llama-3, Qwen, Mistral) |
| **Voice** | `core/voice.py` | pyttsx3 TTS + faster-whisper STT |
| **Doc Processor** | `modules/doc_processor.py` | OCR (EasyOCR/Tesseract), compression, PDF |
| **Captcha Solver** | `modules/captcha_solver.py` | OpenCV + human fallback |
| **PyAutoGUI Fallback** | `modules/pyautogui_fallback.py` | System-level automation |
| **eMitra Bot** | `bots/emitra_bot.py` | SSO login, form filling, docs, payments |
| **Twitter Bot** | `bots/twitter_bot.py` | Post, reply, DM, scrape, rate limits |

## 🚜 Farm & Agriculture Modules

| Module | File | Description |
|--------|------|-------------|
| **Farm Manager** | `modules/farm_manager.py` | GPS boundaries, crop rotation, labor, harvest, P&L |
| **Satellite Monitor** | `modules/satellite_monitor.py` | Sentinel-2/Landsat NDVI, DJI drone, crop health |
| **Predictive Maintenance** | `modules/predictive_maintenance.py` | Vibration/Current analysis, failure prediction |

## 🏠 Smart Home & IoT

| Module | File | Description |
|--------|------|-------------|
| **Smart Home** | `modules/smart_home.py` | MQTT/HTTP devices, schedules, automation rules |
| **Passive Income** | `modules/passive_income.py` | Golem, Akash, Honeygain, bandwidth sharing |

## 📱 Media & Content

| Module | File | Description |
|--------|------|-------------|
| **Video Editor** | `modules/video_editor.py` | Auto-edit, Whisper captions, thumbnails, upload |
| **Data Products** | `modules/data_products.py` | Mandi reports, crop calendars, rate reports |
| **Market Intelligence** | `modules/market_intelligence.py` | NCDEX/MCX futures, price prediction, hedging |

## 🏥 Health & Finance

| Module | File | Description |
|--------|------|-------------|
| **Health Coordinator** | `modules/health_coordinator.py` | Appointments, medicines, vaccinations, insurance |
| **Document Intelligence** | `legal/document_intelligence.py` | Jamabandi, loans, govt PDFs OCR+LLM |
| **Google Sheets Sync** | `finance/sheets_sync.py` | CA-ready GST reports, real-time sync |
| **eNAM Integration** | `modules/enam_integration.py` | eNAM, IndiaMART, TradeIndia price aggregation |

## 🛠️ Utilities

| Module | File | Description |
|--------|------|-------------|
| **Captcha Solver** | `modules/captcha_solver.py` | OpenCV + human fallback |
| **PyAutoGUI Fallback** | `modules/pyautogui_fallback.py` | Template matching, screen automation |
| **Video Editor** | `modules/video_editor.py` | Whisper captions, thumbnails, upload |
| **Captcha Solver** | `modules/captcha_solver.py` | Math/text/image CAPTCHA |

## 🔧 Configuration

### Key Configuration Files
- `config.json` - Main configuration
- `config.json.example` - Template
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Package metadata

### Key Settings
```json
{
  "ollama": { "url": "http://localhost:11434", "model": "llama3:8b" },
  "emitra": { "username": "", "password": "" },
  "twitter": { "username": "", "password": "" },
  "voice": { "tts_engine": "pyttsx3", "whisper_model": "base" },
  "doc": { "ocr_engine": "easyocr", "size_limits": {...} }
}
```

## 🚀 Quick Start

```bash
# 1. Install system deps (Linux)
sudo apt-get install tesseract-ocr tesseract-ocr-hin libgl1-mesa-glx portaudio19-dev chromium-browser

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3:8b

# 3. Install Python deps
pip install -r requirements.txt
playwright install chromium

# 4. Configure
cp config.json.example config.json
# Edit config.json with your credentials

# 5. Run
python -m main
```

## 🎯 Voice Commands Examples

| Command | Action |
|---------|--------|
| "Aadhaar form bhar do" | Start Aadhaar enrollment |
| "Caste certificate chahiye" | Caste certificate service |
| "Twitter pe tweet karo" | Post tweet |
| "Hashtag Rajasthan search karo" | Scrape #Rajasthan |
| "Mera status batao" | System status |
| "Moongphali ka bhav batao" | Get mandi price |
| "Tubewell chalu karo 2 ghante" | Start tubewell |

## 📁 Project Structure

```
wife_god_emitter/
├── main.py                    # Entry point
├── config.json                # Configuration
├── config.json.example        # Template
├── pyproject.toml             # Package config
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
├── README.md                  # Documentation
├── PROJECT_SUMMARY.md         # This file
│
├── core/
│   ├── config.py              # Config management
│   ├── database.py            # SQLite ops
│   ├── local_llm.py           # Ollama interface
│   └── voice.py               # TTS/STT
│
├── modules/
│   ├── doc_processor.py       # OCR, compress, PDF
│   ├── captcha_solver.py      # CAPTCHA handling
│   ├── pyautogui_fallback.py  # System automation
│   ├── farm_manager.py        # GPS, crops, labor
│   ├── satellite_monitor.py   # NDVI, drones
│   ├── predictive_maintenance.py # Vibration, current
│   ├── smart_home.py          # MQTT, schedules, rules
│   ├── health_coordinator.py  # Appointments, meds
│   ├── passive_income.py      # Golem, Honeygain
│   ├── video_editor.py        # Auto-edit, captions
│   ├── market_intelligence.py # NCDEX, predictions
│   ├── data_products.py       # Reports, calendars
│   └── enam_integration.py    # eNAM, IndiaMART
│
├── bots/
│   ├── emitra_bot.py          # eMitra automation
│   └── twitter_bot.py         # Twitter/X automation
│
├── legal/
│   └── document_intelligence.py # Legal docs OCR
│
├── finance/
│   └── sheets_sync.py         # Google Sheets sync
│
├── scripts/
│   └── setup.py               # Auto-installer
│
├── data/                      # SQLite DB, sessions
├── input_documents/           # Drop files for auto-processing
├── output/                    # Receipts, processed docs
├── temp/                      # Temporary files
├── models/                    # Captcha model (optional)
└── logs/                      # Log files
```

## ⚡ Key Features

### 100% Local Execution
- No cloud APIs (except OAuth portals)
- Ollama for LLM inference
- EasyOCR/Tesseract for OCR
- Whisper for STT
- PyAutoGUI for system automation

### Anti-Fragile Design
- Playwright primary, PyAutoGUI fallback
- Human-in-the-loop for CAPTCHA/OTP
- Automatic retry with exponential backoff
- Comprehensive error handling

### Multilingual Support
- Hindi, Hinglish, English, Marwari
- Voice in Hindi/English
- Documents in Hindi/English

### Security & Privacy
- Local SQLite with encryption
- No data leaves machine
- Financial firewall (no auto-payments)
- Encrypted session storage

## 📊 Monitoring & Health

- Real-time resource monitoring
- Disk space alerts
- Ollama health checks
- Structured logging (JSON)
- Task queue with priority

## 🔮 Future Extensions

- [ ] Android app (Termux + ADB)
- [ ] LoRa/WiFi mesh for farm sensors
- [ ] Custom ASR for Marwari dialect
- [ ] Blockchain land records
- [ ] Drone swarm coordination
- [ ] Federated learning across farms

## 📜 License

MIT License - Built for Digital India

---

**Wife God** - Your Sovereign Local AI Assistant 🤖🇮🇳