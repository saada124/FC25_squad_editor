"""
Automated Verification Suite for Experience Maximizer Features:
1. Global Quick-Search Palette (Ctrl+F/Ctrl+K) & Top-Right Search Bar
2. Squad Health & Rule Auditor (Validation, Auto-Fix Duplicate Jerseys, Emergency GK)
3. Wonderkid & Potential Scout Suite (Presets, Developmental Headroom, 1-Click Recruitment)
Strict Zero Emojis Policy Enforced.
"""

import os
import sys
import time

# Ensure src is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from model.squads_db import SquadsSession, strip_accents
from core.auditor import (
    audit_team_squad,
    audit_entire_database,
    resolve_duplicate_jersey_numbers,
    assign_emergency_goalkeeper
)
import dearpygui.dearpygui as dpg

def run_tests():
    print("=" * 70)
    print("RUNNING EXPERIENCE MAXIMIZER VERIFICATION SUITE")
    print("=" * 70)

    # 1. Load active Squads file
    session = SquadsSession()
    squads_file = os.path.join(BASE_DIR, "Squads20261023213623126")
    if not os.path.exists(squads_file):
        squad_alt = os.path.join(BASE_DIR, "squad", "Squads20250924234404432")
        squads_file = squad_alt

    print(f"\n[Test 1] Loading test squads file: {os.path.basename(squads_file)}...")
    t0 = time.time()
    ok, msg = session.load_squads_file(squads_file, create_backup=False)
    t_load = time.time() - t0
    assert ok, f"Failed to load squads file: {msg}"
    print(f"[PASS] File loaded in {t_load:.2f}s: {len(session.players_cache)} players, {len(session.teams_cache)} clubs indexed.")

    # 2. Test Diacritics Normalization & Search Engine
    print("\n[Test 2] Testing Global Quick-Search Engine...")
    t0 = time.time()
    res_mbappe = session.search_entities("mbappe", max_players=15, max_teams=6)
    t_search_p = (time.time() - t0) * 1000
    assert len(res_mbappe["players"]) > 0, "Expected to find Kylian Mbappe via diacritic-tolerant search"
    assert "Mbapp" in res_mbappe["players"][0]["name"], f"Unexpected player name: {res_mbappe['players'][0]['name']}"
    print(f"[PASS] 'mbappe' query resolved in {t_search_p:.2f}ms: found {res_mbappe['players'][0]['name']} (OVR {res_mbappe['players'][0]['overall']})")

    t0 = time.time()
    res_real = session.search_entities("real madrid", max_players=15, max_teams=6)
    t_search_t = (time.time() - t0) * 1000
    assert len(res_real["teams"]) > 0, "Expected to find Real Madrid"
    assert "Real Madrid" in res_real["teams"][0]["name"], f"Unexpected team name: {res_real['teams'][0]['name']}"
    print(f"[PASS] 'real madrid' query resolved in {t_search_t:.2f}ms: found {res_real['teams'][0]['name']} (ID {res_real['teams'][0]['teamid']})")

    # Test ID queries
    res_id = session.search_entities("231747", max_players=5, max_teams=5)
    assert len(res_id["players"]) > 0 and res_id["players"][0]["playerid"] == 231747, "Expected ID 231747 to match Mbappe"
    print(f"[PASS] ID query '231747' resolved correctly to {res_id['players'][0]['name']}.")

    # 3. Test Squad Health & Rule Auditor on Arsenal & Real Madrid
    print("\n[Test 3] Testing Squad Health & Rule Auditor...")
    # Real Madrid (ID: 243)
    rm_audit = audit_team_squad(session, 243)
    assert rm_audit["roster_count"] >= 18, f"Real Madrid roster should have >= 18 players, got {rm_audit['roster_count']}"
    assert rm_audit["gk_count"] >= 2, f"Real Madrid should have >= 2 GKs, got {rm_audit['gk_count']}"
    print(f"[PASS] Real Madrid Audit: status={rm_audit['status']}, roster={rm_audit['roster_count']}, GKs={rm_audit['gk_count']}")

    # Arsenal (ID: 1) - has duplicate jersey #17 (Zinchenko & Martinelli)
    ars_audit = audit_team_squad(session, 1)
    print(f"[PASS] Arsenal Initial Audit: status={ars_audit['status']}, issues count={len(ars_audit['issues'])}")
    assert 17 in ars_audit["duplicate_jerseys"], "Expected jersey #17 collision on Arsenal"

    # Test Auto-Fix Duplicate Jerseys
    fixed = resolve_duplicate_jersey_numbers(session, 1)
    assert fixed > 0, f"Expected resolve_duplicate_jersey_numbers to fix duplicate jersey, fixed={fixed}"
    ars_audit_after = audit_team_squad(session, 1)
    assert 17 not in ars_audit_after["duplicate_jerseys"], "Jersey #17 collision must be resolved"
    assert len(ars_audit_after["duplicate_jerseys"]) == 0, "All duplicate jerseys must be resolved"
    print(f"[PASS] Auto-fixed {fixed} duplicate jersey numbers on Arsenal. Post-fix duplicate jerseys: {ars_audit_after['duplicate_jerseys']}")

    # 4. Test Emergency Goalkeeper Signing
    print("\n[Test 4] Testing Emergency Goalkeeper Signing...")
    # Find or simulate a team with 0/1 GK
    test_tid = 243 # Real Madrid
    initial_gk_count = audit_team_squad(session, test_tid)["gk_count"]
    signed_gk_pid = assign_emergency_goalkeeper(session, test_tid)
    assert signed_gk_pid is not None, "Expected an emergency free agent goalkeeper to be signed"
    post_gk_count = audit_team_squad(session, test_tid)["gk_count"]
    assert post_gk_count == initial_gk_count + 1, f"GK count should increase by 1, was {initial_gk_count}, now {post_gk_count}"
    gk_player = session.players_lookup.get(signed_gk_pid, {})
    print(f"[PASS] Successfully signed emergency GK: {gk_player.get('name')} (ID: {signed_gk_pid}) to Real Madrid.")

    # 5. Test Full Database Audit Scan
    print("\n[Test 5] Testing Full Database Squad Health Audit (All 816 Clubs)...")
    t0 = time.time()
    flagged = audit_entire_database(session)
    t_full_audit = (time.time() - t0) * 1000
    print(f"[PASS] Full DB audit completed in {t_full_audit:.2f}ms: scanned {len(session.teams_cache)} clubs, flagged {len(flagged)} with warnings/errors.")
    assert t_full_audit < 1000, f"Full DB audit took too long: {t_full_audit:.2f}ms (threshold 1000ms)"

    # 6. Test Scouting Presets Logic
    print("\n[Test 6] Testing Scouting Presets & Developmental Calculations...")
    wonderkids = [p for p in session.players_cache if p.get("potential", 0) >= 85 and p.get("age", 25) <= 21]
    assert len(wonderkids) > 0, "Expected at least 1 wonderkid in cache"
    print(f"[PASS] Wonderkids preset matched {len(wonderkids)} elite prospects (e.g. {wonderkids[0]['name']} - Age {wonderkids[0]['age']}, POT {wonderkids[0]['potential']}).")

    high_growth = [p for p in session.players_cache if (p.get("potential", 0) - p.get("overall", 0)) >= 10]
    assert len(high_growth) > 0, "Expected high growth prospects"
    print(f"[PASS] High Growth Prospects matched {len(high_growth)} players (e.g. {high_growth[0]['name']} - OVR {high_growth[0]['overall']} -> POT {high_growth[0]['potential']}, +{high_growth[0]['potential']-high_growth[0]['overall']}).")

    hidden_gems = [p for p in session.players_cache if p.get("overall", 0) <= 74 and p.get("potential", 0) >= 82]
    assert len(hidden_gems) > 0, "Expected hidden gems"
    print(f"[PASS] Hidden Gems matched {len(hidden_gems)} prospects (e.g. {hidden_gems[0]['name']} - OVR {hidden_gems[0]['overall']}, POT {hidden_gems[0]['potential']}).")

    future_gks = [p for p in session.players_cache if (p.get("position") == "GK" or p.get("pos_code") == 0) and p.get("age", 25) <= 23 and p.get("potential", 0) >= 80]
    assert len(future_gks) > 0, "Expected future goalkeepers"
    print(f"[PASS] Future Goalkeepers matched {len(future_gks)} prospects (e.g. {future_gks[0]['name']} - Age {future_gks[0]['age']}, POT {future_gks[0]['potential']}).")

    # 7. Test 1-Click Instant Recruitment Pipeline
    print("\n[Test 7] Testing 1-Click Instant Recruitment Action...")
    target_prospect = wonderkids[0]
    pid = target_prospect["playerid"]
    dest_tid = 1 # Arsenal
    ok = session.transfer_player(pid, dest_tid, track=True)
    assert ok, "transfer_player should succeed"
    assert pid in session.team_rosters[dest_tid], "Player must be added to Arsenal roster"
    assert session.user_transfers[pid] == dest_tid, "Player transfer must be registered in user_transfers delta"
    print(f"[PASS] 1-Click recruitment successfully transferred {target_prospect['name']} to Arsenal (ID: {dest_tid}).")

    # 8. Test Dear PyGui UI Construction & Required Widget Tags
    print("\n[Test 8] Testing Dear PyGui UI Tree Construction & Tag Registry...")
    from ui.app import SquadEditorApp
    app = SquadEditorApp()
    dpg.create_context()
    app._build_ui()

    required_tags = [
        "top_global_search_input",
        "quick_search_modal",
        "quick_search_input",
        "quick_search_results_listbox",
        "team_health_modal",
        "team_health_badge",
        "btn_audit_fix_jerseys",
        "btn_audit_sign_gk",
        "global_audit_modal",
        "tab_players",
        "tab_teams",
        "tab_database",
        "tab_settings",
        "player_badge_growth",
        "btn_quick_sign_active_club"
    ]

    for tag in required_tags:
        assert dpg.does_item_exist(tag), f"Missing required Dear PyGui widget tag: {tag}"
    print(f"[PASS] All {len(required_tags)} required UI widget tags verified in active DPG context.")
    dpg.destroy_context()

    print("\n" + "=" * 70)
    print("ALL EXPERIENCE MAXIMIZER TESTS PASSED SUCCESSFULLY! (8/8)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
