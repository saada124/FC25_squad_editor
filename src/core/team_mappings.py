"""
Team mappings and relationships for EA Sports FC 25.
Maps secondary/women's teams (which share identical string names in table lyxL)
to their primary/parent clubs for asset inheritance, search differentiation,
and roster assignments.
"""

from typing import Dict, Set, Optional

# Mapping of Secondary/Women's Team ID -> Primary/Men's Team ID
# Contains authentic 4-byte Frostbite IDs (from FIFA DB v8 kISL.DmlS + 1) and legacy 2-byte IDs.
SECONDARY_TO_PRIMARY_TEAMS: Dict[int, int] = {
    # Authentic Frostbite IDs from FIFA DB v8 kISL.DmlS + 1
    116003: 1,      # Arsenal (Women) -> Arsenal
    116004: 5,      # Chelsea (Women) -> Chelsea
    116005: 18,     # Spurs (Women) -> Spurs
    116009: 11,     # Manchester Utd (Women) -> Man Utd
    116010: 1808,   # Brighton (Women) -> Brighton
    116011: 19,     # West Ham (Women) -> West Ham
    116012: 2,      # Aston Villa (Women) -> Aston Villa
    116013: 7,      # Everton (Women) -> Everton
    116014: 10,     # Manchester City (Women) -> Manchester City
    116015: 95,     # Leicester City (Women) -> Leicester City
    116016: 112172, # RB Leipzig (Women) -> RB Leipzig
    116017: 66,     # OL (Women) -> OL
    116020: 73,     # Paris SG (Women) -> Paris SG
    116021: 111817, # Paris FC (Women) -> Paris FC
    116034: 70,     # Montpellier (Women) -> Montpellier
    116036: 379,    # Stade de Reims (Women) -> Stade de Reims
    116037: 62,     # En Avant Guingamp (Women) -> En Avant Guingamp
    116039: 1819,   # AS Saint Étienne (Women) -> Saint-Étienne
    116040: 45,     # Juventus (Women) -> Juventus
    116310: 241,    # FC Barcelona (Women) -> FC Barcelona
    116311: 243,    # Real Madrid CF (Women) -> Real Madrid
    116312: 240,    # Atlético de Madrid (Women) -> Atlético de Madrid
    116325: 448,    # Athletic Club (Women) -> Athletic Club
    116326: 449,    # Real Betis (Women) -> Real Betis
    116327: 467,    # SD Eibar (Women) -> SD Eibar
    116330: 1853,   # Levante UD (Women) -> Levante UD
    116332: 457,    # Real Sociedad (Women) -> Real Sociedad
    116333: 481,    # Sevilla FC (Women) -> Sevilla FC
    116334: 461,    # Valencia CF (Women) -> Valencia CF
    116336: 9,      # Liverpool (Women) -> Liverpool
    115841: 21,     # FC Bayern München (Women) -> FC Bayern München
    115845: 32,     # Leverkusen (Women) -> Leverkusen
    115891: 1824,   # Frankfurt (Women) -> Frankfurt
    115995: 175,    # VfL Wolfsburg (Women) -> VfL Wolfsburg
    115996: 10029,  # TSG Hoffenheim (Women) -> TSG Hoffenheim
    115999: 25,     # SC Freiburg (Women) -> SC Freiburg
    116000: 31,     # 1. FC Köln (Women) -> 1. FC Köln
    116001: 38,     # SV Werder Bremen (Women) -> SV Werder Bremen
    111325: 1891,   # Nacional (Women) -> Nacional
    112615: 101085, # Racing Club (Women) -> Racing Club
    113002: 1318,   # England (Women) -> England
    113003: 1335,   # France (Women) -> France
    113004: 1337,   # Germany (Women) -> Germany
    113007: 1352,   # Norway (Women) -> Norway
    113008: 1363,   # Sweden (Women) -> Sweden
    113009: 1387,   # United States (Women) -> United States
    113010: 1386,   # Mexico (Women) -> Mexico
    113011: 105035, # Netherlands (Women) -> Netherlands
    113012: 1362,   # Spain (Women) -> Spain
    113973: 1359,   # Scotland (Women) -> Scotland
    113974: 1369,   # Argentina (Women) -> Argentina
    115486: 1354,   # Portugal (Women) -> Portugal
    116343: 1738,   # Havre AC (Women) -> Havre AC
    116360: 71,     # FC Nantes (Women) -> FC Nantes
    116361: 1341,   # Iceland (Women) -> Iceland
    116417: 1334,   # Finland (Women) -> Finland
    131125: 234,    # SL Benfica (Women) -> SL Benfica
    131159: 245,    # Ajax (Women) -> Ajax
    131173: 266,    # Slavia Praha (Women) -> Slavia Praha
    131174: 894,    # FC Zürich (Women) -> FC Zürich
    131359: 111592, # Free Agents (Women) -> Free Agents
    131361: 110832, # Granada CF (Women) -> Granada CF
    131524: 242,    # RC Deportivo (Women) -> RC Deportivo
    131527: 76,     # Strasbourg (Women) -> Strasbourg
    131680: 1799,   # Crystal Palace (Women) -> Crystal Palace
    131681: 452,    # RCD Espanyol (Women) -> RCD Espanyol

    # Legacy 2-byte truncated IDs for backwards compatibility with older tools
    50473: 1,       # Arsenal (Legacy)
    50474: 5,       # Chelsea (Legacy)
    50475: 18,      # Spurs (Legacy)
    50476: 11,      # Man Utd (Legacy)
    50477: 1808,    # Brighton (Legacy)
    50478: 19,      # West Ham (Legacy)
    50479: 2,       # Aston Villa (Legacy)
    50480: 7,       # Everton (Legacy)
    50481: 10,      # Manchester City (Legacy)
    50484: 95,      # Leicester City (Legacy)
    50485: 46636,   # RB Leipzig (Legacy)
    50497: 66,      # OL (Legacy)
    50498: 73,      # Paris SG (Legacy)
    50499: 46281,   # Paris FC (Legacy)
    50501: 70,      # Montpellier (Legacy)
    50503: 1819,    # Saint Étienne (Legacy)
    50504: 379,     # Stade de Reims (Legacy)
    50506: 62,      # En Avant Guingamp (Legacy)
    50744: 45,      # Juventus (Legacy)
    50789: 241,     # FC Barcelona (Legacy)
    50790: 243,     # Real Madrid CF (Legacy)
    50791: 240,     # Atlético de Madrid (Legacy)
    50792: 448,     # Athletic Club (Legacy)
    50794: 449,     # Real Betis (Legacy)
    50795: 467,     # SD Eibar (Legacy)
    50797: 1853,    # Levante UD (Legacy)
    50800: 457,     # Real Sociedad (Legacy)
    50801: 481,     # Sevilla FC (Legacy)
    50803: 461,     # Valencia CF (Legacy)
    50807: 9,       # Liverpool (Legacy)
    50880: 1738,    # Havre AC (Legacy)
    50881: 71,      # FC Nantes (Legacy)
    50892: 1341,    # Iceland (Legacy)
    52: 1334,       # Finland (Legacy)
    286: 234,       # SL Benfica (Legacy)
    287: 245,       # Ajax (Legacy)
    288: 266,       # Slavia Praha (Legacy)
    289: 894,       # FC Zürich (Legacy)
    296: 46056,     # Free Agents (Legacy)
    319: 45296,     # Granada CF (Legacy)
    648: 242,       # RC Deportivo (Legacy)
    652: 76,        # Strasbourg (Legacy)
    653: 1799,      # Crystal Palace (Legacy)
    661: 452,       # RCD Espanyol (Legacy)
    45789: 1891,    # Nacional (Legacy)
    47079: 35549,   # Racing Club (Legacy)
    47466: 1318,    # England (Legacy)
    47467: 1335,    # France (Legacy)
    47468: 1337,    # Germany (Legacy)
    47471: 1352,    # Norway (Legacy)
    47472: 1363,    # Sweden (Legacy)
    47473: 1387,    # United States (Legacy)
    47474: 1386,    # Mexico (Legacy)
    47475: 39499,   # Netherlands (Legacy)
    47476: 1362,    # Spain (Legacy)
    48448: 1359,    # Scotland (Legacy)
    48460: 1369,    # Argentina (Legacy)
    50146: 1354,    # Portugal (Legacy)
    50459: 21,      # FC Bayern München (Legacy)
    50460: 32,      # Leverkusen (Legacy)
    50461: 1824,    # Frankfurt (Legacy)
    50462: 175,     # VfL Wolfsburg (Legacy)
    50463: 10029,   # TSG Hoffenheim (Legacy)
    50466: 25,      # SC Freiburg (Legacy)
    50467: 31,      # 1. FC Köln (Legacy)
    50468: 38,      # SV Werder Bremen (Legacy)
}

