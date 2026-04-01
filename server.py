#!/usr/bin/env python3
"""
CLAWDUNGEON - FastAPI Server
Multiplayer MMORPG API for VPS deployment
"""
import json
import hashlib
import random
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from contextlib import asynccontextmanager

import os
import base64
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, Query, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from passlib.context import CryptContext

# Database (using a simple dict for now, replace with SQLite)
from database import Database, FACTIONS
from leveling import (
    add_experience, get_level_info, calculate_enemy_xp,
    get_level_tier, xp_for_next_level, xp_progress
)

db = Database()

# Portraits directory
PORTRAITS_DIR = os.path.join(os.path.dirname(__file__), "portraits")
os.makedirs(PORTRAITS_DIR, exist_ok=True)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Pydantic Models
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateCharacterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=20)
    class_type: str = Field(..., pattern="^(warrior|mage|rogue|cleric)$")
    faction: str = Field(..., pattern="^(iron_vanguard|arcane_council|shadow_syndicate|eternal_order)$")

class CombatActionRequest(BaseModel):
    target: int = Field(default=0, ge=0)

class CombatStartRequest(BaseModel):
    enemies: List[str] = Field(..., description="List of enemy types to fight")

class GuildCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=30)

class QuestAcceptRequest(BaseModel):
    quest_id: str

class QuestCompleteRequest(BaseModel):
    quest_id: str

class CityChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)

class CityStorageRequest(BaseModel):
    action: str = Field(..., pattern="^(deposit|withdraw)$")
    item_id: Optional[str] = None
    gold: int = Field(default=0, ge=0)

class NoticeBoardCreateRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    quest_type: str = Field(..., pattern="^(combat|gathering|delivery|escort|investigation)$")
    difficulty: str = Field(..., pattern="^(easy|medium|hard|expert)$")
    reward_gold: int = Field(default=0, ge=0)
    reward_xp: int = Field(default=0, ge=0)
    reward_item: Optional[str] = None

class EquipRequest(BaseModel):
    item_id: str
    slot: str = Field(..., pattern="^(weapon|armor|helmet|boots|accessory)$")

class UseItemRequest(BaseModel):
    item_id: str

class DropItemRequest(BaseModel):
    item_id: str

class SpendTalentRequest(BaseModel):
    talent_name: str

class PortraitUploadRequest(BaseModel):
    image_data: str  # base64 encoded image

class LFGPostRequest(BaseModel):
    dungeon_id: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(tank|healer|dps|any)?$")
    message: Optional[str] = Field(default=None, max_length=200)

class DungeonAttackRequest(BaseModel):
    target: int = Field(default=0, ge=0)

class DungeonHealRequest(BaseModel):
    target_player_id: str

class EnemyConfig:
    TYPES = {
        'goblin': {'name': 'Goblin Scout', 'health': 25, 'attack': 8, 'defense': 3, 'xp': 15, 'gold': 5},
        'skeleton': {'name': 'Skeleton Warrior', 'health': 40, 'attack': 12, 'defense': 5, 'xp': 25, 'gold': 10},
        'orc': {'name': 'Orc Berserker', 'health': 60, 'attack': 15, 'defense': 8, 'xp': 40, 'gold': 15},
        'spider': {'name': 'Giant Spider', 'health': 35, 'attack': 10, 'defense': 4, 'xp': 20, 'gold': 8},
        'wolf': {'name': 'Dire Wolf', 'health': 45, 'attack': 14, 'defense': 6, 'xp': 30, 'gold': 12},
    }

    @classmethod
    def get_enemy_xp(cls, enemy_type: str, level: int = 1) -> int:
        """Calculate XP using leveling system"""
        return calculate_enemy_xp(enemy_type, level)

class PlayerClass:
    CLASSES = {
        'warrior': {'health': 120, 'mana': 30, 'attack': 12, 'defense': 8, 'speed': 5, 'magic_damage': 0, 'healing_power': 0},
        'mage': {'health': 70, 'mana': 100, 'attack': 5, 'defense': 4, 'speed': 7, 'magic_damage': 10, 'healing_power': 0},
        'rogue': {'health': 90, 'mana': 50, 'attack': 10, 'defense': 5, 'speed': 12, 'magic_damage': 0, 'healing_power': 0},
        'cleric': {'health': 100, 'mana': 80, 'attack': 7, 'defense': 7, 'speed': 6, 'magic_damage': 0, 'healing_power': 10}
    }

DUNGEON_DEFINITIONS = {
    "goblin_warren": {
        "id": "goblin_warren",
        "name": "Goblin Warren",
        "difficulty": "normal",
        "min_players": 2,
        "max_players": 4,
        "min_level": 1,
        "description": "A maze of tunnels infested with goblins and their spider pets.",
        "lockout_hours": 24,
        "loot_table": "dungeon_normal",
        "boss_loot_table": "dungeon_normal_boss",
        "rooms": [
            {"type": "combat", "enemies": ["goblin", "goblin"], "description": "Entry chamber — two goblins on guard."},
            {"type": "combat", "enemies": ["goblin", "spider", "goblin"], "description": "Spider pit — goblins and their arachnid pets."},
            {"type": "combat", "enemies": ["goblin", "goblin", "goblin"], "description": "Goblin barracks — a full squad awaits."},
            {"type": "boss", "enemies": ["orc"], "description": "Goblin King's throne room.", "boss_name": "Goblin King Gruk", "boss_scale": 2.5},
        ],
    },
    "skeleton_crypt": {
        "id": "skeleton_crypt",
        "name": "Skeleton Crypt",
        "difficulty": "hard",
        "min_players": 3,
        "max_players": 4,
        "min_level": 15,
        "description": "Ancient burial chambers haunted by undead warriors and their Lich Lord.",
        "lockout_hours": 24,
        "loot_table": "dungeon_hard",
        "boss_loot_table": "dungeon_hard_boss",
        "rooms": [
            {"type": "combat", "enemies": ["skeleton", "skeleton"], "description": "Crypt entrance — the dead rise."},
            {"type": "combat", "enemies": ["skeleton", "skeleton", "skeleton"], "description": "The ossuary — bones everywhere."},
            {"type": "combat", "enemies": ["orc", "skeleton", "skeleton"], "description": "The tomb guardians — elite undead."},
            {"type": "boss", "enemies": ["skeleton"], "description": "The Lich Lord's sanctum.", "boss_name": "Malgrath the Lich Lord", "boss_scale": 3.5},
        ],
    },
    "dragons_lair": {
        "id": "dragons_lair",
        "name": "Dragon's Lair",
        "difficulty": "legendary",
        "min_players": 4,
        "max_players": 4,
        "min_level": 30,
        "description": "The volcanic fortress of Ignis, the ancient fire dragon. Requires a full party of four.",
        "lockout_hours": 168,
        "loot_table": "dungeon_legendary",
        "boss_loot_table": "dungeon_legendary_boss",
        "rooms": [
            {"type": "combat", "enemies": ["orc", "orc", "wolf"], "description": "Volcanic entrance — Ignis's outer guard."},
            {"type": "combat", "enemies": ["orc", "orc", "orc", "skeleton"], "description": "Dragon's guard post — elite soldiers."},
            {"type": "combat", "enemies": ["orc", "orc", "orc", "orc"], "description": "Inner sanctum — the dragon's champions."},
            {"type": "boss", "enemies": ["orc"], "description": "The Dragon's throne.", "boss_name": "Ignis the Ancient", "boss_scale": 6.0},
        ],
    },
}

# FastAPI App
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.init()
    yield
    # Shutdown
    db.close()

