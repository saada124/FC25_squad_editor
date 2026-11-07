"""
FC 25 PlayStyles and Player Traits Engine
Reverse-engineered from EA Sports FC 25 & Live Editor v25.4.2 (playstyles_enum.lua).

PlayStyle Bitmask Architecture:
  trait1 / icontrait1: Bits 0 to 29 (Scoring, Passing, Defending, Ball Control, Physical, GK Footwork/Far Throw)
  trait2 / icontrait2: Bits 0 to 10 (GK Reactions/Reach, Low Driven Shot, Career Traits)

Tier States:
  0 = None
  1 = Regular (+)   (Silver PlayStyle - bit set in trait1/trait2, 0 in icontrait1/icontrait2)
  2 = PlayStyle+ (++) (Gold PlayStyle+ - bit set in BOTH trait1/trait2 AND icontrait1/icontrait2)
"""

from typing import Dict, List, Tuple, Any

PLAYSTYLE_CATEGORIES = {
    "Scoring": [
        ("finesse_shot", "Finesse Shot", 1, 0, "Curled precision shots with maximum curve and accuracy."),
        ("chip_shot", "Chip Shot", 1, 1, "Quick, delicate chips over rushing goalkeepers."),
        ("power_shot", "Power Shot", 1, 2, "Unleashes devastatingly powerful long-range shots."),
        ("dead_ball", "Dead Ball", 1, 3, "Exceptional free kicks and corners with trajectory line."),
        ("power_header", "Power Header", 1, 4, "High power and accuracy on attacking headers.")
    ],
    "Passing": [
        ("incisive_pass", "Incisive Pass", 1, 5, "Laser through balls that bypass defensive lines."),
        ("pinged_pass", "Pinged Pass", 1, 6, "High-speed ground passes without loss of ball control."),
        ("long_ball_pass", "Long Ball Pass", 1, 7, "Direct, lofted balls driven accurately over distance."),
        ("tiki_taka", "Tiki Taka", 1, 8, "Immediate one-touch first-time passing mastery."),
        ("whipped_pass", "Whipped Pass", 1, 9, "High-curve curling crosses and set deliveries.")
    ],
    "Defending": [
        ("jockey", "Jockey", 1, 10, "Rapid acceleration and responsiveness while jockeying."),
        ("block", "Block", 1, 11, "Greater reach and success when blocking shots/crosses."),
        ("intercept", "Intercept", 1, 12, "Superior reach and ball retention during interceptions."),
        ("anticipate", "Anticipate", 1, 13, "Supreme stand tackling without giving away fouls."),
        ("slide_tackle", "Slide Tackle", 1, 14, "Stops the ball directly at defender's feet on slide."),
        ("bruiser", "Bruiser", 1, 15, "Overpowering physical strength when dispossessing.")
    ],
    "Ball Control": [
        ("technical", "Technical", 1, 16, "Ultra-smooth controlled sprint with close touch."),
        ("rapid", "Rapid", 1, 17, "Explosive sprint speed while dribbling downfield."),
        ("flair", "Flair", 1, 18, "Fancy passes and trick skill executions."),
        ("first_touch", "First Touch", 1, 19, "Flawless cushioning and transition upon receiving."),
        ("trickster", "Trickster", 1, 20, "Unique 5-star skill moves and deceptive flick animations."),
        ("press_proven", "Press Proven", 1, 21, "Shielding and close control under heavy opponent pressure.")
    ],
    "Physical & Movement": [
        ("quick_step", "Quick Step", 1, 22, "Explosive acceleration burst when taking first step."),
        ("relentless", "Relentless", 1, 23, "Vastly reduced stamina consumption and mid-game recovery."),
        ("trivela", "Trivela", 1, 24, "Contextual outside-of-foot curlers and driven passes."),
        ("acrobatic", "Acrobatic", 1, 25, "Volleys and scissor kicks with high agility acrobatic flair."),
        ("long_throw", "Long Throw", 1, 26, "Launches throw-ins with huge distance into the box."),
        ("aerial", "Aerial", 1, 27, "Tremendous vertical jumping height and aerial duel presence.")
    ],
    "Goalkeeping": [
        ("gk_far_throw", "GK Far Throw", 1, 28, "Allows the goalkeeper to initiate attacks with massive throws."),
        ("gk_footwork", "GK Footwork", 1, 29, "More frequent and successful foot saves from close range."),
        ("gk_cross_claimer", "GK Cross Claimer", 2, 0, "Aggressively punches or intercepts aerial balls in box."),
        ("gk_rush_out", "GK Rush Out", 2, 1, "High closing speed when rushing outside the 6-yard box."),
        ("gk_far_reach", "GK Far Reach", 2, 2, "Long-distance diving reach for top-corner saves."),
        ("gk_quick_reflexes", "GK Quick Reflexes", 2, 3, "Rapid reflex saves against close-range strikes.")
    ],
    "Career & Player Traits": [
        ("low_driven_shot", "Low Driven Shot", 2, 4, "High tendency to drill low-driven ground finishes."),
        ("solid_player", "Solid Player", 2, 6, "Low injury risk; consistently resilient."),
        ("team_player", "Team Player", 2, 7, "Puts team tactical objectives before personal glory."),
        ("one_club_player", "One Club Player", 2, 8, "High loyalty; career-long devotion to their club."),
        ("injury_prone", "Injury Prone", 2, 9, "Higher likelihood of suffering muscle/ligament injuries."),
        ("leadership", "Leadership", 2, 10, "Inspirational captain influence on teammates' morale.")
    ]
}

