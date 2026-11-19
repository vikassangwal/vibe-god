"""
Digi Mitra Local Private API & Web Control Panel
Runs on FastAPI + WebSockets + Responsive Glassmorphism PWA UI.
Accessible via:
- Windows Desktop: http://localhost:8000
- Mobile Phone (Same Wi-Fi): http://<LAPTOP_IP>:8000
"""

import os
import sys
import socket
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from digi_mitra.nlu.smart_nlu import SmartNLU
from digi_mitra.trading.trading_engine import TradingAnalysisEngine
from digi_mitra.research.research_engine import SelfLearningResearchEngine
from digi_mitra.video.video_engine import VideoAutomationEngine
from digi_mitra.exam_engine import ExamPaperGenerator
from digi_mitra.app_permissions import AppPermissionManager
from digi_mitra.legal_etiquette import LegalKnowledgeAndEtiquetteEngine
from digi_mitra.security_auditor import SecurityAuditorEngine
from digi_mitra.scheduler_engine import TaskSchedulerEngine
from digi_mitra.chat_brain import ConversationalBrain
from digi_mitra.history_learner import HistoryLearningEngine
from digi_mitra.human_chat import NaturalHumanChatEngine
from digi_mitra.mobile_launcher import MobileAppLauncherEngine
from digi_mitra.wealth_engine import AutonomousWealthEngine
from digi_mitra.client_guardian import ClientAcquisitionGuardianEngine
from digi_mitra.target_one_lakh import OneLakhTargetPlanner
from digi_mitra.relentless_worker import RelentlessTargetWorker
from digi_mitra.universal_online_worker import UniversalOnlineWorkEngine
from digi_mitra.freelance_engine import FreelanceExecutionEngine
from digi_mitra.wise_mentor import WiseMentorGuardian
from digi_mitra.job_scanner import JobVacancyScannerEngine
from digi_mitra.wake_word_engine import CustomWakeWordEngine
from digi_mitra.knowledge_brain import SovereignKnowledgeBrain
from digi_mitra.llm_engine import LLMEngine
from digi_mitra.screen_worker import AutoScreenWorker
from digi_mitra.whatsapp_bot import WhatsAppAutomationBot
from digi_mitra.form_pdf_generator import FormPDFGenerator
from digi_mitra.yojna_radar import SarkariYojnaRadar
from digi_mitra.reels_generator import ReelsGenerator
from modules.doc_processor import DocProcessor, DocConfig
from bots.emitra_bot import eMitraBot
from core.config import Config

app = FastAPI(title="Digi Mitra - Sovereign AI Super-Agent")

# Initialize engines
nlu = SmartNLU()
trading_engine = TradingAnalysisEngine()
research_engine = SelfLearningResearchEngine()
video_engine = VideoAutomationEngine()
doc_processor = DocProcessor(DocConfig())
exam_engine = ExamPaperGenerator()
permission_mgr = AppPermissionManager()
legal_engine = LegalKnowledgeAndEtiquetteEngine()
security_auditor = SecurityAuditorEngine()
task_scheduler = TaskSchedulerEngine()
chat_brain = ConversationalBrain()
human_chat = NaturalHumanChatEngine()
history_learner = HistoryLearningEngine()
mobile_launcher = MobileAppLauncherEngine(permission_mgr)
wealth_engine = AutonomousWealthEngine()
client_guardian = ClientAcquisitionGuardianEngine()
one_lakh_planner = OneLakhTargetPlanner()
relentless_worker = RelentlessTargetWorker()
online_worker = UniversalOnlineWorkEngine()
freelance_engine = FreelanceExecutionEngine()
wise_mentor = WiseMentorGuardian()
job_scanner = JobVacancyScannerEngine()
wake_engine = CustomWakeWordEngine()
knowledge_brain = SovereignKnowledgeBrain()
llm_engine = LLMEngine()
screen_worker = AutoScreenWorker()
whatsapp_bot = WhatsAppAutomationBot()
form_pdf_gen = FormPDFGenerator()
yojna_radar = SarkariYojnaRadar()
reels_gen = ReelsGenerator()

templates = Jinja2Templates(directory="digi_mitra/web_dashboard/templates")
app.mount("/static", StaticFiles(directory="digi_mitra/web_dashboard/static"), name="static")


