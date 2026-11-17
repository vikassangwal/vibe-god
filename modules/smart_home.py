"""
Smart Home IoT Module for Wife God Agent
Geyser, Water Tank, Security, AC, Lights - MQTT/HTTP control
"""

import asyncio
import logging
import json
import time
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

logger = logging.getLogger("WifeGod.SmartHome")


class DeviceType(Enum):
    GEYSER = "geyser"
    WATER_TANK = "water_tank"
    AC = "ac"
    LIGHT = "light"
    FAN = "fan"
    SECURITY_CAMERA = "security_camera"
    DOOR_SENSOR = "door_sensor"
    MOTION_SENSOR = "motion_sensor"
    SMOKE_DETECTOR = "smoke_detector"
    GAS_DETECTOR = "gas_detector"
    SMART_PLUG = "smart_plug"
    CURTAIN = "curtain"
    LOCK = "lock"


class DeviceStatus(Enum):
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class DeviceConfig:
    id: str
    name: str
    type: DeviceType
    room: str
    protocol: str  # mqtt, http, zigbee, zwave, gpio
    connection_params: Dict[str, Any] = field(default_factory=dict)
    schedules: List[Dict] = field(default_factory=list)
    auto_rules: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceState:
    device_id: str
    status: DeviceStatus
    value: Any = None  # temperature, brightness, level, etc.
    last_update: datetime = field(default_factory=datetime.now)
    is_online: bool = True
    error: str = ""


@dataclass
class Schedule:
    id: str
    device_id: str
    action: str  # "on", "off", "set_value"
    value: Any = None
    cron: str = ""  # cron expression
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@dataclass
class AutomationRule:
    id: str
    name: str
    trigger: Dict  # {"type": "time"/"sensor"/"voice", "condition": "..."}
    conditions: List[Dict] = field(default_factory=list)
    actions: List[Dict] = field(default_factory=list)  # [{"device_id": "...", "action": "on", "value": ...}]
    enabled: bool = True
    last_triggered: Optional[datetime] = None