# Lookup map: key -> (name, trait_group, bit_index, desc)
PLAYSTYLE_MAP = {}
for cat_name, p_list in PLAYSTYLE_CATEGORIES.items():
    for key, name, group, bit, desc in p_list:
        PLAYSTYLE_MAP[key] = {
            "name": name,
            "category": cat_name,
            "group": group, # 1 for trait1/icontrait1, 2 for trait2/icontrait2
            "bit": bit,
            "mask": 1 << bit,
            "desc": desc
        }

def decode_player_playstyles(trait1: int, trait2: int, icontrait1: int, icontrait2: int) -> Dict[str, int]:
    """
    Decodes player bitmasks into individual PlayStyle tier values:
      0 = None
      1 = Regular (+) (Silver)
      2 = PlayStyle+ (++) (Gold)
    """
    states: Dict[str, int] = {}
    for key, info in PLAYSTYLE_MAP.items():
        bit = info["bit"]
        if info["group"] == 1:
            has_regular = bool(trait1 & (1 << bit))
            has_icon = bool(icontrait1 & (1 << bit))
        else:
            has_regular = bool(trait2 & (1 << bit))
            has_icon = bool(icontrait2 & (1 << bit))
            
        if has_icon:
            states[key] = 2  # Gold PlayStyle+
        elif has_regular:
            states[key] = 1  # Silver PlayStyle
        else:
            states[key] = 0  # None
            
    return states

def encode_player_playstyles(states: Dict[str, int]) -> Tuple[int, int, int, int]:
    """
    Encodes PlayStyle tier states back into FC 25 bitmasks:
    Returns (trait1, trait2, icontrait1, icontrait2).
    """
    trait1 = 0
    trait2 = 0
    icontrait1 = 0
    icontrait2 = 0
    
    for key, state in states.items():
        if key not in PLAYSTYLE_MAP or state <= 0:
            continue
        info = PLAYSTYLE_MAP[key]
        bit = info["bit"]
        mask = 1 << bit
        
        if info["group"] == 1:
            trait1 |= mask
            if state == 2:
                icontrait1 |= mask
        else:
            trait2 |= mask
            if state == 2:
                icontrait2 |= mask
                
    return trait1, trait2, icontrait1, icontrait2

def get_active_playstyles_summary(states: Dict[str, int]) -> Tuple[List[str], List[str]]:
    """
    Returns two lists: (list of PlayStyle+ gold names, list of regular silver names).
    """
    plus_list = []
    reg_list = []
    for key, state in states.items():
        if key in PLAYSTYLE_MAP:
            name = PLAYSTYLE_MAP[key]["name"]
            if state == 2:
                plus_list.append(f"{name}+")
            elif state == 1:
                reg_list.append(name)
    return plus_list, reg_list
