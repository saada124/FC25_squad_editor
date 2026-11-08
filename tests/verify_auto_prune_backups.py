import os
import sys
import shutil
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.backup import (
    create_load_backup,
    list_folder_backups,
    purge_old_backups,
    get_folder_backups_summary,
    get_backup_metadata
)
from src.model.squads_db import SquadsSession
from src.core.settings import AppSettings


def main():
    print("Initializing Auto-Prune Backup Verification...")

    # Create a dummy squads file for isolated testing
    test_dir = os.path.join("tests", "temp_backup_test")
    os.makedirs(test_dir, exist_ok=True)
    dummy_squad = os.path.join(test_dir, "SquadsDummy")
    with open(dummy_squad, "wb") as f:
        f.write(b"FIFA_TEST_SQUADS_PAYLOAD_DUMMY_DATA" * 100)

    try:
        # 1. Test create_load_backup with max_retain = 3
        print("\n--- Test 1: Sequential Backup Creation with max_retain=3 ---")
        created_paths = []
        for i in range(6):
            time.sleep(1.05)  # Ensure distinct timestamp
            bp, msg = create_load_backup(dummy_squad, auto_prune=True, max_retain=3)
            created_paths.append(bp)
            summary = get_folder_backups_summary(dummy_squad)
            print(f"Created #{i+1}: {os.path.basename(bp)} | Total in folder: {summary['count']} ({summary['total_size_str']})")

        backups = list_folder_backups(dummy_squad)
        assert len(backups) == 3, f"Expected exactly 3 backups retained, found {len(backups)}"
        print(f"[OK] Max retain of 3 verified! Folder only holds 3 backups.")

        # Check that the 3 remaining backups are indeed the newest ones
        newest_expected = [os.path.basename(p) for p in created_paths[-3:]]
        actual_names = [os.path.basename(p) for p in backups]
        for name in actual_names:
            assert name in newest_expected, f"Found older unexpected backup: {name}"
        print("[OK] Retained backups are the newest ones.")

        # 2. Test get_folder_backups_summary
        print("\n--- Test 2: Storage Summary Metrics ---")
        summary = get_folder_backups_summary(dummy_squad)
        assert summary["count"] == 3
        assert summary["total_bytes"] > 0
        print(f"[OK] Summary metrics: {summary['count']} files, {summary['total_size_str']}")

        # 3. Test lowering limit to 1
        print("\n--- Test 3: Lowering Retention Limit (Purge to 1) ---")
        purged, purge_msg = purge_old_backups(dummy_squad, keep_last=1)
        assert purged == 2, f"Expected 2 backups purged, got {purged}"
        remaining = list_folder_backups(dummy_squad)
        assert len(remaining) == 1, f"Expected 1 backup remaining, got {len(remaining)}"
        print(f"[OK] Purge succeeded: {purge_msg} (Remaining: 1)")

        # 4. Test SquadsSession with real squad file and auto_prune
        print("\n--- Test 4: SquadsSession load_squads_file with auto-pruning ---")
        real_squad = "Squads20261023213623126"
        if os.path.exists(real_squad):
            session = SquadsSession()
            ok, msg = session.load_squads_file(real_squad, create_backup=True, max_backups_retain=2)
            assert ok
            real_backups = list_folder_backups(real_squad)
            print(f"[OK] Real squads load created backup: {os.path.basename(session.backup_path)}")
            print(f"[OK] Total real backups in directory: {len(real_backups)} (enforced max: 2)")
            assert len(real_backups) <= 2

            # Clean up the test backup created for real_squad
            for b in real_backups:
                if os.path.exists(b):
                    os.remove(b)
            print("[OK] Cleaned up real squads test backup.")

        print("\nALL AUTO-PRUNING VERIFICATION TESTS PASSED SUCCESSFULLY!")

    finally:
        # Cleanup temp directory
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    main()
