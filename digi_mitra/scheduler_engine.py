\"\"\"
Digi Mitra Autonomous Task Scheduler & Smart Alarm Engine
- Schedules tasks with time & frequency:
  * One-time: 'kal subah 9 baje ye kaam karo'
  * Recurring: 'roz subah 9:15 baje Nifty chart dekho', 'har somwar bijli bill check karo'
- Remembers 'kab kab aur kaise karna hai' in offline database
\"\"\"

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class TaskSchedulerEngine:
    def __init__(self, schedule_file: str = './data/scheduled_tasks.json'):
        self.schedule_file = Path(schedule_file)
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> List[Dict[str, Any]]:
        if self.schedule_file.exists():
            try:
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_tasks(self):
        try:
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_scheduled_task(self, command: str, schedule_time: str, frequency: str = 'once', instructions: str = '') -> Dict[str, Any]:
        \"\"\"
        Adds an autonomous scheduled task.
        frequency: 'once', 'daily', 'weekly', 'monthly'
        \"\"\"
        task_id = f'task_{len(self.tasks) + 1}'
        task_entry = {
            'id': task_id,
            'command': command,
            'schedule_time': schedule_time, # e.g. '09:15 AM'
            'frequency': frequency,         # e.g. 'daily'
            'instructions': instructions or 'Autonomous execution by Digi Mitra',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'ACTIVE (Tayyar)'
        }
        self.tasks.append(task_entry)
        self._save_tasks()

        freq_hindi = {
            'once': 'Ek baar (Nirdharit samay par)',
            'daily': 'Roz (Har din is samay par)',
            'weekly': 'Har hafte',
            'monthly': 'Har mahine'
        }.get(frequency, frequency)

        return {
            'success': True,
            'task': task_entry,
            'message': f'⏰ <b>Task Schedule Ho Gaya!</b><br>📌 <b>Kaam:</b> {command}<br>🕒 <b>Samay:</b> {schedule_time}<br>🔁 <b>Aavritti (Frequency):</b> {freq_hindi}<br>⚙️ <b>Vidhi (Kaise karna hai):</b> {task_entry[\"instructions\"]}'
        }

    def get_all_scheduled_tasks(self) -> List[Dict[str, Any]]:
        return self.tasks
