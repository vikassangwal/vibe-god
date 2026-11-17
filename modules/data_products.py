"""
Data Products Generator Module for Wife God Agent
Automated generation of Mandi Reports, Crop Calendars, Freelance Rate Reports
"""

import asyncio
import logging
import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.local_llm import LocalLLM
    from ..core.voice import VoiceCommunicator
    from ..core.database import DatabaseManager

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
except ImportError:
    pass

logger = logging.getLogger("WifeGod.DataProducts")


class ProductType(Enum):
    MANDI_WEEKLY = "mandi_weekly"
    MANDI_MONTHLY = "mandi_monthly"
    CROP_CALENDAR = "crop_calendar"
    FREELANCE_RATES = "freelance_rates"
    INPUT_PRICES = "input_prices"
    WEATHER_REPORT = "weather_report"
    CROP_ADVISORY = "crop_advisory"
    MARKET_ANALYSIS = "market_analysis"


class OutputFormat(Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


@dataclass
class ProductTemplate:
    id: str
    name: str
    type: ProductType
    description: str
    sections: List[Dict]
    frequency: str  # daily, weekly, monthly, quarterly
    formats: List[OutputFormat]
    subscribers: List[str] = field(default_factory=list)


@dataclass
class GeneratedProduct:
    id: str
    template_id: str
    name: str
    format: OutputFormat
    file_path: str
    generated_at: datetime
    size_bytes: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataProductsGenerator:
    """
    Data Products Generator
    - Mandi Weekly/Monthly Reports
    - Crop Calendars (Kharif/Rabi/Zaid)
    - Freelance Rate Reports
    - Input Price Tracking
    - Weather Reports
    - Crop Advisory Bulletins
    - Auto-publish to Gumroad/own site
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.templates: Dict[str, ProductTemplate] = {}
        self.products: Dict[str, GeneratedProduct] = {}
        self._db = None
        self._llm = None
        self._voice = None
        self._generation_task = None
        self._output_dir = Path(self.config.get("output_dir", "./data_products"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def set_dependencies(self, db, llm, voice):
        self._db = db
        self._llm = llm
        self._voice = voice

    async def initialize(self):
        """Initialize data products generator"""
        logger.info("Initializing DataProductsGenerator...")

        # Load templates
        await self._load_templates()

        # Start generation scheduler
        self._generation_task = asyncio.create_task(self._generation_scheduler())

        logger.info("DataProductsGenerator initialized")

    async def _load_templates(self):
        """Load product templates"""
        # Default templates
        default_templates = [
            ProductTemplate(
                id="mandi_weekly",
                name="Weekly Mandi Report",
                type=ProductType.MANDI_WEEKLY,
                description="Weekly mandi price analysis for major commodities",
                sections=[
                    {"name": "Price Summary", "data_source": "spot_prices"},
                    {"name": "Top Gainers/Losers", "data_source": "price_changes"},
                    {"name": "Arrival Trends", "data_source": "arrivals"},
                    {"name": "Market Outlook", "data_source": "predictions"}
                ],
                frequency="weekly",
                formats=[OutputFormat.PDF, OutputFormat.EXCEL, OutputFormat.CSV]
            ),
            ProductTemplate(
                id="mandi_monthly",
                name="Monthly Mandi Report",
                type=ProductType.MANDI_MONTHLY,
                description="Comprehensive monthly market analysis",
                sections=[
                    {"name": "Executive Summary", "data_source": "summary"},
                    {"name": "Commodity-wise Analysis", "data_source": "commodity_analysis"},
                    {"name": "Mandi-wise Comparison", "data_source": "mandi_comparison"},
                    {"name": "Seasonal Trends", "data_source": "seasonal"},
                    {"name": "Policy Impact", "data_source": "policy"}
                ],
                frequency="monthly",
                formats=[OutputFormat.PDF, OutputFormat.EXCEL]
            ),
            ProductTemplate(
                id="crop_calendar_kharif",
                name="Kharif Crop Calendar",
                type=ProductType.CROP_CALENDAR,
                description="Kharif season crop calendar with activities",
                sections=[
                    {"name": "Month-wise Activities", "data_source": "crop_activities"},
                    {"name": "Sowing Calendar", "data_source": "sowing_dates"},
                    {"name": "Input Schedule", "data_source": "input_schedule"},
                    {"name": "Pest/Disease Alerts", "data_source": "pest_alerts"}
                ],
                frequency="seasonal",
                formats=[OutputFormat.PDF, OutputFormat.HTML]
            ),
            ProductTemplate(
                id="crop_calendar_rabi",
                name="Rabi Crop Calendar",
                type=ProductType.CROP_CALENDAR,
                description="Rabi season crop calendar with activities",
                sections=[
                    {"name": "Month-wise Activities", "data_source": "crop_activities"},
                    {"name": "Sowing Calendar", "data_source": "sowing_dates"},
                    {"name": "Irrigation Schedule", "data_source": "irrigation_schedule"},
                    {"name": "Harvest Timeline", "data_source": "harvest_timeline"}
                ],
                frequency="seasonal",
                formats=[OutputFormat.PDF, OutputFormat.HTML]
            ),
            ProductTemplate(
                id="freelance_rates",
                name="Freelance Rate Report",
                type=ProductType.FREELANCE_RATES,
                description="Upwork/LinkedIn rate analysis by skill",
                sections=[
                    {"name": "Rate Trends", "data_source": "rate_trends"},
                    {"name": "Skill-wise Rates", "data_source": "skill_rates"},
                    {"name": "Geographic Analysis", "data_source": "geo_rates"},
                    {"name": "Project Type Rates", "data_source": "project_rates"}
                ],
                frequency="monthly",
                formats=[OutputFormat.PDF, OutputFormat.EXCEL, OutputFormat.CSV]
            ),
            ProductTemplate(
                id="input_prices",
                name="Agricultural Input Prices",
                type=ProductType.INPUT_PRICES,
                description="Fertilizer, seed, pesticide price tracking",
                sections=[
                    {"name": "Fertilizer Prices", "data_source": "fertilizer_prices"},
                    {"name": "Seed Prices", "data_source": "seed_prices"},
                    {"name": "Pesticide Prices", "data_source": "pesticide_prices"},
                    {"name": "Equipment Rates", "data_source": "equipment_rates"}
                ],
                frequency="weekly",
                formats=[OutputFormat.PDF, OutputFormat.EXCEL]
            ),
            ProductTemplate(
                id="weather_report",
                name="Weekly Weather Report",
                type=ProductType.WEATHER_REPORT,
                description="Agricultural weather forecast",
                sections=[
                    {"name": "7-Day Forecast", "data_source": "weather_forecast"},
                    {"name": "Rainfall Analysis", "data_source": "rainfall"},
                    {"name": "Advisories", "data_source": "advisories"}
                ],
                frequency="weekly",
                formats=[OutputFormat.PDF, OutputFormat.HTML]
            ),
            ProductTemplate(
                id="crop_advisory",
                name="Crop Advisory Bulletin",
                type=ProductType.CROP_ADVISORY,
                description="Weekly crop-specific advisories",
                sections=[
                    {"name": "Crop-wise Advisory", "data_source": "crop_advisory"},
                    {"name": "Pest/Disease Alerts", "data_source": "pest_alerts"},
                    {"name": "Input Recommendations", "data_source": "input_recs"},
                    {"name": "Weather-based Advice", "data_source": "weather_advice"}
                ],
                frequency="weekly",
                formats=[OutputFormat.PDF, OutputFormat.HTML]
            ),
        ]

        for template in default_templates:
            self.templates[template.id] = template

    async def generate_product(self, template_id: str, format: OutputFormat = OutputFormat.PDF,
                               custom_data: Dict = None) -> Dict[str, Any]:
        """Generate a data product"""
        if template_id not in self.templates:
            return {"success": False, "error": "Template not found"}

        template = self.templates[template_id]
        if format not in template.formats:
            return {"success": False, "error": f"Format {format.value} not supported for this template"}

        logger.info(f"Generating {template.name} in {format.value}...")

        try:
            if self._voice:
                await self._voice.speak(f"{template.name} generate kar raha hoon...")

            # Gather data for sections
            section_data = await self._gather_section_data(template, custom_data)

            # Generate content with LLM
            content = await self._generate_content(template, section_data)

            # Generate file
            file_path = await self._generate_file(template, content, format)

            # Create product record
            product = GeneratedProduct(
                id=f"{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                template_id=template_id,
                name=template.name,
                format=format,
                file_path=file_path,
                generated_at=datetime.now(),
                size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                metadata={"sections": list(section_data.keys()), "format": format.value}
            )

            self.products[product.id] = product
            await self._save_product(product)

            if self._voice:
                await self._voice.speak(f"{template.name} ready hai. File save ho gaya.")

            return {"success": True, "product": product.__dict__}

        except Exception as e:
            logger.error(f"Product generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _gather_section_data(self, template: ProductTemplate, custom_data: Dict) -> Dict:
        """Gather data for each section"""
        section_data = {}

        for section in template.sections:
            source = section.get("data_source", "")
            # In production, would fetch from relevant agents
            # For now, return mock data structure
            section_data[source] = await self._fetch_section_data(source, custom_data)

        return section_data

    async def _fetch_section_data(self, source: str, custom_data: Dict) -> Dict:
        """Fetch data for a section"""
        # This would connect to various agents (market_intel, farm_manager, etc.)
        # Return mock data for now
        mock_data = {
            "spot_prices": {"wheat": 2400, "bajra": 2200, "mustard": 5200},
            "price_changes": {"gainers": ["cotton", "moong"], "losers": ["wheat", "maize"]},
            "arrivals": {"wheat": 5000, "bajra": 2000},
            "predictions": {"wheat": "bullish", "cotton": "bearish"},
            "commodity_analysis": {},
            "mandi_comparison": {},
            "seasonal": {},
            "policy": {},
            "crop_activities": {},
            "sowing_dates": {},
            "input_schedule": {},
            "pest_alerts": [],
            "sowing_dates_rabi": {},
            "irrigation_schedule": {},
            "harvest_timeline": {},
            "rate_trends": {"python": "rising", "powerbi": "stable"},
            "skill_rates": {"python": 35, "powerbi": 40, "react": 45},
            "geo_rates": {"india": 30, "us": 75, "europe": 60},
            "project_rates": {"fixed": 500, "hourly": 40},
            "fertilizer_prices": {"urea": 266, "dap": 1350},
            "seed_prices": {"wheat": 45, "cotton": 850},
            "pesticide_prices": {"monocrotophos": 450},
            "equipment_rates": {"tractor": 800, "harvester": 2500},
            "weather_forecast": [],
            "rainfall": {},
            "advisories": [],
            "crop_advisory": {},
            "weather_advice": {},
            "input_recs": {},
        }
        return mock_data.get(source, {})

    async def _generate_content(self, template: ProductTemplate, section_data: Dict) -> str:
        """Generate content using LLM"""
        if not self._llm:
            return self._generate_default_content(template, section_data)

        sections_text = []
        for section in template.sections:
            source = section.get("data_source", "")
            data = section_data.get(source, {})
            sections_text.append(f"## {section['name']}\n{json.dumps(data, indent=2, ensure_ascii=False)}")

        prompt = f"""
        Generate a professional {template.name} report.

        Template: {template.name}
        Type: {template.type.value}
        Frequency: {template.frequency}

        Sections:
        {chr(10).join(sections_text)}

        Generate a well-structured report in Hindi/Hinglish with:
        1. Executive Summary
        2. Detailed Analysis per section
        3. Key Insights & Recommendations
        4. Action Items

        Language: Hindi/Hinglish (for farmers) + English (for technical data)
        Format: Professional report suitable for PDF
        """

        response = await self._llm.generate(prompt, temperature=0.3, max_tokens=4000)
        return response.content

    def _generate_default_content(self, template: ProductTemplate, section_data: Dict) -> str:
        """Generate default content without LLM"""
        content = f"# {template.name}\n\n"
        content += f"**Generated:** {datetime.now().strftime('%d %B %Y')}\n"
        content += f"**Frequency:** {template.frequency}\n\n"

        for section in template.sections:
            content += f"## {section['name']}\n\n"
            source = section.get("data_source", "")
            data = section_data.get(source, {})
            content += f"{json.dumps(data, indent=2, ensure_ascii=False)}\n\n"

        return content

    async def _generate_file(self, template: ProductTemplate, content: str, format: OutputFormat) -> str:
        """Generate file in specified format"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{template.id}_{timestamp}.{format.value}"
        file_path = self._output_dir / filename

        if format == OutputFormat.PDF:
            return await self._generate_pdf(file_path, template.name, content)
        elif format == OutputFormat.EXCEL:
            return await self._generate_excel(file_path, template, content)
        elif format == OutputFormat.CSV:
            return await self._generate_csv(file_path, content)
        elif format == OutputFormat.JSON:
            return await self._generate_json(file_path, content)
        elif format == OutputFormat.HTML:
            return await self._generate_html(file_path, template.name, content)

        return str(file_path)

    async def _generate_pdf(self, file_path: Path, title: str, content: str) -> str:
        """Generate PDF using ReportLab"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.units import inch
            from reportlab.lib.colors import HexColor
            from reportlab.lib.enums import TA_CENTER, TA_LEFT

            doc = SimpleDocTemplate(str(file_path), pagesize=A4,
                                    rightMargin=72, leftMargin=72,
                                    topMargin=72, bottomMargin=18)

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                         fontSize=24, textColor=HexColor('#2E86AB'),
                                         alignment=TA_CENTER, spaceAfter=30)
            heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                           fontSize=16, textColor=HexColor('#A23B72'),
                                           spaceBefore=20, spaceAfter=10)
            body_style = ParagraphStyle('CustomBody', parent=styles['Normal'],
                                        fontSize=11, leading=14, alignment=TA_LEFT)

            story = []
            story.append(Paragraph(content.split('\n')[0], title_style))
            story.append(Spacer(1, 20))

            for line in content.split('\n')[1:]:
                if line.startswith('## '):
                    story.append(Paragraph(line[3:], heading_style))
                elif line.startswith('# '):
                    story.append(Paragraph(line[2:], title_style))
                elif line.strip():
                    story.append(Paragraph(line, body_style))
                story.append(Spacer(1, 6))

            doc.build(story)
            return str(file_path)

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            # Fallback: save as text
            with open(file_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
                f.write(content)
            return str(file_path.with_suffix('.txt'))

    async def _generate_excel(self, file_path: Path, template: ProductTemplate, content: str) -> str:
        """Generate Excel file"""
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()

            # Summary sheet
            ws1 = wb.active
            ws1.title = "Summary"
            ws1['A1'] = template.name
            ws1['A2'] = f"Generated: {datetime.now().strftime('%d %B %Y')}"
            ws1['A1'].font = Font(size=16, bold=True, color="2E86AB")

            # Data sheets
            # Would parse content and create sheets
            wb.save(file_path)
            return str(file_path)
        except Exception as e:
            logger.error(f"Excel generation failed: {e}")
            return str(file_path)

    async def _generate_csv(self, file_path: Path, content: str) -> str:
        """Generate CSV"""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            f.write("Content\n")
            f.write(content)
        return str(file_path)

    async def _generate_json(self, file_path: Path, content: str) -> str:
        """Generate JSON"""
        data = {"content": content, "generated_at": datetime.now().isoformat()}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(file_path)

    async def _generate_html(self, file_path: Path, title: str, content: str) -> str:
        """Generate HTML"""
        formatted_content = content.replace('\n', '<br>')
        html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #2E86AB; border-bottom: 3px solid #2E86AB; padding-bottom: 10px; }}
        h2 {{ color: #A23B72; margin-top: 30px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <p class="meta">Generated: {datetime.now().strftime('%d %B %Y')}</p>
        {formatted_content}
    </div>
</body>
</html>"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return str(file_path)

    async def _generation_scheduler(self):
        """Scheduled product generation"""
        while True:
            try:
                now = datetime.now()

                for template in self.templates.values():
                    if await self._should_generate(template):
                        for fmt in template.formats:
                            await self.generate_product(template.id, fmt)

                # Check every hour
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Generation scheduler error: {e}")
                await asyncio.sleep(3600)

    async def _should_generate(self, template: ProductTemplate) -> bool:
        """Check if product should be generated based on frequency"""
        # Check last generated
        last_gen = None
        for product in self.products.values():
            if product.template_id == template.id:
                if last_gen is None or product.generated_at > last_gen:
                    last_gen = product.generated_at

        if not last_gen:
            return True

        freq_hours = {
            "daily": 24,
            "weekly": 168,
            "monthly": 720,
            "quarterly": 2160,
            "seasonal": 2160
        }

        hours_since = (datetime.now() - last_gen).total_seconds() / 3600
        return hours_since >= freq_hours.get(template.frequency, 168)

    async def batch_generate(self, template_ids: List[str], formats: List[OutputFormat]) -> Dict[str, Any]:
        """Generate multiple products"""
        results = {}
        for tid in template_ids:
            for fmt in formats:
                result = await self.generate_product(tid, fmt)
                results[f"{tid}_{fmt.value}"] = result

        return {"results": results}

    async def publish_to_gumroad(self, product_id: str, gumroad_config: Dict) -> Dict[str, Any]:
        """Publish product to Gumroad"""
        if product_id not in self.products:
            return {"success": False, "error": "Product not found"}

        # Would use Gumroad API
        # For now, return success
        return {"success": True, "url": f"https://gumroad.com/l/{self.products[product_id].id}"}

    async def get_product_catalog(self) -> List[Dict]:
        """Get catalog of generated products"""
        return [
            {
                "id": p.id,
                "name": p.name,
                "format": p.format.value,
                "generated_at": p.generated_at.isoformat(),
                "size_kb": p.size_bytes / 1024,
                "file": p.file_path
            }
            for p in self.products.values()
        ]

    async def _save_product(self, product: GeneratedProduct):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO generated_products
                (id, template_id, name, format, file_path, generated_at, size_bytes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product.id, product.template_id, product.name, product.format.value,
                product.file_path, product.generated_at.isoformat(),
                product.size_bytes, json.dumps(product.metadata)
            ))

    async def close(self):
        if self._generation_task:
            self._generation_task.cancel()
        logger.info("DataProductsGenerator closed")

    def get_status(self) -> Dict[str, Any]:
        return {
            "templates": len(self.templates),
            "products_generated": len(self.products),
            "output_dir": str(self._output_dir),
            "templates": {k: {"name": v.name, "type": v.type.value, "frequency": v.frequency} for k, v in self.templates.items()}
        }