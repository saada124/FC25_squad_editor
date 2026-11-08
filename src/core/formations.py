"""
Formations and pitch geometry presets for EA Sports FC 25 Squad Studio.
Defines authentic 11-slot formations with normalized pitch coordinates (rel_x, rel_y),
tactical line categories (GK, DEF, MID, ATT), and preferred position mappings.
"""

from typing import Dict, List, Any, Optional

# Pitch Slot Definition:
# slot_id: integer index 0-10
# name: display label e.g. 'GK', 'LB', 'CB', 'CDM', 'ST'
# category: 'GK', 'DEF', 'MID', 'ATT'
# rel_x: normalized coordinate (0.0=left touchline, 1.0=right touchline, 0.50=center)
# rel_y: normalized coordinate (0.0=opponent goal/attack, 1.0=home goal/defense)
# preferred_pos: list of integer position codes matching POSITION_NAMES

# Authentic position codes from schema.py:
# 0: GK, 1: SW, 2: RWB, 3: RB, 4: RCB, 5: CB, 6: LCB, 7: LB, 8: LWB
# 9: RDM, 10: CDM, 11: LDM, 12: RM, 13: RCM, 14: CM, 15: LCM, 16: LM
# 17: RAM, 18: CAM, 19: LAM, 20: RF, 21: CF, 22: LF, 23: RW, 24: RS, 25: ST, 26: LS, 27: LW

