"""
Market Intelligence Dashboard Module for Wife God Agent
NCDEX/MCX futures tracking, weather derivatives, price prediction, hedging advisor
"""

import asyncio
import logging
import json
import aiohttp
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

logger = logging.getLogger("WifeGod.MarketIntelligence")


class CommodityType(Enum):
    WHEAT = "wheat"
    RICE = "rice"
    MAIZE = "maize"
    BAJRA = "bajra"
    JOWAR = "jowar"
    MOONG = "moong"
    URAD = "urad"
    GROUNDNUT = "groundnut"
    SOYBEAN = "soybean"
    MUSTARD = "mustard"
    COTTON = "cotton"
    CHANA = "chana"
    TURMERIC = "turmeric"
    CORIANDER = "coriander"
    CUMIN = "cumin"


class Exchange(Enum):
    NCDEX = "ncdex"
    MCX = "mcx"
    ICE = "ice"
    CME = "cme"


class TrendDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"


@dataclass
class FuturesContract:
    symbol: str
    commodity: CommodityType
    exchange: Exchange
    expiry: datetime
    lot_size: int
    tick_size: float
    current_price: float = 0
    change: float = 0
    change_percent: float = 0
    open_interest: int = 0
    volume: int = 0
    high: float = 0
    low: float = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SpotPrice:
    commodity: CommodityType
    mandi: str
    state: str
    price: float
    unit: str
    date: datetime
    arrival_tonnes: float = 0


@dataclass
class PricePrediction:
    commodity: CommodityType
    prediction_date: datetime
    target_date: datetime
    predicted_price: float
    confidence: float
    trend: TrendDirection
    support_levels: List[float]
    resistance_levels: List[float]
    reasoning: str


@dataclass
class HedgingRecommendation:
    commodity: CommodityType
    position: str  # "long_hedge", "short_hedge"
    futures_contract: str
    hedge_ratio: float
    contracts_needed: int
    estimated_cost: float
    risk_reduction: float
    reasoning: str


@dataclass
class WeatherDerivative:
    commodity: CommodityType
    region: str
    parameter: str  # rainfall, temperature, humidity
    trigger_value: float
    payout_per_unit: float
    premium: float
    expiry: datetime


