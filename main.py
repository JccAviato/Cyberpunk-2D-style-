"""
Cyber Odyssey — a larger Pygame prototype
----------------------------------------
Controls
- Move: A/D or Left/Right
- Jump: W/Up/Space  (double-jump unlockable via story item)
- Dash: Left Shift  (short burst, has cooldown)
- Attack: J or Z or Left Ctrl
- Interact/Talk/Use: E
- Pause: P   |  Quest Log: Q
- Quick Heal (if you have NanoGels): H
- Save: F5  |  Load: F9
- Restart after death/end: R  | Quit: Esc

Notes
- Purely rectangle/surface visuals (no external art/audio) to stay portable.
- Multiple areas connected by doors, NPCs with branching dialogue,
  side-quests (switches/gates), turrets, a boss, and three endings.
"""
import pygame, sys, json, os
from typing import List, Tuple, Optional, Dict

# -------------------- Settings --------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 960, 540
FPS = 60

GRAVITY = 0.6
PLAYER_SPEED = 4.0
PLAYER_JUMP = 11.0
PLAYER_HEALTH = 6
DASH_SPEED = 11.0
DASH_TIME = 10   # frames
DASH_COOLDOWN = 60  # frames
INVULN_FRAMES = 24

ENEMY_SPEED = 2.0
PROJECTILE_SPEED = 6.0

COLOR_BG   = (12, 14, 18)
COLOR_PLAT = (32, 38, 48)
COLOR_TEXT = (230, 230, 235)
COLOR_PLAYER = (80, 200, 255)
COLOR_ENEMY  = (230, 90, 90)
COLOR_FLY    = (240, 220, 80)
COLOR_BOSS   = (180, 60, 200)
COLOR_TURRET = (120, 120, 220)
COLOR_PROJ   = (255, 110, 40)
COLOR_ATTACK = (255, 230, 60)
COLOR_NPC    = (120, 200, 120)
COLOR_DOOR   = (200, 200, 255)
COLOR_GATE   = (180, 40, 40)
COLOR_SWITCH = (60, 200, 140)
COLOR_CHECK  = (200, 160, 70)

FONT_NAME = None  # default pygame font

# -------------------- Utility --------------------
def clamp(v, a, b):
    return max(a, min(b, v))

# -------------------- Entities --------------------
class AttackBox(pygame.sprite.Sprite):
    def __init__(self, rect: pygame.Rect, frames: int = 10):
        super().__init__()
        self.rect = rect.copy()
        self.frames = frames
    def update(self):
        self.frames -= 1
    def active(self):
        return self.frames > 0