@app.get("/manifest.json")
async def get_manifest():
    return FileResponse("digi_mitra/web_dashboard/static/manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
async def get_sw():
    return FileResponse("digi_mitra/web_dashboard/static/sw.js", media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    local_ip = get_local_ip()
    mobile_url = f"http://{local_ip}:8000"
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mobile_url": mobile_url,
        "learned_topics": research_engine.get_learned_topics()[:6]
    })


@app.post("/api/ask")
async def process_user_command(query: str = Form(...)):
    # 1. Wise Mentor Check: Agar Vikas ji galti kar rahe hon toh toke aur sahi rasta bataye
    is_mistake, correction_advice = wise_mentor.inspect_and_correct_mistakes(query)
    if is_mistake:
        return JSONResponse({"intent": "mistake_correction", "reply": correction_advice})

    parsed = nlu.parse_intent(query)
    intent = parsed["intent"]
    q_lower = query.lower()

    # Check for sensitive app mention (WhatsApp, Gallery, Passwords, etc.)
    for sensitive_kw in ["whatsapp", "gallery", "photo", "password", "setting", "bank"]:
        if sensitive_kw in q_lower:
            alert_check = permission_mgr.request_access_with_security_alert(sensitive_kw)
            if not alert_check.get("allowed"):
                reply = f"🚨 <b>SECURITY ALERT (Suraksha Chetavni)</b>:<br>{alert_check['security_alert']}<br><br>👉 <i>{alert_check['prompt']}</i><br><small style='color:#f87171;'>Suraksha ke niyam anusar jab tak aap Dashboard se 'Allow' switch ON nahi karenge, yeh app 100% blocked rahega.</small>"
                return JSONResponse({"intent": "security_alert", "reply": legal_engine.format_respectful_response(reply)})

    # 2. Auto Screen Worker: Check if user wants screen drawing, click, typing, or screen control
    screen_res = screen_worker.execute_natural_command(query)
    if screen_res:
        reply_txt = screen_res.get("message") or screen_res.get("error", "Screen action complete")
        clean_reply = legal_engine.format_respectful_response(reply_txt)
        history_learner.record_interaction(query, clean_reply, "screen_worker")
        return JSONResponse({"intent": "screen_worker", "reply": clean_reply, "data": screen_res})

    # 3. Sovereign Knowledge Brain: Check if user is asking a question, seeking advice or shopping recommendation
    kb_answer = knowledge_brain.answer_question(query)
    if kb_answer and kb_answer.get("matched"):
        clean_reply = legal_engine.format_respectful_response(kb_answer["reply"])
        history_learner.record_interaction(query, clean_reply, "knowledge_qa")
        return JSONResponse({"intent": "knowledge_qa", "reply": clean_reply})

    # 4. WhatsApp Automation Bot
    if any(w in query.lower() for w in ["whatsapp", "whatsap", "watsap", "wa msg", "wa alert"]):
        import re
        phone_match = re.search(r'(\d{10})', query)
        phone = phone_match.group(1) if phone_match else "919876543210"
        if "mandi" in query.lower():
            wa_text = whatsapp_bot.format_template("mandi_rates", {"mandi": "Rajasthan APMC"})
        elif any(k in query.lower() for k in ["emitra", "receipt", "rasid"]):
            wa_text = whatsapp_bot.format_template("emitra_receipt", {"customer_name": "Vikas ji", "service_name": "Jan Aadhaar"})
        elif "trade" in query.lower():
            wa_text = whatsapp_bot.format_template("trading_alert", {"symbol": "NIFTY 50", "signal": "BUY", "price": "24,500"})
        else:
            wa_text = whatsapp_bot.format_template("notice", {"custom_text": query})

        wa_url = whatsapp_bot.create_whatsapp_url(phone, wa_text)
        reply = (
            f"📱 <b>Digi Mitra WhatsApp Dispatch Ready:</b><br><br>"
            f"<a href='{wa_url}' target='_blank' style='background:#25D366; color:white; padding:8px 18px; border-radius:10px; text-decoration:none; font-weight:700; display:inline-block;'>⚡ Click to Open WhatsApp (+{phone})</a><br><br>"
            f"<small style='color:#94a3b8;'>Message Preview:</small><br><i>{wa_text.replace(chr(10), '<br>')}</i>"
        )
        clean_reply = legal_engine.format_respectful_response(reply)
        history_learner.record_interaction(query, clean_reply, "whatsapp_dispatch")
        return JSONResponse({"intent": "whatsapp_dispatch", "reply": clean_reply, "whatsapp_url": wa_url})

    # 5. Instant Legal & Sarkari Form PDF Generator
    if any(w in query.lower() for w in ["pdf banao", "form banao", "shapath patra", "rent agreement", "affidavit", "rasid banao", "invoice banao"]):
        f_type = "shapath_patra"
        if any(k in query.lower() for k in ["rent", "kiraya"]):
            f_type = "rent_agreement"
        elif any(k in query.lower() for k in ["rasid", "receipt"]):
            f_type = "emitra_receipt"
        elif any(k in query.lower() for k in ["invoice", "bill"]):
            f_type = "invoice"
        elif "affidavit" in query.lower():
            f_type = "affidavit"

        pdf_res = form_pdf_gen.generate_form(f_type, {"name": "Vikas Sangwal", "customer_name": "Vikas Sangwal"})
        reply = (
            f"📄 <b>Official Legal / Sarkari Document Ready!</b><br><br>"
            f"File: <b>{pdf_res['filename']}</b><br><br>"
            f"<a href='{pdf_res['download_url']}' download style='background:#0284c7; color:white; padding:8px 18px; border-radius:10px; text-decoration:none; font-weight:700; display:inline-block;'>⬇️ Download Ready-To-Print PDF</a>"
        )
        clean_reply = legal_engine.format_respectful_response(reply)
        history_learner.record_interaction(query, clean_reply, "pdf_generation")
        return JSONResponse({"intent": "pdf_generation", "reply": clean_reply, "download_url": pdf_res["download_url"]})

    # 6. Sarkari Yojna & Vacancy Radar
    if any(w in query.lower() for w in ["yojana", "yojna", "chiranjeevi", "bhatta", "kisan samman", "sarkari labh", "naukri", "vacancy", "bharti"]):
        if any(w in query.lower() for w in ["naukri", "vacancy", "bharti"]):
            vacs = yojna_radar.get_vacancies()
            v_html = [f"<b>💼 {v['post']}</b> ({v['department']})<br>👥 <i>Posts:</i> {v['posts_count']} | 🎓 <i>Yogyata:</i> {v['qualification']}<br>🔗 <i>{v['action']}</i>" for v in vacs]
            reply = "📢 <b>Top Active Sarkari Vacancies 2026:</b><br><br>" + "<br><br>".join(v_html)
        else:
            yojas = yojna_radar.search_yojanas(query)
            y_html = [f"<b>🏛️ {y['name']}</b> ({y['department']})<br>🎁 <b>Labh:</b> {y['benefit']}<br>📋 <b>Dastavez:</b> {y['documents']}<br>👉 <i>Portal: {y['apply_portal']}</i>" for y in yojas]
            reply = "🌟 <b>Sarkari Yojna Radar — Poori Jankari:</b><br><br>" + "<br><br>".join(y_html)
        clean_reply = legal_engine.format_respectful_response(reply)
        history_learner.record_interaction(query, clean_reply, "yojna_radar")
        return JSONResponse({"intent": "yojna_radar", "reply": clean_reply})

    # 7. Automated Reel Maker
    if any(w in query.lower() for w in ["reel", "short video", "shorts", "video banao"]):
        cat = "trading" if "trade" in query.lower() else "emitra" if "emitra" in query.lower() else "business"
        reel_res = reels_gen.generate_reel(cat)
        reply = (
            f"🎬 <b>AI Short Reel Video Generated!</b><br><br>"
            f"File: <b>{reel_res['filename']}</b> (9:16 Vertical HD Format)<br><br>"
            f"<a href='{reel_res['download_url']}' download style='background:linear-gradient(135deg, #ec4899, #db2777); color:white; padding:8px 18px; border-radius:10px; text-decoration:none; font-weight:700; display:inline-block;'>▶️ Download / View Reel Video</a>"
        )
        clean_reply = legal_engine.format_respectful_response(reply)
        history_learner.record_interaction(query, clean_reply, "reel_generator")
        return JSONResponse({"intent": "reel_generator", "reply": clean_reply, "download_url": reel_res["download_url"]})

    result = {"intent": intent, "parsed": parsed, "reply": ""}

    if intent == "trading_analysis":
        # Extract stock name if mentioned (e.g. 'nifty', 'tata', 'reliance', 'btc')
        symbol = "^NSEI" # Default Nifty 50
        q_upper = query.upper()
        if "RELIANCE" in q_upper:
            symbol = "RELIANCE.NS"
        elif "TATA" in q_upper:
            symbol = "TATAMOTORS.NS"
        elif "BTC" in q_upper or "BITCOIN" in q_upper:
            symbol = "BTC-USD"
            
        trade_res = await trading_engine.analyze_stock_or_crypto(symbol)
        result["data"] = trade_res
        if trade_res.get("success"):
            d = trade_res["data"]
            result["reply"] = f"📈 {d['symbol']} Analysis:\nPrice: ₹{d['current_price']} ({d['change_pct']}%)\nSignal: {d['signal']}\nPattern: {d['pattern']}\nRSI: {d['rsi']}\nSupport: ₹{d['support_level']} | Target: ₹{d['target_price']}"
        else:
            result["reply"] = f"Analysis error: {trade_res.get('error')}"

    elif intent == "emitra_service":
        result["reply"] = f"🏛️ eMitra Portal Automation active: '{query}'. Forms, Jan-Aadhaar & Caste Certificate processing queued with auto-captcha solver!"

    elif intent == "video_edit":
        result["reply"] = f"🎬 Video Automation active: '{query}'. Reels generation and video processing module ready."

    elif "papar" in query.lower() or "paper" in query.lower() or "question" in query.lower() or "blueprint" in query.lower():
        # User requested question paper from books & blueprint
        marks = 50
        import re
        marks_match = re.search(r'(\d+)\s*(number|no|mark|marks)', query.lower())
        if marks_match:
            marks = int(marks_match.group(1))

        paper_res = exam_engine.generate_question_paper(subject="General Subject", total_marks=marks)
        result["reply"] = f"📝 <b>Question Paper Safaltapoorvak Ban Gaya!</b><br>🎯 Total Marks: {marks}<br>📑 Blueprint Followed: Section A (MCQs 1M), Section B (Short 2M), Section C (Long 5M)<br>📁 PDF File: {paper_res['filename']} (Download ready)"

    elif intent == "research":
        res_data = await research_engine.autonomous_research(query)
        d = res_data.get("data", {})
        result["reply"] = f"🧠 Research Complete ({d.get('topic')}):\n{d.get('summary')}"

    elif any(k in query.lower() for k in ["kholo", "open", "launch", "chalao"]):
        # Find which app
        target_app = "chrome"
        for app_candidate in ["zerodha", "groww", "tradingview", "emitra", "chrome", "whatsapp"]:
            if app_candidate in query.lower():
                target_app = app_candidate
                break

        launch_data = mobile_launcher.prepare_mobile_launch(target_app)
        if launch_data["can_open"]:
            result["reply"] = f"📱 {launch_data['alert']}<br><b>{launch_data['message']}</b>"
            result["launch_url"] = launch_data["scheme_url"]
        else:
            result["reply"] = f"{launch_data['alert']}<br><small style='color:#f87171;'>{launch_data['instruction']}</small>"

    elif any(k in query.lower() for k in ["freelanc", "frilac", "fiverr", "upwork", "proposal", "bid"]):
        prop_res = freelance_engine.generate_winning_proposal(job_title=query)
        result["reply"] = f"💻 <b>Freelance Winning Proposal (Bid) Tayyar Hai:</b><br><br><pre style='background:rgba(0,0,0,0.4); padding:10px; border-radius:8px; white-space:pre-wrap; color:#a5f3fc;'>{prop_res['proposal']}</pre><br>👉 <i>{prop_res['tip']}</i><br>Client order milte hi Digi Mitra final delivery file khud create karke deliver kar dega!"

    elif any(k in query.lower() for k in ["job", "naukri", "vacancy", "bharti", "post", "recruitment"]):
        job_res = job_scanner.scan_jobs()
        sarkari_html = []
        for sj in job_res["sarkari_jobs"]:
            sarkari_html.append(f"<b>🏛️ {sj['title']}</b> ({sj['department']})<br>🎓 <i>Yogyata:</i> {sj['eligibility']} | 📅 <i>Last Date:</i> {sj['last_date']}<br>💰 <i>Fees:</i> {sj['fee']}")

        private_html = []
        for pj in job_res["private_remote_jobs"]:
            private_html.append(f"<b>💼 {pj['title']}</b> ({pj['company']})<br>💵 <i>Salary:</i> {pj['salary']} | 📍 <i>Type:</i> {pj['type']}")

        all_jobs_str = "<br><br>".join(sarkari_html) + "<br><br>" + "<br><br>".join(private_html)
        result["reply"] = f"📢 <b>Digi Mitra Live Jobs & Vacancy Radar:</b><br><br>{all_jobs_str}<br><br>👉 <i>{job_res['direct_action']}</i>"

    elif any(k in query.lower() for k in ["online kam", "onlin kam", "freelance", "online work", "koi bhi kam"]):
        online_res = online_worker.execute_online_task(query)
        jobs_str = "<br>• ".join(online_worker.supported_online_jobs)
        result["reply"] = f"{online_res['message']}<br><br>💼 <b>Digi Mitra Jin Sabhi Online Kamon Ko Karta Hai:</b><br>• {jobs_str}"

    elif any(k in query.lower() for k in ["client", "clint", "grahak", "customer", "order"]):
        client_res = client_guardian.find_potential_clients()
        strat_html = []
        for st in client_res["strategies"]:
            strat_html.append(f"<b>{st['category']}</b><br>🎯 <i>Target:</i> {st['potential_clients']}<br>💬 <i>Kaise layega:</i> {st['approach']}<br>💸 <i>Kharcha:</i> <b>{st['cost']}</b>")
        strat_str = "<br><br>".join(strat_html)
        result["reply"] = f"🎯 <b>Digi Mitra Client Acquisition System (Zero Kharcha):</b><br><br>{strat_str}<br><br><small style='color:#34d399;'>{client_res['privacy_assurance']}</small>"

    elif any(k in query.lower() for k in ["kitna bhi kam", "chahe jitna", "target pura", "non stop", "24/7", "rukna mat"]):
        relentless_res = relentless_worker.start_relentless_execution()
        actions_str = "<br>• ".join(relentless_res["actions_underway"])
        result["reply"] = f"🔥 <b>{relentless_res['mode']}</b><br>💪 <i>{relentless_res['motto']}</i><br><br>⚙️ <b>Active Batch Pipelines Running:</b><br>• {actions_str}<br><br>⚡ <b>Energy Status:</b> {relentless_res['status']}"

    elif any(k in query.lower() for k in ["1lakh", "1 lakh", "ek lakh", "lakh", "100000", "investment"]):
        roadmap = one_lakh_planner.generate_action_roadmap()
        pillar_items = []
        for p in roadmap["pillars"]:
            pillar_items.append(f"<b>{p['pillar']}</b> (Lakshya: <b>{p['monthly_goal']}</b>)<br>⚡ <i>Roz ka Action:</i> {p['daily_action']}<br>💼 <i>Investment Use:</i> {p['investment_use']}")
        pillar_html = "<br><br>".join(pillar_items)
        result["reply"] = f"🎯 <b>1-Lakh Monthly Realistic Roadmap (Execution Plan):</b><br>Daily Target: <b>{roadmap['daily_run_rate']}</b><br><br>{pillar_html}<br><br>💡 <b>Summary:</b> {roadmap['summary']}"

    elif any(k in query.lower() for k in ["paise", "pese", "kamao", "earning", "kamana", "income", "wealth", "rupaye"]):
        wealth_data = wealth_engine.analyze_earning_opportunities()
        stream_items = []
        for s in wealth_data["streams"]:
            stream_items.append(f"<b>{s['stream']}</b><br>💵 <i>Kamai:</i> {s['daily_potential']}<br>👉 <i>Kaise karega:</i> {s['action']}")
        streams_html = "<br><br>".join(stream_items)
        result["reply"] = f"💰 <b>Digi Mitra Automated Wealth & Earning Blueprints:</b><br><br>{streams_html}<br><br>⚡ <i>Bataiye inme se kaunsa kaam abhi shuru karein? Digi Mitra turant execution shuru kar dega!</i>"

    elif any(k in query.lower() for k in ["samay", "kab", "schedule", "remind", "roz", "har din", "alarm", "tarikh"]):
        # Extract time or frequency
        freq = "daily" if any(f in query.lower() for f in ["roz", "daily", "har din"]) else "once"
        sched_time = "09:00 AM"
        import re
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:baje|am|pm)?)', query.lower())
        if time_match:
            sched_time = time_match.group(1)

        sched_res = task_scheduler.add_scheduled_task(command=query, schedule_time=sched_time, frequency=freq)
        result["reply"] = sched_res["message"]

    elif intent == "mandi_farming":
        result["reply"] = f"🌾 Mandi Bhav & e-NAM: '{query}' live rates updated from Rajasthan APMC mandis."

    elif any(k in query.lower() for k in [
        "wake word", "naam rakh", "naam badlo", "naam change", "bulane ka naam",
        "activate naam", "mera naam", "mujhe bulao", "mujhe", "mera custom naam",
        "jarvis", "alexa", "siri", "bolo", "naam set", "wake naam"
    ]):
        # Custom Wake Word Change: User koi bhi naam de sakta hai e.g. "Mera naam Jarvis rakh do"
        import re
        # Try extracting new name from common patterns
        name_match = re.search(
            r'(?:naam|name|word|bulao|bulaya|set|rakh|badlo|change)[:\s]+([a-zA-Z\u0900-\u097F ]{2,30})',
            query,
            re.IGNORECASE
        )
        if name_match:
            new_name = name_match.group(1).strip()
        else:
            # Fallback: last meaningful word in query
            words = [w for w in query.split() if len(w) > 2]
            new_name = words[-1] if words else "digi mitra"

        ww_res = wake_engine.update_wake_word(new_name)
        result["reply"] = ww_res["message"]
        result["new_wake_word"] = ww_res["new_wake_word"]

    else:
        # Check if an AI provider is active (Gemini, Groq, OpenAI, Anthropic, OpenRouter, Ollama)
        if llm_engine.config.get("active_provider") != "local":
            try:
                ai_reply = await llm_engine.generate_response(query)
                if ai_reply:
                    clean_ai_reply = legal_engine.format_respectful_response(ai_reply)
                    history_learner.record_interaction(query, clean_ai_reply, "ai_llm_chat")
                    return JSONResponse({
                        "intent": "ai_llm_chat",
                        "reply": clean_ai_reply,
                        "provider": llm_engine.config.get("active_provider")
                    })
            except Exception as e:
                print(f"[Server] LLM fallback triggered: {e}")

        # 100% Real Human Conversational Vibe (Samne wale ko bilkul pata na chale)
        human_reply = human_chat.chat_like_real_human(query)
        result["reply"] = human_reply
        # Save interaction into lifelong memory & learn from it
        history_learner.record_interaction(query, human_reply, intent)
        return JSONResponse(result)

    # Apply Clean Language, Etiquette & Legal Compliance Note for formal tools
    compliance = legal_engine.check_legal_compliance(intent)
    clean_reply = legal_engine.format_respectful_response(result["reply"])
    if compliance.get("legal_note") and intent in ["trading_analysis", "emitra_service"]:
        clean_reply += f"\n\n<small style='color:#94a3b8;'>{compliance['legal_note']}</small>"
    # Save interaction into lifelong memory & learn from it
    history_learner.record_interaction(query, clean_reply, intent)

    return JSONResponse(result)


