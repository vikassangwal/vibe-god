import os
import shutil
from pathlib import Path
from typing import Dict, Any, List

class SmartFileSorter:
    def __init__(self):
        self.home = Path.home()
        self.downloads_dir = self.home / 'Downloads'
        self.desktop_dir = self.home / 'Desktop'

    def get_rules(self) -> Dict[str, List[str]]:
        return {
            'Aadhaar_Govt_Docs': ['.pdf'],
            'Photos_Images': ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.svg'],
            'Work_Spreadsheets': ['.xlsx', '.xls', '.csv'],
            'Documents_Word': ['.docx', '.doc', '.txt', '.rtf'],
            'Media_Videos': ['.mp4', '.mkv', '.avi', '.mov'],
            'Archives_Zip': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'Software_Installers': ['.exe', '.msi']
        }

    def scan_and_sort(self, target_folder: str = 'Downloads') -> Dict[str, Any]:
        source = self.downloads_dir if target_folder.lower() == 'downloads' else self.desktop_dir
        if not source.exists():
            return {'success': False, 'error': f'Folder {source} not found'}

        rules = self.get_rules()
        moved_count = 0
        details = []

        for item in source.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                ext = item.suffix.lower()
                dest_category = None
                for cat, extensions in rules.items():
                    if ext in extensions:
                        dest_category = cat
                        break

                if dest_category:
                    cat_dir = source / dest_category
                    cat_dir.mkdir(exist_ok=True)
                    dest_file = cat_dir / item.name
                    # Avoid overwrite
                    if not dest_file.exists():
                        shutil.move(str(item), str(dest_file))
                        moved_count += 1
                        details.append(f'{item.name} -> {dest_category}/')

        return {
            'success': True,
            'folder': str(source),
            'files_moved': moved_count,
            'details': details[:10],
            'message': f'✅ {moved_count} files successfully organized into clean categories!'
        }
