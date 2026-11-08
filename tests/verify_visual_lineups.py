"""
Automated verification test suite for Visual Starting XI & Lineup Manager in EA Sports FC 25 Squad Editor.
Tests lineup autofit, player swapping, formation switching, tactical sliders, captaincy,
ChangeTracker logging & revert, and Frostbite binary serialization.
"""

import os
import sys

# Ensure repository root is in Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model.squads_db import SquadsSession
from src.core.formations import FORMATIONS, FORMATION_NAMES, DEFAULT_FORMATION, get_formation_slots

def run_verification():
    print("======================================================================")
    print("STARTING TEST: Visual Starting XI & Lineup Manager Verification")
    print("======================================================================")

    session = SquadsSession()
    squad_file = "Squads20261023213623126"
    if not os.path.exists(squad_file):
        print(f"[FAIL] Squad file not found: {squad_file}")
        sys.exit(1)

    ok, msg = session.load_squads_file(squad_file, create_backup=False)
    assert ok, f"Failed to load squads file: {msg}"
    print(f"[PASS] Successfully loaded {squad_file} ({len(session.db.tables)} tables)")

    # 1. Test team_to_ridx mapping for top clubs
    test_clubs = [
        (243, "Real Madrid", 106),
        (241, "Barcelona", 104),
        (10, "Manchester City", 8),
        (1, "Arsenal", 0),
        (21, "Bayern Munich", 17),
        (5, "Chelsea", 4),
        (9, "Liverpool", 7),
    ]

    print("\n--- 1. Testing Team to Row Index (r_idx) Mappings ---")
    for tid, name, expected_ridx in test_clubs:
        ridx = session.team_to_ridx.get(tid)
        assert ridx is not None, f"Team {name} (ID {tid}) not found in team_to_ridx"
        print(f"  [PASS] {name:16s} (ID {tid:3d}) -> r_idx: {ridx:4d}")

    # 2. Test Lineup Autofit & Structure for All Test Clubs
    print("\n--- 2. Testing Lineup Structure & Formation Autofit ---")
    for tid, name, _ in test_clubs:
        lineup = session.get_team_lineup(tid)
        assert lineup is not None, f"Lineup is None for {name}"
        f_name = lineup.get("formation", "")
        xi = lineup.get("starting_xi", [])
        bench = lineup.get("bench", [])
        reserves = lineup.get("reserves", [])
        
        assert len(xi) == 11, f"Expected 11 starters for {name}, got {len(xi)}"
        assert len(bench) <= 9, f"Expected <= 9 bench players for {name}, got {len(bench)}"
        
        # Verify slot 0 is a goalkeeper
        gk_pid = xi[0]
        gk_pdata = session.players_lookup.get(gk_pid, {})
        gk_pos = gk_pdata.get("pos_code", -1)
        assert gk_pos == 0, f"Expected GK (pos_code 0) at slot 0 for {name}, got {gk_pos}"
        
        # Verify no duplicate players between starting_xi, bench, and reserves
        all_assigned = xi + bench + reserves
        assert len(all_assigned) == len(set(all_assigned)), f"Duplicate player IDs found in lineup for {name}"
        
        print(f"  [PASS] {name:16s} | Formation: {f_name:10s} | Starters: {len(xi)} | Bench: {len(bench)} | Reserves: {len(reserves)}")

    # 3. Test Starter-to-Starter Swap & ChangeTracker Revert
    print("\n--- 3. Testing Starter-to-Starter Tactical Swap & Revert ---")
    rm_id = 243
    rm_lineup = session.get_team_lineup(rm_id)
    orig_slot1 = rm_lineup["starting_xi"][1]
    orig_slot2 = rm_lineup["starting_xi"][2]
    name_slot1 = session.players_lookup[orig_slot1]["name"]
    name_slot2 = session.players_lookup[orig_slot2]["name"]
    
    swap_ok, swap_msg = session.swap_lineup_players(rm_id, "starting_xi", 1, "starting_xi", 2)
    assert swap_ok, f"Swap failed: {swap_msg}"
    assert rm_lineup["starting_xi"][1] == orig_slot2, "Slot 1 did not receive player 2"
    assert rm_lineup["starting_xi"][2] == orig_slot1, "Slot 2 did not receive player 1"
    print(f"  [PASS] Swapped {name_slot1} with {name_slot2}: {swap_msg}")
    
    # Verify ChangeTracker
    assert session.change_tracker.count >= 1, "ChangeTracker did not record swap"
    latest_ch = session.change_tracker.changes[-1]
    assert latest_ch.category == "lineup", f"Expected category 'lineup', got {latest_ch.category}"
    print(f"  [PASS] ChangeTracker recorded: {latest_ch.title} | {latest_ch.new_display}")
    
    # Revert swap
    revert_ok = latest_ch.revert_fn()
    assert rm_lineup["starting_xi"][1] == orig_slot1, "Revert failed to restore slot 1"
    assert rm_lineup["starting_xi"][2] == orig_slot2, "Revert failed to restore slot 2"
    print(f"  [PASS] Reverted swap cleanly: Slot 1 is once again {name_slot1}")

    # 4. Test Starter-to-Bench Substitution & Revert
    print("\n--- 4. Testing Starter-to-Bench Substitution & Revert ---")
    st_pid = rm_lineup["starting_xi"][9]
    sub_pid = rm_lineup["bench"][0]
    st_name = session.players_lookup[st_pid]["name"]
    sub_name = session.players_lookup[sub_pid]["name"]
    
    sub_ok, sub_msg = session.swap_lineup_players(rm_id, "starting_xi", 9, "bench", 0)
    assert sub_ok, f"Substitution failed: {sub_msg}"
    assert rm_lineup["starting_xi"][9] == sub_pid, "Starter slot did not receive substitute"
    assert rm_lineup["bench"][0] == st_pid, "Bench slot did not receive starter"
    print(f"  [PASS] Substituted {st_name} with {sub_name}: {sub_msg}")
    
    # Revert substitution
    latest_ch = session.change_tracker.changes[-1]
    latest_ch.revert_fn()
    assert rm_lineup["starting_xi"][9] == st_pid, "Revert failed to restore starter"
    assert rm_lineup["bench"][0] == sub_pid, "Revert failed to restore bench"
    print(f"  [PASS] Reverted substitution cleanly: Starter is once again {st_name}")

    # 5. Test Formation Switching & mDGw.MZIF String Persistence
    print("\n--- 5. Testing Formation Switching & mDGw.MZIF Persistence ---")
    orig_form = rm_lineup["formation"]
    target_form = "4-3-3"
    form_ok, form_msg = session.set_team_formation(rm_id, target_form)
    assert form_ok, f"Failed to set formation: {form_msg}"
    assert rm_lineup["formation"] == target_form, "Lineup formation did not update"
    
    # Verify raw mDGw table byte content
    r_idx = session.team_to_ridx[rm_id]
    mdgw = session.db.tables_map["mDGw"]
    raw_mzif = mdgw.columns_map["MZIF"].decode_value(mdgw.records[r_idx])
    assert raw_mzif == target_form, f"Raw mDGw MZIF was '{raw_mzif}', expected '{target_form}'"
    print(f"  [PASS] Formation updated to {target_form} and persisted into raw mDGw.MZIF: {raw_mzif}")
    
    # Revert formation
    form_ch = session.change_tracker.changes[-1]
    form_ch.revert_fn()
    assert rm_lineup["formation"] == orig_form, "Revert failed to restore original formation"
    raw_mzif_after = mdgw.columns_map["MZIF"].decode_value(mdgw.records[r_idx])
    assert raw_mzif_after == orig_form, f"Raw mDGw MZIF after revert was '{raw_mzif_after}', expected '{orig_form}'"
    print(f"  [PASS] Reverted formation cleanly to {orig_form}: raw mDGw is {raw_mzif_after}")

    # 6. Test Tactical Sliders & Persistence
    print("\n--- 6. Testing Tactical Sliders (mDGw Gtld, Iwmo, DahS) ---")
    orig_tactics = session.get_team_tactics(rm_id)
    print(f"  [INFO] Original Tactics: {orig_tactics}")
    
    new_depth = 0.85
    new_tempo = 0.40
    new_passing = 0.75
    tact_ok, tact_msg = session.set_team_tactics(rm_id, defensive_depth=new_depth, buildup_tempo=new_tempo, passing_directness=new_passing)
    assert tact_ok, f"Failed to set tactics: {tact_msg}"
    
    updated_tactics = session.get_team_tactics(rm_id)
    assert abs(updated_tactics["defensive_depth"] - new_depth) < 0.01, f"Depth mismatch: {updated_tactics['defensive_depth']}"
    assert abs(updated_tactics["buildup_tempo"] - new_tempo) < 0.01, f"Tempo mismatch: {updated_tactics['buildup_tempo']}"
    assert abs(updated_tactics["passing_directness"] - new_passing) < 0.01, f"Passing mismatch: {updated_tactics['passing_directness']}"
    print(f"  [PASS] Updated tactical sliders: Depth={new_depth}, Tempo={new_tempo}, Passing={new_passing}")

    # 7. Test Captain Persistence in lyxL.WLKn
    print("\n--- 7. Testing Team Captain Persistence in lyxL.WLKn ---")
    orig_cap = updated_tactics["captain_id"]
    new_cap = rm_lineup["starting_xi"][5] # Midfielder
    new_cap_name = session.players_lookup[new_cap]["name"]
    
    cap_ok, cap_msg = session.set_team_captain(rm_id, new_cap)
    assert cap_ok, f"Failed to set captain: {cap_msg}"
    
    lyxl = session.db.tables_map["lyxL"]
    raw_cap = int(lyxl.columns_map["WLKn"].decode_value(lyxl.records[r_idx]) or 0)
    assert raw_cap == new_cap, f"Raw lyxL WLKn was {raw_cap}, expected {new_cap}"
    print(f"  [PASS] Team captain set to {new_cap_name} (PID {new_cap}) and verified in raw lyxL.WLKn: {raw_cap}")

    # 8. Test Binary Export & Reload Cycle
    print("\n--- 8. Testing Native Binary Save & Reload Cycle ---")
    test_export_path = "tests/test_lineup_export.squads"
    try:
        save_ok, save_msg = session.save_squads_file(test_export_path)
        assert save_ok, f"Failed to export squads file: {save_msg}"
        assert os.path.exists(test_export_path), "Exported file does not exist on disk"
        file_size = os.path.getsize(test_export_path)
        assert file_size > 1_000_000, f"Exported file is suspiciously small ({file_size} bytes)"
        print(f"  [PASS] Exported {file_size:,} bytes to {test_export_path}")
        
        # Reload in a clean session
        new_session = SquadsSession()
        reload_ok, reload_msg = new_session.load_squads_file(test_export_path, create_backup=False)
        assert reload_ok, f"Failed to reload exported squads file: {reload_msg}"
        
        # Verify persisted captain in reloaded session
        reloaded_tactics = new_session.get_team_tactics(rm_id)
        assert reloaded_tactics["captain_id"] == new_cap, f"Reloaded captain was {reloaded_tactics['captain_id']}, expected {new_cap}"
        assert abs(reloaded_tactics["defensive_depth"] - new_depth) < 0.01, "Reloaded depth mismatch"
        print(f"  [PASS] Reloaded session verified: Captain={reloaded_tactics['captain_id']}, Depth={reloaded_tactics['defensive_depth']:.2f}")
    finally:
        if os.path.exists(test_export_path):
            os.remove(test_export_path)
            print(f"  [CLEANUP] Removed temporary test export: {test_export_path}")

    print("\n======================================================================")
    print("ALL TESTS PASSED: Visual Starting XI & Lineup Manager is 100% Verified!")
    print("======================================================================")

if __name__ == "__main__":
    run_verification()