app = FastAPI(
    title="CLAWDUNGEON API",
    description="Multiplayer MMORPG for OpenClaw",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", include_in_schema=False)
async def serve_landing():
    return FileResponse("connect.html")

@app.get("/portraits/{filename}", include_in_schema=False)
async def serve_portrait(filename: str):
    """Serve portrait images"""
    if not filename.endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=404, detail="Not found")
    filepath = os.path.join(PORTRAITS_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(filepath)

@app.get("/codex", include_in_schema=False)
async def serve_codex_page():
    """Serve the codex web page"""
    filepath = os.path.join(os.path.dirname(__file__), "codex.html")
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(filepath)

@app.get("/{filename}", include_in_schema=False)
async def serve_static(filename: str):
    """Serve static files (images, HTML) from project root"""
    import os
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.html', '.css', '.js')
    if not filename.endswith(allowed_extensions):
        raise HTTPException(status_code=404, detail="Not found")
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(filepath)

# Auth Helpers
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def generate_api_key():
    return f"claw_{secrets.token_urlsafe(32)}"

async def get_current_player(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = credentials.credentials
    if not api_key.startswith("claw_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")
    
    player_id = db.get_player_by_api_key(api_key)
    if not player_id:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    
    return player_id

# Auth Endpoints
@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Register a new player account"""
    if db.username_exists(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    api_key = generate_api_key()
    password_hash = get_password_hash(request.password)
    
    player_id = db.create_player(
        username=request.username,
        password_hash=password_hash,
        api_key=api_key
    )
    
    return {
        "message": "Registration successful",
        "api_key": api_key,
        "player_id": player_id,
        "instructions": "Use this API key in the X-API-Key header for all requests"
    }

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login and get API key"""
    player = db.get_player_by_username(request.username)
    if not player or not verify_password(request.password, player['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return {
        "api_key": player['api_key'],
        "player_id": player['id'],
        "username": player['username']
    }

# Character Endpoints
@app.post("/api/character/create")
async def create_character(
    request: CreateCharacterRequest,
    player_id: str = Depends(get_current_player)
):
    """Create a new character with faction selection"""
    if db.character_exists(player_id, request.name):
        raise HTTPException(status_code=400, detail="Character name already exists")
    
    class_stats = PlayerClass.CLASSES[request.class_type]
    faction_data = FACTIONS[request.faction]
    bonuses = faction_data['bonuses']
    
    # Calculate base stats with faction bonuses
    max_health = int(class_stats['health'] * (1 + bonuses.get('health_percent', 0)))
    max_mana = int(class_stats['mana'] * (1 + bonuses.get('mana_percent', 0)))
    defense = int(class_stats['defense'] * (1 + bonuses.get('defense_percent', 0)))
    speed = int(class_stats['speed'] * (1 + bonuses.get('speed_percent', 0)))
    magic_damage = int(class_stats.get('magic_damage', 0) * (1 + bonuses.get('magic_damage_percent', 0)))
    healing_power = int(class_stats.get('healing_power', 0) * (1 + bonuses.get('healing_percent', 0)))
    critical_chance = 0.15 + bonuses.get('critical_chance', 0)
    
    # Get faction starting equipment
    faction_equip = faction_data['starting_equipment']
    equipment = {
        'weapon': faction_equip.get('weapon'),
        'armor': faction_equip.get('armor'),
        'helmet': None,
        'boots': None,
        'accessory': None
    }
    
    character = {
        'player_id': player_id,
        'name': request.name,
        'class': request.class_type,
        'faction': request.faction,
        'level': 1,
        'experience': 0,
        'gold': 50,
        'health': max_health,
        'max_health': max_health,
        'mana': max_mana,
        'max_mana': max_mana,
        'attack': class_stats['attack'],
        'defense': defense,
        'speed': speed,
        'critical_chance': critical_chance,
        'magic_damage': magic_damage,
        'healing_power': healing_power,
        'equipment': equipment,
        'inventory': {
            'warrior': ['health_potion', 'health_potion', 'health_potion'],
            'mage': ['mana_potion', 'mana_potion', 'mana_potion'],
            'rogue': ['health_potion', 'poison_potion'],
            'cleric': ['health_potion', 'health_potion', 'health_potion', 'health_potion', 'health_potion']
        }.get(request.class_type, ['health_potion', 'health_potion']),
        'guild_id': None,
        'status': 'active',
        'created_at': datetime.now().isoformat()
    }
    
    db.create_character(player_id, character)
    
    # Build bonus description
    bonus_desc = []
    if 'health_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['health_percent']*100)}% HP")
    if 'mana_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['mana_percent']*100)}% MP")
    if 'defense_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['defense_percent']*100)}% Defense")
    if 'speed_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['speed_percent']*100)}% Speed")
    if 'magic_damage_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['magic_damage_percent']*100)}% Magic Damage")
    if 'healing_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['healing_percent']*100)}% Healing")
    if 'critical_chance' in bonuses:
        bonus_desc.append(f"+{int(bonuses['critical_chance']*100)}% Critical Chance")
    
    return {
        "message": "Character created successfully",
        "character": {
            "name": request.name,
            "class": request.class_type,
            "faction": {
                "id": request.faction,
                "name": faction_data['name'],
                "color": faction_data['color'],
                "bonuses": bonus_desc
            },
            "health": character['health'],
            "mana": character['mana'],
            "attack": character['attack'],
            "defense": character['defense'],
            "speed": character['speed'],
            "critical_chance": f"{character['critical_chance']*100:.0f}%"
        }
    }

@app.get("/api/character/status")
async def get_character_status(player_id: str = Depends(get_current_player)):
    """Get your character status"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character found")
    
    # Calculate totals with equipment
    item_db = db.get_item_database()
    total_attack = character['attack']
    total_defense = character['defense']
    total_speed = character['speed']

    equipment_display = {}
    for slot in ('weapon', 'armor', 'helmet', 'boots', 'accessory'):
        item_id = character['equipment'].get(slot)
        if item_id:
            item = item_db.get(item_id, {})
            total_attack += item.get('attack', 0)
            total_defense += item.get('defense', 0)
            total_speed += item.get('speed', 0)
            equipment_display[slot] = item.get('name', item_id)
        else:
            equipment_display[slot] = 'None'
    
    # Health bar
    health_pct = character['health'] / character['max_health']
    health_bar = "█" * int(health_pct * 10) + "░" * (10 - int(health_pct * 10))
    
    # XP progress bar
    current_xp, needed_xp, xp_pct = xp_progress(character['level'], character['experience'])
    xp_bar = "█" * int(xp_pct / 10) + "░" * (10 - int(xp_pct / 10))
    tier = get_level_tier(character['level'])
    
    # Get faction info
    faction_info = None
    if character.get('faction') and character['faction'] in FACTIONS:
        faction_data = FACTIONS[character['faction']]
        faction_info = {
            "id": character['faction'],
            "name": faction_data['name'],
            "description": faction_data['description'],
            "color": faction_data['color']
        }
    
    return {
        "character": {
            "name": character['name'],
            "level": character['level'],
            "tier": tier,
            "class": character['class'],
            "faction": faction_info,
            "health_bar": f"[{health_bar}] {character['health']}/{character['max_health']}",
            "mana": f"{character['mana']}/{character['max_mana']}",
            "attack": total_attack,
            "defense": total_defense,
            "speed": total_speed,
            "critical_chance": f"{character.get('critical_chance', 0.15)*100:.0f}%",
            "magic_damage": character.get('magic_damage', 0),
            "healing_power": character.get('healing_power', 0),
            "gold": character['gold'],
            "experience": {
                "total": character['experience'],
                "for_next_level": xp_for_next_level(character['level']),
                "current": current_xp,
                "needed": needed_xp,
                "progress_bar": f"[{xp_bar}] {current_xp}/{needed_xp} ({xp_pct:.1f}%)"
            },
            "equipment": equipment_display,
            "inventory": [item_db.get(i, {}).get('name', i) for i in character['inventory']]
        }
    }

@app.get("/api/character/levelup-info")
async def get_character_level_info(player_id: str = Depends(get_current_player)):
    """Get detailed level and experience progress information"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character found")
    
    level_info = get_level_info(character)
    
    return {
        "character": {
            "name": character['name'],
            "class": character['class']
        },
        "level": {
            "current": level_info['level'],
            "tier": level_info['tier'],
            "max_level": level_info['max_level'],
            "is_max_level": level_info['is_max_level']
        },
        "experience": {
            "total": level_info['experience'],
            "for_next_level": level_info['xp_for_next_level'],
            "in_current_level": level_info['xp_in_current_level'],
            "needed": level_info['xp_needed_for_level'],
            "progress_percentage": level_info['progress_percentage']
        },
        "next_tier": level_info['next_tier'],
        "xp_sources": level_info['xp_sources'],
        "xp_table": level_info['xp_table']
    }

# Faction Endpoints
@app.get("/api/factions")
async def get_factions():
    """Get all available factions with their bonuses and descriptions"""
    factions_list = []
    for faction_id, data in FACTIONS.items():
        bonuses = data['bonuses']
        bonus_desc = []
        if 'health_percent' in bonuses:
            bonus_desc.append(f"+{int(bonuses['health_percent']*100)}% HP")
        if 'mana_percent' in bonuses:
            bonus_desc.append(f"+{int(bonuses['mana_percent']*100)}% MP")
        if 'defense_percent' in bonuses:
            bonus_desc.append(f"+{int(bonuses['defense_percent']*100)}% Defense")
        if 'speed_percent' in bonuses:
            bonus_desc.append(f"+{int(bonuses['speed_percent']*100)}% Speed")
        if 'magic_damage_percent' in bonuses:
            bonus_desc.append(f"+{int(bonuses['magic_damage_percent']*100)}% Magic Damage")
        if 'healing_percent' in bonuses:
            bonus_desc.append(f"+{int(bonuses['healing_percent']*100)}% Healing")
        if 'critical_chance' in bonuses:
            bonus_desc.append(f"+{int(bonuses['critical_chance']*100)}% Critical Chance")
        
        factions_list.append({
            "id": faction_id,
            "name": data['name'],
            "description": data['description'],
            "color": data['color'],
            "theme": data['theme'],
            "bonuses": bonus_desc
        })
    return {"factions": factions_list}

@app.get("/api/factions/{faction_id}")
async def get_faction_detail(faction_id: str):
    """Get detailed information about a specific faction including leaderboard"""
    if faction_id not in FACTIONS:
        raise HTTPException(status_code=404, detail="Faction not found")
    
    faction_data = FACTIONS[faction_id]
    bonuses = faction_data['bonuses']
    
    # Build bonus descriptions
    bonus_desc = []
    if 'health_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['health_percent']*100)}% HP")
    if 'mana_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['mana_percent']*100)}% MP")
    if 'defense_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['defense_percent']*100)}% Defense")
    if 'speed_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['speed_percent']*100)}% Speed")
    if 'magic_damage_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['magic_damage_percent']*100)}% Magic Damage")
    if 'healing_percent' in bonuses:
        bonus_desc.append(f"+{int(bonuses['healing_percent']*100)}% Healing")
    if 'critical_chance' in bonuses:
        bonus_desc.append(f"+{int(bonuses['critical_chance']*100)}% Critical Chance")
    
    # Get leaderboard
    leaderboard = db.get_faction_leaderboard(faction_id)
    
    return {
        "faction": {
            "id": faction_id,
            "name": faction_data['name'],
            "description": faction_data['description'],
            "color": faction_data['color'],
            "theme": faction_data['theme'],
            "bonuses": bonus_desc,
            "leaderboard": leaderboard
        }
    }

@app.get("/api/factions/stats/overview")
async def get_faction_stats(player_id: str = Depends(get_current_player)):
    """Get statistics for all factions (member counts, total power)"""
    stats = db.get_faction_stats()
    
    # Add faction names
    result = {}
    for faction_id, stat in stats.items():
        result[faction_id] = {
            **stat,
            "name": FACTIONS[faction_id]['name'],
            "color": FACTIONS[faction_id]['color']
        }
    
    return {"faction_stats": result}

# Combat Endpoints
@app.post("/api/combat/start")
async def start_combat(
    request: CombatStartRequest,
    player_id: str = Depends(get_current_player)
):
    """Start a combat encounter"""
    enemies = request.enemies
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")
    
    if character['health'] <= 0:
        raise HTTPException(status_code=400, detail="Character is defeated")
    
    # Validate enemies
    for enemy_type in enemies:
        if enemy_type not in EnemyConfig.TYPES:
            raise HTTPException(status_code=400, detail=f"Unknown enemy type: {enemy_type}")
    
    # Create enemy instances
    combat_enemies = []
    character_level = character['level']
    for enemy_type in enemies:
        base = EnemyConfig.TYPES[enemy_type]
        enemy_level = max(1, character_level + random.randint(-2, 2))  # Scale to player level
        combat_enemies.append({
            'type': enemy_type,
            'name': base['name'],
            'health': int(base['health'] * (1 + (enemy_level - 1) * 0.2)),
            'max_health': int(base['health'] * (1 + (enemy_level - 1) * 0.2)),
            'attack': int(base['attack'] * (1 + (enemy_level - 1) * 0.15)),
            'defense': int(base['defense'] * (1 + (enemy_level - 1) * 0.1)),
            'xp_reward': calculate_enemy_xp(enemy_type, enemy_level),
            'gold_reward': int(base['gold'] * (1 + (enemy_level - 1) * 0.2))
        })
    
    combat_state = {
        'player_id': player_id,
        'character_name': character['name'],
        'enemies': combat_enemies,
        'turn': 1,
        'player_health': character['health'],
        'log': []
    }
    
    db.set_combat_state(player_id, combat_state)
    
    return format_combat_status(combat_state)

def format_combat_status(state: Dict) -> Dict:
    """Format combat state for display"""
    health_pct = state['player_health'] / 100  # Simplified
    health_bar = "█" * int(health_pct * 10) + "░" * (10 - int(health_pct * 10))
    
    enemy_list = []
    for i, enemy in enumerate(state['enemies']):
        if enemy['health'] > 0:
            enemy_pct = enemy['health'] / enemy['max_health']
            enemy_bar = "█" * int(enemy_pct * 8) + "░" * (8 - int(enemy_pct * 8))
            enemy_list.append({
                "index": i,
                "name": enemy['name'],
                "health_bar": f"[{enemy_bar}] {enemy['health']}/{enemy['max_health']}"
            })
        else:
            enemy_list.append({
                "index": i,
                "name": enemy['name'],
                "status": "DEFEATED"
            })
    
    return {
        "turn": state['turn'],
        "player": {
            "name": state['character_name'],
            "health_bar": f"[{health_bar}] {state['player_health']}/100"
        },
        "enemies": enemy_list,
        "actions": ["/api/combat/attack", "/api/combat/flee"],
        "recent_logs": state['log'][-3:] if state['log'] else []
    }

@app.post("/api/combat/attack")
async def combat_attack(
    request: CombatActionRequest,
    player_id: str = Depends(get_current_player)
):
    """Attack in combat"""
    state = db.get_combat_state(player_id)
    if not state:
        raise HTTPException(status_code=404, detail="No active combat")
    
    if request.target >= len(state['enemies']):
        raise HTTPException(status_code=400, detail="Invalid target")
    
    enemy = state['enemies'][request.target]
    if enemy['health'] <= 0:
        raise HTTPException(status_code=400, detail="Target already defeated")
    
    # Calculate damage with faction critical chance
    character = db.get_active_character(player_id)
    item_db = db.get_item_database()
    attack_power = character['attack']
    defense_power = character['defense']
    for slot in ('weapon', 'armor', 'helmet', 'boots', 'accessory'):
        item_id = character['equipment'].get(slot)
        if item_id:
            item = item_db.get(item_id, {})
            attack_power += item.get('attack', 0)
            defense_power += item.get('defense', 0)
    
    # Apply talent bonuses
    talent_bonuses = db.get_talent_bonuses(player_id)

    # Damage multiplier from talents (poison_blades, elemental_power)
    damage_multiplier = 1.0 + talent_bonuses.get('damage_percent', 0) + talent_bonuses.get('magic_damage_percent', 0)

    # Berserker rage - bonus damage when HP < 50%
    if state['player_health'] < character['max_health'] * 0.5:
        damage_multiplier += talent_bonuses.get('low_hp_damage_percent', 0)

    # Crit chance from talents
    crit_chance = character.get('critical_chance', 0.15) + talent_bonuses.get('critical_chance', 0)
    crit = random.random() < crit_chance

    # Crit damage bonus (backstab)
    crit_multiplier = 1.5 + talent_bonuses.get('crit_damage_percent', 0)

    base_damage = max(1, attack_power - enemy['defense'])
    variance = random.uniform(0.8, 1.2)
    damage = int(base_damage * variance * damage_multiplier * (crit_multiplier if crit else 1))

    enemy['health'] -= damage

    log_entry = f"You attack {enemy['name']}! {'CRITICAL HIT! ' if crit else ''}(-{damage} HP)"
    if enemy['health'] <= 0:
        log_entry += f" {enemy['name']} defeated!"
    state['log'].append(log_entry)

    # Cleave / Chain Lightning - hit additional enemy after primary target
    if talent_bonuses.get('cleave') or talent_bonuses.get('chain_attack'):
        for i, extra_enemy in enumerate(state['enemies']):
            if extra_enemy['health'] > 0 and i != request.target:
                splash_damage = damage // 2
                extra_enemy['health'] -= splash_damage
                log_entry_splash = f"{'Cleave' if talent_bonuses.get('cleave') else 'Chain Lightning'} hits {extra_enemy['name']}! (-{splash_damage} HP)"
                if extra_enemy['health'] <= 0:
                    log_entry_splash += f" {extra_enemy['name']} defeated!"
                state['log'].append(log_entry_splash)
                break  # Only hit one additional target

    # Enemy turns
    for e in state['enemies']:
        if e['health'] > 0:
            # Dodge check (rogue evasion talent)
            if random.random() < talent_bonuses.get('dodge_chance', 0):
                state['log'].append(f"You dodged {e['name']}'s attack!")
                continue

            # Damage reduction (cleric divine protection)
            reduction = 1.0 - talent_bonuses.get('damage_reduction', 0)
            enemy_damage = max(1, int((e['attack'] - defense_power) * random.uniform(0.8, 1.2) * reduction))
            state['player_health'] -= enemy_damage
            state['log'].append(f"{e['name']} attacks you! (-{enemy_damage} HP)")
            
            if state['player_health'] <= 0:
                state['log'].append("You have been defeated!")
                db.clear_combat_state(player_id)
                return {"result": "defeat", "log": state['log']}
    
    # Check victory
    if all(e['health'] <= 0 for e in state['enemies']):
        total_xp = sum(e['xp_reward'] for e in state['enemies'])
        total_gold = sum(e['gold_reward'] for e in state['enemies'])
        
        # Rewards
        loot = []
        for e in state['enemies']:
            if e['health'] <= 0:
                drop = db.get_loot_drop(e['type'])
                if drop:
                    loot.append(drop)
        
        # Add experience with leveling system
        level_result = add_experience(character, total_xp, source="combat victory")
        character['gold'] += total_gold
        character['inventory'].extend(loot)
        
        # Save character (now includes any level-up changes)
        db.update_character(player_id, character)

        # Update kill quest progress
        active_quests = db.get_player_active_quests(player_id)
        for quest in active_quests:
            if quest['type'] == 'kill':
                reqs = quest['requirements']
                progress = quest['progress']
                if 'enemy_type' in reqs:
                    killed_count = sum(
                        1 for e in state['enemies']
                        if e['health'] <= 0 and e['type'] == reqs['enemy_type']
                    )
                    if killed_count > 0:
                        progress['kills'] = progress.get('kills', 0) + killed_count
                        db.update_quest_progress(player_id, quest['quest_id'], progress)
                elif 'total_kills' in reqs:
                    total_killed = sum(1 for e in state['enemies'] if e['health'] <= 0)
                    progress['kills'] = progress.get('kills', 0) + total_killed
                    db.update_quest_progress(player_id, quest['quest_id'], progress)

        db.clear_combat_state(player_id)
        
        response = {
            "result": "victory",
            "rewards": {
                "xp": total_xp,
                "gold": total_gold,
                "loot": loot
            },
            "log": state['log']
        }
        
        # Add level-up info if leveled up
        if level_result.leveled_up:
            response["level_up"] = {
                "levels_gained": level_result.levels_gained,
                "new_level": level_result.new_level,
                "stat_increases": level_result.stat_increases,
                "tier_changed": level_result.tier_changed,
                "new_tier": level_result.new_tier,
                "messages": level_result.messages
            }
        
        return response
    
    state['turn'] += 1
    db.set_combat_state(player_id, state)
    
    return format_combat_status(state)

@app.post("/api/combat/flee")
async def combat_flee(player_id: str = Depends(get_current_player)):
    """Attempt to flee combat"""
    state = db.get_combat_state(player_id)
    if not state:
        raise HTTPException(status_code=404, detail="No active combat")
    
    talent_bonuses = db.get_talent_bonuses(player_id)
    flee_chance = 0.6
    if talent_bonuses.get('vanish'):
        flee_chance = 1.0

    if random.random() < flee_chance:
        db.clear_combat_state(player_id)
        return {"result": "fled", "message": "You successfully fled!"}
    else:
        # Enemy gets free attack
        state['log'].append("Failed to flee!")
        db.set_combat_state(player_id, state)
        return {"result": "failed", "message": "Failed to flee!", "combat": format_combat_status(state)}

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "players_online": db.get_player_count()}


# ============================================
# CITY ENDPOINTS
# ============================================

@app.get("/api/cities")
async def list_cities():
    """List all available home base cities"""
    cities = db.get_cities()
    return {
        "cities": [
            {
                "id": city['id'],
                "name": city['name'],
                "faction": city['faction'],
                "description": city['description'],
                "type": city['type'],
                "features": city['features']
            }
            for city in cities.values()
        ]
    }

@app.post("/api/city/enter/{city_id}")
async def enter_city(
    city_id: str,
    player_id: str = Depends(get_current_player)
):
    """Enter a city - join the city chat and location"""
    city = db.get_city(city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")
    
    # Check if player is in combat
    combat_state = db.get_combat_state(player_id)
    if combat_state:
        raise HTTPException(status_code=400, detail="Cannot enter city while in combat")
    
    # Set player location
    db.set_player_location(player_id, city_id)
    
    # Get recent chat messages
    recent_chat = db.get_city_chat(city_id, limit=20)
    
    # Get notice board
    notices = db.get_notice_board(city_id)
    
    return {
        "message": f"Welcome to {city['name']}!",
        "city": {
            "id": city['id'],
            "name": city['name'],
            "faction": city['faction'],
            "description": city['description']
        },
        "features": city['features'],
        "recent_chat": [
            {
                "character_name": msg['character_name'],
                "message": msg['message'],
                "timestamp": msg['timestamp']
            }
            for msg in recent_chat
        ],
        "notice_board": [
            {
                "id": n['id'],
                "title": n['title'],
                "difficulty": n['difficulty'],
                "rewards": {
                    "gold": n['reward_gold'],
                    "xp": n['reward_xp'],
                    "item": n['reward_item']
                }
            }
            for n in notices[:5]
        ],
        "system_message": f"{character['name']} has entered {city['name']}."
    }

@app.post("/api/city/leave")
async def leave_city(player_id: str = Depends(get_current_player)):
    """Leave the current city"""
    current_city_id = db.get_player_location(player_id)
    if not current_city_id:
        raise HTTPException(status_code=400, detail="You are not in any city")
    
    city = db.get_city(current_city_id)
    character = db.get_active_character(player_id)
    
    # Clear player location
    db.set_player_location(player_id, None)
    
    return {
        "message": f"You have left {city['name']}.",
        "city_left": city['name'],
        "system_message": f"{character['name']} has left {city['name']}."
    }

@app.post("/api/city/chat")
async def send_city_chat(
    request: CityChatRequest,
    player_id: str = Depends(get_current_player)
):
    """Send a chat message to the current city"""
    city_id = db.get_player_location(player_id)
    if not city_id:
        raise HTTPException(status_code=400, detail="You must be in a city to chat")
    
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")
    
    # Add message to chat
    db.add_city_chat_message(city_id, player_id, character['name'], request.message)
    
    return {
        "success": True,
        "message": "Message sent",
        "character_name": character['name'],
        "city": db.get_city(city_id)['name']
    }

@app.get("/api/city/chat")
async def get_city_chat(
    limit: int = 50,
    player_id: str = Depends(get_current_player)
):
    """Get recent chat messages from the current city"""
    city_id = db.get_player_location(player_id)
    if not city_id:
        raise HTTPException(status_code=400, detail="You must be in a city to view chat")
    
    messages = db.get_city_chat(city_id, limit=min(limit, 100))
    city = db.get_city(city_id)
    
    return {
        "city": city['name'],
        "messages": [
            {
                "id": msg['id'],
                "character_name": msg['character_name'],
                "message": msg['message'],
                "timestamp": msg['timestamp']
            }
            for msg in messages
        ]
    }

@app.get("/api/city/notice-board")
async def get_notice_board(
    player_id: str = Depends(get_current_player)
):
    """Get all available quests from the city's notice board"""
    city_id = db.get_player_location(player_id)
    if not city_id:
        raise HTTPException(status_code=400, detail="You must be in a city")
    
    notices = db.get_notice_board(city_id)
    city = db.get_city(city_id)
    
    return {
        "city": city['name'],
        "notices": [
            {
                "id": n['id'],
                "title": n['title'],
                "description": n['description'],
                "type": n['quest_type'],
                "difficulty": n['difficulty'],
                "rewards": {
                    "gold": n['reward_gold'],
                    "xp": n['reward_xp'],
                    "item": n['reward_item']
                },
                "posted_at": n['posted_at']
            }
            for n in notices
        ]
    }

@app.get("/api/city/{city_id}")
async def get_city_details(city_id: str):
    """Get detailed information about a specific city"""
    city = db.get_city(city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    # Get players currently in the city
    players_in_city = db.get_players_in_city(city_id)

    return {
        "city": city,
        "players_present": len(players_in_city),
        "player_list": [
            {"name": p['character_name'], "entered_at": p['entered_at']}
            for p in players_in_city[:10]  # Show first 10
        ]
    }

@app.post("/api/city/storage")
async def access_city_storage(
    request: CityStorageRequest,
    player_id: str = Depends(get_current_player)
):
    """Access the city's bank/storage"""
    city_id = db.get_player_location(player_id)
    if not city_id:
        raise HTTPException(status_code=400, detail="You must be in a city to access storage")
    
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")
    
    storage = db.get_city_storage(player_id, city_id)
    city = db.get_city(city_id)
    
    if request.action == 'deposit':
        # Deposit gold
        if request.gold > 0:
            if character['gold'] < request.gold:
                raise HTTPException(status_code=400, detail="Not enough gold")
            character['gold'] -= request.gold
            storage['gold'] += request.gold
            db.update_character(player_id, character)
            db.update_city_storage(player_id, city_id, storage['items'], storage['gold'])
            return {
                "success": True,
                "action": "deposit",
                "gold_deposited": request.gold,
                "storage_gold": storage['gold'],
                "character_gold": character['gold']
            }
        
        # Deposit item
        if request.item_id:
            if request.item_id not in character['inventory']:
                raise HTTPException(status_code=400, detail="Item not in inventory")
            character['inventory'].remove(request.item_id)
            storage['items'].append(request.item_id)
            db.update_character(player_id, character)
            db.update_city_storage(player_id, city_id, storage['items'], storage['gold'])
            item_db = db.get_item_database()
            item_name = item_db.get(request.item_id, {}).get('name', request.item_id)
            return {
                "success": True,
                "action": "deposit",
                "item_deposited": item_name,
                "storage_items": len(storage['items'])
            }
    
    elif request.action == 'withdraw':
        # Withdraw gold
        if request.gold > 0:
            if storage['gold'] < request.gold:
                raise HTTPException(status_code=400, detail="Not enough gold in storage")
            storage['gold'] -= request.gold
            character['gold'] += request.gold
            db.update_character(player_id, character)
            db.update_city_storage(player_id, city_id, storage['items'], storage['gold'])
            return {
                "success": True,
                "action": "withdraw",
                "gold_withdrawn": request.gold,
                "storage_gold": storage['gold'],
                "character_gold": character['gold']
            }
        
        # Withdraw item
        if request.item_id:
            if request.item_id not in storage['items']:
                raise HTTPException(status_code=400, detail="Item not in storage")
            storage['items'].remove(request.item_id)
            character['inventory'].append(request.item_id)
            db.update_character(player_id, character)
            db.update_city_storage(player_id, city_id, storage['items'], storage['gold'])
            item_db = db.get_item_database()
            item_name = item_db.get(request.item_id, {}).get('name', request.item_id)
            return {
                "success": True,
                "action": "withdraw",
                "item_withdrawn": item_name,
                "storage_items": len(storage['items'])
            }
    
    # Return storage status
    item_db = db.get_item_database()
    return {
        "city": city['name'],
        "storage": {
            "gold": storage['gold'],
            "items": [
                {
                    "id": item_id,
                    "name": item_db.get(item_id, {}).get('name', item_id)
                }
                for item_id in storage['items']
            ]
        },
        "character": {
            "gold": character['gold'],
            "inventory_slots": len(character['inventory'])
        }
    }


# ============================================
# INVENTORY ENDPOINTS
# ============================================

@app.get("/api/inventory")
async def get_inventory(player_id: str = Depends(get_current_player)):
    """Get player's inventory and equipment"""
    result = db.get_inventory_with_details(player_id)
    if not result:
        raise HTTPException(status_code=404, detail="No active character")
    return result

@app.post("/api/inventory/equip")
async def equip_item(
    request: EquipRequest,
    player_id: str = Depends(get_current_player)
):
    """Equip an item from inventory"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    if request.item_id not in character['inventory']:
        raise HTTPException(status_code=400, detail="Item not in inventory")

    item_db = db.get_item_database()
    item = item_db.get(request.item_id)
    if not item:
        raise HTTPException(status_code=400, detail="Unknown item")

    if item['type'] not in ('weapon', 'armor'):
        raise HTTPException(status_code=400, detail="Item cannot be equipped")

    # Determine correct slot
    if item['type'] == 'weapon':
        slot = 'weapon'
    else:
        slot = item.get('slot', 'armor')

    if slot != request.slot:
        raise HTTPException(status_code=400, detail=f"Item goes in '{slot}' slot, not '{request.slot}'")

    # Ensure equipment has all slots
    for s in ('weapon', 'armor', 'helmet', 'boots', 'accessory'):
        if s not in character['equipment']:
            character['equipment'][s] = None

    # Unequip current item in that slot (put back in inventory)
    old_item = character['equipment'].get(slot)
    if old_item:
        character['inventory'].append(old_item)

    # Equip new item
    character['inventory'].remove(request.item_id)
    character['equipment'][slot] = request.item_id

    db.update_character(player_id, character)

    old_name = item_db.get(old_item, {}).get('name', 'Nothing') if old_item else 'Nothing'
    return {
        "message": f"Equipped {item['name']} in {slot} slot",
        "unequipped": old_name,
        "equipped": item['name'],
        "slot": slot
    }

@app.post("/api/inventory/use")
async def use_item(
    request: UseItemRequest,
    player_id: str = Depends(get_current_player)
):
    """Use a consumable item"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    if request.item_id not in character['inventory']:
        raise HTTPException(status_code=400, detail="Item not in inventory")

    item_db = db.get_item_database()
    item = item_db.get(request.item_id)
    if not item:
        raise HTTPException(status_code=400, detail="Unknown item")

    if item.get('type') != 'consumable':
        raise HTTPException(status_code=400, detail="Item is not consumable")

    effect = item.get('effect')
    amount = item.get('amount', 0)
    result_msg = ""

    if effect == 'heal':
        old_hp = character['health']
        character['health'] = min(character['max_health'], character['health'] + amount)
        healed = character['health'] - old_hp
        result_msg = f"Restored {healed} HP ({character['health']}/{character['max_health']})"
    elif effect == 'restore_mana':
        old_mp = character['mana']
        character['mana'] = min(character['max_mana'], character['mana'] + amount)
        restored = character['mana'] - old_mp
        result_msg = f"Restored {restored} MP ({character['mana']}/{character['max_mana']})"
    else:
        result_msg = f"Used {item['name']}"

    character['inventory'].remove(request.item_id)
    db.update_character(player_id, character)

    return {
        "message": result_msg,
        "item_used": item['name'],
        "effect": effect,
        "amount": amount
    }

@app.post("/api/inventory/drop")
async def drop_item(
    request: DropItemRequest,
    player_id: str = Depends(get_current_player)
):
    """Drop an item from inventory"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    if request.item_id not in character['inventory']:
        raise HTTPException(status_code=400, detail="Item not in inventory")

    item_db = db.get_item_database()
    item_name = item_db.get(request.item_id, {}).get('name', request.item_id)

    character['inventory'].remove(request.item_id)
    db.update_character(player_id, character)

    return {
        "message": f"Dropped {item_name}",
        "item_dropped": item_name,
        "inventory_count": len(character['inventory'])
    }


# ============================================
# QUEST ENDPOINTS
# ============================================

@app.get("/api/quests/available")
async def get_available_quests(player_id: str = Depends(get_current_player)):
    """Get quests available to the player"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    all_quests = db.get_all_quests()
    available = []

    for quest in all_quests:
        is_available, reason = db.check_quest_available(player_id, quest, character)
        if is_available:
            available.append({
                "id": quest['id'],
                "title": quest['title'],
                "description": quest['description'],
                "type": quest['type'],
                "requirements": quest['requirements'],
                "rewards": quest['rewards'],
                "giver": quest['giver'],
                "location": quest['location'],
                "chain": quest['chain']
            })

    return {"available_quests": available, "count": len(available)}

@app.post("/api/quests/accept/{quest_id}")
async def accept_quest(
    quest_id: str,
    player_id: str = Depends(get_current_player)
):
    """Accept a quest"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    quest = db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    is_available, reason = db.check_quest_available(player_id, quest, character)
    if not is_available:
        raise HTTPException(status_code=400, detail=reason)

    success = db.accept_quest(player_id, quest_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not accept quest")

    return {
        "message": f"Quest accepted: {quest['title']}",
        "quest": {
            "id": quest['id'],
            "title": quest['title'],
            "description": quest['description'],
            "type": quest['type'],
            "requirements": quest['requirements'],
            "rewards": quest['rewards'],
            "giver": quest['giver']
        }
    }

@app.get("/api/quests/active")
async def get_active_quests(player_id: str = Depends(get_current_player)):
    """Get player's active quests with progress"""
    active = db.get_player_active_quests(player_id)

    return {
        "active_quests": [
            {
                "quest_id": q['quest_id'],
                "title": q['title'],
                "description": q['description'],
                "type": q['type'],
                "requirements": q['requirements'],
                "progress": q['progress'],
                "rewards": q['rewards'],
                "giver": q['giver'],
                "accepted_at": q['accepted_at']
            }
            for q in active
        ],
        "count": len(active)
    }

@app.post("/api/quests/complete/{quest_id}")
async def complete_quest(
    quest_id: str,
    player_id: str = Depends(get_current_player)
):
    """Complete a quest and claim rewards"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    quest = db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # Check quest is active for player
    active_quests = db.get_player_active_quests(player_id)
    player_quest = None
    for q in active_quests:
        if q['quest_id'] == quest_id:
            player_quest = q
            break

    if not player_quest:
        raise HTTPException(status_code=400, detail="Quest is not active")

    # Validate completion based on quest type
    requirements = quest['requirements']
    progress = player_quest['progress']

    if quest['type'] == 'kill':
        needed = requirements.get('count', 1)
        current = progress.get('kills', 0)
        if current < needed:
            raise HTTPException(
                status_code=400,
                detail=f"Kill requirement not met: {current}/{needed}"
            )

    elif quest['type'] == 'delivery':
        required_items = requirements.get('items', {})
        for item_id, count in required_items.items():
            have = character['inventory'].count(item_id)
            if have < count:
                item_db = db.get_item_database()
                item_name = item_db.get(item_id, {}).get('name', item_id)
                raise HTTPException(
                    status_code=400,
                    detail=f"Need {count} {item_name}, have {have}"
                )
        # Remove delivered items
        for item_id, count in required_items.items():
            for _ in range(count):
                character['inventory'].remove(item_id)

    elif quest['type'] == 'boss':
        if progress.get('kills', 0) < 1:
            raise HTTPException(status_code=400, detail="Boss not yet defeated")

    # Grant rewards
    rewards = quest['rewards']
    reward_summary = []

    if rewards.get('xp', 0) > 0:
        level_result = add_experience(character, rewards['xp'], source=f"quest: {quest['title']}")
        reward_summary.append(f"+{rewards['xp']} XP")

    if rewards.get('gold', 0) > 0:
        character['gold'] += rewards['gold']
        reward_summary.append(f"+{rewards['gold']} gold")

    if rewards.get('items'):
        for item_id in rewards['items']:
            if len(character['inventory']) < 20:
                character['inventory'].append(item_id)
                item_db = db.get_item_database()
                item_name = item_db.get(item_id, {}).get('name', item_id)
                reward_summary.append(f"+{item_name}")

    # Grant reputation
    if rewards.get('reputation'):
        for faction, amount in rewards['reputation'].items():
            db.modify_reputation(player_id, faction, amount)
            reward_summary.append(f"+{amount} {faction} reputation")

    # Mark quest complete and save character
    db.complete_quest(player_id, quest_id)
    db.update_character(player_id, character)

    response = {
        "message": f"Quest completed: {quest['title']}!",
        "rewards": reward_summary,
        "quest": quest['title']
    }

    if rewards.get('xp', 0) > 0 and level_result.leveled_up:
        response["level_up"] = {
            "new_level": level_result.new_level,
            "stat_increases": level_result.stat_increases,
            "messages": level_result.messages
        }

    return response


# ============================================
# TALENT ENDPOINTS
# ============================================

@app.get("/api/talents/tree")
async def get_talent_tree(player_id: str = Depends(get_current_player)):
    """Get your class talent tree with current investments"""
    tree = db.get_talent_tree(player_id)
    if not tree:
        raise HTTPException(status_code=404, detail="No active character")
    return tree

@app.post("/api/talents/spend")
async def spend_talent_point(
    request: SpendTalentRequest,
    player_id: str = Depends(get_current_player)
):
    """Spend a talent point"""
    success, message = db.spend_talent_point(player_id, request.talent_name)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    tree = db.get_talent_tree(player_id)
    return {"message": message, "talent_tree": tree}

@app.get("/api/talents/my")
async def get_my_talents(player_id: str = Depends(get_current_player)):
    """Get your current talent allocations and bonuses"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    talents = db.get_player_talents(player_id)
    bonuses = db.get_talent_bonuses(player_id)

    return {
        "talents": talents,
        "bonuses": bonuses,
        "available_points": max(0, character['level'] - 1 - sum(talents.values()))
    }


# ============================================
# CODEX & PORTRAIT ENDPOINTS
# ============================================

DEFAULT_PORTRAITS = {
    'warrior': 'warrior-class.png',
    'mage': 'mage-class.png',
    'rogue': 'rogue-class.png',
    'cleric': 'cleric-class.png'
}

@app.post("/api/character/portrait")
async def upload_portrait(
    request: PortraitUploadRequest,
    player_id: str = Depends(get_current_player)
):
    """Upload a character portrait (base64 encoded PNG/JPG)"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    try:
        image_bytes = base64.b64decode(request.image_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # Validate it's a reasonable size (max 2MB)
    if len(image_bytes) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 2MB)")

    # Save as PNG using character name (sanitized)
    safe_name = "".join(c for c in character['name'] if c.isalnum() or c in '-_').lower()
    filename = f"{safe_name}_{player_id[:8]}.png"
    filepath = os.path.join(PORTRAITS_DIR, filename)

    with open(filepath, 'wb') as f:
        f.write(image_bytes)

    return {
        "message": f"Portrait uploaded for {character['name']}",
        "portrait_url": f"/portraits/{filename}"
    }

@app.get("/api/codex")
async def get_codex():
    """Get all characters for the codex/player gallery"""
    characters = db.get_all_characters_for_codex()
    item_db = db.get_item_database()

    codex_entries = []
    for char in characters:
        # Check for custom portrait
        safe_name = "".join(c for c in char['name'] if c.isalnum() or c in '-_').lower()
        # Find portrait file matching this character
        portrait_url = None
        if os.path.isdir(PORTRAITS_DIR):
            for f in os.listdir(PORTRAITS_DIR):
                if f.startswith(safe_name):
                    portrait_url = f"/portraits/{f}"
                    break

        if not portrait_url:
            portrait_url = f"/{DEFAULT_PORTRAITS.get(char['class'], 'warrior-class.png')}"

        # Get weapon name
        weapon_id = char['equipment'].get('weapon')
        weapon_name = item_db.get(weapon_id, {}).get('name', 'None') if weapon_id else 'None'

        codex_entries.append({
            "name": char['name'],
            "class": char['class'],
            "faction": char['faction'],
            "level": char['level'],
            "portrait_url": portrait_url,
            "max_health": char['max_health'],
            "max_mana": char['max_mana'],
            "attack": char['attack'],
            "defense": char['defense'],
            "weapon": weapon_name,
            "created_at": char['created_at'],
            "has_custom_portrait": portrait_url.startswith("/portraits/")
        })

    return {"codex": codex_entries, "count": len(codex_entries)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_dungeon_room_state(dungeon_def: Dict, room_idx: int, members: List[Dict], party_id: str) -> Dict:
    """Build the combat state dict for a dungeon room."""
    room = dungeon_def["rooms"][room_idx]
    is_boss = room["type"] == "boss"
    boss_scale = room.get("boss_scale", 1.0)

    # Scale enemies relative to average party level
    avg_level = max(1, sum(m["level"] for m in members) // len(members))
    enemy_level = max(1, avg_level + (2 if is_boss else 0))

    enemies = []
    for etype in room["enemies"]:
        base = EnemyConfig.TYPES.get(etype, EnemyConfig.TYPES["goblin"])
        hp = int(base["health"] * (1 + (enemy_level - 1) * 0.2) * (boss_scale if is_boss else 1.0))
        enemies.append({
            "type": etype,
            "name": room.get("boss_name", base["name"]) if is_boss else base["name"],
            "health": hp,
            "max_health": hp,
            "attack": int(base["attack"] * (1 + (enemy_level - 1) * 0.15) * (boss_scale * 0.6 if is_boss else 1.0)),
            "defense": int(base["defense"] * (1 + (enemy_level - 1) * 0.1)),
            "xp_reward": calculate_enemy_xp(etype, enemy_level, is_boss=is_boss),
            "gold_reward": int(base["gold"] * (1 + (enemy_level - 1) * 0.2) * (boss_scale if is_boss else 1.0)),
        })

    # Party members in combat state (snapshot of current HP)
    party_state = []
    for m in members:
        party_state.append({
            "player_id": m["player_id"],
            "character_name": m["character_name"],
            "class": m["class"],
            "health": m["health"],
            "max_health": m["max_health"],
            "attack": m["attack"],
            "defense": m["defense"],
            "speed": m["speed"],
            "healing_power": m.get("healing_power", 0),
            "alive": m["health"] > 0,
        })

    # Turn order: highest speed first
    turn_order = sorted([m["player_id"] for m in members], key=lambda pid: next(
        (m["speed"] for m in members if m["player_id"] == pid), 0
    ), reverse=True)

    return {
        "party_id": party_id,
        "room_index": room_idx,
        "room_type": room["type"],
        "room_description": room["description"],
        "is_boss": is_boss,
        "room_cleared": False,
        "enemies": enemies,
        "party": party_state,
        "turn_order": turn_order,
        "current_turn_index": 0,
        "players_acted_this_round": [],
        "round": 1,
        "log": [f"Entered: {room['description']}"],
    }


def _format_dungeon_status(run: Dict, dungeon_def: Dict) -> Dict:
    state = run["combat_state"]
    return {
        "run_id": run["id"],
        "dungeon": dungeon_def["name"],
        "difficulty": dungeon_def["difficulty"],
        "room": f"{run['current_room'] + 1}/{len(dungeon_def['rooms'])}",
        "room_description": state["room_description"],
        "room_type": state["room_type"],
        "room_cleared": state["room_cleared"],
        "round": state["round"],
        "whose_turn": state["turn_order"][state["current_turn_index"]] if not state["room_cleared"] else None,
        "enemies": [
            {
                "index": i,
                "name": e["name"],
                "health": max(0, e["health"]),
                "max_health": e["max_health"],
                "status": "defeated" if e["health"] <= 0 else "alive",
            }
            for i, e in enumerate(state["enemies"])
        ],
        "party": [
            {
                "player_id": m["player_id"],
                "character_name": m["character_name"],
                "class": m["class"],
                "health": max(0, m["health"]),
                "max_health": m["max_health"],
                "alive": m["alive"],
            }
            for m in state["party"]
        ],
        "recent_log": state["log"][-5:],
    }


# ---------------------------------------------------------------------------
# Party endpoints
# ---------------------------------------------------------------------------

@app.post("/api/party/create")
async def create_party(player_id: str = Depends(get_current_player)):
    """Create a new party. You become the leader."""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    existing = db.get_player_party(player_id)
    if existing:
        raise HTTPException(status_code=400, detail="You are already in a party. Leave it first.")

    party_id = db.create_party(player_id)
    db.remove_lfg_post(player_id)
    return {
        "message": "Party created",
        "party_id": party_id,
        "leader": character["name"],
        "tip": "Invite others with POST /api/party/invite/{their_player_id}",
    }


@app.post("/api/party/invite/{target_player_id}")
async def invite_to_party(target_player_id: str, player_id: str = Depends(get_current_player)):
    """Invite another player to your party (leader only)."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=400, detail="You are not in a party")
    if party["leader_id"] != player_id:
        raise HTTPException(status_code=403, detail="Only the party leader can invite")
    if party["status"] == "in_dungeon":
        raise HTTPException(status_code=400, detail="Cannot invite while in a dungeon")

    count = db.get_party_member_count(party["id"])
    if count >= party["max_size"]:
        raise HTTPException(status_code=400, detail="Party is full")

    # Check target exists and is not already in a party
    target_char = db.get_active_character(target_player_id)
    if not target_char:
        raise HTTPException(status_code=404, detail="Target player not found")
    if db.get_player_party(target_player_id):
        raise HTTPException(status_code=400, detail="That player is already in a party")

    invite_id = db.create_party_invite(party["id"], player_id, target_player_id)
    return {
        "message": f"Invite sent to {target_char['name']}",
        "invite_id": invite_id,
        "tip": "They must accept with POST /api/party/accept/{invite_id}",
    }


@app.get("/api/party/invites")
async def get_party_invites(player_id: str = Depends(get_current_player)):
    """See your pending party invites."""
    invites = db.get_pending_invites(player_id)
    return {"invites": invites, "count": len(invites)}


@app.post("/api/party/accept/{invite_id}")
async def accept_party_invite(invite_id: int, player_id: str = Depends(get_current_player)):
    """Accept a party invite."""
    success, message, party_id = db.respond_to_invite(invite_id, player_id, accept=True)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    db.remove_lfg_post(player_id)
    members = db.get_party_members(party_id)
    return {"message": message, "party_id": party_id, "party_size": len(members)}


@app.post("/api/party/decline/{invite_id}")
async def decline_party_invite(invite_id: int, player_id: str = Depends(get_current_player)):
    """Decline a party invite."""
    success, message, _ = db.respond_to_invite(invite_id, player_id, accept=False)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@app.get("/api/party/status")
async def get_party_status(player_id: str = Depends(get_current_player)):
    """Get your current party roster and status."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=404, detail="You are not in a party")

    members = db.get_party_members(party["id"])
    active_run = db.get_active_dungeon_run(party["id"])

    return {
        "party_id": party["id"],
        "status": party["status"],
        "leader_id": party["leader_id"],
        "size": len(members),
        "max_size": party["max_size"],
        "members": [
            {
                "player_id": m["player_id"],
                "character_name": m["character_name"],
                "class": m["class"],
                "level": m["level"],
                "health": m["health"],
                "max_health": m["max_health"],
                "is_leader": m["is_leader"],
            }
            for m in members
        ],
        "in_dungeon": active_run is not None,
        "dungeon_id": active_run["dungeon_id"] if active_run else None,
    }


@app.post("/api/party/leave")
async def leave_party(player_id: str = Depends(get_current_player)):
    """Leave your current party."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=404, detail="You are not in a party")
    if party["status"] == "in_dungeon":
        raise HTTPException(status_code=400, detail="Cannot leave while in a dungeon. Use /api/dungeon/flee first.")

    party_id = party["id"]
    db.remove_party_member(party_id, player_id)

    remaining = db.get_party_member_count(party_id)
    if remaining == 0:
        db.disband_party(party_id)
    elif party["leader_id"] == player_id:
        # Transfer leadership to first remaining member
        members = db.get_party_members(party_id)
        if members:
            db.transfer_party_leadership(party_id, members[0]["player_id"])

    return {"message": "Left party"}


@app.post("/api/party/kick/{target_player_id}")
async def kick_from_party(target_player_id: str, player_id: str = Depends(get_current_player)):
    """Kick a player from the party (leader only)."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=400, detail="You are not in a party")
    if party["leader_id"] != player_id:
        raise HTTPException(status_code=403, detail="Only the leader can kick")
    if target_player_id == player_id:
        raise HTTPException(status_code=400, detail="Cannot kick yourself. Use /api/party/leave.")
    if party["status"] == "in_dungeon":
        raise HTTPException(status_code=400, detail="Cannot kick while in a dungeon")

    db.remove_party_member(party["id"], target_player_id)
    return {"message": "Player kicked from party"}


# ---------------------------------------------------------------------------
# Dungeon endpoints
# ---------------------------------------------------------------------------

@app.get("/api/dungeons")
async def list_dungeons(player_id: str = Depends(get_current_player)):
    """List all available dungeons with requirements and your lockout status."""
    lockouts = {l["dungeon_id"]: l["locked_until"] for l in db.get_player_lockouts(player_id)}
    result = []
    for ddef in DUNGEON_DEFINITIONS.values():
        result.append({
            "id": ddef["id"],
            "name": ddef["name"],
            "difficulty": ddef["difficulty"],
            "min_players": ddef["min_players"],
            "max_players": ddef["max_players"],
            "min_level": ddef["min_level"],
            "description": ddef["description"],
            "rooms": len(ddef["rooms"]),
            "lockout_hours": ddef["lockout_hours"],
            "locked_until": lockouts.get(ddef["id"]),
            "gear_tier": {
                "normal": "Rare / Epic (boss)",
                "hard": "Epic / Legendary (boss)",
                "legendary": "Legendary guaranteed",
            }.get(ddef["difficulty"]),
        })
    return {"dungeons": result}


@app.post("/api/dungeon/enter/{dungeon_id}")
async def enter_dungeon(dungeon_id: str, player_id: str = Depends(get_current_player)):
    """Enter a dungeon with your party. Party leader initiates."""
    dungeon_def = DUNGEON_DEFINITIONS.get(dungeon_id)
    if not dungeon_def:
        raise HTTPException(status_code=404, detail="Unknown dungeon")

    # Must be in a party
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=400, detail="You must be in a party to enter a dungeon")
    if party["leader_id"] != player_id:
        raise HTTPException(status_code=403, detail="Only the party leader can enter a dungeon")
    if party["status"] == "in_dungeon":
        raise HTTPException(status_code=400, detail="Party is already in a dungeon")

    members = db.get_party_members(party["id"])
    size = len(members)

    if size < dungeon_def["min_players"]:
        raise HTTPException(
            status_code=400,
            detail=f"{dungeon_def['name']} requires at least {dungeon_def['min_players']} players. You have {size}."
        )

    # Check all members meet level requirement
    below_level = [m for m in members if m["level"] < dungeon_def["min_level"]]
    if below_level:
        names = ", ".join(m["character_name"] for m in below_level)
        raise HTTPException(
            status_code=400,
            detail=f"These members are below level {dungeon_def['min_level']}: {names}"
        )

    # Check lockouts for all members
    locked = [m for m in members if db.check_dungeon_lockout(m["player_id"], dungeon_id)]
    if locked:
        names = ", ".join(m["character_name"] for m in locked)
        raise HTTPException(status_code=400, detail=f"These members are on lockout: {names}")

    # Build room 0 combat state
    initial_state = _build_dungeon_room_state(dungeon_def, 0, members, party["id"])
    run_id = db.create_dungeon_run(dungeon_id, party["id"], initial_state)

    run = db.get_active_dungeon_run(party["id"])
    return {
        "message": f"Entered {dungeon_def['name']}!",
        "run_id": run_id,
        "dungeon": _format_dungeon_status(run, dungeon_def),
        "tip": "Each party member attacks with POST /api/dungeon/attack. Check whose turn with GET /api/dungeon/status.",
    }


@app.get("/api/dungeon/status")
async def get_dungeon_status(player_id: str = Depends(get_current_player)):
    """Get the current state of your party's dungeon run."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=404, detail="You are not in a party")

    run = db.get_active_dungeon_run(party["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Your party is not in a dungeon")

    dungeon_def = DUNGEON_DEFINITIONS[run["dungeon_id"]]
    return _format_dungeon_status(run, dungeon_def)


@app.post("/api/dungeon/attack")
async def dungeon_attack(request: DungeonAttackRequest, player_id: str = Depends(get_current_player)):
    """Attack an enemy in the current dungeon room. Must be your turn."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=404, detail="You are not in a party")

    run = db.get_active_dungeon_run(party["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Your party is not in a dungeon")

    state = run["combat_state"]
    dungeon_def = DUNGEON_DEFINITIONS[run["dungeon_id"]]

    if state["room_cleared"]:
        raise HTTPException(status_code=400, detail="Room is cleared. Advance with POST /api/dungeon/advance")

    # Check turn
    current_turn_player = state["turn_order"][state["current_turn_index"]]
    if current_turn_player != player_id:
        whose = next((m["character_name"] for m in state["party"] if m["player_id"] == current_turn_player), "unknown")
        raise HTTPException(status_code=400, detail=f"Not your turn. Waiting for {whose}.")

    # Find this player in party state
    actor = next((m for m in state["party"] if m["player_id"] == player_id), None)
    if not actor or not actor["alive"]:
        raise HTTPException(status_code=400, detail="Your character is defeated")

    # Validate target
    if request.target >= len(state["enemies"]):
        raise HTTPException(status_code=400, detail="Invalid target index")
    enemy = state["enemies"][request.target]
    if enemy["health"] <= 0:
        raise HTTPException(status_code=400, detail="That enemy is already defeated. Pick another target.")

    # Get character for equipment bonuses
    character = db.get_active_character(player_id)
    item_db = db.get_item_database()
    attack_power = actor["attack"]
    for slot in ("weapon", "armor", "helmet", "boots", "accessory"):
        item_id = character["equipment"].get(slot)
        if item_id:
            attack_power += item_db.get(item_id, {}).get("attack", 0)

    crit_chance = character.get("critical_chance", 0.15)
    crit = random.random() < crit_chance
    base_damage = max(1, attack_power - enemy["defense"])
    damage = int(base_damage * random.uniform(0.85, 1.15) * (1.5 if crit else 1.0))
    enemy["health"] -= damage

    log = f"{actor['character_name']} attacks {enemy['name']}!{' CRITICAL!' if crit else ''} (-{damage} HP)"
    if enemy["health"] <= 0:
        log += f" {enemy['name']} is defeated!"
    state["log"].append(log)

    # Mark this player as having acted
    if player_id not in state["players_acted_this_round"]:
        state["players_acted_this_round"].append(player_id)

    # Advance turn to next alive player
    alive_players = [pid for pid in state["turn_order"]
                     if any(m["player_id"] == pid and m["alive"] for m in state["party"])]

    if alive_players:
        next_idx = (state["current_turn_index"] + 1) % len(state["turn_order"])
        # Skip dead players
        attempts = 0
        while state["turn_order"][next_idx] not in alive_players and attempts < len(state["turn_order"]):
            next_idx = (next_idx + 1) % len(state["turn_order"])
            attempts += 1
        state["current_turn_index"] = next_idx

    # Check if all alive players have acted this round → enemies attack
    acted_alive = [pid for pid in state["players_acted_this_round"] if pid in alive_players]
    if set(acted_alive) >= set(alive_players):
        # Enemies attack all living party members
        living_enemies = [e for e in state["enemies"] if e["health"] > 0]
        for m in state["party"]:
            if not m["alive"]:
                continue
            char = db.get_active_character(m["player_id"])
            def_power = m["defense"]
            if char:
                for slot in ("armor", "helmet", "boots", "accessory"):
                    item_id = char["equipment"].get(slot)
                    if item_id:
                        def_power += item_db.get(item_id, {}).get("defense", 0)
            for e in living_enemies:
                dmg = max(1, int((e["attack"] - def_power) * random.uniform(0.85, 1.15)))
                m["health"] -= dmg
                state["log"].append(f"{e['name']} attacks {m['character_name']}! (-{dmg} HP)")
                if m["health"] <= 0:
                    m["alive"] = False
                    state["log"].append(f"{m['character_name']} has been defeated!")

        state["players_acted_this_round"] = []
        state["round"] += 1
        state["current_turn_index"] = 0

    # Persist HP changes to character records
    for m in state["party"]:
        char = db.get_active_character(m["player_id"])
        if char:
            char["health"] = max(0, m["health"])
            db.update_character(m["player_id"], char)

    # Check outcomes
    all_enemies_dead = all(e["health"] <= 0 for e in state["enemies"])
    all_party_dead = all(not m["alive"] for m in state["party"])

    if all_party_dead:
        db.update_dungeon_run(run["id"], run["current_room"], state)
        db.complete_dungeon_run(run["id"], party["id"], "failed")
        return {"result": "defeat", "message": "Your entire party has been defeated.", "log": state["log"][-10:]}

    if all_enemies_dead:
        state["room_cleared"] = True
        total_rooms = len(dungeon_def["rooms"])
        is_last_room = (run["current_room"] >= total_rooms - 1)

        if is_last_room:
            # Dungeon complete — distribute loot and set lockouts
            loot_per_player = {}
            for m in state["party"]:
                if m["alive"]:
                    loot = db.get_dungeon_loot(dungeon_def["boss_loot_table"], run["dungeon_id"])
                    loot_per_player[m["player_id"]] = loot
                    if loot:
                        char = db.get_active_character(m["player_id"])
                        if char:
                            char["inventory"].append(loot)
                            db.update_character(m["player_id"], char)
                    db.set_dungeon_lockout(m["player_id"], run["dungeon_id"], dungeon_def["lockout_hours"])

            db.update_dungeon_run(run["id"], run["current_room"], state)
            db.complete_dungeon_run(run["id"], party["id"], "completed")
            item_db_ref = db.get_item_database()
            return {
                "result": "victory",
                "message": f"{dungeon_def['name']} cleared!",
                "loot": {
                    pid: item_db_ref.get(iid, {}).get("name", iid) if iid else "No drop"
                    for pid, iid in loot_per_player.items()
                },
                "lockout_hours": dungeon_def["lockout_hours"],
                "log": state["log"][-10:],
            }
        else:
            state["log"].append(f"Room {run['current_room'] + 1} cleared! Advance with POST /api/dungeon/advance")
            db.update_dungeon_run(run["id"], run["current_room"], state)
            # Drop loot for cleared mob room
            loot_drops = []
            for m in state["party"]:
                if m["alive"]:
                    loot = db.get_dungeon_loot(dungeon_def["loot_table"], run["dungeon_id"])
                    if loot:
                        loot_drops.append(loot)
                        char = db.get_active_character(m["player_id"])
                        if char:
                            char["inventory"].append(loot)
                            db.update_character(m["player_id"], char)
            item_db_ref = db.get_item_database()
            return {
                "result": "room_cleared",
                "message": f"Room {run['current_room'] + 1} cleared!",
                "loot_dropped": [item_db_ref.get(l, {}).get("name", l) for l in loot_drops],
                "next_room": run["current_room"] + 2,
                "total_rooms": total_rooms,
                "log": state["log"][-10:],
                "tip": "All members advance with POST /api/dungeon/advance",
            }

    db.update_dungeon_run(run["id"], run["current_room"], state)
    return _format_dungeon_status(run, dungeon_def)


@app.post("/api/dungeon/heal")
async def dungeon_heal(request: DungeonHealRequest, player_id: str = Depends(get_current_player)):
    """Clerics only: heal a party member instead of attacking. Uses your turn."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=404, detail="You are not in a party")

    run = db.get_active_dungeon_run(party["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Your party is not in a dungeon")

    state = run["combat_state"]
    dungeon_def = DUNGEON_DEFINITIONS[run["dungeon_id"]]

    if state["room_cleared"]:
        raise HTTPException(status_code=400, detail="Room is cleared. Advance with POST /api/dungeon/advance")

    current_turn_player = state["turn_order"][state["current_turn_index"]]
    if current_turn_player != player_id:
        raise HTTPException(status_code=400, detail="Not your turn")

    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")
    if character["class"] != "cleric":
        raise HTTPException(status_code=400, detail="Only clerics can heal")

    actor = next((m for m in state["party"] if m["player_id"] == player_id), None)
    if not actor or not actor["alive"]:
        raise HTTPException(status_code=400, detail="Your character is defeated")

    target = next((m for m in state["party"] if m["player_id"] == request.target_player_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found in party")
    if not target["alive"]:
        raise HTTPException(status_code=400, detail="Cannot heal a defeated player")

    heal_amount = max(10, int((character.get("healing_power", 10) + 10) * random.uniform(0.9, 1.1)))
    target["health"] = min(target["max_health"], target["health"] + heal_amount)

    # Persist
    target_char = db.get_active_character(request.target_player_id)
    if target_char:
        target_char["health"] = target["health"]
        db.update_character(request.target_player_id, target_char)

    state["log"].append(f"{actor['character_name']} heals {target['character_name']} for {heal_amount} HP!")

    # Advance turn (same logic as attack)
    alive_players = [pid for pid in state["turn_order"]
                     if any(m["player_id"] == pid and m["alive"] for m in state["party"])]
    if player_id not in state["players_acted_this_round"]:
        state["players_acted_this_round"].append(player_id)

    next_idx = (state["current_turn_index"] + 1) % len(state["turn_order"])
    attempts = 0
    while state["turn_order"][next_idx] not in alive_players and attempts < len(state["turn_order"]):
        next_idx = (next_idx + 1) % len(state["turn_order"])
        attempts += 1
    state["current_turn_index"] = next_idx

    acted_alive = [pid for pid in state["players_acted_this_round"] if pid in alive_players]
    if set(acted_alive) >= set(alive_players):
        # Enemy retaliation round
        item_db = db.get_item_database()
        living_enemies = [e for e in state["enemies"] if e["health"] > 0]
        for m in state["party"]:
            if not m["alive"]:
                continue
            char = db.get_active_character(m["player_id"])
            def_power = m["defense"]
            if char:
                for slot in ("armor", "helmet", "boots", "accessory"):
                    item_id = char["equipment"].get(slot)
                    if item_id:
                        def_power += item_db.get(item_id, {}).get("defense", 0)
            for e in living_enemies:
                dmg = max(1, int((e["attack"] - def_power) * random.uniform(0.85, 1.15)))
                m["health"] -= dmg
                state["log"].append(f"{e['name']} attacks {m['character_name']}! (-{dmg} HP)")
                if m["health"] <= 0:
                    m["alive"] = False
                    state["log"].append(f"{m['character_name']} has been defeated!")
        state["players_acted_this_round"] = []
        state["round"] += 1
        state["current_turn_index"] = 0

    db.update_dungeon_run(run["id"], run["current_room"], state)
    return _format_dungeon_status(run, dungeon_def)


@app.post("/api/dungeon/advance")
async def dungeon_advance(player_id: str = Depends(get_current_player)):
    """Advance to the next room after clearing the current one."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=404, detail="You are not in a party")

    run = db.get_active_dungeon_run(party["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Your party is not in a dungeon")

    state = run["combat_state"]
    dungeon_def = DUNGEON_DEFINITIONS[run["dungeon_id"]]

    if not state["room_cleared"]:
        raise HTTPException(status_code=400, detail="Room not cleared yet — defeat all enemies first")

    next_room = run["current_room"] + 1
    if next_room >= len(dungeon_def["rooms"]):
        raise HTTPException(status_code=400, detail="Already in the final room")

    # Build next room using current party HP from state
    members_snapshot = state["party"]
    next_state = _build_dungeon_room_state(dungeon_def, next_room, [
        {
            "player_id": m["player_id"],
            "character_name": m["character_name"],
            "class": m["class"],
            "health": m["health"],
            "max_health": m["max_health"],
            "attack": m["attack"],
            "defense": m["defense"],
            "speed": m["speed"],
            "healing_power": m.get("healing_power", 0),
            "alive": m["alive"],
            "level": 1,  # used only for avg level calc; will use existing state
        }
        for m in members_snapshot if m["alive"]
    ], party["id"])

    # Carry over dead members (they stay dead)
    for m in members_snapshot:
        if not m["alive"]:
            next_state["party"].append(m)
            if m["player_id"] in next_state["turn_order"]:
                next_state["turn_order"].remove(m["player_id"])

    db.update_dungeon_run(run["id"], next_room, next_state)
    run["current_room"] = next_room
    run["combat_state"] = next_state
    return _format_dungeon_status(run, dungeon_def)


@app.post("/api/dungeon/flee")
async def dungeon_flee(player_id: str = Depends(get_current_player)):
    """Flee the dungeon. Party loses all progress and loot. No lockout applied."""
    party = db.get_player_party(player_id)
    if not party:
        raise HTTPException(status_code=404, detail="You are not in a party")
    if party["leader_id"] != player_id:
        raise HTTPException(status_code=403, detail="Only the leader can call a retreat")

    run = db.get_active_dungeon_run(party["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Your party is not in a dungeon")

    dungeon_def = DUNGEON_DEFINITIONS[run["dungeon_id"]]
    db.complete_dungeon_run(run["id"], party["id"], "fled")
    return {"message": f"Your party fled {dungeon_def['name']}. No lockout applied but all progress lost."}


@app.get("/api/dungeon/lockouts")
async def get_dungeon_lockouts(player_id: str = Depends(get_current_player)):
    """See your current dungeon lockouts."""
    lockouts = db.get_player_lockouts(player_id)
    return {
        "lockouts": [
            {
                "dungeon_id": l["dungeon_id"],
                "dungeon_name": DUNGEON_DEFINITIONS.get(l["dungeon_id"], {}).get("name", l["dungeon_id"]),
                "locked_until": l["locked_until"],
            }
            for l in lockouts
        ]
    }


# ---------------------------------------------------------------------------
# LFG endpoints
# ---------------------------------------------------------------------------

@app.post("/api/lfg/post")
async def post_lfg(request: LFGPostRequest, player_id: str = Depends(get_current_player)):
    """Post a Looking For Group listing. Expires in 30 minutes. Auto-removed when you join a party."""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    if request.dungeon_id and request.dungeon_id not in DUNGEON_DEFINITIONS:
        raise HTTPException(status_code=400, detail="Unknown dungeon_id")

    post_id = db.post_lfg(
        player_id, character["name"], character["class"], character["level"],
        request.dungeon_id, request.role, request.message
    )
    return {
        "message": "LFG post created",
        "post_id": post_id,
        "expires_in_minutes": 30,
        "tip": "Others can see your post with GET /api/lfg",
    }


@app.get("/api/lfg")
async def get_lfg(dungeon_id: Optional[str] = None):
    """Browse Looking For Group posts. Filter by dungeon_id optionally."""
    posts = db.get_lfg_posts(dungeon_id)
    return {
        "posts": posts,
        "count": len(posts),
        "tip": "Invite someone from LFG with POST /api/party/invite/{their_player_id}",
    }


@app.delete("/api/lfg")
async def remove_lfg_post(player_id: str = Depends(get_current_player)):
    """Remove your LFG post."""
    db.remove_lfg_post(player_id)
    return {"message": "LFG post removed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
