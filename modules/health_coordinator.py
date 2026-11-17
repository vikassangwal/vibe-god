"""
Family Health Coordinator Module for Wife God Agent
Doctor appointments, medicine tracking, vaccination records, health insurance
"""

import asyncio
import logging
import json
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

logger = logging.getLogger("WifeGod.HealthCoordinator")


class AppointmentStatus(Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class MedicineStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ON_HOLD = "on_hold"


class VaccinationStatus(Enum):
    DUE = "due"
    ADMINISTERED = "administered"
    OVERDUE = "overdue"
    SKIPPED = "skipped"


class InsuranceClaimStatus(Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


@dataclass
class FamilyMember:
    id: str
    name: str
    date_of_birth: datetime
    gender: str
    blood_group: str = ""
    allergies: List[str] = field(default_factory=list)
    chronic_conditions: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    emergency_contact: str = ""
    insurance_policy: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DoctorAppointment:
    id: str
    member_id: str
    doctor_name: str
    specialization: str
    clinic_hospital: str
    appointment_date: datetime
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    reason: str = ""
    notes: str = ""
    prescription: str = ""
    follow_up_date: Optional[datetime] = None
    cost: float = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Medicine:
    id: str
    member_id: str
    name: str
    dosage: str
    frequency: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: MedicineStatus = MedicineStatus.ACTIVE
    prescribing_doctor: str = ""
    instructions: str = ""
    side_effects: str = ""
    refill_reminder_days: int = 7
    last_refill: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class VaccinationRecord:
    id: str
    member_id: str
    vaccine_name: str
    dose_number: int
    total_doses: int
    administered_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: VaccinationStatus = VaccinationStatus.DUE
    administered_by: str = ""
    batch_number: str = ""
    next_due_date: Optional[datetime] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class HealthInsuranceClaim:
    id: str
    member_id: str
    policy_number: str
    insurance_company: str
    claim_type: str
    claim_amount: float
    description: str
    status: InsuranceClaimStatus = InsuranceClaimStatus.SUBMITTED
    submitted_date: datetime = field(default_factory=datetime.now)
    approved_amount: float = 0
    documents: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LabReport:
    id: str
    member_id: str
    test_name: str
    lab_name: str
    test_date: datetime
    results: Dict[str, Any] = field(default_factory=dict)
    reference_ranges: Dict[str, str] = field(default_factory=dict)
    doctor_name: str = ""
    file_path: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class HealthCoordinator:
    """
    Family Health Coordinator
    - Doctor appointments management
    - Medicine tracking with refill reminders
    - Vaccination schedule tracking
    - Health insurance claims
    - Lab reports storage
    - Voice reminders
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.members: Dict[str, FamilyMember] = {}
        self.appointments: Dict[str, List[DoctorAppointment]] = {}
        self.medicines: Dict[str, List[Medicine]] = {}
        self.vaccinations: Dict[str, List[VaccinationRecord]] = {}
        self.claims: Dict[str, List[HealthInsuranceClaim]] = {}
        self.lab_reports: Dict[str, List[LabReport]] = {}
        self._db = None
        self._llm = None
        self._voice = None
        self._reminder_task = None

    def set_dependencies(self, db, llm, voice):
        self._db = db
        self._llm = llm
        self._voice = voice

    async def initialize(self):
        """Initialize health coordinator"""
        logger.info("Initializing HealthCoordinator...")

        await self._load_data()
        self._reminder_task = asyncio.create_task(self._reminder_loop())

        logger.info(f"HealthCoordinator initialized with {len(self.members)} family members")

    # Family Member Management
    async def add_member(self, member: FamilyMember) -> Dict[str, Any]:
        """Add family member"""
        if member.id in self.members:
            return {"success": False, "error": "Member ID already exists"}

        self.members[member.id] = member
        self.appointments[member.id] = []
        self.medicines[member.id] = []
        self.vaccinations[member.id] = []
        self.claims[member.id] = []
        self.lab_reports[member.id] = []

        await self._save_member(member)

        if self._voice:
            await self._voice.speak(f"Parivar ke naye sadasya {member.name} add ho gaye.")

        return {"success": True, "member_id": member.id}

    async def update_member(self, member_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update family member"""
        if member_id not in self.members:
            return {"success": False, "error": "Member not found"}

        member = self.members[member_id]
        for key, value in updates.items():
            if hasattr(member, key):
                setattr(member, key, value)

        await self._save_member(member)
        return {"success": True}

    # Appointment Management
    async def add_appointment(self, appointment: DoctorAppointment) -> Dict[str, Any]:
        """Schedule doctor appointment"""
        if appointment.member_id not in self.members:
            return {"success": False, "error": "Member not found"}

        if appointment.member_id not in self.appointments:
            self.appointments[appointment.member_id] = []

        self.appointments[appointment.member_id].append(appointment)
        await self._save_appointment(appointment)

        # Voice confirmation
        if self._voice:
            member = self.members[appointment.member_id]
            await self._voice.speak(
                f"{member.name} ke liye {appointment.doctor_name} ka appointment "
                f"{appointment.appointment_date.strftime('%d %B %Y')} ko fix ho gaya."
            )

        return {"success": True, "appointment_id": appointment.id}

    async def get_upcoming_appointments(self, days: int = 7) -> List[Dict]:
        """Get upcoming appointments"""
        now = datetime.now()
        end = now + timedelta(days=days)
        upcoming = []

        for member_id, appointments in self.appointments.items():
            for apt in appointments:
                if apt.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]:
                    if now <= apt.appointment_date <= end:
                        member = self.members.get(apt.member_id)
                        upcoming.append({
                            "appointment_id": apt.id,
                            "member": member.name if member else "Unknown",
                            "doctor": apt.doctor_name,
                            "specialization": apt.specialization,
                            "clinic": apt.clinic_hospital,
                            "date": apt.appointment_date.isoformat(),
                            "reason": apt.reason,
                            "status": apt.status.value
                        })

        upcoming.sort(key=lambda x: x["date"])
        return upcoming

    async def complete_appointment(self, appointment_id: str, prescription: str = "",
                                   follow_up: datetime = None, cost: float = 0) -> Dict[str, Any]:
        """Mark appointment as completed"""
        for member_id, appointments in self.appointments.items():
            for apt in appointments:
                if apt.id == appointment_id:
                    apt.status = AppointmentStatus.COMPLETED
                    apt.prescription = prescription
                    apt.follow_up_date = follow_up
                    apt.cost = cost
                    await self._save_appointment(apt)
                    return {"success": True}

        return {"success": False, "error": "Appointment not found"}

    # Medicine Management
    async def add_medicine(self, medicine: Medicine) -> Dict[str, Any]:
        """Add medicine prescription"""
        if medicine.member_id not in self.members:
            return {"success": False, "error": "Member not found"}

        if medicine.member_id not in self.medicines:
            self.medicines[medicine.member_id] = []

        self.medicines[medicine.member_id].append(medicine)
        await self._save_medicine(medicine)

        if self._voice:
            member = self.members[medicine.member_id]
            await self._voice.speak(
                f"{member.name} ke liye dawai {medicine.name} add ho gayi. "
                f"Dosage: {medicine.dosage}, {medicine.frequency}."
            )

        return {"success": True, "medicine_id": medicine.id}

    async def get_active_medicines(self, member_id: str = None) -> List[Dict]:
        """Get active medicines"""
        results = []

        members = [member_id] if member_id else list(self.medicines.keys())
        for mid in members:
            if mid not in self.medicines:
                continue
            for med in self.medicines[mid]:
                if med.status == MedicineStatus.ACTIVE:
                    member = self.members.get(mid)
                    results.append({
                        "medicine_id": med.id,
                        "member": self.members[mid].name if mid in self.members else "Unknown",
                        "name": med.name,
                        "dosage": med.dosage,
                        "frequency": med.frequency,
                        "start_date": med.start_date.isoformat(),
                        "end_date": med.end_date.isoformat() if med.end_date else None,
                        "instructions": med.instructions,
                        "prescribing_doctor": med.prescribing_doctor,
                        "refill_reminder_days": med.refill_reminder_days,
                        "last_refill": med.last_refill.isoformat() if med.last_refill else None
                    })

        return results

    async def mark_medicine_refilled(self, medicine_id: str) -> Dict[str, Any]:
        """Mark medicine as refilled"""
        for mid, medicines in self.medicines.items():
            for med in medicines:
                if med.id == medicine_id:
                    med.last_refill = datetime.now()
                    await self._save_medicine(med)
                    return {"success": True}
        return {"success": False, "error": "Medicine not found"}

    async def check_refill_reminders(self) -> List[Dict]:
        """Check medicines needing refill"""
        reminders = []
        now = datetime.now()

        for mid, medicines in self.medicines.items():
            for med in medicines:
                if med.status != MedicineStatus.ACTIVE:
                    continue
                if med.last_refill:
                    days_since = (now - med.last_refill).days
                    if days_since >= med.refill_reminder_days:
                        member = self.members.get(mid)
                        reminders.append({
                            "medicine_id": med.id,
                            "member": self.members[mid].name if mid in self.members else "Unknown",
                            "medicine": med.name,
                            "days_since_refill": (now - med.last_refill).days
                        })

        return reminders

    # Vaccination Tracking
    async def add_vaccination(self, vaccination: VaccinationRecord) -> Dict[str, Any]:
        """Add vaccination record"""
        if vaccination.member_id not in self.members:
            return {"success": False, "error": "Member not found"}

        if vaccination.member_id not in self.vaccinations:
            self.vaccinations[vaccination.member_id] = []

        self.vaccinations[vaccination.member_id].append(vaccination)
        await self._save_vaccination(vaccination)

        return {"success": True, "vaccination_id": vaccination.id}

    async def get_due_vaccinations(self, days_ahead: int = 30) -> List[Dict]:
        """Get upcoming vaccinations"""
        now = datetime.now()
        end = now + timedelta(days=days_ahead)
        due = []

        for mid, vaccs in self.vaccinations.items():
            for vac in vaccs:
                if vac.status == VaccinationStatus.DUE:
                    if now <= vac.due_date <= end:
                        member = self.members.get(vac.member_id)
                        due.append({
                            "vaccination_id": vac.id,
                            "member": self.members[vac.member_id].name if vac.member_id in self.members else "Unknown",
                            "vaccine": vac.vaccine_name,
                            "dose": f"{vac.dose_number}/{vac.total_doses}",
                            "due_date": vac.due_date.isoformat(),
                            "days_until_due": (vac.due_date - datetime.now()).days
                        })

        due.sort(key=lambda x: x["due_date"])
        return due

    async def administer_vaccination(self, vaccination_id: str, administered_date: datetime = None,
                                     administered_by: str = "", batch: str = "") -> Dict[str, Any]:
        """Mark vaccination as administered"""
        for mid, vaccs in self.vaccinations.items():
            for vac in vaccs:
                if vac.id == vaccination_id:
                    vac.status = VaccinationStatus.ADMINISTERED
                    vac.administered_date = administered_date or datetime.now()
                    vac.administered_by = administered_by
                    vac.batch_number = batch

                    # Calculate next dose
                    if vac.dose_number < vac.total_doses:
                        # Would calculate based on vaccine schedule
                        pass

                    await self._save_vaccination(vacc)
                    return {"success": True}

        return {"success": False, "error": "Vaccination not found"}

    # Insurance Claims
    async def submit_claim(self, claim: HealthInsuranceClaim) -> Dict[str, Any]:
        """Submit insurance claim"""
        if claim.member_id not in self.members:
            return {"success": False, "error": "Member not found"}

        if claim.member_id not in self.claims:
            self.claims[claim.member_id] = []

        self.claims[claim.member_id].append(claim)
        await self._save_claim(claim)

        return {"success": True, "claim_id": claim.id}

    async def update_claim_status(self, claim_id: str, status: InsuranceClaimStatus,
                                  approved_amount: float = 0, notes: str = "") -> Dict[str, Any]:
        """Update claim status"""
        for mid, claims in self.claims.items():
            for claim in claims:
                if claim.id == claim_id:
                    claim.status = status
                    claim.approved_amount = approved_amount
                    claim.notes += f"\n{datetime.now()}: {notes}"
                    await self._save_claim(claim)
                    return {"success": True}
        return {"success": False, "error": "Claim not found"}

    async def get_claims_summary(self, member_id: str = None) -> Dict:
        """Get claims summary"""
        claims_list = []
        if member_id:
            claims_list = self.claims.get(member_id, [])
        else:
            for claims in self.claims.values():
                claims_list.extend(claims)

        return {
            "total": len(claims_list),
            "by_status": {
                s.value: len([c for c in claims_list if c.status == s])
                for s in InsuranceClaimStatus
            },
            "total_claimed": sum(c.claim_amount for c in claims_list),
            "total_approved": sum(c.approved_amount for c in claims_list)
        }

    # Lab Reports
    async def add_lab_report(self, report: LabReport) -> Dict[str, Any]:
        """Add lab report"""
        if report.member_id not in self.members:
            return {"success": False, "error": "Member not found"}

        if report.member_id not in self.lab_reports:
            self.lab_reports[report.member_id] = []

        self.lab_reports[report.member_id].append(report)
        await self._save_lab_report(report)

        return {"success": True, "report_id": report.id}

    async def get_lab_reports(self, member_id: str, test_name: str = None) -> List[Dict]:
        """Get lab reports"""
        if member_id not in self.lab_reports:
            return []

        reports = self.lab_reports[member_id]
        if test_name:
            reports = [r for r in reports if test_name.lower() in r.test_name.lower()]

        return [
            {
                "report_id": r.id,
                "test_name": r.test_name,
                "lab_name": r.lab_name,
                "test_date": r.test_date.isoformat(),
                "results": r.results,
                "reference_ranges": r.reference_ranges,
                "doctor": r.doctor_name,
                "file": r.file_path
            }
            for r in reports
        ]

    # Reminders
    async def _reminder_loop(self):
        """Background reminder loop"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour

                # Check appointments
                upcoming = await self.get_upcoming_appointments(1)
                for apt in upcoming:
                    apt_time = datetime.fromisoformat(apt["date"])
                    if apt_time <= datetime.now() + timedelta(hours=2):
                        await self._voice.speak(
                            f"Yaad dilane ke liye: {apt['member']} ka appointment "
                            f"{apt['doctor']} ke saath {apt['date']} ko hai."
                        )

                # Check medicine refills
                refills = await self.check_refill_reminders()
                for refill in refills:
                    await self._voice.speak(
                        f"{refill['member']} ki dawai {refill['medicine']} ka refill chahiye."
                    )

                # Check vaccinations
                due_vaccs = await self.get_due_vaccinations(7)
                for vac in due_vaccs:
                    await self._voice.speak(
                        f"{vac['member']} ka {vac['vaccine']} vaccination {vac['days_until_due']} din mein due hai."
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reminder loop error: {e}")
                await asyncio.sleep(300)

    # Persistence
    async def _save_member(self, member: FamilyMember):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO family_members
                (id, name, date_of_birth, gender, blood_group, allergies, chronic_conditions,
                 medications, emergency_contact, insurance_policy, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                member.id, member.name, member.date_of_birth.isoformat(), member.gender,
                member.blood_group, json.dumps(member.allergies), json.dumps(member.chronic_conditions),
                json.dumps(member.medications), member.emergency_contact, member.insurance_policy,
                member.created_at.isoformat()
            ))

    async def _load_data(self):
        if not self._db:
            return
        # Load members
        rows = await self._db.fetchall("SELECT * FROM family_members")
        for row in rows:
            member = FamilyMember(
                id=row["id"],
                name=row["name"],
                date_of_birth=datetime.fromisoformat(row["date_of_birth"]),
                gender=row["gender"],
                blood_group=row["blood_group"],
                allergies=json.loads(row["allergies"]),
                chronic_conditions=json.loads(row["chronic_conditions"]),
                medications=json.loads(row["medications"]),
                emergency_contact=row["emergency_contact"],
                insurance_policy=row["insurance_policy"],
                created_at=datetime.fromisoformat(row["created_at"])
            )
            self.members[member.id] = member
            self.appointments[member.id] = []
            self.medicines[member.id] = []
            self.vaccinations[member.id] = []
            self.claims[member.id] = []
            self.lab_reports[member.id] = []

        # Load other data...
        # (appointments, medicines, vaccinations, claims, lab_reports would be loaded similarly)

    async def _save_appointment(self, apt: DoctorAppointment):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO appointments
                (id, member_id, doctor_name, specialization, clinic_hospital, appointment_date,
                 status, reason, notes, prescription, follow_up_date, cost, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                apt.id, apt.member_id, apt.doctor_name, apt.specialization,
                apt.clinic_hospital, apt.appointment_date.isoformat(),
                apt.status.value, apt.reason, apt.notes, apt.prescription,
                apt.follow_up_date.isoformat() if apt.follow_up_date else None,
                apt.cost, apt.created_at.isoformat()
            ))

    async def _save_medicine(self, med: Medicine):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO medicines
                (id, member_id, name, dosage, frequency, start_date, end_date, status,
                 prescribing_doctor, instructions, side_effects, refill_reminder_days,
                 last_refill, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                med.id, med.member_id, med.name, med.dosage, med.frequency,
                med.start_date.isoformat(),
                med.end_date.isoformat() if med.end_date else None,
                med.status.value, med.prescribing_doctor, med.instructions,
                med.side_effects, med.refill_reminder_days,
                med.last_refill.isoformat() if med.last_refill else None,
                med.created_at.isoformat()
            ))

    async def _save_vaccination(self, vac: VaccinationRecord):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO vaccinations
                (id, member_id, vaccine_name, dose_number, total_doses, administered_date,
                 due_date, status, administered_by, batch_number, next_due_date, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vac.id, vac.member_id, vac.vaccine_name, vac.dose_number, vac.total_doses,
                vac.administered_date.isoformat() if vac.administered_date else None,
                vac.due_date.isoformat(), vac.status.value, vac.administered_by,
                vac.batch_number, vac.next_due_date.isoformat() if vac.next_due_date else None,
                vac.notes, vac.created_at.isoformat()
            ))

    async def _save_claim(self, claim: HealthInsuranceClaim):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO claims
                (id, member_id, policy_number, insurance_company, claim_type, claim_amount,
                 description, status, submitted_date, approved_amount, documents, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                claim.id, claim.member_id, claim.policy_number, claim.insurance_company,
                claim.claim_type, claim.claim_amount, claim.description, claim.status.value,
                claim.submitted_date.isoformat(), claim.approved_amount,
                json.dumps(claim.documents), claim.notes, claim.created_at.isoformat()
            ))

    async def _save_lab_report(self, report: LabReport):
        if self._db:
            await self._db.execute("""
                INSERT OR REPLACE INTO lab_reports
                (id, member_id, test_name, lab_name, test_date, results, reference_ranges,
                 doctor_name, file_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.id, report.member_id, report.test_name, report.lab_name,
                report.test_date.isoformat(), json.dumps(report.results),
                json.dumps(report.reference_ranges), report.doctor_name,
                report.file_path, report.created_at.isoformat()
            ))

    def get_status(self) -> Dict[str, Any]:
        total_meds = sum(len(m) for m in self.medicines.values())
        active_meds = sum(len([med for med in meds if med.status == MedicineStatus.ACTIVE])
                          for meds in self.medicines.values())

        return {
            "family_members": len(self.members),
            "total_appointments": sum(len(a) for a in self.appointments.values()),
            "total_medicines": total_meds,
            "active_medicines": active_meds,
            "total_vaccinations": sum(len(v) for v in self.vaccinations.values()),
            "total_claims": sum(len(c) for c in self.claims.values()),
            "lab_reports": sum(len(r) for r in self.lab_reports.values()),
        }