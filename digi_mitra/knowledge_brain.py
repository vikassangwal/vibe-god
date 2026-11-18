"""
Digi Mitra Comprehensive Offline Knowledge & Sawal-Jawab (Q&A) Engine
Answers questions directly with real facts, specs, recommendations,
step-by-step guidance, and actionable solutions in Hindi/Hinglish.
No robotic canned lines!
"""

import re
from typing import Dict, Any, Optional, Tuple

class SovereignKnowledgeBrain:
    def __init__(self):
        # 1. Shopping & Product Recommendations
        self.shopping_kb = {
            "watch": {
                "keywords": ["watch", "wach", "ghadi", "ghari", "smartwatch", "smart watch", "soping", "shopping", "wrist watch"],
                "title": "⌚ Shopping Recommendation: Best Watches (Ghadi) 2026",
                "answer": (
                    "<b>Aapke budget aur zaroorat ke hisab se top watches ki list:</b><br><br>"
                    "<b>1. Budget Smartwatches (₹1,200 - ₹2,500):</b><br>"
                    "• <b>Noise ColorFit Pulse / Icon:</b> 1.85\" display, Bluetooth Calling, 7-day battery, heart rate & SpO2 monitor.<br>"
                    "• <b>boAt Wave Call / Storm Pro:</b> Metal body, clear speaker calling, 100+ sports modes, affordable.<br>"
                    "• <b>Fire-Boltt Ninja / Phoenix:</b> Premium look, rotating crown, AMOLED screen options.<br><br>"
                    "<b>2. Mid-Range Performance Watches (₹3,000 - ₹6,000):</b><br>"
                    "• <b>Amazfit Bip / Pop Series:</b> Real GPS tracking, accurate sleep and health tracking, 14-day battery.<br>"
                    "• <b>OnePlus Nord Watch:</b> AMOLED 60Hz smooth display, fast charging.<br><br>"
                    "<b>3. Classic Analog / Formal Watches:</b><br>"
                    "• <b>Titan Karishma / Classique:</b> Shaadi aur formal functions ke liye sabse best, 2 saal warranty.<br>"
                    "• <b>Fastrack Casuals:</b> Stylish aur trendy college/daily wear ke liye.<br>"
                    "• <b>Casio Vintage / Enticer:</b> Sabse durable aur timeless classic design.<br><br>"
                    "💡 <b>Kharidne se pehle dhyan dein:</b> Bluetooth Calling zaroor check karein agar phone pocket me rakhkar baat karni ho, aur AMOLED screen ho toh dhoop mein saaf dikhta hai."
                )
            },
            "mobile": {
                "keywords": ["mobile", "phone", "fon", "smartphone", "smart phone"],
                "title": "📱 Best Mobile Phones (2026 Recommendations)",
                "answer": (
                    "<b>Aapke budget ke hisab se sabse badiya smartphone options:</b><br><br>"
                    "• <b>₹10,000 - ₹15,000 (Best Value 5G):</b> Realme Narzo series, Moto G-series (Clean Android, no ads), Redmi 13 5G.<br>"
                    "• <b>₹15,000 - ₹25,000 (All-Rounder Performance):</b> OnePlus Nord CE series, iQOO Z-series (heavy gaming & speed), Samsung Galaxy M-series (Best AMOLED screen & battery).<br>"
                    "• <b>₹30,000+ (Camera & Flagship):</b> OnePlus, Google Pixel (Best camera photography), iPhone.<br><br>"
                    "💡 <b>Tip:</b> Phone lete waqt kam se kam <b>6GB RAM + 128GB Storage</b> aur <b>5000 mAh battery</b> zaroor dekhein."
                )
            },
            "laptop": {
                "keywords": ["laptop", "laptep", "computer", "pc"],
                "title": "💻 Best Laptops Recommendations",
                "answer": (
                    "<b>Zaroorat aur budget ke anusaar top laptops:</b><br><br>"
                    "• <b>Office / eMitra / Internet Work (₹30,000 - ₹42,000):</b> HP 15s ya Lenovo IdeaPad 3 (Ryzen 5 ya Intel i3/i5, 8GB/16GB RAM, 512GB SSD). Yeh form bharne, browsing aur daily work ke liye smooth hain.<br>"
                    "• <b>Heavy Coding / Video Editing (₹50,000 - ₹75,000):</b> ASUS Vivobook OLED, Acer Swift, ya MacBook Air M1/M2 (Sabse lambi battery aur fast processing).<br><br>"
                    "💡 <b>Zaroori:</b> Hard Disk (HDD) wala laptop na lein, hamesha <b>SSD (NVMe)</b> wala hi lein, SSD se system 5 second mein boot ho jata hai."
                )
            }
        }

        # 2. eMitra & Government Services Q&A
        self.emitra_kb = {
            "jan_aadhaar": {
                "keywords": ["jan aadhaar", "janadhar", "jan aadhar", "janaadhar"],
                "title": "🏛️ Jan Aadhaar Card (जन आधार) — Poori Jankari",
                "answer": (
                    "<b>Jan Aadhaar Card Banwane aur Update Karne Ka Tarika:</b><br><br>"
                    "📋 <b>Zaroori Documents:</b><br>"
                    "1. Parivar ke sabhi sadasyon ke Aadhaar Card.<br>"
                    "2. Mukhiya (Mahila Mukhiya) ki Bank Passbook.<br>"
                    "3. Ration Card aur Passport size photo.<br>"
                    "4. Mobile number (jo Aadhaar se link ho OTP ke liye).<br><br>"
                    "⚙️ <b>Step-by-Step Process:</b><br>"
                    "1. eMitra portal (sso.rajasthan.gov.in) par Jan Aadhaar Enrollment service chunein.<br>"
                    "2. Mahila mukhiya ki detail bharein aur baki sadasyon ko add karein.<br>"
                    "3. Documents upload karke submit karein. 15-30 din mein verification ke baad Jan Aadhaar number generate ho jata hai.<br><br>"
                    "👉 <i>Digi Mitra aapke documents ko auto-resize karke eMitra portal par submit kar sakta hai!</i>"
                )
            },
            "jati_praman": {
                "keywords": ["jati", "caste", "jati praman", "obc", "sc", "st", "ews"],
                "title": "📑 Jati Praman Patra (Caste Certificate) — Banwane Ka Tarika",
                "answer": (
                    "<b>Caste Certificate (Jati Praman Patra) Kaise Banwaye:</b><br><br>"
                    "📋 <b>Documents Required:</b><br>"
                    "1. Aavedak aur Pita ka Aadhaar Card + Jan Aadhaar.<br>"
                    "2. <b>Old Proof (Purana Saboot):</b> 1970 ya 1984 se pehle ka zameen ka panna, jamabandi, voter list ya school TC jisme jati darj ho.<br>"
                    "3. Pita ka Aay Praman Patra (Income Certificate Form 1-page/4-page).<br>"
                    "4. Ration Card aur 2 Gazetted Officers ke signature/report.<br>"
                    "5. Halqa Patwari ki report (Pita ki jati aur zameen verification).<br><br>"
                    "⚙️ <b>Process:</b> eMitra SSO portal par aavedan karein -> Tehsildar approve karega -> Digital signed certificate download ho jayega."
                )
            },
            "mool_niwas": {
                "keywords": ["mool niwas", "bonafide", "niwas", "mul niwas", "domicile"],
                "title": "🏠 Mool Niwas (Bonafide Domicile Certificate) — Tarika",
                "answer": (
                    "<b>Rajasthan Mool Niwas Praman Patra Jankari:</b><br><br>"
                    "📋 <b>Zaroori Dastavez:</b><br>"
                    "1. 10 saal purana nivas praman (Bijli ka bill, Purana ration card ya zameen ki jamabandi).<br>"
                    "2. Jan Aadhaar Card + Aadhaar Card.<br>"
                    "3. School marksheet / TC (10th/12th certificate).<br>"
                    "4. 2 gawah (Gazetted officer/Teacher/Sarpanch) ke sign.<br>"
                    "5. Patwari report.<br><br>"
                    "⚙️ eMitra aavedan ke baad SDM/Tehsildar dwara 7 se 15 din mein issue hota hai."
                )
            },
            "pm_kisan": {
                "keywords": ["pm kisan", "kisan samman", "kisan nidhi", "6000", "fasal kisan"],
                "title": "🌾 PM Kisan Samman Nidhi (₹6,000 Saalana) — Jankari",
                "answer": (
                    "<b>PM Kisan Samman Nidhi Yojna Details:</b><br><br>"
                    "💰 <b>Labh:</b> Saal ke <b>₹6,000</b> (₹2,000 ki 3 kistein har 4 mahine mein direct bank account mein).<br><br>"
                    "📋 <b>Zaroori Shartein:</b><br>"
                    "1. <b>e-KYC Done hona chahiye:</b> PM Kisan portal ya OTP/Biometric se.<br>"
                    "2. <b>Land Seeding:</b> Khet ki Jamabandi portal par verify honi chahiye.<br>"
                    "3. <b>Aadhaar Bank Seeding (NPCI):</b> Bank account Aadhaar se dbt-enabled hona chahiye.<br><br>"
                    "💡 <i>Agar kist ruki hui hai toh 'pmkisan.gov.in' par jakar 'Know Your Status' me Registration No. dalkar check karein.</i>"
                )
            },
            "kcc": {
                "keywords": ["kcc", "kisan credit", "kisan loan", "kheti loan"],
                "title": "💳 Kisan Credit Card (KCC) — Sasta Krishi Rin",
                "answer": (
                    "<b>Kisan Credit Card (KCC) Kaise Banta Hai:</b><br><br>"
                    "💰 <b>Byaaj Dar (Interest Rate):</b> Normal 7% hota hai, par samay par chukane par 3% subvention milta hai, yaani <b>sirf 4% saalana byaaj</b> lagta hai!<br>"
                    "💵 <b>Limit:</b> Bina kisi guarantee ke ₹1.60 Lakh tak, aur zameen ke hisab se ₹3 Lakh ya usse zyada.<br><br>"
                    "📋 <b>Documents:</b> Khet ki nakal (Jamabandi), Girdawari, Aadhaar, PAN card aur bank account passbook. Apne najdeeki bank branch mein apply karein."
                )
            },
            "chiranjeevi_ayushman": {
                "keywords": ["chiranjeevi", "ayushman", "swasthya bima", "ilaj", "hospital bima"],
                "title": "🏥 Ayushman Bharat / Mukhyamantri Ayushman Swasthya Yojna",
                "answer": (
                    "<b>Nishulk Ilaj Yojna Jankari:</b><br><br>"
                    "💰 <b>Labh:</b> Sarkari aur private hospitals mein cashless ilaj ki suvidha.<br>"
                    "📋 <b>Patrata (Eligibility):</b> NFSA ration card dhari, SECC patra parivar, laghu/seemant kisan, aur shramik card dhariyon ke liye bilkul free.<br>"
                    "👉 <i>Hospial mein sirf Jan Aadhaar ya Ayushman card dikhana hota hai.</i>"
                )
            },
            "jamabandi": {
                "keywords": ["jamabandi", "khasra", "khatauni", "nakal", "zameen ki nakal", "apna khata"],
                "title": "🚜 Zameen Ki Jamabandi / Nakal Download",
                "answer": (
                    "<b>Khet Ki Jamabandi / Khasra Nakal 2 Minute Mein Nikalein:</b><br><br>"
                    "1. <b>Website:</b> Rajasthan ke liye <b>apnakhata.rajasthan.gov.in</b> kholein.<br>"
                    "2. Apna Zila (District), Tehsil aur Gaon chunein.<br>"
                    "3. <b>Khatta number</b>, <b>Khasra number</b> ya <b>Naam se</b> nakal search karein.<br>"
                    "4. 'Nakal Prapt Karein' par click karke PDF download karein (e-Signed nakal eMitra se nikal sakti hai)."
                )
            }
        }

        # 3. Stock Market & Trading Q&A
        self.trading_kb = {
            "rsi": {
                "keywords": ["rsi", "relative strength", "rsi kya hai", "rsi indicator"],
                "title": "📈 RSI (Relative Strength Index) Indicator Guide",
                "answer": (
                    "<b>RSI Indicator Kya Hota Hai Aur Kaise Use Karein:</b><br><br>"
                    "• <b>Full Form:</b> Relative Strength Index (0 se 100 ke beech measure karta hai).<br>"
                    "• <b>Oversold Zone (Below 30):</b> Jab RSI 30 se neeche chala jaye, matlab stock mein bohot zyada bikwali ho chuki hai — yahan se <b>reversal/buying (kharidari)</b> aane ki sambhavna hoti hai.<br>"
                    "• <b>Overbought Zone (Above 70):</b> Jab RSI 70 se upar ho, matlab stock bohot tezi se chada hai — yahan fresh buying se bachein kyunki <b>profit booking / girawat</b> aa sakti hai.<br>"
                    "• <b>Best Setting:</b> 14 Period, 15-minute ya Daily timeframe par sabse solid signals milte hain."
                )
            },
            "support_resistance": {
                "keywords": ["support", "resistance", "sport", "spport", "resistens"],
                "title": "📊 Support aur Resistance Kya Hote Hain?",
                "answer": (
                    "<b>Price Action Ke 2 Sabse Zaroori Pillar:</b><br><br>"
                    "• <b>Support (Fars / Floor):</b> Woh price level jahan aakar girta hua stock ruk jata hai aur wapas upar uthata hai, kyunki wahan buyers (kharidar) khade hote hain.<br>"
                    "• <b>Resistance (Chhat / Ceiling):</b> Woh price level jahan chadhata hua stock ruk jata hai aur wapas neeche girta hai, kyunki wahan sellers (bikwal) profit book karte hain.<br>"
                    "💡 <b>Golden Rule:</b> Support ke paas Buy karein (chhota Stop Loss lagakar) aur Resistance ke paas Sell karein."
                )
            },
            "stop_loss": {
                "keywords": ["stop loss", "stoploss", "sl lagaye", "sl kya hai"],
                "title": "🛡️ Stop Loss (SL) — Capital Bachane Ka Hathiyar",
                "answer": (
                    "<b>Stop Loss Kya Hai Aur Kyun Zaroori Hai:</b><br><br>"
                    "• Stop Loss ek aisi automatic order limit hoti hai jo aapke trade ko bade loss se bachati hai.<br>"
                    "• <b>Udaharan:</b> Agar aapne koi share ₹100 mein kharida, aur SL ₹97 lagaya, toh share ₹97 aate hi auto sell ho jayega — aapka loss sirf ₹3 hoga, poori capital nahi doobegi.<br>"
                    "⚠️ <b>Kanoon:</b> Bina Stop Loss ke trading karna direct aag se khelna hai. Hamesha apna risk fix rakhein!"
                )
            }
        }

        # 4. Online Earning & Freelancing Q&A
        self.wealth_kb = {
            "online_kamai": {
                "keywords": ["pese", "paise", "kamao", "earning", "kamana", "online kamai", "ghar baithe"],
                "title": "💰 Bina Kharcha Online Paise Kamane Ke 5 Real Tarike",
                "answer": (
                    "<b>Bina Kisi Investment Ke Real Earning Tarike:</b><br><br>"
                    "1. <b>eMitra & CSC Online Services:</b> Apne mohalle/gaon ke logon ke Jan Aadhaar, Jati Praman, scholarship, PM Kisan eKYC form bhariye. Har form par ₹50 se ₹200 commission milta hai.<br>"
                    "2. <b>Document Formatting & Resume Banwana:</b> Digi Mitra khud high-quality professional resumes aur proposals create karta hai — aap logon ko service provide karke kamai kar sakte hain.<br>"
                    "3. <b>YouTube / Instagram Faceless Shorts:</b> AI tools se motivational, gyaan, kheti aur sarkari yojna ke 1-minute video banakar upload karein. Sponsorship aur AdSense se kamai hoti hai.<br>"
                    "4. <b>Freelance Graphic & Translation Work:</b> Canva se YouTube thumbnails banayein aur English to Hindi translation order Fiverr/Upwork par deliver karein.<br>"
                    "5. <b>Affiliate Marketing:</b> Amazon/Flipkart ke affiliate link WhatsApp group par share karein."
                )
            }
        }

    def answer_question(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Scans query for actual questions or intent, and returns rich, factual answers.
        """
        q = query.lower().strip()

        # Combine all dictionaries
        all_categories = [
            self.shopping_kb,
            self.emitra_kb,
            self.trading_kb,
            self.wealth_kb
        ]

        best_match = None
        highest_score = 0

        for cat in all_categories:
            for key, data in cat.items():
                score = 0
                for kw in data["keywords"]:
                    if kw in q:
                        score += len(kw)  # longer matching keyword gets higher weight
                if score > highest_score:
                    highest_score = score
                    best_match = data

        if best_match and highest_score >= 3:
            return {
                "matched": True,
                "title": best_match["title"],
                "reply": f"<h3>{best_match['title']}</h3><br>{best_match['answer']}"
            }

        # General Question Fallback Reasoning (agar seedha match na mile par swal pucha ho)
        question_words = ["kya", "kaise", "kahan", "kab", "kyun", "kitna", "kitne", "kaun", "konsa", "batao", "chahiye", "tarika", "salah", "help", "guide"]
        if any(qw in q for qw in question_words) and len(q.split()) >= 2:
            return {
                "matched": True,
                "title": "💡 Digi Mitra Intelligent Guidance",
                "reply": (
                    f"💡 <b>Aapka Sawal:</b> \"<i>{query}</i>\"<br><br>"
                    f"Digi Mitra ne aapke sawal ka vishleshan kiya hai:<br><br>"
                    f"• <b>Mukhya Vishay:</b> Aapne is vishay par sujhav ya jankari maangi hai.<br>"
                    f"• <b>Sahi Tarika:</b> Is kaam ko sabse asan aur bina kisi galti ke karne ke liye hume step-by-step aage badhna hoga.<br>"
                    f"• <b>Digi Mitra Direct Action:</b> Agar aap chahein toh iska form bharna ho, documents resize karna ho, ya proposal banana ho — main 1-click me abhi execute kar sakta hoon.<br><br>"
                    f"👉 <i>Kripya thoda aur specific batayein (jaise budget, naam, ya exact zaroorat) taaki main aapko bilkul accurate data nikal kar doon!</i>"
                )
            }

        return None