class Player(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int,int]):
        super().__init__()
        self.image = pygame.Surface((36, 52))
        self.image.fill(COLOR_PLAYER)
        self.rect = self.image.get_rect(topleft=pos)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.facing = 1
        self.health = PLAYER_HEALTH
        self.on_ground = False
        self.can_double = False
        self.double_available = False
        # Dash
        self.dash_timer = 0
        self.dash_cooldown = 0
        # Combat/invuln
        self.invuln = 0

        # Progress
        self.flags: Dict[str, bool] = {}    # story/quest flags
        self.inventory: Dict[str, int] = {} # item -> count
        # Respawn
        self.spawn_point = pos

    def give_item(self, name: str, count=1):
        self.inventory[name] = self.inventory.get(name, 0) + count

    def has_item(self, name: str, count=1):
        return self.inventory.get(name, 0) >= count

    def set_flag(self, key: str, value=True):
        self.flags[key] = value

    def get_flag(self, key: str, default=False):
        return self.flags.get(key, default)

    def damage(self, amount: int):
        if self.invuln > 0: 
            return
        self.health -= amount
        self.invuln = INVULN_FRAMES
        if self.health <= 0:
            # Death: respawn at checkpoint/spawn and lose some items (optional)
            self.health = 0

    def heal(self, amount: int):
        self.health = clamp(self.health + amount, 0, PLAYER_HEALTH)

    def try_quick_heal(self):
        if self.has_item("nanogel", 1):
            self.inventory["nanogel"] -= 1
            if self.inventory["nanogel"] <= 0:
                del self.inventory["nanogel"]
            self.heal(2)

    def start_dash(self):
        if self.dash_cooldown == 0 and self.dash_timer == 0:
            self.dash_timer = DASH_TIME
            self.dash_cooldown = DASH_COOLDOWN

    def apply_input(self, keys) -> Optional[AttackBox]:
        # Horizontal
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
            self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
            self.facing = 1

        # Jump
        attack = None
        jump_pressed = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        if jump_pressed and self.on_ground:
            self.vel_y = -PLAYER_JUMP
            self.double_available = self.can_double
        elif jump_pressed and (not self.on_ground) and self.double_available:
            self.vel_y = -PLAYER_JUMP * 0.9
            self.double_available = False

        # Dash
        if keys[pygame.K_LSHIFT]:
            self.start_dash()

        # Attack
        if keys[pygame.K_j] or keys[pygame.K_z] or keys[pygame.K_LCTRL]:
            # Short sword arc: simple rectangle in front
            if self.facing > 0:
                r = pygame.Rect(self.rect.right, self.rect.y+6, 28, 40)
            else:
                r = pygame.Rect(self.rect.left-28, self.rect.y+6, 28, 40)
            attack = AttackBox(r, frames=12)

        # Heal
        if keys[pygame.K_h]:
            self.try_quick_heal()

        return attack

    def physics(self, platforms: List[pygame.Rect]):
        # Dash affects velocity
        if self.dash_timer > 0:
            self.dash_timer -= 1
            self.vel_x = DASH_SPEED * self.facing
        elif self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        # Gravity
        self.vel_y += GRAVITY

        # Horizontal move/collisions
        self.rect.x += int(self.vel_x)
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_x > 0:
                    self.rect.right = p.left
                elif self.vel_x < 0:
                    self.rect.left = p.right

        # Vertical move/collisions
        self.rect.y += int(self.vel_y)
        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_y > 0:
                    self.rect.bottom = p.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = p.bottom
                    self.vel_y = 0

        if self.invuln > 0:
            self.invuln -= 1

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int,int], patrol: Tuple[int,int]):
        super().__init__()
        self.image = pygame.Surface((36, 36))
        self.image.fill(COLOR_ENEMY)
        self.rect = self.image.get_rect(topleft=pos)
        self.patrol = patrol
        self.vel_x = ENEMY_SPEED
        self.vel_y = 0
        self.on_ground = False
        self.health = 3

    def update(self, platforms: List[pygame.Rect], player: Player, atk: Optional[AttackBox]):
        # Simple left-right patrol
        self.rect.x += int(self.vel_x)
        if self.rect.left < self.patrol[0] or self.rect.right > self.patrol[1]:
            self.vel_x *= -1
            self.rect.x += int(self.vel_x)

        # Gravity
        self.vel_y += GRAVITY
        self.rect.y += int(self.vel_y)
        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_y > 0:
                    self.rect.bottom = p.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = p.bottom
                    self.vel_y = 0

        # Attack collision
        if atk and atk.active() and self.rect.colliderect(atk.rect):
            self.health -= 1
            self.vel_x *= -1
            if player.facing > 0:
                self.rect.x += 10
            else:
                self.rect.x -= 10

        # Damage player on touch
        if self.rect.colliderect(player.rect):
            player.damage(1)
            # push back
            if player.rect.centerx < self.rect.centerx:
                player.rect.x -= 18
            else:
                player.rect.x += 18

class FlyingEnemy(Enemy):
    def __init__(self, pos, patrol):
        super().__init__(pos, patrol)
        self.image = pygame.Surface((32, 32))
        self.image.fill(COLOR_FLY)
        self.rect = self.image.get_rect(topleft=pos)
        self.health = 2
    def update(self, platforms, player, atk):
        # Horizontal hover patrol only
        self.rect.x += int(self.vel_x)
        if self.rect.left < self.patrol[0] or self.rect.right > self.patrol[1]:
            self.vel_x *= -1
            self.rect.x += int(self.vel_x)
        if atk and atk.active() and self.rect.colliderect(atk.rect):
            self.health -= 1
            self.vel_x *= -1
        if self.rect.colliderect(player.rect):
            player.damage(1)

class BossEnemy(Enemy):
    def __init__(self, pos, patrol):
        super().__init__(pos, patrol)
        self.image = pygame.Surface((80, 80))
        self.image.fill(COLOR_BOSS)
        self.rect = self.image.get_rect(topleft=pos)
        self.health = 14
        self.vel_x = ENEMY_SPEED * 0.6
    def update(self, platforms, player, atk):
        super().update(platforms, player, atk)
        # Boss deals extra on contact
        if self.rect.colliderect(player.rect):
            player.damage(2)

