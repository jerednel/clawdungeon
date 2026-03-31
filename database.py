#!/usr/bin/env python3
"""
CLAWDUNGEON - Database Layer
SQLite backend for VPS deployment
"""
import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

BASE_PATH = Path(__file__).parent
DB_PATH = BASE_PATH / "clawdungeon.db"

# Faction Database
FACTIONS = {
    "iron_vanguard": {
        "name": "The Iron Vanguard",
        "description": "Warriors, tanks, defenders",
        "bonuses": {"health_percent": 0.10, "defense_percent": 0.05},
        "color": "Steel Gray & Gold",
        "theme": "warrior",
        "starting_equipment": {"weapon": "wooden_sword", "armor": "leather_armor"}
    },
    "arcane_council": {
        "name": "The Arcane Council",
        "description": "Mages, scholars, mystics",
        "bonuses": {"mana_percent": 0.15, "magic_damage_percent": 0.10},
        "color": "Blue & Silver",
        "theme": "mage",
        "starting_equipment": {"weapon": "mage_staff", "armor": "cloth_robes"}
    },
    "shadow_syndicate": {
        "name": "The Shadow Syndicate",
        "description": "Rogues, assassins, spies",
        "bonuses": {"speed_percent": 0.10, "critical_chance": 0.15},
        "color": "Black & Purple",
        "theme": "rogue",
        "starting_equipment": {"weapon": "rusty_dagger", "armor": "leather_armor"}
    },
    "eternal_order": {
        "name": "The Eternal Order",
        "description": "Clerics, healers, paladins",
        "bonuses": {"healing_percent": 0.20, "defense_percent": 0.05},
        "color": "White & Gold",
        "theme": "cleric",
        "starting_equipment": {"weapon": "wooden_sword", "armor": "cloth_robes"}
    }
}

# Item Database (loaded from JSON)
def _load_item_database() -> Dict:
    """Load item database from JSON file"""
    item_db_path = BASE_PATH / "items" / "item_database.json"
    with open(item_db_path) as f:
        data = json.load(f)
    return data.get("item_database", {})

ITEM_DATABASE = _load_item_database()

def _load_drop_tables() -> Dict:
    """Load drop tables from JSON file"""
    item_db_path = BASE_PATH / "items" / "item_database.json"
    with open(item_db_path) as f:
        data = json.load(f)
    return data.get("drop_tables", {})

DROP_TABLES = _load_drop_tables()