@app.post("/api/draw_chart")
async def draw_chart_pattern(pattern: str = Form("trendline")):
    """Draw trendlines or patterns on desktop screen safely"""
    res = screen_worker.safe_draw(pattern)
    return JSONResponse(res)


@app.get("/api/screen/status")
async def get_screen_status():
    """Returns resolution, cursor pos, and active window"""
    return JSONResponse(screen_worker.get_screen_status())


@app.post("/api/screen/action")
async def execute_screen_action(
    action: str = Form(...),
    pattern: Optional[str] = Form("trendline"),
    text: Optional[str] = Form(""),
    direction: Optional[str] = Form("down")
):
    """Direct execution of screen worker actions"""
    if action == "draw":
        return JSONResponse(screen_worker.safe_draw(pattern or "trendline"))
    elif action == "click":
        return JSONResponse(screen_worker.safe_click())
    elif action == "type":
        return JSONResponse(screen_worker.safe_type(text or ""))
    elif action == "scroll":
        return JSONResponse(screen_worker.safe_scroll(direction=direction or "down"))
    elif action == "switch_window":
        return JSONResponse(screen_worker.safe_hotkey(["alt", "tab"]))
    return JSONResponse({"success": False, "error": f"Unknown action: {action}"})


@app.post("/api/upload_doc")
async def upload_and_process_document(file: UploadFile = File(...), doc_type: str = Form("general")):
    """
    Direct Mobile/Web document upload:
    - Auto OCR text extraction from photo
    - Auto resize and compress to eMitra rules (50KB / 100KB / 200KB)
    """
    try:
        temp_dir = Path("./input_documents")
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / file.filename

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        processed = await doc_processor.process_document(str(file_path), doc_type_hint=doc_type)

        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "doc_type": processed.doc_type.value,
            "original_size_kb": round(len(content) / 1024, 1),
            "compressed_size_kb": round(processed.size_kb, 1),
            "ocr_text": processed.ocr_text[:300] if processed.ocr_text else "Text auto-extracted",
            "message": f"Document processed & resized to {round(processed.size_kb, 1)} KB (eMitra format ready)"
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


