"""
Team mappings and relationships for EA Sports FC 25.
Maps secondary/women's teams (which share identical string names in table lyxL)
to their primary/parent clubs for asset inheritance, search differentiation,
and roster assignments.
"""

from typing import Dict, Set, Optional

# Mapping of Secondary/Women's Team ID -> Primary/Men's Team ID
# Contains both authentic 4-byte Frostbite IDs (>= 65536) and truncated legacy IDs.
SECONDARY_TO_PRIMARY_TEAMS: Dict[int, int] = {
    131124: 1334,     # Finland (Authentic)
    52: 1334,     # Finland (Legacy)
    131358: 234,     # SL Benfica (Authentic)
    286: 234,     # SL Benfica (Legacy)
    131359: 245,     # Ajax (Authentic)
    287: 245,     # Ajax (Legacy)
    131360: 266,     # Slavia Praha (Authentic)
    288: 266,     # Slavia Praha (Legacy)
    131361: 894,     # FC Zürich (Authentic)
    289: 894,     # FC Zürich (Legacy)
    131368: 46056,     # Free Agents (Authentic)
    296: 46056,     # Free Agents (Legacy)
    131391: 45296,     # Granada CF (Authentic)
    319: 45296,     # Granada CF (Legacy)
    131720: 242,     # RC Deportivo (Authentic)
    648: 242,     # RC Deportivo (Legacy)
    131724: 76,     # Strasbourg (Authentic)
    652: 76,     # Strasbourg (Legacy)
    131725: 1799,     # Crystal Palace (Authentic)
    653: 1799,     # Crystal Palace (Legacy)
    131733: 452,     # RCD Espanyol (Authentic)
    661: 452,     # RCD Espanyol (Legacy)
    111325: 1891,     # Nacional (Authentic)
    45789: 1891,     # Nacional (Legacy)
    112615: 35549,     # Racing Club (Authentic)
    47079: 35549,     # Racing Club (Legacy)
    113002: 1318,     # England (Authentic)
    47466: 1318,     # England (Legacy)
    113003: 1335,     # France (Authentic)
    47467: 1335,     # France (Legacy)
    113004: 1337,     # Germany (Authentic)
    47468: 1337,     # Germany (Legacy)
    113007: 1352,     # Norway (Authentic)
    47471: 1352,     # Norway (Legacy)
    113008: 1363,     # Sweden (Authentic)
    47472: 1363,     # Sweden (Legacy)
    113009: 1387,     # United States (Authentic)
    47473: 1387,     # United States (Legacy)
    113010: 1386,     # Mexico (Authentic)
    47474: 1386,     # Mexico (Legacy)
    113011: 39499,     # Netherlands (Authentic)
    47475: 39499,     # Netherlands (Legacy)
    113012: 1362,     # Spain (Authentic)
    47476: 1362,     # Spain (Legacy)
    113984: 1359,     # Scotland (Authentic)
    48448: 1359,     # Scotland (Legacy)
    113996: 1369,     # Argentina (Authentic)
    48460: 1369,     # Argentina (Legacy)
    115682: 1354,     # Portugal (Authentic)
    50146: 1354,     # Portugal (Legacy)
    115995: 21,     # FC Bayern München (Authentic)
    50459: 21,     # FC Bayern München (Legacy)
    115996: 32,     # Leverkusen (Authentic)
    50460: 32,     # Leverkusen (Legacy)
    115997: 1824,     # Frankfurt (Authentic)
    50461: 1824,     # Frankfurt (Legacy)
    115998: 175,     # VfL Wolfsburg (Authentic)
    50462: 175,     # VfL Wolfsburg (Legacy)
    115999: 10029,     # TSG Hoffenheim (Authentic)
    50463: 10029,     # TSG Hoffenheim (Legacy)
    116002: 25,     # SC Freiburg (Authentic)
    50466: 25,     # SC Freiburg (Legacy)
    116003: 31,     # 1. FC Köln (Authentic)
    50467: 31,     # 1. FC Köln (Legacy)
    116004: 38,     # SV Werder Bremen (Authentic)
    50468: 38,     # SV Werder Bremen (Legacy)
    116009: 1,     # Arsenal (Authentic)
    50473: 1,     # Arsenal (Legacy)
    116010: 5,     # Chelsea (Authentic)
    50474: 5,     # Chelsea (Legacy)
    116011: 18,     # Spurs (Authentic)
    50475: 18,     # Spurs (Legacy)
    116013: 1808,     # Brighton (Authentic)
    50477: 1808,     # Brighton (Legacy)
    116014: 19,     # West Ham (Authentic)
    50478: 19,     # West Ham (Legacy)
    116015: 2,     # Aston Villa (Authentic)
    50479: 2,     # Aston Villa (Legacy)
    116016: 7,     # Everton (Authentic)
    50480: 7,     # Everton (Legacy)
    116017: 10,     # Manchester City (Authentic)
    50481: 10,     # Manchester City (Legacy)
    116020: 95,     # Leicester City (Authentic)
    50484: 95,     # Leicester City (Legacy)
    116021: 46636,     # RB Leipzig (Authentic)
    50485: 46636,     # RB Leipzig (Legacy)
    116033: 66,     # OL (Authentic)
    50497: 66,     # OL (Legacy)
    116034: 73,     # Paris SG (Authentic)
    50498: 73,     # Paris SG (Legacy)
    116035: 46281,     # Paris FC (Authentic)
    50499: 46281,     # Paris FC (Legacy)
    116037: 70,     # Montpellier (Authentic)
    50501: 70,     # Montpellier (Legacy)
    116040: 379,     # Stade de Reims (Authentic)
    50504: 379,     # Stade de Reims (Legacy)
    116042: 62,     # En Avant Guingamp (Authentic)
    50506: 62,     # En Avant Guingamp (Legacy)
    116280: 45,     # Juventus (Authentic)
    50744: 45,     # Juventus (Legacy)
    116325: 241,     # FC Barcelona (Authentic)
    50789: 241,     # FC Barcelona (Legacy)
    116327: 240,     # Atlético de Madrid (Authentic)
    50791: 240,     # Atlético de Madrid (Legacy)
    116328: 448,     # Athletic Club (Authentic)
    50792: 448,     # Athletic Club (Legacy)
    116330: 449,     # Real Betis (Authentic)
    50794: 449,     # Real Betis (Legacy)
    116331: 467,     # SD Eibar (Authentic)
    50795: 467,     # SD Eibar (Legacy)
    116333: 1853,     # Levante UD (Authentic)
    50797: 1853,     # Levante UD (Legacy)
    116336: 457,     # Real Sociedad (Authentic)
    50800: 457,     # Real Sociedad (Legacy)
    116337: 481,     # Sevilla FC (Authentic)
    50801: 481,     # Sevilla FC (Legacy)
    116339: 461,     # Valencia CF (Authentic)
    50803: 461,     # Valencia CF (Legacy)
    116343: 9,     # Liverpool (Authentic)
    50807: 9,     # Liverpool (Legacy)
    116416: 1738,     # Havre AC (Authentic)
    50880: 1738,     # Havre AC (Legacy)
    116417: 71,     # FC Nantes (Authentic)
    50881: 71,     # FC Nantes (Legacy)
    116428: 1341,     # Iceland (Authentic)
    50892: 1341,     # Iceland (Legacy)
}

