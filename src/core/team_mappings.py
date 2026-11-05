"""
Team mappings and relationships for EA Sports FC 25.
Maps secondary/women's teams (which share identical string names in table lyxL)
to their primary/parent clubs for asset inheritance, search differentiation,
and roster assignments.
"""

from typing import Dict, Set, Optional

# Mapping of Secondary/Women's Team ID -> Primary/Men's Team ID
SECONDARY_TO_PRIMARY_TEAMS: Dict[int, int] = {
    50467: 31,     # 1. FC Köln
    287: 245,      # Ajax
    48460: 1369,   # Argentina
    50473: 1,      # Arsenal
    50479: 2,      # Aston Villa
    50792: 448,    # Athletic Club
    50791: 240,    # Atlético de Madrid
    50477: 1808,   # Brighton
    50474: 5,      # Chelsea
    653: 1799,     # Crystal Palace
    50506: 62,     # En Avant Guingamp
    47466: 1318,   # England
    50480: 7,      # Everton
    50789: 241,    # FC Barcelona
    50459: 21,     # FC Bayern München
    50881: 71,     # FC Nantes
    289: 894,      # FC Zürich
    52: 1334,      # Finland
    47467: 1335,   # France
    50461: 1824,   # Frankfurt
    296: 46056,    # Free Agents
    47468: 1337,   # Germany
    319: 45296,    # Granada CF
    50880: 1738,   # Havre AC
    50892: 1341,   # Iceland
    50744: 45,     # Juventus
    50484: 95,     # Leicester City
    50797: 1853,   # Levante UD
    50460: 32,     # Leverkusen
    50807: 9,      # Liverpool
    50481: 10,     # Manchester City
    47474: 1386,   # Mexico
    50501: 70,     # Montpellier
    45789: 1891,   # Nacional
    47475: 39499,  # Netherlands
    47471: 1352,   # Norway
    50497: 66,     # OL
    50499: 46281,  # Paris FC
    50498: 73,     # Paris SG
    50146: 1354,   # Portugal
    50485: 46636,  # RB Leipzig
    648: 242,      # RC Deportivo
    661: 452,      # RCD Espanyol
    47079: 35549,  # Racing Club
    50794: 449,    # Real Betis
    50800: 457,    # Real Sociedad
    50466: 25,     # SC Freiburg
    50795: 467,    # SD Eibar
    286: 234,      # SL Benfica
    50468: 38,     # SV Werder Bremen
    48448: 1359,   # Scotland
    50801: 481,    # Sevilla FC
    288: 266,      # Slavia Praha
    47476: 1362,   # Spain
    50475: 18,     # Spurs
    50504: 379,    # Stade de Reims
    652: 76,       # Strasbourg
    47472: 1363,   # Sweden
    50463: 10029,  # TSG Hoffenheim
    47473: 1387,   # United States
    50803: 461,    # Valencia CF
    50462: 175,    # VfL Wolfsburg
    50478: 19,     # West Ham
}

# Reverse mapping: Primary/Men's Team ID -> Secondary/Women's Team ID
PRIMARY_TO_SECONDARY_TEAMS: Dict[int, int] = {v: k for k, v in SECONDARY_TO_PRIMARY_TEAMS.items()}

# Set of all Secondary/Women's Team IDs
SECONDARY_TEAM_IDS: Set[int] = set(SECONDARY_TO_PRIMARY_TEAMS.keys())

# Standalone women's clubs (do not have a men's duplicate in lyxL)
STANDALONE_WOMEN_TEAMS: Set[int] = {
    50464, # Turbine Potsdam
    50465, # SGS Essen
    50469, # Carl Zeiss Jena
    50476, # Manchester Utd (WSL)
    50500, # FC Fleury 91
    50503, # Dijon FCO
    50746, # Roma Femminile
    50764, # Seattle Reign
    50766, # Portland Thorns
    50767, # NC Courage
    50768, # Washington Spirit
    50769, # Chicago Stars FC
    50770, # Houston Dash
    50771, # Orlando Pride
    50772, # Rac. Louisville
    50773, # KC Current
    50774, # NJ/NY Gotham
    50775, # Angel City FC
    50776, # San Diego Wave
    50790, # Real Madrid CF (Liga F)
    50796, # UD Tenerife
    50798, # Madrid CFF
    290,   # FC Rosengård
    291,   # Glasgow City FC
    405,   # Bay FC
    406,   # Utah Royals FC
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
    if 630 <= row_index <= 638 and team_id in [47466, 47467, 47468, 47471, 47472, 47473, 47474, 47475, 47476]:
        return f"{clean_name} (Women)"

    return clean_name

