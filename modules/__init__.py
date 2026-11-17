"""
Modules for Wife God Agent
"""

from .doc_processor import DocProcessor, DocType
from .captcha_solver import CaptchaSolver, CaptchaType
from .pyautogui_fallback import PyAutoGUIFallback
from .farm_manager import FarmManager, CropType, SoilType, IrrigationType
from .smart_home import SmartHomeManager, DeviceType, DeviceStatus
from .health_coordinator import HealthCoordinator, AppointmentStatus, MedicineStatus, VaccinationStatus, InsuranceClaimStatus
from .passive_income import PassiveIncomeManager, PlatformType, ResourceType
from .video_editor import VideoEditor, VideoType, Platform
from .market_intelligence import MarketIntelligence, CommodityType, Exchange, TrendDirection
from .data_products import DataProductsGenerator, ProductType, OutputFormat
from .enam_integration import eNAMIntegration, SourceType, PriceType

__all__ = [
    "DocProcessor",
    "DocType",
    "CaptchaSolver",
    "CaptchaType",
    "PyAutoGUIFallback",
    "FarmManager",
    "CropType",
    "SoilType",
    "IrrigationType",
    "SmartHomeManager",
    "DeviceType",
    "DeviceStatus",
    "HealthCoordinator",
    "AppointmentStatus",
    "MedicineStatus",
    "VaccinationStatus",
    "InsuranceClaimStatus",
    "PassiveIncomeManager",
    "PlatformType",
    "ResourceType",
    "VideoEditor",
    "VideoType",
    "Platform",
    "MarketIntelligence",
    "CommodityType",
    "Exchange",
    "TrendDirection",
    "DataProductsGenerator",
    "ProductType",
    "OutputFormat",
    "eNAMIntegration",
    "SourceType",
    "PriceType",
]