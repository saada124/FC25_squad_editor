import os
import csv
import sys
from typing import Dict, List, Tuple, Any, Optional

try:
    from core.backup import create_load_backup, list_folder_backups, purge_old_backups, get_folder_backups_summary
    from core.fbchunks import FBChunksContainer
    from core.db_codec import FIFADatabase, DBTable, DBColumn, get_bits, set_bits
    from core.schema import get_table_display_name, get_column_display_name, get_column_clean_name, get_position_name, get_team_name, get_nation_name, classify_column, TEAM_NAMES, POSITION_NAMES, NATION_NAMES
    from core.team_mappings import format_team_display_name, SECONDARY_TO_PRIMARY_TEAMS, is_women_team, get_parent_club_id
    from core.change_tracker import ChangeTracker, ChangeEntry
except ImportError:
    from src.core.backup import create_load_backup, list_folder_backups, purge_old_backups, get_folder_backups_summary
    from src.core.fbchunks import FBChunksContainer
    from src.core.db_codec import FIFADatabase, DBTable, DBColumn, get_bits, set_bits
    from src.core.schema import get_table_display_name, get_column_display_name, get_column_clean_name, get_position_name, get_team_name, get_nation_name, classify_column, TEAM_NAMES, POSITION_NAMES, NATION_NAMES
    from src.core.team_mappings import format_team_display_name, SECONDARY_TO_PRIMARY_TEAMS, is_women_team, get_parent_club_id
    from src.core.change_tracker import ChangeTracker, ChangeEntry

