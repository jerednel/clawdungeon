#!/usr/bin/env python3
"""
CLAWDUNGEON - Database Layer
SQLite backend for VPS deployment
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

BASE_PATH = Path(__file__).parent
DB_PATH = BASE_PATH / "clawdungeon.db"

# Item Database (static)
ITEM_DATABASE = {
    "rusty_dagger": {"name": "Rusty Dagger", "type": "weapon", "attack": 3, "value": 5},
    "wooden_sword": {"name": "Wooden Sword", "type": "weapon", "attack": 5, "value": 10},
    "iron_sword": {"name": "Iron Sword", "type": "weapon", "attack": 12, "value": 50},
    "mage_staff": {"name": "Apprentice Staff", "type": "weapon", "attack": 4, "magic": 8, "value": 15},
    "leather_armor": {"name": "Leather Armor", "type": "armor", "defense": 5, "value": 20},
    "cloth_robes": {"name": "Cloth Robes", "type": "armor", "defense": 2, "magic": 5, "value": 10},
    "health_potion": {"name": "Health Potion", "type": "consumable", "effect": "heal", "amount": 25, "value": 10},
    "mana_potion": {"name": "Mana Potion", "type": "consumable", "effect": "restore_mana", "amount": 20, "value": 10},
}

class Database:
    def __init__(self):
        self.conn = None
    
    def init(self):
        """Initialize database"""
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create tables if not exist"""
        cursor = self.conn.cursor()
        
        # Players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)
        
        # Characters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                name TEXT NOT NULL,
                class TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 50,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                mana INTEGER DEFAULT 50,
                max_mana INTEGER DEFAULT 50,
                attack INTEGER DEFAULT 10,
                defense INTEGER DEFAULT 5,
                speed INTEGER DEFAULT 5,
                equipment TEXT DEFAULT '{}',
                inventory TEXT DEFAULT '[]',
                guild_id TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id),
                UNIQUE(player_id, name)
            )
        """)
        
        # Combat state table (temporary)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS combat_states (
                player_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        """)
        
        self.conn.commit()
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    # Player methods
    def username_exists(self, username: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM players WHERE username = ?", (username,))
        return cursor.fetchone() is not None
    
    def create_player(self, username: str, password_hash: str, api_key: str) -> str:
        import uuid
        player_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO players (id, username, password_hash, api_key, created_at) VALUES (?, ?, ?, ?, ?)",
            (player_id, username, password_hash, api_key, datetime.now().isoformat())
        )
        self.conn.commit()
        return player_id
    
    def get_player_by_username(self, username: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM players WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_player_by_api_key(self, api_key: str) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM players WHERE api_key = ?", (api_key,))
        row = cursor.fetchone()
        return row[0] if row else None
    
    def get_player_count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        return cursor.fetchone()[0]
    
    # Character methods
    def character_exists(self, player_id: str, name: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM characters WHERE player_id = ? AND name = ?",
            (player_id, name)
        )
        return cursor.fetchone() is not None
    
    def create_character(self, player_id: str, character: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO characters 
            (player_id, name, class, level, experience, gold, health, max_health, mana, max_mana,
             attack, defense, speed, equipment, inventory, guild_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id, character['name'], character['class'], character['level'],
            character['experience'], character['gold'], character['health'],
            character['max_health'], character['mana'], character['max_mana'],
            character['attack'], character['defense'], character['speed'],
            json.dumps(character['equipment']), json.dumps(character['inventory']),
            character.get('guild_id'), character['status'], character['created_at']
        ))
        self.conn.commit()
    
    def get_active_character(self, player_id: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM characters WHERE player_id = ? AND status = 'active'",
            (player_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        char = dict(row)
        char['equipment'] = json.loads(char['equipment'])
        char['inventory'] = json.loads(char['inventory'])
        return char
    
    def update_character(self, player_id: str, character: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE characters SET
                level = ?, experience = ?, gold = ?, health = ?, max_health = ?,
                mana = ?, max_mana = ?, attack = ?, defense = ?, speed = ?,
                equipment = ?, inventory = ?, guild_id = ?, status = ?
            WHERE player_id = ? AND name = ?
        """, (
            character['level'], character['experience'], character['gold'],
            character['health'], character['max_health'], character['mana'],
            character['max_mana'], character['attack'], character['defense'],
            character['speed'], json.dumps(character['equipment']),
            json.dumps(character['inventory']), character.get('guild_id'),
            character['status'], player_id, character['name']
        ))
        self.conn.commit()
    
    # Combat state methods
    def get_combat_state(self, player_id: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT state FROM combat_states WHERE player_id = ?", (player_id,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    
    def set_combat_state(self, player_id: str, state: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO combat_states (player_id, state, created_at)
            VALUES (?, ?, ?)
        """, (player_id, json.dumps(state), datetime.now().isoformat()))
        self.conn.commit()
    
    def clear_combat_state(self, player_id: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM combat_states WHERE player_id = ?", (player_id,))
        self.conn.commit()
    
    # Item database
    def get_item_database(self) -> Dict:
        return ITEM_DATABASE