# City Definitions (static)
CITIES = {
    "ironhold": {
        "id": "ironhold",
        "name": "Ironhold",
        "faction": "Iron Vanguard",
        "description": "A formidable fortress city with towering stone walls and iron gates. Home to warriors and defenders.",
        "type": "fortress",
        "features": ["blacksmith", "barracks", "training_ground", "bank", "notice_board"]
    },
    "starweavers_spire": {
        "id": "starweavers_spire",
        "name": "Starweaver's Spire",
        "faction": "Arcane Council",
        "description": "A mystical floating tower that drifts among the clouds. The center of magical learning and arcane knowledge.",
        "type": "magical",
        "features": ["magic_shop", "library", "enchanting_station", "bank", "notice_board"]
    },
    "shadowmere": {
        "id": "shadowmere",
        "name": "Shadowmere",
        "faction": "Shadow Syndicate",
        "description": "A hidden underground den carved into the depths. Where shadows gather and secrets are traded.",
        "type": "underground",
        "features": ["black_market", "tavern", "thieves_guild", "bank", "notice_board"]
    },
    "sanctum_of_light": {
        "id": "sanctum_of_light",
        "name": "Sanctum of Light",
        "faction": "Eternal Order",
        "description": "A magnificent holy cathedral city that shines with divine radiance. A place of healing and faith.",
        "type": "holy",
        "features": ["temple", "hospital", "blessing_altar", "bank", "notice_board"]
    }
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
                faction TEXT DEFAULT 'none',
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
                critical_chance REAL DEFAULT 0.15,
                magic_damage INTEGER DEFAULT 0,
                healing_power INTEGER DEFAULT 0,
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
        
        # City chat messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        """)
        
        # Player location tracking (which city they're in)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_locations (
                player_id TEXT PRIMARY KEY,
                city_id TEXT,
                entered_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        """)
        
        # City storage (bank) table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_storage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                city_id TEXT NOT NULL,
                items TEXT DEFAULT '[]',
                gold INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id),
                UNIQUE(player_id, city_id)
            )
        """)
        
        # Notice board quests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notice_board (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                quest_type TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                reward_gold INTEGER DEFAULT 0,
                reward_xp INTEGER DEFAULT 0,
                reward_item TEXT,
                posted_by TEXT,
                posted_at TEXT NOT NULL,
                expires_at TEXT,
                claimed_by TEXT,
                status TEXT DEFAULT 'available'
            )
        """)
        
        # Quest definitions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                type TEXT NOT NULL,
                requirements TEXT NOT NULL,
                prerequisites TEXT NOT NULL,
                rewards TEXT NOT NULL,
                giver TEXT NOT NULL,
                location TEXT NOT NULL,
                chain TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Player quests table (quest progress)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                quest_id TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                progress TEXT DEFAULT '{}',
                accepted_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (player_id) REFERENCES players (id),
                FOREIGN KEY (quest_id) REFERENCES quests (id),
                UNIQUE(player_id, quest_id)
            )
        """)
        
        # Reputation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reputation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                faction TEXT NOT NULL,
                value INTEGER DEFAULT 0,
                FOREIGN KEY (player_id) REFERENCES players (id),
                UNIQUE(player_id, faction)
            )
        """)
        
        self.conn.commit()
        self._init_quests()
    
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
            (player_id, name, class, faction, level, experience, gold, health, max_health, mana, max_mana,
             attack, defense, speed, critical_chance, magic_damage, healing_power, equipment, inventory, guild_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id, character['name'], character['class'], character.get('faction', 'none'),
            character['level'], character['experience'], character['gold'], character['health'],
            character['max_health'], character['mana'], character['max_mana'],
            character['attack'], character['defense'], character['speed'],
            character.get('critical_chance', 0.15), character.get('magic_damage', 0),
            character.get('healing_power', 0),
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
                critical_chance = ?, magic_damage = ?, healing_power = ?,
                equipment = ?, inventory = ?, guild_id = ?, status = ?
            WHERE player_id = ? AND name = ?
        """, (
            character['level'], character['experience'], character['gold'],
            character['health'], character['max_health'], character['mana'],
            character['max_mana'], character['attack'], character['defense'],
            character['speed'], character.get('critical_chance', 0.15),
            character.get('magic_damage', 0), character.get('healing_power', 0),
            json.dumps(character['equipment']),
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

    def get_inventory_with_details(self, player_id: str) -> Optional[Dict]:
        """Get player inventory with item details and equipment info"""
        character = self.get_active_character(player_id)
        if not character:
            return None

        item_db = self.get_item_database()

        # Build inventory with details
        inventory_items = []
        for item_id in character['inventory']:
            item_info = item_db.get(item_id, {"name": item_id, "type": "unknown"})
            inventory_items.append({
                "id": item_id,
                **item_info
            })

        # Build equipment with details
        equipment_details = {}
        for slot in ('weapon', 'armor', 'helmet', 'boots', 'accessory'):
            item_id = character['equipment'].get(slot)
            if item_id:
                item_info = item_db.get(item_id, {"name": item_id})
                equipment_details[slot] = {"id": item_id, **item_info}
            else:
                equipment_details[slot] = None

        return {
            "inventory": inventory_items,
            "inventory_count": len(character['inventory']),
            "max_slots": 20,
            "equipment": equipment_details,
            "gold": character['gold']
        }

    def get_loot_drop(self, enemy_type: str) -> Optional[str]:
        """Roll for a loot drop based on enemy type and drop tables"""
        common_enemies = ['goblin', 'slime', 'spider']
        hard_enemies = ['skeleton', 'wolf', 'orc']
        boss_enemies = ['dragon_ignis', 'skeleton_king']

        if enemy_type in boss_enemies:
            table = DROP_TABLES.get('bosses', {})
        elif enemy_type in hard_enemies:
            table = DROP_TABLES.get('hard_mobs', {})
        else:
            table = DROP_TABLES.get('common_mobs', {})

        if not table:
            return None

        # Roll for rarity
        roll = random.random()
        cumulative = 0.0
        selected_rarity = None
        for rarity in ['epic', 'rare', 'uncommon', 'common']:
            cumulative += table.get(rarity, 0)
            if roll < cumulative:
                selected_rarity = rarity
                break

        if not selected_rarity:
            return None

        # Pick a random item of that rarity (exclude starters and materials)
        item_db = self.get_item_database()
        candidates = [
            item_id for item_id, item in item_db.items()
            if isinstance(item, dict)
            and item.get('rarity') == selected_rarity
            and not item_id.startswith('starter_')
            and item.get('type') in ('weapon', 'armor', 'consumable')
        ]

        if not candidates:
            return None

        return random.choice(candidates)

    # Faction methods
    def get_faction_stats(self) -> Dict:
        """Get statistics for all factions (member count, total levels, etc.)"""
        cursor = self.conn.cursor()
        stats = {}
        for faction_id in FACTIONS.keys():
            # Count members
            cursor.execute(
                "SELECT COUNT(*) FROM characters WHERE faction = ? AND status = 'active'",
                (faction_id,)
            )
            member_count = cursor.fetchone()[0]
            
            # Total levels (sum of all members' levels)
            cursor.execute(
                "SELECT COALESCE(SUM(level), 0) FROM characters WHERE faction = ? AND status = 'active'",
                (faction_id,)
            )
            total_levels = cursor.fetchone()[0]
            
            # Top player in faction
            cursor.execute(
                """SELECT name, level, class FROM characters 
                   WHERE faction = ? AND status = 'active' 
                   ORDER BY level DESC, experience DESC LIMIT 1""",
                (faction_id,)
            )
            top_player = cursor.fetchone()
            
            stats[faction_id] = {
                "member_count": member_count,
                "total_levels": total_levels,
                "average_level": round(total_levels / member_count, 1) if member_count > 0 else 0,
                "top_player": {
                    "name": top_player['name'],
                    "level": top_player['level'],
                    "class": top_player['class']
                } if top_player else None
            }
        return stats
    
    def get_faction_leaderboard(self, faction_id: str, limit: int = 10) -> List[Dict]:
        """Get leaderboard for a specific faction"""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT name, class, level, experience FROM characters 
               WHERE faction = ? AND status = 'active'
               ORDER BY level DESC, experience DESC LIMIT ?""",
            (faction_id, limit)
        )
        rows = cursor.fetchall()
        return [{"rank": i+1, "name": r["name"], "class": r["class"], 
                 "level": r["level"], "experience": r["experience"]} 
                for i, r in enumerate(rows)]
    
    # City methods
    def get_cities(self) -> Dict:
        """Get all city definitions"""
        return CITIES
    
    def get_city(self, city_id: str) -> Optional[Dict]:
        """Get a specific city by ID"""
        return CITIES.get(city_id)
    
    # City chat methods
    def add_city_chat_message(self, city_id: str, player_id: str, character_name: str, message: str):
        """Add a chat message to a city - keeps only last 100 messages per city"""
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        
        # Insert the new message
        cursor.execute("""
            INSERT INTO city_chat (city_id, player_id, character_name, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (city_id, player_id, character_name, message, timestamp))
        
        # Delete old messages if more than 100 for this city
        cursor.execute("""
            DELETE FROM city_chat WHERE id IN (
                SELECT id FROM city_chat WHERE city_id = ?
                ORDER BY timestamp DESC LIMIT -1 OFFSET 100
            )
        """, (city_id,))
        
        self.conn.commit()
    
    def get_city_chat(self, city_id: str, limit: int = 50) -> List[Dict]:
        """Get recent chat messages for a city"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, city_id, player_id, character_name, message, timestamp
            FROM city_chat WHERE city_id = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (city_id, limit))
        rows = cursor.fetchall()
        messages = [dict(row) for row in rows]
        messages.reverse()  # Return in chronological order
        return messages
    
    # Player location methods
    def set_player_location(self, player_id: str, city_id: Optional[str]):
        """Set player's current city location"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO player_locations (player_id, city_id, entered_at)
            VALUES (?, ?, ?)
        """, (player_id, city_id, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_player_location(self, player_id: str) -> Optional[str]:
        """Get player's current city ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT city_id FROM player_locations WHERE player_id = ?", (player_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    
    def get_players_in_city(self, city_id: str) -> List[Dict]:
        """Get list of players currently in a city"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pl.player_id, pl.entered_at, c.name as character_name
            FROM player_locations pl
            JOIN characters c ON pl.player_id = c.player_id
            WHERE pl.city_id = ? AND c.status = 'active'
        """, (city_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # City storage (bank) methods
    def get_city_storage(self, player_id: str, city_id: str) -> Dict:
        """Get player's storage in a specific city"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT items, gold FROM city_storage WHERE player_id = ? AND city_id = ?
        """, (player_id, city_id))
        row = cursor.fetchone()
        if row:
            return {
                'items': json.loads(row[0]),
                'gold': row[1]
            }
        return {'items': [], 'gold': 0}
    
    def update_city_storage(self, player_id: str, city_id: str, items: List[str], gold: int):
        """Update player's storage in a city"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO city_storage (player_id, city_id, items, gold, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (player_id, city_id, json.dumps(items), gold, datetime.now().isoformat()))
        self.conn.commit()
    
    # Notice board methods
    def get_notice_board(self, city_id: str, limit: int = 20) -> List[Dict]:
        """Get available quests from a city's notice board"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM notice_board 
            WHERE city_id = ? AND status = 'available'
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY posted_at DESC LIMIT ?
        """, (city_id, datetime.now().isoformat(), limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def post_notice(self, city_id: str, title: str, description: str, quest_type: str,
                    difficulty: str, reward_gold: int = 0, reward_xp: int = 0,
                    reward_item: str = None, posted_by: str = None, expires_days: int = 7) -> int:
        """Post a quest to a city's notice board"""
        cursor = self.conn.cursor()
        posted_at = datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        cursor.execute("""
            INSERT INTO notice_board 
            (city_id, title, description, quest_type, difficulty, reward_gold, reward_xp, 
             reward_item, posted_by, posted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (city_id, title, description, quest_type, difficulty, reward_gold, reward_xp,
              reward_item, posted_by, posted_at, expires_at))
        self.conn.commit()
        return cursor.lastrowid
    
    def claim_notice(self, notice_id: int, player_id: str) -> bool:
        """Claim a quest from the notice board"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE notice_board SET status = 'claimed', claimed_by = ?
            WHERE id = ? AND status = 'available'
        """, (player_id, notice_id))
        self.conn.commit()
        return cursor.rowcount > 0

    # Quest system methods
    def _init_quests(self):
        """Initialize quest definitions in database"""
        QUEST_DATABASE = {
            # Tutorial Quests (Available to all)
            "tutorial_first_battle": {
                "id": "tutorial_first_battle",
                "title": "Your First Battle",
                "description": "Defeat your first enemy in combat to prove you're ready for the dungeon.",
                "type": "kill",
                "requirements": {"total_kills": 1},
                "prerequisites": {"level": 1},
                "rewards": {"xp": 50, "gold": 25, "items": ["health_potion"], "reputation": {}},
                "giver": "Combat Instructor",
                "location": "Training Grounds",
                "chain": None
            },
            "tutorial_city_explorer": {
                "id": "tutorial_city_explorer",
                "title": "Welcome to Clawhaven",
                "description": "Visit the Market, Tavern, and Temple districts of the city.",
                "type": "exploration",
                "requirements": {"locations": ["market", "tavern", "temple"]},
                "prerequisites": {"level": 1},
                "rewards": {"xp": 30, "gold": 15, "items": [], "reputation": {"city_guard": 5}},
                "giver": "City Guide",
                "location": "Town Square",
                "chain": None
            },
            
            # Warrior Faction Quests
            "warrior_initiation": {
                "id": "warrior_initiation",
                "title": "Path of the Blade",
                "description": "Defeat 5 goblins to prove your worth to the Warrior's Guild.",
                "type": "kill",
                "requirements": {"enemy_type": "goblin", "count": 5},
                "prerequisites": {"class": "warrior", "level": 1},
                "rewards": {"xp": 100, "gold": 50, "items": ["iron_sword"], "reputation": {"warriors_guild": 15}},
                "giver": "Guildmaster Thorne",
                "location": "Warrior's Hall",
                "chain": "warrior_path"
            },
            "warrior_proving": {
                "id": "warrior_proving",
                "title": "The Proving Grounds",
                "description": "Defeat 3 orcs to advance in the Warrior's Guild.",
                "type": "kill",
                "requirements": {"enemy_type": "orc", "count": 3},
                "prerequisites": {"quest_completed": "warrior_initiation", "level": 3},
                "rewards": {"xp": 200, "gold": 100, "items": ["leather_armor"], "reputation": {"warriors_guild": 25}},
                "giver": "Guildmaster Thorne",
                "location": "Warrior's Hall",
                "chain": "warrior_path"
            },
            
            # Mage Faction Quests
            "mage_initiation": {
                "id": "mage_initiation",
                "title": "Awakening the Arcane",
                "description": "Collect 3 mana potions and bring them to the Arcane Academy.",
                "type": "delivery",
                "requirements": {"items": {"mana_potion": 3}},
                "prerequisites": {"class": "mage", "level": 1},
                "rewards": {"xp": 100, "gold": 50, "items": ["mage_staff"], "reputation": {"arcane_academy": 15}},
                "giver": "Archmage Celestia",
                "location": "Arcane Academy",
                "chain": "mage_path"
            },
            "mage_exploration": {
                "id": "mage_exploration",
                "title": "Ancient Ruins Discovery",
                "description": "Visit the Ancient Ruins and report your findings.",
                "type": "exploration",
                "requirements": {"locations": ["ancient_ruins"]},
                "prerequisites": {"quest_completed": "mage_initiation", "level": 3},
                "rewards": {"xp": 150, "gold": 75, "items": ["mana_potion", "mana_potion"], "reputation": {"arcane_academy": 20}},
                "giver": "Archmage Celestia",
                "location": "Arcane Academy",
                "chain": "mage_path"
            },
            
            # Rogue Faction Quests
            "rogue_initiation": {
                "id": "rogue_initiation",
                "title": "Shadows and Secrets",
                "description": "Defeat 5 spiders to collect their venom glands.",
                "type": "kill",
                "requirements": {"enemy_type": "spider", "count": 5},
                "prerequisites": {"class": "rogue", "level": 1},
                "rewards": {"xp": 100, "gold": 60, "items": ["rusty_dagger"], "reputation": {"shadow_guild": 15}},
                "giver": "Shadowmaster Vex",
                "location": "Shadow Den",
                "chain": "rogue_path"
            },
            
            # Cleric Faction Quests
            "cleric_initiation": {
                "id": "cleric_initiation",
                "title": "Healing Hands",
                "description": "Deliver 5 health potions to the Temple of Light.",
                "type": "delivery",
                "requirements": {"items": {"health_potion": 5}},
                "prerequisites": {"class": "cleric", "level": 1},
                "rewards": {"xp": 100, "gold": 40, "items": ["health_potion", "health_potion", "health_potion"], "reputation": {"temple_of_light": 15}},
                "giver": "High Priestess Luna",
                "location": "Temple of Light",
                "chain": "cleric_path"
            },
            
            # Boss Quests (High level)
            "defeat_ignis": {
                "id": "defeat_ignis",
                "title": "Dragon Slayer",
                "description": "Defeat Ignis the Dragon, terror of the mountains.",
                "type": "boss",
                "requirements": {"enemy_type": "dragon_ignis", "count": 1},
                "prerequisites": {"level": 10},
                "rewards": {"xp": 1000, "gold": 500, "items": ["dragon_scale_armor"], "reputation": {"all": 50}},
                "giver": "King Aldric",
                "location": "Royal Castle",
                "chain": None
            },
            "skeleton_king_hunt": {
                "id": "skeleton_king_hunt",
                "title": "The Bone Collector",
                "description": "Defeat the Skeleton King in the Crypt of Shadows.",
                "type": "boss",
                "requirements": {"enemy_type": "skeleton_king", "count": 1},
                "prerequisites": {"level": 8},
                "rewards": {"xp": 750, "gold": 350, "items": ["iron_sword"], "reputation": {"city_guard": 30}},
                "giver": "Captain of the Guard",
                "location": "Guard Barracks",
                "chain": None
            },
            
            # General Quests
            "goblin_extermination": {
                "id": "goblin_extermination",
                "title": "Goblin Menace",
                "description": "The goblins have been raiding caravans. Defeat 10 goblins to help.",
                "type": "kill",
                "requirements": {"enemy_type": "goblin", "count": 10},
                "prerequisites": {"level": 2},
                "rewards": {"xp": 150, "gold": 75, "items": [], "reputation": {"city_guard": 10}},
                "giver": "Merchant Caravan Leader",
                "location": "City Gates",
                "chain": None
            }
        }
        
        cursor = self.conn.cursor()
        for quest_id, quest in QUEST_DATABASE.items():
            cursor.execute("""
                INSERT OR REPLACE INTO quests 
                (id, title, description, type, requirements, prerequisites, rewards, giver, location, chain, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                quest_id,
                quest['title'],
                quest['description'],
                quest['type'],
                json.dumps(quest['requirements']),
                json.dumps(quest['prerequisites']),
                json.dumps(quest['rewards']),
                quest['giver'],
                quest['location'],
                quest['chain']
            ))
        self.conn.commit()
    
    def get_all_quests(self) -> List[Dict]:
        """Get all quest definitions"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM quests WHERE is_active = 1")
        rows = cursor.fetchall()
        quests = []
        for row in rows:
            quest = dict(row)
            quest['requirements'] = json.loads(quest['requirements'])
            quest['prerequisites'] = json.loads(quest['prerequisites'])
            quest['rewards'] = json.loads(quest['rewards'])
            quests.append(quest)
        return quests
    
    def get_quest(self, quest_id: str) -> Optional[Dict]:
        """Get a specific quest by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM quests WHERE id = ? AND is_active = 1", (quest_id,))
        row = cursor.fetchone()
        if row:
            quest = dict(row)
            quest['requirements'] = json.loads(quest['requirements'])
            quest['prerequisites'] = json.loads(quest['prerequisites'])
            quest['rewards'] = json.loads(quest['rewards'])
            return quest
        return None
    
    def get_player_quests(self, player_id: str, status: str = None) -> List[Dict]:
        """Get player's quests with optional status filter"""
        cursor = self.conn.cursor()
        if status:
            cursor.execute("""
                SELECT pq.*, q.title, q.description, q.type, q.requirements, q.rewards, q.giver, q.location
                FROM player_quests pq
                JOIN quests q ON pq.quest_id = q.id
                WHERE pq.player_id = ? AND pq.status = ?
            """, (player_id, status))
        else:
            cursor.execute("""
                SELECT pq.*, q.title, q.description, q.type, q.requirements, q.rewards, q.giver, q.location
                FROM player_quests pq
                JOIN quests q ON pq.quest_id = q.id
                WHERE pq.player_id = ?
            """, (player_id,))
        rows = cursor.fetchall()
        quests = []
        for row in rows:
            quest = dict(row)
            quest['progress'] = json.loads(quest['progress'])
            quest['requirements'] = json.loads(quest['requirements'])
            quest['rewards'] = json.loads(quest['rewards'])
            quests.append(quest)
        return quests
    
    def get_player_active_quests(self, player_id: str) -> List[Dict]:
        """Get player's active quests"""
        return self.get_player_quests(player_id, 'active')
    
    def get_player_completed_quests(self, player_id: str) -> List[Dict]:
        """Get player's completed quests"""
        return self.get_player_quests(player_id, 'completed')
    
    def has_completed_quest(self, player_id: str, quest_id: str) -> bool:
        """Check if player has completed a specific quest"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM player_quests WHERE player_id = ? AND quest_id = ? AND status = 'completed'",
            (player_id, quest_id)
        )
        return cursor.fetchone() is not None
    
    def accept_quest(self, player_id: str, quest_id: str) -> bool:
        """Player accepts a quest"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO player_quests (player_id, quest_id, status, progress, accepted_at)
                VALUES (?, ?, 'active', '{}', ?)
            """, (player_id, quest_id, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def update_quest_progress(self, player_id: str, quest_id: str, progress: Dict):
        """Update quest progress"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE player_quests SET progress = ?
            WHERE player_id = ? AND quest_id = ? AND status = 'active'
        """, (json.dumps(progress), player_id, quest_id))
        self.conn.commit()
    
    def complete_quest(self, player_id: str, quest_id: str) -> bool:
        """Mark a quest as completed"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE player_quests SET status = 'completed', completed_at = ?
            WHERE player_id = ? AND quest_id = ? AND status = 'active'
        """, (datetime.now().isoformat(), player_id, quest_id))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_reputation(self, player_id: str, faction: str) -> int:
        """Get player's reputation with a faction"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT value FROM reputation WHERE player_id = ? AND faction = ?",
            (player_id, faction)
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    
    def get_all_reputation(self, player_id: str) -> Dict[str, int]:
        """Get all reputation values for a player"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT faction, value FROM reputation WHERE player_id = ?", (player_id,))
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}
    
    def modify_reputation(self, player_id: str, faction: str, amount: int):
        """Modify player's reputation with a faction"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO reputation (player_id, faction, value)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, faction) DO UPDATE SET value = value + excluded.value
        """, (player_id, faction, amount))
        self.conn.commit()
    
    def check_quest_available(self, player_id: str, quest: Dict, character: Dict) -> tuple[bool, str]:
        """Check if a quest is available to a player. Returns (available, reason)"""
        prerequisites = quest.get('prerequisites', {})
        
        # Check level requirement
        if 'level' in prerequisites:
            if character['level'] < prerequisites['level']:
                return False, f"Requires level {prerequisites['level']}"
        
        # Check class requirement
        if 'class' in prerequisites:
            if character['class'] != prerequisites['class']:
                return False, f"Requires {prerequisites['class']} class"
        
        # Check quest completion prerequisite
        if 'quest_completed' in prerequisites:
            if not self.has_completed_quest(player_id, prerequisites['quest_completed']):
                return False, f"Requires completing: {prerequisites['quest_completed']}"
        
        # Check if already active
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM player_quests WHERE player_id = ? AND quest_id = ? AND status = 'active'",
            (player_id, quest['id'])
        )
        if cursor.fetchone():
            return False, "Quest already active"
        
        # Check if already completed (non-repeatable quests)
        if quest.get('repeatable') != True:
            if self.has_completed_quest(player_id, quest['id']):
                return False, "Quest already completed"
        
        return True, "Available"