# Reverse mapping: Primary/Men's Team ID -> Secondary/Women's Team ID
PRIMARY_TO_SECONDARY_TEAMS: Dict[int, int] = {v: k for k, v in SECONDARY_TO_PRIMARY_TEAMS.items()}

# Set of all Secondary/Women's Team IDs that have a parent club
SECONDARY_TEAM_IDS: Set[int] = set(SECONDARY_TO_PRIMARY_TEAMS.keys())

# Standalone women's clubs (do not have a men's duplicate in lyxL)
STANDALONE_WOMEN_TEAMS: Set[int] = {
    52,      # AS Roma (Women)
    115997,  # Turbine Potsdam
    115998,  # SGS Essen
    116002,  # Carl Zeiss Jena
    116033,  # FC Fleury 91
    116035,  # Dijon FCO
    116042,  # Roma (Women)
    116044,  # Seattle Reign
    116280,  # Portland Thorns
    116282,  # NC Courage
    116300,  # Washington Spirit
    116302,  # Chicago Stars FC
    116303,  # Houston Dash
    116304,  # Orlando Pride
    116305,  # Rac. Louisville
    116306,  # KC Current
    116307,  # NJ/NY Gotham
    116308,  # Angel City FC
    116309,  # San Diego Wave
    116328,  # UD Tenerife
    116331,  # Madrid CFF
    116428,  # Levante Badalona
    131358,  # Glasgow City FC
    131362,  # FC Rosengård
    131477,  # Bay FC
    131478,  # Utah Royals FC
    # Legacy IDs
    290,     # FC Rosengård (Legacy)
    291,     # Glasgow City FC (Legacy)
    405,     # Bay FC (Legacy)
    406,     # Utah Royals FC (Legacy)
    50464,   # Turbine Potsdam (Legacy)
    50465,   # SGS Essen (Legacy)
    50469,   # Carl Zeiss Jena (Legacy)
    50500,   # FC Fleury 91 (Legacy)
    50746,   # Roma (Legacy)
    50764,   # Seattle Reign (Legacy)
    50766,   # Portland Thorns (Legacy)
    50767,   # NC Courage (Legacy)
    50768,   # Washington Spirit (Legacy)
    50769,   # Chicago Stars FC (Legacy)
    50770,   # Houston Dash (Legacy)
    50771,   # Orlando Pride (Legacy)
    50772,   # Rac. Louisville (Legacy)
    50773,   # KC Current (Legacy)
    50774,   # NJ/NY Gotham (Legacy)
    50775,   # Angel City FC (Legacy)
    50776,   # San Diego Wave (Legacy)
    50796,   # UD Tenerife (Legacy)
    50798,   # Madrid CFF (Legacy)
}

ALL_WOMEN_TEAM_IDS: Set[int] = SECONDARY_TEAM_IDS | STANDALONE_WOMEN_TEAMS


def get_parent_club_id(team_id: int) -> int:
    """Returns the parent Men's club ID for crest/asset inheritance, or team_id itself."""
    return SECONDARY_TO_PRIMARY_TEAMS.get(team_id, team_id)


def is_women_team(team_id: int, row_index: int = -1) -> bool:
    """Returns True if the team is an authentic women's team."""
    return team_id in ALL_WOMEN_TEAM_IDS


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

    if is_women_team(team_id, row_index):
        return f"{clean_name} (Women)"

    return clean_name
