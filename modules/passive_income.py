"""
Passive CPU/GPU Monetization + Bandwidth Sharing Module
Monetize idle resources: Golem, Akash, Honeygain, Crypto nodes
"""

import asyncio
import logging
import json
import time
import psutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.local_llm import LocalLLM
    from ..core.voice import VoiceCommunicator
    from ..core.database import DatabaseManager

logger = logging.getLogger("WifeGod.PassiveIncome")


class PlatformType(Enum):
    GOLEM = "golem"
    AKASH = "akash"
    HONEYGAIN = "honeygain"
    MYSTNODES = "mystnodes"
    TRAFFICMONETIZER = "trafficmonetizer"
    CRYPTO_NODE = "crypto_node"
    FLUX = "flux"
    HYPERSPACE = "hyperspace"


class ResourceType(Enum):
    CPU = "cpu"
    GPU = "gpu"
    BANDWIDTH = "bandwidth"
    STORAGE = "storage"
    RAM = "ram"


@dataclass
class PlatformConfig:
    platform: PlatformType
    enabled: bool = False
    api_key: str = ""
    wallet_address: str = ""
    config_params: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[ResourceType, float] = field(default_factory=dict)


@dataclass
class EarningsRecord:
    id: str
    platform: PlatformType
    resource_type: ResourceType
    amount: float
    currency: str
    timestamp: datetime
    tx_hash: str = ""


@dataclass
class ResourceUsage:
    timestamp: datetime
    cpu_percent: float
    gpu_percent: float
    ram_percent: float
    network_sent_mb: float
    network_recv_mb: float
    disk_read_mb: float
    disk_write_mb: float


