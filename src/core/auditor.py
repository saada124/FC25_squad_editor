"""
Squad Health & Rule Auditor for FC 25 Squad Studio.
Validates roster sizes, goalkeeper depth, jersey number conflicts, and starting lineup assignments.
Provides automated conflict resolution and emergency signings.
Strict Zero Emojis Policy Enforced.
"""

from typing import Dict, Any, List, Optional, Tuple, Set

def audit_team_squad(session: Any, team_id: int) -> Dict[str, Any]:
    """
    Performs comprehensive pre-flight sanity checks on a club squad.
    Returns health status ('healthy', 'warning', 'error'), issue details, and stats.
    """
    team_name = session.resolve_team_name(team_id) if hasattr(session, "resolve_team_name") else f"Team #{team_id}"
    roster = session.team_rosters.get(team_id, [])
    roster_count = len(roster)

    issues: List[Dict[str, str]] = []
    
    # 1. Roster Size Check
    if roster_count < 18:
        issues.append({
            "code": "ROSTER_MIN",
            "severity": "error",
            "message": f"Roster size is critically low: {roster_count} players (minimum required by engine: 18)."
        })
    elif roster_count < 20:
        issues.append({
            "code": "ROSTER_SHALLOW",
            "severity": "warning",
            "message": f"Roster size is shallow: {roster_count} players (recommended: 22+)."
        })
    elif roster_count > 52:
        issues.append({
            "code": "ROSTER_MAX",
            "severity": "error",
            "message": f"Roster exceeds maximum allowed: {roster_count} players (maximum allowed by engine: 52)."
        })
    elif roster_count > 42:
        issues.append({
            "code": "ROSTER_LARGE",
            "severity": "warning",
            "message": f"Roster is very large: {roster_count} players (risk of clutter)."
        })

    # 2. Goalkeeper Depth Check
    gk_players: List[int] = []
    for pid in roster:
        p = session.players_lookup.get(pid, {})
        pos_code = p.get("pos_code", -1)
        if pos_code == 0 or p.get("preferredposition1") == 0 or p.get("position") == "GK":
            gk_players.append(pid)

    gk_count = len(gk_players)
    if gk_count < 1:
        issues.append({
            "code": "GK_ZERO",
            "severity": "error",
            "message": "Critical: Zero registered Goalkeepers in squad. Matches will forfeit."
        })
    elif gk_count == 1:
        issues.append({
            "code": "GK_MIN",
            "severity": "warning",
            "message": "Only 1 Goalkeeper registered. Minimum 2 required to prevent simulation forfeit upon injury/red card."
        })

    # 3. Jersey Number Conflict Check
    jerseys: Dict[int, List[int]] = {}
    for pid in roster:
        jnum = session.get_player_jersey_number(pid)
        if jnum > 0:
            if jnum not in jerseys:
                jerseys[jnum] = []
            jerseys[jnum].append(pid)

    duplicate_jerseys: Dict[int, List[int]] = {j: pids for j, pids in jerseys.items() if len(pids) > 1}
    for jnum, pids in duplicate_jerseys.items():
        player_names = []
        for pid in pids:
            p_data = session.players_lookup.get(pid, {})
            player_names.append(p_data.get("name", f"PID #{pid}"))
        names_str = " and ".join(player_names)
        issues.append({
            "code": "JERSEY_DUP",
            "severity": "error",
            "message": f"Duplicate jersey number #{jnum} assigned to: {names_str}."
        })

    # 4. Starting Lineup & Tactics Validation
    lineup_info = session.get_team_lineup(team_id) if hasattr(session, "get_team_lineup") else {}
    starters = lineup_info.get("starters", [])
    if len(starters) < 11 and roster_count >= 11:
        issues.append({
            "code": "LINEUP_INCOMPLETE",
            "severity": "warning",
            "message": f"Starting XI has only {len(starters)} of 11 positions filled."
        })

    # Determine Overall Health Status
    has_error = any(it["severity"] == "error" for it in issues)
    has_warning = any(it["severity"] == "warning" for it in issues)
    status = "error" if has_error else ("warning" if has_warning else "healthy")

    return {
        "team_id": team_id,
        "team_name": team_name,
        "status": status,
        "issues": issues,
        "roster_count": roster_count,
        "gk_count": gk_count,
        "duplicate_jerseys": duplicate_jerseys
    }