FORMATIONS: Dict[str, List[Dict[str, Any]]] = {
    "4-3-3": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LCM", "category": "MID", "rel_x": 0.28, "rel_y": 0.48, "preferred_pos": [15, 14, 18]},
        {"slot_id": 6, "name": "CDM", "category": "MID", "rel_x": 0.50, "rel_y": 0.60, "preferred_pos": [10, 9, 11]},
        {"slot_id": 7, "name": "RCM", "category": "MID", "rel_x": 0.72, "rel_y": 0.48, "preferred_pos": [13, 14, 18]},
        {"slot_id": 8, "name": "LW", "category": "ATT", "rel_x": 0.14, "rel_y": 0.22, "preferred_pos": [27, 22, 16]},
        {"slot_id": 9, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.14, "preferred_pos": [25, 21, 24, 26]},
        {"slot_id": 10, "name": "RW", "category": "ATT", "rel_x": 0.86, "rel_y": 0.22, "preferred_pos": [23, 20, 12]},
    ],
    "4-2-3-1": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LDM", "category": "MID", "rel_x": 0.34, "rel_y": 0.60, "preferred_pos": [11, 10, 15, 14]},
        {"slot_id": 6, "name": "RDM", "category": "MID", "rel_x": 0.66, "rel_y": 0.60, "preferred_pos": [9, 10, 13, 14]},
        {"slot_id": 7, "name": "LM", "category": "MID", "rel_x": 0.14, "rel_y": 0.36, "preferred_pos": [16, 27, 19]},
        {"slot_id": 8, "name": "CAM", "category": "MID", "rel_x": 0.50, "rel_y": 0.34, "preferred_pos": [18, 17, 19, 14]},
        {"slot_id": 9, "name": "RM", "category": "MID", "rel_x": 0.86, "rel_y": 0.36, "preferred_pos": [12, 23, 17]},
        {"slot_id": 10, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.14, "preferred_pos": [25, 21, 24, 26]},
    ],
    "4-4-2": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LM", "category": "MID", "rel_x": 0.12, "rel_y": 0.46, "preferred_pos": [16, 27]},
        {"slot_id": 6, "name": "LCM", "category": "MID", "rel_x": 0.36, "rel_y": 0.48, "preferred_pos": [15, 14, 10]},
        {"slot_id": 7, "name": "RCM", "category": "MID", "rel_x": 0.64, "rel_y": 0.48, "preferred_pos": [13, 14, 10]},
        {"slot_id": 8, "name": "RM", "category": "MID", "rel_x": 0.88, "rel_y": 0.46, "preferred_pos": [12, 23]},
        {"slot_id": 9, "name": "LS", "category": "ATT", "rel_x": 0.35, "rel_y": 0.16, "preferred_pos": [26, 25, 21]},
        {"slot_id": 10, "name": "RS", "category": "ATT", "rel_x": 0.65, "rel_y": 0.16, "preferred_pos": [24, 25, 21]},
    ],
    "5-3-2": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LWB", "category": "DEF", "rel_x": 0.10, "rel_y": 0.68, "preferred_pos": [8, 7]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.28, "rel_y": 0.78, "preferred_pos": [6, 5]},
        {"slot_id": 3, "name": "CB", "category": "DEF", "rel_x": 0.50, "rel_y": 0.80, "preferred_pos": [5, 6, 4]},
        {"slot_id": 4, "name": "RCB", "category": "DEF", "rel_x": 0.72, "rel_y": 0.78, "preferred_pos": [4, 5]},
        {"slot_id": 5, "name": "RWB", "category": "DEF", "rel_x": 0.90, "rel_y": 0.68, "preferred_pos": [2, 3]},
        {"slot_id": 6, "name": "LCM", "category": "MID", "rel_x": 0.28, "rel_y": 0.46, "preferred_pos": [15, 14, 10]},
        {"slot_id": 7, "name": "CM", "category": "MID", "rel_x": 0.50, "rel_y": 0.50, "preferred_pos": [14, 10, 18]},
        {"slot_id": 8, "name": "RCM", "category": "MID", "rel_x": 0.72, "rel_y": 0.46, "preferred_pos": [13, 14, 10]},
        {"slot_id": 9, "name": "LS", "category": "ATT", "rel_x": 0.35, "rel_y": 0.16, "preferred_pos": [26, 25, 21]},
        {"slot_id": 10, "name": "RS", "category": "ATT", "rel_x": 0.65, "rel_y": 0.16, "preferred_pos": [24, 25, 21]},
    ],
    "3-4-2-1": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LCB", "category": "DEF", "rel_x": 0.26, "rel_y": 0.78, "preferred_pos": [6, 5]},
        {"slot_id": 2, "name": "CB", "category": "DEF", "rel_x": 0.50, "rel_y": 0.80, "preferred_pos": [5, 6, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.74, "rel_y": 0.78, "preferred_pos": [4, 5]},
        {"slot_id": 4, "name": "LM", "category": "MID", "rel_x": 0.10, "rel_y": 0.48, "preferred_pos": [16, 8, 7]},
        {"slot_id": 5, "name": "LCM", "category": "MID", "rel_x": 0.36, "rel_y": 0.52, "preferred_pos": [15, 14, 10]},
        {"slot_id": 6, "name": "RCM", "category": "MID", "rel_x": 0.64, "rel_y": 0.52, "preferred_pos": [13, 14, 10]},
        {"slot_id": 7, "name": "RM", "category": "MID", "rel_x": 0.90, "rel_y": 0.48, "preferred_pos": [12, 2, 3]},
        {"slot_id": 8, "name": "LF", "category": "ATT", "rel_x": 0.32, "rel_y": 0.26, "preferred_pos": [22, 19, 18, 27]},
        {"slot_id": 9, "name": "RF", "category": "ATT", "rel_x": 0.68, "rel_y": 0.26, "preferred_pos": [20, 17, 18, 23]},
        {"slot_id": 10, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.13, "preferred_pos": [25, 21, 24, 26]},
    ],
    "4-1-4-1": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "CDM", "category": "MID", "rel_x": 0.50, "rel_y": 0.62, "preferred_pos": [10, 9, 11]},
        {"slot_id": 6, "name": "LM", "category": "MID", "rel_x": 0.12, "rel_y": 0.42, "preferred_pos": [16, 27]},
        {"slot_id": 7, "name": "LCM", "category": "MID", "rel_x": 0.35, "rel_y": 0.44, "preferred_pos": [15, 14, 18]},
        {"slot_id": 8, "name": "RCM", "category": "MID", "rel_x": 0.65, "rel_y": 0.44, "preferred_pos": [13, 14, 18]},
        {"slot_id": 9, "name": "RM", "category": "MID", "rel_x": 0.88, "rel_y": 0.42, "preferred_pos": [12, 23]},
        {"slot_id": 10, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.15, "preferred_pos": [25, 21, 24, 26]},
    ],
    "3-4-3": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LCB", "category": "DEF", "rel_x": 0.26, "rel_y": 0.78, "preferred_pos": [6, 5]},
        {"slot_id": 2, "name": "CB", "category": "DEF", "rel_x": 0.50, "rel_y": 0.80, "preferred_pos": [5, 6, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.74, "rel_y": 0.78, "preferred_pos": [4, 5]},
        {"slot_id": 4, "name": "LM", "category": "MID", "rel_x": 0.10, "rel_y": 0.48, "preferred_pos": [16, 8, 7]},
        {"slot_id": 5, "name": "LCM", "category": "MID", "rel_x": 0.36, "rel_y": 0.52, "preferred_pos": [15, 14, 10]},
        {"slot_id": 6, "name": "RCM", "category": "MID", "rel_x": 0.64, "rel_y": 0.52, "preferred_pos": [13, 14, 10]},
        {"slot_id": 7, "name": "RM", "category": "MID", "rel_x": 0.90, "rel_y": 0.48, "preferred_pos": [12, 2, 3]},
        {"slot_id": 8, "name": "LW", "category": "ATT", "rel_x": 0.16, "rel_y": 0.20, "preferred_pos": [27, 22, 16]},
        {"slot_id": 9, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.14, "preferred_pos": [25, 21, 24, 26]},
        {"slot_id": 10, "name": "RW", "category": "ATT", "rel_x": 0.84, "rel_y": 0.20, "preferred_pos": [23, 20, 12]},
    ],
    "3-5-2": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LCB", "category": "DEF", "rel_x": 0.26, "rel_y": 0.78, "preferred_pos": [6, 5]},
        {"slot_id": 2, "name": "CB", "category": "DEF", "rel_x": 0.50, "rel_y": 0.80, "preferred_pos": [5, 6, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.74, "rel_y": 0.78, "preferred_pos": [4, 5]},
        {"slot_id": 4, "name": "LDM", "category": "MID", "rel_x": 0.35, "rel_y": 0.60, "preferred_pos": [11, 10, 15, 14]},
        {"slot_id": 5, "name": "RDM", "category": "MID", "rel_x": 0.65, "rel_y": 0.60, "preferred_pos": [9, 10, 13, 14]},
        {"slot_id": 6, "name": "LM", "category": "MID", "rel_x": 0.10, "rel_y": 0.44, "preferred_pos": [16, 8, 7]},
        {"slot_id": 7, "name": "CAM", "category": "MID", "rel_x": 0.50, "rel_y": 0.38, "preferred_pos": [18, 14, 19]},
        {"slot_id": 8, "name": "RM", "category": "MID", "rel_x": 0.90, "rel_y": 0.44, "preferred_pos": [12, 2, 3]},
        {"slot_id": 9, "name": "LS", "category": "ATT", "rel_x": 0.35, "rel_y": 0.15, "preferred_pos": [26, 25, 21]},
        {"slot_id": 10, "name": "RS", "category": "ATT", "rel_x": 0.65, "rel_y": 0.15, "preferred_pos": [24, 25, 21]},
    ],
    "5-2-3": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LWB", "category": "DEF", "rel_x": 0.10, "rel_y": 0.68, "preferred_pos": [8, 7]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.28, "rel_y": 0.78, "preferred_pos": [6, 5]},
        {"slot_id": 3, "name": "CB", "category": "DEF", "rel_x": 0.50, "rel_y": 0.80, "preferred_pos": [5, 6, 4]},
        {"slot_id": 4, "name": "RCB", "category": "DEF", "rel_x": 0.72, "rel_y": 0.78, "preferred_pos": [4, 5]},
        {"slot_id": 5, "name": "RWB", "category": "DEF", "rel_x": 0.90, "rel_y": 0.68, "preferred_pos": [2, 3]},
        {"slot_id": 6, "name": "LCM", "category": "MID", "rel_x": 0.36, "rel_y": 0.48, "preferred_pos": [15, 14, 10]},
        {"slot_id": 7, "name": "RCM", "category": "MID", "rel_x": 0.64, "rel_y": 0.48, "preferred_pos": [13, 14, 10]},
        {"slot_id": 8, "name": "LW", "category": "ATT", "rel_x": 0.16, "rel_y": 0.20, "preferred_pos": [27, 22, 16]},
        {"slot_id": 9, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.14, "preferred_pos": [25, 21, 24, 26]},
        {"slot_id": 10, "name": "RW", "category": "ATT", "rel_x": 0.84, "rel_y": 0.20, "preferred_pos": [23, 20, 12]},
    ],
    "4-1-2-1-2": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "CDM", "category": "MID", "rel_x": 0.50, "rel_y": 0.62, "preferred_pos": [10, 9, 11]},
        {"slot_id": 6, "name": "LM", "category": "MID", "rel_x": 0.14, "rel_y": 0.46, "preferred_pos": [16, 27]},
        {"slot_id": 7, "name": "RM", "category": "MID", "rel_x": 0.86, "rel_y": 0.46, "preferred_pos": [12, 23]},
        {"slot_id": 8, "name": "CAM", "category": "MID", "rel_x": 0.50, "rel_y": 0.34, "preferred_pos": [18, 14, 19]},
        {"slot_id": 9, "name": "LS", "category": "ATT", "rel_x": 0.35, "rel_y": 0.16, "preferred_pos": [26, 25, 21]},
        {"slot_id": 10, "name": "RS", "category": "ATT", "rel_x": 0.65, "rel_y": 0.16, "preferred_pos": [24, 25, 21]},
    ],
    "4-3-1-2": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LCM", "category": "MID", "rel_x": 0.28, "rel_y": 0.54, "preferred_pos": [15, 14, 10]},
        {"slot_id": 6, "name": "CM", "category": "MID", "rel_x": 0.50, "rel_y": 0.56, "preferred_pos": [14, 10, 18]},
        {"slot_id": 7, "name": "RCM", "category": "MID", "rel_x": 0.72, "rel_y": 0.54, "preferred_pos": [13, 14, 10]},
        {"slot_id": 8, "name": "CAM", "category": "MID", "rel_x": 0.50, "rel_y": 0.36, "preferred_pos": [18, 14, 19]},
        {"slot_id": 9, "name": "LS", "category": "ATT", "rel_x": 0.35, "rel_y": 0.16, "preferred_pos": [26, 25, 21]},
        {"slot_id": 10, "name": "RS", "category": "ATT", "rel_x": 0.65, "rel_y": 0.16, "preferred_pos": [24, 25, 21]},
    ],
    "4-2-2-2": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LDM", "category": "MID", "rel_x": 0.34, "rel_y": 0.62, "preferred_pos": [11, 10, 15, 14]},
        {"slot_id": 6, "name": "RDM", "category": "MID", "rel_x": 0.66, "rel_y": 0.62, "preferred_pos": [9, 10, 13, 14]},
        {"slot_id": 7, "name": "LAM", "category": "MID", "rel_x": 0.24, "rel_y": 0.38, "preferred_pos": [19, 18, 16, 27]},
        {"slot_id": 8, "name": "RAM", "category": "MID", "rel_x": 0.76, "rel_y": 0.38, "preferred_pos": [17, 18, 12, 23]},
        {"slot_id": 9, "name": "LS", "category": "ATT", "rel_x": 0.35, "rel_y": 0.15, "preferred_pos": [26, 25, 21]},
        {"slot_id": 10, "name": "RS", "category": "ATT", "rel_x": 0.65, "rel_y": 0.15, "preferred_pos": [24, 25, 21]},
    ],
    "5-4-1": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LWB", "category": "DEF", "rel_x": 0.10, "rel_y": 0.68, "preferred_pos": [8, 7]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.28, "rel_y": 0.78, "preferred_pos": [6, 5]},
        {"slot_id": 3, "name": "CB", "category": "DEF", "rel_x": 0.50, "rel_y": 0.80, "preferred_pos": [5, 6, 4]},
        {"slot_id": 4, "name": "RCB", "category": "DEF", "rel_x": 0.72, "rel_y": 0.78, "preferred_pos": [4, 5]},
        {"slot_id": 5, "name": "RWB", "category": "DEF", "rel_x": 0.90, "rel_y": 0.68, "preferred_pos": [2, 3]},
        {"slot_id": 6, "name": "LM", "category": "MID", "rel_x": 0.12, "rel_y": 0.44, "preferred_pos": [16, 27]},
        {"slot_id": 7, "name": "LCM", "category": "MID", "rel_x": 0.36, "rel_y": 0.48, "preferred_pos": [15, 14, 10]},
        {"slot_id": 8, "name": "RCM", "category": "MID", "rel_x": 0.64, "rel_y": 0.48, "preferred_pos": [13, 14, 10]},
        {"slot_id": 9, "name": "RM", "category": "MID", "rel_x": 0.88, "rel_y": 0.44, "preferred_pos": [12, 23]},
        {"slot_id": 10, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.15, "preferred_pos": [25, 21, 24, 26]},
    ],
    "3-1-4-2": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LCB", "category": "DEF", "rel_x": 0.26, "rel_y": 0.78, "preferred_pos": [6, 5]},
        {"slot_id": 2, "name": "CB", "category": "DEF", "rel_x": 0.50, "rel_y": 0.80, "preferred_pos": [5, 6, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.74, "rel_y": 0.78, "preferred_pos": [4, 5]},
        {"slot_id": 4, "name": "CDM", "category": "MID", "rel_x": 0.50, "rel_y": 0.62, "preferred_pos": [10, 9, 11]},
        {"slot_id": 5, "name": "LM", "category": "MID", "rel_x": 0.10, "rel_y": 0.44, "preferred_pos": [16, 8, 7]},
        {"slot_id": 6, "name": "LCM", "category": "MID", "rel_x": 0.34, "rel_y": 0.46, "preferred_pos": [15, 14, 18]},
        {"slot_id": 7, "name": "RCM", "category": "MID", "rel_x": 0.66, "rel_y": 0.46, "preferred_pos": [13, 14, 18]},
        {"slot_id": 8, "name": "RM", "category": "MID", "rel_x": 0.90, "rel_y": 0.44, "preferred_pos": [12, 2, 3]},
        {"slot_id": 9, "name": "LS", "category": "ATT", "rel_x": 0.35, "rel_y": 0.15, "preferred_pos": [26, 25, 21]},
        {"slot_id": 10, "name": "RS", "category": "ATT", "rel_x": 0.65, "rel_y": 0.15, "preferred_pos": [24, 25, 21]},
    ],
    "4-4-1-1": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LM", "category": "MID", "rel_x": 0.12, "rel_y": 0.46, "preferred_pos": [16, 27]},
        {"slot_id": 6, "name": "LCM", "category": "MID", "rel_x": 0.36, "rel_y": 0.50, "preferred_pos": [15, 14, 10]},
        {"slot_id": 7, "name": "RCM", "category": "MID", "rel_x": 0.64, "rel_y": 0.50, "preferred_pos": [13, 14, 10]},
        {"slot_id": 8, "name": "RM", "category": "MID", "rel_x": 0.88, "rel_y": 0.46, "preferred_pos": [12, 23]},
        {"slot_id": 9, "name": "CF", "category": "ATT", "rel_x": 0.50, "rel_y": 0.28, "preferred_pos": [21, 18, 25]},
        {"slot_id": 10, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.14, "preferred_pos": [25, 24, 26]},
    ],
    "4-5-1": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LM", "category": "MID", "rel_x": 0.12, "rel_y": 0.42, "preferred_pos": [16, 27]},
        {"slot_id": 6, "name": "CM", "category": "MID", "rel_x": 0.50, "rel_y": 0.54, "preferred_pos": [14, 10, 15, 13]},
        {"slot_id": 7, "name": "LCAM", "category": "MID", "rel_x": 0.34, "rel_y": 0.36, "preferred_pos": [18, 19, 14]},
        {"slot_id": 8, "name": "RCAM", "category": "MID", "rel_x": 0.66, "rel_y": 0.36, "preferred_pos": [18, 17, 14]},
        {"slot_id": 9, "name": "RM", "category": "MID", "rel_x": 0.88, "rel_y": 0.42, "preferred_pos": [12, 23]},
        {"slot_id": 10, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.14, "preferred_pos": [25, 21, 24, 26]},
    ],
    "4-2-4": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LCM", "category": "MID", "rel_x": 0.36, "rel_y": 0.50, "preferred_pos": [15, 14, 10]},
        {"slot_id": 6, "name": "RCM", "category": "MID", "rel_x": 0.64, "rel_y": 0.50, "preferred_pos": [13, 14, 10]},
        {"slot_id": 7, "name": "LW", "category": "ATT", "rel_x": 0.14, "rel_y": 0.20, "preferred_pos": [27, 22, 16]},
        {"slot_id": 8, "name": "LS", "category": "ATT", "rel_x": 0.38, "rel_y": 0.15, "preferred_pos": [26, 25, 21]},
        {"slot_id": 9, "name": "RS", "category": "ATT", "rel_x": 0.62, "rel_y": 0.15, "preferred_pos": [24, 25, 21]},
        {"slot_id": 10, "name": "RW", "category": "ATT", "rel_x": 0.86, "rel_y": 0.20, "preferred_pos": [23, 20, 12]},
    ],
    "4-3-2-1": [
        {"slot_id": 0, "name": "GK", "category": "GK", "rel_x": 0.50, "rel_y": 0.90, "preferred_pos": [0]},
        {"slot_id": 1, "name": "LB", "category": "DEF", "rel_x": 0.12, "rel_y": 0.74, "preferred_pos": [7, 8]},
        {"slot_id": 2, "name": "LCB", "category": "DEF", "rel_x": 0.36, "rel_y": 0.78, "preferred_pos": [6, 5, 4]},
        {"slot_id": 3, "name": "RCB", "category": "DEF", "rel_x": 0.64, "rel_y": 0.78, "preferred_pos": [4, 5, 6]},
        {"slot_id": 4, "name": "RB", "category": "DEF", "rel_x": 0.88, "rel_y": 0.74, "preferred_pos": [3, 2]},
        {"slot_id": 5, "name": "LCM", "category": "MID", "rel_x": 0.26, "rel_y": 0.52, "preferred_pos": [15, 14, 10]},
        {"slot_id": 6, "name": "CM", "category": "MID", "rel_x": 0.50, "rel_y": 0.54, "preferred_pos": [14, 10, 18]},
        {"slot_id": 7, "name": "RCM", "category": "MID", "rel_x": 0.74, "rel_y": 0.52, "preferred_pos": [13, 14, 10]},
        {"slot_id": 8, "name": "LF", "category": "ATT", "rel_x": 0.32, "rel_y": 0.28, "preferred_pos": [22, 19, 27, 25]},
        {"slot_id": 9, "name": "RF", "category": "ATT", "rel_x": 0.68, "rel_y": 0.28, "preferred_pos": [20, 17, 23, 25]},
        {"slot_id": 10, "name": "ST", "category": "ATT", "rel_x": 0.50, "rel_y": 0.14, "preferred_pos": [25, 21, 24, 26]},
    ],
}

