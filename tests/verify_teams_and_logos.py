import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import dearpygui.dearpygui as dpg

from src.model.squads_db import SquadsSession
from src.core.assets import AssetManager
from src.core.schema import get_team_name
from src.core.team_mappings import get_parent_club_id

def main():
    print("Initializing test...")
    squad_file = "Squads20261023213623126"
    if not os.path.exists(squad_file):
        print(f"Error: {squad_file} not found")
        sys.exit(1)

    session = SquadsSession()
    success, msg = session.load_squads_file(squad_file)
    if not success:
        print(f"Failed to load squads file: {msg}")
        sys.exit(1)
    print("Database parsed successfully.")
    
    # Check teams
    teams = session.teams_cache
    print(f"Total teams loaded: {len(teams)}")
    
    # Key teams to verify:
    # 243: Real Madrid
    # 241: FC Barcelona
    # 10: Manchester City
    # 1: Arsenal
    # 21: FC Bayern München
    # 5: Chelsea
    # 240: Atlético de Madrid
    # 116311: Real Madrid CF (Women) -> parent 243
    # 116310: FC Barcelona (Women) -> parent 241
    
    expected = {
        243: {"name": "Real Madrid", "min_roster": 20, "stars": ["Mbappé", "Bellingham", "Vinícius"]},
        241: {"name": "FC Barcelona", "min_roster": 20, "stars": ["Lewandowski", "González López", "Yamal"]},
        10: {"name": "Manchester City", "min_roster": 20, "stars": ["Haaland", "De Bruyne", "Rodri"]},
        1: {"name": "Arsenal", "min_roster": 20, "stars": ["Saka", "Ødegaard"]},
        21: {"name": "FC Bayern München", "min_roster": 20, "stars": ["Kane", "Musiala"]},
        5: {"name": "Chelsea", "min_roster": 25, "stars": ["Palmer"]},
        240: {"name": "Atlético de Madrid", "min_roster": 20, "stars": ["Griezmann"]},
    }
    
    teams_by_id = {t["teamid"]: t for t in teams}
    
    all_passed = True
    for tid, info in expected.items():
        if tid not in teams_by_id:
            print(f"[FAIL] Team ID {tid} ({info['name']}) not found in teams!")
            all_passed = False
            continue
        team = teams_by_id[tid]
        roster_pids = team.get("roster", [])
        roster = [session.players_lookup.get(pid, {"playerid": pid, "name": f"Player #{pid}"}) for pid in roster_pids]
        print(f"[OK] Found Team {tid}: {team['name']} | Stadium: {team.get('stadium', 'N/A')} | Manager: {team.get('manager_name', 'N/A')} | Roster size: {len(roster)}")
        
        if len(roster) < info["min_roster"]:
            print(f"  [WARN] Roster size {len(roster)} < expected {info['min_roster']}")
            all_passed = False
            
        roster_names = [p.get("name", "") for p in roster]
        for star in info["stars"]:
            # fuzzy check or direct check
            found = any(star.lower() in rn.lower() or rn.lower() in star.lower() for rn in roster_names)
            if not found:
                # check surname or partial
                parts = star.split()
                found = any(parts[-1].lower() in rn.lower() for rn in roster_names)
            if found:
                print(f"  [OK] Star player verified: {star}")
            else:
                print(f"  [FAIL] Star player MISSING: {star} (Found sample: {roster_names[:6]}...)")
                all_passed = False

    # Check Women's teams parent ID
    assert get_parent_club_id(116311) == 243, "Real Madrid Women parent ID mismatch"
    assert get_parent_club_id(116310) == 241, "Barcelona Women parent ID mismatch"
    assert get_parent_club_id(116003) == 1, "Arsenal Women parent ID mismatch"
    assert get_parent_club_id(116004) == 5, "Chelsea Women parent ID mismatch"
    assert get_parent_club_id(116009) == 11, "Manchester Utd Women parent ID mismatch"
    print("[OK] Women's parent club IDs verified.")

    # Check that Serie A clubs Lazio and Atalanta are clean men's clubs
    lazio = teams_by_id[115536]
    atalanta = teams_by_id[115682]
    assert "women" not in lazio["name"].lower(), f"Lazio incorrectly marked as women: {lazio['name']}"
    assert "women" not in atalanta["name"].lower(), f"Atalanta incorrectly marked as women: {atalanta['name']}"
    print(f"[OK] Serie A men's clubs verified clean: {lazio['name']} (ID {lazio['teamid']}), {atalanta['name']} (ID {atalanta['teamid']})")

    # Check AssetManager
    dpg.create_context()
    with dpg.texture_registry(tag="app_texture_registry"):
        pass

    assets = AssetManager()
    assets.init_dpg_textures()
    # Test club crest loading for primary clubs
    for tid in [243, 241, 10, 1, 21, 5, 240, 116311]:
        # Sync get or queued async
        tname = get_team_name(tid)
        tex = assets.get_club_texture(tid, tname)
        print(f"Crest request for TID {tid} ({tname}): Texture {tex}")

    dpg.destroy_context()
    
    if all_passed:
        print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    else:
        print("\nSOME CHECKS FAILED - REVIEW LOGS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    main()