def audit_entire_database(session: Any) -> List[Dict[str, Any]]:
    """
    Audits all indexed clubs in the database and returns a sorted list of teams with issues.
    Prioritizes errors first, followed by warnings.
    """
    flagged: List[Dict[str, Any]] = []
    teams = getattr(session, "teams_cache", [])
    for t in teams:
        tid = t.get("teamid", 0)
        if tid <= 0:
            continue
        audit = audit_team_squad(session, tid)
        if audit["status"] != "healthy":
            flagged.append(audit)

    # Sort: errors first, then warnings, then by issue count descending
    flagged.sort(key=lambda a: (0 if a["status"] == "error" else 1, -len(a["issues"])))
    return flagged


def resolve_duplicate_jersey_numbers(session: Any, team_id: int) -> int:
    """
    Automatically resolves duplicate jersey numbers for a team.
    Keeps the jersey number for the higher-rated or first player, and assigns the lowest
    unused number between 1 and 99 to the other conflicting players.
    Returns the count of players renumbered.
    """
    roster = session.team_rosters.get(team_id, [])
    if not roster:
        return 0

    assigned_jerseys: Set[int] = set()
    player_jerseys: Dict[int, int] = {}
    jersey_holders: Dict[int, List[int]] = {}

    for pid in roster:
        j = session.get_player_jersey_number(pid)
        player_jerseys[pid] = j
        if j > 0:
            if j not in jersey_holders:
                jersey_holders[j] = []
            jersey_holders[j].append(pid)

    fixed_count = 0
    # Collect all currently used jersey numbers
    used_numbers = set(j for j in player_jerseys.values() if j > 0)

    for jnum, pids in jersey_holders.items():
        if len(pids) <= 1:
            continue

        # Sort conflicting players by overall rating descending: keep highest rated with the number
        pids_sorted = sorted(
            pids,
            key=lambda p: session.players_lookup.get(p, {}).get("overall", 50),
            reverse=True
        )

        # First player keeps the number
        for conflicting_pid in pids_sorted[1:]:
            # Find next free number in 1..99
            new_num = 1
            while new_num in used_numbers and new_num <= 99:
                new_num += 1

            if new_num <= 99:
                session.set_player_jersey_number(conflicting_pid, new_num, track=True)
                used_numbers.add(new_num)
                fixed_count += 1

    return fixed_count


def assign_emergency_goalkeeper(session: Any, team_id: int) -> Optional[int]:
    """
    Finds the highest-rated available Free Agent Goalkeeper and transfers them
    to the target team, assigning a free jersey number.
    Returns the player ID of the signed goalkeeper, or None if none available.
    """
    candidates: List[Dict[str, Any]] = []
    for p in session.players_cache:
        if p.get("teamid") in (0, 111592):
            pos = p.get("position", "")
            pos_code = p.get("pos_code", -1)
            if pos == "GK" or pos_code == 0:
                candidates.append(p)

    if not candidates:
        return None

    # Pick top-rated free agent goalkeeper
    candidates.sort(key=lambda p: (p.get("overall", 0), p.get("potential", 0)), reverse=True)
    best_gk = candidates[0]
    gk_pid = best_gk["playerid"]

    # Transfer player to target club
    session.transfer_player(gk_pid, team_id, track=True)

    # Resolve jersey number: pick 1 if free, otherwise 13, 25, or lowest free
    roster = session.team_rosters.get(team_id, [])
    used_numbers = set(session.get_player_jersey_number(p) for p in roster if p != gk_pid)
    preferred_gk_nums = [1, 13, 25, 12, 16, 22, 30, 31]
    chosen_num = None
    for n in preferred_gk_nums:
        if n not in used_numbers:
            chosen_num = n
            break

    if chosen_num is None:
        for n in range(1, 100):
            if n not in used_numbers:
                chosen_num = n
                break

    if chosen_num:
        session.set_player_jersey_number(gk_pid, chosen_num, track=True)

    return gk_pid
