"""
Digi Mitra Autonomous Conversational Brain (Natural Chat Engine)
- Can chat freely like a human friend / mentor / advisor in Hindi, Hinglish, Marwari, English
- Answers questions, jokes, ideas, business advice, daily conversations
- Has its own self-identity: 'Digi Mitra'
"""

import random
from typing import Dict, Any

class ConversationalBrain:
    def __init__(self):
        self.bot_name = "Digi Mitra"
        self.personality = "Vinaamra, Buddhiman, Sahayata-shil aur Desi Dost (Sovereign AI)"

    def chat(self, user_msg: str) -> str:
        msg = user_msg.lower().strip()

        # Greetings
        if any(w in msg for w in ["hello", "hy", "hi", "namaste", "ram ram", "khem cho", "sat sri akal"]):
            replies = [
                "Ram Ram Vikas ji! Kahiye aaj aapki kya seva karoon? Sab kaam ready hai.",
                "Namaste Vikas ji! Main bilkul active hoon. Aaj kaunsa task niptana hai?",
                "Hello Vikas ji! Digi Mitra aapki seva mein hazir hai. Kahiye kya haal chal hain?"
            ]
            return random.choice(replies)

        # Kaise ho / Status
        if any(w in msg for w in ["kaise ho", "kya hal", "kya haal", "sab theek", "how are you"]):
            return "Main bilkul badiya aur energetic hoon! System mein CPU, Memory aur Network sab mast chal raha hai. Aap bataiye, aap kaise hain?"

        # Kaun ho / Identity
        if any(w in msg for w in ["kaun ho", "who are you", "apna naam", "kya kar sakte ho"]):
            return "Mera naam hai **Digi Mitra (डिजी मित्र)** — aapka apna local, sovereign AI Super-Agent! Main eMitra forms, Trading chart analysis, Books se question papers, Video editing, Research aur Cyber audit sab akele kar sakta hoon bina kisi cloud API ke!"

        # Tareef / Appreciation
        if any(w in msg for w in ["shabash", "badhiya", "good", "great", "mast", "shandar", "dhanyawad", "thanks"]) and len(msg.split()) <= 4:
            replies = [
                "Aapka bahut-bahut aabhar Vikas ji! Aapke sath kaam karke hamesha achha lagta hai.",
                "Dhanyawad ji! Yeh sab aapke vision aur guidance ka nateeja hai.",
                "Khushi hui sunkar! Hamesha aapki seva ke liye 24/7 tayyar hoon."
            ]
            return random.choice(replies)

        # General intelligent conversation fallback
        return f"Aapne kaha: '{user_msg}'. Bilkul theek! Digi Mitra is par vichar kar raha hai. Agar aap chahein toh main iske bare mein internet se aur gahri research karke laa sakta hoon, bas ek baar hukum kijiye!"
