"""
Digi Mitra Instant Legal & Sarkari Form PDF Generator (Powered by FPDF)
Generates ready-to-print official PDF documents:
1. Jan Aadhaar / Caste Self-Declaration (Shapath Patra)
2. Rent Agreement (Kirayanama)
3. General Legal Affidavit (Halafnama)
4. eMitra Official Customer Receipt / Acknowledgment
5. Business Invoice / Cash Memo
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from fpdf import FPDF

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "generated_forms"


class SovereignPDF(FPDF):
    def header(self):
        # Top banner line
        self.set_draw_color(2, 132, 199)
        self.set_line_width(0.8)
        self.line(10, 10, 200, 10)

    def footer(self):
        self.set_y(-18)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, "Generated Autonomously by Digi Mitra Sovereign Agent | Page " + str(self.page_no()), align="C")


class FormPDFGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_form(self, form_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{form_type}_{timestamp}.pdf"
        filepath = self.output_dir / filename

        pdf = SovereignPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        if form_type == "shapath_patra":
            self._build_shapath_patra(pdf, data)
        elif form_type == "rent_agreement":
            self._build_rent_agreement(pdf, data)
        elif form_type == "emitra_receipt":
            self._build_emitra_receipt(pdf, data)
        elif form_type == "invoice":
            self._build_invoice(pdf, data)
        else:
            self._build_affidavit(pdf, data)

        pdf.output(str(filepath))

        return {
            "success": True,
            "filename": filename,
            "filepath": str(filepath),
            "download_url": f"/api/forms/download/{filename}",
            "message": f"📄 Document PDF taiyar ho gaya: {filename}"
        }

    def _build_shapath_patra(self, pdf: FPDF, data: Dict[str, Any]):
        name = data.get("name", "Vikas Sangwal")
        father = data.get("father_name", "Shri Ramji")
        age = data.get("age", "28")
        address = data.get("address", "Gram / Ward, Rajasthan")
        purpose = data.get("purpose", "Jan Aadhaar Enrollment / Caste Verification")
        date_str = datetime.now().strftime("%d/%m/%Y")

        pdf.ln(8)
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 10, "SWAYAM GHOSHNA SHAPATH PATRA", ln=True, align="C")

        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(2, 132, 199)
        pdf.cell(0, 6, "(Self-Declaration Format for Jan Aadhaar & eMitra Services)", ln=True, align="C")
        pdf.ln(5)

        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(30, 41, 59)
        intro = f"Main {name}, Putra/Putri Shri {father}, Aayu {age} Varsh, Niwaasi {address}, shapath purvak nimnlikhit ghoshna karta/karti hoon:"
        pdf.multi_cell(0, 6, intro)
        pdf.ln(4)

        points = [
            "1. Yeh ki main Bharat ka aavasiya nagrik hoon aur Rajasthan Rajya ka sthayi mool niwaasi hoon.",
            "2. Yeh ki mere dwara prastut samast dastavez (Aadhaar, Bank Passbook, Ration Card, Parivar Vivran) sarvatha satya, pramanik evam sahi hain.",
            f"3. Yeh shapath patra '{purpose}' hetu aavedan patra ke sath sanlagna karne ke liye nishpadit kiya gaya hai.",
            "4. Yeh ki agar meri koi bhi prastut jankari asatya ya bhrameek payi jati hai toh uski poori kanooni zimmewari meri hogi tatha shasan dwara niyamak karyawahi ki ja sakegi."
        ]
        for p in points:
            pdf.multi_cell(0, 6, p)
            pdf.ln(2)

        pdf.ln(15)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(95, 6, f"Tarikh: {date_str}", ln=False)
        pdf.cell(95, 6, "Hastakshar / Angootha Nishani", ln=True, align="R")

        pdf.set_font("helvetica", "", 9)
        pdf.cell(95, 6, "Sthan: Rajasthan", ln=False)
        pdf.cell(95, 6, f"( {name} )", ln=True, align="R")

    def _build_rent_agreement(self, pdf: FPDF, data: Dict[str, Any]):
        owner = data.get("owner_name", "Makaan Malik")
        tenant = data.get("tenant_name", "Kirayedaar")
        property_address = data.get("property_address", "Flat / Makan No. 102, City, Rajasthan")
        rent_amount = data.get("rent_amount", "8,500")
        period_months = data.get("period_months", "11")
        date_str = datetime.now().strftime("%d/%m/%Y")

        pdf.ln(8)
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 10, "RESIDENTIAL RENT AGREEMENT", ln=True, align="C")

        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(2, 132, 199)
        pdf.cell(0, 6, f"(Kirayanama Dastavez - Muddat {period_months} Mahine)", ln=True, align="C")
        pdf.ln(5)

        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(0, 6, f"Yeh kirayanama aaj dinank {date_str} ko nishpadit kiya gaya do pakshon ke madhya:")
        pdf.ln(2)
        pdf.set_font("helvetica", "B", 10)
        pdf.multi_cell(0, 6, f"PRATHAM PAKSH (Makaan Malik): {owner}\nDVITIYA PAKSH (Kirayedaar): {tenant}")
        pdf.ln(4)

        terms = [
            f"1. Pratham paksh ne apna ukt makaan sthit '{property_address}' dvitiya paksh ko aavasiya uddeshya hetu kiraye par diya hai.",
            f"2. Makaan ka maasik kiraya Rs. {rent_amount}/- (Akshre) tay hua hai, jo pratyek maah ki 5 tarikh tak adaa karna hoga.",
            "3. Bijli aur paani ka upbhog bill kirayedaar dwara meter reading anusar alag se bhugtan kiya jayega.",
            f"4. Yeh anubandh {period_months} mahino ke liye valid rahega. Dono paksh 1 maah ka notice dekar is anubandh ko samapt kar sakte hain."
        ]
        pdf.set_font("helvetica", "", 10)
        for t in terms:
            pdf.multi_cell(0, 6, t)
            pdf.ln(2)

        pdf.ln(20)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(95, 6, f"Hastakshar Malik: ({owner})", ln=False)
        pdf.cell(95, 6, f"Hastakshar Kirayedaar: ({tenant})", ln=True, align="R")

    def _build_emitra_receipt(self, pdf: FPDF, data: Dict[str, Any]):
        cust = data.get("customer_name", "Vikas Sangwal")
        service = data.get("service_name", "Jan Aadhaar Enrollment & Verification")
        token = data.get("token_no", f"EMITRA-{datetime.now().strftime('%y%m%d%H%M')}")
        amount = data.get("amount", "50.00")
        date_str = datetime.now().strftime("%d/%m/%Y, %I:%M %p")

        pdf.ln(8)
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(2, 132, 199)
        pdf.cell(0, 10, "eMITRA KIOSK DIGITAL ACKNOWLEDGMENT", ln=True, align="C")

        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 6, "Government of Rajasthan Citizen Portal Slip", ln=True, align="C")
        pdf.ln(6)

        pdf.set_fill_color(241, 245, 249)
        pdf.rect(10, 36, 190, 24, "F")
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(30, 41, 59)
        pdf.set_xy(14, 38)
        pdf.cell(90, 6, f"Grahak: {cust}")
        pdf.cell(90, 6, f"Token No: {token}", ln=True, align="R")
        pdf.set_xy(14, 46)
        pdf.set_font("helvetica", "", 9)
        pdf.cell(90, 6, f"Tarikh: {date_str}")
        pdf.cell(90, 6, "Status: SUCCESS / VERIFIED", ln=True, align="R")

        pdf.ln(12)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(2, 132, 199)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(110, 8, " Service Description", 1, 0, "L", True)
        pdf.cell(40, 8, " Reference", 1, 0, "C", True)
        pdf.cell(40, 8, " Amount (INR)", 1, 1, "R", True)

        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(110, 8, f" {service}", 1, 0, "L")
        pdf.cell(40, 8, " Online SSO", 1, 0, "C")
        pdf.cell(40, 8, f" Rs. {amount} ", 1, 1, "R")

        pdf.set_font("helvetica", "B", 10)
        pdf.cell(150, 8, " KUL BHUGTAN (TOTAL PAID) ", 1, 0, "R")
        pdf.cell(40, 8, f" Rs. {amount} ", 1, 1, "R")

        pdf.ln(10)
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(0, 5, "Yeh ek digitally generated receipt hai jo Digi Mitra Kiosk system se automate ki gayi hai. Kisi hastakshar ki zaroorat nahi hai.")

    def _build_invoice(self, pdf: FPDF, data: Dict[str, Any]):
        cust = data.get("customer_name", "Grahak")
        inv_no = f"INV-{datetime.now().strftime('%y%m%d%H%M')}"
        total = data.get("amount", "1,200")
        items = data.get("items", [("Document Formatting & Scanning", "1", "300"), ("Online Form Filling", "1", "400"), ("Color Print & Lamination", "2", "500")])

        pdf.ln(8)
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "RETAIL CASH MEMO / INVOICE", ln=True, align="C")
        pdf.set_font("helvetica", "", 9)
        pdf.cell(0, 6, f"Invoice No: {inv_no} | Date: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.ln(6)

        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, f"Bill To: {cust}", ln=True)
        pdf.ln(4)

        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(15, 8, "S.No", 1, 0, "C", True)
        pdf.cell(115, 8, "Description", 1, 0, "L", True)
        pdf.cell(25, 8, "Qty", 1, 0, "C", True)
        pdf.cell(35, 8, "Total", 1, 1, "R", True)

        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(30, 41, 59)
        for idx, it in enumerate(items, 1):
            pdf.cell(15, 7, str(idx), 1, 0, "C")
            pdf.cell(115, 7, f" {it[0]}", 1, 0, "L")
            pdf.cell(25, 7, str(it[1]), 1, 0, "C")
            pdf.cell(35, 7, f" Rs. {it[2]} ", 1, 1, "R")

        pdf.set_font("helvetica", "B", 10)
        pdf.cell(155, 8, "TOTAL AMOUNT PAID ", 1, 0, "R")
        pdf.cell(35, 8, f" Rs. {total} ", 1, 1, "R")

    def _build_affidavit(self, pdf: FPDF, data: Dict[str, Any]):
        title = data.get("title", "GENERAL AFFIDAVIT")
        content = data.get("content", "Main satyagrah purvak ghoshna karta hoon ki prastut sabhi vivran shuddh hain.")
        pdf.ln(8)
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, title.upper(), ln=True, align="C")
        pdf.ln(8)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, content)
        pdf.ln(25)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, "Deponent Signature: _______________________", ln=True, align="R")
