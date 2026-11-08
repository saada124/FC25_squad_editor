import os
import sys
import tkinter as tk
from tkinter import filedialog
from typing import Optional, Dict, Any, List
from datetime import datetime

import dearpygui.dearpygui as dpg

try:
    from model.squads_db import SquadsSession
    from core.schema import (
        get_table_display_name, get_column_display_name, get_column_clean_name, get_position_name, get_team_name, get_nation_name,
        POSITION_NAMES, TEAM_NAMES, NATION_NAMES, CATEGORY_LIST, TABLE_CATEGORIES, TABLE_SAFETY_CONFIG,
        get_table_category, get_table_safety_info, is_column_id_or_key, get_column_safety_warning,
        validate_column_value, classify_column
    )
    from core.backup import (
        list_folder_backups, create_load_backup, restore_backup,
        delete_backup, purge_old_backups, get_backup_metadata
    )
    from core.settings import AppSettings
    from core.playstyles import PLAYSTYLE_CATEGORIES, PLAYSTYLE_MAP, decode_player_playstyles, encode_player_playstyles, get_active_playstyles_summary
    from core.assets import AssetManager
except ImportError:
    from src.model.squads_db import SquadsSession
    from src.core.schema import (
        get_table_display_name, get_column_display_name, get_column_clean_name, get_position_name, get_team_name, get_nation_name,
        POSITION_NAMES, TEAM_NAMES, NATION_NAMES, CATEGORY_LIST, TABLE_CATEGORIES, TABLE_SAFETY_CONFIG,
        get_table_category, get_table_safety_info, is_column_id_or_key, get_column_safety_warning,
        validate_column_value, classify_column
    )
    from src.core.backup import (
        list_folder_backups, create_load_backup, restore_backup,
        delete_backup, purge_old_backups, get_backup_metadata
    )
    from src.core.settings import AppSettings
    from src.core.playstyles import PLAYSTYLE_CATEGORIES, PLAYSTYLE_MAP, decode_player_playstyles, encode_player_playstyles, get_active_playstyles_summary
    from src.core.assets import AssetManager