class MarketIntelligence:
    """
    Market Intelligence Dashboard
    - NCDEX/MCX futures tracking
    - Mandi spot prices
    - Price prediction with ML
    - Hedging advisory
    - Weather derivatives
    - Seasonal analysis
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.futures_data: Dict[str, FuturesContract] = {}
        self.spot_prices: Dict[str, List[SpotPrice]] = {}
        self.predictions: Dict[str, PricePrediction] = {}
        self.hedging_advice: Dict[str, HedgingRecommendation] = {}
        self.weather_derivatives: List[WeatherDerivative] = []
        self._db = None
        self._llm = None
        self._voice = None
        self._fetch_task = None

    def set_dependencies(self, db, llm, voice):
        self._db = db
        self._llm = llm
        self._voice = voice

    async def initialize(self):
        """Initialize market intelligence"""
        logger.info("Initializing MarketIntelligence...")

        # Load cached data
        await self._load_cached_data()

        # Start price fetcher
        self._fetch_task = asyncio.create_task(self._price_fetch_loop())

        logger.info("MarketIntelligence initialized")

    async def _price_fetch_loop(self):
        """Background price fetching"""
        while True:
            try:
                await self._fetch_futures_prices()
                await self._fetch_spot_prices()
                await self._generate_predictions()
                await asyncio.sleep(300)  # Every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Price fetch error: {e}")
                await asyncio.sleep(60)

    async def _fetch_futures_prices(self):
        """Fetch futures prices from NCDEX/MCX"""
        # In production, would connect to exchange APIs
        # For now, simulate with mock data
        commodities = [
            (CommodityType.WHEAT, "NCDEX", "WHEAT24MAR"),
            (CommodityType.MUSTARD, "NCDEX", "MUSTARD24MAR"),
            (CommodityType.SOYBEAN, "NCDEX", "SOYBEAN24MAR"),
            (CommodityType.COTTON, "MCX", "COTTON24MAR"),
            (CommodityType.CHANA, "NCDEX", "CHANA24MAR"),
        ]

        for commodity, exchange, symbol in commodities:
            # Mock price data
            import random
            base_price = self._get_base_price(commodity)
            price = base_price + random.uniform(-50, 50)

            contract = FuturesContract(
                symbol=symbol,
                commodity=commodity,
                exchange=Exchange(exchange),
                expiry=datetime.now() + timedelta(days=30),
                lot_size=self._get_lot_size(commodity),
                tick_size=self._get_tick_size(commodity),
                current_price=price,
                change=random.uniform(-20, 20),
                change_percent=random.uniform(-1, 1),
                open_interest=random.randint(10000, 100000),
                volume=random.randint(5000, 50000),
                high=price + random.uniform(0, 30),
                low=price - random.uniform(0, 30)
            )

            self.futures_data[symbol] = contract
            await self._save_futures_price(contract)

    async def _fetch_spot_prices(self):
        """Fetch mandi spot prices"""
        # Would connect to AgMarkNet API
        mandis = [
            ("Bikaner", "Rajasthan", CommodityType.WHEAT),
            ("Nokha", "Rajasthan", CommodityType.BAJRA),
            ("Sri Ganganagar", "Rajasthan", CommodityType.COTTON),
            ("Jodhpur", "Rajasthan", CommodityType.MUSTARD),
            ("Indore", "Madhya Pradesh", CommodityType.SOYBEAN),
        ]

        for mandi, state, commodity in mandis:
            base = self._get_base_price(commodity)
            price = base + random.uniform(-100, 100)

            spot = SpotPrice(
                commodity=commodity,
                mandi=mandi,
                state=state,
                price=price,
                unit="quintal",
                date=datetime.now(),
                arrival_tonnes=random.uniform(100, 5000)
            )

            key = f"{commodity.value}_{mandi}"
            if key not in self.spot_prices:
                self.spot_prices[key] = []
            self.spot_prices[key].append(spot)
            await self._save_spot_price(spot)

    def _get_base_price(self, commodity: CommodityType) -> float:
        """Get base price for commodity"""
        base_prices = {
            CommodityType.WHEAT: 2400,
            CommodityType.RICE: 3200,
            CommodityType.MAIZE: 1800,
            CommodityType.BAJRA: 2200,
            CommodityType.JOWAR: 2500,
            CommodityType.MOONG: 7500,
            CommodityType.URAD: 8000,
            CommodityType.GROUNDNUT: 5500,
            CommodityType.SOYBEAN: 4800,
            CommodityType.MUSTARD: 5200,
            CommodityType.COTTON: 6000,
            CommodityType.CHANA: 7000,
            CommodityType.TURMERIC: 9000,
            CommodityType.CORIANDER: 6500,
            CommodityType.CUMIN: 15000,
        }
        return base_prices.get(commodity, 3000)

    def _get_lot_size(self, commodity: CommodityType) -> int:
        lot_sizes = {
            CommodityType.WHEAT: 10,
            CommodityType.RICE: 10,
            CommodityType.MAIZE: 10,
            CommodityType.BAJRA: 10,
            CommodityType.COTTON: 25,
            CommodityType.MUSTARD: 10,
            CommodityType.SOYBEAN: 10,
            CommodityType.CHANA: 10,
        }
        return lot_sizes.get(commodity, 10)

    def _get_tick_size(self, commodity: CommodityType) -> float:
        return 0.10  # 10 paise for most agri commodities

    async def _generate_predictions(self):
        """Generate price predictions using ML/LLM"""
        if not self._llm:
            return

        for symbol, contract in self.futures_data.items():
            try:
                prediction = await self._predict_price(contract)
                if prediction:
                    self.predictions[contract.commodity.value] = prediction
                    await self._save_prediction(prediction)
            except Exception as e:
                logger.error(f"Prediction failed for {contract.symbol}: {e}")

    async def _predict_price(self, contract: FuturesContract) -> Optional[PricePrediction]:
        """Predict price using LLM"""
        if not self._llm:
            return None

        # Get historical data
        history = await self._get_price_history(contract.commodity)

        prompt = f"""
        Predict price for {contract.commodity.value} futures ({contract.symbol})
        Current price: ₹{contract.current_price}
        Change: {contract.change_percent:.2f}%
        OI: {contract.open_interest}, Volume: {contract.volume}

        Recent history: {history[-10:] if history else 'No data'}

        Predict price for 1 week, 2 weeks, 1 month.
        Return JSON: {{
            "predicted_price_1w": float,
            "predicted_price_2w": float,
            "predicted_price_1m": float,
            "confidence": 0-1,
            "trend": "bullish/bearish/sideways/volatile",
            "support": [float],
            "resistance": [float],
            "reasoning": "string"
        }}
        """

        response = await self._llm.generate(prompt, temperature=0.2)
        try:
            data = json.loads(response.content)
            return PricePrediction(
                commodity=contract.commodity,
                prediction_date=datetime.now(),
                target_date=datetime.now() + timedelta(days=30),
                predicted_price=data.get("predicted_price_1m", contract.current_price),
                confidence=data.get("confidence", 0.5),
                trend=TrendDirection(data.get("trend", "sideways")),
                support_levels=data.get("support", []),
                resistance_levels=data.get("resistance", []),
                reasoning=data.get("reasoning", "")
            )
        except:
            return None

    async def get_hedging_advice(self, commodity: CommodityType, position: str,
                                 quantity: float, risk_appetite: str = "moderate") -> HedgingRecommendation:
        """Get hedging recommendation"""
        if not self._llm:
            return None

        contract = self.futures_data.get(f"{commodity.value.upper()}24MAR")
        if not contract:
            return None

        prompt = f"""
        Hedging advice for {commodity.value}:
        Current position: {position} {quantity} quintals
        Current spot: ~₹{self._get_base_price(commodity)}
        Futures: ₹{contract.current_price}
        Risk appetite: {risk_appetite}

        Recommend hedge strategy:
        Return JSON: {{
            "position": "long_hedge|short_hedge",
            "hedge_ratio": 0-1,
            "contracts_needed": int,
            "estimated_cost": float,
            "risk_reduction": 0-100,
            "reasoning": "string"
        }}
        """

        response = await self._llm.generate(prompt, temperature=0.2)
        try:
            data = json.loads(response.content)
            return HedgingRecommendation(
                commodity=commodity,
                position=data.get("position", "short_hedge"),
                futures_contract=f"{commodity.value.upper()}24MAR",
                hedge_ratio=data.get("hedge_ratio", 0.8),
                contracts_needed=data.get("contracts_needed", 1),
                estimated_cost=data.get("estimated_cost", 0),
                risk_reduction=data.get("risk_reduction", 50),
                reasoning=data.get("reasoning", "")
            )
        except:
            return None

    async def get_market_summary(self) -> Dict[str, Any]:
        """Get market summary"""
        return {
            "futures": {
                k: {
                    "symbol": v.symbol,
                    "price": v.current_price,
                    "change": v.change,
                    "change_pct": v.change_percent,
                    "oi": v.open_interest,
                    "volume": v.volume
                } for k, v in self.futures_data.items()
            },
            "spot_prices": {
                k: [{"mandi": s.mandi, "price": s.price, "arrival": s.arrival_tonnes} for s in v[-5:]]
                for k, v in self.spot_prices.items()
            },
            "predictions": {
                k: {
                    "predicted": v.predicted_price,
                    "confidence": v.confidence,
                    "trend": v.trend.value
                } for k, v in self.predictions.items()
            }
        }

    # Persistence
    async def _save_futures_price(self, contract: FuturesContract):
        if self._db:
            await self._db.execute("""
                INSERT INTO futures_prices
                (symbol, commodity, exchange, expiry, lot_size, tick_size, current_price,
                 change, change_percent, open_interest, volume, high, low, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contract.symbol, contract.commodity.value, contract.exchange.value,
                contract.expiry.isoformat(), contract.lot_size, contract.tick_size,
                contract.current_price, contract.change, contract.change_percent,
                contract.open_interest, contract.volume, contract.high, contract.low,
                contract.timestamp.isoformat()
            ))

    async def _save_spot_price(self, spot: SpotPrice):
        if self._db:
            await self._db.execute("""
                INSERT INTO spot_prices
                (commodity, mandi, state, price, unit, date, arrival_tonnes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                spot.commodity.value, spot.mandi, spot.state, spot.price,
                spot.unit, spot.date.isoformat(), spot.arrival_tonnes
            ))

    async def _save_prediction(self, pred: PricePrediction):
        if self._db:
            await self._db.execute("""
                INSERT INTO price_predictions
                (commodity, prediction_date, target_date, predicted_price, confidence,
                 trend, support_levels, resistance_levels, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pred.commodity.value, pred.prediction_date.isoformat(),
                pred.target_date.isoformat(), pred.predicted_price, pred.confidence,
                pred.trend.value, json.dumps(pred.support_levels),
                json.dumps(pred.resistance_levels), pred.reasoning
            ))

    async def _load_cached_data(self):
        if not self._db:
            return
        # Load recent futures, spots, predictions
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "futures_tracked": len(self.futures_data),
            "spot_markets": len(self.spot_prices),
            "predictions": len(self.predictions),
            "last_update": datetime.now().isoformat()
        }