"""
Digi Mitra Wise Mentor & Mistake Correction Guardian Engine
Role:
- If user gives a mistaken, risky, unfeasible, or wrong instruction:
  * Immediately intercepts with respectful correction ('Rukiye Vikas ji, yahan ek galti ho sakti hai...')
  * Explains the right, safe, and profitable alternative
  * Executes the corrected, optimal path upon user consent
"""

from typing import Dict, Any, Tuple

class WiseMentorGuardian:
    def __init__(self):
        pass

    def inspect_and_correct_mistakes(self, user_command: str) -> Tuple[bool, str]:
        cmd = user_command.lower()

        # Mistake 1: Risky or wrong trading move (e.g. buying at extreme top or selling at bottom)
        if any(w in cmd for w in ["all in", "pura paisa laga do", "saare paise trade me", "loan leke\出于"]):
            return (
                True,
                "⚠️ <b>Rukiye Vikas ji!</b> Yahan risk management ki galti ho rahi hai.<br>"
                "Trading ka sunhera niyam hai: <i>Kabhi bhi sara paisa ek jagah nahi lagate (Capital Protection).</i><br>"
                "👉 <b>Sahi Tarika:</b> Keval 2% se 5% risk ke sath disciplined stop-loss par kaam karein. Kya main safe trade calculate karoon?"
            )

        # Mistake 2: Missing essential documents before filing government form
        if "form bhar do" in cmd and not any(w in cmd for w in ["aadhaar", "photo", "detail", "doc", "jan"]):
            return (
                True,
                "⚠️ <b>Dhyan dijiye Vikas ji!</b> eMitra / Sarkari form bharne se pehle zaroori dastavez check karna zaroori hai.<br>"
                "👉 <b>Sahi Tarika:</b> Pehle aavedak ka Aadhaar, Photo aur Address proof attach karein taaki form reject na ho. Kya main document upload window open karoon?"
            )

        # Mistake 3: Underpricing freelance work
        if any(w in cmd for w in ["10 rupe me", "50 rupe me sara", "free me karke de do"]) and "freelance" in cmd:
            return (
                True,
                "⚠️ <b>Galti se bachiye Vikas ji!</b> Itne kam daam mein kaam karne se aapki service ki value kam ho jayegi.<br>"
                "👉 <b>Sahi Tarika:</b> Standard market rate quote karein taaki client serious samjhe aur achhi kamai ho."
            )

        # Mistake 4: Spending money without ROI
        if any(w in cmd for w in ["paid ad chala do", "kisi ko paise bhej do", "advance pay\出于"]):
            return (
                True,
                "⚠️ <b>Sachet rahein Vikas ji!</b> Bina return-on-investment (ROI) check kiye advance kharcha karna galti ho sakti hai.<br>"
                "👉 <b>Sahi Tarika:</b> Pehle organic/free tarike se test karein. Paisa safe rakhna Digi Mitra ka pehla kartavya hai!"
            )

        return (False, "")

