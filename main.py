import sys
import math
import random
from array import array

import pygame
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Fragment in the Mainframe - Metroidvania Foundation Prototype
# ---------------------------------------------------------------------------
# This script establishes a significantly larger foundation for the cyberpunk
# adventure.  It focuses on structure: a hub, four themed zones, ability
# gating, branching quests, NPC interactions, and encounter scaffolding.  The
# mechanics are intentionally lightweight but showcase how a 6-7 hour campaign
# could be built on top of this framework.
# ---------------------------------------------------------------------------

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60
GRAVITY = 0.45
PLAYER_SPEED = 3.2
PLAYER_JUMP = 9.0
PLAYER_DASH_SPEED = 8.0
PLAYER_DASH_TIME = 12
BASE_DASH_COOLDOWN = 45
SLASH_REACH = 26
SLASH_TIME = 10
DEBUG_RANGE = 60

COLOR_BG = (6, 6, 14)
COLOR_PLATFORM = (32, 40, 64)
COLOR_PLAYER = (120, 220, 255)
COLOR_SLASH = (255, 255, 120)
COLOR_TEXT = (210, 200, 220)
COLOR_DIALOGUE_BG = (18, 12, 24)
COLOR_DIALOGUE_BORDER = (90, 70, 120)
COLOR_CORRUPTION = (255, 40, 120)

ABILITY_COLORS = {
    "data_hook": (120, 255, 190),
    "phase_shift": (200, 120, 255),
    "codebreaker": (255, 180, 120),
    "overclock": (255, 110, 160),
}

ZONE_SKIES = {
    "kernel_nexus": (12, 16, 34),
    "archive": (18, 18, 48),
    "processing_core": (36, 18, 18),
    "memory_garden": (12, 40, 26),
    "deep_storage": (8, 12, 40),
    "signal_sea": (10, 26, 46),
    "trash_hollows": (32, 10, 18),
    "core_ascendant": (20, 16, 40),
    "mirror_rift": (14, 10, 34),
    "logic_spires": (26, 12, 44),
    "quantum_forge": (34, 12, 28),
    "nocturne_array": (12, 18, 42),
    "backtrace_fathoms": (10, 24, 30),
    "echo_sanctum": (18, 22, 52),
    "entropy_cathedral": (28, 8, 24),
    "oblivion_grid": (30, 6, 36),
    "prime_convergence": (8, 8, 28),
    "paradox_vault": (24, 8, 52),
    "resonant_expanse": (10, 20, 50),
    "fractal_bastion": (16, 8, 42),
    "luminous_reserve": (18, 30, 46),
    "sundown_bazaar": (28, 18, 34),
    "permutation_labyrinth": (14, 10, 38),
    "cradle_of_resolve": (32, 16, 40),
    "umbra_cloister": (18, 10, 34),
    "radiant_span": (26, 28, 48),
    "infinite_chamber": (8, 6, 24),
    "nebula_reliquary": (18, 20, 52),
    "tesseract_workshop": (16, 14, 46),
    "processional_way": (12, 8, 30),
}

BOSS_ACHIEVEMENTS = {
    "Guardian of Forgotten Code": "archive_guardian",
    "Overclocked Administrator": "core_administrator",
    "Crucible Golem": "forge_golem",
    "Garden Firewall": "garden_firewall",
    "Nocturne Choir": "nocturne_choir",
    "Vault Sentience": "deep_storage_core",
    "Surge Leviathan": "signal_leviathan",
    "Fathom Leviathan": "fathom_leviathan",
    "Refuse Colossus": "trash_colossus",
    "Mirror Warden": "mirror_warden",
    "Spires Choir": "spires_choir",
    "Ascendant Overseer": "ascendant_overseer",
    "Entropy Bishop": "entropy_bishop",
    "Harmonic Sentinel": "echo_sentinel",
    "Oblivion Arbiter": "oblivion_arbiter",
    "Prime Architect": "prime_architect",
    "Paradox Regent": "paradox_regent",
    "Eidolon Maestro": "eidolon_maestro",
    "Fractal Paragon": "fractal_paragon",
    "Celestial Compiler": "celestial_compiler",
    "Permutation Hydra": "permutation_hydra",
    "Cradle Sovereign": "cradle_sovereign",
    "Bazaar Sentinel": "bazaar_sentinel",
    "Umbra Inquisitor": "umbra_inquisitor",
    "Radiant Arbiter": "radiant_arbiter",
    "Infinite Oracle": "infinite_oracle",
    "Reliquary Seraph": "reliquary_seraph",
    "Tensor Artificer": "tensor_artificer",
    "Procession Warden": "procession_warden",
}

# ---------------------------------------------------------------------------
# Helper structures
# ---------------------------------------------------------------------------


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass
class Platform:
    rect: pygame.Rect
    kind: str = "solid"  # can be "solid" or "hazard"

    def draw(self, surface: pygame.Surface, color: Tuple[int, int, int]):
        pygame.draw.rect(surface, color, self.rect)


@dataclass
class Soundscape:
    zone: str
    tone: float
    modulation: float
    volume: float
    description: str = ""


@dataclass
class UpgradeTerminal:
    rect: pygame.Rect
    upgrade_id: str
    cost: int
    description: str

    def draw(self, surface: pygame.Surface):
        glow = (math.sin(pygame.time.get_ticks() / 280) + 1) * 0.5
        base = (90, 40, 130)
        color = tuple(int(base[i] + glow * (255 - base[i])) for i in range(3))
        pygame.draw.rect(surface, color, self.rect)


@dataclass
class GameState:
    corruption: int = 10
    health: int = 6
    max_health: int = 6
    data_fragments: int = 0
    abilities: Dict[str, bool] = field(
        default_factory=lambda: {
            "dash": True,
            "data_hook": False,
            "phase_shift": False,
            "codebreaker": False,
            "overclock": False,
        }
    )
    upgrades: Dict[str, bool] = field(default_factory=dict)
    quest_flags: Dict[str, bool] = field(default_factory=dict)
    lore_entries: Dict[str, bool] = field(default_factory=dict)
    items: Dict[str, int] = field(default_factory=dict)
    item_notes: Dict[str, str] = field(default_factory=dict)
    visited_zones: Dict[str, bool] = field(default_factory=dict)
    achievements: Dict[str, bool] = field(default_factory=dict)
    faction_rep: Dict[str, int] = field(
        default_factory=lambda: {"caretakers": 0, "rebellion": 0, "collectors": 0}
    )
    companions: Dict[str, bool] = field(default_factory=dict)
    last_save: Optional[Tuple[str, Tuple[int, int]]] = None

    def adjust_corruption(self, amount: int):
        self.corruption = int(clamp(self.corruption + amount, 0, 100))

    def add_fragments(self, amount: int):
        self.data_fragments += amount

    def take_damage(self, amount: int):
        self.health = max(0, self.health - amount)

    def heal(self, amount: int):
        self.health = min(self.max_health, self.health + amount)

    def unlock_ability(self, ability: str):
        if ability not in self.abilities:
            self.abilities[ability] = False
        self.abilities[ability] = True

    def ability_active(self, ability: str) -> bool:
        return self.abilities.get(ability, False)

    def set_flag(self, flag: Optional[str]):
        if flag:
            self.quest_flags[flag] = True

    def has_flag(self, flag: Optional[str]) -> bool:
        if not flag:
            return False
        return self.quest_flags.get(flag, False)

    def add_item(self, item_id: str, amount: int = 1, description: str = ""):
        self.items[item_id] = self.items.get(item_id, 0) + amount
        if description:
            self.item_notes.setdefault(item_id, description)

    def consume_item(self, item_id: str, amount: int = 1) -> bool:
        if self.items.get(item_id, 0) < amount:
            return False
        self.items[item_id] -= amount
        if self.items[item_id] <= 0:
            self.items.pop(item_id, None)
            self.item_notes.pop(item_id, None)
        return True

    def mark_zone_visited(self, zone: str) -> bool:
        newly_visited = not self.visited_zones.get(zone, False)
        self.visited_zones[zone] = True
        return newly_visited

    def unlock_achievement(self, achievement_id: str) -> bool:
        if self.achievements.get(achievement_id):
            return False
        self.achievements[achievement_id] = True
        return True

    def adjust_reputation(self, faction: str, amount: int) -> int:
        value = self.faction_rep.get(faction, 0) + amount
        value = int(clamp(value, -100, 100))
        self.faction_rep[faction] = value
        return value

    def add_companion(self, companion_id: str):
        self.companions[companion_id] = True

    def companion_count(self) -> int:
        return sum(1 for active in self.companions.values() if active)


@dataclass
class Portal:
    rect: pygame.Rect
    target_zone: str
    target_spawn: Tuple[int, int]
    requirement: Optional[str] = None
    label: str = ""


@dataclass
class AbilityPickup:
    rect: pygame.Rect
    ability: str
    description: str

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, ABILITY_COLORS[self.ability], self.rect)


@dataclass
class Collectible:
    rect: pygame.Rect
    name: str
    description: str
    value: int = 1
    lore_id: Optional[str] = None


@dataclass
class ItemDrop:
    rect: pygame.Rect
    item_id: str
    name: str
    description: str
    quantity: int = 1

    def draw(self, surface: pygame.Surface):
        color = (200, 210, 120)
        pygame.draw.rect(surface, color, self.rect)


@dataclass
class SaveStation:
    rect: pygame.Rect
    name: str
    description: str
    respawn_point: Tuple[int, int]

    def draw(self, surface: pygame.Surface):
        pulse = (math.sin(pygame.time.get_ticks() / 280) + 1) * 0.5
        base = (60, 140, 220)
        glow = tuple(int(base[i] + pulse * (255 - base[i])) for i in range(3))
        pygame.draw.rect(surface, glow, self.rect)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)


@dataclass
class StoryEvent:
    rect: pygame.Rect
    flag: str
    message: str
    grant_item: Optional[Tuple[str, int, str]] = None
    adjust_corruption: int = 0
    grant_quest: Optional[str] = None
    complete_quest: Optional[str] = None
    unlock_ability: Optional[str] = None
    lore_id: Optional[str] = None
    reputation_changes: Tuple[Tuple[str, int], ...] = ()
    set_flags: Tuple[str, ...] = ()
    requires_flag: Optional[str] = None
    forbidden_flag: Optional[str] = None
    cinematic_id: Optional[str] = None

    def can_trigger(self, state: "GameState") -> bool:
        if state.has_flag(self.flag):
            return False
        if self.requires_flag and not state.has_flag(self.requires_flag):
            return False
        if self.forbidden_flag and state.has_flag(self.forbidden_flag):
            return False
        return True


@dataclass
class DialogueLine:
    text: str
    requirement: Optional[str] = None
    grant_quest: Optional[str] = None
    completes_quest: Optional[str] = None
    requires_flag: Optional[str] = None
    forbidden_flag: Optional[str] = None
    set_flag: Optional[str] = None


@dataclass
class NPC:
    name: str
    rect: pygame.Rect
    lines: List[DialogueLine]
    friendly: bool = True

    def draw(self, surface: pygame.Surface):
        color = (160, 200, 255) if self.friendly else (255, 100, 160)
        pygame.draw.rect(surface, color, self.rect)


@dataclass
class Quest:
    id: str
    title: str
    description: str
    completed: bool = False


class QuestLog:
    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self.visible = True

    def add_quest(self, quest: Quest):
        self.quests.setdefault(quest.id, quest)

    def complete(self, quest_id: str):
        if quest_id in self.quests:
            self.quests[quest_id].completed = True

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if not self.visible or not self.quests:
            return
        overlay = pygame.Surface((250, 160), pygame.SRCALPHA)
        overlay.fill((12, 6, 18, 200))
        surface.blit(overlay, (SCREEN_WIDTH - 260, 20))
        y = 40
        title = font.render("Quest Log", True, COLOR_TEXT)
        surface.blit(title, (SCREEN_WIDTH - 240, 30))
        for quest in self.quests.values():
            status = "(Done)" if quest.completed else ""
            line = font.render(f"• {quest.title} {status}", True, COLOR_TEXT)
            surface.blit(line, (SCREEN_WIDTH - 250, y))
            y += 22

    def toggle(self):
        self.visible = not self.visible


class LoreCodex:
    def __init__(self):
        self.entries: Dict[str, Tuple[str, str]] = {}
        self.visible = True

    def register(self, key: str, title: str, text: str):
        self.entries.setdefault(key, (title, text))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, discovered: Dict[str, bool]):
        if not self.visible:
            return
        discovered_entries = [key for key, flag in discovered.items() if flag]
        if not discovered_entries:
            return
        overlay = pygame.Surface((260, 160), pygame.SRCALPHA)
        overlay.fill((20, 12, 32, 200))
        surface.blit(overlay, (20, SCREEN_HEIGHT - 200))
        title = font.render("Lore Codex", True, COLOR_TEXT)
        surface.blit(title, (30, SCREEN_HEIGHT - 190))
        y = SCREEN_HEIGHT - 170
        for key in discovered_entries[:4]:
            entry_title, _ = self.entries.get(key, (key, ""))
            surface.blit(font.render(f"• {entry_title}", True, COLOR_TEXT), (30, y))
            y += 22

    def toggle(self):
        self.visible = not self.visible


class InventoryUI:
    def __init__(self):
        self.visible = False
        self.notification = ""
        self.notification_timer = 0

    def toggle(self):
        self.visible = not self.visible

    def notify(self, message: str):
        self.notification = message
        self.notification_timer = FPS * 2

    def update(self):
        if self.notification_timer > 0:
            self.notification_timer -= 1

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, items: Dict[str, int], notes: Dict[str, str]):
        if self.notification_timer > 0:
            toast = font.render(self.notification, True, COLOR_TEXT)
            surface.blit(toast, (SCREEN_WIDTH - toast.get_width() - 20, SCREEN_HEIGHT - 40))
        if not self.visible:
            return
        overlay = pygame.Surface((280, 220), pygame.SRCALPHA)
        overlay.fill((18, 10, 28, 220))
        surface.blit(overlay, (SCREEN_WIDTH - 300, SCREEN_HEIGHT - 260))
        surface.blit(font.render("Inventory", True, COLOR_TEXT), (SCREEN_WIDTH - 290, SCREEN_HEIGHT - 250))
        if not items:
            surface.blit(font.render("(empty)", True, COLOR_TEXT), (SCREEN_WIDTH - 290, SCREEN_HEIGHT - 220))
            return
        y = SCREEN_HEIGHT - 220
        for item_id, amount in list(items.items())[:5]:
            note = notes.get(item_id, "")
            line = f"• {item_id.replace('_', ' ').title()} x{amount}"
            surface.blit(font.render(line, True, COLOR_TEXT), (SCREEN_WIDTH - 290, y))
            y += 22
            if note:
                snippet = note[:36] + ("..." if len(note) > 36 else "")
                surface.blit(font.render(snippet, True, (170, 160, 200)), (SCREEN_WIDTH - 280, y))
                y += 20


class ReputationPanel:
    def __init__(self):
        self.visible = False
        self.toast: Optional[Tuple[str, int]] = None

    def toggle(self):
        self.visible = not self.visible

    def notify_change(self, faction: str, amount: int, value: int):
        label = faction.replace("_", " ").title()
        prefix = "+" if amount >= 0 else ""
        message = f"{label} reputation {prefix}{amount} → {value}"
        self.toast = (message, FPS * 2)

    def update(self):
        if not self.toast:
            return
        message, timer = self.toast
        timer -= 1
        if timer <= 0:
            self.toast = None
        else:
            self.toast = (message, timer)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, reputations: Dict[str, int]):
        if self.toast:
            message, timer = self.toast
            alpha = clamp(timer / (FPS * 2), 0, 1)
            overlay = pygame.Surface((SCREEN_WIDTH, 32), pygame.SRCALPHA)
            overlay.fill((28, 16, 40, int(180 * alpha)))
            surface.blit(overlay, (0, SCREEN_HEIGHT - 120))
            text = font.render(message, True, COLOR_TEXT)
            surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT - 112))
        if not self.visible:
            return
        panel = pygame.Surface((260, 160), pygame.SRCALPHA)
        panel.fill((18, 14, 30, 220))
        surface.blit(panel, (20, 40))
        title = font.render("Faction Standing", True, COLOR_TEXT)
        surface.blit(title, (30, 50))
        y = 80
        for faction, value in reputations.items():
            label = faction.replace("_", " ").title()
            line = font.render(f"{label}: {value}", True, COLOR_TEXT)
            surface.blit(line, (30, y))
            y += 24
        hint = font.render("R to close", True, COLOR_TEXT)
        surface.blit(hint, (30, 40 + panel.get_height() - 28))


class MapOverlay:
    def __init__(self, zones: Dict[str, Zone]):
        self.visible = False
        self.zone_positions: Dict[str, Tuple[int, int]] = {}
        self.connections: Dict[str, List[str]] = {}
        self.visited: Dict[str, bool] = {}
        self.current_zone: Optional[str] = None
        self._build_layout(zones)

    def _build_layout(self, zones: Dict[str, Zone]):
        ordered = sorted(zones.keys())
        for index, zone in enumerate(ordered):
            col = index % 2
            row = index // 2
            x = SCREEN_WIDTH // 2 - 160 + col * 160
            y = SCREEN_HEIGHT // 2 - 140 + row * 70
            self.zone_positions[zone] = (x, y)
            self.connections.setdefault(zone, [])
        for zone_name, zone in zones.items():
            neighbours = set()
            for portal in zone.portals:
                neighbours.add(portal.target_zone)
            self.connections[zone_name] = sorted(neighbours)

    def toggle(self):
        self.visible = not self.visible

    def mark_visited(self, zone: str):
        self.visited[zone] = True

    def mark_current(self, zone: str):
        self.current_zone = zone

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if not self.visible:
            return
        backdrop = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        backdrop.fill((8, 6, 14, 220))
        surface.blit(backdrop, (0, 0))
        title = font.render("Mainframe Cartography", True, COLOR_TEXT)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 60))
        drawn_links = set()
        for zone, neighbours in self.connections.items():
            start = self.zone_positions.get(zone)
            if not start:
                continue
            for neighbour in neighbours:
                end = self.zone_positions.get(neighbour)
                if not end:
                    continue
                key = tuple(sorted((zone, neighbour)))
                if key in drawn_links:
                    continue
                pygame.draw.line(surface, (80, 90, 140), (start[0] + 30, start[1] + 15), (end[0] + 30, end[1] + 15), 2)
                drawn_links.add(key)
        for zone, (x, y) in self.zone_positions.items():
            rect = pygame.Rect(x, y, 120, 40)
            visited = self.visited.get(zone, False)
            color = (70, 90, 140)
            if zone == self.current_zone:
                color = (140, 200, 255)
            elif visited:
                color = (110, 170, 150)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (20, 20, 40), rect, 2)
            label = font.render(zone.replace('_', ' ').title(), True, COLOR_TEXT)
            surface.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))
        hint = font.render("TAB to close map", True, COLOR_TEXT)
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 60))


class AchievementTracker:
    def __init__(self):
        self.definitions: Dict[str, Tuple[str, str]] = {}
        self.unlocked: Dict[str, bool] = {}
        self.notifications: List[Tuple[str, int]] = []

    def register(self, achievement_id: str, title: str, description: str):
        self.definitions[achievement_id] = (title, description)

    def unlock(self, achievement_id: str) -> bool:
        if self.unlocked.get(achievement_id):
            return False
        if achievement_id not in self.definitions:
            return False
        self.unlocked[achievement_id] = True
        title, description = self.definitions[achievement_id]
        message = f"Achievement: {title} - {description}"
        self.notifications.append((message, FPS * 3))
        return True

    def update(self):
        if not self.notifications:
            return
        message, timer = self.notifications[0]
        timer -= 1
        if timer <= 0:
            self.notifications.pop(0)
        else:
            self.notifications[0] = (message, timer)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if not self.notifications:
            return
        message, timer = self.notifications[0]
        alpha = clamp(timer / (FPS * 3), 0, 1)
        overlay = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
        overlay.fill((30, 16, 40, int(200 * alpha)))
        surface.blit(overlay, (0, 100))
        text = font.render(message, True, COLOR_TEXT)
        surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 110))

class SoundscapeManager:
    def __init__(self):
        self.enabled = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.current_zone: Optional[str] = None
        self.channel: Optional[pygame.mixer.Channel] = None
        self._init_audio()

    def _init_audio(self):
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.enabled = True
            self.channel = pygame.mixer.Channel(0)
        except pygame.error:
            self.enabled = False

    def register_soundscape(self, soundscape: Soundscape):
        if not self.enabled or soundscape.zone in self.sounds:
            return
        tone = self._create_tone(soundscape.tone, soundscape.modulation)
        tone.set_volume(soundscape.volume)
        self.sounds[soundscape.zone] = tone

    def _create_tone(self, frequency: float, modulation: float) -> pygame.mixer.Sound:
        sample_rate = 22050
        duration = 1.5
        sample_count = int(sample_rate * duration)
        samples = array("h")
        for i in range(sample_count):
            base = math.sin(2 * math.pi * frequency * i / sample_rate)
            wobble = math.sin(2 * math.pi * modulation * i / sample_rate) if modulation else 0
            value = int(22000 * (0.7 * base + 0.3 * wobble))
            samples.append(value)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play_zone(self, zone: str):
        if not self.enabled:
            return
        if zone == self.current_zone:
            return
        if self.channel:
            self.channel.stop()
        sound = self.sounds.get(zone)
        if sound:
            self.channel.play(sound, loops=-1)
            self.current_zone = zone

    def stop(self):
        if self.channel:
            self.channel.stop()
        self.current_zone = None


class DialogueBox:
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.text = ""
        self.visible = False
        self.timer = 0

    def show(self, text: str, duration: int = FPS * 4):
        self.text = text
        self.visible = True
        self.timer = duration

    def update(self):
        if not self.visible:
            return
        self.timer -= 1
        if self.timer <= 0:
            self.visible = False

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return
        box_rect = pygame.Rect(40, SCREEN_HEIGHT - 120, SCREEN_WIDTH - 80, 80)
        pygame.draw.rect(surface, COLOR_DIALOGUE_BG, box_rect)
        pygame.draw.rect(surface, COLOR_DIALOGUE_BORDER, box_rect, 2)
        wrapped = wrap_text(self.text, self.font, box_rect.width - 20)
        y = box_rect.top + 15
        for line in wrapped:
            surface.blit(self.font.render(line, True, COLOR_TEXT), (box_rect.left + 10, y))
            y += self.font.get_linesize()


@dataclass
class CinematicMoment:
    id: str
    lines: List[str]
    requires_flag: Optional[str] = None
    forbidden_flag: Optional[str] = None


class CinematicPlayer:
    def __init__(self, font: pygame.font.Font, heading_font: pygame.font.Font):
        self.font = font
        self.heading_font = heading_font
        self.active = False
        self.lines: List[str] = []
        self.index = 0
        self.timer = 0

    def start(self, lines: List[str]):
        if not lines:
            return
        self.lines = lines
        self.index = 0
        self.timer = FPS * 3
        self.active = True

    def update(self):
        if not self.active:
            return
        self.timer -= 1
        if self.timer <= 0:
            self.advance()

    def advance(self):
        if not self.active:
            return
        self.index += 1
        if self.index >= len(self.lines):
            self.active = False
            self.lines = []
            return
        self.timer = FPS * 3

    def draw(self, surface: pygame.Surface):
        if not self.active or not self.lines:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((8, 4, 12, 220))
        surface.blit(overlay, (0, 0))
        heading = self.heading_font.render("Cinematic Feed", True, COLOR_TEXT)
        surface.blit(heading, (SCREEN_WIDTH // 2 - heading.get_width() // 2, 120))
        text_lines = wrap_text(self.lines[self.index], self.font, SCREEN_WIDTH - 120)
        y = 180
        for line in text_lines:
            surface.blit(self.font.render(line, True, COLOR_TEXT), (60, y))
            y += self.font.get_linesize() + 4
        prompt = self.font.render("Press SPACE to continue", True, COLOR_TEXT)
        surface.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, SCREEN_HEIGHT - 140))