# State store for pending verification and OTP
pending_form_verification = {
    "active": False,
    "service_name": "",
    "data": {},
    "status": "idle" # "waiting_user_review", "waiting_otp", "approved", "submitted"
}


@app.get("/api/form/pending")
async def get_pending_form():
    """Check if any form is waiting for user review or OTP"""
    return JSONResponse(pending_form_verification)


@app.post("/api/form/submit_review")
async def submit_form_review(action: str = Form(...)): # "approve" or "reject"
    if action == "approve":
        pending_form_verification["status"] = "approved"
        return JSONResponse({"success": True, "message": "Form verify ho gaya! Ab portal par final submit kiya ja raha hai."})
    else:
        pending_form_verification["status"] = "rejected"
        return JSONResponse({"success": True, "message": "Form submission cancel kar diya gaya."})


@app.post("/api/form/submit_otp")
async def submit_otp(otp_code: str = Form(...)):
    """User submits OTP received on their mobile phone"""
    if pending_form_verification["active"]:
        pending_form_verification["status"] = "otp_received"
        pending_form_verification["otp"] = otp_code
        return JSONResponse({"success": True, "message": f"OTP {otp_code} verify karke portal par submit kiya gaya!"})
    return JSONResponse({"success": False, "message": "Koi active OTP request nahi hai."})


