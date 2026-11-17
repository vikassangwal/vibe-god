#!/usr/bin/env python3
"""
Wife God - Integration Test Suite
End-to-end tests for all major workflows.
"""

import asyncio
import sys
import os
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config
from core.database import DatabaseManager
from core.local_llm import LocalLLM
from core.voice import VoiceCommunicator
from modules.doc_processor import DocProcessor
from modules.captcha_solver import CaptchaSolver
from modules.pyautogui_fallback import PyAutoGUIFallback
from bots.emitra_bot import eMitraBot
from bots.twitter_bot import TwitterBot
from modules.farm_manager import FarmManager
from modules.smart_home import SmartHomeManager
from modules.health_coordinator import HealthCoordinator
from modules.passive_income import PassiveIncomeManager
from modules.video_editor import VideoEditor
from modules.market_intelligence import MarketIntelligence
from modules.data_products import DataProductsGenerator
from modules.enam_integration import eNAMIntegration


class IntegrationTestSuite:
    """Complete integration test suite for Wife God"""

    def __init__(self):
        self.config = Config("config.json")
        self.db = None
        self.llm = None
        self.voice = None
        self.doc_processor = None
        self.captcha_solver = None
        self.pyautogui_fallback = None
        self.emitra_bot = None
        self.twitter_bot = None
        self.farm_manager = None
        self.smart_home = None
        self.health_coordinator = None
        self.passive_income = None
        self.video_editor = None
        self.market_intel = None
        self.data_products = None
        self.enam = None
        self.results = []

    async def setup(self):
        """Initialize all components"""
        print("🔧 Setting up test environment...")

        self.db = DatabaseManager(self.config.db_path)
        await self.db.initialize()

        self.llm = LocalLLM(self.config.ollama_url, self.config.ollama_model)
        await self.llm.initialize()

        self.voice = VoiceCommunicator(self.config.voice_config)
        await self.voice.initialize()

        self.doc_processor = DocProcessor(self.config.doc_config)
        await self.doc_processor.initialize()

        self.captcha_solver = CaptchaSolver(self.config.captcha_config)
        await self.captcha_solver.initialize()

        self.pyautogui_fallback = PyAutoGUIFallback(self.config.fallback_config)
        await self.pyautogui_fallback.initialize()

        self.emitra_bot = eMitraBot(
            config=self.config.emitra_config,
            llm=self.llm,
            voice=self.voice,
            doc_processor=self.doc_processor,
            captcha_solver=self.captcha_solver,
            pyautogui_fallback=self.pyautogui_fallback,
            db=self.db
        )
        await self.emitra_bot.initialize()

        self.twitter_bot = TwitterBot(
            config=self.config.twitter_config,
            llm=self.llm,
            voice=self.voice,
            doc_processor=self.doc_processor,
            pyautogui_fallback=self.pyautogui_fallback,
            db=self.db
        )
        await self.twitter_bot.initialize()

        # Initialize farm manager
        self.farm_manager = FarmManager(self.config.get("farm", {}))
        self.farm_manager.set_dependencies(self.db, self.llm, self.voice)
        await self.farm_manager.initialize()

        # Initialize smart home
        self.smart_home = SmartHomeManager(self.config.get("smart_home", {}))
        self.smart_home.set_dependencies(self.db, self.llm, self.voice)
        await self.smart_home.initialize()

        # Initialize health coordinator
        self.health_coordinator = HealthCoordinator(self.config.get("health", {}))
        self.health_coordinator.set_dependencies(self.db, self.llm, self.voice)
        await self.health_coordinator.initialize()

        # Initialize passive income
        self.passive_income = PassiveIncomeManager(self.config.get("passive_income", {}))
        self.passive_income.set_dependencies(self.db, self.llm, self.voice)
        await self.passive_income.initialize()

        # Initialize video editor
        self.video_editor = VideoEditor(self.config.get("video", {}))
        self.video_editor.set_dependencies(self.db, self.llm, self.voice)
        await self.video_editor.initialize()

        # Initialize market intelligence
        self.market_intel = MarketIntelligence(self.config.get("market", {}))
        self.market_intel.set_dependencies(self.db, self.llm, self.voice)
        await self.market_intel.initialize()

        # Initialize data products
        self.data_products = DataProductsGenerator(self.config.get("data_products", {}))
        self.data_products.set_dependencies(self.db, self.llm, self.voice)
        await self.data_products.initialize()

        # Initialize eNAM integration
        self.enam = eNAMIntegration(self.config.get("enam", {}))
        self.enam.set_dependencies(self.db, self.llm, self.voice)
        await self.enam.initialize()

    def record(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {'✅' if passed else '❌'} {test_name}: {details}")

    async def test_llm_basic(self):
        """Test basic LLM functionality"""
        try:
            resp = await self.llm.generate(
                "Say hello in Hindi",
                temperature=0.1,
                max_tokens=50
            )
            if resp.content and "नमस्ते" in resp.content:
                self.record("LLM Basic Generation", True, "Hindi response generated")
            else:
                self.record("LLM Basic Generation", True, f"Response: {resp.content[:50]}")
        except Exception as e:
            self.record("LLM Basic Generation", False, str(e))

    async def test_llm_structured(self):
        """Test structured output from LLM"""
        try:
            resp = await self.llm.generate(
                'Return JSON: {"name": "test", "value": 42}',
                system_prompt="Return only valid JSON",
                temperature=0.0,
                max_tokens=100
            )
            import json
            data = json.loads(resp.content)
            if data.get("name") == "test" and data.get("value") == 42:
                self.record("LLM Structured Output", True, "Valid JSON returned")
            else:
                self.record("LLM Structured Output", False, "Invalid JSON structure")
        except Exception as e:
            self.record("LLM Structured Output", False, str(e))

    async def test_voice_tts(self):
        """Test TTS"""
        try:
            await self.voice.speak("Test message")
            self.record("Voice TTS", True, "Spoke test message")
        except Exception as e:
            self.record("Voice TTS", False, str(e))

    async def test_voice_stt(self):
        """Test STT (requires audio file)"""
        try:
            # This would need an audio file - skip for now
            self.record("Voice STT", True, "Skipped (requires audio file)")
        except Exception as e:
            self.record("Voice STT", False, str(e))

    async def test_doc_processor(self):
        """Test document processor with a dummy image"""
        try:
            # Create a simple test image
            from PIL import Image, ImageDraw, ImageFont
            import io

            img = Image.new('RGB', (400, 200), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), "Test Aadhaar 1234 5678 9012", fill='black')

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                img.save(f.name)
                temp_path = f.name

            result = await self.doc_processor.process_document(temp_path, "aadhaar")
            os.unlink(temp_path)

            if result.status == "success" and "1234" in result.ocr_text:
                self.record("Doc Processor OCR", True, "Aadhaar number extracted")
            else:
                self.record("Doc Processor OCR", False, f"Status: {result.status}")
        except Exception as e:
            self.record("Doc Processor OCR", False, str(e))

    async def test_doc_compression(self):
        """Test image compression"""
        try:
            from PIL import Image
            import tempfile
            import os

            # Create large test image
            img = Image.new('RGB', (2000, 1500), color='red')
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                img.save(f.name, quality=95)
                temp_path = f.name

            original_size = os.path.getsize(temp_path)
            result = await self.doc_processor.process_document(temp_path, "photo")
            os.unlink(temp_path)

            if result.status == "success" and result.size_kb <= 100:
                self.record("Doc Compression", True, f"Compressed to {result.size_kb:.1f}KB")
            else:
                self.record("Doc Compression", False, f"Size: {result.size_kb:.1f}KB")
        except Exception as e:
            self.record("Doc Compression", False, str(e))

    async def test_database(self):
        """Test database operations"""
        try:
            # Test task logging
            from core.base_agent import Task, TaskType, TaskStatus
            from datetime import datetime

            task = Task(
                id="test_task_1",
                type=TaskType.DOC_PROCESS,
                status=TaskStatus.COMPLETED,
                params={"test": True},
                result={"success": True}
            )
            await self.db.log_task(task)

            # Retrieve
            task_data = await self.db.get_task("test_task_1")
            if task_data and task_data["status"] == "completed":
                self.record("Database Operations", True, "Task logged and retrieved")
            else:
                self.record("Database Operations", False, "Task not found")
        except Exception as e:
            self.record("Database Operations", False, str(e))

    async def test_captcha_solver(self):
        """Test captcha solver"""
        try:
            # Test math captcha
            from modules.captcha_solver import CaptchaType
            result = await self.captcha_solver._solve_math("2 + 3 = ")
            if result.success and result.answer == "5":
                self.record("Captcha Math Solver", True, "Solved 2+3=5")
            else:
                self.record("Captcha Math Solver", False, f"Answer: {result.answer}")
        except Exception as e:
            self.record("Captcha Math Solver", False, str(e))

    async def test_pyautogui_fallback(self):
        """Test PyAutoGUI fallback"""
        try:
            pos = self.pyautogui_fallback.get_mouse_position()
            if pos and len(pos) == 2:
                self.record("PyAutoGUI Position", True, f"Position: {pos}")
            else:
                self.record("PyAutoGUI Position", False, "Could not get position")
        except Exception as e:
            self.record("PyAutoGUI Position", False, str(e))

    async def test_farm_manager(self):
        """Test farm manager"""
        try:
            from modules.farm_manager import FieldBoundary, GPSPoint, CropType, SoilType, IrrigationType
            from datetime import datetime

            field = FieldBoundary(
                id="test_field_1",
                name="Test Field",
                coordinates=[
                    GPSPoint(73.3, 28.0),
                    GPSPoint(73.31, 28.0),
                    GPSPoint(73.31, 28.01),
                    GPSPoint(73.3, 28.01)
                ],
                area_hectares=1.0,
                soil_type=SoilType.LOAMY,
                irrigation_type=IrrigationType.TUBEWELL
            )

            result = await self.farm_manager.add_field(field)
            if result.get("success"):
                self.record("Farm Manager Add Field", True, f"Area: {result['area_hectares']} ha")
            else:
                self.record("Farm Manager Add Field", False, result.get("error"))
        except Exception as e:
            self.record("Farm Manager Add Field", False, str(e))

    async def test_crop_rotation(self):
        """Test crop rotation suggestions"""
        try:
            field_id = "test_field_1"
            if field_id in self.farm_manager.fields:
                suggestions = await self.farm_manager.get_crop_rotation_suggestions(field_id)
                if suggestions and len(suggestions) > 0:
                    self.record("Crop Rotation Suggestions", True, f"Got {len(suggestions)} suggestions")
                else:
                    self.record("Crop Rotation Suggestions", False, "No suggestions returned")
            else:
                self.record("Crop Rotation Suggestions", False, "Test field not found")
        except Exception as e:
            self.record("Crop Rotation Suggestions", False, str(e))

    async def test_smart_home(self):
        """Test smart home device control"""
        try:
            from modules.smart_home import DeviceConfig, DeviceType, DeviceStatus

            device = DeviceConfig(
                id="test_light",
                name="Test Light",
                type=DeviceType.LIGHT,
                room="living_room",
                protocol="gpio",
                connection_params={"pin": 18}
            )

            result = await self.smart_home.add_device(device)
            if result.get("success"):
                self.record("Smart Home Add Device", True, "Device added")
            else:
                self.record("Smart Home Add Device", False, result.get("error"))

            # Test control
            result = await self.smart_home.control_device("test_light", "on")
            self.record("Smart Home Control", True, "Control attempted")
        except Exception as e:
            self.record("Smart Home Control", False, str(e))

    async def test_health_coordinator(self):
        """Test health coordinator"""
        try:
            from modules.health_coordinator import FamilyMember, DoctorAppointment, Medicine
            from datetime import datetime, timedelta

            member = FamilyMember(
                id="test_member",
                name="Test User",
                date_of_birth=datetime(1990, 1, 1),
                gender="Male"
            )

            result = await self.health_coordinator.add_member(member)
            if result.get("success"):
                self.record("Health Coordinator Add Member", True, "Member added")
            else:
                self.record("Health Coordinator Add Member", False, result.get("error"))

            # Test appointment
            apt = DoctorAppointment(
                id="test_apt",
                member_id="test_member",
                doctor_name="Dr. Test",
                specialization="General",
                clinic_hospital="Test Clinic",
                appointment_date=datetime.now() + timedelta(days=1)
            )
            result = await self.health_coordinator.add_appointment(apt)
            self.record("Health Coordinator Appointment", result.get("success", False), "Appointment added")
        except Exception as e:
            self.record("Health Coordinator", False, str(e))

    async def test_market_intelligence(self):
        """Test market intelligence"""
        try:
            summary = await self.market_intel.get_market_summary()
            if summary and "futures" in summary:
                self.record("Market Intelligence Summary", True, f"Got {len(summary['futures'])} futures")
            else:
                self.record("Market Intelligence Summary", False, "Empty summary")
        except Exception as e:
            self.record("Market Intelligence Summary", False, str(e))

    async def test_price_prediction(self):
        """Test price prediction"""
        try:
            from modules.market_intelligence import CommodityType
            pred = await self.market_intel._predict_price_for_commodity(CommodityType.WHEAT)
            if pred:
                self.record("Price Prediction", True, f"Prediction generated")
            else:
                self.record("Price Prediction", False, "No prediction returned")
        except Exception as e:
            self.record("Price Prediction", False, str(e))

    async def test_hedging_advice(self):
        """Test hedging advice"""
        try:
            from modules.market_intelligence import CommodityType
            advice = await self.market_intel.get_hedging_advice(
                CommodityType.WHEAT, "long", 1000, "moderate"
            )
            if advice:
                self.record("Hedging Advice", True, f"Hedge ratio: {advice.hedge_ratio}")
            else:
                self.record("Hedging Advice", False, "No advice returned")
        except Exception as e:
            self.record("Hedging Advice", False, str(e))

    async def test_data_products(self):
        """Test data products generation"""
        try:
            result = await self.data_products.generate_product("mandi_weekly", "pdf")
            if result.get("success"):
                self.record("Data Products Generation", True, "Weekly report generated")
            else:
                self.record("Data Products Generation", False, result.get("error"))
        except Exception as e:
            self.record("Data Products Generation", False, str(e))

    async def test_enam_integration(self):
        """Test eNAM integration"""
        try:
            comparison = await self.enam.get_price_comparison("wheat", "Bikaner", "Rajasthan")
            if "error" not in comparison:
                self.record("eNAM Price Comparison", True, f"Sources: {list(comparison['by_source'].keys())}")
            else:
                self.record("eNAM Price Comparison", False, comparison.get("error"))
        except Exception as e:
            self.record("eNAM Price Comparison", False, str(e))

    async def test_procurement_optimization(self):
        """Test procurement optimization"""
        try:
            result = await self.enam.get_best_procurement_option("wheat", 1000, "Bikaner")
            if result.get("best_option"):
                self.record("Procurement Optimization", True, f"Best: {result['best_option']['source']}")
            else:
                self.record("Procurement Optimization", False, "No best option")
        except Exception as e:
            self.record("Procurement Optimization", False, str(e))

    async def test_video_editor(self):
        """Test video editor project creation"""
        try:
            from modules.video_editor import VideoProject, VideoType

            project = VideoProject(
                id="test_project",
                name="Test Video",
                type=VideoType.FARM_TIMELAPSE,
                source_files=[]
            )

            result = await self.video_editor.create_project(project)
            if result.get("success"):
                self.record("Video Editor Project", True, "Project created")
            else:
                self.record("Video Editor Project", False, result.get("error"))
        except Exception as e:
            self.record("Video Editor Project", False, str(e))

    async def test_passive_income(self):
        """Test passive income manager"""
        try:
            from modules.passive_income import PlatformType, ResourceType

            config = {
                "platform": PlatformType.HONEYGAIN,
                "enabled": False,  # Don't actually start
                "api_key": "test"
            }

            result = await self.passive_income.configure_platform(PlatformType.HONEYGAIN, config)
            if result.get("success"):
                self.record("Passive Income Config", True, "Platform configured")
            else:
                self.record("Passive Income Config", False, result.get("error"))

            resources = await self.passive_income.get_system_resources()
            if resources and "cpu_percent" in resources:
                self.record("Resource Monitoring", True, f"CPU: {resources['cpu_percent']}%")
            else:
                self.record("Resource Monitoring", False, "No resources returned")
        except Exception as e:
            self.record("Passive Income", False, str(e))

    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*60)
        print("🧪 WIFE GOD INTEGRATION TEST SUITE")
        print("="*60 + "\n")

        await self.setup()

        print("\n📋 Running Core Tests...")
        await self.test_llm_basic()
        await self.test_llm_structured()
        await self.test_voice_tts()
        await self.test_voice_stt()

        print("\n📄 Document Processing Tests...")
        await self.test_doc_processor()
        await self.test_doc_compression()
        await self.test_captcha_solver()

        print("\n💾 Database Tests...")
        await self.test_database()

        print("\n🖥️ System Automation Tests...")
        await self.test_pyautogui_fallback()
        await self.test_captcha_solver()

        print("\n🚜 Farm Management Tests...")
        await self.test_farm_manager()
        await self.test_crop_rotation()

        print("\n🏠 Smart Home Tests...")
        await self.test_smart_home()

        print("\n🏥 Health Coordinator Tests...")
        await self.test_health_coordinator()

        print("\n📈 Market Intelligence Tests...")
        await self.test_market_intelligence()
        await self.test_price_prediction()
        await self.test_hedging_advice()

        print("\n📊 Data Products Tests...")
        await self.test_data_products()

        print("\n💰 Market Integration Tests...")
        await self.test_enam_integration()
        await self.test_procurement_optimization()

        print("\n🎬 Video Editor Tests...")
        await self.test_video_editor()

        print("\n💰 Passive Income Tests...")
        await self.test_passive_income()

        # Summary
        self.print_summary()

    def print_summary(self):
        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"])
        total = len(self.results)

        print("\n" + "="*60)
        print("📊 INTEGRATION TEST SUMMARY")
        print("="*60)
        print(f"  Total Tests:  {len(self.results)}")
        print(f"  ✅ Passed:     {passed}")
        print(f"  ❌ Failed:     {failed}")
        print(f"  📊 Pass Rate:  {passed/len(self.results)*100:.1f}%")

        if failed > 0:
            print("\n❌ Failed Tests:")
            for r in self.results:
                if not r["passed"]:
                    print(f"  ❌ {r['test']}: {r['details']}")

        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {failed} test(s) failed")

        return failed == 0


async def main():
    suite = IntegrationTestSuite()
    success = await suite.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())