class Projectile(pygame.sprite.Sprite):
    def __init__(self, rect: pygame.Rect, velx: int):
        super().__init__()
        self.image = pygame.Surface((12, 6))
        self.image.fill(COLOR_PROJ)
        self.rect = rect.copy()
        self.velx = velx
        self.frames = 300
    def update(self, platforms, player: Player):
        self.rect.x += self.velx
        self.frames -= 1
        for p in platforms:
            if self.rect.colliderect(p):
                self.frames = 0
                break
        if self.rect.colliderect(player.rect):
            player.damage(1)
            self.frames = 0
    def alive(self):
        return self.frames > 0

class Turret(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int,int], facing: int = 1, cooldown=90):
        super().__init__()
        self.image = pygame.Surface((28, 28))
        self.image.fill(COLOR_TURRET)
        self.rect = self.image.get_rect(topleft=pos)
        self.facing = 1 if facing >= 0 else -1
        self.cooldown = cooldown
        self.timer = cooldown//2
    def update(self, projectiles: List[Projectile]):
        self.timer -= 1
        if self.timer <= 0:
            self.timer = self.cooldown
            # Fire
            if self.facing > 0:
                start = pygame.Rect(self.rect.right, self.rect.centery-3, 12, 6)
            else:
                start = pygame.Rect(self.rect.left-12, self.rect.centery-3, 12, 6)
            projectiles.append(Projectile(start, PROJECTILE_SPEED * self.facing))

# -------------------- World Objects --------------------
class Door:
    def __init__(self, rect: pygame.Rect, target_level: int, target_pos: Tuple[int,int]):
        self.rect = rect
        self.target_level = target_level
        self.target_pos = target_pos

class Gate:
    """Blocking rectangle that disappears if required flag is set."""
    def __init__(self, rect: pygame.Rect, requires_flag: str):
        self.rect = rect
        self.requires_flag = requires_flag

class Switch:
    """Sets a flag when activated by pressing E while overlapping."""
    def __init__(self, rect: pygame.Rect, sets_flag: str):
        self.rect = rect
        self.sets_flag = sets_flag
        self.activated = False

class NPC:
    def __init__(self, rect: pygame.Rect, name: str, pages: List[str], on_finish=None):
        self.rect = rect
        self.name = name
        self.pages = pages
        self.on_finish = on_finish
        self.talked = False

class Trigger:
    """Auto-trigger lore or checkpoint, no input needed."""
    def __init__(self, rect: pygame.Rect, pages: List[str], kind="lore", data=None):
        self.rect = rect
        self.pages = pages
        self.kind = kind  # lore or checkpoint
        self.data = data or {}
        self.fired = False

class Level:
    def __init__(self, platforms: List[pygame.Rect], enemies, npcs, doors, triggers=None, gates=None, switches=None, turrets=None, boss=None):
        self.platforms = platforms
        self.enemies: List[Enemy] = enemies
        self.npcs: List[NPC] = npcs
        self.doors: List[Door] = doors
        self.triggers: List[Trigger] = triggers or []
        self.gates: List[Gate] = gates or []
        self.switches: List[Switch] = switches or []
        self.turrets: List[Turret] = turrets or []
        self.boss: Optional[BossEnemy] = boss

# -------------------- UI --------------------
class DialogueBox:
    def __init__(self, font, small_font):
        self.font = font
        self.small = small_font
    def draw(self, surf, name: str, text: str):
        box = pygame.Rect(60, SCREEN_HEIGHT-180, SCREEN_WIDTH-120, 140)
        # background
        pygame.draw.rect(surf, (0,0,0), box)
        pygame.draw.rect(surf, (70,72,90), box, 2)
        # name
        if name:
            tag = self.small.render(name, True, COLOR_TEXT)
            surf.blit(tag, (box.x+10, box.y+8))
        # multiline text
        y = box.y+32
        for line in text.split("\n"):
            img = self.font.render(line, True, COLOR_TEXT)
            surf.blit(img, (box.x+10, y))
            y += img.get_height()+4
        hint = self.small.render("Space/Enter: continue", True, (180,180,200))
        surf.blit(hint, (box.x+10, box.bottom-26))

