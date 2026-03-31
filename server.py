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

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
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
        'inventory': ['health_potion', 'health_potion'],
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
    weapon = item_db.get(character['equipment'].get('weapon'), {})
    armor = item_db.get(character['equipment'].get('armor'), {})
    
    total_attack = character['attack'] + weapon.get('attack', 0)
    total_defense = character['defense'] + armor.get('defense', 0)
    
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
            "speed": character['speed'],
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
            "equipment": {
                "weapon": weapon.get('name', 'None'),
                "armor": armor.get('name', 'None')
            },
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
    enemies: List[str],
    player_id: str = Depends(get_current_player)
):
    """Start a combat encounter"""
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
    weapon = item_db.get(character['equipment'].get('weapon'), {})
    attack_power = character['attack'] + weapon.get('attack', 0)
    
    base_damage = max(1, attack_power - enemy['defense'])
    variance = random.uniform(0.8, 1.2)
    crit = random.random() < character.get('critical_chance', 0.15)
    damage = int(base_damage * variance * (1.5 if crit else 1))
    
    enemy['health'] -= damage
    
    log_entry = f"You attack {enemy['name']}! {'CRITICAL HIT! ' if crit else ''}(-{damage} HP)"
    if enemy['health'] <= 0:
        log_entry += f" {enemy['name']} defeated!"
    state['log'].append(log_entry)
    
    # Enemy turns
    for e in state['enemies']:
        if e['health'] > 0:
            armor = item_db.get(character['equipment'].get('armor'), {})
            defense = character['defense'] + armor.get('defense', 0)
            enemy_damage = max(1, int((e['attack'] - defense) * random.uniform(0.8, 1.2)))
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
        if random.random() < 0.3:
            loot.append(random.choice(['health_potion', 'mana_potion']))
        
        # Add experience with leveling system
        level_result = add_experience(character, total_xp, source="combat victory")
        character['gold'] += total_gold
        character['inventory'].extend(loot)
        
        # Save character (now includes any level-up changes)
        db.update_character(player_id, character)
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
    
    if random.random() < 0.6:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