# Reverse mapping: Primary/Men's Team ID -> Secondary/Women's Team ID
PRIMARY_TO_SECONDARY_TEAMS: Dict[int, int] = {v: k for k, v in SECONDARY_TO_PRIMARY_TEAMS.items()}

# Set of all Secondary/Women's Team IDs
SECONDARY_TEAM_IDS: Set[int] = set(SECONDARY_TO_PRIMARY_TEAMS.keys())

# Standalone women's clubs (do not have a men's duplicate in lyxL)
STANDALONE_WOMEN_TEAMS: Set[int] = {
    131362,  # FC Rosengård (Authentic)
    290,  # FC Rosengård (Legacy)
    131363,  # Glasgow City FC (Authentic)
    291,  # Glasgow City FC (Legacy)
    131477,  # Bay FC (Authentic)
    405,  # Bay FC (Legacy)
    131478,  # Utah Royals FC (Authentic)
    406,  # Utah Royals FC (Legacy)
    116000,  # Turbine Potsdam (Authentic)
    50464,  # Turbine Potsdam (Legacy)
    116001,  # SGS Essen (Authentic)
    50465,  # SGS Essen (Legacy)
    116005,  # Carl Zeiss Jena (Authentic)
    50469,  # Carl Zeiss Jena (Legacy)
    116012,  # Manchester Utd (Authentic)
    50476,  # Manchester Utd (Legacy)
    116036,  # FC Fleury 91 (Authentic)
    50500,  # FC Fleury 91 (Legacy)
    116039,  # Dijon FCO (Authentic)
    50503,  # Dijon FCO (Legacy)
    116282,  # Roma (Authentic)
    50746,  # Roma (Legacy)
    116300,  # Seattle Reign (Authentic)
    50764,  # Seattle Reign (Legacy)
    116302,  # Portland Thorns (Authentic)
    50766,  # Portland Thorns (Legacy)
    116303,  # NC Courage (Authentic)
    50767,  # NC Courage (Legacy)
    116304,  # Washington Spirit (Authentic)
    50768,  # Washington Spirit (Legacy)
    116305,  # Chicago Stars FC (Authentic)
    50769,  # Chicago Stars FC (Legacy)
    116306,  # Houston Dash (Authentic)
    50770,  # Houston Dash (Legacy)
    116307,  # Orlando Pride (Authentic)
    50771,  # Orlando Pride (Legacy)
    116308,  # Rac. Louisville (Authentic)
    50772,  # Rac. Louisville (Legacy)
    116309,  # KC Current (Authentic)
    50773,  # KC Current (Legacy)
    116310,  # NJ/NY Gotham (Authentic)
    50774,  # NJ/NY Gotham (Legacy)
    116311,  # Angel City FC (Authentic)
    50775,  # Angel City FC (Legacy)
    116312,  # San Diego Wave (Authentic)
    50776,  # San Diego Wave (Legacy)
    116326,  # Real Madrid CF (Authentic)
    50790,  # Real Madrid CF (Legacy)
    116332,  # UD Tenerife (Authentic)
    50796,  # UD Tenerife (Legacy)
    116334,  # Madrid CFF (Authentic)
    50798,  # Madrid CFF (Legacy)
}