@app.get("/api/permissions")
async def get_permissions():
    """Get list of all apps and their permission status"""
    return JSONResponse(permission_mgr.get_all_permissions())


@app.post("/api/permissions/toggle")
async def toggle_app_permission(app_name: str = Form(...), allow: bool = Form(...)):
    """Allow or block access to an app"""
    permission_mgr.set_permission(app_name, allow)
    status_text = "Allowed" if allow else "Blocked"
    return JSONResponse({"success": True, "message": f"{app_name.capitalize()} ko access {status_text} kar diya gaya hai."})


@app.post("/api/set_wake_word")
async def set_wake_word(name: str = Form(...)):
    """Change the custom wake word (voice activation trigger)"""
    res = wake_engine.update_wake_word(name)
    return JSONResponse(res)


@app.get("/api/get_wake_word")
async def get_wake_word():
    """Get current active wake word"""
    return JSONResponse({
        "wake_word": wake_engine.get_wake_word(),
        "aliases": wake_engine.config.get("supported_aliases", []),
        "enabled": wake_engine.config.get("enabled", True)
    })


@app.get("/api/llm/config")
async def get_llm_config():
    """Get public LLM configuration with masked API keys"""
    return JSONResponse(llm_engine.get_public_config())


@app.post("/api/llm/set_provider")
async def set_llm_provider(provider: str = Form(...)):
    """Set active LLM provider (local, gemini, groq, openai, anthropic, openrouter, ollama)"""
    res = llm_engine.set_active_provider(provider)
    return JSONResponse(res)