# Ordered list of all supported formations for UI dropdown
FORMATION_NAMES: List[str] = list(FORMATIONS.keys())

DEFAULT_FORMATION = "4-3-3"

def get_formation_slots(formation_name: str) -> List[Dict[str, Any]]:
    """Returns the 11 slot definitions for the specified formation name, defaulting to 4-3-3."""
    clean_name = (formation_name or "").strip()
    if clean_name in FORMATIONS:
        return FORMATIONS[clean_name]
    # Check partial match
    for k in FORMATIONS:
        if k in clean_name or clean_name in k:
            return FORMATIONS[k]
    return FORMATIONS[DEFAULT_FORMATION]

def get_slot_category_color(category: str) -> tuple:
    """Returns RGBA color tuple for position category badge."""
    c = (category or "").upper()
    if c == "GK":
        return (245, 158, 11, 255) # Vivid Amber
    elif c == "DEF":
        return (37, 99, 235, 255) # Royal Blue
    elif c == "MID":
        return (16, 185, 129, 255) # Emerald Green
    elif c == "ATT":
        return (239, 68, 68, 255) # Crimson Red
    return (150, 150, 150, 255) # Grey default

def get_ovr_tier_color(ovr: int) -> tuple:
    """Returns RGBA color tuple for player rating tier."""
    if ovr >= 90:
        return (255, 215, 0, 255) # Electric Gold
    elif ovr >= 85:
        return (251, 191, 36, 255) # Warm Gold
    elif ovr >= 80:
        return (52, 211, 153, 255) # Mint Green
    elif ovr >= 75:
        return (203, 213, 225, 255) # Silver
    return (249, 115, 22, 255) # Bronze