class HUD:
    def __init__(self, font, small):
        self.font, self.small = font, small
    def draw(self, surf, player: Player):
        # Hearts
        for i in range(PLAYER_HEALTH):
            x = 10 + i*24
            y = 10
            rect = pygame.Rect(x, y, 18, 16)
            if i < player.health:
                pygame.draw.rect(surf, (220,40,40), rect)
            else:
                pygame.draw.rect(surf, (100,40,40), rect, 2)
        # Inventory quick view
        x = SCREEN_WIDTH - 260
        inv_title = self.small.render("Inventory:", True, COLOR_TEXT)
        surf.blit(inv_title, (x, 12))
        i = 0
        for k,v in player.inventory.items():
            txt = self.small.render(f"{k}: {v}", True, COLOR_TEXT)
            surf.blit(txt, (x, 30 + i*16))
            i += 1

class PauseOverlay:
    def __init__(self, font, small):
        self.font, self.small = font, small
    def draw(self, surf, player: Player):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        surf.blit(overlay, (0,0))
        title = self.font.render("Paused", True, COLOR_TEXT)
        surf.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 80))
        lines = [
            "Controls: A/D or Arrows move, W/Up/Space jump, LShift dash, J/Z/Ctrl attack, E interact",
            "H: quick heal (consumes NanoGels), Q: quest log, F5: save, F9: load",
        ]
        y = 140
        for ln in lines:
            img = self.small.render(ln, True, COLOR_TEXT)
            surf.blit(img, (SCREEN_WIDTH//2 - img.get_width()//2, y))
            y += img.get_height()+6
        # Stats
        y += 8
        surf.blit(self.small.render(f"Double-jump: {'Unlocked' if player.can_double else 'Locked'}", True, COLOR_TEXT), (160, y)); y+=18
        surf.blit(self.small.render(f"Flags: {', '.join(sorted([k for k,v in player.flags.items() if v])) or '(none)'}", True, COLOR_TEXT), (160, y))

class QuestLogOverlay:
    def __init__(self, font, small):
        self.font, self.small = font, small
    def draw(self, surf, player: Player):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        surf.blit(overlay, (0,0))
        title = self.font.render("Quest Log", True, COLOR_TEXT)
        surf.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 60))
        quests = []
        if not player.get_flag("met_sailor"):
            quests.append("Find the cyber sailor.")
        if not player.get_flag("tinkerer_helped"):
            quests.append("Help the tinkerer power the switch.")
        if player.get_flag("tinkerer_helped") and not player.get_flag("tower_open"):
            quests.append("Reach the tower and confront the sentinel.")
        if player.get_flag("double_unlocked")==False:
            quests.append("Unlock double-jump (seek a mentor).")
        if player.get_flag("final_choice_made")==False:
            quests.append("Make your choice at the portal (1 or 2).")
        if not quests:
            quests = ["Explore freely and seek your ending."]
        y = 120
        for q in quests:
            img = self.small.render("- "+q, True, COLOR_TEXT)
            surf.blit(img, (120, y)); y += 20