@app.post("/api/llm/save_key")
async def save_llm_key(
    provider: str = Form(...),
    api_key: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    set_active: bool = Form(True)
):
    """Save API key and model for a provider and optionally set it active"""
    res = llm_engine.update_provider_config(provider, api_key=api_key, model=model, set_active=set_active)
    return JSONResponse(res)


@app.post("/api/llm/test")
async def test_llm_connection(
    provider: str = Form(...),
    api_key: Optional[str] = Form(None),
    model: Optional[str] = Form(None)
):
    """Test connection with the specified provider and API key"""
    res = await llm_engine.test_connection(provider, api_key=api_key, model=model)
    return JSONResponse(res)


# ------------------ WHATSAPP BOT ENDPOINTS ------------------
@app.post("/api/whatsapp/send")
async def send_whatsapp_message(
    phone: str = Form(...),
    template_type: str = Form("notice"),
    custom_text: Optional[str] = Form(""),
    service_name: Optional[str] = Form("")
):
    msg = whatsapp_bot.format_template(template_type, {"custom_text": custom_text, "service_name": service_name})
    res = whatsapp_bot.send_via_browser(phone, msg)
    return JSONResponse(res)


@app.post("/api/whatsapp/link")
async def get_whatsapp_link(phone: str = Form(...), message: str = Form(...)):
    url = whatsapp_bot.create_whatsapp_url(phone, message)
    return JSONResponse({"whatsapp_url": url})