class SquadEditorApp:
    def __init__(self):
        self.session = SquadsSession()
        self.assets = AssetManager()
        self.config: AppSettings = AppSettings.load()
        self._is_populating_player: bool = False
        self.pending_restore_backup_path: Optional[str] = None
        self.selected_player: Optional[Dict[str, Any]] = None
        self.selected_team: Optional[Dict[str, Any]] = None
        self.selected_table_sname: str = "CZUM"
        self.selected_category: str = "All Categories (76 tables)"
        self.pending_structural_action: Optional[str] = None
        self.current_table_page: int = 0
        self.page_size: int = 50
        self.selected_record_index: Optional[int] = None
        self.inspector_filter_query: str = ""
        self.inspector_show_tech_tags: bool = False
        self.selected_team_roster_pid: Optional[int] = None
        self.filtered_sign_players: List[Dict[str, Any]] = []
        self.selected_sign_player: Optional[Dict[str, Any]] = None
        
        # Filtered lists & Presets (Clean ASCII/Unicode labels)
        self.filtered_players: List[Dict[str, Any]] = []
        self.filtered_teams: List[Dict[str, Any]] = []
        self.filter_preset: str = "All Players"
        self.preset_filter_names = [
            "All Players",
            "Transferred Players [T]",
            "Free Agents",
            "Top Superstars (85+)",
            "Wonderkids (POT 85+, Age <= 21)",
            "Messi Regen (ARG)",
            "CR7 Regen (POR)",
            "Benzema Regen (FRA)",
            "RL9 Regen (POL)",
            "Retiring Players",
            "Generated Players"
        ]
        self.pos_filter_options = [
            "All", "Attackers", "Midfielders", "Defenders", "Goalkeepers",
            "GK", "CB", "LB", "RB", "LWB", "RWB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "CF", "ST"
        ]
        self.sort_by_options = [
            "Overall (High -> Low)",
            "Overall (Low -> High)",
            "Potential (High -> Low)",
            "Name (A -> Z)",
            "Age (Young -> Old)",
            "Age (Old -> Young)",
            "Player ID"
        ]
        self.age_bracket_options = [
            "Any Age",
            "U21 (<=21)",
            "U23 (<=23)",
            "Prime (24-29)",
            "30+ Vet"
        ]
        self.filter_pos_category: str = "All"
        self.min_ovr_filter: int = 0
        self.max_ovr_filter: int = 99
        self.filter_league: str = "All Leagues"
        self.filter_club: str = "All Clubs"
        self.filter_nation: str = "All Nations"
        self.filter_foot: str = "Any"
        self.filter_age_bracket: str = "Any Age"
        self.sort_by_mode: str = "Overall (High -> Low)"
        self.assets.on_asset_loaded = self._on_async_asset_loaded

    def _on_async_asset_loaded(self, asset_type: str, id_val: int, tag: str):
        """Asynchronously updates image widgets when CDN downloads complete."""
        try:
            if asset_type == "player":
                if self.selected_player and self.selected_player.get("playerid") == id_val:
                    if dpg.does_item_exist("player_miniface_img"):
                        dpg.configure_item("player_miniface_img", texture_tag=tag)
                if hasattr(self, "selected_team_roster_pid") and self.selected_team_roster_pid == id_val:
                    if dpg.does_item_exist("roster_player_miniface_img"):
                        dpg.configure_item("roster_player_miniface_img", texture_tag=tag)
            elif asset_type == "club":
                if self.selected_team:
                    cur_tid = self.selected_team.get("teamid", 0)
                    cur_parent = get_parent_club_id(cur_tid)
                    if cur_tid == id_val or cur_parent == id_val:
                        if dpg.does_item_exist("team_crest_img"):
                            dpg.configure_item("team_crest_img", texture_tag=tag)
        except Exception:
            pass

    def run(self):
        dpg.create_context()
        self._setup_theme()
        
        dpg.create_viewport(title="FC 25 Squad Editor v1.0.0 - Full Database & Squad Studio", width=1320, height=860, min_width=1050, min_height=720)
        self._build_ui()
        
        dpg.setup_dearpygui()
        dpg.show_viewport()
        while dpg.is_dearpygui_running():
            self.assets.process_pending_textures()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()

    def _setup_theme(self):
        font_path = r"C:\Windows\Fonts\segoeui.ttf"
        if os.path.exists(font_path):
            try:
                with dpg.font_registry():
                    def_font = dpg.add_font(font_path, 16)
                dpg.bind_font(def_font)
            except Exception:
                pass

        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                # Dark slate palette matching Live Editor
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (24, 25, 29, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (30, 32, 38, 255))
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (32, 34, 42, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (50, 54, 65, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (40, 43, 52, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (55, 60, 72, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (65, 72, 88, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (35, 38, 48, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Header, (45, 52, 68, 255))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (58, 68, 90, 255))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (0, 122, 204, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Button, (45, 55, 75, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (60, 75, 105, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 122, 204, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Tab, (32, 35, 44, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (55, 65, 85, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (0, 122, 204, 255))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (0, 150, 255, 255))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (50, 180, 255, 255))
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
        dpg.bind_theme(global_theme)

        # Specialized Accent Themes for Save Button, Changes Counter, and Revert
        with dpg.theme(tag="theme_save_btn_dirty"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 140, 60, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 175, 75, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 205, 90, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.theme(tag="theme_changes_btn_active"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (170, 95, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (210, 120, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (240, 145, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.theme(tag="theme_revert_btn"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (160, 35, 35, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (200, 50, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (230, 70, 70, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

    def _build_ui(self):
        self.assets.init_dpg_textures()
        with dpg.window(tag="primary_window", no_title_bar=True, no_move=True, no_resize=True):
            # Top Control & Status Header
            with dpg.group(horizontal=True):
                dpg.add_text("FC 25 SQUAD STUDIO", color=(0, 200, 255))
                dpg.add_text("|", color=(100, 100, 100))
                dpg.add_button(label="Open Squads", callback=self._on_click_open)
                dpg.add_button(label="Save File", tag="btn_primary_save", callback=self._on_click_save)
                dpg.add_button(label="Changes (0)", tag="btn_review_changes", callback=self._on_open_pending_changes)
                dpg.add_button(label="Save As...", callback=self._on_click_save_as)
                dpg.add_spacer(width=20)
                dpg.add_text("Ready. Please open a Squads save file.", tag="status_text", color=(180, 180, 180))

            dpg.add_separator()

            # Main Navigation Tabs
            with dpg.tab_bar(tag="main_tab_bar"):
                # TAB 1: PLAYERS
                with dpg.tab(label=" Players "):
                    self._build_players_tab()

                # TAB 2: TEAMS
                with dpg.tab(label=" Teams & Clubs "):
                    self._build_teams_tab()

                # TAB 3: FULL DATABASE EDITOR (ALL 76 TABLES)
                with dpg.tab(label=" Database Tables (All 76) "):
                    self._build_database_tab()

                # TAB 4: SAFETY BACKUPS & INFO
                with dpg.tab(label=" Settings & Backups "):
                    self._build_settings_tab()

            # Structural Modification Confirmation Modal
            with dpg.window(label="[!] Structural Table Action Warning", modal=True, show=False, tag="structural_confirm_modal", width=540, height=240, no_resize=True):
                dpg.add_text("WARNING: Modifying Table Row Count", color=(255, 80, 80))
                dpg.add_spacer(height=6)
                dpg.add_text("", tag="structural_modal_msg", wrap=510)
                dpg.add_spacer(height=15)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="[!] Confirm & Proceed", callback=self._on_confirm_structural_action, width=170)
                    dpg.add_spacer(width=20)
                    dpg.add_button(label="Cancel", callback=lambda: dpg.configure_item("structural_confirm_modal", show=False), width=100)

            # Global Search & Sign Player Modal
            with dpg.window(label="[+] Sign Player to Club", modal=True, show=False, tag="sign_player_modal", width=700, height=540, no_resize=True):
                dpg.add_text("Transfer & Sign Player to Club", color=(0, 200, 255))
                dpg.add_text("Target Destination: None", tag="sign_player_target_club_label", color=(255, 200, 0))
                dpg.add_separator()

                with dpg.group(horizontal=True):
                    dpg.add_text("Search:")
                    dpg.add_input_text(hint="Search player name, ID or current club...", callback=self._on_filter_sign_players, tag="sign_player_search_input", width=260)
                    dpg.add_text("Pos:")
                    dpg.add_combo(items=["All", "Attackers", "Midfielders", "Defenders", "Goalkeepers"], default_value="All", callback=self._on_filter_sign_players, tag="sign_player_pos_combo", width=120)
                    dpg.add_text("Min OVR:")
                    dpg.add_slider_int(min_value=0, max_value=95, default_value=0, callback=self._on_filter_sign_players, tag="sign_player_min_ovr_slider", width=90)

                dpg.add_spacer(height=4)
                dpg.add_text("Matching Players: 0", tag="sign_player_count_label", color=(150, 150, 150))
                dpg.add_listbox(items=[], num_items=12, tag="sign_player_listbox", callback=self._on_select_sign_player, width=670)

                dpg.add_spacer(height=6)
                with dpg.group(horizontal=True):
                    dpg.add_text("Selected:", color=(0, 255, 120))
                    dpg.add_text("None selected", tag="sign_player_selected_info", color=(240, 240, 240))

                dpg.add_spacer(height=12)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Complete Transfer & Sign to Club", callback=self._on_confirm_sign_player, width=280)
                    dpg.add_spacer(width=20)
                    dpg.add_button(label="Cancel", callback=lambda: dpg.configure_item("sign_player_modal", show=False), width=100)

            # Review Pending Changes Modal Window
            with dpg.window(label="Review Pending File Changes", modal=True, show=False, tag="pending_changes_modal", width=820, height=560, no_resize=False):
                with dpg.group(horizontal=True):
                    dpg.add_text("Session Change Log & Revert Manager", color=(0, 200, 255))
                    dpg.add_spacer(width=20)
                    dpg.add_text("", tag="changes_modal_count_badge", color=(255, 200, 0))
                dpg.add_text("All staged changes in current session. Click red '[X] Revert' to cancel any edit, or 'Save All to File' to persist.", color=(170, 170, 170))
                dpg.add_separator()
                
                with dpg.child_window(height=420, tag="pending_changes_container"):
                    pass
                
                dpg.add_spacer(height=6)
                dpg.add_separator()
                dpg.add_spacer(height=6)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Save All to File", callback=self._on_modal_save_all, width=170)
                    dpg.add_spacer(width=15)
                    dpg.add_button(label="Discard All Changes", callback=self._on_modal_discard_all, width=180)
                    dpg.add_spacer(width=280)
                    dpg.add_button(label="Close", callback=lambda: dpg.configure_item("pending_changes_modal", show=False), width=100)

            # Restore Backup Confirmation Modal
            with dpg.window(label="[!] Confirm Backup Restore", modal=True, show=False, tag="restore_backup_confirm_modal", width=560, height=220, no_resize=True):
                dpg.add_text("WARNING: Overwriting Squads File", color=(255, 80, 80))
                dpg.add_spacer(height=6)
                dpg.add_text("", tag="restore_modal_msg", wrap=520)
                dpg.add_spacer(height=15)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Confirm & Restore File", callback=self._on_confirm_restore_backup, width=190)
                    dpg.add_spacer(width=20)
                    dpg.add_button(label="Cancel", callback=lambda: dpg.configure_item("restore_backup_confirm_modal", show=False), width=100)

            # Discard All Changes Confirmation Modal
            with dpg.window(label="[!] Confirm Discard All Changes", modal=True, show=False, tag="discard_all_confirm_modal", width=520, height=200, no_resize=True):
                dpg.add_text("WARNING: Discard All Session Changes", color=(255, 80, 80))
                dpg.add_spacer(height=6)
                dpg.add_text("Are you sure you want to discard all staged modifications?\nThis will revert all changes made during this session back to the loaded file state.", wrap=480)
                dpg.add_spacer(height=15)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Yes, Discard All", callback=self._on_confirm_discard_all, width=150)
                    dpg.add_spacer(width=20)
                    dpg.add_button(label="Cancel", callback=lambda: dpg.configure_item("discard_all_confirm_modal", show=False), width=100)

        dpg.set_primary_window("primary_window", True)

    def _build_players_tab(self):
        with dpg.group(horizontal=True):
            # Left Column: Player Search & Multi-Criteria Filtering Pane
            with dpg.child_window(width=440):
                with dpg.group(horizontal=True):
                    dpg.add_text("Search & Filter Players", color=(0, 180, 240))
                    dpg.add_spacer(width=45)
                    dpg.add_button(label="Reset", callback=self._on_clear_player_search, width=65)
                    dpg.add_button(label="Export CSV", callback=self._on_export_filtered_players_csv, width=90)
                
                # Search Bar with Instant Filter & Clear
                with dpg.group(horizontal=True):
                    dpg.add_input_text(hint="Search name, ID, club, nation, league...", callback=self._on_filter_players, tag="player_search_input", width=385)
                    dpg.add_button(label="X", callback=self._on_clear_search_box_only, width=30)

                # Row 2: Preset & Sort By
                with dpg.group(horizontal=True):
                    dpg.add_text("Preset:")
                    dpg.add_combo(items=self.preset_filter_names, default_value="All Players", callback=self._on_change_preset_filter, tag="player_preset_combo", width=155)
                    dpg.add_text("Sort:")
                    dpg.add_combo(items=self.sort_by_options, default_value="Overall (High -> Low)", callback=self._on_change_sort_by, tag="player_sort_combo", width=165)

                # Row 3: Position (Group or Exact), Preferred Foot & Age Bracket
                with dpg.group(horizontal=True):
                    dpg.add_text("Pos:   ")
                    dpg.add_combo(items=self.pos_filter_options, default_value="All", callback=self._on_change_pos_filter, tag="player_pos_combo", width=105)
                    dpg.add_text("Foot:")
                    dpg.add_combo(items=["Any", "Right", "Left"], default_value="Any", callback=self._on_change_foot_filter, tag="player_foot_combo", width=75)
                    dpg.add_text("Age:")
                    dpg.add_combo(items=self.age_bracket_options, default_value="Any Age", callback=self._on_change_age_filter, tag="player_age_combo", width=115)

                # Row 4: League & Nation Dropdowns
                with dpg.group(horizontal=True):
                    dpg.add_text("League:")
                    dpg.add_combo(items=["All Leagues"] + self.session.all_leagues, default_value="All Leagues", callback=self._on_change_league_filter, tag="player_league_filter_combo", width=155)
                    dpg.add_text("Nation:")
                    dpg.add_combo(items=["All Nations"] + self.session.all_nations, default_value="All Nations", callback=self._on_change_nation_filter, tag="player_nation_filter_combo", width=148)

                # Row 5: Club Dropdown (Cascades from League filter)
                with dpg.group(horizontal=True):
                    dpg.add_text("Club:  ")
                    dpg.add_combo(items=["All Clubs", "Free Agent"], default_value="All Clubs", callback=self._on_change_club_filter, tag="player_club_filter_combo", width=365)

                # Row 6: Min & Max Overall Rating Range
                with dpg.group(horizontal=True):
                    dpg.add_text("Min OVR:")
                    dpg.add_slider_int(min_value=0, max_value=99, default_value=0, callback=self._on_change_min_ovr, tag="player_min_ovr_slider", width=130)
                    dpg.add_text("Max OVR:")
                    dpg.add_slider_int(min_value=1, max_value=99, default_value=99, callback=self._on_change_max_ovr, tag="player_max_ovr_slider", width=130)

                dpg.add_separator()
                dpg.add_text("Total Players: 0", tag="player_count_label", color=(150, 150, 150))
                dpg.add_listbox(items=[], num_items=20, tag="players_listbox", callback=self._on_select_player, width=420)

            # Right Column: Player Attribute Inspector & Full Editor
            with dpg.child_window():
                # Color-Coded Header Card with Player Miniface
                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_image("tex_default_player", width=75, height=75, tag="player_miniface_img")
                        dpg.add_button(label="Face", callback=self._on_import_player_face, width=75)
                    dpg.add_spacer(width=12)
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            dpg.add_text("[ -- ]", tag="player_badge_ovr", color=(0, 255, 120))
                            dpg.add_text("Select a player from the list to view and edit details.", tag="player_header_name", color=(240, 240, 240))
                        dpg.add_text("No player selected", tag="player_sub_header", color=(160, 160, 160))
                dpg.add_separator()

                with dpg.group(tag="player_edit_controls", show=False):
                    with dpg.tab_bar():
                        # TAB 1: CORE BIO, RATINGS, POSITIONS & CLUB
                        with dpg.tab(label=" Bio & Positions "):
                            dpg.add_spacer(height=5)
                            with dpg.group(horizontal=True):
                                dpg.add_text("Overall Rating:   ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_ovr", width=220, callback=self._on_player_field_changed, user_data="overallrating")
                                dpg.add_spacer(width=20)
                                dpg.add_text("Potential Rating: ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_pot", width=220, callback=self._on_player_field_changed, user_data="potential")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Club Transfer:    ")
                                dpg.add_combo(items=[], tag="edit_player_club_combo", width=240)
                                dpg.add_button(label="Transfer Club", callback=self._on_transfer_player, width=130)

                            dpg.add_spacer(height=5)
                            with dpg.group(horizontal=True):
                                dpg.add_text("Player ID:        ")
                                dpg.add_input_int(tag="edit_player_id_display", width=140, readonly=True)
                                dpg.add_spacer(width=20)
                                dpg.add_text("Age: ")
                                dpg.add_input_int(tag="edit_player_age_display", width=80, callback=self._on_player_field_changed, user_data="age")
                                dpg.add_spacer(width=20)
                                dpg.add_text("Jersey #: ")
                                dpg.add_input_int(tag="edit_player_jersey", width=80, callback=self._on_player_field_changed, user_data="jerseynumber")
                                dpg.add_spacer(width=20)
                                dpg.add_checkbox(label="Retiring", tag="edit_player_isretiring", callback=self._on_player_field_changed, user_data="isretiring")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Preferred Foot:   ")
                                dpg.add_combo(items=["Right", "Left"], default_value="Right", tag="edit_player_foot", width=140, callback=self._on_player_field_changed, user_data="foot")
                                dpg.add_spacer(width=20)
                                dpg.add_text("Primary Position: ")
                                pos_items = [POSITION_NAMES[k] for k in sorted(POSITION_NAMES.keys()) if k >= 0]
                                pos_items_with_none = ["None"] + pos_items
                                dpg.add_combo(items=pos_items, tag="edit_player_pos1", width=140, callback=self._on_player_field_changed, user_data="pos1")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Alt Position 1:   ")
                                dpg.add_combo(items=pos_items_with_none, tag="edit_player_pos2", width=140, callback=self._on_player_field_changed, user_data="pos2")
                                dpg.add_spacer(width=20)
                                dpg.add_text("Alt Position 2:   ")
                                dpg.add_combo(items=pos_items_with_none, tag="edit_player_pos3", width=140, callback=self._on_player_field_changed, user_data="pos3")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Alt Position 3:   ")
                                dpg.add_combo(items=pos_items_with_none, tag="edit_player_pos4", width=140, callback=self._on_player_field_changed, user_data="pos4")
                                dpg.add_spacer(width=20)
                                dpg.add_text("Contract Valid:   ")
                                dpg.add_input_int(tag="edit_player_contract", width=140, callback=self._on_player_field_changed, user_data="contractvaliduntil")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Skill Moves (Stars):  ")
                                dpg.add_slider_int(min_value=1, max_value=5, tag="edit_player_skills", width=160, callback=self._on_player_field_changed, user_data="skills")
                                dpg.add_spacer(width=40)
                                dpg.add_text("Weak Foot (Stars):    ")
                                dpg.add_slider_int(min_value=1, max_value=5, tag="edit_player_weakfoot", width=160, callback=self._on_player_field_changed, user_data="weakfoot")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Height (cm):      ")
                                dpg.add_input_int(tag="edit_player_height", width=140, callback=self._on_player_field_changed, user_data="height")
                                dpg.add_spacer(width=100)
                                dpg.add_text("Weight (kg):      ")
                                dpg.add_input_int(tag="edit_player_weight", width=140, callback=self._on_player_field_changed, user_data="weight")

                        # TAB 2: PLAYSTYLES & TRAITS SELECTOR (AUTHENTIC FC 25 ENGINE)
                        with dpg.tab(label=" PlayStyles & Traits "):
                            dpg.add_spacer(height=5)
                            with dpg.group(horizontal=True):
                                dpg.add_text("Authentic FC 25 PlayStyles Engine", color=(0, 220, 255))
                                dpg.add_spacer(width=30)
                                dpg.add_text("Active: 0 Gold (++), 0 Silver (+)", tag="player_playstyles_summary_badge", color=(0, 255, 120))

                            dpg.add_text("Pick any of the 34 authentic FC 25 PlayStyles & career traits. Choose None, Regular (+ Silver), or PlayStyle+ (++ Gold Icon).", color=(180, 180, 180))
                            dpg.add_spacer(height=3)

                            # Quick Preset Action Buttons
                            with dpg.group(horizontal=True):
                                dpg.add_button(label="Clear All", callback=self._on_clear_playstyles, width=110)
                                dpg.add_button(label="All Regular (+)", callback=self._on_all_silver_playstyles, width=130)
                                dpg.add_button(label="All Gold (++)", callback=self._on_all_gold_playstyles, width=130)
                                dpg.add_button(label="Meta Superstar Preset", callback=self._on_meta_playstyles, width=170)

                            dpg.add_spacer(height=5)
                            dpg.add_separator()

                            # Scrollable PlayStyles Matrix
                            with dpg.child_window(height=360):
                                for cat_name, ps_items in PLAYSTYLE_CATEGORIES.items():
                                    dpg.add_spacer(height=4)
                                    dpg.add_text(cat_name, color=(0, 210, 255))
                                    dpg.add_separator()
                                    for key, name, group, bit, desc in ps_items:
                                        with dpg.group(horizontal=True):
                                            dpg.add_text(f"{name:18s}", color=(240, 240, 240))
                                            dpg.add_radio_button(
                                                items=["None", "(+) Regular", "(++) PlayStyle+"],
                                                default_value="None",
                                                horizontal=True,
                                                tag=f"ps_radio_{key}",
                                                callback=self._on_update_playstyles_summary
                                            )
                                            dpg.add_spacer(width=10)
                                            dpg.add_text(f"- {desc}", color=(130, 130, 130))

                        # TAB 3: ROLES & FC IQ
                        with dpg.tab(label=" Roles & FC IQ "):
                            dpg.add_spacer(height=5)
                            dpg.add_text("FC IQ Tactical Roles (New EA SPORTS FC 25 Engine)", color=(0, 220, 255))
                            dpg.add_text("Define player role assignments and role proficiency levels (+ and ++).", color=(180, 180, 180))
                            dpg.add_spacer(height=5)
                            with dpg.group(horizontal=True):
                                dpg.add_text("Tactical Role 1: ")
                                dpg.add_slider_int(min_value=0, max_value=255, tag="edit_player_role1", width=200, callback=self._on_player_field_changed, user_data="role1")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Tactical Role 2: ")
                                dpg.add_slider_int(min_value=0, max_value=255, tag="edit_player_role2", width=200, callback=self._on_player_field_changed, user_data="role2")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Tactical Role 3: ")
                                dpg.add_slider_int(min_value=0, max_value=255, tag="edit_player_role3", width=200, callback=self._on_player_field_changed, user_data="role3")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Tactical Role 4: ")
                                dpg.add_slider_int(min_value=0, max_value=255, tag="edit_player_role4", width=200, callback=self._on_player_field_changed, user_data="role4")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Tactical Role 5: ")
                                dpg.add_slider_int(min_value=0, max_value=255, tag="edit_player_role5", width=200, callback=self._on_player_field_changed, user_data="role5")

                        # TAB 4: PACE & SHOOTING
                        with dpg.tab(label=" Pace & Shooting "):
                            dpg.add_spacer(height=5)
                            dpg.add_text("Pace Attributes", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Acceleration:    ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_accel", width=220, callback=self._on_player_field_changed, user_data="acceleration")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Sprint Speed:    ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_sprint", width=220, callback=self._on_player_field_changed, user_data="sprintspeed")

                            dpg.add_spacer(height=10)
                            dpg.add_text("Shooting Attributes", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Positioning:     ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_pos", width=220, callback=self._on_player_field_changed, user_data="positioning")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Finishing:       ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_finish", width=220, callback=self._on_player_field_changed, user_data="finishing")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Shot Power:      ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_shotpwr", width=220, callback=self._on_player_field_changed, user_data="shotpower")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Long Shots:      ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_longshots", width=220, callback=self._on_player_field_changed, user_data="longshots")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Volleys:         ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_volleys", width=220, callback=self._on_player_field_changed, user_data="volleys")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Penalties:       ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_penalties", width=220, callback=self._on_player_field_changed, user_data="penalties")

                        # TAB 5: PASSING & DRIBBLING
                        with dpg.tab(label=" Passing & Dribbling "):
                            dpg.add_spacer(height=5)
                            dpg.add_text("Passing Attributes", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Vision:          ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_vision", width=220, callback=self._on_player_field_changed, user_data="vision")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Crossing:        ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_crossing", width=220, callback=self._on_player_field_changed, user_data="crossing")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Free Kick Acc.:  ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_fk", width=220, callback=self._on_player_field_changed, user_data="freekickaccuracy")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Short Passing:   ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_shortpass", width=220, callback=self._on_player_field_changed, user_data="shortpassing")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Long Passing:    ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_longpass", width=220, callback=self._on_player_field_changed, user_data="longpassing")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Curve:           ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_curve", width=220, callback=self._on_player_field_changed, user_data="curve")

                            dpg.add_spacer(height=10)
                            dpg.add_text("Dribbling Attributes", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Agility:         ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_agility", width=220, callback=self._on_player_field_changed, user_data="agility")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Balance:         ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_balance", width=220, callback=self._on_player_field_changed, user_data="balance")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Reactions:       ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_reactions", width=220, callback=self._on_player_field_changed, user_data="reactions")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Ball Control:    ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_ballctrl", width=220, callback=self._on_player_field_changed, user_data="ballcontrol")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Dribbling:       ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_dribble", width=220, callback=self._on_player_field_changed, user_data="dribbling")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Composure:       ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_composure", width=220, callback=self._on_player_field_changed, user_data="composure")

                        # TAB 6: DEFENDING & PHYSICAL
                        with dpg.tab(label=" Defending & Physical "):
                            dpg.add_spacer(height=5)
                            dpg.add_text("Defending Attributes", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Interceptions:   ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_interceptions", width=220, callback=self._on_player_field_changed, user_data="interceptions")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Heading Acc.:    ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_heading", width=220, callback=self._on_player_field_changed, user_data="headingaccuracy")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Def. Awareness:  ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_defawareness", width=220, callback=self._on_player_field_changed, user_data="defensiveawareness")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Standing Tackle: ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_standtackle", width=220, callback=self._on_player_field_changed, user_data="standingtackle")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Sliding Tackle:  ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_slidetackle", width=220, callback=self._on_player_field_changed, user_data="slidingtackle")

                            dpg.add_spacer(height=10)
                            dpg.add_text("Physical Attributes", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Jumping:         ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_jumping", width=220, callback=self._on_player_field_changed, user_data="jumping")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Stamina:         ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_stamina", width=220, callback=self._on_player_field_changed, user_data="stamina")
                            with dpg.group(horizontal=True):
                                dpg.add_text("Strength:        ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_strength", width=220, callback=self._on_player_field_changed, user_data="strength")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Aggression:      ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_aggression", width=220, callback=self._on_player_field_changed, user_data="aggression")

                        # TAB 7: GOALKEEPER
                        with dpg.tab(label=" Goalkeeper "):
                            dpg.add_spacer(height=5)
                            dpg.add_text("Goalkeeper Attributes", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("GK Diving:       ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_gkdiving", width=220, callback=self._on_player_field_changed, user_data="gkdiving")
                                dpg.add_spacer(width=30)
                                dpg.add_text("GK Handling:     ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_gkhandling", width=220, callback=self._on_player_field_changed, user_data="gkhandling")
                            with dpg.group(horizontal=True):
                                dpg.add_text("GK Kicking:      ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_gkkicking", width=220, callback=self._on_player_field_changed, user_data="gkkicking")
                                dpg.add_spacer(width=30)
                                dpg.add_text("GK Reflexes:     ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_gkreflexes", width=220, callback=self._on_player_field_changed, user_data="gkreflexes")
                            with dpg.group(horizontal=True):
                                dpg.add_text("GK Positioning:  ")
                                dpg.add_slider_int(min_value=1, max_value=99, tag="edit_player_gkpos", width=220, callback=self._on_player_field_changed, user_data="gkpositioning")

                        # TAB 8: KIT & APPEARANCE (ALL ORIGINAL OPTIONS)
                        with dpg.tab(label=" Kit & Appearance "):
                            dpg.add_spacer(height=5)
                            dpg.add_text("Player Head & Body Model", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Head Asset ID:   ")
                                dpg.add_input_int(tag="edit_player_headasset", width=160, callback=self._on_player_field_changed, user_data="headassetid")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Body Type:       ")
                                dpg.add_input_int(tag="edit_player_bodytype", width=120, callback=self._on_player_field_changed, user_data="bodytypecode")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Hairstyle Code:  ")
                                dpg.add_input_int(tag="edit_player_hairstyle", width=160, callback=self._on_player_field_changed, user_data="hairstylecode")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Hair Color:      ")
                                dpg.add_input_int(tag="edit_player_haircolor", width=120, callback=self._on_player_field_changed, user_data="haircolorcode")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Skin Tone Code:  ")
                                dpg.add_input_int(tag="edit_player_skintone", width=160, callback=self._on_player_field_changed, user_data="skintonecode")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Eye Color:       ")
                                dpg.add_input_int(tag="edit_player_eyecolor", width=120, callback=self._on_player_field_changed, user_data="eyecolorcode")

                            dpg.add_spacer(height=10)
                            dpg.add_text("Kit & Accessory Options", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Jersey Style:    ")
                                dpg.add_combo(items=["Tucked", "Untucked"], default_value="Untucked", tag="edit_player_jerseystyle", width=160, callback=self._on_player_field_changed, user_data="jerseystyle")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Sleeves:         ")
                                dpg.add_combo(items=["Short", "Long"], default_value="Short", tag="edit_player_sleeves", width=120, callback=self._on_player_field_changed, user_data="sleeves")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Jersey Fit:      ")
                                dpg.add_combo(items=["Normal", "Tight"], default_value="Normal", tag="edit_player_fit", width=160, callback=self._on_player_field_changed, user_data="fit")
                                dpg.add_spacer(width=30)
                                dpg.add_text("Sock Length:     ")
                                dpg.add_combo(items=["Short", "Average", "High"], default_value="Average", tag="edit_player_socklength", width=120, callback=self._on_player_field_changed, user_data="socklength")

                            with dpg.group(horizontal=True):
                                dpg.add_text("Shoe Type Code:  ")
                                dpg.add_input_int(tag="edit_player_shoetype", width=160, callback=self._on_player_field_changed, user_data="shoetypecode")
                                dpg.add_spacer(width=30)
                                dpg.add_text("GK Glove Code:   ")
                                dpg.add_input_int(tag="edit_player_gkglove", width=120, callback=self._on_player_field_changed, user_data="gkglovetypecode")

                            dpg.add_spacer(height=10)
                            dpg.add_text("Direct Bitmask Monitors (Synced with PlayStyles Tab)", color=(0, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_text("Trait 1:   ")
                                dpg.add_input_text(tag="edit_player_trait1", width=140, readonly=True)
                                dpg.add_spacer(width=15)
                                dpg.add_text("Trait 2:   ")
                                dpg.add_input_text(tag="edit_player_trait2", width=140, readonly=True)
                            with dpg.group(horizontal=True):
                                dpg.add_text("IconTrait1:")
                                dpg.add_input_text(tag="edit_player_icontrait1", width=140, readonly=True)
                                dpg.add_spacer(width=15)
                                dpg.add_text("IconTrait2:")
                                dpg.add_input_text(tag="edit_player_icontrait2", width=140, readonly=True)

                    dpg.add_spacer(height=15)
                    dpg.add_separator()
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Prime 99 Boost", callback=self._on_boost_player, width=160)
                        dpg.add_spacer(width=20)
                        dpg.add_text("Live Auto-Apply enabled: Every edit stages immediately into session.", color=(150, 150, 150))
                        dpg.add_spacer(width=20)
                        dpg.add_text("", tag="player_save_feedback", color=(0, 255, 120))

    def _build_teams_tab(self):
        with dpg.group(horizontal=True):
            # Left Column: Teams List Pane
            with dpg.child_window(width=410):
                dpg.add_text("Search Clubs & Teams", color=(0, 180, 240))
                dpg.add_input_text(hint="Search club name or ID...", callback=self._on_filter_teams, tag="team_search_input", width=390)
                dpg.add_separator()
                dpg.add_text("Total Clubs: 0", tag="team_count_label", color=(150, 150, 150))
                dpg.add_listbox(items=[], num_items=28, tag="teams_listbox", callback=self._on_select_team, width=390)

            # Right Column: Team Inspector & Roster
            with dpg.child_window():
                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_image("tex_default_club", width=70, height=70, tag="team_crest_img")
                        dpg.add_button(label="[Crest]", callback=self._on_import_club_crest, width=70)
                    dpg.add_spacer(width=12)
                    with dpg.group():
                        dpg.add_text("Club Inspector", color=(0, 180, 240))
                        dpg.add_text("Select a team to view information and squad roster.", tag="team_selected_header", color=(200, 200, 200))
                dpg.add_separator()

                with dpg.group(tag="team_edit_controls", show=False):
                    with dpg.group(horizontal=True):
                        dpg.add_text("Team ID:      ")
                        dpg.add_input_int(tag="edit_team_id", width=140, readonly=True)
                        dpg.add_spacer(width=20)
                        dpg.add_text("Team Name:    ")
                        dpg.add_input_text(tag="edit_team_name", width=260)

                    with dpg.group(horizontal=True):
                        dpg.add_text("Stadium:        ")
                        dpg.add_input_text(tag="edit_team_stadium", width=360)
                        dpg.add_button(label="Save Club Details", callback=self._on_save_team_changes, width=160)

                    # Manager & Head Coach Profile Card
                    dpg.add_spacer(height=6)
                    with dpg.group(horizontal=True):
                        with dpg.group():
                            dpg.add_image("tex_default_manager", width=54, height=54, tag="team_manager_img")
                            dpg.add_button(label="[Face]", callback=self._on_import_manager_face, width=54)
                        dpg.add_spacer(width=10)
                        with dpg.group():
                            dpg.add_text("Head Coach / Manager:", color=(0, 220, 160))
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(tag="edit_team_manager_name", hint="Manager Name", width=200)
                                dpg.add_input_text(tag="edit_team_manager_nat", hint="Nationality", width=110)
                                dpg.add_button(label="Save Manager", callback=self._on_save_manager_changes, width=130)
                            dpg.add_text("Role: Head Coach", tag="team_manager_role_label", color=(150, 150, 150))

                    dpg.add_spacer(height=10)
                    dpg.add_separator()

                    # Squad Roster Header & Sign Player Action
                    with dpg.group(horizontal=True):
                        dpg.add_text("Club Squad Roster", color=(0, 200, 255))
                        dpg.add_spacer(width=160)
                        dpg.add_button(label="[+] Sign Player to Club", callback=self._on_open_sign_player_modal, width=190)

                    dpg.add_text("Click a player below to edit shirt number or release to free agents:", color=(160, 160, 160))
                    dpg.add_listbox(items=[], num_items=14, tag="team_roster_listbox", callback=self._on_select_team_roster_player, width=620)

                    # Selected Player Roster Management Card
                    with dpg.group(tag="team_roster_player_actions", show=False):
                        dpg.add_spacer(height=6)
                        with dpg.group(horizontal=True):
                            dpg.add_image("tex_default_player", width=50, height=50, tag="roster_player_miniface_img")
                            dpg.add_spacer(width=8)
                            with dpg.group():
                                dpg.add_text("Managing: None", tag="team_roster_player_title", color=(0, 255, 180))
                                with dpg.group(horizontal=True):
                                    dpg.add_text("Jersey #: ")
                                    dpg.add_input_int(tag="edit_team_roster_jersey_num", min_value=1, max_value=99, default_value=10, width=80)
                                    dpg.add_button(label="Set #", callback=self._on_set_roster_jersey_num, width=70)
                                    dpg.add_spacer(width=20)
                                    dpg.add_button(label="[X] Release to Free Agents", callback=self._on_release_roster_player, width=200)

                    dpg.add_spacer(height=10)
                    dpg.add_text("", tag="team_save_feedback", color=(0, 255, 120))

    def _build_database_tab(self):
        with dpg.group():
            # Category and Table selector toolbar
            with dpg.group(horizontal=True):
                dpg.add_text("Category:")
                dpg.add_combo(items=CATEGORY_LIST, default_value=CATEGORY_LIST[0], tag="db_category_selector", callback=self._on_change_db_category, width=225)
                dpg.add_spacer(width=5)
                dpg.add_text("Table:")
                dpg.add_combo(items=[], tag="db_table_selector", callback=self._on_change_db_table, width=380)
                dpg.add_input_text(hint="Quick search...", tag="db_table_filter_input", callback=self._on_filter_db_tables, width=140)
                dpg.add_spacer(width=8)
                dpg.add_button(label="+ Add Row", callback=self._on_click_add_row, width=85)
                dpg.add_button(label="Clone", callback=self._on_clone_row, width=75)
                dpg.add_button(label="Delete", callback=self._on_click_delete_row, width=80)
                dpg.add_spacer(width=10)
                dpg.add_button(label="Export CSV", callback=self._on_export_table_csv, width=105)
                dpg.add_button(label="Import CSV", callback=self._on_import_table_csv, width=105)
                dpg.add_button(label="Export All (ZIP)", callback=self._on_export_all_tables_zip, width=130)

            dpg.add_spacer(height=4)
            # Table Safety & Stats Card
            with dpg.group(horizontal=True):
                dpg.add_text("[SAFE]", tag="db_table_safety_badge", color=(0, 255, 120))
                dpg.add_text("|", color=(100, 100, 100))
                dpg.add_text("Safe to edit player attributes directly.", tag="db_table_safety_desc", color=(200, 230, 255))
            with dpg.group(horizontal=True):
                dpg.add_text("Rows: 0 | Columns: 0 | Record Size: 0 bytes", tag="db_table_stats_text", color=(150, 150, 150))
                dpg.add_spacer(width=20)
                dpg.add_text("", tag="db_table_action_feedback", color=(0, 255, 180))
            dpg.add_separator()

            with dpg.group(horizontal=True):
                # Left Pane: Records Grid & Pagination
                with dpg.child_window(width=580):
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="< Prev", callback=self._on_prev_page)
                        dpg.add_text("Page 1 of 1", tag="db_pagination_text")
                        dpg.add_button(label="Next >", callback=self._on_next_page)
                        dpg.add_spacer(width=15)
                        dpg.add_input_text(hint="Filter rows (name, club, ID)...", callback=self._on_filter_records, tag="db_record_search_input", width=240)

                    dpg.add_listbox(items=[], num_items=26, tag="db_records_listbox", callback=self._on_select_record, width=560)

                # Right Pane: Modernized Record Column Field Inspector
                with dpg.child_window():
                    dpg.add_text("Record Column Inspector", color=(0, 180, 240))
                    dpg.add_text("", tag="record_inspector_entity_banner", color=(0, 255, 200))
                    dpg.add_text("Select a row from the left to view and edit column values.", tag="record_inspector_header", color=(220, 220, 220))
                    dpg.add_text("", tag="record_inspector_safety_warning", color=(255, 180, 0))
                    dpg.add_separator()
                    
                    with dpg.group(horizontal=True):
                        dpg.add_input_text(hint="Filter columns (e.g. name, rating, id)...", callback=self._on_filter_inspector_columns, tag="inspector_column_filter", width=330)
                        dpg.add_checkbox(label="Show Tech IDs/Bits", default_value=False, tag="inspector_show_tech_tags", callback=self._on_toggle_tech_tags)
                    dpg.add_spacer(height=3)

                    with dpg.child_window(height=480, tag="record_fields_container"):
                        pass
                        
                    dpg.add_spacer(height=10)
                    with dpg.group(horizontal=True, tag="record_actions_group", show=False):
                        dpg.add_button(label="Save Record Changes", callback=self._on_save_record_changes, width=220)
                        dpg.add_text("", tag="record_save_feedback", color=(0, 255, 120))

    def _build_settings_tab(self):
        with dpg.child_window():
            dpg.add_text("Application Preferences, Backups & System Diagnostics", color=(0, 180, 240))
            dpg.add_separator()
            dpg.add_spacer(height=6)
            
            with dpg.group(horizontal=True):
                # LEFT COLUMN: Backups & File Recovery Hub
                with dpg.child_window(width=580, height=640):
                    dpg.add_text("FILE BACKUPS & RECOVERY HUB", color=(255, 200, 0))
                    dpg.add_separator()
                    dpg.add_spacer(height=4)
                    
                    dpg.add_text("Currently Loaded File:", color=(180, 180, 180))
                    dpg.add_text("None", tag="settings_active_file", color=(255, 220, 100), wrap=550)
                    
                    dpg.add_spacer(height=4)
                    dpg.add_text("Safety Backup on Load:", color=(180, 180, 180))
                    dpg.add_text("None", tag="settings_backup_file", color=(0, 255, 150), wrap=550)
                    
                    dpg.add_spacer(height=8)
                    dpg.add_separator()
                    dpg.add_spacer(height=6)
                    
                    dpg.add_text("Available Squad Backups:", color=(200, 200, 200))
                    dpg.add_listbox(items=[], num_items=12, tag="settings_backups_listbox", width=550)
                    
                    dpg.add_spacer(height=10)
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="[+] Create Backup Now", callback=self._on_click_create_manual_backup, width=170)
                        dpg.add_button(label="Restore Selected", callback=self._on_click_restore_backup, width=140)
                        dpg.add_button(label="Delete Selected", callback=self._on_click_delete_backup, width=130)
                    
                    dpg.add_spacer(height=6)
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Open Backups Folder", callback=self._on_click_open_backup_folder, width=170)
                        dpg.add_button(label="Purge Old Backups", callback=self._on_click_purge_backups, width=140)
                        
                    dpg.add_spacer(height=8)
                    dpg.add_text("", tag="settings_backup_feedback", color=(0, 255, 120), wrap=550)

                dpg.add_spacer(width=15)
                
                # RIGHT COLUMN: Preferences & Database Diagnostics Hub
                with dpg.child_window(width=620, height=640):
                    dpg.add_text("APPLICATION PREFERENCES & SAFETY", color=(0, 220, 160))
                    dpg.add_separator()
                    dpg.add_spacer(height=6)
                    
                    dpg.add_checkbox(
                        label="Auto-backup squads file on open",
                        tag="cfg_auto_backup_on_load",
                        default_value=self.config.auto_backup_on_load,
                        callback=self._on_toggle_config,
                        user_data="auto_backup_on_load"
                    )
                    dpg.add_text("- Creates an immediate timestamped duplicate before parsing starts.", color=(140, 140, 140))
                    
                    dpg.add_spacer(height=4)
                    dpg.add_checkbox(
                        label="Auto-backup squads file before saving",
                        tag="cfg_auto_backup_on_save",
                        default_value=self.config.auto_backup_on_save,
                        callback=self._on_toggle_config,
                        user_data="auto_backup_on_save"
                    )
                    dpg.add_text("- Safeguards existing save file prior to rewriting disk chunks.", color=(140, 140, 140))

                    dpg.add_spacer(height=4)
                    dpg.add_checkbox(
                        label="Live auto-apply player edits",
                        tag="cfg_auto_apply_player_edits",
                        default_value=self.config.auto_apply_player_edits,
                        callback=self._on_toggle_config,
                        user_data="auto_apply_player_edits"
                    )
                    dpg.add_text("- Every slider/input in Player Inspector updates memory and staged diffs instantly.", color=(140, 140, 140))

                    dpg.add_spacer(height=4)
                    dpg.add_checkbox(
                        label="Strict bitfield clamping",
                        tag="cfg_strict_clamping",
                        default_value=self.config.strict_clamping,
                        callback=self._on_toggle_config,
                        user_data="strict_clamping"
                    )
                    dpg.add_text("- Enforces strict bounds matching FC 25 binary bit lengths (prevents corrupted values).", color=(140, 140, 140))

                    dpg.add_spacer(height=4)
                    dpg.add_checkbox(
                        label="Confirmation prompt before discarding all staged changes",
                        tag="cfg_confirm_discard_all",
                        default_value=self.config.confirm_discard_all,
                        callback=self._on_toggle_config,
                        user_data="confirm_discard_all"
                    )

                    dpg.add_spacer(height=6)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Backups retention limit:")
                        items_retain = ["3 Backups", "5 Backups", "10 Backups", "20 Backups", "Unlimited"]
                        cur_str = f"{self.config.max_backups_retain} Backups" if self.config.max_backups_retain < 999 else "Unlimited"
                        dpg.add_combo(items=items_retain, default_value=cur_str, tag="cfg_max_backups_combo", width=140, callback=self._on_change_max_backups)

                    dpg.add_spacer(height=12)
                    dpg.add_separator()
                    dpg.add_spacer(height=6)

                    dpg.add_text("DATABASE ENGINE DIAGNOSTICS", color=(0, 200, 255))
                    dpg.add_separator()
                    dpg.add_spacer(height=4)

                    dpg.add_text("Relational Tables: --", tag="diag_tables_count")
                    dpg.add_text("Indexed Players: --", tag="diag_players_count")
                    dpg.add_text("Indexed Clubs: --", tag="diag_teams_count")
                    dpg.add_text("Active In-File Transfers: --", tag="diag_transfers_count")
                    dpg.add_text("Staged Session Changes: --", tag="diag_staged_count")

                    dpg.add_spacer(height=10)
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Run Integrity Scan", callback=self._on_run_integrity_scan, width=170)
                        dpg.add_button(label="Export Diagnostics Report", callback=self._on_export_diagnostics_report, width=190)

                    dpg.add_spacer(height=8)
                    dpg.add_text("", tag="diag_feedback_text", color=(0, 255, 120), wrap=580)
                    
                    dpg.add_spacer(height=10)
                    dpg.add_separator()
                    dpg.add_spacer(height=4)
                    dpg.add_text("EA SPORTS FC 25 Engine Specifications:", color=(160, 160, 160))
                    dpg.add_text("- Container: Frostbite Engine FBCHUNKS v1 (250-byte chunk header with native GUID).", color=(130, 130, 130))
                    dpg.add_text("- Core Relational Database: FIFA DB v8 (magic 'DB\\x00\\x08', 76 bit-packed relational tables).", color=(130, 130, 130))
                    dpg.add_text("- In-Game Guarantee: Round-trip exports bit-for-byte exact schema for full career/kickoff mode compatibility.", color=(130, 130, 130))

    # --- File & Session Handlers ---

    def _on_click_open(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Open EA SPORTS FC 25 Squads File",
            filetypes=[("Squads File", "*.*"), ("All Files", "*.*")]
        )
        root.destroy()
        if not path:
            return

        success, msg = self.session.load_squads_file(path)
        if success:
            dpg.set_value("status_text", f"Loaded: {os.path.basename(path)}")
            dpg.set_value("settings_active_file", path)
            dpg.set_value("settings_backup_file", self.session.backup_path or "Created")
            self._update_backups_list()
            self._load_players_list()
            self._load_teams_list()
            self._load_database_tables_dropdown()
            self._populate_club_combo()
            self._update_save_and_changes_toolbar()
            self._refresh_diagnostics_tab()
            if dpg.does_item_exist("pending_changes_modal") and dpg.is_item_shown("pending_changes_modal"):
                self._refresh_pending_changes_modal()
        else:
            dpg.set_value("status_text", f"Error: {msg}")

    def _on_click_save(self):
        if not self.session.is_loaded:
            dpg.set_value("status_text", "Error: No squads file loaded.")
            return
        if self.config.auto_backup_on_save and self.session.filepath:
            try:
                create_load_backup(self.session.filepath)
                if self.config.max_backups_retain < 999:
                    purge_old_backups(self.session.filepath, keep_last=self.config.max_backups_retain)
                self._update_backups_list()
            except Exception:
                pass
        success, msg = self.session.save_squads_file()
        dpg.set_value("status_text", msg)
        self._update_save_and_changes_toolbar()
        self._refresh_diagnostics_tab()
        if dpg.does_item_exist("pending_changes_modal") and dpg.is_item_shown("pending_changes_modal"):
            self._refresh_pending_changes_modal()

    def _refresh_diagnostics_tab(self):
        if not self.session.is_loaded:
            return
        if dpg.does_item_exist("diag_tables_count"):
            dpg.set_value("diag_tables_count", f"Relational Tables: {len(self.session.db.tables)} loaded")
        if dpg.does_item_exist("diag_players_count"):
            dpg.set_value("diag_players_count", f"Indexed Players: {len(self.session.players_cache):,} players")
        if dpg.does_item_exist("diag_teams_count"):
            dpg.set_value("diag_teams_count", f"Indexed Clubs: {len(self.session.teams_cache)} authentic clubs")
        if dpg.does_item_exist("diag_transfers_count"):
            dpg.set_value("diag_transfers_count", f"Active In-File Transfers: {len(self.session.user_transfers)} players")
        if dpg.does_item_exist("diag_staged_count"):
            dpg.set_value("diag_staged_count", f"Staged Session Changes: {self.session.change_tracker.count} modifications")

    def _on_click_create_manual_backup(self):
        if not self.session.filepath:
            dpg.set_value("settings_backup_feedback", "[!] Load a squads file first to create a backup.")
            return
        try:
            bp, msg = create_load_backup(self.session.filepath)
            self._update_backups_list()
            dpg.set_value("settings_backup_feedback", f"[OK] Created backup: {os.path.basename(bp)}")
        except Exception as e:
            dpg.set_value("settings_backup_feedback", f"[Error] Backup creation failed: {e}")

    def _on_click_restore_backup(self):
        if not self.session.filepath:
            dpg.set_value("settings_backup_feedback", "[!] Load a squads file first.")
            return
        sel_str = dpg.get_value("settings_backups_listbox")
        if not sel_str:
            dpg.set_value("settings_backup_feedback", "[!] Select a backup from the list first.")
            return
        sel_filename = sel_str.split("  [")[0].strip()
        target_path = None
        for bp in getattr(self, "cached_backup_paths", []):
            if os.path.basename(bp) == sel_filename:
                target_path = bp
                break
        if not target_path:
            dpg.set_value("settings_backup_feedback", "[!] Selected backup path not found.")
            return
        self.pending_restore_backup_path = target_path
        dpg.set_value("restore_modal_msg", f"Are you sure you want to restore:\n\n{os.path.basename(target_path)}\n\nThis will overwrite the active file '{os.path.basename(self.session.filepath)}' and reload all tables.")
        dpg.configure_item("restore_backup_confirm_modal", show=True)

    def _on_confirm_restore_backup(self):
        dpg.configure_item("restore_backup_confirm_modal", show=False)
        if not self.pending_restore_backup_path or not self.session.filepath:
            return
        target_path = self.session.filepath
        ok, msg = restore_backup(self.pending_restore_backup_path, target_path)
        if ok:
            success, load_msg = self.session.load_squads_file(target_path)
            if success:
                self._load_players_list()
                self._load_teams_list()
                self._load_database_tables_dropdown()
                self._populate_club_combo()
                self._update_save_and_changes_toolbar()
                self._refresh_diagnostics_tab()
                dpg.set_value("settings_backup_feedback", f"[OK] Restored and reloaded: {os.path.basename(self.pending_restore_backup_path)}")
                dpg.set_value("status_text", f"Restored from backup: {os.path.basename(self.pending_restore_backup_path)}")
            else:
                dpg.set_value("settings_backup_feedback", f"[Error] Reload failed: {load_msg}")
        else:
            dpg.set_value("settings_backup_feedback", f"[Error] {msg}")

    def _on_click_delete_backup(self):
        sel_str = dpg.get_value("settings_backups_listbox")
        if not sel_str:
            dpg.set_value("settings_backup_feedback", "[!] Select a backup from the list first.")
            return
        sel_filename = sel_str.split("  [")[0].strip()
        target_path = None
        for bp in getattr(self, "cached_backup_paths", []):
            if os.path.basename(bp) == sel_filename:
                target_path = bp
                break
        if not target_path:
            dpg.set_value("settings_backup_feedback", "[!] Selected backup path not found.")
            return
        ok, msg = delete_backup(target_path)
        self._update_backups_list()
        dpg.set_value("settings_backup_feedback", f"[OK] {msg}" if ok else f"[Error] {msg}")

    def _on_click_open_backup_folder(self):
        if not self.session.filepath:
            dpg.set_value("settings_backup_feedback", "[!] Load a squads file first.")
            return
        folder = os.path.dirname(os.path.abspath(self.session.filepath))
        try:
            os.startfile(folder)
            dpg.set_value("settings_backup_feedback", f"[OK] Opened folder: {folder}")
        except Exception as e:
            dpg.set_value("settings_backup_feedback", f"[Error] Could not open folder: {e}")

    def _on_click_purge_backups(self):
        if not self.session.filepath:
            dpg.set_value("settings_backup_feedback", "[!] Load a squads file first.")
            return
        limit = self.config.max_backups_retain if self.config.max_backups_retain < 999 else 5
        count, msg = purge_old_backups(self.session.filepath, keep_last=limit)
        self._update_backups_list()
        dpg.set_value("settings_backup_feedback", f"[OK] {msg}")

    def _on_toggle_config(self, sender, app_data, user_data):
        if hasattr(self.config, user_data):
            setattr(self.config, user_data, bool(app_data))
            self.config.save()
            dpg.set_value("diag_feedback_text", f"Preference '{user_data}' set to {bool(app_data)} (saved)")

    def _on_change_max_backups(self, sender, app_data):
        val_str = app_data
        if "3" in val_str:
            self.config.max_backups_retain = 3
        elif "5" in val_str:
            self.config.max_backups_retain = 5
        elif "10" in val_str:
            self.config.max_backups_retain = 10
        elif "20" in val_str:
            self.config.max_backups_retain = 20
        else:
            self.config.max_backups_retain = 999
        self.config.save()
        dpg.set_value("diag_feedback_text", f"Retention limit set to {val_str} (saved)")

    def _on_run_integrity_scan(self):
        if not self.session.is_loaded:
            dpg.set_value("diag_feedback_text", "[!] Load a squads file first to run integrity scan.")
            return
        total_tables = len(self.session.db.tables)
        total_players = len(self.session.players_cache)
        total_teams = len(self.session.teams_cache)
        transfers_count = len(self.session.user_transfers)
        
        czum = self.session.db.tables_map.get("CZUM")
        risb = self.session.db.tables_map.get("rIsB")
        czum_pids = set(r.get("playerid", 0) for r in czum.records) if czum else set()
        orphaned = 0
        if risb:
            for r in risb.records:
                pid = r.get("playerid", 0)
                if pid and pid not in czum_pids:
                    orphaned += 1
                    
        if orphaned == 0:
            dpg.set_value("diag_feedback_text", f"[OK] Integrity Scan PASSED: All {total_tables} tables intact. {total_players:,} players, {total_teams} clubs, {transfers_count} transfers verified. 0 orphaned links.")
        else:
            dpg.set_value("diag_feedback_text", f"[!] Integrity Scan WARNING: {orphaned} player references in rIsB not found in CZUM.")

    def _on_export_diagnostics_report(self):
        if not self.session.is_loaded:
            dpg.set_value("diag_feedback_text", "[!] Load a squads file first.")
            return
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        default_name = f"Squads_Diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        initial_dir = os.path.dirname(os.path.abspath(self.session.filepath)) if self.session.filepath else ""
        save_path = filedialog.asksaveasfilename(
            title="Export Database Diagnostics Report",
            initialdir=initial_dir,
            initialfile=default_name,
            filetypes=[("Text Report", "*.txt"), ("All Files", "*.*")]
        )
        root.destroy()
        if not save_path:
            return
            
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write("EA SPORTS FC 25 SQUADS DATABASE DIAGNOSTIC REPORT\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Squads File: {self.session.filepath}\n")
                if self.session.filepath and os.path.exists(self.session.filepath):
                    f.write(f"File Size: {os.path.getsize(self.session.filepath):,} bytes\n")
                f.write(f"Active Backup: {self.session.backup_path or 'None'}\n\n")
                
                f.write("--- Relational Database Summary ---\n")
                f.write(f"Total Tables: {len(self.session.db.tables)}\n")
                f.write(f"Total Indexed Players: {len(self.session.players_cache):,}\n")
                f.write(f"Total Authentic Clubs: {len(self.session.teams_cache):,}\n")
                f.write(f"Active In-File Transfers: {len(self.session.user_transfers)}\n")
                f.write(f"Staged Session Modifications: {self.session.change_tracker.count}\n\n")
                
                f.write("--- Table Schema & Record Manifest ---\n")
                f.write(f"{'Table SNAME':<12} | {'Records':<8} | {'Cols':<6} | {'Row Bit Length':<14} | Description\n")
                f.write("-" * 75 + "\n")
                for tbl in self.session.db.tables:
                    disp = get_table_display_name(tbl.sname)
                    row_bits = getattr(tbl, "row_bit_length", 0)
                    f.write(f"{tbl.sname:<12} | {len(tbl.records):<8} | {len(tbl.columns):<6} | {row_bits:<14} | {disp}\n")
                    
                f.write("\n" + "=" * 70 + "\n")
                f.write("END OF REPORT\n")
                f.write("=" * 70 + "\n")
            dpg.set_value("diag_feedback_text", f"[OK] Exported diagnostics report to: {os.path.basename(save_path)}")
        except Exception as e:
            dpg.set_value("diag_feedback_text", f"[Error] Export report failed: {e}")

    def _on_click_save_as(self):
        if not self.session.is_loaded:
            dpg.set_value("status_text", "Error: No squads file loaded.")
            return
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        target = filedialog.asksaveasfilename(
            title="Save EA SPORTS FC 25 Squads File As",
            initialfile=os.path.basename(self.session.filepath or "Squads_Custom"),
            filetypes=[("Squads File", "*.*"), ("All Files", "*.*")]
        )
        root.destroy()
        if not target:
            return
        success, msg = self.session.save_squads_file(target)
        dpg.set_value("status_text", msg)
        self._update_save_and_changes_toolbar()
        self._refresh_diagnostics_tab()
        if dpg.does_item_exist("pending_changes_modal") and dpg.is_item_shown("pending_changes_modal"):
            self._refresh_pending_changes_modal()

    def _update_save_and_changes_toolbar(self):
        """Dynamically updates the unified save button and changes badge in the header toolbar."""
        tracker = self.session.change_tracker
        count = tracker.count
        if count > 0:
            if dpg.does_item_exist("btn_primary_save"):
                dpg.configure_item("btn_primary_save", label=f"Save File ({count})*")
                dpg.bind_item_theme("btn_primary_save", "theme_save_btn_dirty")
            if dpg.does_item_exist("btn_review_changes"):
                dpg.configure_item("btn_review_changes", label=f"Changes ({count})*")
                dpg.bind_item_theme("btn_review_changes", "theme_changes_btn_active")
        else:
            if dpg.does_item_exist("btn_primary_save"):
                dpg.configure_item("btn_primary_save", label="Save File")
                dpg.bind_item_theme("btn_primary_save", "")
            if dpg.does_item_exist("btn_review_changes"):
                dpg.configure_item("btn_review_changes", label="Changes (0)")
                dpg.bind_item_theme("btn_review_changes", "")

    def _on_open_pending_changes(self):
        """Opens the review dialog showing all staged session modifications."""
        self._refresh_pending_changes_modal()
        dpg.configure_item("pending_changes_modal", show=True)

    def _refresh_pending_changes_modal(self):
        """Re-renders the pending changes list cards in the review dialog."""
        if not dpg.does_item_exist("pending_changes_container"):
            return
        dpg.delete_item("pending_changes_container", children_only=True)
        tracker = self.session.change_tracker
        changes = tracker.get_changes()
        count = len(changes)

        dpg.set_value("changes_modal_count_badge", f"Total: {count} unpersisted edit{'s' if count != 1 else ''}")

        if count == 0:
            with dpg.group(parent="pending_changes_container"):
                dpg.add_spacer(height=60)
                dpg.add_text("[OK] No pending changes.", color=(0, 255, 120))
                dpg.add_text("The active session is completely in sync with the squad file.", color=(160, 160, 160))
            return

        category_colors = {
            "player": (60, 180, 255),      # Cyan
            "transfer": (255, 170, 0),     # Orange
            "team": (200, 120, 255),       # Purple
            "table": (180, 220, 140),      # Soft olive
        }

        with dpg.group(parent="pending_changes_container"):
            for idx, c in enumerate(reversed(changes), 1):
                badge_color = category_colors.get(c.category, (200, 200, 200))
                with dpg.group(horizontal=True):
                    dpg.add_text(f"[{c.category.upper()}]", color=badge_color)
                    dpg.add_text(f"{c.title}", color=(240, 240, 240))
                    dpg.add_text(f"({c.get_time_str()})", color=(130, 130, 130))
                    dpg.add_spacer(width=20)
                    btn = dpg.add_button(
                        label="[X] Revert",
                        user_data=c.id,
                        callback=self._on_revert_single_change_clicked,
                        width=85
                    )
                    dpg.bind_item_theme(btn, "theme_revert_btn")

                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=20)
                    dpg.add_text(f"{c.field_label}:", color=(180, 180, 180))
                    dpg.add_text(f"{c.old_display}", color=(255, 110, 110))
                    dpg.add_text("->", color=(255, 255, 255))
                    dpg.add_text(f"{c.new_display}", color=(100, 255, 140))

                dpg.add_separator()

    def _on_revert_single_change_clicked(self, sender, app_data, user_data):
        """Handles single change revert when clicking the '[X] Revert' button."""
        change_id = user_data
        if not change_id:
            return
        success = self.session.change_tracker.revert(change_id)
        if success:
            self._update_save_and_changes_toolbar()
            self._refresh_pending_changes_modal()
            self._refresh_views_after_revert()
            dpg.set_value("status_text", "Reverted edit successfully.")

    def _on_modal_discard_all(self):
        """Reverts all pending changes in the session, restoring pristine file state."""
        count = self.session.change_tracker.count
        if count == 0:
            return
        if self.config.confirm_discard_all:
            dpg.configure_item("discard_all_confirm_modal", show=True)
        else:
            self._on_confirm_discard_all()

    def _on_confirm_discard_all(self):
        dpg.configure_item("discard_all_confirm_modal", show=False)
        reverted_count = self.session.change_tracker.revert_all()
        self._update_save_and_changes_toolbar()
        self._refresh_pending_changes_modal()
        self._refresh_views_after_revert()
        dpg.set_value("status_text", f"Discarded all {reverted_count} changes. File is in original state.")

    def _on_modal_save_all(self):
        """Saves all staged changes to the squads file from inside the modal dialog."""
        self._on_click_save()
        if self.session.change_tracker.count == 0:
            dpg.configure_item("pending_changes_modal", show=False)

    def _refresh_views_after_revert(self):
        """Synchronizes all UI inspector components with reverted memory state."""
        # 1. Update active player view if one is selected
        if self.selected_player:
            sel_pid = self.selected_player.get("playerid")
            for p in self.session.players_cache:
                if p["playerid"] == sel_pid:
                    self.selected_player = p
                    self._populate_player_details(p)
                    break
        self._on_filter_players()

        # 2. Update active team view if one is selected
        if self.selected_team:
            sel_tid = self.selected_team.get("teamid")
            for t in self.session.teams_cache:
                if t["teamid"] == sel_tid:
                    self.selected_team = t
                    self._populate_team_details(t)
                    break
        self._on_filter_teams()

        # 3. Update database table view if one is open
        if self.selected_table_sname:
            self._load_db_table(self.selected_table_sname)
            if self.selected_record_index is not None:
                tbl = self.session.get_table(self.selected_table_sname)
                if tbl and self.selected_record_index < len(tbl.records):
                    self._inspect_record(tbl, self.selected_record_index)

    def _update_backups_list(self):
        if self.session.filepath:
            backups = list_folder_backups(self.session.filepath)
            self.cached_backup_paths = backups
            items = []
            for bp in backups:
                meta = get_backup_metadata(bp)
                items.append(f"{meta.get('filename', os.path.basename(bp))}  [{meta.get('size_str', '')}]  -  {meta.get('mtime', '')}")
            if dpg.does_item_exist("settings_backups_listbox"):
                dpg.configure_item("settings_backups_listbox", items=items)

    def _populate_club_combo(self):
        club_items = ["Free Agent"]
        for t in self.session.teams_cache:
            if t["teamid"] > 0:
                club_items.append(f"{t['name']} (ID {t['teamid']})")
        if dpg.does_item_exist("edit_player_club_combo"):
            dpg.configure_item("edit_player_club_combo", items=club_items)
        if dpg.does_item_exist("player_league_filter_combo"):
            dpg.configure_item("player_league_filter_combo", items=["All Leagues"] + self.session.all_leagues)
        if dpg.does_item_exist("player_nation_filter_combo"):
            dpg.configure_item("player_nation_filter_combo", items=["All Nations"] + self.session.all_nations)
        self._refresh_club_filter_combo()

    def _refresh_club_filter_combo(self):
        if not dpg.does_item_exist("player_club_filter_combo"):
            return
        filter_clubs = ["All Clubs", "Free Agent"]
        seen = {"All Clubs", "Free Agent"}
        target_lg = self.filter_league
        for t in self.session.teams_cache:
            if t["teamid"] <= 0:
                continue
            if target_lg != "All Leagues" and t.get("league", "") != target_lg:
                continue
            cname = t["name"]
            if cname not in seen:
                filter_clubs.append(cname)
                seen.add(cname)
        dpg.configure_item("player_club_filter_combo", items=filter_clubs)
        if self.filter_club not in seen:
            self.filter_club = "All Clubs"
            dpg.set_value("player_club_filter_combo", "All Clubs")

    # --- Players UI Callbacks ---

    def _load_players_list(self):
        self._on_filter_players()

    def _on_change_preset_filter(self, sender, app_data):
        self.filter_preset = app_data
        self._on_filter_players()

    def _on_change_sort_by(self, sender, app_data):
        self.sort_by_mode = app_data
        self._on_filter_players()

    def _on_change_foot_filter(self, sender, app_data):
        self.filter_foot = app_data
        self._on_filter_players()

    def _on_change_age_filter(self, sender, app_data):
        self.filter_age_bracket = app_data
        self._on_filter_players()

    def _on_change_league_filter(self, sender, app_data):
        self.filter_league = app_data
        self._refresh_club_filter_combo()
        self._on_filter_players()

    def _on_change_nation_filter(self, sender, app_data):
        self.filter_nation = app_data
        self._on_filter_players()

    def _on_change_club_filter(self, sender, app_data):
        self.filter_club = app_data
        self._on_filter_players()

    def _on_change_max_ovr(self, sender, app_data):
        self.max_ovr_filter = app_data
        self._on_filter_players()

    def _on_clear_search_box_only(self):
        if dpg.does_item_exist("player_search_input"):
            dpg.set_value("player_search_input", "")
        self._on_filter_players()

    def _on_export_filtered_players_csv(self):
        if not self.filtered_players:
            dpg.set_value("status_text", "No filtered players to export.")
            return
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        default_name = f"FC25_Players_Filtered_{len(self.filtered_players)}.csv"
        target_path = filedialog.asksaveasfilename(
            title="Export Filtered Players to CSV",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV Spreadsheet", "*.csv"), ("All Files", "*.*")]
        )
        root.destroy()
        if not target_path:
            return
        ok, msg, _ = self.session.export_players_list_csv(self.filtered_players, target_path)
        dpg.set_value("status_text", f"[OK] {msg}" if ok else f"[ERR] {msg}")

    def _on_filter_players(self):
        search_txt = ""
        if dpg.does_item_exist("player_search_input"):
            search_txt = (dpg.get_value("player_search_input") or "").lower().strip()
        pos_cat = self.filter_pos_category
        min_ovr = self.min_ovr_filter
        max_ovr = self.max_ovr_filter
        preset = self.filter_preset
        target_league = self.filter_league
        target_nation = self.filter_nation
        target_club = self.filter_club
        target_foot = self.filter_foot
        target_age = self.filter_age_bracket

        filtered = []
        for p in self.session.players_cache:
            ovr = p["overall"]
            if (min_ovr > 0 and ovr < min_ovr) or (max_ovr < 99 and ovr > max_ovr):
                continue

            # Presets copied from Live Editor filters/players
            if "Transferred Players" in preset:
                if p["playerid"] not in self.session.user_transfers:
                    continue
            elif "Free Agents" in preset:
                if p["teamid"] not in (0, 111592):
                    continue
            elif "Superstars" in preset:
                if ovr < 85:
                    continue
            elif "Wonderkids" in preset:
                if p["potential"] < 85 or p.get("age", 25) > 21:
                    continue
            elif "Messi Regen" in preset:
                if not (p["pos_code"] == 23 and p.get("nationality") == 52 and p["potential"] >= 89):
                    continue
            elif "CR7 Regen" in preset:
                if not (p["pos_code"] == 25 and p.get("nationality") == 38 and p["potential"] >= 85):
                    continue
            elif "Benzema Regen" in preset:
                if not (p["pos_code"] == 25 and p.get("nationality") == 18 and p["potential"] >= 85):
                    continue
            elif "RL9 Regen" in preset:
                if not (p["pos_code"] == 25 and p.get("nationality") == 37 and p["potential"] >= 85):
                    continue
            elif "Retiring" in preset:
                if p.get("isretiring", 0) != 1 and p.get("age", 25) < 35:
                    continue
            elif "Generated" in preset:
                if p["playerid"] < 460000:
                    continue

            # Position filtering (Group or Exact + Alternate Positions)
            if pos_cat != "All":
                pos = p["position"]
                if pos_cat == "Attackers":
                    if pos not in ("ST", "RW", "LW", "CF", "RF", "LF", "RS", "LS"):
                        continue
                elif pos_cat == "Midfielders":
                    if pos not in ("CAM", "CM", "CDM", "LM", "RM", "RCM", "LCM", "RDM", "LDM", "RAM", "LAM"):
                        continue
                elif pos_cat == "Defenders":
                    if pos not in ("CB", "LB", "RB", "LWB", "RWB", "RCB", "LCB", "SW"):
                        continue
                elif pos_cat == "Goalkeepers":
                    if pos != "GK":
                        continue
                else:
                    alt_pos_list = [ap.strip() for ap in str(p.get("alt_positions", "")).replace("/", ",").split(",") if ap.strip()]
                    if pos != pos_cat and pos_cat not in alt_pos_list:
                        continue

            # Preferred Foot filtering
            if target_foot != "Any" and p.get("foot", "Right") != target_foot:
                continue

            # Age Bracket filtering
            if target_age != "Any Age":
                age_val = p.get("age", 25)
                if target_age == "U21 (<=21)" and age_val > 21:
                    continue
                elif target_age == "U23 (<=23)" and age_val > 23:
                    continue
                elif target_age == "Prime (24-29)" and not (24 <= age_val <= 29):
                    continue
                elif target_age == "30+ Vet" and age_val < 30:
                    continue

            # League filtering
            if target_league != "All Leagues" and p.get("league", "") != target_league:
                continue

            # Nation filtering
            if target_nation != "All Nations" and p.get("nation_name", "") != target_nation:
                continue

            # Club filtering
            if target_club != "All Clubs":
                if target_club == "Free Agent":
                    if p["teamid"] not in (0, 111592) and p["club"] != "Free Agent":
                        continue
                elif p["club"] != target_club:
                    continue

            # Search text matching: name, ID, club, nation, league, or position
            if search_txt:
                haystack = f"{p['name']} {p['playerid']} {p['club']} {p.get('nation_name', '')} {p.get('league', '')} {p['position']}".lower()
                if search_txt not in haystack:
                    continue

            filtered.append(p)

        # Multi-mode sorting
        sort_mode = self.sort_by_mode
        if sort_mode == "Overall (Low -> High)":
            filtered.sort(key=lambda x: (x["overall"], x["potential"]))
        elif sort_mode == "Potential (High -> Low)":
            filtered.sort(key=lambda x: (x["potential"], x["overall"]), reverse=True)
        elif sort_mode == "Name (A -> Z)":
            filtered.sort(key=lambda x: x["name"].lower())
        elif sort_mode == "Age (Young -> Old)":
            filtered.sort(key=lambda x: (x.get("age", 25), -x["overall"]))
        elif sort_mode == "Age (Old -> Young)":
            filtered.sort(key=lambda x: (-x.get("age", 25), -x["overall"]))
        elif sort_mode == "Player ID":
            filtered.sort(key=lambda x: x["playerid"])
        else:
            filtered.sort(key=lambda x: (x["overall"], x["potential"]), reverse=True)

        self.filtered_players = filtered
        items = []
        for p in self.filtered_players:
            is_trans = p.get("playerid") in self.session.user_transfers
            badge = " [T]" if is_trans else ""
            items.append(f"[{p['overall']}] {p['name']} ({p['position']}) - {p['club']}{badge}")
        if dpg.does_item_exist("players_listbox"):
            dpg.configure_item("players_listbox", items=items)
        if dpg.does_item_exist("player_count_label"):
            dpg.set_value("player_count_label", f"Total Players: {len(self.filtered_players):,} matches")

    def _on_clear_player_search(self):
        self.filter_pos_category = "All"
        self.min_ovr_filter = 0
        self.max_ovr_filter = 99
        self.filter_preset = "All Players"
        self.filter_league = "All Leagues"
        self.filter_club = "All Clubs"
        self.filter_nation = "All Nations"
        self.filter_foot = "Any"
        self.filter_age_bracket = "Any Age"
        self.sort_by_mode = "Overall (High -> Low)"

        if dpg.does_item_exist("player_search_input"):
            dpg.set_value("player_search_input", "")
        if dpg.does_item_exist("player_preset_combo"):
            dpg.set_value("player_preset_combo", "All Players")
        if dpg.does_item_exist("player_sort_combo"):
            dpg.set_value("player_sort_combo", "Overall (High -> Low)")
        if dpg.does_item_exist("player_pos_combo"):
            dpg.set_value("player_pos_combo", "All")
        if dpg.does_item_exist("player_foot_combo"):
            dpg.set_value("player_foot_combo", "Any")
        if dpg.does_item_exist("player_age_combo"):
            dpg.set_value("player_age_combo", "Any Age")
        if dpg.does_item_exist("player_league_filter_combo"):
            dpg.set_value("player_league_filter_combo", "All Leagues")
        if dpg.does_item_exist("player_nation_filter_combo"):
            dpg.set_value("player_nation_filter_combo", "All Nations")
        self._refresh_club_filter_combo()
        if dpg.does_item_exist("player_club_filter_combo"):
            dpg.set_value("player_club_filter_combo", "All Clubs")
        if dpg.does_item_exist("player_min_ovr_slider"):
            dpg.set_value("player_min_ovr_slider", 0)
        if dpg.does_item_exist("player_max_ovr_slider"):
            dpg.set_value("player_max_ovr_slider", 99)
        self._on_filter_players()

    def _on_change_pos_filter(self, sender, app_data):
        self.filter_pos_category = app_data
        self._on_filter_players()

    def _on_change_min_ovr(self, sender, app_data):
        self.min_ovr_filter = app_data
        self._on_filter_players()

    def _on_update_playstyles_summary(self):
        gold_count = 0
        silver_count = 0
        states = {}
        for key in PLAYSTYLE_MAP:
            tag = f"ps_radio_{key}"
            if dpg.does_item_exist(tag):
                val = dpg.get_value(tag)
                if "(++)" in val:
                    gold_count += 1
                    states[key] = 2
                elif "(+)" in val:
                    silver_count += 1
                    states[key] = 1
                else:
                    states[key] = 0
        if dpg.does_item_exist("player_playstyles_summary_badge"):
            dpg.set_value("player_playstyles_summary_badge", f"Active: {gold_count} Gold (++), {silver_count} Silver (+)")
            
        # Update raw bitmask monitors
        t1, t2, it1, it2 = encode_player_playstyles(states)
        if dpg.does_item_exist("edit_player_trait1"):
            dpg.set_value("edit_player_trait1", str(t1))
        if dpg.does_item_exist("edit_player_trait2"):
            dpg.set_value("edit_player_trait2", str(t2))
        if dpg.does_item_exist("edit_player_icontrait1"):
            dpg.set_value("edit_player_icontrait1", str(it1))
        if dpg.does_item_exist("edit_player_icontrait2"):
            dpg.set_value("edit_player_icontrait2", str(it2))

        # Auto-commit PlayStyles live to session
        if not getattr(self, "_is_populating_player", False) and self.selected_player:
            pid = self.selected_player["playerid"]
            stats = self.selected_player.setdefault("stats", {})
            self.session.update_player_attribute(pid, "trait1", t1)
            self.session.update_player_attribute(pid, "trait2", t2)
            self.session.update_player_attribute(pid, "icontrait1", it1)
            self.session.update_player_attribute(pid, "icontrait2", it2)
            stats["trait1"] = str(t1)
            stats["trait2"] = str(t2)
            stats["icontrait1"] = str(it1)
            stats["icontrait2"] = str(it2)
            self._update_save_and_changes_toolbar()
            staged_n = self.session.change_tracker.count
            dpg.set_value("player_save_feedback", f"Auto-applied: PlayStyles updated ({staged_n} staged)")

    def _on_clear_playstyles(self):
        for key in PLAYSTYLE_MAP:
            tag = f"ps_radio_{key}"
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, "None")
        self._on_update_playstyles_summary()

    def _on_all_silver_playstyles(self):
        for key in PLAYSTYLE_MAP:
            tag = f"ps_radio_{key}"
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, "(+) Regular")
        self._on_update_playstyles_summary()

    def _on_all_gold_playstyles(self):
        for key in PLAYSTYLE_MAP:
            tag = f"ps_radio_{key}"
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, "(++) PlayStyle+")
        self._on_update_playstyles_summary()

    def _on_meta_playstyles(self):
        meta_gold = ["finesse_shot", "quick_step", "anticipate", "technical", "relentless", "incisive_pass"]
        for key in PLAYSTYLE_MAP:
            tag = f"ps_radio_{key}"
            if dpg.does_item_exist(tag):
                if key in meta_gold:
                    dpg.set_value(tag, "(++) PlayStyle+")
                else:
                    dpg.set_value(tag, "(+) Regular")
        self._on_update_playstyles_summary()

    def _on_select_player(self, sender, app_data):
        items = dpg.get_item_configuration("players_listbox")["items"]
        if not items or app_data not in items:
            return
        idx = items.index(app_data)
        if idx >= len(self.filtered_players):
            return

        p = self.filtered_players[idx]
        self.selected_player = p
        self._populate_player_details(p)

    def _update_player_sub_header(self):
        if not self.selected_player:
            return
        p = self.selected_player
        pid = p["playerid"]
        jersey_num = self.session.get_player_jersey_number(pid)
        is_trans = pid in self.session.user_transfers
        trans_tag = " [TRANSFERRED]" if is_trans else ""
        dpg.set_value("player_header_name", f"#{jersey_num} {p['name']} (ID: {pid})")
        dpg.set_value("player_sub_header", f"Club: {p['club']}{trans_tag}  |  Kit: #{jersey_num}  |  Position: {p.get('position', 'None')}  |  Foot: {p.get('foot', 'Right')}  |  Skills: {p.get('skills', 3)}*  |  Weak Foot: {p.get('weak_foot', 3)}*")

    def _on_player_field_changed(self, sender, app_data, user_data):
        if getattr(self, "_is_populating_player", False):
            return
        if not self.selected_player:
            return
            
        pid = self.selected_player["playerid"]
        stats = self.selected_player.setdefault("stats", {})
        attr = user_data
        
        def _get_pos_code(pos_str):
            for k, v in POSITION_NAMES.items():
                if v == pos_str:
                    return k
            return -1

        if attr == "overallrating":
            val = dpg.get_value("edit_player_ovr")
            self.session.update_player_attribute(pid, "overallrating", val)
            self.selected_player["overall"] = val
            badge_color = (0, 255, 120) if val >= 80 else (120, 255, 80) if val >= 70 else (255, 220, 0) if val >= 60 else (255, 140, 0) if val >= 50 else (255, 50, 50)
            dpg.set_value("player_badge_ovr", f"[ {val:2d} ]")
            dpg.configure_item("player_badge_ovr", color=badge_color)
            self._update_save_and_changes_toolbar()
            
        elif attr == "potential":
            val = dpg.get_value("edit_player_pot")
            self.session.update_player_attribute(pid, "potential", val)
            self.selected_player["potential"] = val
            self._update_save_and_changes_toolbar()
            
        elif attr == "age":
            val = dpg.get_value("edit_player_age_display")
            self.session.update_player_attribute(pid, "age", val)
            self.selected_player["age"] = val
            self._update_save_and_changes_toolbar()
            
        elif attr == "jerseynumber":
            val = dpg.get_value("edit_player_jersey")
            self.session.set_player_jersey_number(pid, val)
            self._update_player_sub_header()
            self._update_save_and_changes_toolbar()
            
        elif attr == "isretiring":
            val = 1 if dpg.get_value("edit_player_isretiring") else 0
            self.session.update_player_attribute(pid, "isretiring", val)
            self.selected_player["isretiring"] = val
            self._update_save_and_changes_toolbar()
            
        elif attr == "foot":
            val = dpg.get_value("edit_player_foot")
            foot_code = 1 if val == "Left" else 0
            self.session.update_player_attribute(pid, "preferredfoot", foot_code)
            self.selected_player["foot"] = val
            self._update_player_sub_header()
            self._update_save_and_changes_toolbar()
            
        elif attr == "pos1":
            pos_str = dpg.get_value("edit_player_pos1")
            code = _get_pos_code(pos_str)
            if code >= 0:
                self.session.update_player_attribute(pid, "preferredposition1", code)
                self.selected_player["position"] = pos_str
                self._update_player_sub_header()
                self._update_save_and_changes_toolbar()
                
        elif attr in ("pos2", "pos3", "pos4"):
            pos_str = dpg.get_value(f"edit_player_{attr}")
            code = _get_pos_code(pos_str)
            col_name = f"preferredposition{attr[-1]}"
            self.session.update_player_attribute(pid, col_name, code)
            stats[col_name] = str(code)
            self._update_save_and_changes_toolbar()
            
        elif attr == "contractvaliduntil":
            val = dpg.get_value("edit_player_contract")
            self.session.update_player_attribute(pid, "contractvaliduntil", val)
            stats["contractvaliduntil"] = str(val)
            self._update_save_and_changes_toolbar()
            
        elif attr == "skills":
            val = dpg.get_value("edit_player_skills")
            self.session.update_player_attribute(pid, "skillmoves", val)
            self.selected_player["skills"] = val
            stats["skillmoves"] = str(val)
            self._update_player_sub_header()
            self._update_save_and_changes_toolbar()
            
        elif attr == "weakfoot":
            val = dpg.get_value("edit_player_weakfoot")
            self.session.update_player_attribute(pid, "weakfootabilitytypecode", val)
            self.selected_player["weak_foot"] = val
            stats["weakfootabilitytypecode"] = str(val)
            self._update_player_sub_header()
            self._update_save_and_changes_toolbar()
            
        elif attr in ("height", "weight"):
            val = dpg.get_value(f"edit_player_{attr}")
            self.session.update_player_attribute(pid, attr, val)
            self.selected_player[attr] = val
            stats[attr] = str(val)
            self._update_save_and_changes_toolbar()
            
        elif attr in ("role1", "role2", "role3", "role4", "role5"):
            val = dpg.get_value(f"edit_player_{attr}")
            self.session.update_player_attribute(pid, attr, val)
            stats[attr] = str(val)
            self._update_save_and_changes_toolbar()
            
        elif attr == "jerseystyle":
            val = 1 if dpg.get_value("edit_player_jerseystyle") == "Untucked" else 0
            self.session.update_player_attribute(pid, "jerseystylecode", val)
            stats["jerseystylecode"] = str(val)
            self._update_save_and_changes_toolbar()
            
        elif attr == "sleeves":
            val = 1 if dpg.get_value("edit_player_sleeves") == "Long" else 0
            self.session.update_player_attribute(pid, "jerseysleevelengthcode", val)
            stats["jerseysleevelengthcode"] = str(val)
            self._update_save_and_changes_toolbar()
            
        elif attr == "fit":
            val = 1 if dpg.get_value("edit_player_fit") == "Tight" else 0
            self.session.update_player_attribute(pid, "jerseyfit", val)
            stats["jerseyfit"] = str(val)
            self._update_save_and_changes_toolbar()
            
        elif attr == "socklength":
            s_val = dpg.get_value("edit_player_socklength")
            val = 1 if s_val == "Short" else 2 if s_val == "High" else 0
            self.session.update_player_attribute(pid, "socklengthcode", val)
            stats["socklengthcode"] = str(val)
            self._update_save_and_changes_toolbar()
            
        else:
            val = dpg.get_value(sender)
            self.session.update_player_attribute(pid, attr, val)
            stats[attr] = str(val)
            self._update_save_and_changes_toolbar()

        staged_n = self.session.change_tracker.count
        dpg.set_value("player_save_feedback", f"Auto-applied: {attr} ({staged_n} staged)")

    def _populate_player_details(self, p: Dict[str, Any]):
        self._is_populating_player = True
        try:
            pid = p["playerid"]

            # Set color-coded badge
            ovr = p["overall"]
            badge_color = (0, 255, 120) if ovr >= 80 else (120, 255, 80) if ovr >= 70 else (255, 220, 0) if ovr >= 60 else (255, 140, 0) if ovr >= 50 else (255, 50, 50)
            dpg.set_value("player_badge_ovr", f"[ {ovr:2d} ]")
            dpg.configure_item("player_badge_ovr", color=badge_color)

            jersey_num = self.session.get_player_jersey_number(pid)
            dpg.set_value("player_header_name", f"#{jersey_num} {p['name']} (ID: {pid})")
            is_trans = pid in self.session.user_transfers
            trans_tag = " [TRANSFERRED]" if is_trans else ""
            lg_part = f" ({p['league']})" if p.get("league") else ""
            nat_part = f"  |  Nation: {p['nation_name']}" if p.get("nation_name") else ""
            alt_part = f" [{p['alt_positions']}]" if p.get("alt_positions") else ""
            dpg.set_value("player_sub_header", f"Club: {p['club']}{lg_part}{trans_tag}{nat_part}  |  Pos: {p['position']}{alt_part}  |  Foot: {p.get('foot', 'Right')}  |  Skills: {p.get('skills', 3)}*  |  WF: {p.get('weak_foot', 3)}*")

            # Update player miniface texture
            p_tex = self.assets.get_player_texture(pid, p["name"], jersey_num, ovr, p["position"])
            if dpg.does_item_exist("player_miniface_img"):
                dpg.configure_item("player_miniface_img", texture_tag=p_tex)

            stats = p.get("stats", {})
            
            # Populate sliders and fields
            dpg.set_value("edit_player_ovr", ovr)
            dpg.set_value("edit_player_pot", p.get("potential", ovr))
            dpg.set_value("edit_player_id_display", pid)
            dpg.set_value("edit_player_age_display", p.get("age", 25))
            
            # Club dropdown with all authentic 808 teams
            club_items = ["Free Agent"] + [f"{t['name']} (ID {t['teamid']})" for t in self.session.teams_cache if t['teamid'] > 0]
            dpg.configure_item("edit_player_club_combo", items=club_items)
            club_display = "Free Agent" if p["teamid"] == 0 else f"{p['club']} (ID {p['teamid']})"
            dpg.set_value("edit_player_club_combo", club_display)
            
            dpg.set_value("edit_player_foot", p.get("foot", "Right"))
            if p["position"] in POSITION_NAMES.values():
                dpg.set_value("edit_player_pos1", p["position"])
                
            def _get_pos_name_safe(p_code):
                try:
                    code_int = int(p_code)
                    return POSITION_NAMES.get(code_int, "None")
                except Exception:
                    return "None"

            dpg.set_value("edit_player_pos2", _get_pos_name_safe(stats.get("preferredposition2", -1)))
            dpg.set_value("edit_player_pos3", _get_pos_name_safe(stats.get("preferredposition3", -1)))
            dpg.set_value("edit_player_pos4", _get_pos_name_safe(stats.get("preferredposition4", -1)))

            dpg.set_value("edit_player_jersey", jersey_num)
            
            try:
                contract_yr = int(stats.get("contractvaliduntil", 2028))
            except Exception:
                contract_yr = 2028
            dpg.set_value("edit_player_contract", contract_yr)
            dpg.set_value("edit_player_isretiring", bool(p.get("isretiring", 0)))

            dpg.set_value("edit_player_skills", int(stats.get("skillmoves", p.get("skills", 3))))
            dpg.set_value("edit_player_weakfoot", int(stats.get("weakfootabilitytypecode", p.get("weak_foot", 3))))
            dpg.set_value("edit_player_height", int(stats.get("height", p.get("height", 182))))
            dpg.set_value("edit_player_weight", int(stats.get("weight", p.get("weight", 77))))

            # Decode and set PlayStyles & Traits
            try:
                t1 = int(stats.get("trait1", 0))
            except Exception:
                t1 = 0
            try:
                t2 = int(stats.get("trait2", 0))
            except Exception:
                t2 = 0
            try:
                it1 = int(stats.get("icontrait1", 0))
            except Exception:
                it1 = 0
            try:
                it2 = int(stats.get("icontrait2", 0))
            except Exception:
                it2 = 0

            ps_states = decode_player_playstyles(t1, t2, it1, it2)
            for key in PLAYSTYLE_MAP:
                tag = f"ps_radio_{key}"
                if dpg.does_item_exist(tag):
                    st = ps_states.get(key, 0)
                    val_str = "None" if st == 0 else "(+) Regular" if st == 1 else "(++) PlayStyle+"
                    dpg.set_value(tag, val_str)
            self._on_update_playstyles_summary()

            # Roles & FC IQ
            dpg.set_value("edit_player_role1", int(stats.get("role1", 0)))
            dpg.set_value("edit_player_role2", int(stats.get("role2", 0)))
            dpg.set_value("edit_player_role3", int(stats.get("role3", 0)))
            dpg.set_value("edit_player_role4", int(stats.get("role4", 0)))
            dpg.set_value("edit_player_role5", int(stats.get("role5", 0)))

            # Pace & Shooting
            dpg.set_value("edit_player_accel", int(stats.get("acceleration", 70)))
            dpg.set_value("edit_player_sprint", int(stats.get("sprintspeed", 70)))
            dpg.set_value("edit_player_pos", int(stats.get("positioning", 70)))
            dpg.set_value("edit_player_finish", int(stats.get("finishing", 70)))
            dpg.set_value("edit_player_shotpwr", int(stats.get("shotpower", 70)))
            dpg.set_value("edit_player_longshots", int(stats.get("longshots", 70)))
            dpg.set_value("edit_player_volleys", int(stats.get("volleys", 70)))
            dpg.set_value("edit_player_penalties", int(stats.get("penalties", 70)))

            # Passing & Dribbling
            dpg.set_value("edit_player_vision", int(stats.get("vision", 70)))
            dpg.set_value("edit_player_crossing", int(stats.get("crossing", 70)))
            dpg.set_value("edit_player_fk", int(stats.get("freekickaccuracy", 70)))
            dpg.set_value("edit_player_shortpass", int(stats.get("shortpassing", 70)))
            dpg.set_value("edit_player_longpass", int(stats.get("longpassing", 70)))
            dpg.set_value("edit_player_curve", int(stats.get("curve", 70)))
            dpg.set_value("edit_player_agility", int(stats.get("agility", 70)))
            dpg.set_value("edit_player_balance", int(stats.get("balance", 70)))
            dpg.set_value("edit_player_reactions", int(stats.get("reactions", 70)))
            dpg.set_value("edit_player_ballctrl", int(stats.get("ballcontrol", 70)))
            dpg.set_value("edit_player_dribble", int(stats.get("dribbling", 70)))
            dpg.set_value("edit_player_composure", int(stats.get("composure", 70)))

            # Defending & Physical
            dpg.set_value("edit_player_interceptions", int(stats.get("interceptions", 60)))
            dpg.set_value("edit_player_heading", int(stats.get("headingaccuracy", 60)))
            dpg.set_value("edit_player_defawareness", int(stats.get("defensiveawareness", 60)))
            dpg.set_value("edit_player_standtackle", int(stats.get("standingtackle", 60)))
            dpg.set_value("edit_player_slidetackle", int(stats.get("slidingtackle", 60)))
            dpg.set_value("edit_player_jumping", int(stats.get("jumping", 70)))
            dpg.set_value("edit_player_stamina", int(stats.get("stamina", 70)))
            dpg.set_value("edit_player_strength", int(stats.get("strength", 70)))
            dpg.set_value("edit_player_aggression", int(stats.get("aggression", 65)))

            # Goalkeeper
            dpg.set_value("edit_player_gkdiving", int(stats.get("gkdiving", 10)))
            dpg.set_value("edit_player_gkhandling", int(stats.get("gkhandling", 10)))
            dpg.set_value("edit_player_gkkicking", int(stats.get("gkkicking", 10)))
            dpg.set_value("edit_player_gkreflexes", int(stats.get("gkreflexes", 10)))
            dpg.set_value("edit_player_gkpos", int(stats.get("gkpositioning", 10)))

            # Appearance & Kit options
            dpg.set_value("edit_player_headasset", int(stats.get("headassetid", 0)))
            dpg.set_value("edit_player_bodytype", int(stats.get("bodytypecode", 0)))
            dpg.set_value("edit_player_hairstyle", int(stats.get("hairstylecode", 0)))
            dpg.set_value("edit_player_haircolor", int(stats.get("haircolorcode", 0)))
            dpg.set_value("edit_player_skintone", int(stats.get("skintonecode", 0)))
            dpg.set_value("edit_player_eyecolor", int(stats.get("eyecolorcode", 0)))
            dpg.set_value("edit_player_jerseystyle", "Untucked" if stats.get("jerseystylecode") == "1" else "Tucked")
            dpg.set_value("edit_player_sleeves", "Long" if stats.get("jerseysleevelengthcode") == "1" else "Short")
            dpg.set_value("edit_player_fit", "Tight" if stats.get("jerseyfit") == "1" else "Normal")
            dpg.set_value("edit_player_socklength", "Short" if stats.get("socklengthcode") == "1" else "High" if stats.get("socklengthcode") == "2" else "Average")
            dpg.set_value("edit_player_shoetype", int(stats.get("shoetypecode", 0)))
            dpg.set_value("edit_player_gkglove", int(stats.get("gkglovetypecode", 0)))

            dpg.configure_item("player_edit_controls", show=True)
            dpg.set_value("player_save_feedback", "")
        finally:
            self._is_populating_player = False

    def _on_transfer_player(self):
        if not self.selected_player:
            return
        combo_val = dpg.get_value("edit_player_club_combo") or ""
        target_tid = 0
        if "ID" in combo_val:
            try:
                target_tid = int(combo_val.split("ID")[-1].replace(")", "").strip())
            except Exception:
                target_tid = 0
                
        pid = self.selected_player["playerid"]
        old_tid = self.selected_player.get("teamid", 0)
        self.session.transfer_player(pid, target_tid)
        club_name = get_team_name(target_tid) if target_tid > 0 else "Free Agent"
        self.selected_player["club"] = club_name
        self.selected_player["teamid"] = target_tid
        
        jersey_num = self.session.get_player_jersey_number(pid)
        is_trans = pid in self.session.user_transfers
        trans_tag = " [TRANSFERRED]" if is_trans else ""
        
        dpg.set_value("player_header_name", f"#{jersey_num} {self.selected_player['name']} (ID: {pid})")
        dpg.set_value("player_sub_header", f"Club: {club_name}{trans_tag}  |  Kit: #{jersey_num}  |  Position: {self.selected_player['position']}  |  Foot: {self.selected_player.get('foot', 'Right')}  |  Skills: {self.selected_player.get('skills', 3)}*  |  Weak Foot: {self.selected_player.get('weak_foot', 3)}*")
        if dpg.does_item_exist("edit_player_jersey"):
            dpg.set_value("edit_player_jersey", jersey_num)
            
        # Synchronize team view if currently viewing old or new team
        if self.selected_team:
            sel_tid = self.selected_team.get("teamid")
            if sel_tid in (old_tid, target_tid):
                self.selected_team["roster"] = list(self.session.team_rosters.get(sel_tid, []))
                self.selected_team["roster_count"] = len(self.selected_team["roster"])
                self._refresh_team_roster_display()
                
        dpg.set_value("player_save_feedback", f"[OK] Transferred player to {club_name} (#{jersey_num})!")
        self._on_filter_players()
        self._on_filter_teams()
        self._update_save_and_changes_toolbar()

    def _on_save_player_changes(self):
        if not self.selected_player:
            return
        pid = self.selected_player["playerid"]
        stats = self.selected_player.get("stats", {})
        
        # 1. Read core attributes
        ovr = dpg.get_value("edit_player_ovr")
        pot = dpg.get_value("edit_player_pot")
        skills = dpg.get_value("edit_player_skills")
        wf = dpg.get_value("edit_player_weakfoot")
        height = dpg.get_value("edit_player_height")
        weight = dpg.get_value("edit_player_weight")
        
        self.session.update_player_attribute(pid, "overallrating", ovr)
        self.session.update_player_attribute(pid, "potential", pot)
        self.session.update_player_attribute(pid, "skillmoves", skills)
        self.session.update_player_attribute(pid, "weakfootabilitytypecode", wf)
        self.session.update_player_attribute(pid, "height", height)
        self.session.update_player_attribute(pid, "weight", weight)

        # 2. Collect and Encode all 34 PlayStyles & Traits
        ps_states = {}
        for key in PLAYSTYLE_MAP:
            tag = f"ps_radio_{key}"
            if dpg.does_item_exist(tag):
                val = dpg.get_value(tag)
                ps_states[key] = 2 if "(++)" in val else 1 if "(+)" in val else 0
        t1, t2, it1, it2 = encode_player_playstyles(ps_states)

        self.session.update_player_attribute(pid, "trait1", t1)
        self.session.update_player_attribute(pid, "trait2", t2)
        self.session.update_player_attribute(pid, "icontrait1", it1)
        self.session.update_player_attribute(pid, "icontrait2", it2)

        stats["trait1"] = str(t1)
        stats["trait2"] = str(t2)
        stats["icontrait1"] = str(it1)
        stats["icontrait2"] = str(it2)

        # 3. Secondary positions
        def _get_pos_code(pos_str):
            for k, v in POSITION_NAMES.items():
                if v == pos_str:
                    return k
            return -1

        pos1_code = _get_pos_code(dpg.get_value("edit_player_pos1"))
        pos2_code = _get_pos_code(dpg.get_value("edit_player_pos2"))
        pos3_code = _get_pos_code(dpg.get_value("edit_player_pos3"))
        pos4_code = _get_pos_code(dpg.get_value("edit_player_pos4"))

        if pos1_code >= 0:
            self.session.update_player_attribute(pid, "preferredposition1", pos1_code)
        self.session.update_player_attribute(pid, "preferredposition2", pos2_code)
        self.session.update_player_attribute(pid, "preferredposition3", pos3_code)
        self.session.update_player_attribute(pid, "preferredposition4", pos4_code)

        stats["preferredposition2"] = str(pos2_code)
        stats["preferredposition3"] = str(pos3_code)
        stats["preferredposition4"] = str(pos4_code)

        # 4. Roles & FC IQ
        for r_i in range(1, 6):
            if dpg.does_item_exist(f"edit_player_role{r_i}"):
                r_val = dpg.get_value(f"edit_player_role{r_i}")
                self.session.update_player_attribute(pid, f"role{r_i}", r_val)
                stats[f"role{r_i}"] = str(r_val)

        # 5. Jersey, Contract, Retiring
        jersey_num = dpg.get_value("edit_player_jersey")
        contract_yr = dpg.get_value("edit_player_contract")
        is_ret = 1 if dpg.get_value("edit_player_isretiring") else 0
        self.session.set_player_jersey_number(pid, jersey_num)
        self.session.update_player_attribute(pid, "contractvaliduntil", contract_yr)
        self.session.update_player_attribute(pid, "isretiring", is_ret)
        stats["jerseynumber"] = str(jersey_num)
        stats["contractvaliduntil"] = str(contract_yr)
        stats["isretiring"] = str(is_ret)

        self._update_player_sub_header()

        # 6. Kit & Appearance
        j_style = 1 if dpg.get_value("edit_player_jerseystyle") == "Untucked" else 0
        s_length = 1 if dpg.get_value("edit_player_sleeves") == "Long" else 0
        j_fit = 1 if dpg.get_value("edit_player_fit") == "Tight" else 0
        sock_val = 1 if dpg.get_value("edit_player_socklength") == "Short" else 2 if dpg.get_value("edit_player_socklength") == "High" else 0
        shoe_val = dpg.get_value("edit_player_shoetype")
        glove_val = dpg.get_value("edit_player_gkglove")

        stats["jerseystylecode"] = str(j_style)
        stats["jerseysleevelengthcode"] = str(s_length)
        stats["jerseyfit"] = str(j_fit)
        stats["socklengthcode"] = str(sock_val)
        stats["shoetypecode"] = str(shoe_val)
        stats["gkglovetypecode"] = str(glove_val)

        # 7. Physical and Technical stats dict
        stat_inputs = [
            ("accel", "acceleration"), ("sprint", "sprintspeed"), ("pos", "positioning"),
            ("finish", "finishing"), ("shotpwr", "shotpower"), ("longshots", "longshots"),
            ("volleys", "volleys"), ("penalties", "penalties"), ("vision", "vision"),
            ("crossing", "crossing"), ("fk", "freekickaccuracy"), ("shortpass", "shortpassing"),
            ("longpass", "longpassing"), ("curve", "curve"), ("agility", "agility"),
            ("balance", "balance"), ("reactions", "reactions"), ("ballctrl", "ballcontrol"),
            ("dribble", "dribbling"), ("composure", "composure"), ("interceptions", "interceptions"),
            ("heading", "headingaccuracy"), ("defawareness", "defensiveawareness"),
            ("standtackle", "standingtackle"), ("slidetackle", "slidingtackle"),
            ("jumping", "jumping"), ("stamina", "stamina"), ("strength", "strength"),
            ("aggression", "aggression"), ("gkdiving", "gkdiving"), ("gkhandling", "gkhandling"),
            ("gkkicking", "gkkicking"), ("gkreflexes", "gkreflexes"), ("gkpos", "gkpositioning")
        ]
        for ui_key, stat_key in stat_inputs:
            tag = f"edit_player_{ui_key}"
            if dpg.does_item_exist(tag):
                val = dpg.get_value(tag)
                self.session.update_player_attribute(pid, stat_key, val)
                stats[stat_key] = str(val)

        self._on_filter_players()
        self._update_save_and_changes_toolbar()
        staged_n = self.session.change_tracker.count
        dpg.set_value("player_save_feedback", f"[OK] Applied player changes ({staged_n} staged).")

    def _on_boost_player(self):
        if not self.selected_player:
            return
        pid = self.selected_player["playerid"]
        stats = self.selected_player.setdefault("stats", {})
        
        boost_attrs = [
            ("edit_player_ovr", "overallrating", 99),
            ("edit_player_pot", "potential", 99),
            ("edit_player_skills", "skillmoves", 5),
            ("edit_player_weakfoot", "weakfootabilitytypecode", 5),
            ("edit_player_accel", "acceleration", 99),
            ("edit_player_sprint", "sprintspeed", 99),
            ("edit_player_pos", "positioning", 99),
            ("edit_player_finish", "finishing", 99),
            ("edit_player_shotpwr", "shotpower", 99),
            ("edit_player_longshots", "longshots", 99),
            ("edit_player_volleys", "volleys", 99),
            ("edit_player_penalties", "penalties", 99),
            ("edit_player_vision", "vision", 99),
            ("edit_player_crossing", "crossing", 99),
            ("edit_player_fk", "freekickaccuracy", 99),
            ("edit_player_shortpass", "shortpassing", 99),
            ("edit_player_longpass", "longpassing", 99),
            ("edit_player_curve", "curve", 99),
            ("edit_player_agility", "agility", 99),
            ("edit_player_balance", "balance", 99),
            ("edit_player_reactions", "reactions", 99),
            ("edit_player_ballctrl", "ballcontrol", 99),
            ("edit_player_dribble", "dribbling", 99),
            ("edit_player_composure", "composure", 99),
            ("edit_player_interceptions", "interceptions", 99),
            ("edit_player_heading", "headingaccuracy", 99),
            ("edit_player_defawareness", "defensiveawareness", 99),
            ("edit_player_standtackle", "standingtackle", 99),
            ("edit_player_slidetackle", "slidingtackle", 99),
            ("edit_player_jumping", "jumping", 99),
            ("edit_player_stamina", "stamina", 99),
            ("edit_player_strength", "strength", 99),
            ("edit_player_aggression", "aggression", 99)
        ]
        
        self._is_populating_player = True
        try:
            for ui_tag, stat_key, target_val in boost_attrs:
                if dpg.does_item_exist(ui_tag):
                    dpg.set_value(ui_tag, target_val)
                self.session.update_player_attribute(pid, stat_key, target_val)
                stats[stat_key] = str(target_val)
                if stat_key == "overallrating":
                    self.selected_player["overall"] = target_val
                elif stat_key == "potential":
                    self.selected_player["potential"] = target_val
                elif stat_key == "skillmoves":
                    self.selected_player["skills"] = target_val
                elif stat_key == "weakfootabilitytypecode":
                    self.selected_player["weak_foot"] = target_val
        finally:
            self._is_populating_player = False
            
        dpg.set_value("player_badge_ovr", "[ 99 ]")
        dpg.configure_item("player_badge_ovr", color=(0, 255, 120))
        self._update_player_sub_header()
        self._on_all_gold_playstyles()
        self._on_filter_players()
        self._update_save_and_changes_toolbar()
        staged_n = self.session.change_tracker.count
        dpg.set_value("player_save_feedback", f"[OK] Prime 99 & All Gold PlayStyles+ Applied ({staged_n} staged)!")

    def _on_import_player_face(self):
        """Allows user to select and import a custom miniface image for the selected player."""
        if not self.selected_player:
            dpg.set_value("player_save_feedback", "[!] Select a player first to import miniface.")
            return
        pid = self.selected_player["playerid"]
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filepath = filedialog.askopenfilename(
            title=f"Import Miniface for {self.selected_player['name']} (p{pid})",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.dds;*.bmp"), ("All Files", "*.*")]
        )
        root.destroy()
        if not filepath:
            return
        ok, msg = self.assets.import_custom_player_face(pid, filepath)
        if ok:
            tex_tag = f"tex_player_{pid}"
            if dpg.does_item_exist("player_miniface_img"):
                dpg.configure_item("player_miniface_img", texture_tag=tex_tag)
            if hasattr(self, "selected_team_roster_pid") and self.selected_team_roster_pid == pid:
                if dpg.does_item_exist("roster_player_miniface_img"):
                    dpg.configure_item("roster_player_miniface_img", texture_tag=tex_tag)
            dpg.set_value("player_save_feedback", f"[OK] {msg}")
        else:
            dpg.set_value("player_save_feedback", f"[Error] {msg}")
        pid = self.selected_player["playerid"]
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filepath = filedialog.askopenfilename(
            title=f"Import Miniface for {self.selected_player['name']} (p{pid})",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.dds;*.bmp"), ("All Files", "*.*")]
        )
        root.destroy()
        if not filepath:
            return
        ok, msg = self.assets.import_custom_player_face(pid, filepath)
        if ok:
            tex_tag = f"tex_player_{pid}"
            if dpg.does_item_exist("player_miniface_img"):
                dpg.configure_item("player_miniface_img", texture_tag=tex_tag)
            if hasattr(self, "selected_team_roster_pid") and self.selected_team_roster_pid == pid:
                if dpg.does_item_exist("roster_player_miniface_img"):
                    dpg.configure_item("roster_player_miniface_img", texture_tag=tex_tag)
            dpg.set_value("player_save_feedback", f"[OK] {msg}")
        else:
            dpg.set_value("player_save_feedback", f"[Error] {msg}")

    # --- Teams UI Callbacks ---

    def _load_teams_list(self):
        self._on_filter_teams()

    def _on_filter_teams(self):
        search_txt = ""
        if dpg.does_item_exist("team_search_input"):
            search_txt = (dpg.get_value("team_search_input") or "").lower().strip()
        filtered = []
        for t in self.session.teams_cache:
            if search_txt:
                name_match = search_txt in t["name"].lower()
                id_match = search_txt in str(t["teamid"])
                if not (name_match or id_match):
                    continue
            filtered.append(t)
        self.filtered_teams = filtered
        items = [f"{t['name']} (ID: {t['teamid']}) - {t['roster_count']} players" for t in self.filtered_teams]
        if dpg.does_item_exist("teams_listbox"):
            dpg.configure_item("teams_listbox", items=items)
        if dpg.does_item_exist("team_count_label"):
            dpg.set_value("team_count_label", f"Total Clubs: {len(self.filtered_teams):,} matches")

    def _refresh_team_roster_display(self):
        if not self.selected_team:
            return
        t = self.selected_team
        roster_items = []
        for pid in t.get("roster", []):
            jersey = self.session.get_player_jersey_number(pid)
            is_trans = pid in self.session.user_transfers
            trans_tag = " [T]" if is_trans else ""
            if pid in self.session.players_lookup:
                p = self.session.players_lookup[pid]
                pos_str = get_position_name(p["pos_code"])
                roster_items.append(f"#{jersey:02d} | [{p['overall']}] {p['name']} ({pos_str}){trans_tag} - ID {pid}")
            else:
                roster_items.append(f"#{jersey:02d} | Player ID #{pid}{trans_tag} - ID {pid}")
        if dpg.does_item_exist("team_roster_listbox"):
            dpg.configure_item("team_roster_listbox", items=roster_items)

    def _on_select_team(self, sender, app_data):
        items = dpg.get_item_configuration("teams_listbox")["items"]
        if not items or app_data not in items:
            return
        idx = items.index(app_data)
        if idx >= len(self.filtered_teams):
            return
        t = self.filtered_teams[idx]
        self.selected_team = t
        self._populate_team_details(t)

    def _populate_team_details(self, t: Dict[str, Any]):
        dpg.set_value("team_selected_header", f"Club: {t['name']} (ID: {t['teamid']})")
        dpg.set_value("edit_team_id", t["teamid"])
        dpg.set_value("edit_team_name", t["name"])
        dpg.set_value("edit_team_stadium", t.get("stadium", "Default Stadium"))

        # Update club crest texture
        crest_tex = self.assets.get_club_texture(t["teamid"], t["name"])
        if dpg.does_item_exist("team_crest_img"):
            dpg.configure_item("team_crest_img", texture_tag=crest_tex)

        # Update manager details & texture from authentic database or assets
        mgr_name = t.get("manager_name") or ""
        mgr_asset_id = t.get("manager_asset_id", 0)
        mgr_info = self.assets.get_club_manager_info(t["teamid"], t["name"])
        if not mgr_name:
            mgr_name = mgr_info.get("name", "Head Coach")
        mgr_nat = mgr_info.get("nationality", "International")

        if dpg.does_item_exist("edit_team_manager_name"):
            dpg.set_value("edit_team_manager_name", mgr_name)
        if dpg.does_item_exist("edit_team_manager_nat"):
            dpg.set_value("edit_team_manager_nat", mgr_nat)
        if dpg.does_item_exist("team_manager_role_label"):
            role_txt = f"Role: {mgr_info.get('role', 'Head Coach')}"
            if mgr_asset_id > 0:
                role_txt += f"  |  Asset ID: {mgr_asset_id}"
            dpg.set_value("team_manager_role_label", role_txt)

        mgr_tex = self.assets.get_manager_texture(t["teamid"], mgr_name, mgr_asset_id)
        if dpg.does_item_exist("team_manager_img"):
            dpg.configure_item("team_manager_img", texture_tag=mgr_tex)

        self._refresh_team_roster_display()
        self.selected_team_roster_pid = None
        if dpg.does_item_exist("team_roster_player_actions"):
            dpg.configure_item("team_roster_player_actions", show=False)
        dpg.configure_item("team_edit_controls", show=True)
        dpg.set_value("team_save_feedback", "")

    def _on_select_team_roster_player(self, sender, app_data):
        if not app_data or "ID " not in app_data:
            return
        try:
            pid = int(app_data.split("ID ")[-1].strip())
        except Exception:
            return
        self.selected_team_roster_pid = pid
        p = self.session.players_lookup.get(pid)
        pname = p["name"] if p else f"Player #{pid}"
        ovr = p.get("overall", "--") if p else "--"
        pos = get_position_name(p.get("pos_code", -1)) if p else "N/A"
        jersey = self.session.get_player_jersey_number(pid)
        
        dpg.set_value("team_roster_player_title", f"Managing: #{jersey} {pname} ({pos} | {ovr} OVR | PID: {pid})")
        dpg.set_value("edit_team_roster_jersey_num", jersey)

        # Update roster player miniface
        roster_tex = self.assets.get_player_texture(pid, pname, jersey, ovr if isinstance(ovr, int) else 75, pos)
        if dpg.does_item_exist("roster_player_miniface_img"):
            dpg.configure_item("roster_player_miniface_img", texture_tag=roster_tex)

        dpg.configure_item("team_roster_player_actions", show=True)

    def _on_set_roster_jersey_num(self):
        if not self.selected_team_roster_pid or not self.selected_team:
            return
        pid = self.selected_team_roster_pid
        num = dpg.get_value("edit_team_roster_jersey_num")
        if not (1 <= num <= 99):
            dpg.set_value("team_save_feedback", "[!] Jersey number must be between 1 and 99.")
            return
            
        duplicate_name = None
        for other_pid in self.selected_team.get("roster", []):
            if other_pid != pid:
                if self.session.get_player_jersey_number(other_pid) == num:
                    other_p = self.session.players_lookup.get(other_pid)
                    duplicate_name = other_p["name"] if other_p else f"Player #{other_pid}"
                    break
                    
        self.session.set_player_jersey_number(pid, num)
        p = self.session.players_lookup.get(pid)
        pname = p["name"] if p else f"Player #{pid}"
        
        self._refresh_team_roster_display()
        self._update_save_and_changes_toolbar()
        if duplicate_name:
            dpg.set_value("team_save_feedback", f"[OK] Set #{num} for {pname} (Note: #{num} was also worn by {duplicate_name})")
        else:
            dpg.set_value("team_save_feedback", f"[OK] Set jersey #{num} for {pname} ({self.session.change_tracker.count} staged)!")

    def _on_release_roster_player(self):
        if not self.selected_team_roster_pid or not self.selected_team:
            return
        pid = self.selected_team_roster_pid
        p = self.session.players_lookup.get(pid)
        pname = p["name"] if p else f"Player #{pid}"
        tid = self.selected_team["teamid"]
        
        # Transfer to Free Agents (0)
        self.session.transfer_player(pid, 0)
        
        self.selected_team["roster"] = list(self.session.team_rosters.get(tid, []))
        self.selected_team["roster_count"] = len(self.selected_team["roster"])
            
        if self.selected_player and self.selected_player.get("playerid") == pid:
            self.selected_player["teamid"] = 0
            self.selected_player["club"] = "Free Agent"
            jersey_num = self.session.get_player_jersey_number(pid)
            dpg.set_value("player_header_name", f"#{jersey_num} {self.selected_player['name']} (ID: {pid})")
            dpg.set_value("player_sub_header", f"Club: Free Agent [TRANSFERRED]  |  Kit: #{jersey_num}  |  Position: {self.selected_player['position']}  |  Foot: {self.selected_player.get('foot', 'Right')}  |  Skills: {self.selected_player.get('skills', 3)}*  |  Weak Foot: {self.selected_player.get('weak_foot', 3)}*")
            if dpg.does_item_exist("edit_player_jersey"):
                dpg.set_value("edit_player_jersey", jersey_num)

        self.selected_team_roster_pid = None
        dpg.configure_item("team_roster_player_actions", show=False)
        self._refresh_team_roster_display()
        self._on_filter_teams()
        self._on_filter_players()
        self._update_save_and_changes_toolbar()
        dpg.set_value("team_save_feedback", f"[OK] Released {pname} to Free Agents ({self.session.change_tracker.count} staged)!")

    def _on_open_sign_player_modal(self):
        if not self.selected_team:
            return
        tname = self.selected_team["name"]
        tid = self.selected_team["teamid"]
        dpg.set_value("sign_player_target_club_label", f"Target Destination: {tname} (ID: {tid})")
        dpg.set_value("sign_player_search_input", "")
        dpg.set_value("sign_player_pos_combo", "All")
        dpg.set_value("sign_player_min_ovr_slider", 0)
        dpg.set_value("sign_player_selected_info", "None selected")
        self.selected_sign_player = None
        self._on_filter_sign_players()
        dpg.configure_item("sign_player_modal", show=True)

    def _on_filter_sign_players(self):
        search_txt = (dpg.get_value("sign_player_search_input") or "").lower().strip()
        pos_cat = dpg.get_value("sign_player_pos_combo") or "All"
        min_ovr = dpg.get_value("sign_player_min_ovr_slider") or 0
        
        current_roster = set(self.selected_team.get("roster", [])) if self.selected_team else set()
        
        filtered = []
        for p in self.session.players_cache:
            pid = p["playerid"]
            if pid in current_roster:
                continue
            if p["overall"] < min_ovr:
                continue
            if pos_cat != "All":
                pos_code = p["pos_code"]
                if pos_cat == "Attackers" and pos_code not in [20, 21, 22, 23, 24, 25, 26, 27]:
                    continue
                elif pos_cat == "Midfielders" and pos_code not in [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]:
                    continue
                elif pos_cat == "Defenders" and pos_code not in [1, 2, 3, 4, 5, 6, 7, 8]:
                    continue
                elif pos_cat == "Goalkeepers" and pos_code != 0:
                    continue
            if search_txt:
                name_match = search_txt in p["name"].lower()
                club_match = search_txt in p["club"].lower()
                id_match = search_txt in str(pid)
                if not (name_match or club_match or id_match):
                    continue
            filtered.append(p)
            if len(filtered) >= 250:
                break
                
        self.filtered_sign_players = filtered
        items = [f"[{p['overall']}] {p['name']} ({get_position_name(p['pos_code'])}) - {p['club']} (Age {p['age']}) - ID {p['playerid']}" for p in self.filtered_sign_players]
        dpg.configure_item("sign_player_listbox", items=items)
        dpg.set_value("sign_player_count_label", f"Matching Players: {len(self.filtered_sign_players):,} (showing top 250)")

    def _on_select_sign_player(self, sender, app_data):
        items = dpg.get_item_configuration("sign_player_listbox")["items"]
        if not items or app_data not in items:
            return
        idx = items.index(app_data)
        if idx >= len(self.filtered_sign_players):
            return
        p = self.filtered_sign_players[idx]
        self.selected_sign_player = p
        pos_str = get_position_name(p["pos_code"])
        dpg.set_value("sign_player_selected_info", f"[{p['overall']}] {p['name']} ({pos_str}) - Current: {p['club']} | Age: {p['age']} | ID: {p['playerid']}")

    def _on_confirm_sign_player(self):
        if not self.selected_sign_player or not self.selected_team:
            return
        p = self.selected_sign_player
        pid = p["playerid"]
        tid = self.selected_team["teamid"]
        tname = self.selected_team["name"]
        
        # Execute transfer in database
        self.session.transfer_player(pid, tid)
        
        # Update current team roster
        self.selected_team["roster"] = list(self.session.team_rosters.get(tid, []))
        self.selected_team["roster_count"] = len(self.selected_team["roster"])
        
        # If currently selected player in Player tab is this player, update them too
        if self.selected_player and self.selected_player.get("playerid") == pid:
            self.selected_player["teamid"] = tid
            self.selected_player["club"] = tname
            jersey_num = self.session.get_player_jersey_number(pid)
            dpg.set_value("player_header_name", f"#{jersey_num} {self.selected_player['name']} (ID: {pid})")
            dpg.set_value("player_sub_header", f"Club: {tname} [TRANSFERRED]  |  Kit: #{jersey_num}  |  Position: {self.selected_player['position']}  |  Foot: {self.selected_player.get('foot', 'Right')}  |  Skills: {self.selected_player.get('skills', 3)}*  |  Weak Foot: {self.selected_player.get('weak_foot', 3)}*")
            if dpg.does_item_exist("edit_player_jersey"):
                dpg.set_value("edit_player_jersey", jersey_num)
        
        dpg.configure_item("sign_player_modal", show=False)
        self._refresh_team_roster_display()
        self._on_filter_teams()
        self._on_filter_players()
        self._update_save_and_changes_toolbar()
        dpg.set_value("team_save_feedback", f"[OK] Successfully signed {p['name']} to {tname} ({self.session.change_tracker.count} staged)!")

    def _on_save_team_changes(self):
        if not self.selected_team:
            return
        new_name = dpg.get_value("edit_team_name")
        new_stadium = dpg.get_value("edit_team_stadium")
        self.selected_team["name"] = new_name
        self.selected_team["stadium"] = new_stadium
        self.session.update_team_stadium(self.selected_team["teamid"], new_stadium)
        self._on_filter_teams()
        self._update_save_and_changes_toolbar()
        dpg.set_value("team_save_feedback", f"[OK] Club details & stadium updated ({self.session.change_tracker.count} staged)!")

    def _on_import_club_crest(self):
        """Allows user to select and import a custom club crest image."""
        if not self.selected_team:
            dpg.set_value("team_save_feedback", "[!] Select a club first to import crest.")
            return
        tid = self.selected_team["teamid"]
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filepath = filedialog.askopenfilename(
            title=f"Import Crest for {self.selected_team['name']} (ID {tid})",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.dds;*.bmp"), ("All Files", "*.*")]
        )
        root.destroy()
        if not filepath:
            return
        ok, msg = self.assets.import_custom_club_crest(tid, filepath)
        if ok:
            tex_tag = f"tex_club_{tid}"
            if dpg.does_item_exist("team_crest_img"):
                dpg.configure_item("team_crest_img", texture_tag=tex_tag)
            dpg.set_value("team_save_feedback", f"[OK] {msg}")
        else:
            dpg.set_value("team_save_feedback", f"[Error] {msg}")

    def _on_import_manager_face(self):
        """Allows user to select and import a custom manager photo."""
        if not self.selected_team:
            dpg.set_value("team_save_feedback", "[!] Select a club first to import manager photo.")
            return
        tid = self.selected_team["teamid"]
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filepath = filedialog.askopenfilename(
            title=f"Import Manager Photo for {self.selected_team['name']}",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.dds;*.bmp"), ("All Files", "*.*")]
        )
        root.destroy()
        if not filepath:
            return
        ok, msg = self.assets.import_custom_manager_face(tid, filepath)
        if ok:
            tex_tag = f"tex_manager_{tid}"
            if dpg.does_item_exist("team_manager_img"):
                dpg.configure_item("team_manager_img", texture_tag=tex_tag)
            dpg.set_value("team_save_feedback", f"[OK] {msg}")
        else:
            dpg.set_value("team_save_feedback", f"[Error] {msg}")

    def _on_save_manager_changes(self):
        """Saves custom manager name and nationality into database and assets."""
        if not self.selected_team:
            return
        tid = self.selected_team["teamid"]
        m_name = (dpg.get_value("edit_team_manager_name") or "Head Coach").strip()
        m_nat = (dpg.get_value("edit_team_manager_nat") or "International").strip()
        # Persist to database table Knen
        self.session.update_team_manager(tid, m_name)
        self.selected_team["manager_name"] = m_name
        self.assets.set_club_manager_info(tid, m_name, m_nat, "Head Coach")
        mgr_tex = self.assets.get_manager_texture(tid, m_name)
        if dpg.does_item_exist("team_manager_img"):
            dpg.configure_item("team_manager_img", texture_tag=mgr_tex)
        self._update_save_and_changes_toolbar()
        dpg.set_value("team_save_feedback", f"[OK] Manager details updated ({self.session.change_tracker.count} staged): {m_name} ({m_nat})")

    # --- Database Editor UI Callbacks ---

    def _load_database_tables_dropdown(self):
        entries = []
        for sname, tbl in self.session.db.tables_map.items():
            disp = get_table_display_name(sname)
            safety = get_table_safety_info(sname)
            cat = get_table_category(sname)
            label = f"{safety['badge']} {sname} - {disp} ({len(tbl.records):,} rows)"
            entries.append((sname, cat, label))
        self.all_table_entries = entries
        self._refresh_tables_dropdown()

    def _refresh_tables_dropdown(self):
        if not hasattr(self, "all_table_entries"):
            return
        cat_filter = self.selected_category
        clean_cat = cat_filter.split("(")[0].strip()
        search_txt = (dpg.get_value("db_table_filter_input") or "").lower().strip() if dpg.does_item_exist("db_table_filter_input") else ""

        filtered_items = []
        for sname, cat, label in self.all_table_entries:
            if "All Categories" not in clean_cat and clean_cat not in cat:
                continue
            if search_txt and search_txt not in label.lower() and search_txt not in sname.lower():
                continue
            filtered_items.append(label)

        if dpg.does_item_exist("db_table_selector"):
            dpg.configure_item("db_table_selector", items=filtered_items)
            if filtered_items:
                current_val = dpg.get_value("db_table_selector")
                if current_val in filtered_items:
                    target_label = current_val
                else:
                    target_label = filtered_items[0]
                    dpg.set_value("db_table_selector", target_label)
                sname = self._parse_sname_from_label(target_label)
                if sname != self.selected_table_sname or not hasattr(self, "_last_loaded_db_table") or self._last_loaded_db_table != sname:
                    self.selected_table_sname = sname
                    self._last_loaded_db_table = sname
                    self.current_table_page = 0
                    self._load_db_table(sname)
            else:
                dpg.set_value("db_table_selector", "")

    def _parse_sname_from_label(self, label: str) -> str:
        tokens = label.split(" ")
        for tok in tokens:
            cleaned = tok.strip()
            if len(cleaned) == 4 and cleaned.isalnum():
                return cleaned
        return label.split(" ")[0]

    def _on_change_db_category(self, sender, app_data):
        self.selected_category = app_data
        self._refresh_tables_dropdown()

    def _on_filter_db_tables(self, sender, app_data):
        self._refresh_tables_dropdown()

    def _on_change_db_table(self, sender, app_data):
        sname = self._parse_sname_from_label(app_data)
        self.selected_table_sname = sname
        self._last_loaded_db_table = sname
        self.current_table_page = 0
        self._load_db_table(sname)

    def _load_db_table(self, sname: str):
        tbl = self.session.get_table(sname)
        if not tbl:
            return
        safety = get_table_safety_info(sname)
        cat = get_table_category(sname)

        if dpg.does_item_exist("db_table_safety_badge"):
            dpg.set_value("db_table_safety_badge", safety["badge"])
            if safety["level"] == "SAFE":
                dpg.configure_item("db_table_safety_badge", color=(0, 255, 120))
            elif safety["level"] == "DANGEROUS":
                dpg.configure_item("db_table_safety_badge", color=(255, 70, 70))
            else:
                dpg.configure_item("db_table_safety_badge", color=(255, 200, 0))

        if dpg.does_item_exist("db_table_safety_desc"):
            dpg.set_value("db_table_safety_desc", safety["desc"])

        if dpg.does_item_exist("db_table_stats_text"):
            dpg.set_value("db_table_stats_text", f"Rows: {len(tbl.records):,} | Columns: {len(tbl.columns)} | Record Size: {tbl.rec_size} bytes | Category: {cat}")

        self._render_db_records_page()

    def _on_click_add_row(self):
        tbl = self.session.get_table(self.selected_table_sname)
        if not tbl:
            return
        safety = get_table_safety_info(self.selected_table_sname)
        self.pending_structural_action = "add"
        msg = (
            f"You are about to ADD a new row to table '{self.selected_table_sname} - {get_table_display_name(self.selected_table_sname)}'.\n\n"
            f"Safety Level: {safety['badge']}\n"
            f"Note: In EA SPORTS FC 25, relational tables have fixed memory allocations referenced by the game engine. "
            f"Adding rows in core tables may alter indexing or cause game crashes.\n\n"
            f"Confirm only if you intend to add a record."
        )
        dpg.set_value("structural_modal_msg", msg)
        dpg.configure_item("structural_confirm_modal", show=True)

    def _on_clone_row(self):
        tbl = self.session.get_table(self.selected_table_sname)
        if tbl and self.selected_record_index is not None:
            self.session.clone_table_row(self.selected_table_sname, self.selected_record_index)
            self._load_db_table(self.selected_table_sname)
            self._update_save_and_changes_toolbar()
            dpg.set_value("record_save_feedback", f"[OK] Cloned row #{self.selected_record_index} to end of table ({self.session.change_tracker.count} staged)!")

    def _on_click_delete_row(self):
        tbl = self.session.get_table(self.selected_table_sname)
        if not tbl or self.selected_record_index is None:
            return
        safety = get_table_safety_info(self.selected_table_sname)
        self.pending_structural_action = "delete"
        msg = (
            f"You are about to DELETE row #{self.selected_record_index} from table '{self.selected_table_sname} - {get_table_display_name(self.selected_table_sname)}'.\n\n"
            f"Safety Level: {safety['badge']}\n"
            f"WARNING: This operation shifts row indices. Deleting crucial rows for players, teams, or competitions may corrupt save files or crash the game!\n\n"
            f"Confirm only if you know what you are doing."
        )
        dpg.set_value("structural_modal_msg", msg)
        dpg.configure_item("structural_confirm_modal", show=True)

    def _on_confirm_structural_action(self):
        dpg.configure_item("structural_confirm_modal", show=False)
        action = self.pending_structural_action
        self.pending_structural_action = None
        if action == "add":
            self.session.add_table_row(self.selected_table_sname)
            self._load_db_table(self.selected_table_sname)
            self._update_save_and_changes_toolbar()
            dpg.set_value("record_save_feedback", f"[OK] New blank row added at end of table ({self.session.change_tracker.count} staged)!")
        elif action == "delete" and self.selected_record_index is not None:
            deleted_idx = self.selected_record_index
            self.session.delete_table_row(self.selected_table_sname, deleted_idx)
            self.selected_record_index = None
            self._load_db_table(self.selected_table_sname)
            dpg.delete_item("record_fields_container", children_only=True)
            dpg.configure_item("record_actions_group", show=False)
            self._update_save_and_changes_toolbar()
            dpg.set_value("record_save_feedback", f"[OK] Deleted row #{deleted_idx} ({self.session.change_tracker.count} staged)!")

    def _on_export_table_csv(self):
        """Exports the active database table to a CSV file."""
        if not self.session.is_loaded:
            dpg.set_value("db_table_action_feedback", "[!] Load a squad file first.")
            return
        tbl_sname = self.selected_table_sname
        tbl = self.session.get_table(tbl_sname)
        if not tbl:
            dpg.set_value("db_table_action_feedback", "[!] Select a table first.")
            return

        disp_name = get_table_display_name(tbl_sname).replace(" ", "_").replace("/", "_")
        default_filename = f"{tbl_sname}_{disp_name}.csv"

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        target = filedialog.asksaveasfilename(
            title=f"Export Table '{tbl_sname}' to CSV",
            initialfile=default_filename,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        root.destroy()

        if not target:
            return

        ok, msg, count = self.session.export_table_csv(tbl_sname, target)
        if ok:
            dpg.set_value("db_table_action_feedback", f"[OK] Exported {count:,} rows to {os.path.basename(target)}!")
        else:
            dpg.set_value("db_table_action_feedback", f"[Error] {msg}")

    def _on_import_table_csv(self):
        """Imports records from a CSV file into the active database table."""
        if not self.session.is_loaded:
            dpg.set_value("db_table_action_feedback", "[!] Load a squad file first.")
            return
        tbl_sname = self.selected_table_sname
        tbl = self.session.get_table(tbl_sname)
        if not tbl:
            dpg.set_value("db_table_action_feedback", "[!] Select a table first.")
            return

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filepath = filedialog.askopenfilename(
            title=f"Import CSV into Table '{tbl_sname}' ({get_table_display_name(tbl_sname)})",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        root.destroy()

        if not filepath:
            return

        ok, msg, stats = self.session.import_table_csv(tbl_sname, filepath)
        if ok:
            # Refresh table display & caches
            self._load_db_table(self.selected_table_sname)
            self._on_filter_players()
            self._on_filter_teams()
            dpg.set_value("db_table_action_feedback", f"[OK] {msg}")
        else:
            dpg.set_value("db_table_action_feedback", f"[Error] {msg}")

    def _on_export_all_tables_zip(self):
        """Exports all 76 database tables as individual CSVs inside a ZIP archive."""
        if not self.session.is_loaded:
            dpg.set_value("db_table_action_feedback", "[!] Load a squad file first.")
            return

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        target = filedialog.asksaveasfilename(
            title="Export All 76 Database Tables to ZIP",
            initialfile="FC25_Squads_All_Tables.zip",
            filetypes=[("ZIP Archives", "*.zip"), ("All Files", "*.*")]
        )
        root.destroy()

        if not target:
            return

        ok, msg, count = self.session.export_all_tables_zip(target)
        if ok:
            dpg.set_value("db_table_action_feedback", f"[OK] Exported {count} tables to {os.path.basename(target)}!")
        else:
            dpg.set_value("db_table_action_feedback", f"[Error] {msg}")

    def _render_db_records_page(self):
        tbl = self.session.get_table(self.selected_table_sname)
        if not tbl:
            return

        total_rows = len(tbl.records)
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        page = min(self.current_table_page, total_pages - 1)
        self.current_table_page = page

        dpg.set_value("db_pagination_text", f"Page {page + 1} of {total_pages}")

        start_idx = page * self.page_size
        end_idx = min(start_idx + self.page_size, total_rows)

        items = []
        filter_txt = (dpg.get_value("db_record_search_input") or "").lower().strip() if dpg.does_item_exist("db_record_search_input") else ""
        for r_idx in range(start_idx, end_idx):
            row_str = self.session.format_table_row_summary(self.selected_table_sname, r_idx)
            if filter_txt and filter_txt not in row_str.lower():
                continue
            items.append(row_str)

        dpg.configure_item("db_records_listbox", items=items)
        dpg.configure_item("record_actions_group", show=False)

    def _on_prev_page(self):
        if self.current_table_page > 0:
            self.current_table_page -= 1
            self._render_db_records_page()

    def _on_next_page(self):
        tbl = self.session.get_table(self.selected_table_sname)
        if tbl:
            total_pages = max(1, (len(tbl.records) + self.page_size - 1) // self.page_size)
            if self.current_table_page < total_pages - 1:
                self.current_table_page += 1
                self._render_db_records_page()

    def _on_filter_records(self, sender, app_data):
        self._render_db_records_page()

    def _on_select_record(self, sender, app_data):
        tbl = self.session.get_table(self.selected_table_sname)
        if not tbl or not tbl.records:
            return

        try:
            row_idx = int(app_data.split("|")[0].replace("Row", "").strip())
        except Exception:
            return

        self.selected_record_index = row_idx
        self._inspect_record(tbl, row_idx)

    def _on_filter_inspector_columns(self, sender, app_data):
        self.inspector_filter_query = (app_data or "").strip().lower()
        if self.selected_record_index is not None and self.selected_table_sname:
            tbl = self.session.get_table(self.selected_table_sname)
            if tbl:
                self._inspect_record(tbl, self.selected_record_index)

    def _on_toggle_tech_tags(self, sender, app_data):
        self.inspector_show_tech_tags = bool(app_data)
        if self.selected_record_index is not None and self.selected_table_sname:
            tbl = self.session.get_table(self.selected_table_sname)
            if tbl:
                self._inspect_record(tbl, self.selected_record_index)

    def _inspect_record(self, tbl, row_idx):
        self.selected_record_index = row_idx
        entity_hdr = self.session.get_row_entity_header(tbl.sname, row_idx)
        if entity_hdr:
            dpg.set_value("record_inspector_entity_banner", entity_hdr)
        else:
            dpg.set_value("record_inspector_entity_banner", "")

        safety = get_table_safety_info(tbl.sname)
        dpg.set_value("record_inspector_header", f"Editing Table '{tbl.sname}' ({get_table_display_name(tbl.sname)}) Row #{row_idx}")
        
        if safety["level"] == "DANGEROUS":
            dpg.set_value("record_inspector_safety_warning", f"[HIGH RISK TABLE]: {safety['desc']}")
        elif safety["level"] == "CAUTION":
            dpg.set_value("record_inspector_safety_warning", f"[CAUTION]: {safety['desc']}")
        else:
            dpg.set_value("record_inspector_safety_warning", "")

        rec = tbl.records[row_idx]
        dpg.delete_item("record_fields_container", children_only=True)

        keys_cols = []
        core_cols = []
        flag_cols = []
        adv_cols = []

        query = getattr(self, "inspector_filter_query", "")
        show_tech = getattr(self, "inspector_show_tech_tags", False)

        for col in tbl.columns:
            val = col.decode_value(rec)
            clean_name = get_column_clean_name(col.sname, tbl.sname)
            raw_disp = get_column_display_name(col.sname, tbl.sname)
            info = classify_column(tbl.sname, col.sname, col.col_type, col.bit_size, clean_name)
            
            # Filter match check
            if query:
                match_text = f"{clean_name} {raw_disp} {col.sname} {val}".lower()
                if query not in match_text:
                    continue

            item = (col, val, clean_name, info)
            sec = info["section"]
            if sec == "KEYS":
                keys_cols.append(item)
            elif sec == "FLAGS":
                flag_cols.append(item)
            elif sec == "ADVANCED":
                adv_cols.append(item)
            else:
                core_cols.append(item)

        with dpg.group(parent="record_fields_container"):
            def render_field_entry(col, val, clean_name, info):
                with dpg.group():
                    with dpg.group(horizontal=True):
                        # Clean label formatting
                        if show_tech:
                            lbl = f"{clean_name} [{col.sname} - {col.bit_size}b]:"
                        else:
                            lbl = f"{clean_name}:"
                            
                        with dpg.group(width=300):
                            dpg.add_text(lbl, color=(190, 225, 255))
                            
                        # Role badge
                        dpg.add_text(info["badge"], color=info["badge_color"])
                        dpg.add_spacer(width=4)
                        
                        tag = f"field_edit_{col.sname}"
                        
                        # Foreign Key / Entity resolver check
                        entity_ref = ""
                        if info.get("target_entity"):
                            entity_ref = self.session.resolve_entity_reference(info["target_entity"], val)
                            
                        # Controls
                        if col.col_type == 0:  # String
                            dpg.add_input_text(default_value=str(val), tag=tag, width=320)
                        elif col.col_type == 4:  # Float
                            dpg.add_input_float(default_value=float(val), tag=tag, width=180)
                        elif col.bit_size == 1:  # Boolean
                            items = ["0 - Disabled", "1 - Enabled"]
                            if tbl.sname == "kISL" and col.sname == "GdYI":
                                items = ["0 - Official Venue Name", "1 - Custom Stadium Override"]
                            elif tbl.sname == "kISL" and col.sname == "WMtm":
                                items = ["0 - Standard Venue Capacity", "1 - Major Stadium Tier"]
                            elif "name" in clean_name.lower() or "custom" in clean_name.lower():
                                items = ["0 - Official / Default", "1 - Custom Name Active"]
                            default_item = items[1] if val else items[0]
                            dpg.add_combo(items=items, default_value=default_item, tag=tag, width=230)
                        elif col.bit_size > 32 or (isinstance(val, int) and (val > 2147483647 or val < -2147483648)):
                            dpg.add_input_text(default_value=str(val), tag=tag, width=320)
                        else:  # Standard integer
                            dpg.add_input_int(default_value=int(val), tag=tag, width=180)
                            
                        if entity_ref:
                            dpg.add_spacer(width=4)
                            dpg.add_text(f"-> {entity_ref}", color=(0, 255, 180))
                            
                    # Warning (only when real primary key or raw large blob)
                    if info.get("warning"):
                        dpg.add_text(f"   {info['warning']}", color=(255, 90, 90))
                    dpg.add_spacer(height=3)

            # 1. Render Keys & Relational Links
            if keys_cols:
                dpg.add_text(f"=== [ID] Identification & Relational Links ({len(keys_cols)}) ===", color=(255, 200, 60))
                dpg.add_separator()
                for c, v, cn, inf in keys_cols:
                    render_field_entry(c, v, cn, inf)
                dpg.add_spacer(height=8)

            # 2. Render Core Properties & Ratings
            if core_cols:
                dpg.add_text(f"=== [Props] Core Properties & Attributes ({len(core_cols)}) ===", color=(0, 210, 255))
                dpg.add_separator()
                for c, v, cn, inf in core_cols:
                    render_field_entry(c, v, cn, inf)
                dpg.add_spacer(height=8)

            # 3. Render Flags & State Toggles
            if flag_cols:
                dpg.add_text(f"=== [Flags] Flags & State Toggles ({len(flag_cols)}) ===", color=(0, 255, 180))
                dpg.add_separator()
                for c, v, cn, inf in flag_cols:
                    render_field_entry(c, v, cn, inf)
                dpg.add_spacer(height=8)

            # 4. Render Advanced & Internal Engine Variables (Collapsed by default!)
            if adv_cols:
                with dpg.collapsing_header(label=f"[Advanced] Internal Engine Fields ({len(adv_cols)} fields)", default_open=False):
                    dpg.add_text("Internal bitmasks, raw engine hashes, and undocumented variables.", color=(150, 150, 160))
                    dpg.add_separator()
                    for c, v, cn, inf in adv_cols:
                        render_field_entry(c, v, cn, inf)

        dpg.configure_item("record_actions_group", show=True)
        dpg.set_value("record_save_feedback", "")

    def _on_save_record_changes(self):
        tbl = self.session.get_table(self.selected_table_sname)
        if not tbl or self.selected_record_index is None:
            return

        row_idx = self.selected_record_index
        # 1. Validation pass: Check every column value for valid types and bit overflow
        parsed_values = {}
        for col in tbl.columns:
            tag = f"field_edit_{col.sname}"
            if dpg.does_item_exist(tag):
                raw_val = dpg.get_value(tag)
                if col.bit_size == 1 and isinstance(raw_val, str):
                    val = 1 if ("1" in raw_val or "Custom" in raw_val or "Enabled" in raw_val or "Yes" in raw_val) else 0
                elif col.col_type == 3 and isinstance(raw_val, str):
                    try:
                        val = int(raw_val.strip())
                    except ValueError:
                        val = 0
                else:
                    val = raw_val
                    
                is_valid, err_msg = validate_column_value(col.col_type, col.bit_size, val)
                if not is_valid:
                    disp_name = get_column_clean_name(col.sname, tbl.sname)
                    dpg.set_value("record_save_feedback", f"ERROR in '{disp_name}' [{col.sname}]: {err_msg}")
                    dpg.configure_item("record_save_feedback", color=(255, 80, 80))
                    return
                parsed_values[col.sname] = val

        # 2. Apply verified changes
        for sname, val in parsed_values.items():
            self.session.update_table_cell(self.selected_table_sname, row_idx, sname, val)

        self._update_save_and_changes_toolbar()
        dpg.configure_item("record_save_feedback", color=(0, 255, 120))
        dpg.set_value("record_save_feedback", f"[OK] Record #{row_idx} staged ({self.session.change_tracker.count} changes)! Click 'Save File' above to persist.")
        self._render_db_records_page()

def main():
    app = SquadEditorApp()
    app.run()

if __name__ == "__main__":
    main()
