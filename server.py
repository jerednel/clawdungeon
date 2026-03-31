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
from database import Database

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

class CombatActionRequest(BaseModel):
    target: int = Field(default=0, ge=0)

class GuildCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=30)

class EnemyConfig:
    TYPES = {
        'goblin': {'name': 'Goblin Scout', 'health': 25, 'attack': 8, 'defense': 3, 'xp': 15, 'gold': 5},
        'skeleton': {'name': 'Skeleton Warrior', 'health': 40, 'attack': 12, 'defense': 5, 'xp': 25, 'gold': 10},
        'orc': {'name': 'Orc Berserker', 'health': 60, 'attack': 15, 'defense': 8, 'xp': 40, 'gold': 15},
        'spider': {'name': 'Giant Spider', 'health': 35, 'attack': 10, 'defense': 4, 'xp': 20, 'gold': 8},
        'wolf': {'name': 'Dire Wolf', 'health': 45, 'attack': 14, 'defense': 6, 'xp': 30, 'gold': 12},
    }

class PlayerClass:
    CLASSES = {
        'warrior': {'health': 120, 'mana': 30, 'attack': 12, 'defense': 8, 'speed': 5},
        'mage': {'health': 70, 'mana': 100, 'attack': 5, 'defense': 4, 'speed': 7},
        'rogue': {'health': 90, 'mana': 50, 'attack': 10, 'defense': 5, 'speed': 12},
        'cleric': {'health': 100, 'mana': 80, 'attack': 7, 'defense': 7, 'speed': 6}
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
    """Create a new character"""
    if db.character_exists(player_id, request.name):
        raise HTTPException(status_code=400, detail="Character name already exists")
    
    class_stats = PlayerClass.CLASSES[request.class_type]
    
    # Starting equipment
    equipment = {'weapon': None, 'armor': None, 'accessory': None}
    if request.class_type == 'warrior':
        equipment = {'weapon': 'wooden_sword', 'armor': 'leather_armor', 'accessory': None}
    elif request.class_type == 'mage':
        equipment = {'weapon': 'mage_staff', 'armor': 'cloth_robes', 'accessory': None}
    elif request.class_type == 'rogue':
        equipment = {'weapon': 'rusty_dagger', 'armor': 'leather_armor', 'accessory': None}
    elif request.class_type == 'cleric':
        equipment = {'weapon': 'wooden_sword', 'armor': 'cloth_robes', 'accessory': None}
    
    character = {
        'player_id': player_id,
        'name': request.name,
        'class': request.class_type,
        'level': 1,
        'experience': 0,
        'gold': 50,
        'health': class_stats['health'],
        'max_health': class_stats['health'],
        'mana': class_stats['mana'],
        'max_mana': class_stats['mana'],
        'attack': class_stats['attack'],
        'defense': class_stats['defense'],
        'speed': class_stats['speed'],
        'equipment': equipment,
        'inventory': ['health_potion', 'health_potion'],
        'guild_id': None,
        'status': 'active',
        'created_at': datetime.now().isoformat()
    }
    
    db.create_character(player_id, character)
    
    return {
        "message": "Character created successfully",
        "character": {
            "name": request.name,
            "class": request.class_type,
            "health": character['health'],
            "mana": character['mana']
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
    
    return {
        "character": {
            "name": character['name'],
            "level": character['level'],
            "class": character['class'],
            "health_bar": f"[{health_bar}] {character['health']}/{character['max_health']}",
            "mana": f"{character['mana']}/{character['max_mana']}",
            "attack": total_attack,
            "defense": total_defense,
            "speed": character['speed'],
            "gold": character['gold'],
            "experience": character['experience'],
            "equipment": {
                "weapon": weapon.get('name', 'None'),
                "armor": armor.get('name', 'None')
            },
            "inventory": [item_db.get(i, {}).get('name', i) for i in character['inventory']]
        }
    }

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
    for enemy_type in enemies:
        base = EnemyConfig.TYPES[enemy_type]
        combat_enemies.append({
            'type': enemy_type,
            'name': base['name'],
            'health': base['health'],
            'max_health': base['health'],
            'attack': base['attack'],
            'defense': base['defense'],
            'xp_reward': base['xp'],
            'gold_reward': base['gold']
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
    
    # Calculate damage
    character = db.get_active_character(player_id)
    item_db = db.get_item_database()
    weapon = item_db.get(character['equipment'].get('weapon'), {})
    attack_power = character['attack'] + weapon.get('attack', 0)
    
    base_damage = max(1, attack_power - enemy['defense'])
    variance = random.uniform(0.8, 1.2)
    crit = random.random() < 0.15
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
        
        character['experience'] += total_xp
        character['gold'] += total_gold
        character['inventory'].extend(loot)
        db.update_character(player_id, character)
        db.clear_combat_state(player_id)
        
        return {
            "result": "victory",
            "rewards": {
                "xp": total_xp,
                "gold": total_gold,
                "loot": loot
            },
            "log": state['log']
        }
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