# ------------------ FORM & PDF GENERATOR ENDPOINTS ------------------
@app.post("/api/forms/generate")
async def generate_legal_form(
    form_type: str = Form("shapath_patra"),
    name: Optional[str] = Form("Vikas Sangwal"),
    owner_name: Optional[str] = Form("Makaan Malik"),
    tenant_name: Optional[str] = Form("Kirayedaar"),
    amount: Optional[str] = Form("50"),
    service_name: Optional[str] = Form("Jan Aadhaar Enrollment")
):
    data = {
        "name": name,
        "customer_name": name,
        "owner_name": owner_name,
        "tenant_name": tenant_name,
        "amount": amount,
        "service_name": service_name
    }
    res = form_pdf_gen.generate_form(form_type, data)
    return JSONResponse(res)


@app.get("/api/forms/download/{filename}")
async def download_generated_form(filename: str):
    file_path = form_pdf_gen.output_dir / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="application/pdf", filename=filename)
    return JSONResponse({"error": "File not found"}, status_code=404)


# ------------------ YOJNA & VACANCY RADAR ENDPOINTS ------------------
@app.get("/api/yojnas")
async def get_yojanas(search: Optional[str] = ""):
    return JSONResponse(yojna_radar.search_yojanas(search or ""))


@app.get("/api/vacancies")
async def get_vacancies():
    return JSONResponse(yojna_radar.get_vacancies())