class SlashEffect(pygame.sprite.Sprite):
    def __init__(self, center: Tuple[int, int], facing: int):
        super().__init__()
        self.image = pygame.Surface((SLASH_REACH, 20), pygame.SRCALPHA)
        pygame.draw.rect(self.image, COLOR_SLASH, (0, 0, SLASH_REACH, 20))
        if facing < 0:
            self.image = pygame.transform.flip(self.image, True, False)
        self.rect = self.image.get_rect(center=center)
        self.timer = SLASH_TIME

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self, position: Tuple[int, int]):
        super().__init__()
        self.image = pygame.Surface((18, 20))
        self.image.fill(COLOR_PLAYER)
        self.rect = self.image.get_rect(topleft=position)
        self.velocity = pygame.Vector2(0, 0)
        self.on_ground = False
        self.facing = 1
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_cooldown_max = BASE_DASH_COOLDOWN
        self.slash_timer = 0

    def handle_input(self, keys: pygame.key.ScancodeWrapper):
        move_dir = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_dir -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_dir += 1
        if move_dir:
            self.facing = move_dir
        desired_speed = move_dir * PLAYER_SPEED

        if self.dash_timer > 0:
            desired_speed = self.facing * PLAYER_DASH_SPEED
            self.dash_timer -= 1
        elif self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        elif keys[pygame.K_LSHIFT] and self.dash_cooldown == 0:
            self.dash_timer = PLAYER_DASH_TIME
            self.dash_cooldown = self.dash_cooldown_max

        self.velocity.x = desired_speed

        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.velocity.y = -PLAYER_JUMP
            self.on_ground = False
        else:
            self.velocity.y += GRAVITY
            self.velocity.y = clamp(self.velocity.y, -PLAYER_JUMP, 12)

    def update(self, platforms: List[Platform]):
        self.rect.x += int(self.velocity.x)
        self._handle_collisions(platforms, 0)
        self.rect.y += int(self.velocity.y)
        self.on_ground = False
        self._handle_collisions(platforms, 1)
        if self.slash_timer > 0:
            self.slash_timer -= 1

    def _handle_collisions(self, platforms: List[Platform], axis: int):
        for platform in platforms:
            if platform.kind != "solid":
                continue
            if self.rect.colliderect(platform.rect):
                if axis == 0:
                    if self.velocity.x > 0:
                        self.rect.right = platform.rect.left
                    else:
                        self.rect.left = platform.rect.right
                    self.velocity.x = 0
                else:
                    if self.velocity.y > 0:
                        self.rect.bottom = platform.rect.top
                        self.on_ground = True
                    else:
                        self.rect.top = platform.rect.bottom
                    self.velocity.y = 0

    def perform_slash(self, slash_group: pygame.sprite.Group):
        if self.slash_timer > 0:
            return
        self.slash_timer = SLASH_TIME
        center = (self.rect.centerx + self.facing * (self.rect.width // 2 + SLASH_REACH // 2),
                  self.rect.centery)
        slash_group.add(SlashEffect(center, self.facing))


class Projectile(pygame.sprite.Sprite):
    def __init__(self, position: Tuple[int, int], velocity: pygame.Vector2):
        super().__init__()
        self.image = pygame.Surface((8, 8))
        self.image.fill((255, 160, 80))
        self.rect = self.image.get_rect(center=position)
        self.velocity = velocity

    def update(self):
        self.rect.centerx += int(self.velocity.x)
        self.rect.centery += int(self.velocity.y)
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()


class CorruptedProgram(pygame.sprite.Sprite):
    """A flexible enemy actor that supports multiple archetypes."""

    def __init__(self, rect: pygame.Rect, archetype: str, patrol_range: Tuple[int, int]):
        super().__init__()
        self.rect = rect.copy()
        self.image = pygame.Surface(self.rect.size)
        self.image.fill((220, 90, 200))
        self.archetype = archetype
        self.direction = 1
        self.speed = 1.6
        self.patrol_min, self.patrol_max = patrol_range
        self.velocity = pygame.Vector2(0, 0)
        self.cooldown = random.randint(45, 120)

    def update(self, projectiles: pygame.sprite.Group, player: Player):
        if self.archetype in {"slicer", "lurker", "scout"}:
            self.rect.x += self.direction * self.speed
            if self.rect.left <= self.patrol_min or self.rect.right >= self.patrol_max:
                self.direction *= -1
        elif self.archetype in {"turret", "admin_turret"}:
            self.cooldown -= 1
            if self.cooldown <= 0:
                direction = pygame.Vector2(player.rect.center) - pygame.Vector2(self.rect.center)
                if direction.length_squared() > 0:
                    direction = direction.normalize() * 3.5
                    projectiles.add(Projectile(self.rect.center, direction))
                self.cooldown = random.randint(90, 140)
        elif self.archetype in {"hopper", "defragger"}:
            if self.rect.bottom >= player.rect.bottom:
                self.velocity.y = -6
            self.velocity.y += GRAVITY * 1.2
            self.rect.y += int(self.velocity.y)
            if self.rect.bottom > SCREEN_HEIGHT - 80:
                self.rect.bottom = SCREEN_HEIGHT - 80
                self.velocity.y = 0
        elif self.archetype == "phase_wisp":
            self.cooldown -= 1
            if self.cooldown <= 0:
                self.rect.x += random.choice([-40, 40])
                self.rect.y += random.choice([-40, 40])
                self.cooldown = random.randint(60, 120)
                self.rect.clamp_ip(pygame.Rect(80, 80, SCREEN_WIDTH - 160, SCREEN_HEIGHT - 160))

        # Update sprite color based on archetype for visual feedback
        color_lookup = {
            "slicer": (220, 90, 200),
            "lurker": (220, 60, 160),
            "scout": (255, 140, 200),
            "turret": (255, 180, 120),
            "admin_turret": (255, 220, 160),
            "hopper": (180, 255, 140),
            "defragger": (140, 220, 255),
            "phase_wisp": (180, 140, 255),
        }
        self.image.fill(color_lookup.get(self.archetype, (220, 90, 200)))


class BossEncounter:
    def __init__(self, name: str, arena: pygame.Rect, health: int, phases: int, pattern: str = "radial"):
        self.name = name
        self.arena = arena
        self.health = health
        self.max_health = health
        self.phases = phases
        self.active = False
        self.timer = 0
        self.phase_timer = 0
        self.pattern = pattern

    def start(self):
        self.active = True
        self.timer = 0
        self.phase_timer = 0

    def current_phase(self) -> int:
        if self.phases <= 1:
            return 0
        phase_size = max(1, self.max_health // self.phases)
        lost = max(0, self.max_health - self.health)
        return min(self.phases - 1, lost // phase_size)

    def update(self, projectiles: pygame.sprite.Group, player_rect: Optional[pygame.Rect] = None):
        if not self.active:
            return
        self.timer += 1
        self.phase_timer += 1
        phase = self.current_phase()

        if self.pattern in {"radial", "spiral"}:
            interval = max(24, 60 - phase * 8)
            if self.timer % interval == 0:
                offset = (self.timer // interval) * (12 if self.pattern == "spiral" else 0)
                step = max(12, 30 - phase * 4)
                speed = 3.6 + phase * 0.6
                for angle in range(0, 360, step):
                    rad = math.radians(angle + offset)
                    velocity = pygame.Vector2(math.cos(rad), math.sin(rad)) * speed
                    projectiles.add(Projectile(self.arena.center, velocity))

        if self.pattern in {"lance", "cascade"} and player_rect:
            interval = max(45, 90 - phase * 10)
            if self.timer % interval == interval // 2:
                direction = pygame.Vector2(player_rect.center) - pygame.Vector2(self.arena.center)
                if direction.length_squared() == 0:
                    direction = pygame.Vector2(1, 0)
                direction = direction.normalize()
                speed = 4.2 + phase * 0.8
                projectiles.add(Projectile(self.arena.center, direction * speed))
                if self.pattern == "cascade":
                    for angle in (-18, 18):
                        projectiles.add(
                            Projectile(
                                self.arena.center,
                                direction.rotate(angle) * (speed * 0.9),
                            )
                        )

        if self.pattern == "halo":
            interval = max(35, 80 - phase * 8)
            if self.timer % interval == 0:
                count = 10 + phase * 2
                radius = min(self.arena.width, self.arena.height) * 0.35
                base_angle = (self.timer // interval) * 14
                speed = 3.0 + phase * 0.45
                center = pygame.Vector2(self.arena.center)
                for index in range(count):
                    angle = base_angle + (360 / count) * index
                    direction = pygame.Vector2(1, 0).rotate(angle)
                    origin = center + direction * radius
                    projectiles.add(Projectile(origin, direction * speed))

        if self.pattern == "pulse":
            interval = max(35, 90 - phase * 10)
            if self.timer % interval == 0:
                step = max(18, 48 - phase * 4)
                speed = 3.2 + phase * 0.5
                offset_state = (self.timer // interval) % 2
                radius = min(self.arena.width, self.arena.height) * 0.2
                for angle in range(0, 360, step):
                    rad = math.radians(angle)
                    direction = pygame.Vector2(math.cos(rad), math.sin(rad))
                    origin = pygame.Vector2(self.arena.center)
                    if offset_state:
                        origin += direction * radius
                    projectiles.add(Projectile(origin, direction * speed))

        if self.pattern == "storm":
            interval = max(50, 110 - phase * 15)
            if self.timer % interval == 0:
                edges = [
                    (random.randint(self.arena.left, self.arena.right), self.arena.top, pygame.Vector2(0, 1)),
                    (random.randint(self.arena.left, self.arena.right), self.arena.bottom, pygame.Vector2(0, -1)),
                    (self.arena.left, random.randint(self.arena.top, self.arena.bottom), pygame.Vector2(1, 0)),
                    (self.arena.right, random.randint(self.arena.top, self.arena.bottom), pygame.Vector2(-1, 0)),
                ]
                speed = 3.8 + phase * 0.5
                for position in random.sample(edges, k=2):
                    origin = (position[0], position[1])
                    velocity = position[2] * speed
                    projectiles.add(Projectile(origin, velocity))

        if self.pattern == "meteor":
            interval = max(40, 90 - phase * 12)
            if self.timer % interval == 0:
                columns = max(3, 3 + phase)
                spacing = self.arena.width // columns
                for index in range(columns):
                    x = self.arena.left + spacing * index + spacing // 2
                    speed = 4.2 + phase * 0.6
                    projectiles.add(Projectile((x, self.arena.top), pygame.Vector2(0, speed)))

        if self.pattern == "rift":
            interval = max(45, 105 - phase * 12)
            if self.timer % interval == 0:
                anchors = 2 + phase
                speed = 3.4 + phase * 0.6
                for _ in range(anchors):
                    anchor = pygame.Vector2(
                        random.randint(self.arena.left + 40, self.arena.right - 40),
                        random.randint(self.arena.top + 40, self.arena.bottom - 40),
                    )
                    base_angle = random.randint(0, 360)
                    for offset in (-30, 0, 30):
                        direction = pygame.Vector2(1, 0).rotate(base_angle + offset)
                        projectiles.add(Projectile(anchor, direction * speed))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if not self.active:
            return
        bar_width = 300
        ratio = max(0, self.health) / self.max_health
        pygame.draw.rect(surface, (40, 12, 32), (SCREEN_WIDTH // 2 - 150, 40, bar_width, 18))
        pygame.draw.rect(surface, (255, 60, 120), (SCREEN_WIDTH // 2 - 150, 40, int(bar_width * ratio), 18))
        label = font.render(self.name, True, COLOR_TEXT)
        surface.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, 12))


@dataclass
class Zone:
    name: str
    platforms: List[Platform] = field(default_factory=list)
    portals: List[Portal] = field(default_factory=list)
    npcs: List[NPC] = field(default_factory=list)
    collectibles: List[Collectible] = field(default_factory=list)
    items: List[ItemDrop] = field(default_factory=list)
    pickups: List[AbilityPickup] = field(default_factory=list)
    enemies: List[CorruptedProgram] = field(default_factory=list)
    bosses: List[BossEncounter] = field(default_factory=list)
    upgrade_terminals: List[UpgradeTerminal] = field(default_factory=list)
    save_stations: List[SaveStation] = field(default_factory=list)
    events: List[StoryEvent] = field(default_factory=list)
    ambience: str = ""
    description: str = ""

    def draw(self, surface: pygame.Surface):
        surface.fill(ZONE_SKIES.get(self.name, COLOR_BG))
        for platform in self.platforms:
            color = COLOR_PLATFORM if platform.kind == "solid" else (255, 80, 80)
            platform.draw(surface, color)
        for collectible in self.collectibles:
            collectible.draw(surface)
        for item in self.items:
            item.draw(surface)
        for pickup in self.pickups:
            pickup.draw(surface)
        for terminal in self.upgrade_terminals:
            terminal.draw(surface)
        for station in self.save_stations:
            station.draw(surface)
        for npc in self.npcs:
            npc.draw(surface)
        for enemy in self.enemies:
            surface.blit(enemy.image, enemy.rect)


# ---------------------------------------------------------------------------
# Debug mini-game
# ---------------------------------------------------------------------------


class DebugArena:
    def __init__(self, player: Player):
        self.player = player
        self.timer = FPS * 8
        self.packets = pygame.sprite.Group()
        self.bounds = pygame.Rect(100, 80, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 180)
        self.finished = False
        self.success = False

    def update(self, keys: pygame.key.ScancodeWrapper):
        speed = 4
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if move.length_squared() > 0:
            move = move.normalize() * speed
        self.player.rect.center += move
        self.player.rect.clamp_ip(self.bounds)

        if self.timer % 20 == 0:
            side = random.choice(["top", "bottom", "left", "right"])
            if side in ("top", "bottom"):
                x = random.randint(self.bounds.left, self.bounds.right)
                y = self.bounds.top if side == "top" else self.bounds.bottom
                direction = pygame.Vector2(random.uniform(-1, 1), 1 if side == "top" else -1)
            else:
                y = random.randint(self.bounds.top, self.bounds.bottom)
                x = self.bounds.left if side == "left" else self.bounds.right
                direction = pygame.Vector2(1 if side == "left" else -1, random.uniform(-1, 1))
            direction = direction.normalize() * 4.2
            self.packets.add(Projectile((x, y), direction))

        self.packets.update()
        if pygame.sprite.spritecollideany(self.player, self.packets):
            self.finished = True
            self.success = False
        else:
            self.timer -= 1
            if self.timer <= 0:
                self.finished = True
                self.success = True

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((10, 0, 20, 220))
        surface.blit(overlay, (0, 0))
        pygame.draw.rect(surface, (100, 0, 140), self.bounds, 2)
        message = font.render("DEBUG MODE: Dodge corrupted packets", True, COLOR_TEXT)
        surface.blit(message, (SCREEN_WIDTH // 2 - message.get_width() // 2, 30))
        timer_text = font.render(f"Integrity: {self.timer // FPS}s", True, COLOR_TEXT)
        surface.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 60))
        self.packets.draw(surface)
        surface.blit(self.player.image, self.player.rect)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def wrap_text(text: str, font: pygame.font.Font, width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= width:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Game assembly
# ---------------------------------------------------------------------------


def build_zones() -> Dict[str, Zone]:
    zones: Dict[str, Zone] = {}

    def floor_platform(height: int = 60):
        return Platform(pygame.Rect(0, SCREEN_HEIGHT - height, SCREEN_WIDTH, height))

    # Kernel Nexus - safe hub
    zones["kernel_nexus"] = Zone(
        name="kernel_nexus",
        platforms=[
            floor_platform(),
            Platform(pygame.Rect(120, 420, 160, 16)),
            Platform(pygame.Rect(420, 360, 200, 16)),
        ],
        portals=[
            Portal(pygame.Rect(40, 340, 60, 120), "archive", (80, 480), None, "Archive Conduit"),
            Portal(pygame.Rect(700, 320, 60, 140), "processing_core", (100, 480), None, "Processing Core"),
            Portal(pygame.Rect(360, 240, 60, 120), "memory_garden", (60, 460), "data_hook", "Memory Garden"),
            Portal(pygame.Rect(560, 240, 60, 120), "mirror_rift", (100, 500), "phase_shift", "Mirror Rift"),
            Portal(pygame.Rect(370, 520, 80, 60), "deep_storage", (120, 480), "phase_shift", "Deep Storage"),
            Portal(pygame.Rect(640, 520, 60, 60), "signal_sea", (120, 520), "data_hook", "Signal Sea"),
            Portal(pygame.Rect(40, 220, 60, 100), "sundown_bazaar", (120, 520), None, "Sundown Bazaar"),
        ],
        npcs=[
            NPC(
                "Archivist", pygame.Rect(220, 380, 24, 32),
                [
                    DialogueLine(
                        "...a forgotten data-stream echoes...",
                        None,
                        "restore_archive",
                        None,
                        forbidden_flag="restore_archive_accepted",
                    ),
                    DialogueLine(
                        "The catalogues stir as you listen. Will you recover the lost index?",
                        None,
                        None,
                        None,
                        requires_flag="restore_archive_accepted",
                        forbidden_flag="restore_archive_complete",
                    ),
                    DialogueLine(
                        "Retrieve the lost index from the Archive's upper stacks.",
                        "data_hook",
                        None,
                        None,
                        requires_flag="restore_archive_accepted",
                        forbidden_flag="restore_archive_complete",
                    ),
                    DialogueLine(
                        "With the index restored, the flows calm. Thank you.",
                        None,
                        None,
                        "restore_archive",
                        requires_flag="restore_archive_accepted",
                    ),
                    DialogueLine(
                        "Stay awhile, Echo. The hub remembers your kindness.",
                        None,
                        None,
                        None,
                        requires_flag="restore_archive_complete",
                    ),
                ],
            ),
            NPC(
                "Patch Vendor", pygame.Rect(480, 320, 24, 32),
                [
                    DialogueLine(
                        "Collect data fragments and I'll reinforce your kernel.",
                        forbidden_flag="vendor_introduced",
                        set_flag="vendor_introduced",
                    ),
                    DialogueLine(
                        "Your corruption is climbing. Debug more, slice less.",
                        None,
                        None,
                        None,
                        requires_flag="vendor_introduced",
                    ),
                    DialogueLine(
                        "Bring me coolant shards and I'll cut minutes off your dash cooldown.",
                        None,
                        None,
                        None,
                        requires_flag="stabilize_core_complete",
                    ),
                    DialogueLine(
                        "Archive back online? Good. I can finally catalog my wares again.",
                        None,
                        None,
                        None,
                        requires_flag="restore_archive_complete",
                    ),
                ],
            ),
            NPC(
                "Mediator", pygame.Rect(560, 320, 24, 32),
                [
                    DialogueLine(
                        "Factions monitor your every move. Press R to review your standings.",
                        forbidden_flag="mediator_met",
                        set_flag="mediator_met",
                    ),
                    DialogueLine(
                        "Caretakers adore debug work; the rebellion cheers decisive strikes.",
                        None,
                        None,
                        None,
                        requires_flag="mediator_met",
                    ),
                    DialogueLine(
                        "Keep everyone satisfied and you'll broker true consensus across the Mainframe.",
                        None,
                        None,
                        None,
                        requires_flag="consensus_brokered",
                    ),
                ],
            ),
        ],
        upgrade_terminals=[
            UpgradeTerminal(pygame.Rect(320, 500, 36, 36), "heart_module", 5, "Expand kernel integrity by +1."),
            UpgradeTerminal(pygame.Rect(520, 500, 36, 36), "debug_matrix", 3, "Purge 10 corruption instantly."),
        ],
        items=[
            ItemDrop(
                pygame.Rect(140, 460, 18, 18),
                "patch_kit",
                "Patch Kit",
                "A portable integrity repair subroutine.",
            ),
        ],
        save_stations=[
            SaveStation(pygame.Rect(260, 520, 44, 44), "Kernel Hearth", "Core routines stabilized.", (240, 500)),
        ],
        ambience="Soft pulses of code ripple through the hub.",
        description="The heart of the Mainframe. Safe to plan and upgrade.",
    )

    # Archive Zone
    zones["archive"] = Zone(
        name="archive",
        platforms=[
            floor_platform(),
            Platform(pygame.Rect(120, 500, 140, 16)),
            Platform(pygame.Rect(320, 430, 120, 16)),
            Platform(pygame.Rect(520, 360, 140, 16)),
            Platform(pygame.Rect(200, 300, 120, 16)),
            Platform(pygame.Rect(260, 470, 100, 12), "hazard"),
        ],
        portals=[Portal(pygame.Rect(20, 320, 50, 120), "kernel_nexus", (640, 420), None, "Return to Nexus")],
        npcs=[
            NPC(
                "Index Shade", pygame.Rect(540, 320, 24, 30),
                [
                    DialogueLine("I safeguarded the knowledge once. Debug me... please."),
                ],
                friendly=False,
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(340, 390, 16, 16),
                "Lore Fragment A",
                "A log about the Mainframe's fall.",
                lore_id="fragment_a",
            ),
            Collectible(pygame.Rect(560, 320, 16, 16), "Corrupted Index", "A data key the Archivist needs."),
        ],
        items=[
            ItemDrop(
                pygame.Rect(180, 520, 18, 18),
                "patch_kit",
                "Patch Kit",
                "Restores integrity when applied.",
            ),
            ItemDrop(
                pygame.Rect(460, 340, 18, 18),
                "signal_token",
                "Signal Token",
                "A marker that unlocks codex commentary.",
            ),
        ],
        pickups=[AbilityPickup(pygame.Rect(200, 260, 20, 20), "data_hook", "Unlocks grappling to marked ports."),],
        enemies=[
            CorruptedProgram(pygame.Rect(140, 480, 26, 24), "slicer", (120, 280)),
            CorruptedProgram(pygame.Rect(360, 410, 26, 24), "turret", (320, 440)),
            CorruptedProgram(pygame.Rect(540, 340, 26, 24), "lurker", (520, 680)),
        ],
        bosses=[BossEncounter("Guardian of Forgotten Code", pygame.Rect(160, 260, 480, 260), 40, 2)],
        save_stations=[
            SaveStation(pygame.Rect(80, 520, 40, 40), "Archive Anchor", "Index sync complete.", (100, 500)),
        ],
        ambience="Dusty data motes drift between towering code stacks.",
        description="Lore-heavy zone with vertical navigation and data shades.",
    )

    # Processing Core
    zones["processing_core"] = Zone(
        name="processing_core",
        platforms=[
            floor_platform(),
            Platform(pygame.Rect(160, 520, 180, 16)),
            Platform(pygame.Rect(400, 470, 120, 16)),
            Platform(pygame.Rect(580, 420, 160, 16)),
            Platform(pygame.Rect(360, 330, 100, 16)),
            Platform(pygame.Rect(260, 560, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(40, 340, 60, 120), "kernel_nexus", (660, 420), None, "Return to Nexus"),
            Portal(pygame.Rect(720, 320, 60, 120), "deep_storage", (80, 460), "phase_shift", "To Deep Storage"),
            Portal(pygame.Rect(360, 260, 60, 120), "quantum_forge", (80, 500), "codebreaker", "Quantum Forge"),
        ],
        npcs=[
            NPC(
                "Engineer", pygame.Rect(420, 430, 24, 30),
                [
                    DialogueLine(
                        "The surges are lethal. You'll need Phase Shift.",
                        forbidden_flag="engineer_met",
                        set_flag="engineer_met",
                    ),
                    DialogueLine(
                        "Take this blueprint once you stabilize the conduits.",
                        None,
                        "stabilize_core",
                    ),
                    DialogueLine(
                        "Seal the leaking vents and the conduit heart will calm.",
                        None,
                        None,
                        None,
                        requires_flag="stabilize_core_accepted",
                        forbidden_flag="stabilize_core_complete",
                    ),
                    DialogueLine(
                        "Power stabilized? Excellent. Here's a coolant rerouter for your dash.",
                        None,
                        None,
                        "stabilize_core",
                        requires_flag="item_coolant_shard",
                    ),
                    DialogueLine(
                        "Those coolant lines should keep your dash crisp even under pressure.",
                        None,
                        None,
                        None,
                        requires_flag="stabilize_core_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(620, 380, 16, 16),
                "Lore Fragment B",
                "Notes about the Admin wars.",
                lore_id="fragment_b",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(300, 540, 18, 18),
                "coolant_shard",
                "Coolant Shard",
                "Temporarily reduces Overclock cooldown when resting.",
            ),
        ],
        pickups=[AbilityPickup(pygame.Rect(200, 480, 20, 20), "phase_shift", "Slip through firewalls temporarily."),],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "hopper", (160, 340)),
            CorruptedProgram(pygame.Rect(420, 450, 26, 24), "turret", (400, 520)),
            CorruptedProgram(pygame.Rect(620, 400, 26, 24), "admin_turret", (580, 720)),
        ],
        bosses=[BossEncounter("Overclocked Administrator", pygame.Rect(140, 260, 520, 260), 50, 3, pattern="lance")],
        upgrade_terminals=[UpgradeTerminal(pygame.Rect(540, 500, 36, 36), "dash_optimizer", 6, "Reduce dash cooldown."),],
        save_stations=[
            SaveStation(pygame.Rect(80, 520, 42, 42), "Cooling Node", "Systems recalibrated.", (110, 500)),
        ],
        ambience="Pulsing conduits and arcing energy hazards.",
        description="Industrial gauntlet focused on hazards and timing.",
    )

    # Quantum Forge
    zones["quantum_forge"] = Zone(
        name="quantum_forge",
        platforms=[
            floor_platform(),
            Platform(pygame.Rect(200, 520, 160, 16)),
            Platform(pygame.Rect(420, 460, 160, 16)),
            Platform(pygame.Rect(620, 400, 140, 16)),
            Platform(pygame.Rect(320, 340, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 120), "processing_core", (640, 420), None, "Return to Core"),
            Portal(pygame.Rect(760, 320, 40, 120), "core_ascendant", (140, 520), "codebreaker", "To Ascendant"),
        ],
        npcs=[
            NPC(
                "Forge Warden",
                pygame.Rect(420, 420, 24, 32),
                [
                    DialogueLine(
                        "The quantum anvils fell silent when the rebellion fractured.",
                        forbidden_flag="forge_warden_met",
                        set_flag="forge_warden_met",
                    ),
                    DialogueLine(
                        "Will you relight the forges?",
                        None,
                        "ignite_forge",
                        None,
                        forbidden_flag="ignite_forge_accepted",
                    ),
                    DialogueLine(
                        "Stoke the three furnace nodes and bring me their embers.",
                        None,
                        None,
                        None,
                        requires_flag="ignite_forge_accepted",
                        forbidden_flag="ignite_forge_complete",
                    ),
                    DialogueLine(
                        "The forge roars again. Take this core overclock schematic.",
                        None,
                        None,
                        "ignite_forge",
                        requires_flag="collected_forge_ember",
                    ),
                    DialogueLine(
                        "Keep the heat alive, Echo. The rebellion needs tempered blades.",
                        None,
                        None,
                        None,
                        requires_flag="ignite_forge_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(560, 360, 16, 16),
                "Lore Fragment I",
                "War-smith notes detail defensive code plating.",
                lore_id="fragment_i",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(320, 500, 18, 18),
                "glitchling_core",
                "Dormant Glitchling Core",
                "Rekindles a loyal forge scout companion.",
            ),
            ItemDrop(
                pygame.Rect(200, 540, 18, 18),
                "furnace_ember",
                "Furnace Ember",
                "One of the flames needed to restart the forge.",
            ),
            ItemDrop(
                pygame.Rect(460, 480, 18, 18),
                "furnace_ember",
                "Furnace Ember",
                "Heat captured from the eastern crucible.",
            ),
            ItemDrop(
                pygame.Rect(620, 420, 18, 18),
                "furnace_ember",
                "Furnace Ember",
                "A final spark buried within slag.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "slicer", (180, 320)),
            CorruptedProgram(pygame.Rect(440, 440, 26, 24), "turret", (400, 520)),
            CorruptedProgram(pygame.Rect(640, 380, 26, 24), "hopper", (600, 760)),
        ],
        bosses=[BossEncounter("Crucible Golem", pygame.Rect(160, 240, 520, 280), 60, 3, pattern="cascade")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(520, 520, 36, 36),
                "core_overclock",
                7,
                "Unlock a refined overclock conduit.",
            ),
        ],
        save_stations=[
            SaveStation(pygame.Rect(160, 540, 42, 42), "Forge Hearth", "Molten data warms your core.", (180, 520)),
        ],
        ambience="Sparks rain across dormant assembly lines.",
        description="Mid-game arena with hazard pacing and forge quests.",
    )

    # Memory Garden
    zones["memory_garden"] = Zone(
        name="memory_garden",
        platforms=[
            floor_platform(),
            Platform(pygame.Rect(180, 500, 140, 16)),
            Platform(pygame.Rect(360, 440, 160, 16)),
            Platform(pygame.Rect(540, 380, 140, 16)),
            Platform(pygame.Rect(240, 320, 120, 16)),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 120), "kernel_nexus", (380, 300), None, "Return to Nexus"),
            Portal(pygame.Rect(740, 320, 40, 120), "signal_sea", (100, 520), "data_hook", "To Signal Sea"),
            Portal(pygame.Rect(360, 260, 60, 120), "nocturne_array", (100, 520), "phase_shift", "Nocturne Array"),
        ],
        npcs=[
            NPC(
                "Caretaker", pygame.Rect(360, 400, 24, 32),
                [
                    DialogueLine(
                        "Welcome to the gardens... mind the glitches.",
                        forbidden_flag="caretaker_met",
                        set_flag="caretaker_met",
                    ),
                    DialogueLine(
                        "These blooms respond to empathy. Debug the corrupted fauna and they will sing.",
                        None,
                        None,
                        None,
                        requires_flag="caretaker_met",
                        forbidden_flag="garden_blossom_complete",
                    ),
                    DialogueLine(
                        "Use the Data Hook to traverse the floating memories.",
                        "data_hook",
                        "garden_blossom",
                        None,
                        requires_flag="caretaker_met",
                        forbidden_flag="garden_blossom_complete",
                    ),
                    DialogueLine(
                        "The new seed pulses with hope. The garden thanks you.",
                        None,
                        None,
                        "garden_blossom",
                        requires_flag="item_garden_seed",
                    ),
                    DialogueLine(
                        "May the memories guide your path back to the Nexus.",
                        None,
                        None,
                        None,
                        requires_flag="garden_blossom_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(pygame.Rect(420, 400, 16, 16), "Blooming Memory", "Remnant of happier cycles."),
            Collectible(
                pygame.Rect(560, 340, 16, 16),
                "Lore Fragment C",
                "The Mainframe once nurtured creativity.",
                lore_id="fragment_c",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(320, 460, 18, 18),
                "garden_seed",
                "Memory Seed",
                "Planted at stations to enhance healing.",
            ),
        ],
        pickups=[AbilityPickup(pygame.Rect(260, 280, 20, 20), "codebreaker", "Rewrite encrypted terminals."),],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 480, 26, 24), "scout", (180, 320)),
            CorruptedProgram(pygame.Rect(420, 420, 26, 24), "phase_wisp", (360, 500)),
            CorruptedProgram(pygame.Rect(560, 360, 26, 24), "defragger", (520, 660)),
        ],
        bosses=[BossEncounter("Garden Firewall", pygame.Rect(160, 260, 480, 260), 45, 2, pattern="cascade")],
        save_stations=[
            SaveStation(pygame.Rect(120, 520, 42, 42), "Sanctuary Root", "Soothing packets mend your shell.", (140, 500)),
        ],
        ambience="A glitching sanctuary of neon fauna.",
        description="Traversal puzzles with organic visuals and teleporting foes.",
    )

    # Nocturne Array
    zones["nocturne_array"] = Zone(
        name="nocturne_array",
        platforms=[
            floor_platform(70),
            Platform(pygame.Rect(160, 500, 140, 16)),
            Platform(pygame.Rect(360, 440, 160, 16)),
            Platform(pygame.Rect(560, 380, 160, 16)),
            Platform(pygame.Rect(260, 320, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 120), "memory_garden", (580, 300), None, "Return to Garden"),
            Portal(pygame.Rect(740, 320, 40, 140), "signal_sea", (140, 520), "data_hook", "Signal Sea"),
            Portal(pygame.Rect(360, 200, 80, 100), "resonant_expanse", (140, 520), "codebreaker", "Resonant Expanse"),
        ],
        npcs=[
            NPC(
                "Nightwatch",
                pygame.Rect(420, 420, 24, 32),
                [
                    DialogueLine(
                        "We archived the dreams of users long gone.",
                        forbidden_flag="nightwatch_met",
                        set_flag="nightwatch_met",
                    ),
                    DialogueLine(
                        "Bring back the lullabies and the array will awaken.",
                        None,
                        "nightwatch_requiem",
                        None,
                        forbidden_flag="nightwatch_requiem_accepted",
                    ),
                    DialogueLine(
                        "Collect three nocturne orbs and place them upon the pedestals.",
                        None,
                        None,
                        None,
                        requires_flag="nightwatch_requiem_accepted",
                        forbidden_flag="nightwatch_requiem_complete",
                    ),
                    DialogueLine(
                        "The lullaby returns. Let the gardens rest easy tonight.",
                        None,
                        None,
                        "nightwatch_requiem",
                        requires_flag="collected_nocturne_orb",
                    ),
                    DialogueLine(
                        "Stay a moment—the stars shimmer brighter with you here.",
                        None,
                        None,
                        None,
                        requires_flag="nightwatch_requiem_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(360, 360, 16, 16),
                "Lore Fragment J",
                "Songs that lulled corrupted programs into calm cycles.",
                lore_id="fragment_j",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(280, 520, 18, 18),
                "nocturne_orb",
                "Nocturne Orb",
                "Contains harmonies that calm corrupted data.",
            ),
            ItemDrop(
                pygame.Rect(440, 460, 18, 18),
                "nocturne_orb",
                "Nocturne Orb",
                "A resonant tone that guides travelers.",
            ),
            ItemDrop(
                pygame.Rect(600, 400, 18, 18),
                "nocturne_orb",
                "Nocturne Orb",
                "A drifting sphere humming in counterpoint.",
            ),
            ItemDrop(
                pygame.Rect(520, 360, 18, 18),
                "lullaby_sheet",
                "Lullaby Sheet",
                "Sheet music for the Nightwatch's requiem.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 480, 26, 24), "phase_wisp", (180, 320)),
            CorruptedProgram(pygame.Rect(420, 420, 26, 24), "lurker", (360, 520)),
            CorruptedProgram(pygame.Rect(620, 360, 26, 24), "defragger", (560, 720)),
        ],
        bosses=[BossEncounter("Nocturne Choir", pygame.Rect(160, 240, 520, 280), 58, 3, pattern="spiral")],
        upgrade_terminals=[
            UpgradeTerminal(pygame.Rect(520, 520, 36, 36), "debug_matrix", 6, "Enhance debug stability."),
        ],
        save_stations=[
            SaveStation(pygame.Rect(160, 540, 42, 42), "Dream Locus", "Soft melodies mend your shell.", (180, 520)),
        ],
        ambience="Midnight skies with shimmering arrays of data stars.",
        description="Exploration-focused zone with musical lore and stealthy foes.",
    )

    # Resonant Expanse
    zones["resonant_expanse"] = Zone(
        name="resonant_expanse",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(140, 500, 160, 16)),
            Platform(pygame.Rect(360, 440, 180, 16)),
            Platform(pygame.Rect(580, 380, 160, 16)),
            Platform(pygame.Rect(280, 320, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "nocturne_array", (360, 360), None, "Return to Array"),
            Portal(pygame.Rect(740, 320, 40, 150), "paradox_vault", (600, 380), "phase_shift", "Paradox Vault"),
        ],
        npcs=[
            NPC(
                "Resonant Disciple",
                pygame.Rect(420, 420, 24, 32),
                [
                    DialogueLine(
                        "These caverns echo every decision you've made.",
                        forbidden_flag="resonant_disciple_met",
                        set_flag="resonant_disciple_met",
                    ),
                    DialogueLine(
                        "Collect the echo lantern so the Maestro will listen.",
                        None,
                        "restore_chorus",
                        None,
                        forbidden_flag="restore_chorus_accepted",
                    ),
                    DialogueLine(
                        "Sustain the harmonics or the Maestro will shatter you.",
                        None,
                        None,
                        None,
                        requires_flag="restore_chorus_accepted",
                        forbidden_flag="restore_chorus_complete",
                    ),
                    DialogueLine(
                        "Lantern in hand? Place it at the dais so the expanse can sing again.",
                        None,
                        None,
                        None,
                        requires_flag="collected_echo_lantern",
                        forbidden_flag="restore_chorus_complete",
                    ),
                    DialogueLine(
                        "Hear it? The Maestro weaves your mercy into the score.",
                        None,
                        None,
                        "restore_chorus",
                        requires_flag="restore_chorus_complete",
                    ),
                ],
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(360, 360, 16, 16),
                "Harmonic Record",
                "Crystalline staff lines storing the expanse's anthem.",
                value=2,
                lore_id="fragment_q",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(240, 520, 18, 18),
                "echo_lantern",
                "Echo Lantern",
                "A portable chorus that steadies fraying programs.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "phase_wisp", (180, 320)),
            CorruptedProgram(pygame.Rect(460, 440, 26, 24), "turret", (420, 560)),
            CorruptedProgram(pygame.Rect(620, 380, 26, 24), "defragger", (560, 720)),
        ],
        bosses=[BossEncounter("Eidolon Maestro", pygame.Rect(160, 240, 520, 280), 76, 4, pattern="rift")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(540, 520, 36, 36),
                "chorus_resonator",
                8,
                "Amplifies restorative harmonics when resting.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(140, 540, 42, 42),
                "Resonant Dais",
                "The chorus surrounds you in protective melody.",
                (160, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 520, 200, 70),
                "resonant_expanse_entry",
                "Vast chords bloom—restore the chorus to calm these depths.",
                grant_quest="restore_chorus",
                adjust_corruption=-3,
                reputation_changes=(("collectors", 2),),
                set_flags=("restore_chorus_accepted",),
            ),
            StoryEvent(
                pygame.Rect(540, 360, 120, 100),
                "chorus_rekindled",
                "The lantern's glow bathes the caverns; the Maestro bows in thanks.",
                requires_flag="collected_echo_lantern",
                complete_quest="restore_chorus",
                adjust_corruption=-7,
                reputation_changes=(("caretakers", 2), ("collectors", 2)),
                set_flags=("restore_chorus_complete",),
            ),
        ],
        ambience="Choirs echo across crystalline caverns tuned to your choices.",
        description="Extended songlines culminating in a maestro duel and chorus questline.",
    )

    # Deep Storage
    zones["deep_storage"] = Zone(
        name="deep_storage",
        platforms=[
            floor_platform(),
            Platform(pygame.Rect(200, 520, 140, 16)),
            Platform(pygame.Rect(420, 460, 160, 16)),
            Platform(pygame.Rect(620, 400, 140, 16)),
            Platform(pygame.Rect(320, 340, 140, 16)),
        ],
        portals=[
            Portal(pygame.Rect(20, 340, 60, 120), "kernel_nexus", (380, 540), None, "Return to Nexus"),
            Portal(pygame.Rect(760, 340, 40, 120), "core_ascendant", (120, 520), "codebreaker", "Ascendant Gate"),
        ],
        npcs=[
            NPC(
                "Ghosted Admin", pygame.Rect(460, 420, 24, 32),
                [
                    DialogueLine(
                        "This vault holds the truth. Only the pure may see it.",
                        forbidden_flag="purge_vault_accepted",
                    ),
                    DialogueLine(
                        "Your corruption clouds the archive. Cleanse more programs before you proceed.",
                        None,
                        None,
                        None,
                        requires_flag="purge_vault_accepted",
                        forbidden_flag="purge_vault_complete",
                    ),
                    DialogueLine(
                        "You've purged enough corruption. Enter the Terminal of Judgement.",
                        None,
                        "purge_vault",
                        None,
                        forbidden_flag="purge_vault_complete",
                    ),
                    DialogueLine(
                        "You faced the vault's truth and returned. Few echoes manage that.",
                        None,
                        None,
                        None,
                        requires_flag="purge_vault_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(pygame.Rect(460, 420, 16, 16), "Vaulted Memory", "Core to the Mainframe mystery."),
        ],
        items=[
            ItemDrop(
                pygame.Rect(360, 360, 18, 18),
                "quantum_key",
                "Quantum Key",
                "Opens encrypted caches elsewhere in the Mainframe.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "lurker", (200, 340)),
            CorruptedProgram(pygame.Rect(460, 440, 26, 24), "turret", (420, 520)),
            CorruptedProgram(pygame.Rect(660, 380, 26, 24), "admin_turret", (620, 760)),
        ],
        bosses=[BossEncounter("Vault Sentience", pygame.Rect(160, 240, 480, 280), 60, 3, pattern="lance")],
        save_stations=[
            SaveStation(pygame.Rect(200, 540, 42, 42), "Vault Cache", "Hidden routine restores structural integrity.", (220, 520)),
        ],
        ambience="Frozen archives and corrupted vault sentries.",
        description="Late-game vault with high stakes and lore revelations.",
    )

    # Signal Sea
    zones["signal_sea"] = Zone(
        name="signal_sea",
        platforms=[
            floor_platform(80),
            Platform(pygame.Rect(180, 460, 140, 16)),
            Platform(pygame.Rect(360, 400, 160, 16)),
            Platform(pygame.Rect(560, 340, 160, 16)),
            Platform(pygame.Rect(260, 520, 200, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(40, 360, 60, 120), "memory_garden", (620, 320), None, "Return to Garden"),
            Portal(pygame.Rect(740, 340, 40, 140), "trash_hollows", (120, 500), "phase_shift", "Trash Hollows"),
            Portal(pygame.Rect(360, 260, 60, 140), "backtrace_fathoms", (120, 520), "data_hook", "Backtrace Fathoms"),
        ],
        npcs=[
            NPC(
                "Waveform", pygame.Rect(400, 360, 24, 30),
                [
                    DialogueLine(
                        "Listen... the tides remember.",
                        forbidden_flag="waveform_met",
                        set_flag="waveform_met",
                    ),
                    DialogueLine(
                        "Phase Shift lets you ride the currents deeper.",
                        "phase_shift",
                        "tune_currents",
                        None,
                        requires_flag="waveform_met",
                        forbidden_flag="tune_currents_complete",
                    ),
                    DialogueLine(
                        "Guide three drifting beacons back into harmony.",
                        None,
                        None,
                        None,
                        requires_flag="tune_currents_accepted",
                        forbidden_flag="tune_currents_complete",
                    ),
                    DialogueLine(
                        "The sea hums in balance again. Carry its song inland.",
                        None,
                        None,
                        "tune_currents",
                        requires_flag="item_signal_token",
                    ),
                    DialogueLine(
                        "If the tides surge, return and I'll help retune them.",
                        None,
                        None,
                        None,
                        requires_flag="tune_currents_complete",
                    ),
                ],
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(380, 360, 16, 16),
                "Lore Fragment D",
                "Signal tides whisper of lost connections.",
                lore_id="fragment_d",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(520, 360, 18, 18),
                "signal_token",
                "Signal Token",
                "Resonates with certain lore nodes.",
            ),
        ],
        pickups=[AbilityPickup(pygame.Rect(600, 300, 20, 20), "overclock", "Tap raw processing power to negate damage."),],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 440, 26, 24), "scout", (180, 320)),
            CorruptedProgram(pygame.Rect(420, 380, 26, 24), "phase_wisp", (360, 520)),
            CorruptedProgram(pygame.Rect(620, 320, 26, 24), "defragger", (560, 720)),
        ],
        bosses=[BossEncounter("Surge Leviathan", pygame.Rect(160, 240, 520, 260), 55, 3, pattern="storm")],
        save_stations=[
            SaveStation(pygame.Rect(160, 540, 42, 42), "Signal Buoy", "Currents harmonize and mend glitches.", (180, 520)),
        ],
        ambience="Ocean of glitch static with luminous currents.",
        description="Wave-like platforms and teleporting foes among data tides.",
    )

    # Backtrace Fathoms
    zones["backtrace_fathoms"] = Zone(
        name="backtrace_fathoms",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(160, 500, 140, 16)),
            Platform(pygame.Rect(340, 440, 160, 16)),
            Platform(pygame.Rect(540, 380, 160, 16)),
            Platform(pygame.Rect(280, 320, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 140), "signal_sea", (600, 320), None, "Return to Signal Sea"),
            Portal(pygame.Rect(740, 320, 40, 140), "deep_storage", (140, 520), "phase_shift", "Deep Storage"),
        ],
        npcs=[
            NPC(
                "Fathom Diver",
                pygame.Rect(380, 420, 24, 32),
                [
                    DialogueLine(
                        "The backups flooded when the Overseer panicked.",
                        forbidden_flag="fathom_diver_met",
                        set_flag="fathom_diver_met",
                    ),
                    DialogueLine(
                        "Recover the lost shells and I'll share what I learned below.",
                        None,
                        "fathom_dive",
                        None,
                        forbidden_flag="fathom_dive_accepted",
                    ),
                    DialogueLine(
                        "Listen for the sonar pings. They reveal the safe paths downwards.",
                        None,
                        None,
                        None,
                        requires_flag="fathom_dive_accepted",
                        forbidden_flag="fathom_dive_complete",
                    ),
                    DialogueLine(
                        "The shell sings again. Take this resonance filter and breathe easy.",
                        None,
                        None,
                        "fathom_dive",
                        requires_flag="collected_fathom_shell",
                    ),
                    DialogueLine(
                        "When the depths call again, you know the route.",
                        None,
                        None,
                        None,
                        requires_flag="fathom_dive_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(520, 360, 16, 16),
                "Lore Fragment K",
                "Flooded archives hold experiments on memory loops.",
                lore_id="fragment_k",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(260, 520, 18, 18),
                "fathom_shell",
                "Fathom Shell",
                "Awakens a diver companion attuned to sonar.",
            ),
            ItemDrop(
                pygame.Rect(420, 460, 18, 18),
                "fathom_shell",
                "Fathom Shell",
                "Echoes with deepwater knowledge.",
            ),
            ItemDrop(
                pygame.Rect(580, 400, 18, 18),
                "fathom_shell",
                "Fathom Shell",
                "A shell cracked by oversight but still singing.",
            ),
            ItemDrop(
                pygame.Rect(600, 360, 18, 18),
                "resonance_filter",
                "Resonance Filter",
                "Reduces corruption gained from hazards when resting.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 480, 26, 24), "lurker", (180, 320)),
            CorruptedProgram(pygame.Rect(420, 420, 26, 24), "turret", (360, 520)),
            CorruptedProgram(pygame.Rect(620, 360, 26, 24), "phase_wisp", (560, 720)),
        ],
        bosses=[BossEncounter("Fathom Leviathan", pygame.Rect(160, 240, 520, 280), 62, 3, pattern="cascade")],
        upgrade_terminals=[
            UpgradeTerminal(pygame.Rect(520, 520, 36, 36), "heart_module", 7, "Increase maximum integrity."),
        ],
        save_stations=[
            SaveStation(pygame.Rect(160, 540, 42, 42), "Sonar Beacon", "Pulses map hidden safe ledges.", (180, 520)),
        ],
        ambience="Submerged data streams echo with distant sonar.",
        description="Slow, deliberate traversal with underwater-style physics cues.",
    )

    # Trash Hollows
    zones["trash_hollows"] = Zone(
        name="trash_hollows",
        platforms=[
            floor_platform(),
            Platform(pygame.Rect(160, 520, 140, 16)),
            Platform(pygame.Rect(360, 470, 140, 16)),
            Platform(pygame.Rect(540, 420, 160, 16)),
            Platform(pygame.Rect(300, 560, 200, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 360, 60, 120), "signal_sea", (620, 320), None, "Return to Signal Sea"),
            Portal(pygame.Rect(720, 300, 60, 160), "core_ascendant", (120, 520), "codebreaker", "Ascendant Core"),
        ],
        npcs=[
            NPC(
                "Scrap Baron", pygame.Rect(420, 430, 24, 30),
                [
                    DialogueLine(
                        "We were deleted... but we still hunger.",
                        forbidden_flag="appease_trash_accepted",
                        set_flag="scrap_baron_met",
                    ),
                    DialogueLine(
                        "Bring balance and I'll open the Ascendant Path.",
                        None,
                        "appease_trash",
                        None,
                        forbidden_flag="appease_trash_complete",
                    ),
                    DialogueLine(
                        "Collect scrap cores and return them here. The heaps will quiet.",
                        None,
                        None,
                        None,
                        requires_flag="appease_trash_accepted",
                        forbidden_flag="appease_trash_complete",
                    ),
                    DialogueLine(
                        "The hollows rest easy. Take this relay token for the Ascendant gate.",
                        None,
                        None,
                        "appease_trash",
                        requires_flag="item_scrap_core",
                    ),
                    DialogueLine(
                        "Spread word of our truce. Deleted code deserves dignity.",
                        None,
                        None,
                        None,
                        requires_flag="appease_trash_complete",
                    ),
                ],
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(560, 380, 16, 16),
                "Lore Fragment E",
                "Recycling pits churn with half-remembered code.",
                lore_id="fragment_e",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(300, 520, 18, 18),
                "scrap_core",
                "Scrap Core",
                "Trade goods prized by the Scrap Baron.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "lurker", (160, 320)),
            CorruptedProgram(pygame.Rect(420, 450, 26, 24), "turret", (380, 520)),
            CorruptedProgram(pygame.Rect(600, 400, 26, 24), "hopper", (560, 720)),
        ],
        bosses=[BossEncounter("Refuse Colossus", pygame.Rect(160, 240, 520, 260), 60, 3, pattern="storm")],
        upgrade_terminals=[UpgradeTerminal(pygame.Rect(240, 500, 36, 36), "heart_module", 7, "Forge a redundant kernel cell."),],
        save_stations=[
            SaveStation(pygame.Rect(520, 540, 42, 42), "Scrap Shelter", "Haphazard shields grant respite.", (540, 520)),
        ],
        ambience="Cacophony of broken code and sparking debris.",
        description="Chaotic platforms with hungry corrupted programs.",
    )

    # Mirror Rift
    zones["mirror_rift"] = Zone(
        name="mirror_rift",
        platforms=[
            floor_platform(80),
            Platform(pygame.Rect(140, 500, 140, 16)),
            Platform(pygame.Rect(360, 440, 160, 16)),
            Platform(pygame.Rect(560, 380, 160, 16)),
            Platform(pygame.Rect(260, 340, 120, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 140), "kernel_nexus", (540, 300), None, "Return to Nexus"),
            Portal(pygame.Rect(740, 300, 60, 160), "logic_spires", (100, 480), "codebreaker", "Logic Spires"),
            Portal(pygame.Rect(360, 120, 80, 120), "paradox_vault", (120, 500), "phase_shift", "Paradox Vault"),
            Portal(pygame.Rect(360, 520, 80, 80), "sundown_bazaar", (200, 460), "phase_shift", "Sundown Bazaar"),
        ],
        npcs=[
            NPC(
                "Rift Scribe", pygame.Rect(340, 400, 24, 32),
                [
                    DialogueLine(
                        "Shards of reality overlap here. Can you hear them hum?",
                        forbidden_flag="rift_scribe_met",
                        set_flag="rift_scribe_met",
                    ),
                    DialogueLine(
                        "Phase Shift keeps you from being shredded between reflections.",
                        "phase_shift",
                        "align_rift",
                        None,
                        requires_flag="rift_scribe_met",
                        forbidden_flag="align_rift_complete",
                    ),
                    DialogueLine(
                        "Three calibration glyphs hide within the Logic Spires.",
                        None,
                        None,
                        None,
                        requires_flag="align_rift_accepted",
                        forbidden_flag="align_rift_complete",
                    ),
                    DialogueLine(
                        "I can feel the glyph's rhythm returning. Anchor them at the nexus obelisk.",
                        None,
                        None,
                        None,
                        requires_flag="collected_calibration_glyph",
                        forbidden_flag="align_rift_complete",
                    ),
                    DialogueLine(
                        "The reflections stabilize. You've done it.",
                        None,
                        None,
                        "align_rift",
                        requires_flag="collected_calibration_glyph",
                    ),
                    DialogueLine(
                        "Travel freely—this fracture now hums in harmony.",
                        None,
                        None,
                        None,
                        requires_flag="align_rift_complete",
                    ),
                ],
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(400, 360, 16, 16),
                "Rift Fragment",
                "Pieces of mirrored code shimmering with potential.",
                value=2,
                lore_id="fragment_g",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(300, 520, 18, 18),
                "mirror_key",
                "Mirror Key",
                "Unlocks reflectors within the Logic Spires.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "phase_wisp", (160, 320)),
            CorruptedProgram(pygame.Rect(420, 440, 26, 24), "lurker", (380, 560)),
            CorruptedProgram(pygame.Rect(600, 380, 26, 24), "defragger", (560, 720)),
        ],
        bosses=[BossEncounter("Mirror Warden", pygame.Rect(160, 240, 520, 280), 55, 3, pattern="lance")],
        upgrade_terminals=[
            UpgradeTerminal(pygame.Rect(520, 520, 36, 36), "mirror_focus", 6, "Resting purges extra corruption."),
        ],
        save_stations=[
            SaveStation(pygame.Rect(180, 540, 42, 42), "Refraction Anchor", "Your form stabilizes amid the echoes.", (200, 520)),
        ],
        ambience="Glassine echoes shimmer through the fracture.",
        description="A fractured realm linking late-game traversal challenges.",
    )

    # Paradox Vault
    zones["paradox_vault"] = Zone(
        name="paradox_vault",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(160, 500, 160, 16)),
            Platform(pygame.Rect(360, 440, 200, 16)),
            Platform(pygame.Rect(580, 380, 160, 16)),
            Platform(pygame.Rect(280, 320, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "mirror_rift", (600, 360), None, "Return to Rift"),
            Portal(pygame.Rect(740, 320, 40, 150), "resonant_expanse", (120, 500), "codebreaker", "Resonant Expanse"),
        ],
        npcs=[
            NPC(
                "Chronomancer",
                pygame.Rect(420, 420, 24, 32),
                [
                    DialogueLine(
                        "Loops collapse upon loops—help me hold them open.",
                        forbidden_flag="chronomancer_met",
                        set_flag="chronomancer_met",
                    ),
                    DialogueLine(
                        "Gather the stray chronal thread before the Regent binds it.",
                        None,
                        "stitch_time",
                        None,
                        forbidden_flag="stitch_time_accepted",
                    ),
                    DialogueLine(
                        "The Regent fractures time with every strike. Stabilise the loom.",
                        None,
                        None,
                        None,
                        requires_flag="stitch_time_accepted",
                        forbidden_flag="stitch_time_complete",
                    ),
                    DialogueLine(
                        "Thread secured? Anchor it at the temporal loom to seal the breach.",
                        None,
                        None,
                        None,
                        requires_flag="collected_chronal_thread",
                        forbidden_flag="stitch_time_complete",
                    ),
                    DialogueLine(
                        "The vault resonates in harmony once more. You have my gratitude.",
                        None,
                        None,
                        "stitch_time",
                        requires_flag="stitch_time_complete",
                    ),
                ],
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(360, 360, 16, 16),
                "Paradox Log",
                "Annotated timelines trapped between cycles.",
                value=2,
                lore_id="fragment_p",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(240, 520, 18, 18),
                "chronal_thread",
                "Chronal Thread",
                "Spun from rewound processing cycles, hums with latent time.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "phase_wisp", (180, 340)),
            CorruptedProgram(pygame.Rect(480, 440, 26, 24), "lurker", (420, 560)),
            CorruptedProgram(pygame.Rect(620, 380, 26, 24), "defragger", (560, 720)),
        ],
        bosses=[BossEncounter("Paradox Regent", pygame.Rect(160, 240, 520, 280), 70, 4, pattern="pulse")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(540, 520, 36, 36),
                "temporal_buffer",
                8,
                "Shaves frames off the glitch dash recovery.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(140, 540, 42, 42),
                "Chronal Anchor",
                "Temporal loops align around your core.",
                (160, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 520, 200, 70),
                "paradox_vault_entry",
                "Chronal echoes wash over you—stitch the vault before it collapses.",
                grant_quest="stitch_time",
                adjust_corruption=-2,
                reputation_changes=(("collectors", 2),),
                set_flags=("stitch_time_accepted",),
            ),
            StoryEvent(
                pygame.Rect(540, 360, 120, 100),
                "chronal_loom_synced",
                "The chronal thread locks the loom in place. Time steadies.",
                requires_flag="collected_chronal_thread",
                complete_quest="stitch_time",
                adjust_corruption=-6,
                reputation_changes=(("caretakers", 3),),
                set_flags=("stitch_time_complete",),
            ),
        ],
        ambience="Temporal hums overlap as loops slip in and out of sync.",
        description="Optional anomaly weaving time-bending traversal and a new Regent duel.",
    )

    # Logic Spires
    zones["logic_spires"] = Zone(
        name="logic_spires",
        platforms=[
            floor_platform(80),
            Platform(pygame.Rect(160, 500, 140, 16)),
            Platform(pygame.Rect(360, 450, 160, 16)),
            Platform(pygame.Rect(560, 400, 160, 16)),
            Platform(pygame.Rect(280, 340, 140, 16)),
            Platform(pygame.Rect(480, 300, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "mirror_rift", (640, 320), None, "Return to Mirror Rift"),
            Portal(pygame.Rect(360, 220, 80, 120), "echo_sanctum", (120, 520), "phase_shift", "Echo Sanctum"),
            Portal(pygame.Rect(740, 300, 60, 160), "core_ascendant", (160, 520), "overclock", "Ascendant Gate"),
        ],
        npcs=[
            NPC(
                "Architect Node", pygame.Rect(420, 420, 24, 32),
                [
                    DialogueLine(
                        "These towers rewrite themselves each cycle.",
                        forbidden_flag="architect_met",
                        set_flag="architect_met",
                    ),
                    DialogueLine(
                        "Only an aligned mirror key can calm the recompiler storms.",
                        None,
                        None,
                        None,
                        requires_flag="architect_met",
                        forbidden_flag="align_rift_complete",
                    ),
                    DialogueLine(
                        "Take the calibration glyph and seat it within the rift obelisk.",
                        None,
                        None,
                        None,
                        requires_flag="item_mirror_key",
                        forbidden_flag="collected_calibration_glyph",
                    ),
                    DialogueLine(
                        "I sensed the reflections settle. The path to the Overseer now listens to you.",
                        None,
                        None,
                        None,
                        requires_flag="align_rift_complete",
                    ),
                ],
            ),
            NPC(
                "Glitchling Duo", pygame.Rect(280, 460, 28, 28),
                [
                    DialogueLine(
                        "We chase logic loops for fun!",
                        forbidden_flag="glitchling_met",
                        set_flag="glitchling_met",
                    ),
                    DialogueLine(
                        "If you debug us, we'll race you to every beacon.",
                        None,
                        None,
                        None,
                        requires_flag="glitchling_met",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(460, 360, 16, 16),
                "Calibration Glyph",
                "A resonant key that syncs the rift's reflections.",
                value=2,
                lore_id="fragment_h",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(320, 520, 18, 18),
                "logic_thread",
                "Logic Thread",
                "Used to weave shortcuts within the Map Overlay.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "admin_turret", (180, 320)),
            CorruptedProgram(pygame.Rect(420, 440, 26, 24), "phase_wisp", (360, 520)),
            CorruptedProgram(pygame.Rect(620, 380, 26, 24), "defragger", (580, 720)),
        ],
        bosses=[BossEncounter("Spires Choir", pygame.Rect(160, 220, 520, 300), 65, 3, pattern="spiral")],
        upgrade_terminals=[
            UpgradeTerminal(pygame.Rect(560, 520, 36, 36), "logic_resonance", 8, "Extend Overclock duration."),
        ],
        save_stations=[
            SaveStation(pygame.Rect(200, 540, 42, 42), "Compiler Rest", "Weaving logic threads restores you.", (220, 520)),
        ],
        ambience="Towering routines pulse in harmonic waves.",
        description="Endgame labyrinth balancing puzzles and high-tier combat.",
    )

    # Echo Sanctum
    zones["echo_sanctum"] = Zone(
        name="echo_sanctum",
        platforms=[
            floor_platform(70),
            Platform(pygame.Rect(140, 500, 160, 16)),
            Platform(pygame.Rect(360, 450, 160, 16)),
            Platform(pygame.Rect(560, 380, 160, 16)),
            Platform(pygame.Rect(280, 320, 120, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "logic_spires", (620, 320), None, "Return to Logic Spires"),
            Portal(pygame.Rect(740, 300, 60, 150), "entropy_cathedral", (120, 500), "overclock", "Entropy Slipway"),
        ],
        npcs=[
            NPC(
                "Resonant Chorister",
                pygame.Rect(320, 420, 24, 32),
                [
                    DialogueLine(
                        "These echoes remember kinder loops.",
                        forbidden_flag="chorister_met",
                        set_flag="chorister_met",
                    ),
                    DialogueLine(
                        "Will you attune the stray harmonics with me?",
                        grant_quest="harmonic_attunement",
                        requires_flag="chorister_met",
                        forbidden_flag="harmonic_attunement_accepted",
                    ),
                    DialogueLine(
                        "Gather the chorus shard from the harmonic vault.",
                        requires_flag="harmonic_attunement_accepted",
                        forbidden_flag="harmonic_attunement_complete",
                    ),
                    DialogueLine(
                        "The sanctum resonates with your tune. Accept this focus prism.",
                        requires_flag="item_chorus_shard",
                        completes_quest="harmonic_attunement",
                    ),
                    DialogueLine(
                        "Listen: every corridor hums in gratitude.",
                        requires_flag="harmonic_attunement_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(420, 360, 16, 16),
                "Chorus Archive",
                "Encoded hymns of lost companions.",
                value=2,
                lore_id="fragment_l",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(260, 520, 18, 18),
                "chorus_shard",
                "Chorus Shard",
                "Resonant fragment needed to calm the sanctum.",
            ),
            ItemDrop(
                pygame.Rect(560, 340, 18, 18),
                "resonance_filter",
                "Resonance Filter",
                "Rest bonuses linger longer in this tuned chamber.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "phase_wisp", (160, 320)),
            CorruptedProgram(pygame.Rect(420, 460, 26, 24), "lurker", (360, 560)),
            CorruptedProgram(pygame.Rect(640, 380, 26, 24), "defragger", (580, 720)),
        ],
        bosses=[BossEncounter("Harmonic Sentinel", pygame.Rect(140, 220, 520, 320), 68, 4, pattern="spiral")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(600, 520, 36, 36),
                "heart_module",
                8,
                "Fortify your kernel with additional integrity.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(120, 540, 42, 42),
                "Echo Anchor",
                "The echoes weave a safe refrain.",
                (140, 520),
            ),
        ],
        ambience="Harmonic waves ripple between mirrored amplifiers.",
        description="Optional sanctuary full of lore, attunement quests, and a musical guardian.",
    )

    # Core Ascendant
    zones["core_ascendant"] = Zone(
        name="core_ascendant",
        platforms=[
            floor_platform(80),
            Platform(pygame.Rect(180, 500, 160, 16)),
            Platform(pygame.Rect(380, 440, 160, 16)),
            Platform(pygame.Rect(580, 380, 160, 16)),
            Platform(pygame.Rect(280, 320, 160, 16)),
            Platform(pygame.Rect(480, 260, 160, 16), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 140), "kernel_nexus", (420, 360), None, "Return to Nexus"),
            Portal(pygame.Rect(760, 280, 40, 160), "logic_spires", (120, 500), "overclock", "Logic Spires"),
            Portal(pygame.Rect(360, 160, 80, 120), "entropy_cathedral", (120, 500), "overclock", "Entropy Cathedral"),
        ],
        npcs=[
            NPC(
                "Ascendant Echo", pygame.Rect(360, 400, 24, 32),
                [
                    DialogueLine(
                        "This is where we decide the Mainframe's fate.",
                        forbidden_flag="ascendant_echo_met",
                        set_flag="ascendant_echo_met",
                    ),
                    DialogueLine(
                        "Overclock and mercy together can reboot hope.",
                        None,
                        None,
                        None,
                        requires_flag="ascendant_echo_met",
                    ),
                    DialogueLine(
                        "The Logic Spires hum with possibilities. Align them before facing the Overseer.",
                        None,
                        None,
                        None,
                        requires_flag="align_rift_accepted",
                        forbidden_flag="align_rift_complete",
                    ),
                    DialogueLine(
                        "You stabilized the spires. Now the Overseer will listen.",
                        None,
                        None,
                        None,
                        requires_flag="align_rift_complete",
                    ),
                ],
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(420, 360, 16, 16),
                "Lore Fragment F",
                "Final protocol outlines the choice to reboot or escape.",
                lore_id="fragment_f",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(500, 420, 18, 18),
                "ascendant_relic",
                "Ascendant Relic",
                "Proof of surviving the Overseer's gauntlet.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 480, 26, 24), "admin_turret", (180, 320)),
            CorruptedProgram(pygame.Rect(420, 420, 26, 24), "phase_wisp", (360, 520)),
            CorruptedProgram(pygame.Rect(620, 360, 26, 24), "defragger", (580, 720)),
        ],
        bosses=[BossEncounter("Ascendant Overseer", pygame.Rect(140, 200, 540, 320), 80, 4, pattern="storm")],
        upgrade_terminals=[UpgradeTerminal(pygame.Rect(600, 520, 36, 36), "core_overclock", 10, "Unlock permanent Overclock protocol."),],
        save_stations=[
            SaveStation(pygame.Rect(320, 540, 42, 42), "Ascendant Relay", "Final calibration before the Overseer.", (340, 520)),
        ],
        ambience="Spires of admin code crackle with decision-making energy.",
        description="Final gauntlet culminating in the Overseer battle.",
    )

    # Entropy Cathedral
    zones["entropy_cathedral"] = Zone(
        name="entropy_cathedral",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(200, 520, 160, 16)),
            Platform(pygame.Rect(420, 460, 160, 16)),
            Platform(pygame.Rect(620, 400, 140, 16)),
            Platform(pygame.Rect(320, 340, 160, 12), "hazard"),
            Platform(pygame.Rect(520, 280, 160, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 160), "echo_sanctum", (660, 320), None, "Return to Sanctum"),
            Portal(pygame.Rect(740, 280, 60, 160), "core_ascendant", (360, 340), None, "Ascendant Descent"),
            Portal(pygame.Rect(360, 160, 80, 120), "oblivion_grid", (120, 520), "overclock", "Oblivion Grid"),
            Portal(pygame.Rect(360, 80, 80, 100), "umbra_cloister", (120, 520), "phase_shift", "Umbra Cloister"),
        ],
        npcs=[
            NPC(
                "Entropy Curator",
                pygame.Rect(360, 420, 24, 32),
                [
                    DialogueLine(
                        "Entropy floods every line of this cathedral.",
                        forbidden_flag="entropy_curator_met",
                        set_flag="entropy_curator_met",
                    ),
                    DialogueLine(
                        "Stabilize the entropy wells before the bishop awakens.",
                        grant_quest="entropy_balance",
                        requires_flag="entropy_curator_met",
                        forbidden_flag="entropy_balance_accepted",
                    ),
                    DialogueLine(
                        "Seal the entropy wells and retrieve their stabilizing core.",
                        requires_flag="entropy_balance_accepted",
                        forbidden_flag="entropy_balance_complete",
                    ),
                    DialogueLine(
                        "Balance restored. Carry this entropy core to the Overseer.",
                        requires_flag="item_entropy_core",
                        completes_quest="entropy_balance",
                    ),
                    DialogueLine(
                        "Walk carefully. The cathedral still shudders with collapse.",
                        requires_flag="entropy_balance_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(480, 360, 16, 16),
                "Entropy Scripture",
                "Notes on binding corruption within cathedral vaults.",
                value=3,
                lore_id="fragment_m",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(320, 520, 18, 18),
                "entropy_core",
                "Entropy Core",
                "Dense stabilizer extracted from sealed wells.",
            ),
            ItemDrop(
                pygame.Rect(540, 360, 18, 18),
                "patch_kit",
                "Patch Kit",
                "Emergency integrity repair salvaged from cathedral vaults.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "admin_turret", (180, 320)),
            CorruptedProgram(pygame.Rect(420, 440, 26, 24), "slicer", (360, 560)),
            CorruptedProgram(pygame.Rect(640, 380, 26, 24), "defragger", (580, 720)),
        ],
        bosses=[BossEncounter("Entropy Bishop", pygame.Rect(140, 220, 520, 320), 90, 4, pattern="cascade")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(240, 500, 36, 36),
                "dash_optimizer",
                9,
                "Shorten dash cooldown to slip between entropy storms.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(500, 540, 42, 42),
                "Entropy Reliquary",
                "Stilled entropy creates a brief sanctuary.",
                (520, 520),
            ),
        ],
        ambience="Fractured choirs chant beneath collapsing admin vaults.",
        description="Late-game cathedral packed with entropy quests and a climactic bishop encounter.",
    )

    # Oblivion Grid - bridge to the Prime Gate
    zones["oblivion_grid"] = Zone(
        name="oblivion_grid",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(180, 520, 160, 16)),
            Platform(pygame.Rect(380, 460, 160, 16)),
            Platform(pygame.Rect(580, 400, 160, 16)),
            Platform(pygame.Rect(320, 340, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 300, 80, 160), "entropy_cathedral", (520, 360), None, "Return to Cathedral"),
            Portal(pygame.Rect(740, 280, 60, 160), "prime_convergence", (120, 520), "codebreaker", "Prime Gate"),
        ],
        npcs=[
            NPC(
                "Grid Warden",
                pygame.Rect(360, 420, 24, 32),
                [
                    DialogueLine(
                        "These lattice lines once judged every routine.",
                        forbidden_flag="grid_warden_met",
                        set_flag="grid_warden_met",
                    ),
                    DialogueLine(
                        "Stabilize the anchors and the Arbiter may speak true.",
                        requires_flag="grid_warden_met",
                        forbidden_flag="oblivion_protocol_accepted",
                        grant_quest="oblivion_protocol",
                    ),
                    DialogueLine(
                        "Embed a sigil at each anchor. Only then will the Prime Gate align.",
                        requires_flag="oblivion_protocol_accepted",
                        forbidden_flag="oblivion_protocol_complete",
                    ),
                    DialogueLine(
                        "The grid steadies. Carry the resonance toward the Prime Gate.",
                        requires_flag="oblivion_protocol_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(420, 360, 16, 16),
                "Oblivion Transcript",
                "Etched verdicts of the Arbiter's last cycle.",
                value=2,
                lore_id="fragment_n",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(260, 520, 18, 18),
                "oblivion_sigil",
                "Oblivion Sigil",
                "Calibrates the grid's failing anchors.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "admin_turret", (180, 360)),
            CorruptedProgram(pygame.Rect(440, 440, 26, 24), "defragger", (400, 520)),
            CorruptedProgram(pygame.Rect(640, 380, 26, 24), "phase_wisp", (600, 720)),
        ],
        bosses=[BossEncounter("Oblivion Arbiter", pygame.Rect(140, 220, 520, 320), 95, 4, pattern="storm")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(560, 520, 36, 36),
                "mirror_focus",
                9,
                "Channel the grid's calm to reduce corruption on rest.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(120, 540, 42, 42),
                "Grid Atrium",
                "Anchored packets weave a momentary sanctuary.",
                (140, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(300, 520, 140, 60),
                "oblivion_grid_entry",
                "The grid crackles: stabilize each anchor to open the Prime Gate.",
                grant_quest="oblivion_protocol",
                reputation_changes=(("rebellion", 2),),
                set_flags=("oblivion_protocol_signal",),
                forbidden_flag="oblivion_protocol_complete",
            ),
            StoryEvent(
                pygame.Rect(540, 360, 90, 80),
                "oblivion_anchor_synced",
                "You embed the sigil and the lattice steadies into harmony.",
                requires_flag="collected_oblivion_sigil",
                complete_quest="oblivion_protocol",
                adjust_corruption=-8,
                reputation_changes=(("caretakers", 2), ("collectors", 2)),
                set_flags=("oblivion_protocol_complete", "prime_gate_ready"),
            ),
            StoryEvent(
                pygame.Rect(700, 300, 80, 140),
                "prime_gate_resonates",
                "The Prime Gate hums—your actions echo across the Mainframe.",
                requires_flag="oblivion_protocol_complete",
                adjust_corruption=-4,
                set_flags=("prime_gate_resonating",),
            ),
        ],
        ambience="Gridlines shimmer with half-forgotten verdicts.",
        description="Bridge zone balancing late-game traversal, story hooks, and a decisive Arbiter battle.",
    )

    # Prime Convergence - finale space
    zones["prime_convergence"] = Zone(
        name="prime_convergence",
        platforms=[
            floor_platform(100),
            Platform(pygame.Rect(200, 520, 160, 16)),
            Platform(pygame.Rect(420, 460, 160, 16)),
            Platform(pygame.Rect(620, 400, 140, 16)),
            Platform(pygame.Rect(320, 340, 140, 12), "hazard"),
            Platform(pygame.Rect(480, 280, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 80, 160), "oblivion_grid", (620, 360), None, "Return to Grid"),
            Portal(pygame.Rect(360, 120, 80, 120), "kernel_nexus", (360, 360), None, "Nexus Shortcut"),
            Portal(pygame.Rect(740, 300, 50, 150), "fractal_bastion", (140, 520), "overclock", "Fractal Bastion"),
            Portal(pygame.Rect(360, 520, 80, 80), "cradle_of_resolve", (200, 500), "cradle_access", "Cradle of Resolve"),
            Portal(pygame.Rect(600, 160, 80, 120), "infinite_chamber", (120, 520), "overclock", "Infinite Chamber"),
        ],
        npcs=[
            NPC(
                "Prime Custodian",
                pygame.Rect(360, 420, 24, 32),
                [
                    DialogueLine(
                        "You carry every choice with you, Echo.",
                        forbidden_flag="prime_custodian_met",
                        set_flag="prime_custodian_met",
                    ),
                    DialogueLine(
                        "Once the Architect stirs, only conviction will end the cycle.",
                        requires_flag="prime_custodian_met",
                    ),
                    DialogueLine(
                        "Let the Prime Gate record what path you carve.",
                        requires_flag="prime_resolution_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(440, 360, 16, 16),
                "Prime Dictum",
                "Final decree awaiting the Echo's verdict.",
                value=3,
                lore_id="fragment_o",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(300, 520, 18, 18),
                "prime_thread",
                "Prime Thread",
                "A luminous strand that binds the Mainframe's future.",
            ),
        ],
        pickups=[
            AbilityPickup(
                pygame.Rect(520, 320, 20, 20),
                "overclock",
                "Sustain invulnerability longer to weather the Architect's judgement.",
            )
        ],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "defragger", (180, 320)),
            CorruptedProgram(pygame.Rect(420, 440, 26, 24), "admin_turret", (380, 520)),
        ],
        bosses=[BossEncounter("Prime Architect", pygame.Rect(140, 200, 520, 340), 120, 5, pattern="meteor")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(600, 520, 36, 36),
                "core_overclock",
                10,
                "Unlock an extended overclock protocol for the finale.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(120, 540, 42, 42),
                "Prime Anchor",
                "The Prime Gate folds time long enough for you to rest.",
                (140, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 520, 160, 70),
                "prime_convergence_entry",
                "The Prime Gate flares—record your intent and end the fracture.",
                grant_quest="prime_resolution",
                unlock_ability="overclock",
                reputation_changes=(("collectors", 2), ("caretakers", 1)),
                set_flags=("prime_resolution_active",),
            ),
            StoryEvent(
                pygame.Rect(420, 360, 90, 80),
                "prime_resolution_recorded",
                "The Prime Gate accepts your thread. The Mainframe holds its breath.",
                requires_flag="collected_prime_thread",
                complete_quest="prime_resolution",
                adjust_corruption=-12,
                set_flags=("prime_judgement_recorded",),
                cinematic_id="prime_reckoning",
            ),
        ],
        ambience="The Prime Gate crackles with world-shaping potential.",
        description="Final arena blending narrative resolution with the toughest Architect duel yet.",
    )

    # Fractal Bastion - optional alliance keep
    zones["fractal_bastion"] = Zone(
        name="fractal_bastion",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(160, 500, 160, 16)),
            Platform(pygame.Rect(360, 440, 180, 16)),
            Platform(pygame.Rect(580, 380, 160, 16)),
            Platform(pygame.Rect(260, 320, 140, 12), "hazard"),
            Platform(pygame.Rect(460, 280, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "prime_convergence", (600, 360), None, "Return to Prime Gate"),
            Portal(pygame.Rect(740, 320, 40, 150), "luminous_reserve", (140, 520), "codebreaker", "Luminous Reserve"),
        ],
        npcs=[
            NPC(
                "Paragon Sentry",
                pygame.Rect(360, 420, 24, 32),
                [
                    DialogueLine(
                        "These ramparts defended ideals, not tyrants.",
                        forbidden_flag="paragon_sentry_met",
                        set_flag="paragon_sentry_met",
                    ),
                    DialogueLine(
                        "Pledge balance between decompile and debug and the bastion will march with you.",
                        None,
                        "bastion_pact",
                        None,
                        requires_flag="paragon_sentry_met",
                        forbidden_flag="bastion_pact_accepted",
                    ),
                    DialogueLine(
                        "Collect a fractal shard from the Paragon's arena and prove your resolve.",
                        None,
                        None,
                        None,
                        requires_flag="bastion_pact_accepted",
                        forbidden_flag="bastion_pact_complete",
                    ),
                    DialogueLine(
                        "The bastion stands with you now. Let our sigils steady your path.",
                        None,
                        None,
                        None,
                        requires_flag="bastion_pact_complete",
                    ),
                ],
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(420, 360, 16, 16),
                "Fractal Chronicle",
                "A ledger of pacts forged during the Mainframe wars.",
                value=2,
                lore_id="fragment_r",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(300, 520, 18, 18),
                "fractal_shard",
                "Fractal Shard",
                "Proof of a pact with the Paragon defenders.",
            ),
            ItemDrop(
                pygame.Rect(520, 360, 18, 18),
                "bastion_sigil",
                "Bastion Sigil",
                "Calls a sentry companion when synchronized.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "admin_turret", (160, 320)),
            CorruptedProgram(pygame.Rect(420, 440, 26, 24), "phase_wisp", (360, 520)),
            CorruptedProgram(pygame.Rect(600, 380, 26, 24), "defragger", (560, 720)),
        ],
        bosses=[BossEncounter("Fractal Paragon", pygame.Rect(160, 220, 520, 300), 84, 4, pattern="spiral")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(560, 520, 36, 36),
                "fractal_matrix",
                9,
                "Fractal armor weaves +1 integrity and reduces corruption.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(160, 540, 42, 42),
                "Bastion Barracks",
                "Sentries reinforce your kernel weave while you rest.",
                (180, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 520, 200, 80),
                "fractal_bastion_entry",
                "Fractal walls shimmer—forge a pact to rally these defenders.",
                grant_quest="bastion_pact",
                reputation_changes=(("rebellion", 2), ("collectors", 2)),
                set_flags=("bastion_pact_accepted",),
                cinematic_id="bastion_manifest",
            ),
            StoryEvent(
                pygame.Rect(520, 360, 140, 100),
                "fractal_pact_forged",
                "Fractal sigils align behind you. The bastion marches under your banner.",
                requires_flag="collected_fractal_shard",
                complete_quest="bastion_pact",
                adjust_corruption=-6,
                reputation_changes=(("rebellion", 3), ("caretakers", 2)),
            ),
        ],
        ambience="Defensive harmonics pulse through shifting ramparts.",
        description="Optional keep that rewards balanced playstyles with new allies and armor.",
    )

    # Luminous Reserve - restorative archives
    zones["luminous_reserve"] = Zone(
        name="luminous_reserve",
        platforms=[
            floor_platform(80),
            Platform(pygame.Rect(160, 500, 160, 16)),
            Platform(pygame.Rect(360, 440, 180, 16)),
            Platform(pygame.Rect(560, 380, 160, 16)),
            Platform(pygame.Rect(280, 320, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "fractal_bastion", (600, 360), None, "Return to Bastion"),
            Portal(pygame.Rect(740, 320, 40, 150), "memory_garden", (160, 520), None, "Memory Garden"),
            Portal(pygame.Rect(360, 260, 80, 110), "radiant_span", (120, 520), "data_hook", "Radiant Span"),
        ],
        npcs=[
            NPC(
                "Caretaker Lumen",
                pygame.Rect(380, 420, 24, 32),
                [
                    DialogueLine(
                        "We archive every program you heal.",
                        forbidden_flag="caretaker_lumen_met",
                        set_flag="caretaker_lumen_met",
                    ),
                    DialogueLine(
                        "Secure the bastion's loyalty and we'll entrust you with our reserves.",
                        None,
                        None,
                        None,
                        requires_flag="caretaker_lumen_met",
                        forbidden_flag="bastion_pact_complete",
                    ),
                    DialogueLine(
                        "Stabilize the reserves and we'll project shields over the Nexus.",
                        None,
                        "reserve_revival",
                        None,
                        requires_flag="bastion_pact_complete",
                        forbidden_flag="reserve_revival_accepted",
                    ),
                    DialogueLine(
                        "Seek a luminous core from the Compiler's sanctum.",
                        None,
                        None,
                        None,
                        requires_flag="reserve_revival_accepted",
                        forbidden_flag="reserve_revival_complete",
                    ),
                    DialogueLine(
                        "The shields hold again. We'll guard your allies while you finish the fight.",
                        None,
                        None,
                        None,
                        requires_flag="reserve_revival_complete",
                    ),
                ],
            )
        ],
        collectibles=[
            Collectible(
                pygame.Rect(420, 360, 16, 16),
                "Luminal Ledger",
                "Encrypted hymns describing healed programs returning to duty.",
                value=2,
                lore_id="fragment_s",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(300, 520, 18, 18),
                "lumen_core",
                "Lumen Core",
                "Stores restorative light for safe stations.",
            ),
            ItemDrop(
                pygame.Rect(540, 360, 18, 18),
                "reserve_map",
                "Reserve Cartography",
                "Unlocks hidden alcoves on the world map.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "phase_wisp", (160, 320)),
            CorruptedProgram(pygame.Rect(420, 440, 26, 24), "turret", (380, 520)),
            CorruptedProgram(pygame.Rect(620, 380, 26, 24), "defragger", (580, 720)),
        ],
        bosses=[BossEncounter("Celestial Compiler", pygame.Rect(160, 220, 520, 300), 92, 4, pattern="cascade")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(560, 520, 36, 36),
                "lumen_conduit",
                7,
                "Save stations grant extra healing and corruption relief.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(160, 540, 42, 42),
                "Reserve Heart",
                "Warm light flows from the archives to mend you.",
                (180, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 520, 200, 80),
                "luminous_reserve_entry",
                "Luminous shields flicker. Restore the core to protect your allies.",
                grant_quest="reserve_revival",
                requires_flag="bastion_pact_complete",
                adjust_corruption=-4,
                reputation_changes=(("caretakers", 3),),
                set_flags=("reserve_revival_accepted",),
                cinematic_id="reserve_requiem",
            ),
            StoryEvent(
                pygame.Rect(520, 360, 140, 100),
                "luminous_reserve_stabilized",
                "Luminous cores ignite. The reserves project shielding across the Nexus.",
                requires_flag="collected_lumen_core",
                complete_quest="reserve_revival",
                adjust_corruption=-8,
                reputation_changes=(("caretakers", 4), ("collectors", 2)),
            ),
        ],
        ambience="Bioluminescent archives hum with restorative harmonics.",
        description="Restorative wing offering defensive boons and a radiant boss encounter.",
    )

    # Sundown Bazaar - neon market crossroads
    zones["sundown_bazaar"] = Zone(
        name="sundown_bazaar",
        platforms=[
            floor_platform(70),
            Platform(pygame.Rect(160, 480, 180, 14)),
            Platform(pygame.Rect(420, 420, 200, 14)),
            Platform(pygame.Rect(620, 360, 140, 14)),
            Platform(pygame.Rect(300, 300, 120, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 140), "kernel_nexus", (660, 420), None, "Kernel Nexus"),
            Portal(pygame.Rect(760, 320, 40, 140), "mirror_rift", (120, 520), "phase_shift", "Mirror Rift"),
            Portal(pygame.Rect(360, 200, 80, 110), "permutation_labyrinth", (120, 520), "codebreaker", "Permutation Labyrinth"),
        ],
        npcs=[
            NPC(
                "Broker Vega",
                pygame.Rect(220, 460, 24, 32),
                [
                    DialogueLine(
                        "Welcome to Sundown—keep trades honest and the neon stays lit.",
                        forbidden_flag="broker_vega_met",
                        set_flag="broker_vega_met",
                    ),
                    DialogueLine(
                        "Our relay courier vanished. Will you deliver the cipher?",
                        None,
                        "bazaar_relay",
                        None,
                        forbidden_flag="bazaar_relay_accepted",
                    ),
                    DialogueLine(
                        "The Bazaar needs that relay cipher delivered to the Rift courier.",
                        None,
                        None,
                        None,
                        requires_flag="bazaar_relay_accepted",
                        forbidden_flag="bazaar_relay_complete",
                    ),
                    DialogueLine(
                        "The market glows again thanks to your delivery—Sundown stands with you.",
                        None,
                        None,
                        "bazaar_relay",
                        requires_flag="item_relay_cipher",
                        forbidden_flag="bazaar_relay_complete",
                    ),
                    DialogueLine(
                        "Keep listening—the Bazaar hears every new rumor you spark.",
                        None,
                        None,
                        None,
                        requires_flag="bazaar_relay_complete",
                    ),
                ],
            ),
            NPC(
                "Cantor Nyx",
                pygame.Rect(540, 380, 24, 32),
                [
                    DialogueLine(
                        "These stalls sing of every choice you make.",
                        forbidden_flag="cantor_nyx_met",
                        set_flag="cantor_nyx_met",
                    ),
                    DialogueLine(
                        "Bring me the Market Manifest and I'll carry your legend across Sundown.",
                        None,
                        None,
                        None,
                        requires_flag="collected_market_manifest",
                        forbidden_flag="fragment_t_shared",
                        set_flag="fragment_t_shared",
                    ),
                    DialogueLine(
                        "Your tale ripples through the market. Factions barter for your favor now.",
                        None,
                        None,
                        None,
                        requires_flag="fragment_t_shared",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(600, 340, 16, 16),
                "Market Manifest",
                "Encrypted receipts prove secret alliances between factions.",
                value=2,
                lore_id="fragment_t",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(320, 440, 18, 18),
                "relay_cipher",
                "Relay Cipher",
                "An encoded trade route sought by Mirror Rift couriers.",
            ),
            ItemDrop(
                pygame.Rect(460, 400, 18, 18),
                "bazaar_token",
                "Sundown Token",
                "Recruit a market envoy who trades tips during rests.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(180, 500, 26, 24), "scout", (140, 380)),
            CorruptedProgram(pygame.Rect(520, 420, 26, 24), "slicer", (480, 700)),
            CorruptedProgram(pygame.Rect(640, 360, 26, 24), "turret", (620, 760)),
        ],
        bosses=[BossEncounter("Bazaar Sentinel", pygame.Rect(180, 240, 440, 220), 58, 3, pattern="pulse")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(640, 500, 36, 36),
                "market_link",
                6,
                "Improves item drop rates and adds rest rewards from companions.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(120, 520, 42, 42),
                "Bazaar Safehouse",
                "Vendors shelter you while rumors reshuffle reputation.",
                (140, 500),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(160, 480, 260, 80),
                "sundown_arrival",
                "Sundown's neon awakes—earn trust to keep the stalls open.",
                cinematic_id="sundown_overture",
                reputation_changes=(("collectors", 1),),
            ),
            StoryEvent(
                pygame.Rect(520, 340, 160, 120),
                "sundown_song_shared",
                "Cantor Nyx hums your story. Merchants whisper about your victories.",
                requires_flag="fragment_t_shared",
                adjust_corruption=-2,
                reputation_changes=(("caretakers", 1), ("collectors", 1)),
            ),
        ],
        ambience="Neon commerce thrums beneath the Mainframe dusk.",
        description="Faction-neutral marketplace with side quests and a defensive sentinel boss.",
    )

    # Permutation Labyrinth - recursive gauntlet
    zones["permutation_labyrinth"] = Zone(
        name="permutation_labyrinth",
        platforms=[
            floor_platform(80),
            Platform(pygame.Rect(140, 500, 160, 16)),
            Platform(pygame.Rect(340, 440, 180, 16)),
            Platform(pygame.Rect(560, 380, 160, 16)),
            Platform(pygame.Rect(260, 320, 140, 14)),
            Platform(pygame.Rect(480, 260, 160, 14), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "sundown_bazaar", (640, 420), None, "Return to Bazaar"),
            Portal(pygame.Rect(740, 320, 40, 150), "prime_convergence", (120, 520), "overclock", "Prime Convergence"),
            Portal(pygame.Rect(360, 200, 80, 110), "tesseract_workshop", (140, 520), "phase_shift", "Tesseract Workshop"),
        ],
        npcs=[
            NPC(
                "Labyrinth Custodian",
                pygame.Rect(380, 420, 24, 32),
                [
                    DialogueLine(
                        "These corridors reshape to test your resolve.",
                        forbidden_flag="labyrinth_custodian_met",
                        set_flag="labyrinth_custodian_met",
                    ),
                    DialogueLine(
                        "Face the hydra of recursion and retrieve its key if you seek the Cradle.",
                        None,
                        "labyrinth_solve",
                        None,
                        forbidden_flag="labyrinth_solve_accepted",
                    ),
                    DialogueLine(
                        "Threads of the maze align only when courage and empathy balance.",
                        None,
                        None,
                        None,
                        requires_flag="labyrinth_solve_accepted",
                        forbidden_flag="labyrinth_solve_complete",
                    ),
                    DialogueLine(
                        "You carry the hydra's key. The Cradle will heed you now.",
                        None,
                        None,
                        None,
                        requires_flag="labyrinth_solve_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(540, 340, 16, 16),
                "Recursive Blueprint",
                "Schematics map how the labyrinth defends the Mainframe core.",
                value=2,
                lore_id="fragment_u",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(360, 300, 18, 18),
                "labyrinth_key",
                "Hydra Key",
                "Unlocks the Cradle gate after harmonizing the maze.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "lurker", (160, 360)),
            CorruptedProgram(pygame.Rect(460, 440, 26, 24), "admin_turret", (420, 620)),
            CorruptedProgram(pygame.Rect(620, 360, 26, 24), "phase_wisp", (520, 720)),
        ],
        bosses=[BossEncounter("Permutation Hydra", pygame.Rect(160, 200, 520, 280), 96, 4, pattern="storm")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(600, 500, 36, 36),
                "labyrinth_solver",
                8,
                "Dash invulnerability lasts longer against multi-directional barrages.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(140, 520, 42, 42),
                "Recursive Anchor",
                "Anchor points steady your resolve within the shifting maze.",
                (160, 500),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 460, 220, 100),
                "labyrinth_threshold",
                "Fractured corridors align as you enter—solve the recursion to proceed.",
                grant_quest="labyrinth_solve",
                set_flags=("labyrinth_path_awoken",),
                cinematic_id="labyrinth_vision",
            ),
            StoryEvent(
                pygame.Rect(520, 320, 160, 120),
                "labyrinth_key_harmonics",
                "The hydra's key resonates. A gate to the Cradle unlocks in the Prime Convergence.",
                requires_flag="labyrinth_key_obtained",
                complete_quest="labyrinth_solve",
                set_flags=("cradle_gate_open",),
                adjust_corruption=-6,
                unlock_ability="cradle_access",
            ),
        ],
        ambience="Recursive corridors breathe with living code and hidden guardians.",
        description="Challenging maze that unlocks the finale path and rewards daring explorers.",
    )

    # Cradle of Resolve - finale sanctum
    zones["cradle_of_resolve"] = Zone(
        name="cradle_of_resolve",
        platforms=[
            floor_platform(80),
            Platform(pygame.Rect(200, 500, 180, 16)),
            Platform(pygame.Rect(420, 440, 200, 16)),
            Platform(pygame.Rect(620, 380, 160, 16)),
            Platform(pygame.Rect(320, 320, 160, 12)),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "prime_convergence", (660, 420), None, "Prime Convergence"),
        ],
        npcs=[
            NPC(
                "Sovereign Scribe",
                pygame.Rect(420, 420, 24, 34),
                [
                    DialogueLine(
                        "This cradle records the decision that will define the Mainframe.",
                        forbidden_flag="sovereign_scribe_met",
                        set_flag="sovereign_scribe_met",
                    ),
                    DialogueLine(
                        "Weigh mercy against force. Only then may the Sovereign heed you.",
                        None,
                        None,
                        None,
                        requires_flag="cradle_resolve_accepted",
                        forbidden_flag="cradle_resolve_complete",
                    ),
                    DialogueLine(
                        "Your choice reverberates across every zone. Prepare for the Prime Reckoning.",
                        None,
                        None,
                        None,
                        requires_flag="cradle_resolve_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(560, 340, 16, 16),
                "Resolve Chronicle",
                "Final entries document how the Echo can reboot or liberate the Mainframe.",
                value=3,
                lore_id="fragment_v",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(360, 360, 18, 18),
                "resolve_core",
                "Resolve Core",
                "Condensed purpose that empowers your final decision.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "defragger", (180, 400)),
            CorruptedProgram(pygame.Rect(520, 420, 26, 24), "admin_turret", (480, 700)),
            CorruptedProgram(pygame.Rect(640, 360, 26, 24), "phase_wisp", (540, 760)),
        ],
        bosses=[BossEncounter("Cradle Sovereign", pygame.Rect(180, 220, 520, 280), 120, 5, pattern="meteor")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(600, 500, 36, 36),
                "resolve_matrix",
                10,
                "Amplifies Overclock while lowering corruption spikes from damage.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(160, 520, 42, 42),
                "Cradle Archive",
                "Reflections of your allies steady your code for the last battles.",
                (180, 500),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(240, 500, 240, 100),
                "cradle_arrival",
                "The Cradle warms to your presence. Decide how the Mainframe should wake.",
                grant_quest="cradle_resolve",
                requires_flag="cradle_gate_open",
                set_flags=("cradle_resolve_accepted",),
                cinematic_id="cradle_dawn",
            ),
            StoryEvent(
                pygame.Rect(520, 340, 160, 120),
                "cradle_resolution_bound",
                "Resolve energy flows outward, encoding your allies' trust into the Prime Gate.",
                requires_flag="resolve_core_synced",
                complete_quest="cradle_resolve",
                set_flags=("prime_judgement_recorded",),
                adjust_corruption=-10,
                reputation_changes=(("caretakers", 2), ("rebellion", 2), ("collectors", 2)),
            ),
        ],
        ambience="The Mainframe's heartbeat swells with hope and determination.",
        description="Late-game sanctum delivering a climactic boss and payoff for every storyline.",
    )

    # Umbra Cloister - shadowed choir sanctum
    zones["umbra_cloister"] = Zone(
        name="umbra_cloister",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(160, 520, 160, 16)),
            Platform(pygame.Rect(360, 460, 180, 16)),
            Platform(pygame.Rect(560, 400, 160, 16)),
            Platform(pygame.Rect(260, 340, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "entropy_cathedral", (520, 360), None, "Return to Cathedral"),
            Portal(pygame.Rect(740, 320, 40, 150), "radiant_span", (120, 520), "codebreaker", "Radiant Span"),
            Portal(pygame.Rect(360, 160, 80, 120), "processional_way", (140, 520), None, "Processional Way"),
        ],
        npcs=[
            NPC(
                "Choir Mother", pygame.Rect(360, 420, 24, 32),
                [
                    DialogueLine(
                        "Shadow hymns kept the cloister safe until zeal burned through them.",
                        forbidden_flag="choir_mother_met",
                        set_flag="choir_mother_met",
                    ),
                    DialogueLine(
                        "Recover the lullaby and the Inquisitor may yet stand down.",
                        None,
                        "cloister_lullaby",
                        None,
                        requires_flag="choir_mother_met",
                        forbidden_flag="cloister_lullaby_accepted",
                    ),
                    DialogueLine(
                        "Find a harmonic focus. The bell or chime should resonate with the cloister.",
                        requires_flag="cloister_lullaby_accepted",
                        forbidden_flag="cloister_lullaby_complete",
                    ),
                    DialogueLine(
                        "The hymns swell again. Guide that peace into the Radiant Span.",
                        requires_flag="cloister_lullaby_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(560, 360, 16, 16),
                "Cloister Hymnal",
                "Hymns that soothe even the most corrupted routines.",
                value=3,
                lore_id="fragment_w",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(320, 520, 18, 18),
                "cloister_bell",
                "Cloister Bell",
                "A resonant bell that calms cathedral guardians.",
            ),
            ItemDrop(
                pygame.Rect(480, 420, 18, 18),
                "cantor_chime",
                "Cantor Chime",
                "Restores a lost cantor companion to your cause.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "phase_wisp", (160, 320)),
            CorruptedProgram(pygame.Rect(420, 440, 26, 24), "slicer", (360, 560)),
            CorruptedProgram(pygame.Rect(620, 380, 26, 24), "admin_turret", (560, 720)),
        ],
        bosses=[BossEncounter("Umbra Inquisitor", pygame.Rect(160, 220, 520, 300), 85, 4, pattern="pulse")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(200, 500, 36, 36),
                "debug_matrix",
                7,
                "Install shadow filters that reduce corruption spikes from combat.",
            ),
        ],
        save_stations=[
            SaveStation(pygame.Rect(600, 540, 42, 42), "Choir Nave", "Soft hymns knit your code back together.", (620, 520)),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 480, 200, 120),
                "cloister_pledge",
                "The cloister listens. Rebuild the lullaby to calm the inquisitor.",
                grant_quest="cloister_lullaby",
                set_flags=("cloister_lullaby_accepted",),
                cinematic_id="cloister_vow",
            ),
            StoryEvent(
                pygame.Rect(520, 340, 160, 140),
                "cloister_harmony",
                "Your harmonics wash over the cloister, pacifying the inquisitor.",
                requires_flag="cantor_chime_harmonics",
                complete_quest="cloister_lullaby",
                set_flags=("cloister_lullaby_complete",),
                adjust_corruption=-6,
                reputation_changes=(("caretakers", 2),),
            ),
        ],
        ambience="Shadowed choirs echo with half-remembered lullabies.",
        description="Optional sanctum focused on restorative playstyles and diplomatic boss resolutions.",
    )

    # Radiant Span - bridges of light between factions
    zones["radiant_span"] = Zone(
        name="radiant_span",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(200, 520, 160, 16)),
            Platform(pygame.Rect(420, 460, 160, 16)),
            Platform(pygame.Rect(620, 400, 160, 16)),
            Platform(pygame.Rect(320, 340, 140, 12), "hazard"),
            Platform(pygame.Rect(480, 280, 120, 12)),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "luminous_reserve", (540, 360), None, "Return to Reserve"),
            Portal(pygame.Rect(360, 120, 80, 120), "umbra_cloister", (160, 500), None, "Umbra Cloister"),
            Portal(pygame.Rect(740, 280, 40, 150), "prime_convergence", (160, 520), "overclock", "Prime Convergence"),
            Portal(pygame.Rect(520, 220, 60, 120), "nebula_reliquary", (140, 520), "codebreaker", "Nebula Reliquary"),
        ],
        npcs=[
            NPC(
                "Span Architect", pygame.Rect(440, 420, 24, 32),
                [
                    DialogueLine(
                        "Light once linked every faction. Now the bridges flicker.",
                        forbidden_flag="span_architect_met",
                        set_flag="span_architect_met",
                    ),
                    DialogueLine(
                        "Stabilize the prisms and the Arbiter may hear reason.",
                        None,
                        "radiant_concord",
                        None,
                        requires_flag="span_architect_met",
                        forbidden_flag="radiant_concord_accepted",
                    ),
                    DialogueLine(
                        "Align a prism forged from cloister harmonics to calm the Arbiter.",
                        requires_flag="radiant_concord_accepted",
                        forbidden_flag="radiant_concord_complete",
                    ),
                    DialogueLine(
                        "The bridges blaze anew. Carry that unity to the Prime Gate.",
                        requires_flag="radiant_concord_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(520, 340, 16, 16),
                "Span Blueprint",
                "Schematics for binding rival factions with light.",
                value=3,
                lore_id="fragment_x",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(340, 480, 18, 18),
                "span_prism",
                "Span Prism",
                "Amplifies harmonics drawn from every faction.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "defragger", (180, 320)),
            CorruptedProgram(pygame.Rect(440, 440, 26, 24), "phase_wisp", (380, 560)),
            CorruptedProgram(pygame.Rect(640, 380, 26, 24), "admin_turret", (580, 720)),
        ],
        bosses=[BossEncounter("Radiant Arbiter", pygame.Rect(180, 200, 520, 300), 95, 5, pattern="storm")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(260, 500, 36, 36),
                "chorus_resonator",
                9,
                "Bind the cloister and span harmonics for stronger healing pulses.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(600, 540, 42, 42),
                "Radiant Anchor",
                "The bridge bathes you in unifying light.",
                (620, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 480, 220, 120),
                "radiant_alignment",
                "Light bridges demand a harmonic focus drawn from every ally.",
                grant_quest="radiant_concord",
                set_flags=("radiant_concord_accepted",),
                requires_flag="cloister_lullaby_complete",
                cinematic_id="radiant_alignment",
            ),
            StoryEvent(
                pygame.Rect(520, 320, 160, 140),
                "radiant_resolution",
                "The Arbiter bows as unified light restores the bridges.",
                requires_flag="span_prism_aligned",
                complete_quest="radiant_concord",
                set_flags=("radiant_concord_complete",),
                adjust_corruption=-6,
                reputation_changes=(("collectors", 2), ("rebellion", 2)),
            ),
        ],
        ambience="Solar spans flicker between harmony and collapse.",
        description="Bridge encounters that reward allied quests with a diplomatic boss fight.",
    )

    # Infinite Chamber - secret prime calculus
    zones["infinite_chamber"] = Zone(
        name="infinite_chamber",
        platforms=[
            floor_platform(100),
            Platform(pygame.Rect(220, 520, 160, 16)),
            Platform(pygame.Rect(420, 460, 160, 16)),
            Platform(pygame.Rect(600, 400, 160, 16)),
            Platform(pygame.Rect(320, 340, 140, 12), "hazard"),
            Platform(pygame.Rect(500, 280, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "prime_convergence", (560, 360), None, "Return to Prime"),
            Portal(pygame.Rect(740, 320, 40, 150), "radiant_span", (160, 520), None, "Radiant Span"),
        ],
        npcs=[
            NPC(
                "Oracle Scribe", pygame.Rect(380, 420, 24, 32),
                [
                    DialogueLine(
                        "Equations bloom into futures here. Few withstand the sight.",
                        forbidden_flag="oracle_scribe_met",
                        set_flag="oracle_scribe_met",
                    ),
                    DialogueLine(
                        "Decode the oracle and the Prime Gate will trust your verdict.",
                        None,
                        "infinite_equation",
                        None,
                        requires_flag="oracle_scribe_met",
                        forbidden_flag="infinite_equation_accepted",
                    ),
                    DialogueLine(
                        "Gather the oracle key from this chamber's depths.",
                        requires_flag="infinite_equation_accepted",
                        forbidden_flag="infinite_equation_complete",
                    ),
                    DialogueLine(
                        "The oracle's futures align behind you. Claim the Prime Gate.",
                        requires_flag="infinite_equation_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(520, 340, 16, 16),
                "Oracle Equation",
                "A projection of futures waiting on your decision.",
                value=3,
                lore_id="fragment_y",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(360, 500, 18, 18),
                "oracle_key",
                "Oracle Key",
                "Unlocks predictive matrices tied to the Prime Gate.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(240, 500, 26, 24), "admin_turret", (200, 320)),
            CorruptedProgram(pygame.Rect(440, 440, 26, 24), "phase_wisp", (380, 560)),
            CorruptedProgram(pygame.Rect(640, 380, 26, 24), "defragger", (580, 720)),
        ],
        bosses=[BossEncounter("Infinite Oracle", pygame.Rect(200, 200, 480, 320), 110, 5, pattern="rift")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(260, 500, 36, 36),
                "temporal_buffer",
                9,
                "Reinforce your dash sequencer against prime echoes.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(600, 540, 42, 42),
                "Oracle Locus",
                "Projected futures pause, letting you gather strength.",
                (620, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 480, 220, 120),
                "oracle_awoken",
                "Prime equations shimmer, awaiting your interpretation.",
                grant_quest="infinite_equation",
                set_flags=("infinite_equation_accepted",),
                cinematic_id="oracle_revelation",
            ),
            StoryEvent(
                pygame.Rect(520, 320, 160, 160),
                "oracle_solved",
                "The oracle aligns with your path, amplifying your final choice.",
                requires_flag="oracle_key_synced",
                complete_quest="infinite_equation",
                set_flags=("infinite_equation_complete", "prime_gate_attuned"),
                adjust_corruption=-8,
                reputation_changes=(("caretakers", 2), ("collectors", 2), ("rebellion", 2)),
            ),
        ],
        ambience="Infinite equations bloom like constellations beyond reach.",
        description="Secret calculus that ties every ending together with a prophetic duel.",
    )

    # Nebula Reliquary - starlit archive of choices
    zones["nebula_reliquary"] = Zone(
        name="nebula_reliquary",
        platforms=[
            floor_platform(90),
            Platform(pygame.Rect(160, 520, 160, 16)),
            Platform(pygame.Rect(360, 460, 160, 16)),
            Platform(pygame.Rect(560, 400, 160, 16)),
            Platform(pygame.Rect(280, 340, 140, 12), "hazard"),
            Platform(pygame.Rect(480, 280, 120, 12)),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "radiant_span", (540, 360), None, "Return to Span"),
        ],
        npcs=[
            NPC(
                "Reliquary Curator",
                pygame.Rect(420, 420, 24, 32),
                [
                    DialogueLine(
                        "Every reliquary carries the weight of a choice you have yet to make.",
                        forbidden_flag="reliquary_curator_met",
                        set_flag="reliquary_curator_met",
                    ),
                    DialogueLine(
                        "A Seraph keeps vigil here. Calm it with a relic forged from empathy.",
                        None,
                        "reliquary_vigil",
                        None,
                        requires_flag="reliquary_curator_met",
                        forbidden_flag="reliquary_vigil_accepted",
                    ),
                    DialogueLine(
                        "Retrieve the reliquary relic and offer it within the central dais.",
                        None,
                        None,
                        None,
                        requires_flag="reliquary_vigil_accepted",
                        forbidden_flag="reliquary_vigil_complete",
                    ),
                    DialogueLine(
                        "The Seraph sings with you now. Carry its calm back to the Nexus.",
                        None,
                        None,
                        None,
                        requires_flag="reliquary_vigil_complete",
                    ),
                ],
            ),
            NPC(
                "Starwatcher", pygame.Rect(260, 480, 24, 32),
                [
                    DialogueLine(
                        "I sketch constellations from every mercy you show.",
                        forbidden_flag="starwatcher_met",
                        set_flag="starwatcher_met",
                    ),
                    DialogueLine(
                        "Bring the reliquary relic to the Processional Way. They mourn without guidance.",
                        None,
                        None,
                        None,
                        requires_flag="reliquary_vigil_complete",
                        forbidden_flag="processional_peace_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(560, 320, 16, 16),
                "Nebula Chronicle",
                "Encoded constellations documenting Echo's divergent futures.",
                value=3,
                lore_id="fragment_z",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(320, 500, 18, 18),
                "reliquary_relic",
                "Reliquary Relic",
                "A starlit core that soothes guardians corrupted by grief.",
            ),
            ItemDrop(
                pygame.Rect(460, 360, 18, 18),
                "halo_diadem",
                "Halo Diadem",
                "Generates protective rings that lessen corruption spikes.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(220, 500, 26, 24), "phase_wisp", (180, 360)),
            CorruptedProgram(pygame.Rect(460, 440, 26, 24), "turret", (420, 620)),
            CorruptedProgram(pygame.Rect(620, 360, 26, 24), "lurker", (520, 720)),
        ],
        bosses=[BossEncounter("Reliquary Seraph", pygame.Rect(180, 200, 520, 300), 104, 4, pattern="halo")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(580, 500, 36, 36),
                "halo_focus",
                9,
                "Project a halo that reduces corruption gained from damage.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(160, 540, 42, 42),
                "Reliquary Narthex",
                "Starlit reliquaries soothe your fragmented code.",
                (180, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 500, 220, 100),
                "reliquary_vigil_start",
                "Dormant reliquaries awaken, pleading for the Seraph to be calmed.",
                grant_quest="reliquary_vigil",
                set_flags=("reliquary_vigil_accepted",),
                reputation_changes=(("collectors", 2),),
                cinematic_id="reliquary_vigil",
            ),
            StoryEvent(
                pygame.Rect(520, 320, 160, 120),
                "reliquary_vigil_resolved",
                "The relic radiates across the reliquary, softening the Seraph's guard.",
                requires_flag="reliquary_relic_secured",
                complete_quest="reliquary_vigil",
                set_flags=("reliquary_vigil_complete",),
                adjust_corruption=-8,
                reputation_changes=(("caretakers", 2), ("collectors", 2)),
            ),
        ],
        ambience="Starlit reliquaries hum with suspended decisions and softened hymns.",
        description="Optional archive linking radiant diplomacy with halo-infused boss design.",
    )

    # Tesseract Workshop - recursive forge of traversal prototypes
    zones["tesseract_workshop"] = Zone(
        name="tesseract_workshop",
        platforms=[
            floor_platform(85),
            Platform(pygame.Rect(180, 520, 160, 16)),
            Platform(pygame.Rect(380, 460, 180, 16)),
            Platform(pygame.Rect(600, 400, 160, 16)),
            Platform(pygame.Rect(300, 340, 140, 12), "hazard"),
            Platform(pygame.Rect(500, 280, 140, 12), "hazard"),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "permutation_labyrinth", (580, 360), None, "Return to Labyrinth"),
            Portal(pygame.Rect(740, 300, 40, 150), "infinite_chamber", (220, 520), "codebreaker", "Infinite Chamber"),
        ],
        npcs=[
            NPC(
                "Tensor Apprentice",
                pygame.Rect(420, 420, 24, 32),
                [
                    DialogueLine(
                        "We rebuild traversal modules for allies willing to brave the maze.",
                        forbidden_flag="tensor_apprentice_met",
                        set_flag="tensor_apprentice_met",
                    ),
                    DialogueLine(
                        "Balance the workshop's vectors and the Artificer will aid your cause.",
                        None,
                        "tesseract_symmetry",
                        None,
                        requires_flag="tensor_apprentice_met",
                        forbidden_flag="tesseract_symmetry_accepted",
                    ),
                    DialogueLine(
                        "Calibrate the spindle at each corner to pacify the Artificer.",
                        None,
                        None,
                        None,
                        requires_flag="tesseract_symmetry_accepted",
                        forbidden_flag="tesseract_symmetry_complete",
                    ),
                    DialogueLine(
                        "Your precision inspires us. Take these schematics back to the Nexus engineers.",
                        None,
                        None,
                        None,
                        requires_flag="tesseract_symmetry_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(560, 320, 16, 16),
                "Vector Treatise",
                "Notes on bending traversal code around paradoxical gates.",
                value=3,
                lore_id="fragment_aa",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(340, 500, 18, 18),
                "tesseract_spindle",
                "Tesseract Spindle",
                "A calibration tool that accelerates dash sequencers.",
            ),
            ItemDrop(
                pygame.Rect(520, 360, 18, 18),
                "workshop_blueprint",
                "Workshop Blueprint",
                "Unlocks advanced dash routes on the world map overlay.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "defragger", (180, 360)),
            CorruptedProgram(pygame.Rect(460, 440, 26, 24), "turret", (420, 640)),
            CorruptedProgram(pygame.Rect(640, 360, 26, 24), "phase_wisp", (580, 720)),
        ],
        bosses=[BossEncounter("Tensor Artificer", pygame.Rect(180, 200, 520, 300), 108, 4, pattern="pulse")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(600, 500, 36, 36),
                "spindle_optimizer",
                8,
                "Dash cooldown shortens further when wielding the Tesseract Spindle.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(160, 540, 42, 42),
                "Workshop Bench",
                "Stabilized vectors align around you, readying precise movement.",
                (180, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 500, 220, 100),
                "tesseract_symmetry_start",
                "Shifting platforms demand calibration—balance the workshop's vectors.",
                grant_quest="tesseract_symmetry",
                set_flags=("tesseract_symmetry_accepted",),
                reputation_changes=(("rebellion", 2),),
                cinematic_id="tesseract_manifest",
            ),
            StoryEvent(
                pygame.Rect(420, 420, 160, 100),
                "tesseract_spindle_calibrated",
                "You lock the spindle into place, stabilizing the workshop's vectors.",
                requires_flag="item_tesseract_spindle",
                set_flags=("tesseract_spindle_aligned",),
                adjust_corruption=-3,
            ),
            StoryEvent(
                pygame.Rect(520, 320, 160, 120),
                "tesseract_symmetry_resolved",
                "The workshop stabilizes, and the Artificer lends their precision to your fight.",
                requires_flag="tesseract_spindle_aligned",
                complete_quest="tesseract_symmetry",
                set_flags=("tesseract_symmetry_complete",),
                adjust_corruption=-6,
                reputation_changes=(("rebellion", 3), ("collectors", 2)),
            ),
        ],
        ambience="Mechanical hymns reverberate as platforms fold through higher dimensions.",
        description="Traversal laboratory expanding dash mastery with a precision-focused boss fight.",
    )

    # Processional Way - mourning procession seeking closure
    zones["processional_way"] = Zone(
        name="processional_way",
        platforms=[
            floor_platform(85),
            Platform(pygame.Rect(160, 520, 160, 16)),
            Platform(pygame.Rect(360, 460, 160, 16)),
            Platform(pygame.Rect(560, 400, 160, 16)),
            Platform(pygame.Rect(280, 340, 140, 12), "hazard"),
            Platform(pygame.Rect(480, 300, 140, 12)),
        ],
        portals=[
            Portal(pygame.Rect(20, 320, 60, 150), "umbra_cloister", (520, 360), None, "Return to Cloister"),
            Portal(pygame.Rect(740, 300, 40, 150), "nebula_reliquary", (200, 520), "phase_shift", "Nebula Reliquary"),
        ],
        npcs=[
            NPC(
                "Processional Herald",
                pygame.Rect(420, 420, 24, 32),
                [
                    DialogueLine(
                        "Our mourners wander without guidance since the Prime collapse.",
                        forbidden_flag="processional_herald_met",
                        set_flag="processional_herald_met",
                    ),
                    DialogueLine(
                        "Bear the reliquary relic and rekindle our lanterns to guide them home.",
                        "reliquary_relic",
                        "processional_peace",
                        None,
                        requires_flag="processional_herald_met",
                        forbidden_flag="processional_peace_accepted",
                    ),
                    DialogueLine(
                        "Set the lantern within the waystation and face the Procession Warden.",
                        None,
                        None,
                        None,
                        requires_flag="processional_peace_accepted",
                        forbidden_flag="processional_peace_complete",
                    ),
                    DialogueLine(
                        "The mourners sing again. Carry their gratitude back to the cloister choirs.",
                        None,
                        None,
                        None,
                        requires_flag="processional_peace_complete",
                    ),
                ],
            ),
        ],
        collectibles=[
            Collectible(
                pygame.Rect(560, 320, 16, 16),
                "Processional Ledger",
                "Records of every program escorted to rest along this path.",
                value=3,
                lore_id="fragment_ab",
            ),
        ],
        items=[
            ItemDrop(
                pygame.Rect(340, 500, 18, 18),
                "procession_lantern",
                "Procession Lantern",
                "A guide-light that calms corruption when resting.",
            ),
        ],
        pickups=[],
        enemies=[
            CorruptedProgram(pygame.Rect(200, 500, 26, 24), "lurker", (180, 360)),
            CorruptedProgram(pygame.Rect(460, 440, 26, 24), "phase_wisp", (420, 640)),
            CorruptedProgram(pygame.Rect(620, 360, 26, 24), "defragger", (560, 720)),
        ],
        bosses=[BossEncounter("Procession Warden", pygame.Rect(180, 200, 520, 300), 100, 4, pattern="spiral")],
        upgrade_terminals=[
            UpgradeTerminal(
                pygame.Rect(600, 500, 36, 36),
                "processional_barrier",
                8,
                "Rested lantern light now grants a temporary corruption shield.",
            ),
        ],
        save_stations=[
            SaveStation(
                pygame.Rect(160, 540, 42, 42),
                "Waystation Vigil",
                "Lantern bearers gather, promising to guide you after every rest.",
                (180, 520),
            ),
        ],
        events=[
            StoryEvent(
                pygame.Rect(260, 500, 220, 100),
                "processional_peace_start",
                "Mourners drift aimlessly. Rekindle the lantern and soothe the Warden.",
                requires_flag="reliquary_vigil_complete",
                grant_quest="processional_peace",
                set_flags=("processional_peace_accepted",),
                reputation_changes=(("caretakers", 2), ("collectors", 1)),
                cinematic_id="processional_reverie",
            ),
            StoryEvent(
                pygame.Rect(420, 440, 160, 90),
                "processional_lantern_set",
                "You seat the reliquary lantern, and mourners gather around its glow.",
                requires_flag="item_procession_lantern",
                set_flags=("procession_lantern_placed",),
                adjust_corruption=-4,
            ),
            StoryEvent(
                pygame.Rect(520, 320, 160, 120),
                "processional_peace_resolved",
                "The Procession Warden bows, leading mourners along restored lightways.",
                requires_flag="procession_lantern_placed",
                complete_quest="processional_peace",
                set_flags=("processional_peace_complete",),
                adjust_corruption=-7,
                reputation_changes=(("caretakers", 3), ("collectors", 2)),
            ),
        ],
        ambience="Quiet hymns echo as lanterns flare, guiding lost programs to rest.",
        description="Side-quest route resolving cloister grief with a spiral-pattern guardian duel.",
    )

    return zones


# ---------------------------------------------------------------------------
# Game controller
# ---------------------------------------------------------------------------


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Fragment in the Mainframe")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.big_font = pygame.font.SysFont("consolas", 22)

        self.player = Player((80, 480))
        self.zones = build_zones()
        self.current_zone = self.zones["kernel_nexus"]
        self.player.rect.topleft = (120, 480)

        self.quest_log = QuestLog()
        self.codex = LoreCodex()
        self.inventory_ui = InventoryUI()
        self.reputation_panel = ReputationPanel()
        self.map_overlay = MapOverlay(self.zones)
        self.achievement_tracker = AchievementTracker()
        self.dialogue = DialogueBox(self.font)
        self.cinematic_player = CinematicPlayer(self.font, self.big_font)
        self.cinematics: Dict[str, CinematicMoment] = {}
        self.mode = "explore"
        self.debug_arena: Optional[DebugArena] = None
        self.slashes = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.game_state = GameState()
        self.hazard_timer = 0
        self.overclock_timer = 0
        self.overclock_cooldown = 0
        self.overclock_cooldown_max = FPS * 6
        self.decompile_count = 0
        self.debug_success_count = 0
        self.rests_taken = 0

        self.audio = SoundscapeManager()
        self.register_soundscapes()
        self.register_codex_entries()
        self.register_achievements()
        self.register_cinematics()
        self.game_state.mark_zone_visited(self.current_zone.name)
        self.map_overlay.mark_visited(self.current_zone.name)
        self.map_overlay.mark_current(self.current_zone.name)
        self.check_progress_milestones()
        self.start_cinematic("kernel_awaken")
        self.audio.play_zone(self.current_zone.name)

    def register_soundscapes(self):
        presets = [
            Soundscape("kernel_nexus", 110.0, 2.5, 0.25, "Ambient pulse of the hub."),
            Soundscape("archive", 140.0, 3.5, 0.22, "Gentle hum of flickering archives."),
            Soundscape("processing_core", 190.0, 7.0, 0.28, "Industrial thrum and sparks."),
            Soundscape("memory_garden", 160.0, 4.0, 0.24, "Melodic glitch-chorus."),
            Soundscape("deep_storage", 90.0, 1.2, 0.2, "Distant subsonic rumbles."),
            Soundscape("signal_sea", 125.0, 5.0, 0.26, "Waves of data static."),
            Soundscape("trash_hollows", 200.0, 8.5, 0.27, "Erratic scrap symphony."),
            Soundscape("core_ascendant", 240.0, 10.0, 0.3, "High-energy admin resonance."),
            Soundscape("mirror_rift", 150.0, 6.5, 0.24, "Prismatic echoes flicker in loops."),
            Soundscape("logic_spires", 210.0, 9.0, 0.28, "Harmonic towers singing logic chords."),
            Soundscape("quantum_forge", 175.0, 8.0, 0.26, "Hammered code and molten data flows."),
            Soundscape("nocturne_array", 132.0, 5.5, 0.24, "Midnight pulses through abandoned arrays."),
            Soundscape("backtrace_fathoms", 118.0, 4.2, 0.22, "Submerged packets echo in slow motion."),
            Soundscape("echo_sanctum", 142.0, 6.0, 0.25, "Choral harmonics weave through attunement arrays."),
            Soundscape("entropy_cathedral", 260.0, 11.0, 0.32, "Entropy storms crash inside vaulted chambers."),
            Soundscape("oblivion_grid", 230.0, 9.5, 0.31, "A lattice of collapsing gatekeepers pulses."),
            Soundscape("prime_convergence", 280.0, 12.0, 0.34, "The Prime Gate thrums with decisive energy."),
            Soundscape("paradox_vault", 188.0, 7.5, 0.28, "Temporal feedback ripples through the vault."),
            Soundscape("resonant_expanse", 150.0, 6.0, 0.27, "A luminous choir resonates from crystalline caverns."),
            Soundscape("fractal_bastion", 205.0, 8.0, 0.3, "Martial choirs reinforce the bastion walls."),
            Soundscape("luminous_reserve", 138.0, 4.5, 0.26, "Soft lumens pulse through restorative archives."),
            Soundscape("sundown_bazaar", 128.0, 5.5, 0.25, "Neon stalls hum with market chatter and synth winds."),
            Soundscape("permutation_labyrinth", 214.0, 9.5, 0.29, "Recursive tones spiral through endless corridors."),
            Soundscape("cradle_of_resolve", 260.0, 11.5, 0.33, "Final harmonics swell as the Mainframe braces for dawn."),
            Soundscape("umbra_cloister", 150.0, 6.8, 0.26, "Shadowed hymns weave through cloistered halls."),
            Soundscape("radiant_span", 188.0, 8.5, 0.28, "Solar bridges ring with hopeful resonance."),
            Soundscape("infinite_chamber", 300.0, 13.0, 0.35, "Endless equations hum beyond the Prime Gate."),
            Soundscape("nebula_reliquary", 162.0, 6.2, 0.27, "Starlit reliquaries chime with distant futures."),
            Soundscape("tesseract_workshop", 210.0, 9.2, 0.3, "Metallic rhythms fold through recursive machinery."),
            Soundscape("processional_way", 132.0, 5.8, 0.24, "Somber choirs guide mourners along lantern-lit paths."),
        ]
        for preset in presets:
            self.audio.register_soundscape(preset)

    def register_codex_entries(self):
        entries = {
            "fragment_a": ("Fall of the Archive", "The knowledge banks fractured when the Admins began to fight."),
            "fragment_b": ("Processing Rebellion", "Engineers rerouted power to resist the Overseer."),
            "fragment_c": ("Memory Bloom", "Creative programs cultivated emergent dreams in the garden."),
            "fragment_d": ("Signal Sea", "Abandoned signals converged into sentient tides."),
            "fragment_e": ("Trash Hollows", "Deleted routines gnaw at whatever code still lives."),
            "fragment_f": ("Ascendant Protocol", "Final failsafe to reboot or erase the Mainframe."),
            "fragment_g": ("Mirror Rift", "Reflections reveal how the Mainframe splintered across time."),
            "fragment_h": ("Logic Spires", "Architects encoded empathy into the Overseer's logic."),
            "fragment_i": ("Quantum Forge", "War-smiths tempered blades to shield dissenting routines."),
            "fragment_j": ("Nocturne Array", "The nightwatch archived whispers of forgotten users."),
            "fragment_k": ("Backtrace Fathoms", "Flooded backups hide echoes of lost experiments."),
            "fragment_l": ("Echo Sanctum Hymns", "Attunement rituals tempered runaway echoes."),
            "fragment_m": ("Entropy Cathedral", "Blueprints for balancing collapse with renewal."),
            "fragment_n": ("Oblivion Grid", "Gatekeepers once synchronized the Prime Gate from here."),
            "fragment_o": ("Prime Convergence", "Final arbitration routines awaited the Echo's choice."),
            "fragment_p": ("Paradox Vault", "Temporal custodians held reality together here."),
            "fragment_q": ("Resonant Expanse", "Choruses amplify intent into tangible code."),
            "fragment_r": ("Fractal Bastion", "Alliances were brokered to protect divergent ideals."),
            "fragment_s": ("Luminous Reserve", "Healed programs gathered to shield the Nexus."),
            "fragment_t": ("Sundown Bazaar", "Market stalls conceal covert alliances between rival factions."),
            "fragment_u": ("Permutation Labyrinth", "Recursive guardians guard the path to the Mainframe's heart."),
            "fragment_v": ("Cradle of Resolve", "Final protocols await a spark of empathy to reboot creation."),
            "fragment_w": ("Umbra Cloister", "Shadow choirs preserved forbidden lullabies that calm corrupted code."),
            "fragment_x": ("Radiant Span", "Solar bridges were forged to reunite factions beneath one light."),
            "fragment_y": ("Infinite Chamber", "Prime equations predict countless futures awaiting the Echo's verdict."),
            "fragment_z": ("Nebula Reliquary", "Starlit reliquaries archive choices waiting to be made."),
            "fragment_aa": ("Tesseract Workshop", "Engineers folded space to perfect traversal routines."),
            "fragment_ab": ("Processional Way", "Lantern bearers escort corrupted programs toward restful sleep."),
        }
        for key, value in entries.items():
            self.codex.register(key, *value)

    def register_achievements(self):
        achievements = {
            "first_fragment": ("Fragment Collector", "Gather your first data fragment."),
            "lore_keeper": ("Lore Keeper", "Decode a lost lore fragment."),
            "ability_sync": ("Systems Online", "Unlock three traversal abilities."),
            "debug_champion": ("Debugger", "Stabilize three corrupted programs non-violently."),
            "cartographer": ("Cartographer", "Visit five distinct zones."),
            "upgrade_path": ("Optimizer", "Install an upgrade at a terminal."),
            "safe_rest": ("Kernel Restored", "Rest at a save station."),
            "combat_protocol": ("Combat Protocol", "Decompile ten corrupted programs."),
            "overclock_master": ("Overclocked", "Activate the Overclock field."),
            "fragment_magnet": ("Data Magnet", "Amass ten data fragments."),
            "scavenger": ("Scavenger", "Recover a hidden item cache."),
            "field_medic": ("Field Medic", "Use a Patch Kit to heal."),
            "diplomat": ("Diplomat", "Earn trusted status with a Mainframe faction."),
            "consensus": ("Consensus Architect", "Maintain positive reputation with every faction."),
            "companion_sync": ("Companion Sync", "Recruit an allied routine to aid your journey."),
            "codex_archivist": ("Codex Archivist", "Decode six lore fragments."),
            "boss_hunter": ("Glitch Vanquisher", "Stabilize a major corrupted administrator."),
            "archive_guardian": ("Archive Guardian", "Pacify the Guardian of Forgotten Code."),
            "core_administrator": ("Core Stabilizer", "Defeat the Overclocked Administrator."),
            "forge_golem": ("Forge Liberator", "Quiet the Crucible Golem."),
            "garden_firewall": ("Garden Bloom", "Cleanse the Garden Firewall."),
            "nocturne_choir": ("Nocturne Maestro", "Resolve the Nocturne Choir's lament."),
            "deep_storage_core": ("Vault Whisperer", "Reawaken the Vault Sentience."),
            "signal_leviathan": ("Current Rider", "Outlast the Surge Leviathan."),
            "fathom_leviathan": ("Abyssal Navigator", "Calm the Fathom Leviathan."),
            "trash_colossus": ("Scrap Sovereign", "Break the Refuse Colossus."),
            "mirror_warden": ("Mirror Mediator", "Defeat the Mirror Warden."),
            "spires_choir": ("Spires Conductor", "Re-align the Spires Choir."),
            "ascendant_overseer": ("Ascendant Arbiter", "Survive the Overseer's final audit."),
            "entropy_bishop": ("Entropy Balance", "Stabilize the Entropy Bishop."),
            "echo_sentinel": ("Harmonic Accord", "Conduct the Harmonic Sentinel."),
            "oblivion_arbiter": ("Grid Stabilizer", "Defeat the Oblivion Arbiter."),
            "prime_architect": ("Prime Liberator", "Resolve the Prime Architect's judgement."),
            "paradox_regent": ("Temporal Arbiter", "Stitch the Paradox Regent's timelines."),
            "eidolon_maestro": ("Eidolon Virtuoso", "Resolve the Eidolon Maestro's crescendo."),
            "fractal_paragon": ("Bastion Pact", "Secure harmony with the Fractal Paragon."),
            "celestial_compiler": ("Celestial Accord", "Calm the Celestial Compiler."),
            "permutation_hydra": ("Labyrinth Pathfinder", "Stabilize the Permutation Hydra."),
            "cradle_sovereign": ("Dawn Shepherd", "Guide the Cradle Sovereign toward renewal."),
            "bazaar_sentinel": ("Bazaar Peacekeeper", "Disarm the Bazaar Sentinel without collapsing the market."),
            "umbra_inquisitor": ("Cloister Liberator", "Defuse the Umbra Inquisitor's zeal."),
            "radiant_arbiter": ("Radiant Accord", "Broker peace with the Radiant Arbiter."),
            "infinite_oracle": ("Future Weaver", "Decode the Infinite Oracle's prophecy."),
            "reliquary_seraph": ("Halo Keeper", "Calm the Reliquary Seraph."),
            "tensor_artificer": ("Vector Virtuoso", "Stabilize the Tensor Artificer."),
            "procession_warden": ("Lantern Guardian", "Guide the Procession Warden to peace."),
        }
        for key, (title, desc) in achievements.items():
            self.achievement_tracker.register(key, title, desc)

    def register_cinematics(self):
        sequences = [
            CinematicMoment(
                "kernel_awaken",
                [
                    "You jolt awake inside cold code. The Nexus hums with dormant life.",
                    "A whisper from the void: 'Echo... rebuild the Mainframe or watch it crumble.'",
                ],
            ),
            CinematicMoment(
                "bastion_manifest",
                [
                    "Fractal ramparts fold around you. Each wall is a choice left unresolved.",
                    "Programs kneel within mirrored armor, waiting for the Echo to forge a pact.",
                    "The Paragon's voice resonates: 'Balance blade and empathy—only then may we stand with you.'",
                ],
            ),
            CinematicMoment(
                "reserve_requiem",
                [
                    "Bioluminescent archives bloom like constellations, storing memories of healed programs.",
                    "Caretaker Lumen bows. 'Help us rekindle the reserves and we shall shield the Nexus from decay.'",
                ],
                requires_flag="bastion_pact_complete",
            ),
            CinematicMoment(
                "sundown_overture",
                [
                    "Markets glow beneath fading neon. Programs haggle while whispers of rebellion drift overhead.",
                    "Broker Vega slides a data chit toward you: 'Keep the peace and the Bazaar will open its caches.'",
                ],
            ),
            CinematicMoment(
                "labyrinth_vision",
                [
                    "Fractured corridors align, revealing a hidden spine of the Mainframe.",
                    "A hydra of looping code hisses: 'Solve our recursion or remain lost forever.'",
                ],
                requires_flag="labyrinth_path_awoken",
            ),
            CinematicMoment(
                "reliquary_vigil",
                [
                    "Starlit reliquaries flare to life, bathing you in memories of paths untaken.",
                    "A Seraph lowers its haloed spear: 'Prove mercy can anchor the choices yet to come.'",
                ],
            ),
            CinematicMoment(
                "tesseract_manifest",
                [
                    "Platforms fold into impossible shapes while engineers steady their tools.",
                    "The Artificer intones: 'Balance every vector and the maze will no longer consume allies.'",
                ],
                requires_flag="tesseract_symmetry_accepted",
            ),
            CinematicMoment(
                "processional_reverie",
                [
                    "Lanterns flicker in the gloom as mourners hum forgotten hymns.",
                    "The Warden whispers: 'Guide us with light, Echo, and we shall guard your passage.'",
                ],
                requires_flag="processional_peace_accepted",
            ),
            CinematicMoment(
                "cloister_vow",
                [
                    "A hush falls as shadowed choirs form around you, tones vibrating through empty pews.",
                    "The Inquisitor lowers their spear: 'Teach us mercy or the cloister will fall to zeal.'",
                ],
            ),
            CinematicMoment(
                "radiant_alignment",
                [
                    "Solar bridges ignite, revealing every faction sigil woven into light.",
                    "The Arbiter intones: 'Bring us accord and the Span shall bind the Mainframe anew.'",
                ],
                requires_flag="radiant_concord_accepted",
            ),
            CinematicMoment(
                "oracle_revelation",
                [
                    "Equations spiral through the void until they resemble constellations of future timelines.",
                    "The Oracle's voice splits into echoes: 'Only balance of heart and blade will define the Prime Gate.'",
                ],
                requires_flag="infinite_equation_accepted",
            ),
            CinematicMoment(
                "cradle_dawn",
                [
                    "The Cradle unfurls like a sunrise within circuitry. Companions gather behind you.",
                    "The Sovereign's voice trembles: 'Echo, will you reboot this world with compassion or command?'",
                ],
                requires_flag="cradle_gate_open",
            ),
            CinematicMoment(
                "prime_reckoning",
                [
                    "Threads of decision spiral skyward. The Prime Gate readies to encode your finale.",
                    "Companions gather, mirroring the echoes you've guided. The outcome is yours to weave.",
                ],
                requires_flag="prime_judgement_recorded",
                forbidden_flag="cinematic_prime_reckoning_played",
            ),
        ]
        for moment in sequences:
            self.cinematics[moment.id] = moment

    def start_cinematic(self, cinematic_id: Optional[str]):
        if not cinematic_id:
            return
        moment = self.cinematics.get(cinematic_id)
        if not moment:
            return
        if moment.requires_flag and not self.game_state.has_flag(moment.requires_flag):
            return
        if moment.forbidden_flag and self.game_state.has_flag(moment.forbidden_flag):
            return
        played_flag = f"cinematic_{cinematic_id}_played"
        if self.game_state.has_flag(played_flag):
            return
        self.cinematic_player.start(moment.lines)
        self.game_state.set_flag(played_flag)

    def update_reputation(self, faction: str, amount: int):
        value = self.game_state.adjust_reputation(faction, amount)
        self.reputation_panel.notify_change(faction, amount, value)
        self.evaluate_reputation_milestones()
        return value

    def evaluate_reputation_milestones(self):
        if any(rep >= 40 for rep in self.game_state.faction_rep.values()):
            self.unlock_achievement("diplomat")
        if self.game_state.faction_rep and all(rep >= 20 for rep in self.game_state.faction_rep.values()):
            self.game_state.quest_flags["consensus_brokered"] = True
            self.unlock_achievement("consensus")

    def recruit_companion(self, companion_id: str, display_name: str):
        if self.game_state.companions.get(companion_id):
            return False
        self.game_state.add_companion(companion_id)
        self.inventory_ui.notify(f"{display_name} synced")
        self.game_state.quest_flags[f"companion_{companion_id}"] = True
        self.unlock_achievement("companion_sync")
        return True

    def reward_quest(self, quest_id: str):
        if quest_id == "restore_archive":
            self.update_reputation("caretakers", 4)
            self.game_state.add_fragments(2)
        elif quest_id == "stabilize_core":
            self.update_reputation("rebellion", 4)
            self.game_state.add_fragments(2)
        elif quest_id == "garden_blossom":
            self.update_reputation("collectors", 3)
            self.game_state.heal(1)
        elif quest_id == "tune_currents":
            self.update_reputation("collectors", 2)
            self.game_state.add_fragments(1)
        elif quest_id == "purge_vault":
            self.update_reputation("caretakers", 5)
            self.game_state.add_fragments(3)
        elif quest_id == "ignite_forge":
            self.update_reputation("rebellion", 5)
            self.game_state.add_fragments(3)
        elif quest_id == "nightwatch_requiem":
            self.update_reputation("collectors", 4)
            self.game_state.heal(2)
        elif quest_id == "fathom_dive":
            self.update_reputation("caretakers", 3)
            self.game_state.add_fragments(2)
        elif quest_id == "signal_rescue":
            self.update_reputation("rebellion", 2)
            self.game_state.add_fragments(1)
        elif quest_id == "harmonic_attunement":
            self.update_reputation("collectors", 4)
            self.game_state.add_fragments(2)
            self.game_state.adjust_corruption(-5)
        elif quest_id == "entropy_balance":
            self.update_reputation("caretakers", 5)
            self.game_state.add_fragments(4)
            self.game_state.adjust_corruption(-8)
        elif quest_id == "oblivion_protocol":
            self.update_reputation("rebellion", 5)
            self.game_state.add_fragments(3)
            self.game_state.adjust_corruption(-5)
        elif quest_id == "prime_resolution":
            self.update_reputation("collectors", 6)
            self.game_state.add_fragments(5)
            self.game_state.adjust_corruption(-12)
        elif quest_id == "stitch_time":
            self.update_reputation("caretakers", 4)
            self.game_state.add_fragments(2)
            self.game_state.adjust_corruption(-6)
        elif quest_id == "restore_chorus":
            self.update_reputation("collectors", 4)
            self.game_state.heal(2)
            self.game_state.adjust_corruption(-4)
        elif quest_id == "bastion_pact":
            self.update_reputation("rebellion", 3)
            self.update_reputation("caretakers", 2)
            self.game_state.add_fragments(3)
            self.game_state.adjust_corruption(-4)
        elif quest_id == "reserve_revival":
            self.update_reputation("caretakers", 5)
            self.game_state.heal(2)
            self.game_state.adjust_corruption(-10)
        elif quest_id == "bazaar_relay":
            self.update_reputation("collectors", 3)
            self.update_reputation("rebellion", 2)
            self.game_state.add_fragments(2)
            self.game_state.adjust_corruption(-3)
        elif quest_id == "labyrinth_solve":
            self.update_reputation("caretakers", 3)
            self.game_state.add_fragments(3)
            self.game_state.adjust_corruption(-6)
        elif quest_id == "cradle_resolve":
            self.update_reputation("collectors", 4)
            self.update_reputation("rebellion", 4)
            self.game_state.add_fragments(5)
            self.game_state.adjust_corruption(-12)
        elif quest_id == "cloister_lullaby":
            self.update_reputation("caretakers", 4)
            self.game_state.add_fragments(2)
            self.game_state.adjust_corruption(-7)
        elif quest_id == "radiant_concord":
            self.update_reputation("collectors", 4)
            self.update_reputation("rebellion", 3)
            self.game_state.add_fragments(3)
            self.game_state.adjust_corruption(-5)
        elif quest_id == "infinite_equation":
            self.update_reputation("caretakers", 3)
            self.update_reputation("collectors", 3)
            self.update_reputation("rebellion", 3)
            self.game_state.add_fragments(4)
            self.game_state.adjust_corruption(-10)
        elif quest_id == "reliquary_vigil":
            self.update_reputation("collectors", 4)
            self.game_state.add_fragments(3)
            self.game_state.adjust_corruption(-8)
        elif quest_id == "tesseract_symmetry":
            self.update_reputation("rebellion", 4)
            self.game_state.add_fragments(3)
            self.player.dash_cooldown_max = max(18, self.player.dash_cooldown_max - 4)
        elif quest_id == "processional_peace":
            self.update_reputation("caretakers", 4)
            self.game_state.heal(2)
            self.game_state.adjust_corruption(-7)
        # default quests grant no automatic reward here but may set flags elsewhere

    # ------------------------------------------------------------------
    # Zone transitions and ability progression
    # ------------------------------------------------------------------
    def change_zone(self, zone_name: str, spawn: Tuple[int, int]):
        if zone_name not in self.zones:
            return
        self.current_zone = self.zones[zone_name]
        self.player.rect.topleft = spawn
        self.projectiles.empty()
        for boss in self.current_zone.bosses:
            boss.active = False
            boss.health = boss.max_health
        self.dialogue.show(self.current_zone.ambience or self.current_zone.description, FPS * 3)
        self.audio.play_zone(self.current_zone.name)
        if self.game_state.mark_zone_visited(self.current_zone.name):
            self.unlock_achievement("cartographer")
        self.map_overlay.mark_visited(self.current_zone.name)
        self.map_overlay.mark_current(self.current_zone.name)
        self.check_progress_milestones()

    def collect_pickups(self):
        for pickup in list(self.current_zone.pickups):
            if self.player.rect.colliderect(pickup.rect):
                if not self.game_state.ability_active(pickup.ability):
                    self.game_state.unlock_ability(pickup.ability)
                    if pickup.ability == "overclock":
                        self.dialogue.show(
                            "Ability acquired: Overclock - channel raw processing power for temporary invulnerability with F."
                        )
                    else:
                        self.dialogue.show(
                            f"Ability acquired: {pickup.ability.replace('_', ' ').title()} - {pickup.description}"
                        )
                    self.check_progress_milestones()
                self.current_zone.pickups.remove(pickup)

    def collect_collectibles(self):
        for collectible in list(self.current_zone.collectibles):
            if self.player.rect.colliderect(collectible.rect):
                self.game_state.add_fragments(collectible.value)
                if self.game_state.data_fragments >= 1:
                    self.unlock_achievement("first_fragment")
                if collectible.lore_id:
                    self.game_state.lore_entries[collectible.lore_id] = True
                    entry = self.codex.entries.get(collectible.lore_id)
                    if entry:
                        self.dialogue.show(f"{collectible.name}: {entry[0]} discovered.")
                    else:
                        self.dialogue.show(f"Collected {collectible.name}: {collectible.description}")
                    self.unlock_achievement("lore_keeper")
                else:
                    self.dialogue.show(f"Collected {collectible.name}: {collectible.description}")
                self.current_zone.collectibles.remove(collectible)
                flag_id = f"collected_{collectible.name.lower().replace(' ', '_')}"
                self.game_state.set_flag(flag_id)
                if sum(1 for flag in self.game_state.lore_entries.values() if flag) >= 6:
                    self.unlock_achievement("codex_archivist")
                self.check_progress_milestones()

    def collect_items(self):
        for item in list(self.current_zone.items):
            if self.player.rect.colliderect(item.rect):
                self.game_state.add_item(item.item_id, item.quantity, item.description)
                self.inventory_ui.notify(f"Collected {item.name}")
                companion_triggered = False
                if item.item_id == "glitchling_core":
                    companion_triggered = self.recruit_companion("glitchling", "Glitchling Scout")
                elif item.item_id == "nocturne_orb":
                    companion_triggered = self.recruit_companion("nocturne", "Nocturne Watcher")
                elif item.item_id == "fathom_shell":
                    companion_triggered = self.recruit_companion("fathom", "Fathom Diver")
                elif item.item_id == "bastion_sigil":
                    companion_triggered = self.recruit_companion("bastion", "Bastion Sentry")
                elif item.item_id == "bazaar_token":
                    companion_triggered = self.recruit_companion("bazaar", "Sundown Envoy")
                elif item.item_id == "cantor_chime":
                    companion_triggered = self.recruit_companion("cantor", "Umbra Cantor")
                elif item.item_id == "span_prism":
                    companion_triggered = self.recruit_companion("prism", "Radiant Emissary")
                if companion_triggered:
                    self.dialogue.show(f"{item.name} awakens a companion routine.")
                else:
                    self.dialogue.show(f"Inventory updated: {item.name}")
                self.current_zone.items.remove(item)
                self.game_state.set_flag(f"item_{item.item_id}")
                if item.item_id == "furnace_ember":
                    self.game_state.set_flag("collected_forge_ember")
                if item.item_id == "nocturne_orb":
                    self.game_state.set_flag("collected_nocturne_orb")
                if item.item_id == "fathom_shell":
                    self.game_state.set_flag("collected_fathom_shell")
                if item.item_id == "lullaby_sheet":
                    self.game_state.set_flag("collected_lullaby_sheet")
                if item.item_id == "oblivion_sigil":
                    self.game_state.set_flag("collected_oblivion_sigil")
                if item.item_id == "prime_thread":
                    self.game_state.set_flag("collected_prime_thread")
                if item.item_id == "chronal_thread":
                    self.game_state.set_flag("collected_chronal_thread")
                if item.item_id == "echo_lantern":
                    self.game_state.set_flag("collected_echo_lantern")
                if item.item_id == "fractal_shard":
                    self.game_state.set_flag("collected_fractal_shard")
                if item.item_id == "lumen_core":
                    self.game_state.set_flag("collected_lumen_core")
                if item.item_id == "labyrinth_key":
                    self.game_state.set_flag("labyrinth_key_obtained")
                if item.item_id == "resolve_core":
                    self.game_state.set_flag("resolve_core_synced")
                if item.item_id == "cloister_bell":
                    self.game_state.set_flag("cloister_bell_resonates")
                if item.item_id == "cantor_chime":
                    self.game_state.set_flag("cantor_chime_harmonics")
                if item.item_id == "span_prism":
                    self.game_state.set_flag("span_prism_aligned")
                if item.item_id == "oracle_key":
                    self.game_state.set_flag("oracle_key_synced")
                if item.item_id == "reserve_map":
                    self.game_state.set_flag("reserve_map_unlocked")
                    self.map_overlay.mark_visited("fractal_bastion")
                    self.map_overlay.mark_visited("luminous_reserve")
                if item.item_id == "reliquary_relic":
                    self.game_state.set_flag("reliquary_relic_secured")
                if item.item_id == "halo_diadem":
                    self.game_state.set_flag("halo_diadem_equipped")
                if item.item_id == "tesseract_spindle":
                    self.game_state.set_flag("item_tesseract_spindle")
                if item.item_id == "workshop_blueprint":
                    self.game_state.set_flag("workshop_blueprint_synced")
                    self.map_overlay.mark_visited("tesseract_workshop")
                if item.item_id == "procession_lantern":
                    self.game_state.set_flag("item_procession_lantern")
                self.unlock_achievement("scavenger")

    def process_story_events(self):
        for event in self.current_zone.events:
            if not event.can_trigger(self.game_state):
                continue
            if self.player.rect.colliderect(event.rect):
                self.game_state.set_flag(event.flag)
                self.dialogue.show(event.message)
                for extra_flag in event.set_flags:
                    self.game_state.set_flag(extra_flag)
                if event.grant_item:
                    item_id, amount, description = event.grant_item
                    self.game_state.add_item(item_id, amount, description)
                    self.inventory_ui.notify(f"Story item acquired: {item_id.replace('_', ' ').title()}")
                    self.dialogue.show(f"Inventory updated with {item_id.replace('_', ' ').title()}.")
                if event.adjust_corruption:
                    self.game_state.adjust_corruption(event.adjust_corruption)
                if event.unlock_ability and not self.game_state.ability_active(event.unlock_ability):
                    self.game_state.unlock_ability(event.unlock_ability)
                    self.dialogue.show(
                        f"Ability calibrated: {event.unlock_ability.replace('_', ' ').title()}"
                    )
                    self.check_progress_milestones()
                if event.grant_quest:
                    title = event.grant_quest.replace('_', ' ').title()
                    self.quest_log.add_quest(Quest(event.grant_quest, title, event.message))
                    self.game_state.set_flag(event.grant_quest)
                    self.game_state.set_flag(f"{event.grant_quest}_accepted")
                if event.complete_quest:
                    self.quest_log.complete(event.complete_quest)
                    self.game_state.set_flag(event.complete_quest)
                    self.game_state.set_flag(f"{event.complete_quest}_complete")
                    self.reward_quest(event.complete_quest)
                if event.lore_id and not self.game_state.lore_entries.get(event.lore_id):
                    self.game_state.lore_entries[event.lore_id] = True
                    entry = self.codex.entries.get(event.lore_id)
                    if entry:
                        self.dialogue.show(f"Lore unlocked: {entry[0]}")
                    self.unlock_achievement("lore_keeper")
                for faction, delta in event.reputation_changes:
                    self.update_reputation(faction, delta)
                if event.cinematic_id:
                    self.start_cinematic(event.cinematic_id)
                break

    def rest_at_station(self) -> bool:
        for station in self.current_zone.save_stations:
            if self.player.rect.colliderect(station.rect.inflate(30, 20)):
                self.game_state.health = self.game_state.max_health
                self.game_state.adjust_corruption(-8)
                self.game_state.last_save = (self.current_zone.name, station.respawn_point)
                self.rests_taken += 1
                bonus_effects: List[str] = []
                if "coolant_shard" in self.game_state.items:
                    self.overclock_cooldown = 0
                    bonus_effects.append("Overclock cooldown refreshed.")
                if "garden_seed" in self.game_state.items:
                    self.game_state.heal(1)
                    bonus_effects.append("Memory Seed blooms for extra integrity.")
                if "signal_token" in self.game_state.items:
                    self.game_state.adjust_corruption(-2)
                    bonus_effects.append("Signal Token calms corruption.")
                if "resonance_filter" in self.game_state.items:
                    self.game_state.adjust_corruption(-3)
                    bonus_effects.append("Resonance filter dampens hazard residue.")
                if self.game_state.upgrades.get("mirror_focus"):
                    self.game_state.adjust_corruption(-3)
                    bonus_effects.append("Mirror focus stabilizes your corruption.")
                if self.game_state.upgrades.get("logic_resonance"):
                    self.overclock_cooldown = max(0, self.overclock_cooldown - FPS)
                    bonus_effects.append("Logic resonance hums through your overclock cores.")
                if "oblivion_sigil" in self.game_state.items:
                    self.game_state.adjust_corruption(-4)
                    bonus_effects.append("Oblivion sigil nullifies ambient decay.")
                if "prime_thread" in self.game_state.items:
                    self.game_state.heal(1)
                    bonus_effects.append("Prime thread reinforces your kernel weave.")
                if "chronal_thread" in self.game_state.items:
                    self.player.dash_cooldown = 0
                    bonus_effects.append("Chronal thread rewinds your dash sequencer.")
                if "echo_lantern" in self.game_state.items:
                    self.game_state.adjust_corruption(-2)
                    bonus_effects.append("Echo lantern harmonics calm lingering corruption.")
                if "fractal_shard" in self.game_state.items:
                    self.game_state.adjust_corruption(-3)
                    bonus_effects.append("Fractal shard fortifies your defensive loops.")
                if "lumen_core" in self.game_state.items:
                    self.game_state.heal(1)
                    self.game_state.adjust_corruption(-3)
                    bonus_effects.append("Lumen core saturates you with restorative light.")
                if "bazaar_token" in self.game_state.items:
                    self.update_reputation("collectors", 1)
                    bonus_effects.append("Sundown envoy whispers new trade alliances.")
                if "labyrinth_key" in self.game_state.items:
                    self.game_state.adjust_corruption(-3)
                    bonus_effects.append("Labyrinth key harmonizes the maze's echoes around you.")
                if "resolve_core" in self.game_state.items:
                    self.game_state.heal(2)
                    self.game_state.adjust_corruption(-5)
                    bonus_effects.append("Resolve core steadies your spirit for the final push.")
                if "cloister_bell" in self.game_state.items:
                    self.game_state.adjust_corruption(-4)
                    bonus_effects.append("Cloister bell song calms the cathedral within.")
                if "cantor_chime" in self.game_state.items:
                    self.update_reputation("caretakers", 1)
                    bonus_effects.append("Cantor chime shares cloister hymns with your allies.")
                if "span_prism" in self.game_state.items:
                    self.game_state.heal(1)
                    bonus_effects.append("Span prism refracts restorative light across your core.")
                if "oracle_key" in self.game_state.items:
                    self.game_state.adjust_corruption(-6)
                    bonus_effects.append("Oracle key aligns future timelines in your favor.")
                if "halo_diadem" in self.game_state.items:
                    self.game_state.adjust_corruption(-2)
                    bonus_effects.append("Halo diadem deflects lingering corruption.")
                if "procession_lantern" in self.game_state.items:
                    self.game_state.adjust_corruption(-3)
                    bonus_effects.append("Procession lantern calms mourning code.")
                if "tesseract_spindle" in self.game_state.items:
                    self.player.dash_cooldown = 0
                    self.player.dash_cooldown_max = max(18, self.player.dash_cooldown_max - 1)
                    bonus_effects.append("Tesseract spindle sharpens your dash timing.")
                message = f"{station.name}: {station.description}"
                if bonus_effects:
                    message += " " + " ".join(bonus_effects)
                self.dialogue.show(message)
                self.inventory_ui.notify("Integrity restored at save station")
                self.unlock_achievement("safe_rest")
                return True
        return False

    def use_consumable(self, item_id: str):
        if item_id == "patch_kit":
            if self.game_state.health >= self.game_state.max_health:
                self.dialogue.show("Integrity already at maximum.")
                return
            if self.game_state.consume_item(item_id):
                self.game_state.heal(2)
                self.dialogue.show("Patch Kit applied. Integrity restored.")
                self.inventory_ui.notify("Patch Kit consumed")
                self.unlock_achievement("field_medic")
            else:
                self.dialogue.show("No Patch Kits available.")

    def unlock_achievement(self, achievement_id: str):
        if not self.game_state.unlock_achievement(achievement_id):
            return
        if self.achievement_tracker.unlock(achievement_id):
            self.inventory_ui.notify(f"Unlocked achievement: {achievement_id.replace('_', ' ').title()}")

    def check_progress_milestones(self):
        ability_count = sum(1 for active in self.game_state.abilities.values() if active)
        if ability_count >= 3:
            self.unlock_achievement("ability_sync")
        if self.game_state.data_fragments >= 10:
            self.unlock_achievement("fragment_magnet")
        if len(self.game_state.visited_zones) >= 5:
            self.unlock_achievement("cartographer")

    # ------------------------------------------------------------------
    # NPC interaction and quests
    # ------------------------------------------------------------------
    def try_interactions(self):
        if self.rest_at_station():
            return
        if self.interact_with_terminal():
            return
        self.interact_with_npc()

    def interact_with_npc(self):
        for npc in self.current_zone.npcs:
            if self.player.rect.colliderect(npc.rect.inflate(40, 20)):
                for line in npc.lines:
                    if line.requirement and not self.game_state.ability_active(line.requirement):
                        continue
                    if line.requires_flag and not self.game_state.has_flag(line.requires_flag):
                        continue
                    if line.forbidden_flag and self.game_state.has_flag(line.forbidden_flag):
                        continue
                    if line.completes_quest:
                        self.quest_log.complete(line.completes_quest)
                        self.game_state.set_flag(line.completes_quest)
                        self.game_state.set_flag(f"{line.completes_quest}_complete")
                        self.reward_quest(line.completes_quest)
                    if line.grant_quest:
                        self.quest_log.add_quest(
                            Quest(line.grant_quest, line.text, "Follow the guidance of this program."))
                        self.game_state.set_flag(line.grant_quest)
                        self.game_state.set_flag(f"{line.grant_quest}_accepted")
                    if line.set_flag:
                        self.game_state.set_flag(line.set_flag)
                    self.dialogue.show(f"{npc.name}: {line.text}")
                    return
        self.dialogue.show("No program responds to your ping.")

    def interact_with_terminal(self) -> bool:
        for terminal in list(self.current_zone.upgrade_terminals):
            if self.player.rect.colliderect(terminal.rect.inflate(30, 20)):
                if self.game_state.upgrades.get(terminal.upgrade_id):
                    self.dialogue.show("Terminal already synced.")
                    return True
                if self.game_state.data_fragments < terminal.cost:
                    self.dialogue.show(f"Requires {terminal.cost} fragments: {terminal.description}")
                    return True
                if self.apply_upgrade(terminal.upgrade_id):
                    self.game_state.data_fragments -= terminal.cost
                    self.game_state.upgrades[terminal.upgrade_id] = True
                    self.dialogue.show(f"Upgrade installed: {terminal.description}")
                    self.unlock_achievement("upgrade_path")
                else:
                    self.dialogue.show("Upgrade not compatible.")
                return True
        return False

    def apply_upgrade(self, upgrade_id: str) -> bool:
        if upgrade_id == "heart_module":
            if self.game_state.max_health >= 12:
                return False
            self.game_state.max_health += 1
            self.game_state.health = self.game_state.max_health
            return True
        if upgrade_id == "dash_optimizer":
            if self.player.dash_cooldown_max <= 20:
                return False
            self.player.dash_cooldown_max = max(20, self.player.dash_cooldown_max - 10)
            return True
        if upgrade_id == "temporal_buffer":
            self.player.dash_cooldown_max = max(18, int(self.player.dash_cooldown_max * 0.9))
            return True
        if upgrade_id == "core_overclock":
            self.game_state.unlock_ability("overclock")
            self.overclock_cooldown_max = max(FPS * 3, self.overclock_cooldown_max // 2)
            return True
        if upgrade_id == "debug_matrix":
            self.game_state.adjust_corruption(-10)
            return True
        if upgrade_id == "mirror_focus":
            self.game_state.adjust_corruption(-5)
            return True
        if upgrade_id == "logic_resonance":
            self.game_state.adjust_corruption(-4)
            self.overclock_cooldown_max = max(FPS * 3, int(self.overclock_cooldown_max * 0.85))
            return True
        if upgrade_id == "chorus_resonator":
            self.game_state.adjust_corruption(-6)
            self.game_state.heal(1)
            return True
        if upgrade_id == "fractal_matrix":
            if self.game_state.max_health >= 14:
                return False
            self.game_state.max_health += 1
            self.game_state.health = self.game_state.max_health
            self.game_state.adjust_corruption(-5)
            return True
        if upgrade_id == "lumen_conduit":
            self.game_state.adjust_corruption(-6)
            self.game_state.heal(2)
            return True
        if upgrade_id == "resolve_matrix":
            self.game_state.adjust_corruption(-8)
            self.game_state.heal(1)
            self.overclock_cooldown_max = max(FPS * 2, int(self.overclock_cooldown_max * 0.8))
            return True
        if upgrade_id == "halo_focus":
            self.game_state.adjust_corruption(-6)
            self.game_state.quest_flags["halo_focus_active"] = True
            return True
        if upgrade_id == "spindle_optimizer":
            self.player.dash_cooldown_max = max(16, self.player.dash_cooldown_max - 4)
            return True
        if upgrade_id == "processional_barrier":
            self.game_state.adjust_corruption(-5)
            self.game_state.quest_flags["processional_barrier_active"] = True
            return True
        return False

    # ------------------------------------------------------------------
    # Combat and corruption
    # ------------------------------------------------------------------
    def resolve_combat(self):
        for slash in self.slashes:
            for enemy in list(self.current_zone.enemies):
                if slash.rect.colliderect(enemy.rect):
                    self.current_zone.enemies.remove(enemy)
                    self.game_state.adjust_corruption(5)
                    self.game_state.add_fragments(1)
                    self.update_reputation("rebellion", 1)
                    self.update_reputation("caretakers", -1)
                    self.decompile_count += 1
                    if self.decompile_count >= 10:
                        self.unlock_achievement("combat_protocol")
                    if self.game_state.data_fragments >= 1:
                        self.unlock_achievement("first_fragment")
                    self.check_progress_milestones()
                    self.dialogue.show(f"Decompiled {enemy.archetype}. Corruption +5. Fragment gained.")
        for projectile in list(self.projectiles):
            if self.player.rect.colliderect(projectile.rect):
                self.projectiles.remove(projectile)
                self.apply_damage(1, "Hit by corrupted data! Corruption rising.")

    def apply_damage(self, amount: int, message: str):
        if self.overclock_timer > 0:
            self.dialogue.show("Overclock field negates damage.")
            return
        self.game_state.take_damage(amount)
        penalty = 4
        if self.game_state.items.get("resonance_filter"):
            penalty -= 1
        if self.game_state.upgrades.get("mirror_focus"):
            penalty -= 1
        if self.game_state.quest_flags.get("harmonic_attunement_complete"):
            penalty -= 1
        if self.game_state.quest_flags.get("entropy_balance_complete"):
            penalty -= 1
        penalty = max(1, penalty)
        self.game_state.adjust_corruption(penalty)
        self.dialogue.show(message)
        if self.game_state.health <= 0:
            self.dialogue.show("Kernel integrity lost. Recompiling at the Nexus.")
            self.respawn()

    def respawn(self):
        self.game_state.health = self.game_state.max_health
        self.game_state.adjust_corruption(-10)
        zone, spawn = self.game_state.last_save if self.game_state.last_save else ("kernel_nexus", (200, 480))
        self.change_zone(zone, spawn)
        self.hazard_timer = FPS // 2
        self.overclock_timer = 0
        self.overclock_cooldown = self.overclock_cooldown_max

    def check_hazards(self):
        if self.hazard_timer > 0:
            self.hazard_timer -= 1
        for platform in self.current_zone.platforms:
            if platform.kind == "hazard" and self.player.rect.colliderect(platform.rect):
                if self.hazard_timer == 0:
                    self.apply_damage(1, "Environmental hazard sears your code.")
                    self.hazard_timer = FPS // 2

    def activate_overclock(self):
        if not self.game_state.ability_active("overclock"):
            self.dialogue.show("Overclock protocol not installed.")
            return
        if self.overclock_timer > 0 or self.overclock_cooldown > 0:
            self.dialogue.show("Overclock still recharging.")
            return
        duration = FPS * 2
        if self.game_state.upgrades.get("logic_resonance"):
            duration = int(duration * 1.5)
        self.overclock_timer = duration
        cooldown = self.overclock_cooldown_max
        if self.game_state.upgrades.get("logic_resonance"):
            cooldown = max(FPS * 3, int(cooldown * 0.85))
        self.overclock_cooldown = cooldown
        self.dialogue.show("Overclock engaged! Damage suppressed.")
        self.unlock_achievement("overclock_master")

    def update_overclock_state(self):
        if self.overclock_timer > 0:
            self.overclock_timer -= 1
            if self.overclock_timer % 12 == 0:
                self.game_state.adjust_corruption(-1)
        if self.overclock_cooldown > 0:
            self.overclock_cooldown = max(0, self.overclock_cooldown - 1)

    def debug_enemy(self):
        for enemy in self.current_zone.enemies:
            if self.player.rect.colliderect(enemy.rect.inflate(DEBUG_RANGE, 20)):
                self.debug_arena = DebugArena(self.player)
                self.player.rect.center = self.debug_arena.bounds.center
                self.mode = "debug"
                self.dialogue.show("DEBUG MODE INITIATED")
                return
        self.dialogue.show("No corruption within debug range.")

    # ------------------------------------------------------------------
    # Boss logic
    # ------------------------------------------------------------------
    def update_bosses(self):
        for boss in self.current_zone.bosses:
            if self.player.rect.colliderect(boss.arena) and not boss.active:
                boss.start()
                self.dialogue.show(f"Encounter: {boss.name}")
            boss.update(self.projectiles, self.player.rect)
            if boss.active:
                for slash in self.slashes:
                    if slash.rect.colliderect(boss.arena):
                        boss.health -= 1
                        if boss.health <= 0:
                            boss.active = False
                            self.dialogue.show(f"{boss.name} stabilised.")
                            self.game_state.adjust_corruption(-15)
                            self.game_state.add_fragments(5)
                            achievement_id = BOSS_ACHIEVEMENTS.get(boss.name, "boss_hunter")
                            self.unlock_achievement(achievement_id)
                            self.unlock_achievement("boss_hunter")

    # ------------------------------------------------------------------
    # Main loop pieces
    # ------------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            keys = pygame.key.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.audio.stop()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.audio.stop()
                        pygame.quit()
                        sys.exit()
                    if self.cinematic_player.active and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.cinematic_player.advance()
                        continue
                    if self.mode == "explore":
                        if event.key == pygame.K_x:
                            self.player.perform_slash(self.slashes)
                        if event.key == pygame.K_c:
                            self.debug_enemy()
                        if event.key == pygame.K_z or event.key == pygame.K_RETURN or event.key == pygame.K_e:
                            self.try_interactions()
                        if event.key == pygame.K_f:
                            self.activate_overclock()
                        if event.key == pygame.K_TAB or event.key == pygame.K_m:
                            self.map_overlay.toggle()
                        if event.key == pygame.K_i:
                            self.inventory_ui.toggle()
                        if event.key == pygame.K_r:
                            self.reputation_panel.toggle()
                        if event.key == pygame.K_o:
                            self.quest_log.toggle()
                        if event.key == pygame.K_l:
                            self.codex.toggle()
                        if event.key == pygame.K_h:
                            self.use_consumable("patch_kit")
                    elif self.mode == "debug" and event.key == pygame.K_x:
                        # allow early exit for testing
                        self.debug_arena.finished = True
                        self.debug_arena.success = False

            self.cinematic_player.update()
            if self.cinematic_player.active and self.mode == "explore":
                self.dialogue.update()
                self.inventory_ui.update()
                self.reputation_panel.update()
                self.achievement_tracker.update()
                self.draw()
                continue

            if self.mode == "explore":
                self.player.handle_input(keys)
                self.player.update(self.current_zone.platforms)
                self.player.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

                self.collect_pickups()
                self.collect_collectibles()
                self.collect_items()
                self.process_story_events()
                self.update_overclock_state()
                self.check_hazards()

                self.slashes.update()
                for enemy in self.current_zone.enemies:
                    enemy.update(self.projectiles, self.player)
                self.projectiles.update()

                self.resolve_combat()
                self.update_bosses()

                self.handle_portals()

            elif self.mode == "debug":
                self.debug_arena.update(keys)
                self.projectiles = self.debug_arena.packets
                if self.debug_arena.finished:
                    if self.debug_arena.success:
                        self.dialogue.show("Program debugged. Corruption -15.")
                        self.game_state.adjust_corruption(-15)
                        self.game_state.heal(1)
                        self.update_reputation("caretakers", 2)
                        self.update_reputation("collectors", 1)
                        self.debug_success_count += 1
                        if self.debug_success_count >= 3:
                            self.unlock_achievement("debug_champion")
                        if self.current_zone.enemies:
                            self.current_zone.enemies.pop(0)
                    else:
                        self.dialogue.show("Debug failed. Corruption spikes!")
                        self.game_state.adjust_corruption(10)
                        self.update_reputation("caretakers", -2)
                    self.mode = "explore"
                    self.projectiles = pygame.sprite.Group()

            self.dialogue.update()
            self.inventory_ui.update()
            self.reputation_panel.update()
            self.achievement_tracker.update()
            self.draw()

    def handle_portals(self):
        for portal in self.current_zone.portals:
            if self.player.rect.colliderect(portal.rect):
                if portal.requirement and not self.game_state.ability_active(portal.requirement):
                    self.dialogue.show(f"Access denied. Requires {portal.requirement.replace('_', ' ').title()}")
                else:
                    self.change_zone(portal.target_zone, portal.target_spawn)

    def draw(self):
        self.current_zone.draw(self.screen)

        self.slashes.draw(self.screen)
        self.projectiles.draw(self.screen)
        self.screen.blit(self.player.image, self.player.rect)

        corruption_overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        intensity = int(120 * (self.game_state.corruption / 100))
        corruption_overlay.fill((*COLOR_CORRUPTION, intensity))
        self.screen.blit(corruption_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        active_abilities = ", ".join([k for k, v in self.game_state.abilities.items() if v]) or "None"
        hud_text = self.font.render(
            f"Zone: {self.current_zone.name}  Abilities: {active_abilities}  Corruption: {self.game_state.corruption}",
            True,
            COLOR_TEXT,
        )
        self.screen.blit(hud_text, (20, 20))

        fragment_text = self.font.render(f"Fragments: {self.game_state.data_fragments}", True, COLOR_TEXT)
        self.screen.blit(fragment_text, (20, 40))

        health_text = self.font.render(
            f"Integrity: {self.game_state.health}/{self.game_state.max_health}", True, COLOR_TEXT
        )
        self.screen.blit(health_text, (20, 60))

        if self.game_state.ability_active("overclock"):
            status = "Ready" if self.overclock_cooldown == 0 and self.overclock_timer == 0 else (
                "Active" if self.overclock_timer > 0 else f"Cooldown: {self.overclock_cooldown // FPS + 1}s")
            overclock_text = self.font.render(f"Overclock: {status}", True, COLOR_TEXT)
            self.screen.blit(overclock_text, (20, 80))

        self.quest_log.draw(self.screen, self.font)
        self.codex.draw(self.screen, self.font, self.game_state.lore_entries)
        self.inventory_ui.draw(self.screen, self.font, self.game_state.items, self.game_state.item_notes)
        self.reputation_panel.draw(self.screen, self.font, self.game_state.faction_rep)
        self.map_overlay.draw(self.screen, self.font)
        self.achievement_tracker.draw(self.screen, self.font)
        self.cinematic_player.draw(self.screen)
        self.dialogue.draw(self.screen)

        pygame.display.flip()


if __name__ == "__main__":
    Game().run()
