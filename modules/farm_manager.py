"""
Multi-Farm Manager Module for Wife God Agent
GPS Boundaries, Crop Rotation, Field Management, Labor Tracking
"""

import asyncio
import logging
import json
import math
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

logger = logging.getLogger("WifeGod.FarmManager")


class CropType(Enum):
    WHEAT = "wheat"
    RICE = "rice"
    MAIZE = "maize"
    BAJRA = "bajra"
    JOWAR = "jowar"
    MOONG = "moong"
    URAD = "urad"
    GROUNDNUT = "groundnut"
    MUSTARD = "mustard"
    COTTON = "cotton"
    SUGARCANE = "sugarcane"
    VEGETABLES = "vegetables"
    FODDER = "fodder"
    FALLOW = "fallow"


class SoilType(Enum):
    SANDY = "sandy"
    LOAMY = "loamy"
    CLAYEY = "clayey"
    SILTY = "silty"
    BLACK_COTTON = "black_cotton"
    RED = "red"
    LATERITE = "laterite"


class IrrigationType(Enum):
    RAINFED = "rainfed"
    CANAL = "canal"
    TUBEWELL = "tubewell"
    DRIP = "drip"
    SPRINKLER = "sprinkler"
    FLOOD = "flood"


@dataclass
class GPSPoint:
    latitude: float
    longitude: float
    altitude: float = 0.0


@dataclass
class FieldBoundary:
    id: str
    name: str
    coordinates: List[GPSPoint]
    area_hectares: float
    soil_type: SoilType
    irrigation_type: IrrigationType
    water_source: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CropPlan:
    field_id: str
    crop: CropType
    variety: str
    sowing_date: datetime
    expected_harvest: datetime
    seed_rate_kg_per_ha: float
    fertilizer_schedule: List[Dict] = field(default_factory=list)
    pesticide_schedule: List[Dict] = field(default_factory=list)
    irrigation_schedule: List[Dict] = field(default_factory=list)
    expected_yield_kg_per_ha: float = 0
    status: str = "planned"


@dataclass
class LaborRecord:
    id: str
    field_id: str
    date: datetime
    activity: str
    workers: int
    hours: float
    rate_per_hour: float
    total_cost: float
    description: str = ""


@dataclass
class InputRecord:
    id: str
    field_id: str
    date: datetime
    input_type: str
    name: str
    quantity: float
    unit: str
    cost_per_unit: float
    total_cost: float
    supplier: str = ""


@dataclass
class HarvestRecord:
    id: str
    field_id: str
    crop: CropType
    date: datetime
    area_harvested_ha: float
    yield_kg: float
    quality_grade: str = ""
    moisture_percent: float = 0
    storage_location: str = ""
    sold_qty_kg: float = 0
    sale_price_per_kg: float = 0


