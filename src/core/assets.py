import os
import sys
import io
import time
import queue
import threading
import urllib.request
import urllib.error
from typing import Optional, Dict, Tuple, List, Any
import dearpygui.dearpygui as dpg
from PIL import Image, ImageDraw, ImageFont

try:
    from core.team_mappings import get_parent_club_id, is_women_team
except ImportError:
    from src.core.team_mappings import get_parent_club_id, is_women_team

# Authentic Managers for major EA Sports FC 25 clubs
AUTHENTIC_CLUB_MANAGERS: Dict[int, Dict[str, str]] = {
    243: {"name": "Carlo Ancelotti", "nationality": "Italy", "role": "Tactical Mastermind"},
    10: {"name": "Pep Guardiola", "nationality": "Spain", "role": "Tiki-Taka Visionary"},
    1: {"name": "Mikel Arteta", "nationality": "Spain", "role": "Modern Strategist"},
    9: {"name": "Arne Slot", "nationality": "Netherlands", "role": "High-Press Specialist"},
    241: {"name": "Hansi Flick", "nationality": "Germany", "role": "Direct Attacking Pioneer"},
    240: {"name": "Diego Simeone", "nationality": "Argentina", "role": "Defensive Organizer"},
    5: {"name": "Enzo Maresca", "nationality": "Italy", "role": "Positional Playmaster"},
    11: {"name": "Erik ten Hag", "nationality": "Netherlands", "role": "System Builder"},
    18: {"name": "Ange Postecoglou", "nationality": "Australia", "role": "Aggressive High-Line"},
    21: {"name": "Vincent Kompany", "nationality": "Belgium", "role": "Modern Leader"},
    32: {"name": "Xabi Alonso", "nationality": "Spain", "role": "Fluid Play Architect"},
    73: {"name": "Luis Enrique", "nationality": "Spain", "role": "Possession General"},
    44: {"name": "Simone Inzaghi", "nationality": "Italy", "role": "3-5-2 Maestro"},
    45: {"name": "Thiago Motta", "nationality": "Italy", "role": "Dynamic Tactician"},
    47: {"name": "Paulo Fonseca", "nationality": "Portugal", "role": "Attacking Flow"},
    112139: {"name": "Stefano Pioli", "nationality": "Italy", "role": "Pragmatic Motivator"},
    605: {"name": "Jorge Jesus", "nationality": "Portugal", "role": "Dominant Press"},
    112893: {"name": "Gerardo Martino", "nationality": "Argentina", "role": "Experienced Tactician"},
    112885: {"name": "Laurent Blanc", "nationality": "France", "role": "Calm Commander"},
    237: {"name": "Rúben Amorim", "nationality": "Portugal", "role": "Intense Wingback Engine"},
    234: {"name": "Bruno Lage", "nationality": "Portugal", "role": "Development Expert"},
    236: {"name": "Vítor Bruno", "nationality": "Portugal", "role": "Aggressive Transition"},
    13: {"name": "Eddie Howe", "nationality": "England", "role": "Relentless Intensity"},
    2: {"name": "Unai Emery", "nationality": "Spain", "role": "Cup Tournament King"},
    48: {"name": "Antonio Conte", "nationality": "Italy", "role": "Disciplined Machine"},
    52: {"name": "Ivan Jurić", "nationality": "Croatia", "role": "Physical Man-Marking"},
    22: {"name": "Nuri Şahin", "nationality": "Turkey", "role": "Youth Integrator"},
    189: {"name": "Roberto De Zerbi", "nationality": "Italy", "role": "Vertical Build-Up"},
}

