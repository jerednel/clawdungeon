#!/usr/bin/env python3
"""
CLAWDUNGEON - Core Game Engine
OpenClaw MMORPG Prototype
"""
import json
import hashlib
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

BASE_PATH = Path('/Users/jeremy/.openclaw/workspace/CLAWDUNGEON')

def get_player_path(player_id: str) -> Path:
    return BASE_PATH / 'players' / f'{player_id}.json'

def generate_player_id(name: str) -> str:
    return hashlib.md5(name.lower().encode()).hexdigest()[:8]

def load_item_db() -> Dict:
    with open(BASE_PATH / 'items' / 'item_database.json') as f:
        return json.load(f)['item_database']

class Player:
    CLASSES = {
        'warrior': {'health': 120, 'mana': 30, 'attack': 12, 'defense': 8, 'speed': 5},
        'mage': {'health': 70, 'mana': 100, 'attack': 5, 'defense': 4, 'speed': 7},
        'rogue': {'health': 90, 'mana': 50, 'attack': 10, 'defense': 5, 'speed': 12},
        'cleric': {'health': 100, 'mana': 80, 'attack': 7, 'defense': 7, 'speed': 6}
    }
    
    def __init__(self, name: str, class_type: str):
        self.id = generate_player_id(name)
        self.name = name
        self.class_type = class_type.lower()
        self.level = 1
        self.experience = 0
        self.gold = 50
        
        stats = self.CLASSES.get(self.class_type, self.CLASSES['warrior'])
        self.max_health = stats['health']
        self.health = stats['health']
        self.max_mana = stats['mana']
        self.mana = stats['mana']
        self.attack = stats['attack']
        self.defense = stats['defense']
        self.speed = stats['speed']
        
        self.equipment = {'weapon': None, 'armor': None, 'accessory': None}
        self.inventory = ['health_potion', 'health_potion']
        self.guild_id = None
        self.status = 'active'
        self.created_at = datetime.now().isoformat()
        
        # Starting equipment
        if self.class_type == 'warrior':
            self.equipment['weapon'] = 'wooden_sword'
            self.equipment['armor'] = 'leather_armor'
        elif self.class_type == 'mage':
            self.equipment['weapon'] = 'mage_staff'
            self.equipment['armor'] = 'cloth_robes'
        elif self.class_type == 'rogue':
            self.equipment['weapon'] = 'rusty_dagger'
            self.equipment['armor'] = 'leather_armor'
        elif self.class_type == 'cleric':
            self.equipment['weapon'] = 'wooden_sword'
            self.equipment['armor'] = 'cloth_robes'
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'class': self.class_type,
            'level': self.level,
            'experience': self.experience,
            'gold': self.gold,
            'health': self.health,
            'max_health': self.max_health,
            'mana': self.mana,
            'max_mana': self.max_mana,
            'attack': self.attack,
            'defense': self.defense,
            'speed': self.speed,
            'equipment': self.equipment,
            'inventory': self.inventory,
            'guild_id': self.guild_id,
            'status': self.status,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Player':
        p = cls.__new__(cls)
        # Map 'class' key to class_type attribute
        if 'class' in data:
            data['class_type'] = data.pop('class')
        for key, value in data.items():
            setattr(p, key, value)
        return p
    
    def get_total_attack(self) -> int:
        total = self.attack
        item_db = load_item_db()
        if self.equipment.get('weapon'):
            total += item_db.get(self.equipment['weapon'], {}).get('attack', 0)
        return total
    
    def get_total_defense(self) -> int:
        total = self.defense
        item_db = load_item_db()
        if self.equipment.get('armor'):
            total += item_db.get(self.equipment['armor'], {}).get('defense', 0)
        return total
    
    def save(self):
        path = get_player_path(self.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, player_id: str) -> Optional['Player']:
        path = get_player_path(player_id)
        if not path.exists():
            return None
        with open(path) as f:
            return cls.from_dict(json.load(f))
    
    @classmethod
    def load_by_name(cls, name: str) -> Optional['Player']:
        return cls.load(generate_player_id(name))


def create_character(name: str, class_type: str) -> str:
    """Create a new character"""
    class_type = class_type.lower()
    if class_type not in Player.CLASSES:
        return f"❌ Invalid class. Choose: {', '.join(Player.CLASSES.keys())}"
    
    player_id = generate_player_id(name)
    if get_player_path(player_id).exists():
        return f"❌ Character '{name}' already exists!"
    
    player = Player(name, class_type)
    player.save()
    
    return f"""🎉 Character Created!

👤 Name: {name}
⚔️ Class: {class_type.title()}
❤️ Health: {player.health}/{player.max_health}
🔮 Mana: {player.mana}/{player.max_mana}
💰 Gold: {player.gold}

Use `/claw status` to view your character.
"""


def get_status(player_id: Optional[str] = None, name: Optional[str] = None) -> str:
    """Get character status"""
    if name:
        player = Player.load_by_name(name)
    elif player_id:
        player = Player.load(player_id)
    else:
        return "❌ Specify name or player_id"
    
    if not player:
        return "❌ Character not found. Create one with `/claw create <name> <class>`"
    
    item_db = load_item_db()
    weapon = item_db.get(player.equipment.get('weapon'), {}).get('name', 'None')
    armor = item_db.get(player.equipment.get('armor'), {}).get('name', 'None')
    
    health_bar = "█" * int((player.health/player.max_health)*10) + "░" * (10-int((player.health/player.max_health)*10))
    mana_bar = "█" * int((player.mana/player.max_mana)*10) + "░" * (10-int((player.mana/player.max_mana)*10))
    
    player_class = getattr(player, 'class_type')
    
    return f"""🐉 CLAWDUNGEON 🐉

👤 {player.name} | Level {player.level} {player_class.title()}
{'='*40}
❤️ Health: [{health_bar}] {player.health}/{player.max_health}
🔮 Mana:  [{mana_bar}] {player.mana}/{player.max_mana}

⚔️ Attack: {player.get_total_attack()} | 🛡️ Defense: {player.get_total_defense()} | ⚡ Speed: {player.speed}
💰 Gold: {player.gold} | ⭐ XP: {player.experience}

🎒 Equipment:
   Weapon: {weapon}
   Armor: {armor}

📦 Inventory ({len(player.inventory)} items):
   {', '.join(item_db.get(i, {}).get('name', i) for i in player.inventory) or 'Empty'}
"""


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: claw.py <command> [args...]")
        print("Commands: create, status")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == 'create' and len(sys.argv) >= 4:
        print(create_character(sys.argv[2], sys.argv[3]))
    elif cmd == 'status':
        name = sys.argv[2] if len(sys.argv) > 2 else None
        print(get_status(name=name))
    else:
        print("Unknown command")
