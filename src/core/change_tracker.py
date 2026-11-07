"""
Centralized Change Tracking & Staging Engine for EA SPORTS FC 25 Squad Editor.
Tracks session modifications across Players, Clubs, Transfers, and Database Tables
with granular individual revert ('X') support.
"""

import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class ChangeEntry:
    id: str
    category: str  # "player", "transfer", "club", "manager", "table"
    title: str     # e.g. "Mohamed Salah (ID 209331)"
    entity_id: Any
    field_name: str # e.g. "overallrating", "teamid", "stadium"
    field_label: str # e.g. "Overall Rating", "Club Transfer", "Home Stadium"
    old_value: Any
    new_value: Any
    old_display: str # e.g. "89", "Liverpool", "Anfield"
    new_display: str # e.g. "94", "Real Madrid", "New Anfield"
    timestamp: float = field(default_factory=time.time)
    revert_fn: Optional[Callable[[], bool]] = None

    def get_time_str(self) -> str:
        return time.strftime("%H:%M:%S", time.localtime(self.timestamp))

    @property
    def change_id(self) -> str:
        return self.id

    @property
    def old_val(self) -> Any:
        return self.old_value

    @property
    def new_val(self) -> Any:
        return self.new_value


class ChangeTracker:
    """
    Maintains an active queue of all unpersisted modifications in the current session.
    Coalesces consecutive edits to the same field and provides 1-click revert.
    """
    def __init__(self):
        self.changes: List[ChangeEntry] = []
        self._key_map: Dict[tuple, int] = {}

    def record_change(
        self,
        category: str,
        title: str,
        entity_id: Any,
        field_name: str,
        field_label: str,
        old_val: Any,
        new_val: Any,
        revert_fn: Optional[Callable[[], bool]] = None,
        old_disp: Optional[str] = None,
        new_disp: Optional[str] = None,
    ) -> Optional[ChangeEntry]:
        """
        Records a modification. If the field was already modified, coalesces the new value
        while preserving the original baseline old_value.
        """
        if str(old_val).strip() == str(new_val).strip():
            return None

        key = (category, str(entity_id), str(field_name))

        if key in self._key_map:
            idx = self._key_map[key]
            if idx < len(self.changes):
                existing = self.changes[idx]
                # If modified back to the exact initial value, remove from pending changes
                if str(existing.old_value).strip() == str(new_val).strip():
                    del self.changes[idx]
                    self._rebuild_key_map()
                    return None
                else:
                    existing.new_value = new_val
                    existing.new_display = str(new_disp if new_disp is not None else new_val)
                    existing.timestamp = time.time()
                    return existing

        c_id = str(uuid.uuid4())[:8]
        entry = ChangeEntry(
            id=c_id,
            category=category,
            title=title,
            entity_id=entity_id,
            field_name=field_name,
            field_label=field_label,
            old_value=old_val,
            new_value=new_val,
            old_display=str(old_disp if old_disp is not None else old_val),
            new_display=str(new_disp if new_disp is not None else new_val),
            revert_fn=revert_fn,
        )
        self.changes.append(entry)
        self._key_map[key] = len(self.changes) - 1
        return entry

    def _rebuild_key_map(self):
        self._key_map.clear()
        for idx, c in enumerate(self.changes):
            key = (c.category, str(c.entity_id), str(c.field_name))
            self._key_map[key] = idx

    def revert(self, change_id: str) -> bool:
        """
        Reverts a single change by executing its rollback callback and removing it from the changelist.
        """
        for idx, c in enumerate(self.changes):
            if c.id == change_id:
                ok = True
                if c.revert_fn:
                    try:
                        ok = bool(c.revert_fn())
                    except Exception:
                        ok = False
                del self.changes[idx]
                self._rebuild_key_map()
                return ok
        return False

    def revert_all(self) -> int:
        """
        Reverts all pending changes in reverse chronological order.
        """
        count = 0
        for c in reversed(list(self.changes)):
            if c.revert_fn:
                try:
                    c.revert_fn()
                    count += 1
                except Exception:
                    pass
        self.clear()
        return count

    def clear(self):
        """Clears all tracked changes (called after successful file save or fresh file load)."""
        self.changes.clear()
        self._key_map.clear()

    def get_changes(self) -> List[ChangeEntry]:
        """Returns a snapshot of all active changes."""
        return list(self.changes)

    get_all_changes = get_changes

    @property
    def count(self) -> int:
        return len(self.changes)

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0
