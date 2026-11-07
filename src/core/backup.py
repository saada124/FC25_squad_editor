import os
import shutil
from datetime import datetime
from typing import Tuple, List

def create_load_backup(filepath: str) -> Tuple[str, str]:
    """
    Creates an immediate safety duplicate of the squads file in the same directory.
    Format: <OriginalName>.backup_<YYYYMMDD_HHMMSS>
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Squads file not found: {filepath}")
    
    file_dir = os.path.dirname(os.path.abspath(filepath))
    file_name = os.path.basename(filepath)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_name}.backup_{timestamp}"
    backup_path = os.path.join(file_dir, backup_name)
    
    shutil.copy2(filepath, backup_path)
    msg = f"Created safety backup: {backup_name}"
    return backup_path, msg

def list_folder_backups(filepath: str) -> List[str]:
    """Lists all backup copies existing in the same folder as filepath."""
    if not os.path.exists(filepath):
        return []
    file_dir = os.path.dirname(os.path.abspath(filepath))
    file_name = os.path.basename(filepath)
    prefix = f"{file_name}.backup_"
    
    backups = []
    try:
        for entry in os.listdir(file_dir):
            if entry.startswith(prefix):
                backups.append(os.path.join(file_dir, entry))
    except Exception:
        pass
    return sorted(backups, reverse=True)

def restore_backup(backup_path: str, target_path: str) -> Tuple[bool, str]:
    """Restores a backup copy over the target squads file."""
    if not os.path.exists(backup_path):
        return False, f"Backup file not found: {backup_path}"
    try:
        shutil.copy2(backup_path, target_path)
        return True, f"Successfully restored {os.path.basename(backup_path)} over {os.path.basename(target_path)}"
    except Exception as e:
        return False, f"Restore failed: {str(e)}"

def delete_backup(backup_path: str) -> Tuple[bool, str]:
    """Deletes a backup file from disk."""
    if not os.path.exists(backup_path):
        return False, f"Backup file not found: {backup_path}"
    try:
        os.remove(backup_path)
        return True, f"Deleted backup: {os.path.basename(backup_path)}"
    except Exception as e:
        return False, f"Delete failed: {str(e)}"

def purge_old_backups(filepath: str, keep_last: int = 5) -> Tuple[int, str]:
    """Deletes older backups, retaining only the latest keep_last copies."""
    backups = list_folder_backups(filepath)
    if len(backups) <= keep_last:
        return 0, f"No backups to purge ({len(backups)} total, limit is {keep_last})."
    
    to_delete = backups[keep_last:]
    deleted_count = 0
    for bp in to_delete:
        try:
            os.remove(bp)
            deleted_count += 1
        except Exception:
            pass
    return deleted_count, f"Purged {deleted_count} older backups (retained newest {keep_last})."

def get_backup_metadata(backup_path: str) -> dict:
    """Returns human-readable info for a backup file."""
    if not os.path.exists(backup_path):
        return {}
    stat = os.stat(backup_path)
    size_bytes = stat.st_size
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "filename": os.path.basename(backup_path),
        "filepath": backup_path,
        "size_bytes": size_bytes,
        "size_str": f"{size_bytes / 1_048_576:.2f} MB" if size_bytes >= 1_048_576 else f"{size_bytes / 1024:.1f} KB",
        "mtime": mtime
    }