class PassiveIncomeManager:
    """
    Passive Income Manager
    - Golem/Akash compute rental
    - Honeygain/MystNodes bandwidth sharing
    - Crypto node operation (lightweight)
    - Automatic resource management
    - Earnings tracking
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.platforms: Dict[PlatformType, PlatformConfig] = {}
        self._db = None
        self._llm = None
        self._voice = None
        self._monitor_task = None
        self._earnings_task = None
        self._running = False
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._last_network = psutil.net_io_counters()
        self._last_disk = psutil.disk_io_counters()

    def set_dependencies(self, db, llm, voice):
        self._db = db
        self._llm = llm
        self._voice = voice

    async def initialize(self):
        """Initialize passive income manager"""
        logger.info("Initializing PassiveIncomeManager...")

        # Load platform configs
        await self._load_platforms()

        # Start monitoring
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._earnings_task = asyncio.create_task(self._earnings_loop())

        logger.info("PassiveIncomeManager initialized")

    async def configure_platform(self, platform: PlatformType, config: PlatformConfig) -> Dict[str, Any]:
        """Configure a platform"""
        self.platforms[platform] = config
        await self._save_platform_config(platform, config)

        if config.enabled:
            await self._start_platform(platform)

        return {"success": True}

    async def _start_platform(self, platform: PlatformType):
        """Start a platform process"""
        config = self.platforms.get(platform)
        if not config or not config.enabled:
            return

        logger.info(f"Starting {platform.value}...")

        if platform == PlatformType.HONEYGAIN:
            await self._start_honeygain(config)
        elif platform == PlatformType.MYSTNODES:
            await self._start_mystnodes(config)
        elif platform == PlatformType.TRAFFICMONETIZER:
            await self._start_trafficmonetizer(config)
        elif platform == PlatformType.GOLEM:
            await self._start_golem(config)
        elif platform == PlatformType.AKASH:
            await self._start_akash(config)
        elif platform == PlatformType.CRYPTO_NODE:
            await self._start_crypto_node(config)

    async def _start_honeygain(self, config: PlatformConfig):
        """Start Honeygain"""
        try:
            # Honeygain CLI or Docker
            cmd = ["honeygain", "start"]
            if config.api_key:
                cmd.extend(["--api-key", config.api_key])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._processes["honeygain"] = proc
            logger.info("Honeygain started")
        except Exception as e:
            logger.error(f"Honeygain start failed: {e}")

    async def _start_mystnodes(self, config: PlatformConfig):
        """Start MystNodes"""
        try:
            cmd = ["mystnodes", "start"]
            if config.api_key:
                cmd.extend(["--key", config.api_key])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._processes["mystnodes"] = proc
            logger.info("MystNodes started")
        except Exception as e:
            logger.error(f"MystNodes start failed: {e}")

    async def _start_trafficmonetizer(self, config: PlatformConfig):
        """Start TrafficMonetizer"""
        try:
            cmd = ["trafficmonetizer", "start"]
            if config.api_key:
                cmd.extend(["--token", config.api_key])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._processes["trafficmonetizer"] = proc
            logger.info("TrafficMonetizer started")
        except Exception as e:
            logger.error(f"TrafficMonetizer start failed: {e}")

    async def _start_golem(self, config: PlatformConfig):
        """Start Golem provider"""
        try:
            # Golem provider via Docker
            cmd = [
                "docker", "run", "-d",
                "--name", "golem-provider",
                "-p", "7464:7464",
                "-p", "7465:7465",
                "-v", f"{config.config_params.get('data_dir', './golem-data')}:/data",
                "golemfactory/golem:latest",
                "provider", "start"
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._processes["golem"] = proc
            logger.info("Golem provider started")
        except Exception as e:
            logger.error(f"Golem start failed: {e}")

    async def _start_akash(self, config: PlatformConfig):
        """Start Akash provider"""
        try:
            # Akash provider setup
            cmd = ["akash", "provider", "start"]
            if config.wallet_address:
                cmd.extend(["--from", config.wallet_address])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._processes["akash"] = proc
            logger.info("Akash provider started")
        except Exception as e:
            logger.error(f"Akash start failed: {e}")

    async def _start_crypto_node(self, config: PlatformConfig):
        """Start lightweight crypto node"""
        # This would run a lightweight node like Flux, HyperSpace, etc.
        pass

    async def stop_platform(self, platform: PlatformType) -> Dict[str, Any]:
        """Stop a platform"""
        proc = self._processes.get(platform.value)
        if proc:
            proc.terminate()
            await proc.wait()
            del self._processes[platform.value]

        if platform in self.platforms:
            self.platforms[platform].enabled = False
            await self._save_platform_config(platform, self.platforms[platform])

        return {"success": True}

    async def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()

        # GPU info
        gpu_info = {}
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            for i, gpu in enumerate(gpus):
                gpu_info[f"gpu_{i}"] = {
                    "name": gpu.name,
                    "load": gpu.load * 100,
                    "memory_used": gpu.memoryUsed,
                    "memory_total": gpu.memoryTotal,
                    "temperature": gpu.temperature
                }
        except:
            pass

        # Network delta
        current_net = psutil.net_io_counters()
        net_sent_mb = (current_net.bytes_sent - self._last_network.bytes_sent) / 1024 / 1024
        net_recv_mb = (current_net.bytes_recv - self._last_network.bytes_recv) / 1024 / 1024
        self._last_network = current_net

        # Disk delta
        current_disk = psutil.disk_io_counters()
        disk_read_mb = (current_disk.read_bytes - self._last_disk.read_bytes) / 1024 / 1024
        disk_write_mb = (current_disk.write_bytes - self._last_disk.write_bytes) / 1024 / 1024
        self._last_disk = current_disk

        return {
            "cpu_percent": cpu,
            "ram_percent": ram.percent,
            "ram_available_gb": ram.available / 1024 / 1024 / 1024,
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / 1024 / 1024 / 1024,
            "network": {
                "sent_mb": net_sent_mb,
                "recv_mb": net_recv_mb
            },
            "disk_io": {
                "read_mb": disk_read_mb,
                "write_mb": disk_write_mb
            },
            "gpu": gpu_info
        }

    async def _monitor_loop(self):
        """Monitor resources and manage platforms"""
        while self._running:
            try:
                resources = await self.get_system_resources()

                # Auto-pause if user is active (high CPU/RAM usage)
                if resources["cpu_percent"] > 80 or resources["ram_percent"] > 85:
                    await self._pause_all_platforms()
                elif resources["cpu_percent"] < 30 and resources["ram_percent"] < 60:
                    await self._resume_all_platforms()

                # Log resource usage
                if self._db:
                    await self._save_resource_usage(resources)

                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(60)

    async def _pause_all_platforms(self):
        """Pause all platforms when user is active"""
        for platform, proc in self._processes.items():
            if proc and proc.returncode is None:
                # Send SIGSTOP to pause
                try:
                    import signal
                    proc.send_signal(signal.SIGSTOP)
                    logger.info(f"Paused {platform}")
                except:
                    pass

    async def _resume_all_platforms(self):
        """Resume all platforms when user is idle"""
        for platform, proc in self._processes.items():
            if proc and proc.returncode is None:
                try:
                    import signal
                    proc.send_signal(signal.SIGCONT)
                    logger.info(f"Resumed {platform}")
                except:
                    pass

    async def _earnings_loop(self):
        """Track earnings from platforms"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Every hour

                # Fetch earnings from each platform
                for platform in self.platforms:
                    if self.platforms[platform].enabled:
                        earnings = await self._fetch_platform_earnings(platform)
                        if earnings:
                            await self._save_earnings(earnings)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Earnings loop error: {e}")
                await asyncio.sleep(3600)

    async def _fetch_platform_earnings(self, platform: PlatformType) -> List[EarningsRecord]:
        """Fetch earnings from platform API"""
        records = []

        try:
            if platform == PlatformType.HONEYGAIN:
                records = await self._fetch_honeygain_earnings()
            elif platform == PlatformType.MYSTNODES:
                records = await self._fetch_mystnodes_earnings()
            elif platform == PlatformType.TRAFFICMONETIZER:
                records = await self._fetch_trafficmonetizer_earnings()
            elif platform == PlatformType.GOLEM:
                records = await self._fetch_golem_earnings()
            elif platform == PlatformType.AKASH:
                records = await self._fetch_akash_earnings()
        except Exception as e:
            logger.error(f"Earnings fetch failed for {platform.value}: {e}")

        return records

    async def _fetch_honeygain_earnings(self) -> List[EarningsRecord]:
        """Fetch Honeygain earnings"""
        # Would call Honeygain API
        return []

    async def _fetch_mystnodes_earnings(self) -> List[EarningsRecord]:
        return []

    async def _fetch_trafficmonetizer_earnings(self) -> List[EarningsRecord]:
        return []

    async def _fetch_golem_earnings(self) -> List[EarningsRecord]:
        return []

    async def _fetch_akash_earnings(self) -> List[EarningsRecord]:
        return []

    async def get_earnings_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get earnings summary"""
        if not self._db:
            return {"total": 0, "by_platform": {}, "by_currency": {}}

        cutoff = datetime.now() - timedelta(days=days)
        rows = await self._db.fetchall("""
            SELECT platform, currency, SUM(amount) as total
            FROM earnings
            WHERE timestamp > ?
            GROUP BY platform, currency
        """, (cutoff.isoformat(),))

        summary = {"total_usd": 0, "by_platform": {}, "by_currency": {}}
        for row in rows:
            summary["by_platform"][row["platform"]] = summary["by_platform"].get(row["platform"], 0) + row["total"]
            summary["by_currency"][row["currency"]] = summary["by_currency"].get(row["currency"], 0) + row["total"]

        return summary

    async def get_status(self) -> Dict[str, Any]:
        resources = await self.get_system_resources()

        active_platforms = [p.value for p, c in self.platforms.items() if c.enabled]
        running_processes = [p for p, proc in self._processes.items() if proc.returncode is None]

        return {
            "resources": resources,
            "active_platforms": active_platforms,
            "running_processes": running_processes,
            "total_platforms": len(self.platforms)
        }

    # Persistence
    async def _save_platform_config(self, platform: PlatformType, config: PlatformConfig):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO platform_configs
                (platform, enabled, api_key, wallet_address, config_params, resource_limits)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                platform.value, config.enabled, config.api_key, config.wallet_address,
                json.dumps(config.config_params), json.dumps({k.value: v for k, v in config.resource_limits.items()})
            ))

    async def _load_platforms(self):
        if not self._db:
            return
        rows = await self._db.fetchall("SELECT * FROM platform_configs")
        for row in rows:
            self.platforms[PlatformType(row["platform"])] = PlatformConfig(
                platform=PlatformType(row["platform"]),
                enabled=row["enabled"],
                api_key=row["api_key"],
                wallet_address=row["wallet_address"],
                config_params=json.loads(row["config_params"]),
                resource_limits={ResourceType(k): v for k, v in json.loads(row["resource_limits"]).items()}
            )

    async def _save_resource_usage(self, resources: Dict):
        if self._db:
            await self._db.execute("""
                INSERT INTO resource_usage
                (timestamp, cpu_percent, ram_percent, disk_percent, net_sent_mb, net_recv_mb)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                resources["cpu_percent"], resources["ram_percent"],
                resources["disk_percent"], resources["network"]["sent_mb"],
                resources["network"]["recv_mb"]
            ))

    async def _save_earnings(self, records: List[EarningsRecord]):
        if not self._db or not records:
            return

        for r in records:
            await self._db.execute("""
                INSERT INTO earnings
                (id, platform, resource_type, amount, currency, timestamp, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                r.id, r.platform.value, r.resource_type.value,
                r.amount, r.currency, r.timestamp.isoformat(), r.tx_hash
            ))

    async def close(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._earnings_task:
            self._earnings_task.cancel()

        for proc in self._processes.values():
            if proc.returncode is None:
                proc.terminate()
                await proc.wait()

        logger.info("PassiveIncomeManager closed")