class SmartHomeManager:
    """
    Smart Home IoT Manager
    - MQTT/HTTP device control
    - Scheduling (cron-based)
    - Automation rules
    - Voice control
    - Energy monitoring
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.devices: Dict[str, DeviceConfig] = {}
        self.states: Dict[str, DeviceState] = {}
        self.schedules: Dict[str, Schedule] = {}
        self.rules: Dict[str, AutomationRule] = {}
        self._mqtt_client = None
        self._http_session = None
        self._db = None
        self._llm = None
        self._voice = None
        self._scheduler_task = None
        self._monitor_task = None

    def set_dependencies(self, db, llm, voice):
        self._db = db
        self._llm = llm
        self._voice = voice

    async def initialize(self):
        """Initialize smart home manager"""
        logger.info("Initializing SmartHomeManager...")

        # Load devices
        await self._load_devices()

        # Initialize MQTT if configured
        await self._init_mqtt()

        # Start scheduler
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        # Start state monitor
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info(f"SmartHomeManager initialized with {len(self.devices)} devices")

    async def _init_mqtt(self):
        """Initialize MQTT client"""
        mqtt_config = self.config.get("mqtt", {})
        if not mqtt_config.get("enabled", False):
            return

        try:
            import paho.mqtt.client as mqtt
            self._mqtt_client = mqtt.Client()
            self._mqtt_client.on_connect = self._on_mqtt_connect
            self._mqtt_client.on_message = self._on_mqtt_message
            self._mqtt_client.username_pw_set(
                mqtt_config.get("username", ""),
                mqtt_config.get("password", "")
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._mqtt_client.connect(
                    mqtt_config.get("host", "localhost"),
                    mqtt_config.get("port", 1883),
                    60
                )
            )
            self._mqtt_client.loop_start()
            logger.info("MQTT client connected")
        except Exception as e:
            logger.warning(f"MQTT initialization failed: {e}")

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connect callback"""
        if rc == 0:
            logger.info("MQTT connected")
            # Subscribe to device topics
            for device in self.devices.values():
                if device.protocol == "mqtt":
                    topic = device.connection_params.get("state_topic", f"home/{device.id}/state")
                    self._mqtt_client.subscribe(topic)
        else:
            logger.error(f"MQTT connection failed: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = msg.payload.decode()

            # Find device by topic
            for device in self.devices.values():
                if device.protocol == "mqtt":
                    state_topic = device.connection_params.get("state_topic", f"home/{device.id}/state")
                    if topic == state_topic:
                        self._update_state_from_mqtt(device.id, payload)
                        break
        except Exception as e:
            logger.error(f"MQTT message error: {e}")

    def _update_state_from_mqtt(self, device_id: str, payload: str):
        """Update device state from MQTT payload"""
        try:
            data = json.loads(payload)
            if device_id in self.states:
                state = self.states[device_id]
                state.status = DeviceStatus(data.get("status", "unknown"))
                state.value = data.get("value")
                state.last_update = datetime.now()
                state.is_online = True
        except Exception as e:
            logger.error(f"State update error: {e}")

    # Device Management
    async def add_device(self, device: DeviceConfig) -> Dict[str, Any]:
        """Add new IoT device"""
        if device.id in self.devices:
            return {"success": False, "error": "Device ID already exists"}

        self.devices[device.id] = device
        self.states[device.id] = DeviceState(
            device_id=device.id,
            status=DeviceStatus.UNKNOWN
        )

        # Subscribe to MQTT topic if applicable
        if self._mqtt_client and device.protocol == "mqtt":
            topic = device.connection_params.get("state_topic", f"home/{device.id}/state")
            self._mqtt_client.subscribe(topic)

        await self._save_device(device)
        return {"success": True, "device_id": device.id}

    async def remove_device(self, device_id: str) -> Dict[str, Any]:
        """Remove device"""
        if device_id not in self.devices:
            return {"success": False, "error": "Device not found"}

        device = self.devices[device_id]

        # Unsubscribe from MQTT
        if self._mqtt_client and device.protocol == "mqtt":
            topic = device.connection_params.get("state_topic", f"home/{device_id}/state")
            self._mqtt_client.unsubscribe(topic)

        del self.devices[device_id]
        del self.states[device_id]

        if self._db:
            await self._db.execute("DELETE FROM devices WHERE id = ?", (device_id,))

        return {"success": True}

    async def control_device(self, device_id: str, action: str, value: Any = None) -> Dict[str, Any]:
        """Control a device"""
        if device_id not in self.devices:
            return {"success": False, "error": "Device not found"}

        device = self.devices[device_id]

        try:
            if device.protocol == "mqtt" and self._mqtt_client:
                return await self._control_mqtt(device, action, value)
            elif device.protocol == "http":
                return await self._control_http(device, action, value)
            elif device.protocol == "gpio":
                return await self._control_gpio(device, action, value)
            else:
                return {"success": False, "error": f"Unsupported protocol: {device.protocol}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _control_mqtt(self, device: DeviceConfig, action: str, value: Any) -> Dict[str, Any]:
        """Control device via MQTT"""
        if not self._mqtt_client:
            return {"success": False, "error": "MQTT not connected"}

        topic = device.connection_params.get("command_topic", f"home/{device.id}/command")
        payload = {"action": action}
        if value is not None:
            payload["value"] = value

        self._mqtt_client.publish(topic, json.dumps(payload))
        return {"success": True, "method": "mqtt"}

    async def _control_http(self, device: DeviceConfig, action: str, value: Any) -> Dict[str, Any]:
        """Control device via HTTP"""
        import aiohttp

        url = device.connection_params.get("url", "")
        if not url:
            return {"success": False, "error": "No URL configured"}

        headers = device.connection_params.get("headers", {})
        payload = {"action": action}
        if value is not None:
            payload["value"] = value

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return {"success": True, "method": "http"}
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _control_gpio(self, device: DeviceConfig, action: str, value: Any) -> Dict[str, Any]:
        """Control device via GPIO"""
        try:
            import RPi.GPIO as GPIO
            pin = device.connection_params.get("pin")
            if not pin:
                return {"success": False, "error": "No GPIO pin configured"}

            if action == "on":
                GPIO.output(pin, GPIO.HIGH)
            elif action == "off":
                GPIO.output(pin, GPIO.LOW)
            elif action == "pwm":
                # PWM control for dimming/speed
                pwm = GPIO.PWM(pin, device.connection_params.get("frequency", 100))
                pwm.start(value if value else 50)

            return {"success": True, "method": "gpio"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Scheduling
    async def add_schedule(self, schedule: Schedule) -> Dict[str, Any]:
        """Add schedule for device"""
        self.schedules[schedule.id] = schedule
        await self._save_schedule(schedule)

        # Calculate next run
        schedule.next_run = self._calculate_next_run(schedule.cron)
        return {"success": True, "next_run": schedule.next_run.isoformat() if schedule.next_run else None}

    async def remove_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Remove schedule"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            if self._db:
                await self._db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            return {"success": True}
        return {"success": False, "error": "Schedule not found"}

    def _calculate_next_run(self, cron_expr: str) -> Optional[datetime]:
        """Calculate next run time from cron expression"""
        try:
            from croniter import croniter
            base = datetime.now()
            cron = croniter(cron_expr, base)
            return cron.get_next(datetime)
        except:
            return None

    async def _scheduler_loop(self):
        """Background scheduler loop"""
        while True:
            try:
                now = datetime.now()

                for schedule in list(self.schedules.values()):
                    if not schedule.enabled:
                        continue

                    if schedule.next_run and schedule.next_run <= now:
                        # Execute schedule
                        await self.control_device(schedule.device_id, schedule.action, schedule.value)
                        schedule.last_run = now
                        schedule.next_run = self._calculate_next_run(schedule.cron)
                        await self._save_schedule(schedule)

                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    # Automation Rules
    async def add_rule(self, rule: AutomationRule) -> Dict[str, Any]:
        """Add automation rule"""
        self.rules[rule.id] = rule
        await self._save_rule(rule)
        return {"success": True}

    async def remove_rule(self, rule_id: str) -> Dict[str, Any]:
        """Remove automation rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            if self._db:
                await self._db.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            return {"success": True}
        return {"success": False, "error": "Rule not found"}

    async def _monitor_loop(self):
        """Monitor device states and evaluate rules"""
        while True:
            try:
                # Check device online status
                for device_id, state in self.states.items():
                    if state.last_update < datetime.now() - timedelta(minutes=5):
                        state.is_online = False

                # Evaluate rules
                await self._evaluate_rules()

                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(30)

    async def _evaluate_rules(self):
        """Evaluate automation rules"""
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # Check trigger conditions
            triggered = await self._check_rule_trigger(rule)
            if triggered:
                # Execute actions
                for action in rule.actions:
                    device_id = action.get("device_id")
                    action_type = action.get("action")
                    value = action.get("value")
                    if device_id:
                        await self.control_device(device_id, action_type, value)

                rule.last_triggered = datetime.now()
                await self._save_rule(rule)

                if self._voice:
                    await self._voice.speak(f"Automation rule {rule.name} triggered.")

    async def _check_rule_trigger(self, rule: AutomationRule) -> bool:
        """Check if rule trigger conditions are met"""
        trigger = rule.trigger

        if trigger.get("type") == "time":
            # Time-based trigger
            schedule_time = trigger.get("time", "")
            now = datetime.now().strftime("%H:%M")
            return now == schedule_time

        elif trigger.get("type") == "sensor":
            # Sensor-based trigger
            device_id = trigger.get("device_id")
            condition = trigger.get("condition", "")
            if device_id in self.states:
                state = self.states[device_id]
                return self._evaluate_condition(state.value, condition)

        elif trigger.get("type") == "voice":
            # Voice trigger - handled separately
            return False

        return False

    def _evaluate_condition(self, value: Any, condition: str) -> bool:
        """Evaluate condition string like '> 30', '< 20', '== on'"""
        if value is None:
            return False

        try:
            if condition.startswith(">"):
                return float(value) > float(condition[1:])
            elif condition.startswith("<"):
                return float(value) < float(condition[1:])
            elif condition.startswith(">="):
                return float(value) >= float(condition[2:])
            elif condition.startswith("<="):
                return float(value) <= float(condition[2:])
            elif condition.startswith("=="):
                return str(value).lower() == condition[2:].lower().strip()
            elif condition.startswith("!="):
                return str(value).lower() != condition[2:].lower().strip()
        except:
            pass
        return False

    # Voice Control
    async def voice_control(self, command: str) -> Dict[str, Any]:
        """Process voice command for device control"""
        if not self._llm:
            return {"success": False, "error": "LLM not available"}

        # Parse command with LLM
        prompt = f"""
        Parse this voice command for smart home control:
        "{command}"

        Available devices: {json.dumps({d.id: {"name": d.name, "type": d.type.value, "room": d.room} for d in self.devices.values()})}

        Return JSON: {{"action": "control|status|schedule", "device_id": "...", "action": "on|off|set_value", "value": ..., "room": "..."}}
        """

        response = await self._llm.generate(prompt, temperature=0.1)
        try:
            parsed = json.loads(response.content)
            device_id = parsed.get("device_id")
            if device_id and device_id in self.devices:
                return await self.control_device(
                    device_id,
                    parsed.get("action"),
                    parsed.get("value")
                )
            return {"success": False, "error": "Device not found"}
        except:
            return {"success": False, "error": "Failed to parse command"}

    # Energy Monitoring
    async def get_energy_report(self, period: str = "day") -> Dict[str, Any]:
        """Get energy consumption report"""
        # This would aggregate from energy-monitoring devices
        return {
            "period": period,
            "total_kwh": 0,
            "cost": 0,
            "by_device": {},
            "peak_usage": None
        }

    # Quick Actions
    async def turn_off_all_lights(self) -> Dict[str, Any]:
        """Turn off all lights"""
        results = []
        for device in self.devices.values():
            if device.type == DeviceType.LIGHT:
                result = await self.control_device(device.id, "off")
                results.append({"device": device.name, "success": result.get("success")})
        return {"results": results}

    async def set_ac_temperature(self, device_id: str, temperature: float) -> Dict[str, Any]:
        """Set AC temperature"""
        return await self.control_device(device_id, "set_value", {"temperature": temperature})

    async def set_geyser_timer(self, device_id: str, minutes: int) -> Dict[str, Any]:
        """Turn on geyser for specified minutes"""
        result = await self.control_device(device_id, "on")
        if result.get("success"):
            # Schedule auto-off
            asyncio.create_task(self._auto_off(device_id, minutes * 60))
        return result

    async def _auto_off(self, device_id: str, seconds: int):
        await asyncio.sleep(seconds)
        await self.control_device(device_id, "off")

    # Persistence
    async def _save_device(self, device: DeviceConfig):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO devices
                (id, name, type, room, protocol, connection_params, schedules, auto_rules, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device.id, device.name, device.type.value, device.room, device.protocol,
                json.dumps(device.connection_params), json.dumps(device.schedules),
                json.dumps(device.auto_rules), json.dumps(device.metadata),
                datetime.now().isoformat()
            ))

    async def _load_devices(self):
        if not self._db:
            return
        rows = await self._db.fetchall("SELECT * FROM devices")
        for row in rows:
            device = DeviceConfig(
                id=row["id"],
                name=row["name"],
                type=DeviceType(row["type"]),
                room=row["room"],
                protocol=row["protocol"],
                connection_params=json.loads(row["connection_params"]),
                schedules=json.loads(row["schedules"]),
                auto_rules=json.loads(row["auto_rules"]),
                metadata=json.loads(row["metadata"])
            )
            self.devices[device.id] = device
            self.states[device.id] = DeviceState(device_id=device.id, status=DeviceStatus.UNKNOWN)

    async def _save_schedule(self, schedule: Schedule):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO schedules
                (id, device_id, action, value, cron, enabled, last_run, next_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                schedule.id, schedule.device_id, schedule.action,
                json.dumps(schedule.value), schedule.cron, schedule.enabled,
                schedule.last_run.isoformat() if schedule.last_run else None,
                schedule.next_run.isoformat() if schedule.next_run else None
            ))

    async def _save_rule(self, rule: AutomationRule):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO rules
                (id, name, trigger, conditions, actions, enabled, last_triggered)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.id, rule.name, json.dumps(rule.trigger),
                json.dumps(rule.conditions), json.dumps(rule.actions),
                rule.enabled, rule.last_triggered.isoformat() if rule.last_triggered else None
            ))

    def get_status(self) -> Dict[str, Any]:
        online = sum(1 for s in self.states.values() if s.is_online)
        return {
            "total_devices": len(self.devices),
            "online_devices": online,
            "offline_devices": len(self.devices) - online,
            "schedules": len(self.schedules),
            "rules": len(self.rules),
            "states": {k: {"status": v.status.value, "value": v.value, "online": v.is_online} for k, v in self.states.items()}
        }

    async def close(self):
        if self._scheduler_task:
            self._scheduler_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
        logger.info("SmartHomeManager closed")