ALL_WOMEN_TEAM_IDS: Set[int] = SECONDARY_TEAM_IDS | STANDALONE_WOMEN_TEAMS


def get_parent_club_id(team_id: int) -> int:
    """Returns the parent Men's club ID for crest/asset inheritance, or team_id itself."""
    return SECONDARY_TO_PRIMARY_TEAMS.get(team_id, team_id)


def is_women_team(team_id: int, row_index: int = -1) -> bool:
    """Returns True if the team is a women's team."""
    if team_id in ALL_WOMEN_TEAM_IDS:
        return True
    # Rows 628..638 (national women) and 690..756 (club women) in table lyxL
    if 630 <= row_index <= 638 or 690 <= row_index <= 756:
        return True
    return False


def format_team_display_name(team_id: int, base_name: str, row_index: int = -1) -> str:
    """
    Formats the team display name so that secondary/women's teams
    are cleanly differentiated from the primary/men's teams.
    """
    clean_name = base_name.strip()
    if not clean_name:
        return clean_name
        
    if "(Women)" in clean_name or "Women" in clean_name or "Femení" in clean_name or "Féminin" in clean_name:
        return clean_name

    if team_id in SECONDARY_TEAM_IDS or (team_id in ALL_WOMEN_TEAM_IDS and "FC" not in clean_name and "City" not in clean_name):
        return f"{clean_name} (Women)"
        
    # National women's teams in rows 630..638
    if 630 <= row_index <= 638 or team_id in [113002, 113003, 113004, 113007, 113008, 113009, 113010, 113011, 113012, 113984, 113996, 115682, 131124, 116428, 47466, 47467, 47468, 47471, 47472, 47473, 47474, 47475, 47476]:
        return f"{clean_name} (Women)"

    return clean_name
