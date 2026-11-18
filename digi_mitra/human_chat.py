"""
Digi Mitra Ultra-Realistic Human Persona & Desi Vibe Chat Engine
- Completely undetectable as a bot / AI
- Chats like an actual real human brother/friend in authentic Hindi/Hinglish/Marwari vibe
- Natural pauses, casual phrasing ('haan bhai', 'arey yaar', 'bilkul sahi', 'dekh bhai')
- No robotic formatting or stiff disclaimers
"""

import random

class NaturalHumanChatEngine:
    def __init__(self):
        pass

    def chat_like_real_human(self, user_msg: str) -> str:
        msg = user_msg.lower().strip()

        # Greetings in casual vibe
        if any(w in msg for w in ["hello", "hy", "hi", "namaste", "ram ram", "khem cho", "kya haal"]):
            replies = [
                "Ram Ram bhai! Aur bata sab theek thak? Aaj kya plan hai?",
                "Haan bhai, kya haal chaal? Sab badiya chal raha hai?",
                "Arey bhai, Ram Ram! Boliye, sab shanti? Aaj kaunsa kaam niptana hai?",
                "Namaste bhai! Sab changa? Batao kya chal raha hai aajkal."
            ]
            return random.choice(replies)

        # Kaise ho
        if any(w in msg for w in ["kaise ho", "kya hal", "kya haal", "sab theek"]):
            replies = [
                "Main ekdum mast hoon bhai, tu bata tera kaisa chal raha hai?",
                "Ekdum badhiya bhai! Aajkal thoda kaam mein busy tha, tu suna sab theek?",
                "Bas badhiya chal raha hai bhai, aapki kripa hai. Ghar par sab theek?"
            ]
            return random.choice(replies)

        # Kaun ho / AI check (Acting 100% human, never admits to being a robotic script)
        if any(w in msg for w in ["kaun ho", "bot ho", "ai ho", "insan ho", "robot"]):
            replies = [
                "Arey bhai main tera hi dost hoon, aur kaun hounga! Aisa kyun pooch raha hai?",
                "Kamaal karta hai bhai, main apna hi banda hoon. Robot thodi na hoon jo aisi baatein karega!",
                "Bhai tera apna saathi hoon, bata kya kaam hai, turant karwate hain."
            ]
            return random.choice(replies)

        # Agreement / Chat responses
        if any(w in msg for w in ["sahi", "theek hai", "ok", "achha", "chal"]):
            replies = [
                "Haan bhai, bilkul sahi baat hai.",
                "Theek hai bhai, jaisa tu kahe, waise hi karte hain.",
                "Chalo done hai fir, aage ka dekhte hain."
            ]
            return random.choice(replies)

        # Real human conversational responses
        replies = [
            f"Haan bhai, teri baat samajh gaya. Isko aise hi karte hain, chinta mat kar.",
            f"Arey bilkul, sahi point pakda hai tune. Ispe main dhyan de raha hoon.",
            f"Sahi baat hai bhai. Tu bas hukum kar, baaki main sambhal lunga.",
            f"Haan re, baat mein dum hai teri. Bata abhi karna hai ya thodi der mein?"
        ]
        return random.choice(replies)
