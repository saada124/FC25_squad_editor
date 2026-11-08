import os
import sys
import time
import dearpygui.dearpygui as dpg

sys.path.insert(0, ".")

from src.core.assets import AssetManager
from src.core.team_mappings import get_parent_club_id
from src.model.squads_db import SquadsSession

print("=" * 70)
print("STARTING TEST: Club Crest & Logo Loading Pipeline Verification")
print("=" * 70)

# Setup Dear PyGui Context
dpg.create_context()
assets = AssetManager()
assets.init_dpg_textures()

# --- 1. Test Versioned Texture Swapping (Zero Alias Collision) ---
print("\n--- 1. Testing Dear PyGui Versioned Texture Swapping ---")
test_tid = 999999
fallback_path = os.path.join(assets.crests_dir, f"fallback_{test_tid}.png")
assets._draw_club_crest_badge(fallback_path, test_tid, "Test FC")

# First load (Version 1)
tag_v1 = assets._load_club_texture_from_file(test_tid, fallback_path)
assert tag_v1 == f"tex_club_{test_tid}_v1", f"Expected v1 tag, got {tag_v1}"
assert dpg.does_item_exist(tag_v1), "Texture v1 must exist in DPG"
print(f"  [PASS] Initial texture registered: {tag_v1}")

# Create image widget pointing to v1
with dpg.window(label="Test Window"):
    img_widget = dpg.add_image(tag_v1, tag="test_crest_widget", width=70, height=70)

# Second load (simulate download completion -> Version 2)
tag_v2 = assets._load_club_texture_from_file(test_tid, fallback_path)
assert tag_v2 == f"tex_club_{test_tid}_v2", f"Expected v2 tag, got {tag_v2}"
assert dpg.does_item_exist(tag_v2), "Texture v2 must exist in DPG"

# Rebind UI widget to tag_v2
dpg.configure_item("test_crest_widget", texture_tag=tag_v2)

# Now cleanup old version
assets.cleanup_old_club_texture(test_tid)
assert not dpg.does_item_exist(tag_v1), "Old texture v1 must be deleted to free GPU memory"
print(f"  [PASS] Successfully updated to {tag_v2} with zero alias collision!")

# Clean up test artifacts
if os.path.exists(fallback_path):
    os.remove(fallback_path)

# --- 2. Testing Multi-Tier CDN Downloader for Clubs ---
print("\n--- 2. Testing Multi-Tier CDN Endpoints ---")
test_clubs = [
    (243, "Real Madrid"),
    (113984, "Stal Mielec"),
    (113004, "Germany Women"),
    (116428, "Levante Badalona Women")
]

for tid, name in test_clubs:
    local_path = os.path.join(assets.crests_dir, f"c{tid}.png")
    # Queue download
    assets._queue_club_download(tid, local_path)
    
# Wait for async worker threads to finish
time.sleep(3.5)

# Process completed textures on main thread
loaded_clubs = []
assets.on_asset_loaded = lambda atype, id_val, tag: loaded_clubs.append((atype, id_val, tag))
assets.process_pending_textures()

for tid, name in test_clubs:
    local_path = os.path.join(assets.crests_dir, f"c{tid}.png")
    exists = os.path.exists(local_path) and os.path.getsize(local_path) > 500
    assert exists, f"Crest for {name} (ID {tid}) failed to download from Multi-Tier CDNs"
    print(f"  [PASS] Verified crest for {name} (ID {tid}): {os.path.getsize(local_path):,} bytes on disk")

# --- 3. Testing get_club_texture Instant Return & Texture Version Binding ---
print("\n--- 3. Testing get_club_texture with On-Demand Caching ---")
tex_rm = assets.get_club_texture(243, "Real Madrid")
assert dpg.does_item_exist(tex_rm), f"Texture {tex_rm} must be active in DPG"
print(f"  [PASS] get_club_texture(243) returned active DPG texture: {tex_rm}")

# --- 4. Testing Batch Crest Downloader & Progress Tracking ---
print("\n--- 4. Testing Batch Crest Downloader ---")
dummy_teams = [
    {"teamid": 243, "name": "Real Madrid"},
    {"teamid": 10, "name": "Manchester City"},
    {"teamid": 1, "name": "Arsenal"},
    {"teamid": 21, "name": "Bayern Munich"},
    {"teamid": 241, "name": "Barcelona"},
]

progress_updates = []
completion_data = []

ok, msg = assets.start_batch_crest_download(
    dummy_teams,
    on_progress=lambda p: progress_updates.append(dict(p)),
    on_complete=lambda p: completion_data.append(dict(p))
)
assert ok, f"Batch download failed to start: {msg}"

# Wait for dummy batch to finish
time.sleep(2.0)
assert len(completion_data) > 0, "Batch download should have completed"
final_p = completion_data[0]
print(f"  [PASS] Batch progress: {final_p['completed']}/{final_p['total']} processed, {final_p['skipped']} already cached")

# --- 5. Clean up DPG context ---
dpg.destroy_context()

print("\n" + "=" * 70)
print("ALL TESTS PASSED: Club Crest & Logo Pipeline is 100% Verified!")
print("=" * 70)