class AssetManager:
    """
    Manages local and online minifaces, club crests, manager portraits,
    dynamic fallback avatars, and Dear PyGui texture integration.
    """
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir:
            self.base_dir = base_dir
        elif getattr(sys, "frozen", False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.faces_dir = os.path.join(self.base_dir, "assets", "faces")
        self.crests_dir = os.path.join(self.base_dir, "assets", "crests")
        self.managers_dir = os.path.join(self.base_dir, "assets", "managers")
        
        # External Live Editor search paths
        self.le_heads_dir = os.path.join(self.base_dir, "FC25LEv25.4.2", "mods", "root", "Legacy", "data", "ui", "imgAssets", "heads")
        self.le_crest_dir = os.path.join(self.base_dir, "FC25LEv25.4.2", "mods", "root", "Legacy", "data", "ui", "imgAssets", "crest", "dark")

        os.makedirs(self.faces_dir, exist_ok=True)
        os.makedirs(self.crests_dir, exist_ok=True)
        os.makedirs(self.managers_dir, exist_ok=True)

        self.loaded_textures = set()
        self.download_queue = set()
        self.active_downloads = 0
        self.max_threads = 4
        self.lock = threading.Lock()

        # In-memory manager overrides
        self.custom_managers: Dict[int, Dict[str, str]] = {}
        self.pending_textures_queue = queue.Queue()
        self.on_asset_loaded = None  # Optional callback (asset_type: str, id_val: int, tag: str) -> None

        # Version tracking for DPG textures to prevent alias reuse collisions
        self.club_texture_versions: Dict[int, int] = {}

        # Batch downloader state
        self.batch_download_running: bool = False
        self.batch_download_cancel: bool = False
        self.batch_progress: Dict[str, Any] = {}

    def process_pending_textures(self):
        """Processes completed background image downloads into DPG textures safely on the main thread."""
        while not self.pending_textures_queue.empty():
            try:
                item = self.pending_textures_queue.get_nowait()
                asset_type = item[0]
                if asset_type == "club":
                    team_id, local_path = item[1], item[2]
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                        new_tag = self._load_club_texture_from_file(team_id, local_path)
                        if new_tag and callable(self.on_asset_loaded):
                            self.on_asset_loaded("club", team_id, new_tag)
                elif asset_type == "player":
                    player_id, local_path, tag = item[1], item[2], item[3]
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                        if self._load_image_to_texture(local_path, tag):
                            if callable(self.on_asset_loaded):
                                self.on_asset_loaded("player", player_id, tag)
            except Exception:
                pass

    def init_dpg_textures(self):
        """Initializes default placeholder textures in Dear PyGui."""
        if not dpg.does_item_exist("app_texture_registry"):
            dpg.add_texture_registry(tag="app_texture_registry", show=False)

        self._ensure_default_textures()

    def _ensure_default_textures(self):
        """Creates default transparent/fallback textures."""
        # 1. Default Player Face Texture (128x128)
        tag_p = "tex_default_player"
        if not dpg.does_item_exist(tag_p):
            def_p_path = os.path.join(self.faces_dir, "default_player.png")
            if not os.path.exists(def_p_path):
                self._draw_default_player_badge(def_p_path)
            self._load_image_to_texture(def_p_path, tag_p)

        # 2. Default Club Crest Texture (128x128)
        tag_c = "tex_default_club"
        if not dpg.does_item_exist(tag_c):
            def_c_path = os.path.join(self.crests_dir, "default_club.png")
            if not os.path.exists(def_c_path):
                self._draw_default_club_shield(def_c_path)
            self._load_image_to_texture(def_c_path, tag_c)

        # 3. Default Manager Texture (128x128)
        tag_m = "tex_default_manager"
        if not dpg.does_item_exist(tag_m):
            def_m_path = os.path.join(self.managers_dir, "default_manager.png")
            if not os.path.exists(def_m_path):
                self._draw_default_manager_badge(def_m_path)
            self._load_image_to_texture(def_m_path, tag_m)

    def _draw_default_player_badge(self, filepath: str):
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Circular card
        draw.ellipse([6, 6, 122, 122], fill=(28, 32, 42, 255), outline=(0, 160, 240, 255), width=3)
        # Silhouette head & shoulders
        draw.ellipse([46, 26, 82, 62], fill=(70, 80, 100, 255))
        draw.ellipse([24, 68, 104, 130], fill=(70, 80, 100, 255))
        img.save(filepath, "PNG")

    def _draw_default_club_shield(self, filepath: str):
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        points = [(64, 8), (116, 26), (102, 92), (64, 122), (26, 92), (12, 26)]
        draw.polygon(points, fill=(24, 30, 44, 255), outline=(0, 200, 255, 255), width=3)
        draw.ellipse([44, 44, 84, 84], fill=(0, 122, 204, 255))
        img.save(filepath, "PNG")

    def _draw_club_crest_badge(self, filepath: str, team_id: int, team_name: str):
        """Draws a tailored club crest shield with the club's abbreviation/initials."""
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        points = [(64, 8), (116, 26), (104, 94), (64, 122), (24, 94), (12, 26)]
        colors = [
            ((20, 35, 60), (0, 180, 240)),     # Sky Blue
            ((60, 20, 25), (240, 60, 60)),     # Red
            ((40, 20, 60), (180, 80, 240)),    # Purple
            ((15, 45, 30), (0, 220, 140)),     # Emerald
            ((50, 45, 20), (255, 200, 0)),     # Gold
            ((35, 35, 40), (200, 200, 210)),   # Silver
        ]
        bg_col, border_col = colors[team_id % len(colors)]
        draw.polygon(points, fill=(*bg_col, 255), outline=(*border_col, 255), width=3)
        draw.ellipse([36, 36, 92, 92], fill=(25, 28, 38, 255), outline=(*border_col, 180), width=2)
        words = [w for w in team_name.replace("FC", "").replace("CF", "").split() if w]
        if len(words) >= 3:
            abbr = (words[0][0] + words[1][0] + words[2][0]).upper()
        elif len(words) == 2:
            abbr = (words[0][:2] + words[1][0]).upper()
        elif len(words) == 1:
            abbr = words[0][:3].upper()
        else:
            abbr = "FC"
        try:
            draw.text((64, 64), abbr, fill=(255, 255, 255, 255), anchor="mm")
        except Exception:
            draw.text((50, 56), abbr, fill=(255, 255, 255, 255))
        img.save(filepath, "PNG")

    def _draw_default_manager_badge(self, filepath: str):
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([6, 6, 122, 122], radius=16, fill=(30, 36, 48, 255), outline=(0, 220, 150, 255), width=3)
        draw.polygon([(64, 40), (52, 60), (76, 60)], fill=(200, 200, 200, 255))
        draw.polygon([(60, 60), (68, 60), (72, 105), (64, 115), (56, 105)], fill=(0, 200, 140, 255))
        img.save(filepath, "PNG")

    def _draw_manager_badge_with_name(self, filepath: str, name: str):
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([6, 6, 122, 122], radius=16, fill=(24, 32, 44, 255), outline=(0, 220, 150, 255), width=3)
        draw.polygon([(64, 46), (50, 68), (78, 68)], fill=(220, 220, 220, 255))
        draw.polygon([(60, 68), (68, 68), (72, 112), (64, 120), (56, 112)], fill=(0, 200, 140, 255))
        parts = [p for p in name.strip().split() if p]
        initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")) if parts else "HC"
        initials = initials.upper()[:3]
        try:
            draw.text((64, 28), initials, fill=(255, 255, 255, 255), anchor="mm")
        except Exception:
            draw.text((54, 20), initials, fill=(255, 255, 255, 255))
        img.save(filepath, "PNG")

    def _load_image_to_texture(self, img_path: str, tag: str) -> bool:
        """Loads a PNG/JPG/BMP image into Dear PyGui texture registry."""
        if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
            return False
        try:
            w, h, channels, data = dpg.load_image(img_path)
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            dpg.add_static_texture(width=w, height=h, default_value=data, tag=tag, parent="app_texture_registry")
            self.loaded_textures.add(tag)
            return True
        except Exception:
            return False

    def _load_club_texture_from_file(self, team_id: int, img_path: str) -> str:
        """Loads a club crest image into DPG using versioned texture tags to prevent alias conflicts."""
        if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
            return "tex_default_club"
        try:
            try:
                w, h, channels, data = dpg.load_image(img_path)
            except Exception:
                # Fallback: sanitize & resave via PIL as standard 32-bit RGBA PNG
                with Image.open(img_path) as im:
                    im = im.convert("RGBA")
                    im.save(img_path, "PNG")
                w, h, channels, data = dpg.load_image(img_path)

            old_ver = self.club_texture_versions.get(team_id, 0)
            new_ver = old_ver + 1
            new_tag = f"tex_club_{team_id}_v{new_ver}"

            dpg.add_static_texture(width=w, height=h, default_value=data, tag=new_tag, parent="app_texture_registry")
            self.club_texture_versions[team_id] = new_ver
            self.loaded_textures.add(new_tag)

            return new_tag
        except Exception:
            return "tex_default_club"

    def cleanup_old_club_texture(self, team_id: int):
        """Cleans up superseded texture versions for a club after UI has re-bound."""
        cur_ver = self.club_texture_versions.get(team_id, 0)
        for v in range(1, cur_ver):
            old_tag = f"tex_club_{team_id}_v{v}"
            if dpg.does_item_exist(old_tag):
                try:
                    dpg.delete_item(old_tag)
                except Exception:
                    pass
            self.loaded_textures.discard(old_tag)

    def get_player_texture(self, player_id: int, player_name: str = "", jersey: int = 10, ovr: int = 75, pos: str = "CM") -> str:
        """Returns the DPG texture tag for a player. Loads from disk or queues background download."""
        tag = f"tex_player_{player_id}"
        if tag in self.loaded_textures and dpg.does_item_exist(tag):
            return tag

        local_path = os.path.join(self.faces_dir, f"p{player_id}.png")
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            if self._load_image_to_texture(local_path, tag):
                return tag

        le_path = os.path.join(self.le_heads_dir, f"p{player_id}.png")
        if os.path.exists(le_path) and os.path.getsize(le_path) > 0:
            if self._load_image_to_texture(le_path, tag):
                return tag

        self._queue_player_download(player_id, tag, local_path)
        return "tex_default_player"

    def get_club_texture(self, team_id: int, team_name: str = "") -> str:
        """Returns the DPG texture tag for a club crest. Loads from disk or queues download."""
        if team_id <= 0:
            return "tex_default_club"

        # 1. If authentic crest exists on disk, check if already loaded
        local_path = os.path.join(self.crests_dir, f"c{team_id}.png")
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            if team_id in self.club_texture_versions:
                tag = f"tex_club_{team_id}_v{self.club_texture_versions[team_id]}"
                if dpg.does_item_exist(tag):
                    return tag
            return self._load_club_texture_from_file(team_id, local_path)

        # 2. Check Live Editor dump
        le_crest = os.path.join(self.le_crest_dir, f"l{team_id}.png")
        if os.path.exists(le_crest) and os.path.getsize(le_crest) > 0:
            return self._load_club_texture_from_file(team_id, le_crest)

        # 3. Check crest inheritance from parent club
        parent_id = get_parent_club_id(team_id)
        if parent_id != team_id and parent_id > 0:
            parent_local = os.path.join(self.crests_dir, f"c{parent_id}.png")
            if os.path.exists(parent_local) and os.path.getsize(parent_local) > 0:
                return self._load_club_texture_from_file(team_id, parent_local)

        # 4. If current active version already loaded (e.g. fallback already displayed), return it
        if team_id in self.club_texture_versions:
            tag = f"tex_club_{team_id}_v{self.club_texture_versions[team_id]}"
            if dpg.does_item_exist(tag):
                self._queue_club_download(team_id, local_path)
                return tag

        # 5. Create instant personalized fallback shield badge with club initials
        fallback_path = os.path.join(self.crests_dir, f"fallback_{team_id}.png")
        if not os.path.exists(fallback_path):
            self._draw_club_crest_badge(fallback_path, team_id, team_name)

        fallback_tag = self._load_club_texture_from_file(team_id, fallback_path)

        # 6. Queue async download from multi-tier CDNs
        self._queue_club_download(team_id, local_path)
        return fallback_tag

    def get_manager_texture(self, team_id: int, manager_name: str = "", manager_asset_id: int = 0) -> str:
        """Returns the DPG texture tag for a club manager."""
        if team_id <= 0:
            return "tex_default_manager"
            
        tag = f"tex_manager_{team_id}"
        if tag in self.loaded_textures and dpg.does_item_exist(tag):
            return tag

        local_path = os.path.join(self.managers_dir, f"m{team_id}.png")
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            if self._load_image_to_texture(local_path, tag):
                return tag

        # Check Live Editor head directory if manager_asset_id is known
        if manager_asset_id > 0:
            le_mgr = os.path.join(self.le_heads_dir, f"p{manager_asset_id}.png")
            if os.path.exists(le_mgr) and os.path.getsize(le_mgr) > 0:
                if self._load_image_to_texture(le_mgr, tag):
                    return tag

        # Generate custom personalized badge with coach name
        m_info = self.get_club_manager_info(team_id, manager_name)
        m_display_name = manager_name or m_info.get("name", "Head Coach")
        try:
            self._draw_manager_badge_with_name(local_path, m_display_name)
            if self._load_image_to_texture(local_path, tag):
                return tag
        except Exception:
            pass

        return "tex_default_manager"

    def _queue_player_download(self, player_id: int, tag: str, local_path: str):
        with self.lock:
            if player_id in self.download_queue:
                return
            self.download_queue.add(player_id)

        def _worker():
            url = f"https://cdn.futbin.com/content/fifa25/img/players/{player_id}.png"
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        content = resp.read()
                        with open(local_path, "wb") as f:
                            f.write(content)
                        # Queue for safe main-thread texture registration
                        self.pending_textures_queue.put(("player", player_id, local_path, tag))
            except Exception:
                pass
            finally:
                with self.lock:
                    self.download_queue.discard(player_id)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _queue_club_download(self, team_id: int, local_path: str):
        with self.lock:
            if team_id in self.download_queue:
                return
            self.download_queue.add(team_id)

        parent_id = get_parent_club_id(team_id)

        def _worker():
            try:
                target_ids = []
                if team_id == 113154:
                    target_ids.append(113217)
                target_ids.append(team_id)
                if parent_id > 0 and parent_id != team_id:
                    target_ids.append(parent_id)

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://sofifa.com/"
                }

                content = None
                for dl_id in target_ids:
                    urls = [
                        f"https://cdn.futwiz.com/assets/img/fc25/badges/{dl_id}.png",
                        f"https://cdn.sofifa.net/teams/{dl_id}/120.png",
                        f"https://cdn.futbin.com/content/fifa25/img/clubs/{dl_id}.png",
                        f"https://cdn.sofifa.net/teams/{dl_id}/60.png",
                        f"https://cdn.futwiz.com/assets/img/fc24/badges/{dl_id}.png",
                        f"https://cdn.futwiz.com/assets/img/fifa23/badges/{dl_id}.png",
                    ]
                    for url in urls:
                        try:
                            req = urllib.request.Request(url, headers=headers)
                            with urllib.request.urlopen(req, timeout=4) as resp:
                                if resp.status == 200:
                                    data = resp.read()
                                    if len(data) > 500:
                                        content = data
                                        break
                        except Exception:
                            continue
                    if content:
                        break

                if content:
                    try:
                        im = Image.open(io.BytesIO(content)).convert("RGBA")
                        im.save(local_path, "PNG")
                        self.pending_textures_queue.put(("club", team_id, local_path))
                    except Exception:
                        with open(local_path, "wb") as f:
                            f.write(content)
                        self.pending_textures_queue.put(("club", team_id, local_path))
            except Exception:
                pass
            finally:
                with self.lock:
                    self.download_queue.discard(team_id)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def start_batch_crest_download(
        self,
        teams_list: List[Dict[str, Any]],
        on_progress=None,
        on_complete=None
    ) -> Tuple[bool, str]:
        """
        Starts a background batch download of authentic crests for all teams that
        are missing local crests.
        """
        if self.batch_download_running:
            return False, "Batch download is already running."

        self.batch_download_running = True
        self.batch_download_cancel = False
        self.batch_progress = {
            "total": len(teams_list),
            "completed": 0,
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "current_team": ""
        }

        def _batch_worker():
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://sofifa.com/"
            }

            for t in teams_list:
                if self.batch_download_cancel:
                    break

                tid = t.get("teamid", 0)
                tname = t.get("name", "")
                if tid <= 0:
                    self.batch_progress["completed"] += 1
                    continue

                self.batch_progress["current_team"] = tname
                local_path = os.path.join(self.crests_dir, f"c{tid}.png")

                # Skip if already downloaded and valid
                if os.path.exists(local_path) and os.path.getsize(local_path) > 500:
                    self.batch_progress["skipped"] += 1
                    self.batch_progress["completed"] += 1
                    if callable(on_progress):
                        on_progress(dict(self.batch_progress))
                    continue

                parent_id = get_parent_club_id(tid)
                target_ids = []
                if tid == 113154:
                    target_ids.append(113217)
                target_ids.append(tid)
                if parent_id > 0 and parent_id != tid:
                    target_ids.append(parent_id)

                content = None
                for dl_id in target_ids:
                    urls = [
                        f"https://cdn.futwiz.com/assets/img/fc25/badges/{dl_id}.png",
                        f"https://cdn.sofifa.net/teams/{dl_id}/120.png",
                        f"https://cdn.futbin.com/content/fifa25/img/clubs/{dl_id}.png",
                        f"https://cdn.sofifa.net/teams/{dl_id}/60.png",
                        f"https://cdn.futwiz.com/assets/img/fc24/badges/{dl_id}.png",
                        f"https://cdn.futwiz.com/assets/img/fifa23/badges/{dl_id}.png",
                    ]
                    for url in urls:
                        try:
                            req = urllib.request.Request(url, headers=headers)
                            with urllib.request.urlopen(req, timeout=3) as resp:
                                if resp.status == 200:
                                    data = resp.read()
                                    if len(data) > 500:
                                        content = data
                                        break
                        except Exception:
                            continue
                    if content:
                        break

                if content:
                    try:
                        im = Image.open(io.BytesIO(content)).convert("RGBA")
                        im.save(local_path, "PNG")
                        self.batch_progress["downloaded"] += 1
                        self.pending_textures_queue.put(("club", tid, local_path))
                    except Exception:
                        self.batch_progress["failed"] += 1
                else:
                    self.batch_progress["failed"] += 1

                self.batch_progress["completed"] += 1
                if callable(on_progress):
                    on_progress(dict(self.batch_progress))

                time.sleep(0.04)

            self.batch_download_running = False
            if callable(on_complete):
                on_complete(dict(self.batch_progress))

        t = threading.Thread(target=_batch_worker, daemon=True)
        t.start()
        return True, "Batch crest download started."

    def cancel_batch_crest_download(self) -> bool:
        """Signals active batch crest download worker to cancel."""
        if getattr(self, "batch_download_running", False):
            self.batch_download_cancel = True
            return True
        return False

    def import_custom_player_face(self, player_id: int, source_filepath: str) -> Tuple[bool, str]:
        """Imports an external image file (PNG/JPG/BMP/DDS) as player's authentic miniface."""
        if not os.path.exists(source_filepath):
            return False, "Selected image file does not exist."
        try:
            img = Image.open(source_filepath).convert("RGBA")
            target_path = os.path.join(self.faces_dir, f"p{player_id}.png")
            img.save(target_path, "PNG")

            # Reload texture
            tag = f"tex_player_{player_id}"
            self._load_image_to_texture(target_path, tag)
            return True, f"Miniface successfully imported for player #{player_id}!"
        except Exception as e:
            return False, f"Failed to import miniface: {str(e)}"

    def import_custom_club_crest(self, team_id: int, source_filepath: str) -> Tuple[bool, str]:
        """Imports an external image file as club crest."""
        if not os.path.exists(source_filepath):
            return False, "Selected image file does not exist."
        try:
            img = Image.open(source_filepath).convert("RGBA")
            target_path = os.path.join(self.crests_dir, f"c{team_id}.png")
            img.save(target_path, "PNG")

            self._load_club_texture_from_file(team_id, target_path)
            return True, f"Club crest successfully imported for team ID {team_id}!"
        except Exception as e:
            return False, f"Failed to import crest: {str(e)}"

    def import_custom_manager_face(self, team_id: int, source_filepath: str) -> Tuple[bool, str]:
        """Imports an external image file as manager portrait."""
        if not os.path.exists(source_filepath):
            return False, "Selected image file does not exist."
        try:
            img = Image.open(source_filepath).convert("RGBA")
            target_path = os.path.join(self.managers_dir, f"m{team_id}.png")
            img.save(target_path, "PNG")

            tag = f"tex_manager_{team_id}"
            self._load_image_to_texture(target_path, tag)
            return True, f"Manager portrait successfully imported for team ID {team_id}!"
        except Exception as e:
            return False, f"Failed to import manager image: {str(e)}"

    def get_club_manager_info(self, team_id: int, default_team_name: str = "") -> Dict[str, str]:
        """Returns authentic or customized manager details for a club."""
        if team_id in self.custom_managers:
            return self.custom_managers[team_id]
        if team_id in AUTHENTIC_CLUB_MANAGERS:
            return dict(AUTHENTIC_CLUB_MANAGERS[team_id])
        return {
            "name": f"Manager of {default_team_name}" if default_team_name else "Head Coach",
            "nationality": "International",
            "role": "Tactical Director"
        }

    def set_club_manager_info(self, team_id: int, name: str, nationality: str = "International", role: str = "Head Coach"):
        """Saves custom manager details for a club."""
        self.custom_managers[team_id] = {
            "name": name.strip(),
            "nationality": nationality.strip(),
            "role": role.strip()
        }