class FarmManager:
    """
    Multi-farm management system
    - GPS field boundaries
    - Crop rotation planning
    - Labor & input tracking
    - Harvest recording
    - Financial tracking per field
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.fields: Dict[str, FieldBoundary] = {}
        self.crop_plans: Dict[str, List[CropPlan]] = {}
        self.labor_records: Dict[str, List[LaborRecord]] = {}
        self.input_records: Dict[str, List[InputRecord]] = {}
        self.harvest_records: Dict[str, List[HarvestRecord]] = {}
        self._db: Optional['DatabaseManager'] = None
        self._llm: Optional['LocalLLM'] = None
        self._voice: Optional['VoiceCommunicator'] = None

    def set_dependencies(self, db: 'DatabaseManager', llm: 'LocalLLM', voice: 'VoiceCommunicator'):
        self._db = db
        self._llm = llm
        self._voice = voice

    async def initialize(self):
        """Initialize farm manager"""
        logger.info("Initializing FarmManager...")
        await self._load_fields()
        await self._load_crop_plans()
        logger.info(f"FarmManager initialized with {len(self.fields)} fields")

    # Field Management
    async def add_field(self, field: FieldBoundary) -> Dict[str, Any]:
        """Add new field with GPS boundaries"""
        if field.id in self.fields:
            return {"success": False, "error": "Field ID already exists"}

        # Calculate area from coordinates
        field.area_hectares = self._calculate_polygon_area(field.coordinates)

        self.fields[field.id] = field
        await self._save_field(field)

        if self._voice:
            await self._voice.speak(f"Khet {field.name} add ho gaya. Area: {field.area_hectares:.2f} hectare.")

        return {"success": True, "field_id": field.id, "area_hectares": field.area_hectares}

    async def update_field(self, field_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update field details"""
        if field_id not in self.fields:
            return {"success": False, "error": "Field not found"}

        field = self.fields[field_id]
        for key, value in updates.items():
            if hasattr(field, key):
                setattr(field, key, value)

        await self._save_field(field)
        return {"success": True}

    async def delete_field(self, field_id: str) -> Dict[str, Any]:
        """Delete field"""
        if field_id not in self.fields:
            return {"success": False, "error": "Field not found"}

        del self.fields[field_id]
        if self._db:
            await self._db.execute("DELETE FROM fields WHERE id = ?", (field_id,))

        return {"success": True}

    def _calculate_polygon_area(self, coordinates: List[GPSPoint]) -> float:
        """Calculate polygon area in hectares using shoelace formula"""
        if len(coordinates) < 3:
            return 0.0

        # Convert lat/lon to approximate meters (rough approximation)
        # 1 degree lat ≈ 111 km, 1 degree lon ≈ 111 km * cos(lat)
        avg_lat = sum(c.latitude for c in coordinates) / len(coordinates)
        lat_factor = 111000  # meters per degree
        lon_factor = 111000 * math.cos(math.radians(avg_lat))

        area_m2 = 0
        n = len(coordinates)
        for i in range(n):
            j = (i + 1) % n
            x1 = coordinates[i].longitude * lon_factor
            y1 = coordinates[i].latitude * lat_factor
            x2 = coordinates[j].longitude * lon_factor
            y2 = coordinates[j].latitude * lat_factor
            area_m2 += x1 * y2 - x2 * y1

        area_hectares = abs(area_m2) / 2 / 10000
        return round(area_hectares, 4)

    # Crop Rotation Planning
    async def create_crop_plan(self, plan: CropPlan) -> Dict[str, Any]:
        """Create crop plan for a field"""
        if plan.field_id not in self.fields:
            return {"success": False, "error": "Field not found"}

        if plan.field_id not in self.crop_plans:
            self.crop_plans[plan.field_id] = []

        # Check for conflicts with existing plans
        for existing in self.crop_plans[plan.field_id]:
            if not (plan.expected_harvest < existing.sowing_date or plan.sowing_date > existing.expected_harvest):
                return {"success": False, "error": "Crop plan overlaps with existing plan"}

        self.crop_plans[plan.field_id].append(plan)
        await self._save_crop_plan(plan)

        if self._voice:
            await self._voice.speak(f"Fasal {plan.crop.value} ka plan bana diya. Beej: {plan.seed_rate_kg_per_ha} kg/hectare.")

        return {"success": True, "plan_id": id(plan)}

    async def get_crop_rotation_suggestions(self, field_id: str) -> List[Dict]:
        """Get AI-powered crop rotation suggestions"""
        if field_id not in self.fields:
            return []

        field = self.fields[field_id]
        history = self.crop_plans.get(field_id, [])

        # Get last 3 crops
        last_crops = [p.crop.value for p in sorted(history, key=lambda x: x.sowing_date, reverse=True)[:3]]

        if self._llm:
            prompt = f"""
            Field: {field.name}, Area: {field.area_hectares} ha
            Soil: {field.soil_type.value}, Irrigation: {field.irrigation_type.value}
            Last 3 crops: {last_crops}

            Suggest next 3 crops for rotation with reasons. Consider soil health, pest management, market demand.
            Return JSON array: [{{"crop": "...", "reason": "...", "season": "kharif/rabi/zaid"}}]
            """
            response = await self._llm.generate(prompt, temperature=0.3)
            try:
                return json.loads(response.content)
            except:
                pass

        # Fallback basic rotation
        rotations = {
            CropType.WHEAT: [CropType.MOONG, CropType.MAIZE, CropType.MUSTARD],
            CropType.RICE: [CropType.WHEAT, CropType.MUSTARD, CropType.VEGETABLES],
            CropType.MAIZE: [CropType.WHEAT, CropType.MOONG, CropType.GROUNDNUT],
            CropType.COTTON: [CropType.WHEAT, CropType.GRAM, CropType.FODDER],
        }

        last_crop = CropType(last_crops[0]) if last_crops else CropType.FALLOW
        suggestions = rotations.get(last_crop, [CropType.WHEAT, CropType.MOONG, CropType.MUSTARD])

        return [
            {"crop": c.value, "reason": "Soil health improvement", "season": "rabi"}
            for c in suggestions[:3]
        ]

    # Labor Management
    async def add_labor_record(self, record: LaborRecord) -> Dict[str, Any]:
        """Add labor record"""
        if record.field_id not in self.fields:
            return {"success": False, "error": "Field not found"}

        record.total_cost = record.workers * record.hours * record.rate_per_hour

        if record.field_id not in self.labor_records:
            self.labor_records[record.field_id] = []

        self.labor_records[record.field_id].append(record)
        await self._save_labor_record(record)

        return {"success": True, "cost": record.total_cost}

    async def get_labor_summary(self, field_id: str, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get labor cost summary"""
        if field_id not in self.labor_records:
            return {"total_cost": 0, "total_hours": 0, "records": 0}

        records = self.labor_records[field_id]
        if start_date:
            records = [r for r in records if r.date >= start_date]
        if end_date:
            records = [r for r in records if r.date <= end_date]

        total_cost = sum(r.total_cost for r in records)
        total_hours = sum(r.hours * r.workers for r in records)

        return {
            "total_cost": total_cost,
            "total_hours": total_hours,
            "records": len(records),
            "by_activity": self._group_by(records, "activity", lambda r: r.total_cost)
        }

    # Input Tracking
    async def add_input_record(self, record: InputRecord) -> Dict[str, Any]:
        """Add input (fertilizer, pesticide, seed) record"""
        if record.field_id not in self.fields:
            return {"success": False, "error": "Field not found"}

        record.total_cost = record.quantity * record.cost_per_unit

        if record.field_id not in self.input_records:
            self.input_records[record.field_id] = []

        self.input_records[record.field_id].append(record)
        await self._save_input_record(record)

        return {"success": True, "cost": record.total_cost}

    async def get_input_summary(self, field_id: str) -> Dict:
        """Get input cost summary"""
        if field_id not in self.input_records:
            return {"total_cost": 0, "by_type": {}}

        records = self.input_records[field_id]
        total = sum(r.total_cost for r in records)
        by_type = self._group_by(records, "input_type", lambda r: r.total_cost)

        return {"total_cost": total, "by_type": by_type}

    # Harvest Management
    async def record_harvest(self, record: HarvestRecord) -> Dict[str, Any]:
        """Record harvest"""
        if record.field_id not in self.fields:
            return {"success": False, "error": "Field not found"}

        if record.field_id not in self.harvest_records:
            self.harvest_records[record.field_id] = []

        self.harvest_records[record.field_id].append(record)
        await self._save_harvest_record(record)

        # Update crop plan status
        for plan in self.crop_plans.get(record.field_id, []):
            if plan.crop == record.crop and plan.status == "planned":
                plan.status = "harvested"

        if self._voice:
            await self._voice.speak(
                f"{record.crop.value} ki katai ho gayi. "
                f"Pedaavar: {record.yield_kg} kg, Gunvatta: {record.quality_grade}"
            )

        return {"success": True, "yield_kg_per_ha": record.yield_kg / max(record.area_harvested_ha, 0.001)}

    async def get_harvest_summary(self, field_id: str = None, year: int = None) -> Dict:
        """Get harvest summary"""
        records = []
        if field_id:
            records = self.harvest_records.get(field_id, [])
        else:
            for recs in self.harvest_records.values():
                records.extend(recs)

        if year:
            records = [r for r in records if r.date.year == year]

        total_yield = sum(r.yield_kg for r in records)
        total_area = sum(r.area_harvested_ha for r in records)
        total_revenue = sum(r.sold_qty_kg * r.sale_price_per_kg for r in records)

        return {
            "total_yield_kg": total_yield,
            "total_area_ha": total_area,
            "avg_yield_per_ha": total_yield / max(total_area, 0.001),
            "total_revenue": total_revenue,
            "by_crop": self._group_by(records, "crop", lambda r: r.yield_kg)
        }

    # Financial Tracking
    async def get_field_pnl(self, field_id: str, year: int = None) -> Dict:
        """Get profit & loss for a field"""
        if field_id not in self.fields:
            return {"error": "Field not found"}

        start = datetime(year, 1, 1) if year else datetime.now().replace(month=1, day=1)
        end = datetime(year, 12, 31) if year else datetime.now()

        labor = await self.get_labor_summary(field_id, start, end)
        inputs = await self.get_input_summary(field_id)
        harvest = await self.get_harvest_summary(field_id, year)

        revenue = harvest.get("total_revenue", 0)
        costs = labor["total_cost"] + inputs.get("total_cost", 0)

        return {
            "field": self.fields[field_id].name,
            "revenue": revenue,
            "costs": costs,
            "profit": revenue - costs,
            "margin_percent": ((revenue - costs) / max(revenue, 1)) * 100,
            "breakdown": {
                "labor": labor["total_cost"],
                "inputs": inputs.get("total_cost", 0),
                "harvest_revenue": revenue
            }
        }

    # GPS Utilities
    def calculate_distance(self, p1: GPSPoint, p2: GPSPoint) -> float:
        """Calculate distance between two GPS points in meters"""
        R = 6371000  # Earth radius in meters
        lat1, lon1 = math.radians(p1.latitude), math.radians(p1.longitude)
        lat2, lon2 = math.radians(p2.latitude), math.radians(p2.longitude)
        dlat = lat2 - lat1
        dlon = math.radians(p2.longitude - p1.longitude)

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def point_in_field(self, point: GPSPoint, field_id: str) -> bool:
        """Check if GPS point is inside field boundary (ray casting)"""
        if field_id not in self.fields:
            return False

        coords = self.fields[field_id].coordinates
        if len(coords) < 3:
            return False

        x, y = point.longitude, point.latitude
        inside = False

        for i in range(len(coords)):
            j = (i + 1) % len(coords)
            xi, yi = coords[i].longitude, coords[i].latitude
            xj, yj = coords[j].longitude, coords[j].latitude

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside

        return inside

    # Helper Methods
    def _group_by(self, records: List, key: str, value_fn) -> Dict:
        result = {}
        for r in records:
            k = getattr(r, key, "unknown")
            result[k] = result.get(k, 0) + value_fn(r)
        return result

    # Persistence
    async def _save_field(self, field: FieldBoundary):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO fields
                (id, name, coordinates, area_hectares, soil_type, irrigation_type, water_source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                field.id, field.name, json.dumps([{"lat": c.latitude, "lon": c.longitude, "alt": c.altitude} for c in field.coordinates]),
                field.area_hectares, field.soil_type.value, field.irrigation_type.value, field.water_source,
                field.created_at.isoformat()
            ))

    async def _load_fields(self):
        if not self._db:
            return
        rows = await self._db.fetchall("SELECT * FROM fields")
        for row in rows:
            coords = [GPSPoint(**c) for c in json.loads(row["coordinates"])]
            field = FieldBoundary(
                id=row["id"],
                name=row["name"],
                coordinates=coords,
                area_hectares=row["area_hectares"],
                soil_type=SoilType(row["soil_type"]),
                irrigation_type=IrrigationType(row["irrigation_type"]),
                water_source=row["water_source"],
                created_at=datetime.fromisoformat(row["created_at"])
            )
            self.fields[field.id] = field

    async def _save_crop_plan(self, plan: CropPlan):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO crop_plans
                (field_id, crop, variety, sowing_date, expected_harvest, seed_rate_kg_per_ha,
                 fertilizer_schedule, pesticide_schedule, irrigation_schedule, expected_yield_kg_per_ha, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plan.field_id, plan.crop.value, plan.variety,
                plan.sowing_date.isoformat(), plan.expected_harvest.isoformat(),
                plan.seed_rate_kg_per_ha,
                json.dumps(plan.fertilizer_schedule),
                json.dumps(plan.pesticide_schedule),
                json.dumps(plan.irrigation_schedule),
                plan.expected_yield_kg_per_ha, plan.status
            ))

    async def _load_crop_plans(self):
        if not self._db:
            return
        rows = await self._db.fetchall("SELECT * FROM crop_plans")
        for row in rows:
            plan = CropPlan(
                field_id=row["field_id"],
                crop=CropType(row["crop"]),
                variety=row["variety"],
                sowing_date=datetime.fromisoformat(row["sowing_date"]),
                expected_harvest=datetime.fromisoformat(row["expected_harvest"]),
                seed_rate_kg_per_ha=row["seed_rate_kg_per_ha"],
                fertilizer_schedule=json.loads(row["fertilizer_schedule"]),
                pesticide_schedule=json.loads(row["pesticide_schedule"]),
                irrigation_schedule=json.loads(row["irrigation_schedule"]),
                expected_yield_kg_per_ha=row["expected_yield_kg_per_ha"],
                status=row["status"]
            )
            if plan.field_id not in self.crop_plans:
                self.crop_plans[plan.field_id] = []
            self.crop_plans[plan.field_id].append(plan)

    async def _save_labor_record(self, record: LaborRecord):
        if self._db:
            await self._db.execute("""
                INSERT INTO labor_records (id, field_id, date, activity, workers, hours, rate_per_hour, total_cost, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record.id, record.field_id, record.date.isoformat(), record.activity,
                  record.workers, record.hours, record.rate_per_hour, record.total_cost, record.description))

    async def _save_input_record(self, record: InputRecord):
        if self._db:
            await self._db.execute("""
                INSERT INTO input_records (id, field_id, date, input_type, name, quantity, unit, cost_per_unit, total_cost, supplier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record.id, record.field_id, record.date.isoformat(), record.input_type,
                  record.name, record.quantity, record.unit, record.cost_per_unit, record.total_cost, record.supplier))

    async def _save_harvest_record(self, record: HarvestRecord):
        if self._db:
            await self._db.execute("""
                INSERT INTO harvest_records (id, field_id, crop, date, area_harvested_ha, yield_kg, quality_grade, moisture_percent, storage_location, sold_qty_kg, sale_price_per_kg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record.id, record.field_id, record.crop.value, record.date.isoformat(),
                  record.area_harvested_ha, record.yield_kg, record.quality_grade, record.moisture_percent,
                  record.storage_location, record.sold_qty_kg, record.sale_price_per_kg))

    def get_status(self) -> Dict[str, Any]:
        return {
            "fields": len(self.fields),
            "total_area_ha": sum(f.area_hectares for f in self.fields.values()),
            "active_crops": sum(len([p for p in plans if p.status == "planned"]) for plans in self.crop_plans.values()),
            "total_labor_records": sum(len(r) for r in self.labor_records.values()),
            "total_harvests": sum(len(r) for r in self.harvest_records.values()),
        }