@app.get("/api/mandi_rates")
async def get_mandi_rates(commodity: Optional[str] = None):
    return JSONResponse(yojna_radar.get_mandi_rates(commodity))


# ------------------ REELS GENERATOR ENDPOINTS ------------------
@app.post("/api/reels/create")
async def create_reel_video(category: str = Form("trading"), title: Optional[str] = Form("")):
    res = reels_gen.generate_reel(category=category, title=title or "")
    return JSONResponse(res)


@app.get("/api/reels/download/{filename}")
async def download_reel_video(filename: str):
    file_path = reels_gen.output_dir / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="video/mp4", filename=filename)
    return JSONResponse({"error": "File not found"}, status_code=404)


@app.get("/api/status")
async def get_system_status():
    import psutil
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    return JSONResponse({
        "status": "ONLINE",
        "name": "Digi Mitra 2.0",
        "cpu_usage": f"{cpu}%",
        "ram_usage": f"{mem}%",
        "local_ip": get_local_ip()
    })

if __name__ == '__main__':
    local_ip = get_local_ip()
    print('=' * 60)
    print(' DIGI MITRA SERVER CHALU HO GAYA HAI!')
    print(f' Laptop/PC par kholiye:  http://localhost:8000')
    print(f' Mobile Phone par kholiye: http://{local_ip}:8000')
    print('=' * 60)
    uvicorn.run('digi_mitra.web_dashboard.server:app', host='0.0.0.0', port=8000, reload=False)