def get_base_dir() -> str:
    """Returns application directory whether running as script or frozen PyInstaller exe."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return getattr(sys, "_MEIPASS")
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SquadsSession:
    """
    High-level manager for an active FC 25 Squads save file.
    Coordinates backup creation, container parsing, table manipulation, exact export,
    and metadata indexing with 25,000+ real players and clubs.
    """
    def __init__(self):
        self.filepath: Optional[str] = None
        self.backup_path: Optional[str] = None
        self.container = FBChunksContainer()
        self.db = FIFADatabase()
        self.is_loaded = False
        
        # High-level entity caches
        self.players_lookup: Dict[int, Dict[str, Any]] = {}
        self.players_cache: List[Dict[str, Any]] = []
        self.teams_cache: List[Dict[str, Any]] = []
        self.team_rosters: Dict[int, List[int]] = {}
        self.user_transfers: Dict[int, int] = {}
        self.base_players_list: List[int] = []
        self.base_players_records: List[Dict[str, Any]] = []
        self.team_squad_roles: Dict[int, Dict[str, int]] = {}
        self.player_jerseys: Dict[int, int] = {}
        self.user_jerseys: Dict[int, int] = {}
        self.base_team_lookup: Dict[int, int] = {}
        self.base_jersey_lookup: Dict[int, int] = {}
        self.team_to_league: Dict[int, str] = {}
        self.all_leagues: List[str] = []
        self.all_nations: List[str] = []
        self.change_tracker: ChangeTracker = ChangeTracker()

        # Pre-load player presets from Live Editor database
        self._load_player_presets()

    def _load_player_presets(self):
        """Loads and merges cards.csv and base_players.csv from Live Editor presets."""
        base_dir = get_base_dir()
        
        # Check multiple search locations for player_presets
        search_dirs = [
            os.path.join(getattr(sys, "_MEIPASS", ""), "player_presets"),
            os.path.join(base_dir, "player_presets"),
            os.path.join(base_dir, "FC25LEv25.4.2", "player_presets"),
            os.path.join(os.getcwd(), "FC25LEv25.4.2", "player_presets"),
            os.path.join(os.getcwd(), "player_presets"),
            os.path.join(os.path.dirname(sys.executable), "player_presets"),
            os.path.join(os.path.dirname(sys.executable), "FC25LEv25.4.2", "player_presets"),
        ]
        
        presets_dir = None
        for d in search_dirs:
            if os.path.exists(os.path.join(d, "cards.csv")):
                presets_dir = d
                break
                
        if not presets_dir:
            return

        cards_path = os.path.join(presets_dir, "cards.csv")
        base_path = os.path.join(presets_dir, "base_players.csv")
        
        # 1. Ingest cards.csv (all 26,219 cards with real human names)
        if os.path.exists(cards_path):
            try:
                with open(cards_path, "r", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        try:
                            pid = int(r.get("playerid", 0))
                            if pid <= 0: continue
                            # Prefer Normal/base card versions for primary identity
                            if pid not in self.players_lookup or r.get("revision") == "Normal":
                                self.players_lookup[pid] = {
                                    "playerid": pid,
                                    "name": r.get("name", f"Player #{pid}"),
                                    "overall": int(r.get("overallrating", 60)),
                                    "potential": int(r.get("overallrating", 60)),
                                    "pos_code": int(r.get("preferredposition1", -1)),
                                    "weak_foot": int(r.get("weakfootabilitytypecode", 3)),
                                    "skills": int(r.get("skillmoves", 3)),
                                    "height": 182,
                                    "weight": 77,
                                    "foot": "Right",
                                    "teamid": 0,
                                    "club": "Free Agent",
                                    "stats": r
                                }
                        except Exception:
                            continue
            except Exception:
                pass

        # 2. Merge base_players.csv (all 141 physical & technical attributes)
        if os.path.exists(base_path):
            try:
                with open(base_path, "r", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        try:
                            pid = int(r.get("playerid", 0))
                            if pid <= 0: continue
                            self.base_players_list.append(pid)
                            self.base_players_records.append(r)
                            if pid in self.players_lookup:
                                p = self.players_lookup[pid]
                                p["potential"] = int(r.get("potential", p["overall"]))
                                p["height"] = int(r.get("height", 182))
                                p["weight"] = int(r.get("weight", 77))
                                p["foot"] = "Left" if r.get("preferredfoot") == "1" else "Right"
                                for k, v in r.items():
                                    if k not in p["stats"] or not p["stats"][k]:
                                        p["stats"][k] = v
                            else:
                                name = r.get("commonname") or r.get("surname") or f"Player #{pid}"
                                ovr = int(r.get("overallrating", 60))
                                pot = int(r.get("potential", ovr))
                                pos = int(r.get("preferredposition1", -1))
                                self.players_lookup[pid] = {
                                    "playerid": pid,
                                    "name": name,
                                    "overall": ovr,
                                    "potential": pot,
                                    "pos_code": pos,
                                    "weak_foot": int(r.get("weakfootabilitytypecode", 3)),
                                    "skills": int(r.get("skillmoves", 3)),
                                    "height": int(r.get("height", 182)),
                                    "weight": int(r.get("weight", 77)),
                                    "foot": "Left" if r.get("preferredfoot") == "1" else "Right",
                                    "teamid": 0,
                                    "club": "Free Agent",
                                    "stats": r
                                }
                        except Exception:
                            continue
            except Exception:
                pass

        # 3. Ingest player_clubs.json (real clubs, leagues, nations, and playstyles for 17,737+ players)
        clubs_dirs = [
            presets_dir,
            os.path.join(getattr(sys, "_MEIPASS", ""), "player_presets"),
            os.path.join(base_dir, "player_presets"),
            os.path.join(base_dir, "FC25LEv25.4.2", "player_presets"),
            os.path.join(os.getcwd(), "player_presets"),
            os.path.join(os.getcwd(), "FC25LEv25.4.2", "player_presets"),
        ]
        clubs_path = None
        for cd in clubs_dirs:
            if cd and os.path.exists(os.path.join(cd, "player_clubs.json")):
                clubs_path = os.path.join(cd, "player_clubs.json")
                break
        if clubs_path and os.path.exists(clubs_path):
            try:
                import json
                with open(clubs_path, "r", encoding="utf-8") as f:
                    clubs_map = json.load(f)
                for pid_str, cdata in clubs_map.items():
                    pid = int(pid_str)
                    if pid in self.players_lookup:
                        p = self.players_lookup[pid]
                        tid = cdata.get("teamid", 0)
                        cname = cdata.get("club", "Free Agent")
                        # Failsafe routing: if male player is assigned to a secondary/women TID, remap to primary men TID
                        is_female = (p.get("stats", {}).get("gender") == "1" or p.get("gender") == 1 or "women" in cname.lower() or "wsl" in str(cdata.get("league", "")).lower() or "liga f" in str(cdata.get("league", "")).lower())
                        if not is_female and tid in SECONDARY_TO_PRIMARY_TEAMS:
                            tid = SECONDARY_TO_PRIMARY_TEAMS[tid]
                            cname = cname.replace(" (Women)", "").strip()

                        if tid > 0 or cname != "Free Agent":
                            p["teamid"] = tid
                            p["club"] = cname
                            p["base_teamid"] = tid
                            p["base_club"] = cname
                            self.base_team_lookup[pid] = tid
                        lg = cdata.get("league", "")
                        if tid > 0 and lg and tid not in self.team_to_league:
                            self.team_to_league[tid] = lg
                        p["league"] = lg
                        p["nation_name"] = cdata.get("nation", "")
                        p["alt_positions"] = cdata.get("alt_pos", "")
                        p["playstyles_str"] = cdata.get("playstyles", "")
            except Exception:
                pass

        # 4. Ingest player_jerseys.json (authentic kit numbers for 17,737+ real players)
        jerseys_path = None
        for jd in clubs_dirs:
            if jd and os.path.exists(os.path.join(jd, "player_jerseys.json")):
                jerseys_path = os.path.join(jd, "player_jerseys.json")
                break
        if jerseys_path and os.path.exists(jerseys_path):
            try:
                import json
                with open(jerseys_path, "r", encoding="utf-8") as f:
                    j_map = json.load(f)
                for pid_str, num in j_map.items():
                    pid = int(pid_str)
                    num_int = int(num)
                    self.player_jerseys[pid] = num_int
                    self.base_jersey_lookup[pid] = num_int
                    if pid in self.players_lookup:
                        self.players_lookup[pid]["base_jersey"] = num_int
                        self.players_lookup[pid].setdefault("stats", {})["jerseynumber"] = str(num_int)
            except Exception:
                pass

        self._refresh_league_and_nation_lists(self.players_lookup.values())

    def _refresh_league_and_nation_lists(self, player_records):
        """Builds prioritized lists of all unique leagues and nations across the given player records."""
        leagues_set = {p.get("league", "") for p in player_records if p.get("league")}
        nations_set = {p.get("nation_name", "") for p in player_records if p.get("nation_name")}

        top_leagues = [
            "Premier League", "LALIGA EA SPORTS", "Bundesliga", "Serie A Enilive",
            "Ligue 1 McDonald's", "EFL Championship", "MLS", "ROSHN Saudi League",
            "Eredivisie", "Liga Portugal", "Barclays WSL", "Liga F",
            "Frauen-Bundesliga", "Arkema PL", "NWSL"
        ]
        ordered_leagues = [lg for lg in top_leagues if lg in leagues_set]
        ordered_leagues.extend(sorted(leagues_set - set(ordered_leagues)))
        self.all_leagues = ordered_leagues

        top_nations = [
            "England", "France", "Spain", "Germany", "Brazil", "Argentina",
            "Portugal", "Italy", "Netherlands", "Belgium", "Croatia",
            "Uruguay", "Colombia", "United States", "Japan", "Morocco"
        ]
        ordered_nations = [nt for nt in top_nations if nt in nations_set]
        ordered_nations.extend(sorted(nations_set - set(ordered_nations)))
        self.all_nations = ordered_nations

    def load_squads_file(self, filepath: str, create_backup: bool = True, max_backups_retain: int = 10) -> Tuple[bool, str]:
        """
        Loads a squads file.
        IMPORTANT: Immediately creates a duplicate safety copy in the same directory (with auto-pruning).
        """
        try:
            # 1. Immediate Safety Duplicate in same directory with auto-pruning
            if create_backup:
                self.backup_path, backup_msg = create_load_backup(filepath, auto_prune=True, max_retain=max_backups_retain)
            else:
                self.backup_path = None
                if max_backups_retain is not None and max_backups_retain < 999:
                    purge_old_backups(filepath, keep_last=max_backups_retain)
            
            # 2. Parse Frostbite Container & inner DB
            db_payload = self.container.load(filepath)
            self.db.parse(db_payload)
            self.filepath = filepath
            self.is_loaded = True
            
            # 3. Populate all 816 real team names from table lyxL & kISL
            lyxl = self.db.tables_map.get("lyxL")
            kisl = self.db.tables_map.get("kISL")
            col_dmls = kisl.columns_map.get("DmlS") if kisl else None
            if lyxl and "IOSv" in lyxl.columns_map:
                col_tname = lyxl.columns_map["IOSv"]
                for r_idx, rec in enumerate(lyxl.records):
                    tname = col_tname.decode_value(rec)
                    if not tname:
                        continue
                    tid = 0
                    if col_dmls and r_idx < len(kisl.records):
                        try:
                            tid = col_dmls.decode_value(kisl.records[r_idx]) + 1
                        except Exception:
                            tid = 0
                    if tid <= 0:
                        tid = r_idx + 1
                    TEAM_NAMES[tid] = format_team_display_name(tid, tname, r_idx)

            # 4. Index high-level entities
            self._build_indexes()
            self.change_tracker.clear()
            
            status = f"Loaded {len(self.db.tables)} tables. {backup_msg}"
            return True, status
        except Exception as e:
            return False, f"Failed to load squads file: {str(e)}"

    def save_squads_file(self, target_filepath: Optional[str] = None) -> Tuple[bool, str]:
        """
        Repacks and exports the current database into the exact native FBCHUNKS format.
        """
        if not self.is_loaded:
            return False, "No squads file loaded."
            
        save_path = target_filepath or self.filepath
        if not save_path:
            return False, "No target filepath specified."
            
        try:
            rebuilt_db = self.db.serialize()
            total_written = self.container.repack(rebuilt_db, save_path)
            self.filepath = save_path
            self.change_tracker.clear()
            return True, f"Successfully exported {total_written:,} bytes to: {os.path.basename(save_path)}"
        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def _build_indexes(self):
        """Indexes Players and Teams for rapid search and high-level editing."""
        self.players_cache.clear()
        self.teams_cache.clear()
        self.team_rosters.clear()
        
        # 1. Map team player rosters from rIsB (active save transfer delta)
        risb = self.db.tables_map.get("rIsB")
        czum = self.db.tables_map.get("CZUM")
        
        # 2. Extract Stadium Names from kISL
        # In FIFA/FC 25, record r_idx in kISL maps 1:1 to team record r_idx in lyxL
        stadium_names: Dict[int, str] = {}
        kisl = self.db.tables_map.get("kISL")
        if kisl and "fwCQ" in kisl.columns_map:
            col_sname = kisl.columns_map["fwCQ"]
            for r_idx, rec in enumerate(kisl.records):
                try:
                    sname = col_sname.decode_value(rec)
                    if sname:
                        stadium_names[r_idx] = sname.lstrip("_").strip()
                except Exception:
                    pass

        czum_player_rows: Dict[int, int] = {}
        if czum:
            for r_idx, rec in enumerate(czum.records):
                try:
                    pid = get_bits(rec, 356, 18)
                    if pid > 0:
                        czum_player_rows[pid] = r_idx
                except Exception:
                    pass

        risb_player_rows: Dict[int, int] = {}
        if risb:
            for r_idx, rec in enumerate(risb.records):
                try:
                    pid = get_bits(rec, 18, 18)
                    if pid > 0:
                        risb_player_rows[pid] = r_idx
                except Exception:
                    pass

        # 3. Build Players Cache
        # Ingest from self.players_lookup (all 25,369 players with real official clubs)
        for pid, pdata in self.players_lookup.items():
            if pid in self.user_transfers:
                tid = self.user_transfers[pid]
                club_name = get_team_name(tid) if tid > 0 else "Free Agent"
                pdata["teamid"] = tid
                pdata["club"] = club_name
            else:
                tid = pdata.get("teamid", 0)
                club_name = pdata.get("club") or (get_team_name(tid) if tid > 0 else "Free Agent")

            # Add to team roster
            if tid > 0:
                if tid not in self.team_rosters:
                    self.team_rosters[tid] = []
                self.team_rosters[tid].append(pid)

            risb_row = risb_player_rows.get(pid)
            czum_row = czum_player_rows.get(pid)
            ovr = pdata["overall"]
            pot = pdata["potential"]
            pos_code = pdata["pos_code"]

            # If present in active squads CZUM and RrqT, read live database values
            if czum and czum_row is not None and czum_row < len(czum.records):
                rec = czum.records[czum_row]
                db_ovr = get_bits(rec, 877, 7)
                db_pot = get_bits(rec, 159, 7)
                db_pos = get_bits(rec, 441, 7)
                if db_ovr > 0:
                    ovr = db_ovr
                if db_pot > 0:
                    pot = db_pot
                if db_pos >= 0:
                    pos_code = db_pos

                rrqt = self.db.tables_map.get("RrqT")
                if rrqt and czum_row < len(rrqt.records):
                    db_jersey = get_bits(rrqt.records[czum_row], 23, 7)
                    if 1 <= db_jersey <= 99:
                        self.player_jerseys[pid] = db_jersey
                        pdata.setdefault("stats", {})["jerseynumber"] = str(db_jersey)

            club_name = get_team_name(tid) if tid > 0 else "Free Agent"
            pos_name = get_position_name(pos_code)
            
            stats = pdata.get("stats", {})
            if "jerseynumber" not in stats or not stats["jerseynumber"]:
                stats["jerseynumber"] = str(self.get_player_jersey_number(pid))
            b_day = 1
            b_mon = 1
            age_val = 25
            bdate_str = str(stats.get("birthdate", "")).strip()
            if "-" in bdate_str:
                parts = bdate_str.split("-")
                try:
                    if len(parts) >= 3:
                        b_yr = int(parts[0])
                        b_mon = int(parts[1])
                        b_day = int(parts[2])
                        age_val = max(15, min(55, 2024 - b_yr - (1 if (b_mon, b_day) > (9, 1) else 0)))
                except Exception:
                    pass
            elif bdate_str.isdigit():
                try:
                    import datetime
                    days_val = int(bdate_str)
                    if 100000 < days_val < 200000:
                        bdate = datetime.date(1582, 10, 14) + datetime.timedelta(days=days_val)
                        b_mon = bdate.month
                        b_day = bdate.day
                        age_val = max(15, min(55, 2024 - bdate.year - (1 if (b_mon, b_day) > (9, 1) else 0)))
                except Exception:
                    pass
            if "age" in stats and str(stats["age"]).isdigit():
                try:
                    age_val = int(stats["age"])
                except Exception:
                    pass

            try:
                nat_id = int(stats.get("nationality", 0))
            except Exception:
                nat_id = 0
                
            try:
                is_ret = int(stats.get("isretiring", 0))
            except Exception:
                is_ret = 0
            
            nation_str = pdata.get("nation_name", "") or (get_nation_name(nat_id) if nat_id > 0 else "")
            if nation_str.startswith("Nation #"):
                nation_str = ""
            league_str = pdata.get("league", "") or self.team_to_league.get(tid, "")
            alt_pos_str = pdata.get("alt_positions", "")

            entry = {
                "playerid": pid,
                "name": pdata["name"],
                "overall": ovr,
                "potential": pot,
                "position": pos_name,
                "pos_code": pos_code,
                "alt_positions": alt_pos_str,
                "club": club_name,
                "teamid": tid,
                "league": league_str,
                "nationality": nat_id,
                "nation_name": nation_str,
                "age": age_val,
                "birth_day": b_day,
                "birth_month": b_mon,
                "isretiring": is_ret,
                "foot": pdata.get("foot", "Right"),
                "skills": pdata.get("skills", 3),
                "weak_foot": pdata.get("weak_foot", 3),
                "height": pdata.get("height", 182),
                "weight": pdata.get("weight", 77),
                "stats": stats,
                "czum_row_idx": czum_row,
                "risb_row_idx": risb_row,
                "row_index": len(self.players_cache),
                "table_sname": "CZUM"
            }
            self.players_cache.append(entry)

        # Build sorted lists of all available leagues and nations
        self._refresh_league_and_nation_lists(self.players_cache)

        # Sort players by overall rating descending so superstars appear first
        self.players_cache.sort(key=lambda p: (p["overall"], p["potential"]), reverse=True)
        for idx, p in enumerate(self.players_cache):
            p["cache_index"] = idx

        # 4. Build Teams Cache from lyxL & kISL (all 816 authentic clubs with real stadiums and managers)
        lyxl = self.db.tables_map.get("lyxL")
        knen = self.db.tables_map.get("Knen")
        kisl = self.db.tables_map.get("kISL")
        col_dmls = kisl.columns_map.get("DmlS") if kisl else None
        indexed_teams = set()

        if lyxl and "IOSv" in lyxl.columns_map:
            col_tname = lyxl.columns_map["IOSv"]
            for r_idx, rec in enumerate(lyxl.records):
                try:
                    tname = col_tname.decode_value(rec)
                    if not tname:
                        continue
                    tid = 0
                    if col_dmls and r_idx < len(kisl.records):
                        try:
                            tid = col_dmls.decode_value(kisl.records[r_idx]) + 1
                        except Exception:
                            tid = 0
                    if tid <= 0:
                        tid = r_idx + 1
                    if tid > 0 and tid not in indexed_teams:
                        formatted_name = format_team_display_name(tid, tname, r_idx)
                        roster = list(self.team_rosters.get(tid, []))
                        stadium_name = stadium_names.get(r_idx) or f"{formatted_name} Stadium"
                        
                        # Authentic manager lookup from Knen (1:1 correspondence with lyxL)
                        mgr_name = ""
                        mgr_asset_id = 0
                        if knen and r_idx < len(knen.records):
                            rec_k = knen.records[r_idx]
                            common = knen.columns_map["EveZ"].decode_value(rec_k) if "EveZ" in knen.columns_map else ""
                            first = knen.columns_map["OoQO"].decode_value(rec_k) if "OoQO" in knen.columns_map else ""
                            last = knen.columns_map["aArc"].decode_value(rec_k) if "aArc" in knen.columns_map else ""
                            mgr_name = common or f"{first} {last}".strip()
                            if "tFVQ" in knen.columns_map:
                                mgr_asset_id = knen.columns_map["tFVQ"].decode_value(rec_k)

                        if not mgr_name:
                            mgr_name = "Head Coach"

                        self.teams_cache.append({
                            "teamid": tid,
                            "name": formatted_name,
                            "league": self.team_to_league.get(tid, ""),
                            "stadium": stadium_name,
                            "manager_name": mgr_name,
                            "manager_asset_id": mgr_asset_id,
                            "roster_count": len(roster),
                            "roster": roster,
                            "table_sname": "lyxL",
                            "row_index": r_idx
                        })
                        indexed_teams.add(tid)
                except Exception:
                    pass

        # Sort teams by roster size (top active teams first) then alphabetically
        self.teams_cache.sort(key=lambda t: (t["roster_count"] > 0, t["roster_count"], t["name"]), reverse=True)

    def update_player_attribute(self, player_id: int, attr_key: str, new_val: Any, track: bool = True) -> bool:
        """Updates a player's attribute in memory cache and directly into the active database records."""
        pl = self.players_lookup.get(player_id, {})
        old_val = pl.get("stats", {}).get(attr_key)
        if old_val is None:
            old_val = pl.get(attr_key, "")

        # Synchronize players_lookup
        if player_id in self.players_lookup:
            pl = self.players_lookup[player_id]
            pl.setdefault("stats", {})[attr_key] = str(new_val)
            if attr_key == "overallrating":
                pl["overall"] = int(new_val)
            elif attr_key == "potential":
                pl["potential"] = int(new_val)
            elif attr_key == "skillmoves":
                pl["skills"] = int(new_val)
            elif attr_key == "weakfootabilitytypecode":
                pl["weak_foot"] = int(new_val)
            elif attr_key == "preferredposition1":
                pl["pos_code"] = int(new_val)
            elif attr_key == "teamid":
                pl["teamid"] = int(new_val)
                pl["club"] = get_team_name(int(new_val))

        for p in self.players_cache:
            if p["playerid"] == player_id:
                p["stats"][attr_key] = str(new_val)
                if attr_key == "overallrating":
                    p["overall"] = int(new_val)
                elif attr_key == "potential":
                    p["potential"] = int(new_val)
                elif attr_key == "skillmoves":
                    p["skills"] = int(new_val)
                elif attr_key == "weakfootabilitytypecode":
                    p["weak_foot"] = int(new_val)
                elif attr_key == "preferredposition1":
                    p["pos_code"] = int(new_val)
                    p["position"] = get_position_name(int(new_val))
                elif attr_key == "teamid":
                    p["teamid"] = int(new_val)
                    p["club"] = get_team_name(int(new_val))
                elif attr_key == "jerseynumber":
                    try:
                        self.set_player_jersey_number(player_id, int(new_val), track=False)
                    except Exception:
                        pass

                # Write directly to active CZUM database record if present:
                czum_row = p.get("czum_row_idx")
                czum = self.db.tables_map.get("CZUM")
                if czum and czum_row is not None and czum_row < len(czum.records):
                    czum_col_map = {
                        "overallrating": "XjDq",
                        "vision": "ZoOK",
                        "positioning": "aReg",
                        "finishing": "kerE",
                        "crossing": "nmgT",
                        "aggression": "UERs",
                        "interceptions": "dXNv",
                        "standingtackle": "SJKz",
                        "preferredposition1": "NrcP",
                        "preferredposition2": "ypBQ",
                        "preferredposition3": "kqda",
                        "preferredposition4": "aReg",
                        "skillmoves": "iKqs",
                        "weakfootabilitytypecode": "WVsa",
                        "acceleration": "XsFD",
                        "sprintspeed": "HfYD",
                        "shotpower": "CsyD",
                        "longshots": "AGsE",
                        "volleys": "CsBG",
                        "penalties": "xrSG",
                        "freekickaccuracy": "wGOH",
                        "shortpassing": "mpuH",
                        "longpassing": "eYFI",
                        "curve": "YCnI",
                        "agility": "jlQJ",
                        "stamina": "uGEA",
                        "strength": "onGA",
                        "reactions": "HEDC",
                        "composure": "CkYD",
                        "potential": "RRQB",
                        "trait1": "juxV",
                        "icontrait1": "OjQY",
                        "trait2": "vTpl",
                        "icontrait2": "HqUh"
                    }
                    col_sn = czum_col_map.get(attr_key)
                    if col_sn and col_sn in czum.columns_map:
                        try:
                            col = czum.columns_map[col_sn]
                            col.encode_value(czum.records[czum_row], int(new_val))
                        except Exception:
                            pass

                # Update team transfer in rIsB table:
                if attr_key == "teamid":
                    self.transfer_player(player_id, int(new_val), track=False)

                if track and old_val is not None and str(old_val).strip() != str(new_val).strip():
                    pname = pl.get("name", f"Player #{player_id}")
                    disp_label = get_column_display_name(attr_key)
                    if "(" in disp_label:
                        disp_label = disp_label.split(" (")[0]
                    self.change_tracker.record_change(
                        category="player",
                        title=f"{pname} (ID {player_id})",
                        entity_id=player_id,
                        field_name=attr_key,
                        field_label=disp_label or attr_key.capitalize(),
                        old_val=old_val,
                        new_val=new_val,
                        revert_fn=lambda pid=player_id, k=attr_key, ov=old_val: self.update_player_attribute(pid, k, ov, track=False)
                    )

                return True
        return False

    def transfer_player(self, player_id: int, new_team_id: int, jersey_number: Optional[int] = None, track: bool = True) -> bool:
        """
        Transfers player to a new team in active squad database and updates rosters and rIsB bitfields.
        Handles destination translation, jersey collision resolution, and clean revert.
        """
        target_tid = new_team_id
        if target_tid in SECONDARY_TO_PRIMARY_TEAMS and target_tid < 65536:
            target_tid = SECONDARY_TO_PRIMARY_TEAMS[target_tid]

        # Determine authentic base club of player from lookup
        p_lookup = self.players_lookup.get(player_id, {})
        base_tid = p_lookup.get("base_teamid") or self.base_team_lookup.get(player_id, p_lookup.get("teamid", 0))
        base_jersey = p_lookup.get("base_jersey") or self.base_jersey_lookup.get(player_id, int(p_lookup.get("stats", {}).get("jerseynumber", 0) or 0))

        old_team_id = 0
        for p in self.players_cache:
            if p["playerid"] == player_id:
                old_team_id = p["teamid"]
                break
        if old_team_id == 0:
            old_team_id = p_lookup.get("teamid", 0)
        old_jersey = self.get_player_jersey_number(player_id)
        old_team_name = get_team_name(old_team_id) if old_team_id > 0 else "Free Agent"

        self.user_transfers[player_id] = target_tid
        club_name = get_team_name(target_tid) if target_tid > 0 else "Free Agent"

        if player_id in self.players_lookup:
            if "base_teamid" not in self.players_lookup[player_id]:
                self.players_lookup[player_id]["base_teamid"] = base_tid
            if "base_jersey" not in self.players_lookup[player_id]:
                self.players_lookup[player_id]["base_jersey"] = base_jersey
            self.players_lookup[player_id]["teamid"] = target_tid
            self.players_lookup[player_id]["club"] = club_name

        for p in self.players_cache:
            if p["playerid"] == player_id:
                old_team = p["teamid"]
                p["teamid"] = target_tid
                p["club"] = club_name
                p["league"] = self.team_to_league.get(target_tid, "") if target_tid > 0 else ""
                
                # Update team_rosters
                if old_team in self.team_rosters and player_id in self.team_rosters[old_team]:
                    self.team_rosters[old_team].remove(player_id)
                if target_tid > 0:
                    if target_tid not in self.team_rosters:
                        self.team_rosters[target_tid] = []
                    if player_id not in self.team_rosters[target_tid]:
                        self.team_rosters[target_tid].append(player_id)
                        
                # Update team cache counts and rosters
                for t in self.teams_cache:
                    if t["teamid"] == old_team:
                        t["roster"] = list(self.team_rosters.get(old_team, []))
                        t["roster_count"] = len(t["roster"])
                    elif t["teamid"] == target_tid:
                        t["roster"] = list(self.team_rosters.get(target_tid, []))
                        t["roster_count"] = len(t["roster"])

                # Resolve Jersey Number & Collisions
                target_jersey = jersey_number
                if target_jersey is None:
                    if target_tid == base_tid and base_jersey > 0:
                        target_jersey = base_jersey
                    else:
                        target_jersey = self.get_player_jersey_number(player_id)

                if target_tid > 0:
                    target_roster = self.team_rosters.get(target_tid, [])
                    taken_jerseys = {self.get_player_jersey_number(other_pid) for other_pid in target_roster if other_pid != player_id}
                    if target_jersey in taken_jerseys:
                        for cand in range(1, 100):
                            if cand not in taken_jerseys:
                                target_jersey = cand
                                break

                if target_jersey and 1 <= target_jersey <= 99:
                    self.player_jerseys[player_id] = target_jersey
                    self.user_jerseys[player_id] = target_jersey
                    p.setdefault("stats", {})["jerseynumber"] = str(target_jersey)
                    if player_id in self.players_lookup:
                        self.players_lookup[player_id].setdefault("stats", {})["jerseynumber"] = str(target_jersey)

                # Physically persist into rIsB transfer table
                risb = self.db.tables_map.get("rIsB")
                if risb:
                    risb_row = p.get("risb_row_idx")
                    # If not attached, scan to see if player already has a record in rIsB
                    if risb_row is None:
                        for idx, rec in enumerate(risb.records):
                            if get_bits(rec, 18, 18) == player_id:
                                risb_row = idx
                                p["risb_row_idx"] = idx
                                break

                    # Reversion check: if transferring back to authentic base club and default jersey
                    if target_tid == base_tid and (target_jersey == base_jersey or target_jersey == 0 or jersey_number is None):
                        if risb_row is not None and risb_row < len(risb.records):
                            risb.records[risb_row][:] = b"\x00" * 8
                            p["risb_row_idx"] = None
                            if player_id in self.user_transfers:
                                del self.user_transfers[player_id]
                    else:
                        if risb_row is not None and risb_row < len(risb.records):
                            rec = risb.records[risb_row]
                            set_bits(rec, 0, 18, target_tid)
                            set_bits(rec, 18, 18, player_id)
                            if target_jersey and 1 <= target_jersey <= 99:
                                set_bits(rec, 36, 7, target_jersey)
                        else:
                            # Find first empty slot in rIsB
                            target_row = None
                            for idx, rec in enumerate(risb.records):
                                if get_bits(rec, 18, 18) == 0:
                                    target_row = idx
                                    break
                            if target_row is not None:
                                rec = risb.records[target_row]
                                set_bits(rec, 0, 18, target_tid)
                                set_bits(rec, 18, 18, player_id)
                                if target_jersey and 1 <= target_jersey <= 99:
                                    set_bits(rec, 36, 7, target_jersey)
                                p["risb_row_idx"] = target_row
                            else:
                                new_rec = bytearray(risb.rec_size)
                                set_bits(new_rec, 0, 18, target_tid)
                                set_bits(new_rec, 18, 18, player_id)
                                if target_jersey and 1 <= target_jersey <= 99:
                                    set_bits(new_rec, 36, 7, target_jersey)
                                risb.records.append(new_rec)
                                risb.written_records = len(risb.records)
                                p["risb_row_idx"] = len(risb.records) - 1

                if track and (old_team_id != target_tid or (jersey_number is not None and jersey_number != old_jersey)):
                    pname = p_lookup.get("name", f"Player #{player_id}")
                    new_team_name = get_team_name(target_tid) if target_tid > 0 else "Free Agent"
                    new_j = target_jersey if (target_jersey and target_jersey > 0) else old_jersey
                    self.change_tracker.record_change(
                        category="transfer",
                        title=f"{pname} (ID {player_id})",
                        entity_id=player_id,
                        field_name="team_transfer",
                        field_label="Club Transfer",
                        old_val=f"{old_team_name} (#{old_jersey})",
                        new_val=f"{new_team_name} (#{new_j})",
                        revert_fn=lambda pid=player_id, otid=old_team_id, oj=old_jersey: self.transfer_player(pid, otid, jersey_number=oj, track=False)
                    )
                return True
        return False

    def get_team_squad_roles(self, team_id: int) -> Dict[str, int]:
        """Returns active squad roles (captain, penalty, free kicks, corners) for a club."""
        if team_id in self.team_squad_roles:
            return self.team_squad_roles[team_id]
            
        roster = self.team_rosters.get(team_id, [])
        if not roster:
            return {}
            
        # Default roles based on player overall ratings
        sorted_pids = sorted(roster, key=lambda pid: self.players_lookup.get(pid, {}).get("overall", 60), reverse=True)
        roles = {
            "captain": sorted_pids[0],
            "penalty": sorted_pids[0],
            "freekick_short": sorted_pids[1] if len(sorted_pids) > 1 else sorted_pids[0],
            "freekick_long": sorted_pids[2] if len(sorted_pids) > 2 else sorted_pids[0],
            "corner_left": sorted_pids[1] if len(sorted_pids) > 1 else sorted_pids[0],
            "corner_right": sorted_pids[2] if len(sorted_pids) > 2 else sorted_pids[0],
        }
        self.team_squad_roles[team_id] = roles
        return roles

    def set_team_squad_roles(self, team_id: int, roles: Dict[str, int]) -> bool:
        """Saves squad roles for a club."""
        self.team_squad_roles[team_id] = roles
        return True

    def get_player_jersey_number(self, player_id: int) -> int:
        """Returns authentic squad jersey number (1-99) for a player."""
        # 1. User manual runtime edit
        if player_id in self.user_jerseys:
            return self.user_jerseys[player_id]

        # 2. In-memory stats
        if player_id in self.players_lookup:
            stats = self.players_lookup[player_id].get("stats", {})
            try:
                num = int(stats.get("jerseynumber", 0))
                if 1 <= num <= 99:
                    return num
            except Exception:
                pass

        # 3. Verified preset jersey map
        if player_id in self.player_jerseys:
            return self.player_jerseys[player_id]

        # 4. Position-based smart fallback (never pseudo-random modulo)
        pos_code = -1
        if player_id in self.players_lookup:
            pos_code = self.players_lookup[player_id].get("pos_code", -1)
        if pos_code == 0:  # GK
            return 1
        elif pos_code in (2, 3):  # RB / RWB
            return 2
        elif pos_code in (7, 8):  # LB / LWB
            return 3
        elif pos_code in (4, 5, 6):  # CB
            return 4
        elif pos_code in (9, 10, 11):  # CDM
            return 6
        elif pos_code in (12, 23):  # RM / RW
            return 7
        elif pos_code in (13, 14, 15):  # CM
            return 8
        elif pos_code in (20, 21, 24, 25, 26):  # ST / CF
            return 9
        elif pos_code in (17, 18, 19):  # CAM
            return 10
        elif pos_code in (16, 27):  # LM / LW
            return 11
        return 10

    def set_player_jersey_number(self, player_id: int, number: int, track: bool = True) -> bool:
        """Sets squad jersey number (1-99) for a player and persists directly into rIsB and RrqT."""
        if not (1 <= number <= 99):
            return False
        old_num = self.get_player_jersey_number(player_id)
        self.user_jerseys[player_id] = number
        self.player_jerseys[player_id] = number
        if player_id in self.players_lookup:
            self.players_lookup[player_id].setdefault("stats", {})["jerseynumber"] = str(number)
        for p in self.players_cache:
            if p["playerid"] == player_id:
                p.setdefault("stats", {})["jerseynumber"] = str(number)
                
                # Persist to rIsB (active save delta)
                risb = self.db.tables_map.get("rIsB")
                if risb:
                    r_idx = p.get("risb_row_idx")
                    if r_idx is not None and r_idx < len(risb.records):
                        set_bits(risb.records[r_idx], 36, 7, number)
                    else:
                        target_row = None
                        for idx, rec in enumerate(risb.records):
                            if get_bits(rec, 18, 18) == player_id:
                                target_row = idx
                                break
                        if target_row is not None:
                            set_bits(risb.records[target_row], 36, 7, number)
                            p["risb_row_idx"] = target_row
                        else:
                            for idx, rec in enumerate(risb.records):
                                if get_bits(rec, 18, 18) == 0:
                                    target_row = idx
                                    break
                            if target_row is not None:
                                tid_primary = p.get("teamid", 0)
                                if tid_primary in SECONDARY_TO_PRIMARY_TEAMS and tid_primary < 65536:
                                    tid_primary = SECONDARY_TO_PRIMARY_TEAMS[tid_primary]
                                set_bits(risb.records[target_row], 18, 18, player_id)
                                set_bits(risb.records[target_row], 0, 18, tid_primary)
                                set_bits(risb.records[target_row], 36, 7, number)
                                p["risb_row_idx"] = target_row
                            else:
                                new_rec = bytearray(risb.rec_size)
                                set_bits(new_rec, 18, 18, player_id)
                                set_bits(new_rec, 0, 18, p.get("teamid", 0))
                                set_bits(new_rec, 36, 7, number)
                                risb.records.append(new_rec)
                                risb.written_records = len(risb.records)
                                p["risb_row_idx"] = len(risb.records) - 1

                # Also update RrqT if czum_row exists
                r_idx = p.get("czum_row_idx")
                rrqt = self.db.tables_map.get("RrqT")
                if rrqt and r_idx is not None and r_idx < len(rrqt.records):
                    set_bits(rrqt.records[r_idx], 23, 7, number)
                break

        if track and old_num != number:
            pl = self.players_lookup.get(player_id, {})
            pname = pl.get("name", f"Player #{player_id}")
            self.change_tracker.record_change(
                category="player",
                title=f"{pname} (ID {player_id})",
                entity_id=player_id,
                field_name="jerseynumber",
                field_label="Jersey Number",
                old_val=str(old_num),
                new_val=str(number),
                revert_fn=lambda pid=player_id, on=old_num: self.set_player_jersey_number(pid, on, track=False)
            )

        return True

    def update_team_stadium(self, team_id: int, new_stadium_name: str, track: bool = True) -> bool:
        """Updates home stadium name for a club in memory and in table kISL."""
        clean_name = new_stadium_name.strip()
        if not clean_name:
            return False
        for t in self.teams_cache:
            if t["teamid"] == team_id:
                old_stadium = t.get("stadium", "")
                t["stadium"] = clean_name
                r_idx = t.get("row_index")
                if r_idx is not None:
                    kisl = self.db.tables_map.get("kISL")
                    if kisl and r_idx < len(kisl.records):
                        self.update_table_cell("kISL", r_idx, "fwCQ", clean_name, track=False)
                
                if track and old_stadium != clean_name:
                    tname = t.get("name", f"Team #{team_id}")
                    self.change_tracker.record_change(
                        category="team",
                        title=f"{tname} (ID {team_id})",
                        entity_id=team_id,
                        field_name="stadium",
                        field_label="Stadium Name",
                        old_val=old_stadium,
                        new_val=clean_name,
                        revert_fn=lambda tid=team_id, os=old_stadium: self.update_team_stadium(tid, os, track=False)
                    )
                return True
        return False

    def update_team_manager(self, team_id: int, new_manager_name: str, track: bool = True) -> bool:
        """Updates manager name for a club in memory and in authentic table Knen."""
        clean_name = new_manager_name.strip()
        if not clean_name:
            return False
        for t in self.teams_cache:
            if t["teamid"] == team_id:
                old_manager = t.get("manager_name", "")
                t["manager_name"] = clean_name
                r_idx = t.get("row_index")
                if r_idx is not None:
                    knen = self.db.tables_map.get("Knen")
                    if knen and r_idx < len(knen.records):
                        self.update_table_cell("Knen", r_idx, "EveZ", clean_name, track=False)
                
                if track and old_manager != clean_name:
                    tname = t.get("name", f"Team #{team_id}")
                    self.change_tracker.record_change(
                        category="team",
                        title=f"{tname} (ID {team_id})",
                        entity_id=team_id,
                        field_name="manager",
                        field_label="Manager Name",
                        old_val=old_manager,
                        new_val=clean_name,
                        revert_fn=lambda tid=team_id, om=old_manager: self.update_team_manager(tid, om, track=False)
                    )
                return True
        return False

    def update_table_cell(self, sname: str, row_idx: int, col_sname: str, new_val: Any, track: bool = True) -> bool:
        """Directly writes a value into any column of any record in the active database."""
        tbl = self.db.tables_map.get(sname)
        if not tbl or row_idx >= len(tbl.records):
            return False
            
        col = tbl.columns_map.get(col_sname)
        if not col:
            return False
            
        try:
            old_val = col.decode_value(tbl.records[row_idx])
            col.encode_value(tbl.records[row_idx], new_val)
            
            if track and str(old_val).strip() != str(new_val).strip():
                disp_col = get_column_display_name(col_sname)
                self.change_tracker.record_change(
                    category="table",
                    title=f"Table {sname} [Row {row_idx}]",
                    entity_id=f"{sname}_{row_idx}_{col_sname}",
                    field_name=col_sname,
                    field_label=disp_col or col_sname,
                    old_val=str(old_val),
                    new_val=str(new_val),
                    revert_fn=lambda sn=sname, ri=row_idx, csn=col_sname, ov=old_val: self.update_table_cell(sn, ri, csn, ov, track=False)
                )
            return True
        except Exception:
            return False

    def clone_table_row(self, sname: str, row_idx: int, track: bool = True) -> bool:
        """Clones an existing row in a database table."""
        tbl = self.db.tables_map.get(sname)
        if not tbl or row_idx >= len(tbl.records):
            return False
        cloned = bytearray(tbl.records[row_idx])
        tbl.records.append(cloned)
        tbl.written_records = len(tbl.records)
        new_row_idx = len(tbl.records) - 1
        if track:
            self.change_tracker.record_change(
                category="table",
                title=f"Table {sname} [Row {new_row_idx}]",
                entity_id=f"{sname}_{new_row_idx}_clone",
                field_name="clone_row",
                field_label="Row Cloned",
                old_val="None",
                new_val=f"Cloned from Row #{row_idx}",
                revert_fn=lambda sn=sname, ri=new_row_idx: self.delete_table_row(sn, ri, track=False)
            )
        return True

    def delete_table_row(self, sname: str, row_idx: int, track: bool = True) -> bool:
        """Deletes a row from a database table."""
        tbl = self.db.tables_map.get(sname)
        if not tbl or row_idx >= len(tbl.records):
            return False
        deleted_data = bytearray(tbl.records[row_idx])
        del tbl.records[row_idx]
        tbl.written_records = len(tbl.records)
        if track:
            self.change_tracker.record_change(
                category="table",
                title=f"Table {sname} [Row {row_idx}]",
                entity_id=f"{sname}_{row_idx}_delete",
                field_name="delete_row",
                field_label="Row Deleted",
                old_val="Active Record",
                new_val="Deleted",
                revert_fn=lambda sn=sname, ri=row_idx, rec=deleted_data: self._restore_table_row(sn, ri, rec)
            )
        return True

    def _restore_table_row(self, sname: str, row_idx: int, record_bytes: bytearray) -> bool:
        tbl = self.db.tables_map.get(sname)
        if not tbl:
            return False
        tbl.records.insert(row_idx, record_bytes)
        tbl.written_records = len(tbl.records)
        return True

    def add_table_row(self, sname: str, track: bool = True) -> bool:
        """Adds a new blank row into a database table."""
        tbl = self.db.tables_map.get(sname)
        if not tbl:
            return False
        new_row = bytearray(tbl.rec_size)
        tbl.records.append(new_row)
        tbl.written_records = len(tbl.records)
        new_row_idx = len(tbl.records) - 1
        if track:
            self.change_tracker.record_change(
                category="table",
                title=f"Table {sname} [Row {new_row_idx}]",
                entity_id=f"{sname}_{new_row_idx}_add",
                field_name="add_row",
                field_label="Row Added",
                old_val="None",
                new_val="New Record",
                revert_fn=lambda sn=sname, ri=new_row_idx: self.delete_table_row(sn, ri, track=False)
            )
        return True

    def get_table_names_list(self) -> List[Tuple[str, str, int]]:
        """Returns list of (sname, display_name, record_count) for all 76 tables."""
        res = []
        for tbl in self.db.tables:
            disp = get_table_display_name(tbl.sname)
            res.append((tbl.sname, disp, len(tbl.records)))
        return res

    def get_table(self, sname: str) -> Optional[DBTable]:
        return self.db.tables_map.get(sname)

    def export_table_csv(self, table_sname: str, target_path: str, include_labels: bool = True) -> Tuple[bool, str, int]:
        """Exports all records of a specific database table to a CSV file."""
        tbl = self.get_table(table_sname)
        if not tbl:
            return False, f"Table '{table_sname}' not found in active database.", 0
        return tbl.export_to_csv(target_path, include_labels)

    def export_players_list_csv(self, players_list: List[Dict[str, Any]], target_path: str) -> Tuple[bool, str, int]:
        """Exports a list of filtered players with full bio, club, league, nation, and ratings to CSV."""
        try:
            headers = [
                "playerid", "name", "overall", "potential", "position", "alt_positions",
                "club", "teamid", "league", "nation_name", "age", "foot", "skills",
                "weak_foot", "height", "weight", "jerseynumber"
            ]
            with open(target_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for p in players_list:
                    jersey = p.get("stats", {}).get("jerseynumber", "") or self.get_player_jersey_number(p.get("playerid", 0))
                    writer.writerow([
                        p.get("playerid", 0),
                        p.get("name", ""),
                        p.get("overall", 0),
                        p.get("potential", 0),
                        p.get("position", ""),
                        p.get("alt_positions", ""),
                        p.get("club", ""),
                        p.get("teamid", 0),
                        p.get("league", ""),
                        p.get("nation_name", ""),
                        p.get("age", 25),
                        p.get("foot", "Right"),
                        p.get("skills", 3),
                        p.get("weak_foot", 3),
                        p.get("height", 180),
                        p.get("weight", 75),
                        jersey
                    ])
            return True, f"Exported {len(players_list):,} players to {os.path.basename(target_path)}", len(players_list)
        except Exception as e:
            return False, f"Failed to export players CSV: {e}", 0

    def import_table_csv(self, table_sname: str, source_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Imports records from a CSV file into the specified database table.
        Automatically re-indexes session entity caches if the table affects players or clubs.
        """
        tbl = self.get_table(table_sname)
        if not tbl:
            return False, f"Table '{table_sname}' not found in active database.", {}
        ok, msg, stats = tbl.import_from_csv(source_path)
        if ok:
            # Re-index if core entities were affected
            if table_sname in ("CZUM", "RrqT", "lyxL", "mDGw", "rIsB", "kISL", "Knen"):
                try:
                    self._build_indexes()
                except Exception as e:
                    msg += f" (Note: index refresh error: {str(e)})"
        return ok, msg, stats

    def export_all_tables_zip(self, zip_target_path: str) -> Tuple[bool, str, int]:
        """
        Exports all 76 database tables as individual CSV files inside a single ZIP archive.
        """
        import zipfile
        import io
        import csv
        try:
            try:
                from src.core.schema import get_column_display_name, get_table_display_name
            except ImportError:
                from core.schema import get_column_display_name, get_table_display_name

            exported_count = 0
            with zipfile.ZipFile(zip_target_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for tbl in self.db.tables:
                    try:
                        sio = io.StringIO()
                        writer = csv.writer(sio)
                        # Header
                        headers = []
                        for col in tbl.columns:
                            disp = get_column_display_name(col.sname, tbl.sname)
                            if disp and disp != col.sname:
                                headers.append(f"{col.sname} [{disp}]")
                            else:
                                headers.append(col.sname)
                        writer.writerow(headers)
                        # Rows
                        for rec in tbl.records:
                            row_vals = [col.decode_value(rec) for col in tbl.columns]
                            writer.writerow(row_vals)
                        
                        csv_data = sio.getvalue().encode("utf-8-sig")
                        t_disp = get_table_display_name(tbl.sname).replace(" ", "_").replace("/", "_")
                        filename = f"{tbl.sname}_{t_disp}.csv"
                        zf.writestr(filename, csv_data)
                        exported_count += 1
                    except Exception:
                        continue
            return True, f"Successfully exported all {exported_count} tables to {zip_target_path}", exported_count
        except Exception as e:
            return False, f"Failed to export ZIP archive: {str(e)}", 0

    def format_table_row_summary(self, table_sname: str, row_idx: int) -> str:
        """Generates an informative, human-readable summary for a specific table row."""
        tbl = self.get_table(table_sname)
        if not tbl or row_idx >= len(tbl.records):
            return f"Row {row_idx:5d}"
            
        rec = tbl.records[row_idx]

        # 1. Player Attributes & Core Stats (CZUM)
        if table_sname == "CZUM":
            if row_idx < len(self.base_players_list):
                pid = self.base_players_list[row_idx]
                p = self.players_lookup.get(pid)
                b = self.base_players_records[row_idx] if row_idx < len(self.base_players_records) else {}
                pname = p.get("name") if p else f"Player #{pid}"
                club = p.get("club") if p else "Free Agent"
                ovr = b.get("overallrating") or (p.get("overall") if p else 60)
                pot = b.get("potential") or (p.get("potential") if p else ovr)
                pos = get_position_name(p.get("pos_code", -1)) if p else "N/A"
                return f"Row {row_idx:5d} | [{ovr} OVR / {pot} POT] {pname} ({pos})  -  {club} (PID: {pid})"

        # 2. Clubs, Teams & Roster Properties (lyxL)
        elif table_sname == "lyxL":
            col_tname = tbl.columns_map.get("IOSv")
            tid = int.from_bytes(rec[:4], "little") & 0x7FFFFFFF
            tname = col_tname.decode_value(rec) if col_tname else get_team_name(tid)
            ovr = tbl.columns_map.get("sqCP").decode_value(rec) if "sqCP" in tbl.columns_map else 0
            att = tbl.columns_map.get("aDMz").decode_value(rec) if "aDMz" in tbl.columns_map else 0
            star = tbl.columns_map.get("WLKn").decode_value(rec) if "WLKn" in tbl.columns_map else 0
            ucl = tbl.columns_map.get("Tsda").decode_value(rec) if "Tsda" in tbl.columns_map else 0
            star_str = f" | Star PID: #{star}" if star > 0 else ""
            ucl_str = f" | UCL Wins: {ucl}" if ucl > 0 else ""
            return f"Row {row_idx:5d} | [Club] {tname} (ID: {tid}) | {ovr} OVR | {att} ATT{star_str}{ucl_str}"

        # 3. Teams & Club Tactical Profiles (mDGw)
        elif table_sname == "mDGw":
            lyxl = self.get_table("lyxL")
            tid = (int.from_bytes(lyxl.records[row_idx][:4], "little") & 0x7FFFFFFF) if lyxl and row_idx < len(lyxl.records) else (row_idx + 1)
            tname = get_team_name(tid)
            stars_col = tbl.columns_map.get("pFxE")
            stars = stars_col.decode_value(rec) if stars_col else 0.0
            form_col = tbl.columns_map.get("MZIF")
            form_name = form_col.decode_value(rec) if form_col else ""
            rival_col = tbl.columns_map.get("oHkj")
            rival_id = rival_col.decode_value(rec) if rival_col else 0
            form_str = f" | Formation: {form_name}" if form_name else ""
            rival_str = f" | Rival: #{rival_id}" if rival_id > 0 else ""
            return f"Row {row_idx:5d} | [Tactical Profile] {tname} (ID: {tid}) | {stars} Stars{form_str}{rival_str}"

        # 4. Authentic Domestic Leagues & Divisions (onMQ)
        elif table_sname == "onMQ":
            col_lname = tbl.columns_map.get("FtgW")
            col_lid = tbl.columns_map.get("aQrQ")
            col_tier = tbl.columns_map.get("paPI")
            col_teams = tbl.columns_map.get("WDGJ")
            lname = col_lname.decode_value(rec) if col_lname else f"League #{row_idx}"
            lid = col_lid.decode_value(rec) if col_lid else row_idx
            tier = col_tier.decode_value(rec) if col_tier else 1
            num_t = col_teams.decode_value(rec) if col_teams else 0
            return f"Row {row_idx:5d} | [League] {lname} (ID: {lid}) | Tier {tier} | {num_t} Clubs"

        # 5. Club Budgets & Career Financials (ImNE)
        elif table_sname == "ImNE":
            col_cname = tbl.columns_map.get("QmlU")
            col_b = tbl.columns_map.get("Ibup")
            col_s = tbl.columns_map.get("MYrf")
            cname = col_cname.decode_value(rec) if col_cname else f"Club #{row_idx}"
            budget = col_b.decode_value(rec) if col_b else 0
            sid = col_s.decode_value(rec) if col_s else 0
            return f"Row {row_idx:5d} | [Club Finances] {cname} | Budget: EUR {budget:,}K | Stadium: #{sid}"

        # 6. Player Audio Commentary & Callnames (bneD)
        elif table_sname == "bneD":
            col_p = tbl.columns_map.get("FuiB")
            pname = col_p.decode_value(rec) if col_p else f"Name #{row_idx}"
            return f"Row {row_idx:5d} | [Commentary Call Name] '{pname}'"

        # 7. Custom & Edited Player Identity Names (nQVU)
        elif table_sname == "nQVU":
            col_c = tbl.columns_map.get("HdeP")
            col_s = tbl.columns_map.get("xnfZ")
            col_f = tbl.columns_map.get("kRfb")
            col_id = tbl.columns_map.get("ykFq")
            comm = col_c.decode_value(rec) if col_c else ""
            sur = col_s.decode_value(rec) if col_s else ""
            first = col_f.decode_value(rec) if col_f else ""
            pid = col_id.decode_value(rec) if col_id else 0
            full_n = comm or f"{first} {sur}".strip() or f"Player #{pid}"
            return f"Row {row_idx:5d} | [Player Identity] {full_n} (PID: #{pid}) | Kit: {sur}"

        # 8. Player 3D Face & Starhead Assets (nrFl)
        elif table_sname == "nrFl":
            col_pid = tbl.columns_map.get("mCXg")
            col_aid = tbl.columns_map.get("Laxd")
            col_hq = tbl.columns_map.get("McUr")
            pid = col_pid.decode_value(rec) if col_pid else 0
            aid = col_aid.decode_value(rec) if col_aid else 0
            is_hq = col_hq.decode_value(rec) if col_hq else 0
            scan_str = "Authentic Starhead Scan" if is_hq else "Generic Custom Head"
            p = self.players_lookup.get(pid)
            pname = p.get("name") if p else f"Player #{pid}"
            return f"Row {row_idx:5d} | [3D Head Asset] {pname} (PID: #{pid}) | Asset ID: #{aid} ({scan_str})"

        # 9. Player Awards, Ballon d'Or & Accolades (UlaA)
        elif table_sname == "UlaA":
            col_pid = tbl.columns_map.get("mCXg")
            col_aw = tbl.columns_map.get("xKVG")
            col_yr = tbl.columns_map.get("BssH")
            col_comp = tbl.columns_map.get("HjSL")
            pid = col_pid.decode_value(rec) if col_pid else 0
            aw_id = col_aw.decode_value(rec) if col_aw else 0
            yr = col_yr.decode_value(rec) if col_yr else 0
            cid = col_comp.decode_value(rec) if col_comp else 0
            p = self.players_lookup.get(pid)
            pname = p.get("name") if p else f"Player #{pid}"
            return f"Row {row_idx:5d} | [Award Winner] {pname} (PID: #{pid}) | Award #{aw_id} | Season {yr} | Comp #{cid}"

        # 10. League-Team Tournament Links (GdtI)
        elif table_sname == "GdtI":
            col_tid = tbl.columns_map.get("DPYU")
            col_lid = tbl.columns_map.get("eCpU")
            tid = col_tid.decode_value(rec) if col_tid else 0
            lid = col_lid.decode_value(rec) if col_lid else 0
            tname = get_team_name(tid)
            return f"Row {row_idx:5d} | [League Link] {tname} (ID: #{tid}) in League #{lid}"

        # 11. Default Tactical Formations & Lineups (qdZF)
        elif table_sname == "qdZF":
            col_tid = tbl.columns_map.get("mCXg")
            col_fid = tbl.columns_map.get("aQrQ")
            tid = col_tid.decode_value(rec) if col_tid else 0
            fid = col_fid.decode_value(rec) if col_fid else 0
            tname = get_team_name(tid)
            return f"Row {row_idx:5d} | [Formation Lineup] {tname} (ID: #{tid}) | Formation Preset #{fid}"

        # 12. Team Captains & Set-Piece Roles (YNEf)
        elif table_sname == "YNEf":
            col_cap = tbl.columns_map.get("kOha")
            col_fk = tbl.columns_map.get("dUxb")
            col_pen = tbl.columns_map.get("Xxmh")
            cap = col_cap.decode_value(rec) if col_cap else 0
            fk = col_fk.decode_value(rec) if col_fk else 0
            pen = col_pen.decode_value(rec) if col_pen else 0
            cap_p = self.players_lookup.get(cap)
            cname = cap_p.get("name") if cap_p else f"PID #{cap}"
            return f"Row {row_idx:5d} | [Set Pieces] Captain: {cname} | Free Kick: PID #{fk} | Penalty: PID #{pen}"

        # 13. Stadium Ultras Banners & Club Flags (WFUF)
        elif table_sname == "WFUF":
            col_tid = tbl.columns_map.get("daCW")
            col_slot = tbl.columns_map.get("lCau")
            col_tex = tbl.columns_map.get("RdTL")
            tid = col_tid.decode_value(rec) if col_tid else 0
            slot = col_slot.decode_value(rec) if col_slot else 0
            tex = col_tex.decode_value(rec) if col_tex else 0
            tname = get_team_name(tid)
            return f"Row {row_idx:5d} | [Ultras Banner] {tname} (ID: #{tid}) | Slot #{slot} | Texture #{tex}"

        # 14. Official Matchday Balls Catalog (nhky)
        elif table_sname == "nhky":
            col_bid = tbl.columns_map.get("gDDc")
            col_def = tbl.columns_map.get("FCfB")
            bid = col_bid.decode_value(rec) if col_bid else 0
            is_def = "Default Ball" if (col_def and col_def.decode_value(rec)) else "Custom Model"
            return f"Row {row_idx:5d} | [Match Ball] Ball Asset ID: #{bid} ({is_def})"

        # 15. Authentic Boots & Footwear Catalog (RMfq)
        elif table_sname == "RMfq":
            col_bid = tbl.columns_map.get("AsxF")
            col_brand = tbl.columns_map.get("yPLv")
            bid = col_bid.decode_value(rec) if col_bid else 0
            brand = col_brand.decode_value(rec) if col_brand else 0
            return f"Row {row_idx:5d} | [Footwear] Boot Model ID: #{bid} | Brand ID: #{brand}"

        # 16. Licensed Match Officials & Referees (xgkO)
        elif table_sname == "xgkO":
            col_rid = tbl.columns_map.get("eQzB")
            col_nat = tbl.columns_map.get("uvPU")
            col_str = tbl.columns_map.get("cveS")
            rid = col_rid.decode_value(rec) if col_rid else 0
            nat = col_nat.decode_value(rec) if col_nat else 0
            strict = col_str.decode_value(rec) if col_str else 0
            return f"Row {row_idx:5d} | [Referee] Official ID: #{rid} | Nationality: #{nat} | Strictness: #{strict}"

        # 17. Active Squad Transfers & Roster Links (rIsB)
        elif table_sname == "rIsB":
            col_pid = tbl.columns_map.get("wDHM")
            col_hash = tbl.columns_map.get("ykFq")
            pid = col_pid.decode_value(rec) if col_pid else 0
            lhash = col_hash.decode_value(rec) if col_hash else 0
            p = self.players_lookup.get(pid)
            pname = p.get("name") if p else f"Player #{pid}"
            club = p.get("club") if p else "Transfer Link"
            return f"Row {row_idx:5d} | [Transfer Link] {pname} (PID: #{pid})  -  {club} (Link: #{lhash})"

        # 18. Stadium Names & Home Venues (kISL)
        elif table_sname == "kISL":
            col = tbl.columns_map.get("fwCQ")
            sname = col.decode_value(rec).lstrip("_").strip() if col else "Default Stadium"
            lyxl = self.db.tables_map.get("lyxL")
            tname = f"Venue #{row_idx}"
            if lyxl and row_idx < len(lyxl.records):
                col_t = lyxl.columns_map.get("IOSv")
                if col_t:
                    tname = col_t.decode_value(lyxl.records[row_idx])
            return f"Row {row_idx:5d} | [Stadium] {sname}  -  Home Venue of: {tname} (ID: #{row_idx})"

        # 19. Authentic Managers (Knen)
        elif table_sname == "Knen":
            col_c = tbl.columns_map.get("EveZ")
            col_f = tbl.columns_map.get("OoQO")
            col_l = tbl.columns_map.get("aArc")
            col_a = tbl.columns_map.get("tFVQ")
            col_n = tbl.columns_map.get("mIlz")
            col_t = tbl.columns_map.get("qwYd")
            comm = col_c.decode_value(rec) if col_c else ""
            first = col_f.decode_value(rec) if col_f else ""
            last = col_l.decode_value(rec) if col_l else ""
            name = comm or f"{first} {last}".strip() or f"Manager #{row_idx}"
            aid = col_a.decode_value(rec) if col_a else 0
            nid = col_n.decode_value(rec) if col_n else 0
            tid = col_t.decode_value(rec) if col_t else 0
            team_str = f" | Team: {get_team_name(tid)} ({tid})" if tid > 0 else ""
            return f"Row {row_idx:4d} | [Manager] {name} | Head Asset: #{aid} | Nat: #{nid}{team_str}"

        # 20. Tactical Coaching Staff & Trainers (Vmkr)
        elif table_sname == "Vmkr":
            col = tbl.columns_map.get("fwCQ")
            col_sal = tbl.columns_map.get("xpDJ")
            mname = col.decode_value(rec) if col else f"Coach Staff #{row_idx}"
            sal = col_sal.decode_value(rec) if col_sal else 0
            return f"Row {row_idx:5d} | [Coach Staff] {mname} | Salary: EUR {sal:,}"

        # 21. PlayStyles & Gameplay Perks (SPTx)
        elif table_sname == "SPTx":
            col_pid = tbl.columns_map.get("pXwC")
            col_plus = tbl.columns_map.get("JAOM")
            col_tier = tbl.columns_map.get("KTDQ")
            col_cat = tbl.columns_map.get("RzAo")
            pid = col_pid.decode_value(rec) if col_pid else row_idx
            is_plus = "Gold [Plus]" if (col_plus and col_plus.decode_value(rec)) else "Silver [Standard]"
            tier = col_tier.decode_value(rec) if col_tier else 1
            cat = col_cat.decode_value(rec) if col_cat else 0
            return f"Row {row_idx:3d} | [PlayStyle #{pid}] Tier: {is_plus} (Level {tier}) | Category #{cat}"

        # 22. User Gameplay Preferences & Controls (PViY)
        elif table_sname == "PViY":
            col_mode = tbl.columns_map.get("CxKn")
            col_cam = tbl.columns_map.get("XuPr")
            col_cfg = tbl.columns_map.get("NuNs")
            mode = col_mode.decode_value(rec) if col_mode else "DEFAULT"
            cam = col_cam.decode_value(rec) if col_cam else 0
            cfg = col_cfg.decode_value(rec) if col_cfg else 0
            return f"Row {row_idx:4d} | [Gameplay Config] Mode: {mode} | Camera: #{cam} | Controller: #{cfg}"

        # 23. Official Brand & Commercial Sponsors (xuka)
        elif table_sname == "xuka":
            col_b = tbl.columns_map.get("roOU")
            col_c = tbl.columns_map.get("yeEP")
            col_t = tbl.columns_map.get("CkjP")
            bname = col_b.decode_value(rec) if col_b else f"Commercial Partner #{row_idx}"
            cat = col_c.decode_value(rec) if col_c else "Commercial"
            tier = col_t.decode_value(rec) if col_t else 1
            return f"Row {row_idx:4d} | [Brand Partner] {bname} ({cat}) | Tier Level: #{tier}"

        # 24. Goal Net Colors & Mesh Types (SizI)
        elif table_sname == "SizI":
            col_m = tbl.columns_map.get("jmFE")
            col_c = tbl.columns_map.get("mlkc")
            col_s = tbl.columns_map.get("nBFz")
            mesh = col_m.decode_value(rec) if col_m else 0
            color = col_c.decode_value(rec) if col_c else 0
            stripe = col_s.decode_value(rec) if col_s else 0
            return f"Row {row_idx:4d} | [Goal Net] Mesh Type: #{mesh} | Net RGB: #{color:06X} | Stripe RGB: #{stripe:04X}"

        # 25. Goalpost Nets & Styling Mesh (Qxjv)
        elif table_sname == "Qxjv":
            col_d = tbl.columns_map.get("AqxB")
            col_s = tbl.columns_map.get("LBdc")
            col_st = tbl.columns_map.get("vvGh")
            col_t = tbl.columns_map.get("hHvj")
            depth = col_d.decode_value(rec) if col_d else 0
            shape = col_s.decode_value(rec) if col_s else 0
            stanch = col_st.decode_value(rec) if col_st else 0
            tension = col_t.decode_value(rec) if col_t else 0
            return f"Row {row_idx:4d} | [Goalpost Net] Depth: #{depth} | Mesh Shape: #{shape} | Stanchion: #{stanch} | Tension: #{tension}"

        # 26. Stadium Geometry & Lighting Presets (sloG)
        elif table_sname == "sloG":
            col_sid = tbl.columns_map.get("mCXg")
            col_light = tbl.columns_map.get("cCBB")
            col_w = tbl.columns_map.get("SPRd")
            sid = col_sid.decode_value(rec) if col_sid else row_idx
            light = col_light.decode_value(rec) if col_light else 0
            w = col_w.decode_value(rec) if col_w else 0
            return f"Row {row_idx:3d} | [Stadium Lighting] Venue: #{sid} | Lighting Preset: #{light} | Weather Profile: #{w}"

        # 27. Career Inbox & Notifications (Zeam)
        elif table_sname == "Zeam":
            col_typ = tbl.columns_map.get("NKtA")
            col_urg = tbl.columns_map.get("FyBC")
            col_pid = tbl.columns_map.get("hzFG")
            col_tid = tbl.columns_map.get("kGOK")
            ntype = col_typ.decode_value(rec) if col_typ else 0
            urg = "High Priority" if (col_urg and col_urg.decode_value(rec)) else "Normal"
            pid = col_pid.decode_value(rec) if col_pid else 0
            tid = col_tid.decode_value(rec) if col_tid else 0
            p_str = f" | Player: PID #{pid}" if pid > 0 else ""
            t_str = f" | Team: {get_team_name(tid)}" if tid > 0 else ""
            return f"Row {row_idx:4d} | [Inbox Message] Type: #{ntype} ({urg}){p_str}{t_str}"

        # 28. Transfer Records & Historic Market Moves (eqXx)
        elif table_sname == "eqXx":
            col_pid = tbl.columns_map.get("mCXg")
            col_src = tbl.columns_map.get("sNZW")
            col_dst = tbl.columns_map.get("ykrW")
            col_fee = tbl.columns_map.get("lVDX")
            pid = col_pid.decode_value(rec) if col_pid else 0
            src = col_src.decode_value(rec) if col_src else 0
            dst = col_dst.decode_value(rec) if col_dst else 0
            fee = col_fee.decode_value(rec) if col_fee else 0
            p = self.players_lookup.get(pid)
            pname = p.get("name") if p else f"PID #{pid}"
            return f"Row {row_idx:3d} | [Transfer Record] {pname} : {get_team_name(src)} -> {get_team_name(dst)} | Fee: EUR {fee:,}K"

        # 29. News Feed Articles & Media Press (brHl)
        elif table_sname == "brHl":
            col_cat = tbl.columns_map.get("zdlB")
            col_tid = tbl.columns_map.get("myaC")
            col_pid = tbl.columns_map.get("qaaE")
            cat = col_cat.decode_value(rec) if col_cat else 0
            tid = col_tid.decode_value(rec) if col_tid else 0
            pid = col_pid.decode_value(rec) if col_pid else 0
            t_str = f"Club: {get_team_name(tid)}" if tid > 0 else "Worldwide News"
            p_str = f" | PID #{pid}" if pid > 0 else ""
            return f"Row {row_idx:4d} | [Press Article] {t_str}{p_str} | Category #{cat}"

        # 30. League Standings & Table Points (yAGl)
        elif table_sname == "yAGl":
            col_tid = tbl.columns_map.get("zoID")
            col_pts = tbl.columns_map.get("JtVK")
            col_p = tbl.columns_map.get("CgfB")
            col_w = tbl.columns_map.get("kXOE")
            col_d = tbl.columns_map.get("TMoF")
            col_l = tbl.columns_map.get("LGyG")
            col_gd = tbl.columns_map.get("bLBP")
            tid = col_tid.decode_value(rec) if col_tid else row_idx
            pts = col_pts.decode_value(rec) if col_pts else 0
            p = col_p.decode_value(rec) if col_p else 0
            w = col_w.decode_value(rec) if col_w else 0
            d = col_d.decode_value(rec) if col_d else 0
            l = col_l.decode_value(rec) if col_l else 0
            gd = col_gd.decode_value(rec) if col_gd else 0
            return f"Row {row_idx:2d} | [Standing] {get_team_name(tid)} : {pts} Pts | P:{p} W:{w} D:{d} L:{l} (GD: {gd:+d})"

        # 31. Calculated Overall Ratings (kgGh)
        elif table_sname == "kgGh":
            col_pos = tbl.columns_map.get("naWP")
            col_ovr = tbl.columns_map.get("XbPb")
            col_rep = tbl.columns_map.get("LBdc")
            pos = col_pos.decode_value(rec) if col_pos else 0
            ovr = col_ovr.decode_value(rec) if col_ovr else 0
            rep = col_rep.decode_value(rec) if col_rep else 0
            pos_name = get_position_name(pos)
            return f"Row {row_idx:4d} | [OVR Calc] Position: {pos_name} ({pos}) | Calculated Rating: {ovr} OVR | Rep Boost: +{rep}"

        # 32. Player Contracts, Wages & Clauses (AGmV)
        elif table_sname == "AGmV":
            col_w = tbl.columns_map.get("EZGA")
            col_rel = tbl.columns_map.get("MVLC")
            col_yr = tbl.columns_map.get("VgjC")
            col_p0 = tbl.columns_map.get("bveC")
            wage = col_w.decode_value(rec) if col_w else 0
            rel = col_rel.decode_value(rec) if col_rel else 0
            yr = col_yr.decode_value(rec) if col_yr else 0
            pid0 = col_p0.decode_value(rec) if col_p0 else 0
            p = self.players_lookup.get(pid0)
            pname = p.get("name") if p else f"PID #{pid0}"
            rel_str = f" | Release Clause: EUR {rel:,}K" if rel > 0 else ""
            return f"Row {row_idx:4d} | [Contract] {pname} | Wage: EUR {wage:,}/wk | Until: {yr}{rel_str}"

        # Generic fallback for all other tables
        summary_cols = []
        for col in tbl.columns[:4]:
            val = col.decode_value(rec)
            col_name = get_column_display_name(col.sname).split(" (")[0]
            if "team" in col_name.lower() and isinstance(val, int) and val in TEAM_NAMES:
                summary_cols.append(f"{col_name}: {TEAM_NAMES[val]} ({val})")
            else:
                summary_cols.append(f"{col_name}: {val}")
        return f"Row {row_idx:5d} | " + " | ".join(summary_cols)

    def resolve_team_name(self, team_id: int) -> str:
        """Resolves team ID to team name."""
        if team_id is None or team_id < 0:
            return ""
        return get_team_name(team_id)

    def resolve_player_name(self, player_id: int) -> str:
        """Resolves player ID to player name and position."""
        if not player_id or player_id <= 0:
            return ""
        p = self.players_lookup.get(player_id)
        if p:
            pos = get_position_name(p.get("pos_code", -1))
            return f"{p['name']} ({pos}, {p.get('club', '')})"
        return f"PID #{player_id}"

    def resolve_nation_name(self, nation_id: int) -> str:
        """Resolves FIFA nation ID to country name."""
        if not nation_id or nation_id <= 0:
            return ""
        return get_nation_name(nation_id)

    def resolve_stadium_name(self, stadium_id: int) -> str:
        """Resolves stadium ID to venue name."""
        kisl = self.get_table("kISL")
        if kisl and 0 <= stadium_id < len(kisl.records):
            col_s = kisl.columns_map.get("fwCQ")
            if col_s:
                sname = col_s.decode_value(kisl.records[stadium_id]).lstrip("_").strip()
                if sname:
                    return sname
        return f"Stadium #{stadium_id}"

    def resolve_entity_reference(self, target_entity: str, val: Any) -> str:
        """Resolves an entity value based on target entity type."""
        try:
            ival = int(val)
        except (ValueError, TypeError):
            return ""
        if target_entity == "team":
            return self.resolve_team_name(ival)
        elif target_entity == "player":
            return self.resolve_player_name(ival)
        elif target_entity == "nation":
            return self.resolve_nation_name(ival)
        elif target_entity == "stadium":
            return self.resolve_stadium_name(ival)
        return ""

    def get_row_entity_header(self, table_sname: str, row_idx: int) -> Optional[str]:
        """Returns entity context header for the Record Inspector."""
        if table_sname == "CZUM" and row_idx < len(self.base_players_list):
            pid = self.base_players_list[row_idx]
            p = self.players_lookup.get(pid)
            if p:
                pos = get_position_name(p.get("pos_code", -1))
                return f"Player: {p['name']} ({pos})  -  {p['club']} (PID: {pid} | {p['overall']} OVR)"
        elif table_sname == "Knen":
            tbl = self.get_table("Knen")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                comm = tbl.columns_map.get("EveZ").decode_value(rec) if "EveZ" in tbl.columns_map else ""
                first = tbl.columns_map.get("OoQO").decode_value(rec) if "OoQO" in tbl.columns_map else ""
                last = tbl.columns_map.get("aArc").decode_value(rec) if "aArc" in tbl.columns_map else ""
                aid = tbl.columns_map.get("tFVQ").decode_value(rec) if "tFVQ" in tbl.columns_map else 0
                nid = tbl.columns_map.get("mIlz").decode_value(rec) if "mIlz" in tbl.columns_map else 0
                tid = tbl.columns_map.get("qwYd").decode_value(rec) if "qwYd" in tbl.columns_map else 0
                full_m = comm or f"{first} {last}".strip() or f"Manager #{row_idx}"
                t_str = f"  -  Team: {get_team_name(tid)}" if tid > 0 else ""
                return f"Manager: {full_m} (Head Asset: #{aid} | Nat: #{nid}){t_str}"
        elif table_sname == "lyxL":
            tbl = self.get_table("lyxL")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                tid = int.from_bytes(rec[:4], "little") & 0x7FFFFFFF
                col_t = tbl.columns_map.get("IOSv")
                tname = col_t.decode_value(rec) if col_t else get_team_name(tid)
                ovr = tbl.columns_map.get("sqCP").decode_value(rec) if "sqCP" in tbl.columns_map else 0
                att = tbl.columns_map.get("aDMz").decode_value(rec) if "aDMz" in tbl.columns_map else 0
                ucl = tbl.columns_map.get("Tsda").decode_value(rec) if "Tsda" in tbl.columns_map else 0
                star = tbl.columns_map.get("WLKn").decode_value(rec) if "WLKn" in tbl.columns_map else 0
                star_p = self.players_lookup.get(star)
                star_name = star_p.get("name") if star_p else f"PID #{star}"
                return f"Club: {tname} (ID: #{tid})  -  Rating: {ovr} OVR | {att} ATT  -  Star: {star_name} (UCL: {ucl})"
        elif table_sname == "mDGw":
            tbl = self.get_table("mDGw")
            lyxl = self.get_table("lyxL")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                tid = (int.from_bytes(lyxl.records[row_idx][:4], "little") & 0x7FFFFFFF) if lyxl and row_idx < len(lyxl.records) else (row_idx + 1)
                tname = get_team_name(tid)
                stars = tbl.columns_map.get("pFxE").decode_value(rec) if "pFxE" in tbl.columns_map else 0.0
                form = tbl.columns_map.get("MZIF").decode_value(rec) if "MZIF" in tbl.columns_map else "4-3-3"
                return f"Club Tactical Profile: {tname} (ID: #{tid})  -  Star Rating: {stars} Stars  -  Preset: {form}"
        elif table_sname == "onMQ":
            tbl = self.get_table("onMQ")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                lname = tbl.columns_map.get("FtgW").decode_value(rec) if "FtgW" in tbl.columns_map else "League"
                lid = tbl.columns_map.get("aQrQ").decode_value(rec) if "aQrQ" in tbl.columns_map else row_idx
                tier = tbl.columns_map.get("paPI").decode_value(rec) if "paPI" in tbl.columns_map else 1
                num_t = tbl.columns_map.get("WDGJ").decode_value(rec) if "WDGJ" in tbl.columns_map else 0
                return f"Domestic League: {lname} (League ID: #{lid})  -  Tier {tier} ({num_t} member clubs)"
        elif table_sname == "ImNE":
            tbl = self.get_table("ImNE")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                cname = tbl.columns_map.get("QmlU").decode_value(rec) if "QmlU" in tbl.columns_map else "Club"
                budget = tbl.columns_map.get("Ibup").decode_value(rec) if "Ibup" in tbl.columns_map else 0
                sid = tbl.columns_map.get("MYrf").decode_value(rec) if "MYrf" in tbl.columns_map else 0
                return f"Career Finances: {cname}  -  Starting Transfer Budget: EUR {budget:,}K  -  Home Venue: #{sid}"
        elif table_sname == "nrFl":
            tbl = self.get_table("nrFl")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                pid = tbl.columns_map.get("mCXg").decode_value(rec) if "mCXg" in tbl.columns_map else 0
                aid = tbl.columns_map.get("Laxd").decode_value(rec) if "Laxd" in tbl.columns_map else 0
                hq = tbl.columns_map.get("McUr").decode_value(rec) if "McUr" in tbl.columns_map else 0
                p = self.players_lookup.get(pid)
                pname = p.get("name") if p else f"PID #{pid}"
                scan = "Authentic Starhead 3D Scan" if hq else "Generic Frostbite Face"
                return f"Starhead Model: {pname} (PID: #{pid})  -  Head Asset ID: #{aid} ({scan})"
        elif table_sname == "bneD":
            tbl = self.get_table("bneD")
            if tbl and row_idx < len(tbl.records):
                pname = tbl.columns_map.get("FuiB").decode_value(tbl.records[row_idx]) if "FuiB" in tbl.columns_map else ""
                return f"Audio Commentary Dictionary: '{pname}'"
        elif table_sname == "nQVU":
            tbl = self.get_table("nQVU")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                comm = tbl.columns_map.get("HdeP").decode_value(rec) if "HdeP" in tbl.columns_map else ""
                sur = tbl.columns_map.get("xnfZ").decode_value(rec) if "xnfZ" in tbl.columns_map else ""
                first = tbl.columns_map.get("kRfb").decode_value(rec) if "kRfb" in tbl.columns_map else ""
                pid = tbl.columns_map.get("ykFq").decode_value(rec) if "ykFq" in tbl.columns_map else 0
                full_n = comm or f"{first} {sur}".strip() or f"PID #{pid}"
                return f"Player Identity: {full_n} (PID: #{pid})  -  Kit Name: '{sur}'"
        elif table_sname == "UlaA":
            tbl = self.get_table("UlaA")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                pid = tbl.columns_map.get("mCXg").decode_value(rec) if "mCXg" in tbl.columns_map else 0
                aw = tbl.columns_map.get("xKVG").decode_value(rec) if "xKVG" in tbl.columns_map else 0
                yr = tbl.columns_map.get("BssH").decode_value(rec) if "BssH" in tbl.columns_map else 0
                p = self.players_lookup.get(pid)
                pname = p.get("name") if p else f"PID #{pid}"
                return f"Accolade Winner: {pname} (PID: #{pid})  -  Award #{aw} (Season {yr})"
        elif table_sname == "kISL":
            tbl = self.get_table("kISL")
            if tbl and row_idx < len(tbl.records):
                col_s = tbl.columns_map.get("fwCQ")
                sname = col_s.decode_value(tbl.records[row_idx]).lstrip("_").strip() if col_s else "Stadium"
                lyxl = self.get_table("lyxL")
                tname = f"Club #{row_idx}"
                if lyxl and row_idx < len(lyxl.records):
                    col_t = lyxl.columns_map.get("IOSv")
                    if col_t:
                        tname = col_t.decode_value(lyxl.records[row_idx])
                return f"Stadium: {sname}  -  Home Venue of: {tname}"
        elif table_sname == "SPTx":
            tbl = self.get_table("SPTx")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                pid = tbl.columns_map.get("pXwC").decode_value(rec) if "pXwC" in tbl.columns_map else row_idx
                is_plus = "Gold [Plus]" if ("JAOM" in tbl.columns_map and tbl.columns_map.get("JAOM").decode_value(rec)) else "Silver [Standard]"
                return f"PlayStyle Perk #{pid}  -  Tier: {is_plus} (Gameplay Signature Perk)"
        elif table_sname == "AGmV":
            tbl = self.get_table("AGmV")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                p0 = tbl.columns_map.get("bveC").decode_value(rec) if "bveC" in tbl.columns_map else 0
                w = tbl.columns_map.get("EZGA").decode_value(rec) if "EZGA" in tbl.columns_map else 0
                yr = tbl.columns_map.get("VgjC").decode_value(rec) if "VgjC" in tbl.columns_map else 0
                p = self.players_lookup.get(p0)
                pname = p.get("name") if p else f"PID #{p0}"
                return f"Player Contract: {pname} (PID: #{p0})  -  Weekly Wage: EUR {w:,}  -  Valid Until: {yr}"
        elif table_sname == "eqXx":
            tbl = self.get_table("eqXx")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                pid = tbl.columns_map.get("mCXg").decode_value(rec) if "mCXg" in tbl.columns_map else 0
                src = tbl.columns_map.get("sNZW").decode_value(rec) if "sNZW" in tbl.columns_map else 0
                dst = tbl.columns_map.get("ykrW").decode_value(rec) if "ykrW" in tbl.columns_map else 0
                fee = tbl.columns_map.get("lVDX").decode_value(rec) if "lVDX" in tbl.columns_map else 0
                p = self.players_lookup.get(pid)
                pname = p.get("name") if p else f"PID #{pid}"
                return f"Transfer Move: {pname}  -  {get_team_name(src)} to {get_team_name(dst)} (Fee: EUR {fee:,}K)"
        elif table_sname == "yAGl":
            tbl = self.get_table("yAGl")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                tid = tbl.columns_map.get("zoID").decode_value(rec) if "zoID" in tbl.columns_map else row_idx
                pts = tbl.columns_map.get("JtVK").decode_value(rec) if "JtVK" in tbl.columns_map else 0
                p = tbl.columns_map.get("CgfB").decode_value(rec) if "CgfB" in tbl.columns_map else 0
                w = tbl.columns_map.get("kXOE").decode_value(rec) if "kXOE" in tbl.columns_map else 0
                return f"League Table Standings: {get_team_name(tid)}  -  {pts} Points ({w} wins in {p} matches)"
        elif table_sname == "xuka":
            tbl = self.get_table("xuka")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                bname = tbl.columns_map.get("roOU").decode_value(rec) if "roOU" in tbl.columns_map else f"Partner #{row_idx}"
                cat = tbl.columns_map.get("yeEP").decode_value(rec) if "yeEP" in tbl.columns_map else "Commercial"
                return f"Commercial Brand Partner: {bname} (Category: {cat})  -  Official Sponsor"
        elif table_sname == "SizI":
            tbl = self.get_table("SizI")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                mesh = tbl.columns_map.get("jmFE").decode_value(rec) if "jmFE" in tbl.columns_map else 0
                col = tbl.columns_map.get("mlkc").decode_value(rec) if "mlkc" in tbl.columns_map else 0
                return f"Goalpost Net Configuration: Mesh Style #{mesh}  -  Hex Primary Color #{col:06X}"
        elif table_sname == "Zeam":
            tbl = self.get_table("Zeam")
            if tbl and row_idx < len(tbl.records):
                rec = tbl.records[row_idx]
                ntype = tbl.columns_map.get("NKtA").decode_value(rec) if "NKtA" in tbl.columns_map else 0
                urg = "Urgent / Action Required" if ("FyBC" in tbl.columns_map and tbl.columns_map.get("FyBC").decode_value(rec)) else "Standard Notification"
                return f"Career Mode Inbox: Message Type #{ntype} ({urg})"
        return None
