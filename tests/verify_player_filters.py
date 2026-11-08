import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import dearpygui.dearpygui as dpg
from src.ui.app import SquadEditorApp


def main():
    print("Initializing Multi-Criteria Player Filters verification...")
    dpg.create_context()
    app = SquadEditorApp()
    app._setup_theme()
    app._build_ui()

    squad_file = "Squads20261023213623126"
    assert os.path.exists(squad_file), f"{squad_file} not found"

    ok, msg = app.session.load_squads_file(squad_file)
    assert ok, f"Failed to load squads: {msg}"

    app._populate_club_combo()
    app._on_filter_players()

    total_all = len(app.filtered_players)
    print(f"[OK] Total initial players loaded: {total_all:,}")
    assert total_all > 15000, "Expected > 15,000 players"
    assert len(app.session.all_leagues) >= 50, f"Expected >= 50 leagues, got {len(app.session.all_leagues)}"
    assert len(app.session.all_nations) >= 140, f"Expected >= 140 nations, got {len(app.session.all_nations)}"
    print(f"[OK] Indexed {len(app.session.all_leagues)} leagues & {len(app.session.all_nations)} nations")

    # 1. Test League Filter + Club Cascade
    app._on_change_league_filter(None, "LALIGA EA SPORTS")
    laliga_players = len(app.filtered_players)
    print(f"[OK] LALIGA EA SPORTS filter: {laliga_players} players")
    assert 300 < laliga_players < 1200, f"Unexpected LaLiga player count: {laliga_players}"

    # 2. Test Club Filter inside League
    app._on_change_club_filter(None, "Real Madrid")
    rm_players = [p["name"] for p in app.filtered_players]
    print(f"[OK] Real Madrid filter: {len(rm_players)} players (Top: {rm_players[:4]})")
    assert len(rm_players) == 25, f"Expected 25 Real Madrid players, got {len(rm_players)}"

    # 3. Test Exact Position + Foot + Rating Range
    app._on_clear_player_search()
    app._on_change_pos_filter(None, "RW")
    app._on_change_foot_filter(None, "Left")
    app._on_change_min_ovr(None, 84)
    app._on_change_max_ovr(None, 92)
    rw_left_stars = [f"{p['name']} ({p['overall']}, {p['position']})" for p in app.filtered_players]
    print(f"[OK] Left-footed RW (84-92 OVR): {len(rw_left_stars)} matches -> {rw_left_stars[:6]}")
    assert len(rw_left_stars) >= 3, "Expected at least 3 left-footed elite RWs (Salah, Saka, Yamal, etc.)"

    # 4. Test Nation + Age Bracket + Sorting
    app._on_clear_player_search()
    app._on_change_nation_filter(None, "Spain")
    app._on_change_age_filter(None, "U21 (<=21)")
    app._on_change_sort_by(None, "Potential (High -> Low)")
    spain_u21 = [f"{p['name']} (Age {p['age']}, POT {p['potential']})" for p in app.filtered_players]
    print(f"[OK] Spain U21 sorted by Potential: {len(spain_u21)} matches -> Top: {spain_u21[:4]}")
    assert len(spain_u21) > 5, "Expected > 5 Spain U21 players"

    # 5. Test CSV Export of Filtered Players
    csv_out = os.path.join("tests", "temp_spain_u21.csv")
    exp_ok, exp_msg, exp_cnt = app.session.export_players_list_csv(app.filtered_players, csv_out)
    assert exp_ok and exp_cnt == len(spain_u21), f"CSV export failed: {exp_msg}"
    assert os.path.exists(csv_out)
    os.remove(csv_out)
    print(f"[OK] Filtered players CSV export verified ({exp_cnt} rows)")

    # Cleanup auto-backup created during test
    if app.session.backup_path and os.path.exists(app.session.backup_path):
        os.remove(app.session.backup_path)

    dpg.destroy_context()
    print("\nALL MULTI-CRITERIA PLAYER FILTER TESTS PASSED!")


if __name__ == "__main__":
    main()
