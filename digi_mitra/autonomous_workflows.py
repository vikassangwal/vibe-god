import time
from typing import Dict, Any, List

class AutonomousWorkflows:
    def __init__(self, screen_worker, yojna_radar, trading_engine, form_pdf_gen):
        self.screen_worker = screen_worker
        self.yojna_radar = yojna_radar
        self.trading_engine = trading_engine
        self.form_pdf_gen = form_pdf_gen

    def run_morning_briefing(self) -> Dict[str, Any]:
        '''Fetches Mandi rates, Top Govt schemes, and Market outlook'''
        mandi_data = self.yojna_radar.get_mandi_rates()
        vac_data = self.yojna_radar.get_vacancies()

        mandi_list = mandi_data if isinstance(mandi_data, list) else mandi_data.get('rates', [])
        vac_list = vac_data if isinstance(vac_data, list) else vac_data.get('vacancies', [])

        briefing = {
            'greeting': 'सुप्रभात विकास जी! 🌅 आज का डिजि मित्र मॉर्निंग ब्रीफिंग तैयार है:',
            'top_mandi_rates': mandi_list[:4],
            'active_govt_vacancies': vac_list[:3],
            'market_status': 'NIFTY / BANKNIFTY levels ready on dashboard',
            'generated_at': time.strftime('%d %b %Y, %I:%M %p')
        }
        return {'success': True, 'briefing': briefing}

    def generate_daily_shop_report(self, tokens_count: int = 15, total_revenue: float = 750.0) -> Dict[str, Any]:
        '''Generates daily eMitra closing revenue summary'''
        res = self.form_pdf_gen.generate_form(
            form_type='cash_memo',
            data={
                'name': 'Daily eMitra & Cyber Cafe Report',
                'applicant_name': 'Vikas Sangwal',
                'phone': '9876543210',
                'address': 'eMitra Kiosk Center',
                'details': f'Total Tokens Processed: {tokens_count} | Total Online Services: {tokens_count * 2}',
                'items': [
                    {'desc': 'Jan Aadhaar Updates & Enrollments', 'amount': str(total_revenue * 0.4)},
                    {'desc': 'Police Verification & Character Certs', 'amount': str(total_revenue * 0.3)},
                    {'desc': 'Govt Scheme Form Submissions', 'amount': str(total_revenue * 0.3)}
                ],
                'total': str(total_revenue)
            }
        )
        return {
            'success': True,
            'message': f'📊 Daily Closing Report ready! Total Collection: ₹{total_revenue}',
            'pdf_path': res.get('file_path'),
            'download_url': res.get('download_url')
        }
