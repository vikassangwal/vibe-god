"""
eNAM/IndiaMART/TradeIndia Price Integration Module
Aggregates prices from eNAM, IndiaMART, TradeIndia for procurement/selling decisions
"""

import asyncio
import logging
import json
import aiohttp
import re
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

logger = logging.getLogger("WifeGod.eNAMIntegration")


class SourceType(Enum):
    ENAM = "enam"
    INDIAMART = "indiamart"
    TRADEINDIA = "tradeindia"
    AGMARKNET = "agmarknet"
    FARMERTAK = "farmertak"
    NCDEX = "ncdex"
    MCX = "mcx"


class PriceType(Enum):
    SPOT = "spot"
    FUTURES = "futures"
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    MSP = "msp"
    PROCUREMENT = "procurement"


@dataclass
class PriceQuote:
    source: SourceType
    commodity: str
    variety: str
    price: float
    unit: str
    location: str
    state: str
    timestamp: datetime
    quality_grade: str = ""
    min_price: float = 0
    max_price: float = 0
    modal_price: float = 0
    arrival_tonnes: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupplierQuote:
    source: SourceType
    supplier_name: str
    contact: str
    commodity: str
    variety: str
    price: float
    unit: str
    min_order_qty: float
    unit_of_measure: str
    location: str
    rating: float = 0
    response_time: str = ""
    verified: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PriceAlert:
    id: str
    commodity: str
    target_price: float
    condition: str  # "above", "below", "crosses"
    source: SourceType
    location: str = ""
    enabled: bool = True
    triggered: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class eNAMIntegration:
    """
    eNAM/IndiaMART/TradeIndia Price Aggregator
    - eNAM live mandi prices
    - IndiaMART supplier quotes
    - TradeIndia bulk pricing
    - AgMarkNet official prices
    - Price comparison and alerts
    - Procurement optimization
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.price_cache: Dict[str, List[PriceQuote]] = {}
        self.supplier_cache: Dict[str, List[SupplierQuote]] = {}
        self.alerts: Dict[str, PriceAlert] = {}
        self._db = None
        self._llm = None
        self._voice = None
        self._fetch_task = None
        self._session = None

        # API configurations
        self.api_configs = {
            SourceType.ENAM: {
                "base_url": "https://enam.gov.in/api",
                "api_key": self.config.get("enam_api_key", ""),
                "enabled": True
            },
            SourceType.AGMARKNET: {
                "base_url": "https://agmarknet.gov.in/api",
                "api_key": self.config.get("agmarknet_api_key", ""),
                "enabled": True
            },
            SourceType.INDIAMART: {
                "base_url": "https://api.indiamart.com",
                "api_key": self.config.get("indiamart_api_key", ""),
                "enabled": True
            },
            SourceType.TRADEINDIA: {
                "base_url": "https://api.tradeindia.com",
                "api_key": self.config.get("tradeindia_api_key", ""),
                "enabled": True
            },
            SourceType.FARMERTAK: {
                "base_url": "https://api.farmertak.com",
                "api_key": self.config.get("farmertak_api_key", ""),
                "enabled": True
            }
        }

    def set_dependencies(self, db, llm, voice):
        self._db = db
        self._llm = llm
        self._voice = voice

    async def initialize(self):
        """Initialize eNAM integration"""
        logger.info("Initializing eNAM Integration...")

        self._session = aiohttp.ClientSession()
        await self._load_cached_data()

        self._fetch_task = asyncio.create_task(self._fetch_loop())
        logger.info("eNAM Integration initialized")

    async def _fetch_loop(self):
        """Background price fetching loop"""
        while True:
            try:
                await self._fetch_all_prices()
                await self._check_alerts()
                await asyncio.sleep(300)  # Every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Fetch loop error: {e}")
                await asyncio.sleep(60)

    async def _fetch_all_prices(self):
        """Fetch prices from all sources"""
        tasks = []

        for source, config in self.api_configs.items():
            if config.get("enabled", False):
                tasks.append(self._fetch_source_prices(source))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_source_prices(self, source: SourceType):
        """Fetch prices from a specific source"""
        try:
            if source == SourceType.ENAM:
                await self._fetch_enam()
            elif source == SourceType.AGMARKNET:
                await self._fetch_agmarknet()
            elif source == SourceType.INDIAMART:
                await self._fetch_indiamart()
            elif source == SourceType.TRADEINDIA:
                await self._fetch_tradeindia()
            elif source == SourceType.FARMERTAK:
                await self._fetch_farmertak()
        except Exception as e:
            logger.error(f"Fetch failed for {source.value}: {e}")

    async def _fetch_enam(self):
        """Fetch from eNAM"""
        config = self.api_configs[SourceType.ENAM]
        if not config.get("api_key"):
            logger.warning("eNAM API key not configured")
            return

        # eNAM API endpoints
        endpoints = [
            "/api/mandi/prices",
            "/api/commodity/prices",
            "/api/arrival/data"
        ]

        for endpoint in endpoints:
            try:
                async with self._session.get(
                    f"{config['base_url']}{endpoint}",
                    headers={"Authorization": f"Bearer {config['api_key']}"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await self._parse_enam_data(data)
            except Exception as e:
                logger.warning(f"eNAM endpoint {endpoint} failed: {e}")

    async def _parse_enam_data(self, data: Dict):
        """Parse eNAM response"""
        records = data.get("records", data.get("data", []))
        for record in records:
            quote = PriceQuote(
                source=SourceType.ENAM,
                commodity=record.get("commodity", ""),
                variety=record.get("variety", ""),
                price=float(record.get("modal_price", record.get("price", 0))),
                unit=record.get("unit", "quintal"),
                location=record.get("market", record.get("mandi", "")),
                state=record.get("state", ""),
                timestamp=datetime.now(),
                quality_grade=record.get("grade", ""),
                min_price=float(record.get("min_price", 0)),
                max_price=float(record.get("max_price", 0)),
                modal_price=float(record.get("modal_price", 0)),
                arrival_tonnes=float(record.get("arrival", 0)),
                metadata=record
            )
            await self._cache_price_quote(quote)

    async def _fetch_agmarknet(self):
        """Fetch from AgMarkNet"""
        config = self.api_configs[SourceType.AGMARKNET]
        if not config.get("api_key"):
            # Try web scraping if no API
            await self._scrape_agmarknet()

    async def _scrape_agmarknet(self):
        """Scrape AgMarkNet website"""
        try:
            url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
            params = {
                "Tx_Commodity": "0",
                "Tx_State": "0",
                "Tx_District": "0",
                "Tx_Market": "0",
                "DateFrom": datetime.now().strftime("%d-%b-%Y"),
                "DateTo": datetime.now().strftime("%d-%b-%Y"),
                "Fr_Date": datetime.now().strftime("%d-%b-%Y"),
                "To_Date": datetime.now().strftime("%d-%b-%Y"),
                "Tx_Trend": "0",
                "Tx_CommodityHead": "All",
                "Tx_StateHead": "All",
                "Tx_DistrictHead": "All",
                "Tx_MarketHead": "All"
            }

            async with self._session.get(url, params=params) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    await self._parse_agmarknet_html(html)
        except Exception as e:
            logger.warning(f"AgMarkNet scrape failed: {e}")

    async def _parse_agmarknet_html(self, html: str):
        """Parse AgMarkNet HTML table"""
        # Would use BeautifulSoup to parse table
        # For now, skip implementation
        pass

    async def _fetch_indiamart(self):
        """Fetch from IndiaMART"""
        config = self.api_configs[SourceType.INDIAMART]
        if not config.get("api_key"):
            return

        # IndiaMART buy leads / sell leads API
        url = f"{config['base_url']}/ws/v2/buy-leads"
        params = {"key": config['api_key'], "category": "agriculture"}

        try:
            async with self._session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await self._parse_indiamart_data(data)
        except Exception as e:
            logger.warning(f"IndiaMART fetch failed: {e}")

    async def _parse_indiamart_data(self, data: Dict):
        """Parse IndiaMART response"""
        leads = data.get("LEADS", data.get("leads", []))
        for lead in leads:
            quote = SupplierQuote(
                source=SourceType.INDIAMART,
                supplier_name=lead.get("COMPANY_NAME", lead.get("company", "")),
                contact=lead.get("CONTACT_PERSON", lead.get("contact", "")),
                commodity=lead.get("PRODUCT", lead.get("product", "")),
                variety=lead.get("VARIETY", ""),
                price=float(lead.get("PRICE", lead.get("price", 0))),
                unit=lead.get("UNIT", "kg"),
                min_order_qty=float(lead.get("MIN_ORDER", 1)),
                unit_of_measure=lead.get("UOM", "kg"),
                location=lead.get("CITY", "") + ", " + lead.get("STATE", ""),
                rating=float(lead.get("RATING", 0)),
                response_time=lead.get("RESPONSE_TIME", ""),
                verified=lead.get("VERIFIED", False),
                timestamp=datetime.now()
            )
            await self._cache_supplier_quote(quote)

    async def _fetch_tradeindia(self):
        """Fetch from TradeIndia"""
        config = self.api_configs[SourceType.TRADEINDIA]
        if not config.get("api_key"):
            return

        # TradeIndia API
        pass

    async def _fetch_farmertak(self):
        """Fetch from FarmerTak"""
        config = self.api_configs[SourceType.FARMERTAK]
        if not config.get("api_key"):
            return

        # FarmerTak API
        pass

    async def get_price_comparison(self, commodity: str, location: str = "",
                                   state: str = "") -> Dict[str, Any]:
        """Get price comparison across sources"""
        all_quotes = []

        for source, quotes in self.price_cache.items():
            for quote in quotes:
                if quote.commodity.lower() == commodity.lower():
                    if not location or quote.location.lower() == location.lower():
                        if not state or quote.state.lower() == state.lower():
                            all_quotes.append(quote)

        if not all_quotes:
            return {"error": "No prices found"}

        # Group by source
        by_source = {}
        for quote in all_quotes:
            if quote.source not in by_source:
                by_source[quote.source] = []
            by_source[quote.source].append({
                "price": quote.price,
                "unit": quote.unit,
                "location": quote.location,
                "variety": quote.variety,
                "grade": quote.quality_grade,
                "timestamp": quote.timestamp.isoformat()
            })

        # Find best prices
        all_prices = [q.price for q in all_quotes]
        min_price = min(all_prices) if all_prices else 0
        max_price = max(all_prices) if all_prices else 0
        avg_price = sum(all_prices) / len(all_prices) if all_prices else 0

        return {
            "commodity": commodity,
            "location": location,
            "state": state,
            "by_source": by_source,
            "min_price": min_price,
            "max_price": max_price,
            "avg_price": avg_price,
            "spread": max_price - min_price,
            "timestamp": datetime.now().isoformat()
        }

    async def get_supplier_quotes(self, commodity: str, min_qty: float = 0,
                                  location: str = "") -> List[Dict]:
        """Get supplier quotes from IndiaMART/TradeIndia"""
        quotes = []

        for source, quotes_list in self.supplier_cache.items():
            for quote in quotes_list:
                if quote.commodity.lower() == commodity.lower():
                    if min_qty == 0 or quote.min_order_qty >= min_qty:
                        if not location or location.lower() in quote.location.lower():
                            quotes.append({
                                "source": quote.source.value,
                                "supplier": quote.supplier_name,
                                "contact": quote.contact,
                                "price": quote.price,
                                "unit": quote.unit,
                                "min_order": quote.min_order_qty,
                                "uom": quote.unit_of_measure,
                                "location": quote.location,
                                "rating": quote.rating,
                                "response_time": quote.response_time,
                                "verified": quote.verified
                            })

        # Sort by price
        quotes.sort(key=lambda x: x["price"])
        return quotes

    async def set_price_alert(self, alert: PriceAlert) -> Dict[str, Any]:
        """Set price alert"""
        self.alerts[alert.id] = alert
        await self._save_alert(alert)
        return {"success": True, "alert_id": alert.id}

    async def _check_alerts(self):
        """Check price alerts"""
        for alert_id, alert in list(self.alerts.items()):
            if not alert.enabled or alert.triggered:
                continue

            # Get current price
            comparison = await self.get_price_comparison(
                alert.commodity, alert.location, ""
            )

            if "error" not in comparison:
                prices = []
                for source_data in comparison["by_source"].values():
                    for q in source_data:
                        prices.append(q["price"])

                if prices:
                    current_min = min(prices)
                    current_max = max(prices)

                    triggered = False
                    if alert.condition == "below" and current_min <= alert.target_price:
                        triggered = True
                    elif alert.condition == "above" and current_max >= alert.target_price:
                        triggered = True
                    elif alert.condition == "crosses":
                        # Would need previous price
                        pass

                    if triggered:
                        alert.triggered = True
                        await self._save_alert(alert)

                        if self._voice:
                            await self._voice.speak(
                                f"Price alert! {alert.commodity} {alert.condition} "
                                f"₹{alert.target_price}. Current: ₹{current_min}-{current_max}"
                            )

    async def get_best_procurement_option(self, commodity: str, quantity: float,
                                          location: str = "") -> Dict[str, Any]:
        """Get best procurement option"""
        # Get supplier quotes
        suppliers = await self.get_supplier_quotes(commodity, quantity)

        # Get mandi prices
        mandi_comparison = await self.get_price_comparison(commodity)

        # Calculate best option
        best_option = None

        # Compare direct from mandi vs suppliers
        mandi_price = mandi_comparison.get("min_price", 0) if "error" not in mandi_comparison else 0
        supplier_price = suppliers[0]["price"] if suppliers else 0

        if mandi_price > 0 and (supplier_price == 0 or mandi_price < supplier_price):
            best_option = {
                "source": "mandi",
                "price": mandi_price,
                "details": mandi_comparison
            }
        elif supplier_price > 0:
            best_option = {
                "source": "supplier",
                "price": supplier_price,
                "supplier": suppliers[0]
            }

        return {
            "best_option": best_option,
            "mandi_comparison": mandi_comparison,
            "suppliers": suppliers[:5],
            "recommendation": self._generate_procurement_recommendation(
                commodity, quantity, best_option, mandi_comparison, suppliers
            )
        }

    def _generate_procurement_recommendation(self, commodity: str, quantity: float,
                                             best_option: Dict, mandi: Dict, suppliers: List) -> str:
        """Generate procurement recommendation"""
        if not best_option:
            return "कोई विकल्प उपलब्ध नहीं"

        if best_option["source"] == "mandi":
            return f"मंडी से खरीदना सस्ता है। न्यूनतम मूल्य: ₹{best_option['price']}/क्विंटल"
        else:
            return f"सप्लायर से खरीदें: {best_option['supplier']['supplier']} @ ₹{best_option['price']}/{best_option['supplier']['unit']}"

    async def search_products(self, query: str, source: SourceType = None) -> List[Dict]:
        """Search products across sources"""
        results = []
        query_lower = query.lower()

        for source_type, quotes in self.price_cache.items():
            if source and source_type != source:
                continue
            for quote in quotes:
                if query_lower in quote.commodity.lower() or query_lower in quote.variety.lower():
                    results.append({
                        "source": quote.source.value,
                        "commodity": quote.commodity,
                        "variety": quote.variety,
                        "price": quote.price,
                        "unit": quote.unit,
                        "location": quote.location,
                        "state": quote.state
                    })

        # Search suppliers
        for source_type, quotes in self.supplier_cache.items():
            if source and source_type != source:
                continue
            for quote in quotes:
                if query_lower in quote.commodity.lower() or query_lower in quote.variety.lower():
                    results.append({
                        "source": quote.source.value,
                        "type": "supplier",
                        "supplier": quote.supplier_name,
                        "commodity": quote.commodity,
                        "price": quote.price,
                        "min_order": quote.min_order_qty,
                        "contact": quote.contact
                    })

        return results

    # Caching
    async def _cache_price_quote(self, quote: PriceQuote):
        key = f"{quote.source.value}_{quote.commodity}_{quote.location}"
        if key not in self.price_cache:
            self.price_cache[key] = []
        self.price_cache[key].append(quote)

        # Keep last 100
        if len(self.price_cache[key]) > 100:
            self.price_cache[key] = self.price_cache[key][-100:]

        await self._save_price_quote(quote)

    async def _cache_supplier_quote(self, quote: SupplierQuote):
        key = f"{quote.source.value}_{quote.commodity}"
        if key not in self.supplier_cache:
            self.supplier_cache[key] = []
        self.supplier_cache[key].append(quote)

        if len(self.supplier_cache[key]) > 50:
            self.supplier_cache[key] = self.supplier_cache[key][-50:]

        await self._save_supplier_quote(quote)

    # Persistence
    async def _save_price_quote(self, quote: PriceQuote):
        if self._db:
            await self._db.execute("""
                INSERT INTO price_quotes
                (source, commodity, variety, price, unit, location, state, timestamp,
                 quality_grade, min_price, max_price, modal_price, arrival_tonnes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quote.source.value, quote.commodity, quote.variety, quote.price,
                quote.unit, quote.location, quote.state, quote.timestamp.isoformat(),
                quote.quality_grade, quote.min_price, quote.max_price,
                quote.modal_price, quote.arrival_tonnes, json.dumps(quote.metadata)
            ))

    async def _save_supplier_quote(self, quote: SupplierQuote):
        if self._db:
            await self._db.execute("""
                INSERT INTO supplier_quotes
                (source, supplier_name, contact, commodity, variety, price, unit,
                 min_order_qty, unit_of_measure, location, rating, response_time, verified, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quote.source.value, quote.supplier_name, quote.contact,
                quote.commodity, quote.variety, quote.price, quote.unit,
                quote.min_order_qty, quote.unit_of_measure, quote.location,
                quote.rating, quote.response_time, quote.verified,
                quote.timestamp.isoformat()
            ))

    async def _save_alert(self, alert: PriceAlert):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO price_alerts
                (id, commodity, target_price, condition, source, location, enabled, triggered, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id, alert.commodity, alert.target_price, alert.condition,
                alert.source.value, alert.location, alert.enabled, alert.triggered,
                alert.created_at.isoformat()
            ))

    async def _load_cached_data(self):
        if not self._db:
            return
        # Load recent prices and alerts
        pass

    async def close(self):
        if self._fetch_task:
            self._fetch_task.cancel()
        if self._session:
            await self._session.close()
        logger.info("eNAM Integration closed")

    def get_status(self) -> Dict[str, Any]:
        return {
            "cached_sources": len(self.price_cache),
            "total_price_quotes": sum(len(q) for q in self.price_cache.values()),
            "supplier_quotes": len(self.supplier_cache),
            "active_alerts": len([a for a in self.alerts.values() if a.enabled]),
            "sources_enabled": [s.value for s, c in self.api_configs.items() if c.get("enabled")]
        }