# -------------------- Game --------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Cyber Odyssey — Prototype")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(FONT_NAME, 20)
        self.small = pygame.font.Font(FONT_NAME, 16)
        self.big = pygame.font.Font(FONT_NAME, 32)

        self.hud = HUD(self.font, self.small)
        self.dialog = DialogueBox(self.font, self.small)
        self.pause_ui = PauseOverlay(self.big, self.small)
        self.quest_ui = QuestLogOverlay(self.big, self.small)

        self.levels: List[Level] = []
        self.current = 0
        self.player = Player((80, SCREEN_HEIGHT-200))
        self.state = "play"  # play, talk, end, paused, dead
        self.dialog_pages: List[Tuple[str,str]] = []  # list of (name, text) pages
        self.dialog_index = 0
        self.interaction_callback = None
        self.projectiles: List[Projectile] = []

        self.load_world()

    # ----- World assembly -----
    def load_world(self):
        # Helper to build platforms quickly
        def ground(): return pygame.Rect(0, SCREEN_HEIGHT-36, SCREEN_WIDTH, 36)

        # Level 0 — Neon Dock (intro)
        p0 = [ground(), pygame.Rect(120, SCREEN_HEIGHT-180, 180, 16),
              pygame.Rect(360, SCREEN_HEIGHT-270, 160, 16),
              pygame.Rect(640, SCREEN_HEIGHT-350, 160, 16)]
        e0 = [Enemy((380, SCREEN_HEIGHT-306), (360, 520))]
        np0 = [
            NPC(pygame.Rect(140, SCREEN_HEIGHT-196, 34, 52), "Sailor",
                [
                    "I've sailed neon skies and electric seas.",
                    "Treasure isn't coins—it's the bonds you forge.",
                    "Take this NanoGel. When hurt, press H to mend wounds."
                ],
                on_finish=lambda g: g.player.give_item("nanogel", 2) or g.player.set_flag("met_sailor", True))
        ]
        d0 = [Door(pygame.Rect(SCREEN_WIDTH-50, SCREEN_HEIGHT-80, 36, 44), 1, (60, SCREEN_HEIGHT-200))]
        t0 = [
            Trigger(pygame.Rect(660, SCREEN_HEIGHT-366, 40, 16),
                    ["A charred diary speaks of a promise to pass the torch onward."], "lore")
        ]
        lvl0 = Level(p0, e0, np0, d0, triggers=t0)

        # Level 1 — Market Ruins (mid hub)
        p1 = [ground(), pygame.Rect(160, SCREEN_HEIGHT-160, 200, 16),
              pygame.Rect(420, SCREEN_HEIGHT-260, 200, 16),
              pygame.Rect(660, SCREEN_HEIGHT-340, 180, 16)]
        e1 = [Enemy((450, SCREEN_HEIGHT-296), (420, 600)), FlyingEnemy((700, SCREEN_HEIGHT-372), (660, 860))]
        np1 = [
            NPC(pygame.Rect(180, SCREEN_HEIGHT-176, 34, 52), "Mentor",
                [
                    "You're nimble, but the city demands more.",
                    "Focus your will—now leap twice before touching ground.",
                    "Double-jump unlocked."
                ],
                on_finish=lambda g: setattr(g.player, "can_double", True) or g.player.set_flag("double_unlocked", True))
        ]
        d1 = [
            Door(pygame.Rect(10, SCREEN_HEIGHT-80, 36, 44), 0, (SCREEN_WIDTH-80, SCREEN_HEIGHT-200)),
            Door(pygame.Rect(SCREEN_WIDTH-50, SCREEN_HEIGHT-80, 36, 44), 2, (60, SCREEN_HEIGHT-200)),
        ]
        t1 = [
            Trigger(pygame.Rect(670, SCREEN_HEIGHT-356, 46, 16),
                    ["“The abyss smiles wider at the fearless.”"], "lore")
        ]
        lvl1 = Level(p1, e1, np1, d1, triggers=t1)

        # Level 2 — Subterranean Works (switch & gate puzzle + tinkerer)
        p2 = [ground(), pygame.Rect(100, SCREEN_HEIGHT-160, 280, 16),
              pygame.Rect(480, SCREEN_HEIGHT-220, 200, 16),
              pygame.Rect(760, SCREEN_HEIGHT-300, 160, 16)]
        e2 = [Enemy((520, SCREEN_HEIGHT-256), (480, 660))]
        tur2 = [Turret((740, SCREEN_HEIGHT-326), facing=-1, cooldown=80)]
        sw2 = [Switch(pygame.Rect(120, SCREEN_HEIGHT-176, 30, 20), "power_on")]
        ga2 = [Gate(pygame.Rect(600, SCREEN_HEIGHT-76, 80, 40), "power_on")]
        np2 = [
            NPC(pygame.Rect(140, SCREEN_HEIGHT-196, 34, 52), "Tinkerer",
                [
                    "The old conduits need juice. Flip that switch and I'll repay you.",
                    "Good—systems humming again. Take this micro-core and some NanoGels."
                ],
                on_finish=lambda g: (g.player.set_flag("tinkerer_helped", True),
                                     g.player.give_item("micro-core", 1),
                                     g.player.give_item("nanogel", 2)))
        ]
        d2 = [
            Door(pygame.Rect(10, SCREEN_HEIGHT-80, 36, 44), 1, (SCREEN_WIDTH-80, SCREEN_HEIGHT-200)),
            Door(pygame.Rect(SCREEN_WIDTH-50, SCREEN_HEIGHT-80, 36, 44), 3, (60, SCREEN_HEIGHT-200)),
        ]
        t2 = [
            Trigger(pygame.Rect(780, SCREEN_HEIGHT-316, 40, 16),
                    ["A glyph reads: 'Power unlocks passage. Kindness unlocks destiny.'"], "lore")
        ]
        lvl2 = Level(p2, e2, np2, d2, triggers=t2, gates=ga2, switches=sw2, turrets=tur2)

        # Level 3 — Tower Approach (final choice NPC)
        p3 = [ground(), pygame.Rect(200, SCREEN_HEIGHT-160, 220, 16),
              pygame.Rect(480, SCREEN_HEIGHT-220, 180, 16),
              pygame.Rect(720, SCREEN_HEIGHT-300, 160, 16)]
        e3 = [FlyingEnemy((520, SCREEN_HEIGHT-252), (480, 660)),
              Enemy((760, SCREEN_HEIGHT-336), (720, 860))]
        np3 = [
            NPC(pygame.Rect(500, SCREEN_HEIGHT-236, 34, 52), "Warrior",
                [
                    "All journeys meet a gate of shadows.",
                    "Will you defy the darkness, or accept it and grow within it?",
                    "When your heart decides, press 1 to defy, or 2 to accept."
                ],
                on_finish=lambda g: g.player.set_flag("final_choice_ready", True))
        ]
        d3 = [
            Door(pygame.Rect(10, SCREEN_HEIGHT-80, 36, 44), 2, (SCREEN_WIDTH-80, SCREEN_HEIGHT-200)),
            Door(pygame.Rect(SCREEN_WIDTH-50, SCREEN_HEIGHT-80, 36, 44), 4, (60, SCREEN_HEIGHT-200)),
        ]
        t3 = [
            Trigger(pygame.Rect(740, SCREEN_HEIGHT-316, 44, 16),
                    ["A message etched in steel: 'Choice forges fate.'"], "lore")
        ]
        lvl3 = Level(p3, e3, np3, d3, triggers=t3)

        # Level 4 — Tower Interior (boss + ending)
        p4 = [ground(), pygame.Rect(120, SCREEN_HEIGHT-200, 180, 16),
              pygame.Rect(360, SCREEN_HEIGHT-260, 180, 16),
              pygame.Rect(640, SCREEN_HEIGHT-320, 200, 16)]
        e4 = [Enemy((380, SCREEN_HEIGHT-296), (360, 520))]
        boss4 = BossEnemy((660, SCREEN_HEIGHT-400), (620, 860))
        np4 = []
        d4 = [Door(pygame.Rect(10, SCREEN_HEIGHT-80, 36, 44), 3, (SCREEN_WIDTH-80, SCREEN_HEIGHT-200)),
              Door(pygame.Rect(SCREEN_WIDTH-50, SCREEN_HEIGHT-80, 36, 44), 5, (60, SCREEN_HEIGHT-200))]
        t4 = [
            Trigger(pygame.Rect(660, SCREEN_HEIGHT-336, 44, 16),
                    ["You feel the sentinel's gaze. Courage or acceptance—either can be strength."], "lore")
        ]
        lvl4 = Level(p4, e4, np4, d4, triggers=t4, boss=boss4)

        # Level 5 — Epilogue Walkway (ending triggers based on choice)
        p5 = [ground(), pygame.Rect(160, SCREEN_HEIGHT-160, 240, 16),
              pygame.Rect(460, SCREEN_HEIGHT-220, 240, 16),
              pygame.Rect(760, SCREEN_HEIGHT-300, 140, 16)]
        e5 = []
        np5 = []
        d5 = [Door(pygame.Rect(10, SCREEN_HEIGHT-80, 36, 44), 4, (SCREEN_WIDTH-80, SCREEN_HEIGHT-200))]
        t5 = []  # ending handled in code when player reaches far right
        lvl5 = Level(p5, e5, np5, d5, triggers=t5)

        self.levels = [lvl0, lvl1, lvl2, lvl3, lvl4, lvl5]
        self.current = 0
        self.state = "play"
        self.projectiles.clear()
        # default flags
        self.player.flags.setdefault("double_unlocked", False)
        self.player.flags.setdefault("tinkerer_helped", False)
        self.player.flags.setdefault("final_choice_made", False)

    # ----- Save/Load -----
    def save(self, path="save.json"):
        data = {
            "level": self.current,
            "player": {
                "x": self.player.rect.x, "y": self.player.rect.y,
                "health": self.player.health,
                "flags": self.player.flags,
                "inventory": self.player.inventory,
                "can_double": self.player.can_double
            }
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path="save.json"):
        if not os.path.exists(path):
            return
        with open(path) as f:
            data = json.load(f)
        self.current = int(data.get("level", 0))
        p = data.get("player", {})
        self.player.rect.x = int(p.get("x", 80))
        self.player.rect.y = int(p.get("y", SCREEN_HEIGHT-200))
        self.player.health = int(p.get("health", PLAYER_HEALTH))
        self.player.flags = dict(p.get("flags", {}))
        self.player.inventory = dict(p.get("inventory", {}))
        self.player.can_double = bool(p.get("can_double", False))
        self.state = "play"

    # ----- Dialogue -----
    def start_dialog(self, name: str, pages: List[str], callback=None):
        # Store list of (name,text)
        self.dialog_pages = [(name, pg) for pg in pages]
        self.dialog_index = 0
        self.state = "talk"
        self.interaction_callback = callback

    def advance_dialog(self):
        self.dialog_index += 1
        if self.dialog_index >= len(self.dialog_pages):
            # finished
            self.state = "play"
            if self.interaction_callback:
                self.interaction_callback(self)
                self.interaction_callback = None

    # ----- Input & Events -----
    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit(0)
                if ev.key == pygame.K_r and self.state in ("end","dead"):
                    self.__init__(); return
                if ev.key == pygame.K_p and self.state == "play":
                    self.state = "paused"
                elif ev.key == pygame.K_p and self.state == "paused":
                    self.state = "play"
                if ev.key == pygame.K_q and self.state == "play":
                    self.state = "quest"
                elif ev.key == pygame.K_q and self.state == "quest":
                    self.state = "play"
                if ev.key == pygame.K_F5:
                    self.save()
                if ev.key == pygame.K_F9:
                    self.load()

                # Dialogue navigation
                if self.state == "talk" and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.advance_dialog()
                # Choice input (global, but relevant after talking to Warrior)
                if ev.key in (pygame.K_1, pygame.K_KP1):
                    if self.player.get_flag("final_choice_ready", False):
                        self.player.set_flag("final_choice", "defy")
                        self.player.set_flag("final_choice_made", True)
                if ev.key in (pygame.K_2, pygame.K_KP2):
                    if self.player.get_flag("final_choice_ready", False):
                        self.player.set_flag("final_choice", "accept")
                        self.player.set_flag("final_choice_made", True)

    # ----- Update loop -----
    def update_play(self):
        lvl = self.levels[self.current]
        keys = pygame.key.get_pressed()
        attack = self.player.apply_input(keys)
        self.player.physics(lvl.platforms)

        # Attack box tracking
        if attack:
            self._attack = attack
        else:
            self._attack = getattr(self, "_attack", None)
        if self._attack:
            self._attack.update()
            if not self._attack.active():
                self._attack = None

        # Enemies
        for e in list(lvl.enemies):
            e.update(lvl.platforms, self.player, self._attack)
            if e.health <= 0:
                lvl.enemies.remove(e)
                # drop chance
                if len(lvl.enemies) % 2 == 0:
                    self.player.give_item("nanogel", 1)

        # Turrets & projectiles
        for t in lvl.turrets:
            t.update(self.projectiles)
        for pr in list(self.projectiles):
            pr.update(lvl.platforms, self.player)
            if not pr.alive():
                self.projectiles.remove(pr)

        # Boss (if any)
        if lvl.boss:
            lvl.boss.update(lvl.platforms, self.player, self._attack)
            if lvl.boss.health <= 0:
                lvl.boss = None
                self.player.set_flag("boss_defeated", True)

        # Switches
        for sw in lvl.switches:
            if self.player.rect.colliderect(sw.rect):
                keys = pygame.key.get_pressed()
                if keys[pygame.K_e]:
                    sw.activated = True
                    self.player.set_flag(sw.sets_flag, True)

        # Gates block movement unless flag set
        for g in lvl.gates:
            if not self.player.get_flag(g.requires_flag, False):
                # push player outside gate if overlapping
                if self.player.rect.colliderect(g.rect):
                    if self.player.vel_x > 0:
                        self.player.rect.right = g.rect.left
                    elif self.player.vel_x < 0:
                        self.player.rect.left = g.rect.right
                    if self.player.vel_y > 0:
                        self.player.rect.bottom = g.rect.top
                        self.player.vel_y = 0

        # NPC interaction (press E)
        for npc in lvl.npcs:
            if self.player.rect.colliderect(npc.rect):
                if pygame.key.get_pressed()[pygame.K_e]:
                    self.start_dialog(npc.name, npc.pages, npc.on_finish)
                    npc.talked = True

        # Triggers (lore/checkpoint)
        for trig in lvl.triggers:
            if (not trig.fired) and self.player.rect.colliderect(trig.rect):
                trig.fired = True
                if trig.kind == "lore":
                    self.start_dialog("", trig.pages)
                elif trig.kind == "checkpoint":
                    self.player.spawn_point = (self.player.rect.x, self.player.rect.y)

        # Doors
        for d in lvl.doors:
            if self.player.rect.colliderect(d.rect):
                if pygame.key.get_pressed()[pygame.K_e]:
                    self.current = d.target_level
                    self.player.rect.topleft = d.target_pos
                    # clear lingering projectiles on transition
                    self.projectiles.clear()
                    return

        # Death check
        if self.player.health <= 0:
            self.state = "dead"

        # Ending: on Level 5 reaching far right and choice made (and boss defeated)
        if self.current == 5 and self.player.get_flag("final_choice_made", False):
            if self.player.rect.centerx > SCREEN_WIDTH - 80:
                choice = self.player.flags.get("final_choice", "defy")
                pages = []
                if choice == "defy":
                    pages = [
                        "You stood against the dark—unyielding.",
                        "Hope sparks in alleyways and towers alike.",
                        "Your defiance lights the path for others."
                    ]
                elif choice == "accept":
                    pages = [
                        "You embraced the shadow, learned its language.",
                        "In understanding, you protect those who wander.",
                        "Even night can be a guide to dawn."
                    ]
                else:
                    pages = [
                        "You walked a third road—neither denial nor surrender.",
                        "Balance, curiosity, and kindness mark your trail.",
                        "The city hums your name in its circuits."
                    ]
                self.start_dialog("", pages, callback=lambda g: setattr(g, "state", "end"))

    # ----- Draw -----
    def draw(self):
        self.screen.fill(COLOR_BG)
        lvl = self.levels[self.current]
        # platforms
        for p in lvl.platforms:
            pygame.draw.rect(self.screen, COLOR_PLAT, p)
        # gates
        for g in lvl.gates:
            if not self.player.get_flag(g.requires_flag, False):
                pygame.draw.rect(self.screen, COLOR_GATE, g.rect)
        # switches
        for s in lvl.switches:
            pygame.draw.rect(self.screen, COLOR_SWITCH, s.rect, 0 if s.activated else 2)
        # doors
        for d in lvl.doors:
            pygame.draw.rect(self.screen, COLOR_DOOR, d.rect, 2)
        # enemies
        for e in lvl.enemies:
            self.screen.blit(e.image, e.rect)
        # boss
        if lvl.boss:
            self.screen.blit(lvl.boss.image, lvl.boss.rect)
        # turrets
        for t in lvl.turrets:
            self.screen.blit(t.image, t.rect)
        # projectiles
        for pr in self.projectiles:
            self.screen.blit(pr.image, pr.rect)
        # npcs
        for npc in lvl.npcs:
            pygame.draw.rect(self.screen, COLOR_NPC, npc.rect)

        # player (blink if invuln)
        if self.player.invuln % 6 < 4:
            self.screen.blit(self.player.image, self.player.rect)

        # attack box
        if getattr(self, "_attack", None) and self._attack.active():
            pygame.draw.rect(self.screen, COLOR_ATTACK, self._attack.rect, 2)

        # HUD
        self.hud.draw(self.screen, self.player)

        # State overlays
        if self.state == "talk" and self.dialog_pages:
            name, text = self.dialog_pages[self.dialog_index]
            self.dialog.draw(self.screen, name, text)
        elif self.state == "paused":
            self.pause_ui.draw(self.screen, self.player)
        elif self.state == "quest":
            self.quest_ui.draw(self.screen, self.player)
        elif self.state == "dead":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,200))
            self.screen.blit(overlay, (0,0))
            t = self.big.render("You have fallen.", True, (230,70,70))
            self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, 160))
            sub = self.small.render("Press R to restart or Esc to quit.", True, COLOR_TEXT)
            self.screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 210))
        elif self.state == "end":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,200))
            self.screen.blit(overlay, (0,0))
            t = self.big.render("Thank you for playing.", True, COLOR_TEXT)
            self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, 160))
            sub = self.small.render("Press R to restart or Esc to quit.", True, COLOR_TEXT)
            self.screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 210))

        pygame.display.flip()

    # ----- Main loop -----
    def run(self):
        while True:
            self.clock.tick(FPS)
            self.handle_events()
            if self.state == "play":
                self.update_play()
            self.draw()

if __name__ == "__main__":
    try:
        Game().run()
    except Exception as e:
        print("Error:", e)
