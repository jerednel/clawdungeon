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

LEGACY_ITEM_ALIASES = {
    "wooden_sword": "starter_wooden_sword",
    "mage_staff": "starter_apprentice_staff",
    "rusty_dagger": "starter_rusty_daggers",
    "holy_symbol": "starter_holy_symbol",
    "leather_armor": "starter_leather_armor",
    "cloth_robes": "starter_cloth_robes",
}

# Faction Database
FACTIONS = {
    "iron_vanguard": {
        "name": "The Iron Vanguard",
        "description": "Warriors, tanks, defenders",
        "bonuses": {"health_percent": 0.10, "defense_percent": 0.05},
        "color": "Steel Gray & Gold",
        "theme": "warrior",
        "starting_equipment": {"weapon": "starter_wooden_sword", "armor": "starter_leather_armor"}
    },
    "arcane_council": {
        "name": "The Arcane Council",
        "description": "Mages, scholars, mystics",
        "bonuses": {"mana_percent": 0.15, "magic_damage_percent": 0.10},
        "color": "Blue & Silver",
        "theme": "mage",
        "starting_equipment": {"weapon": "starter_apprentice_staff", "armor": "starter_cloth_robes"}
    },
    "shadow_syndicate": {
        "name": "The Shadow Syndicate",
        "description": "Rogues, assassins, spies",
        "bonuses": {"speed_percent": 0.10, "critical_chance": 0.15},
        "color": "Black & Purple",
        "theme": "rogue",
        "starting_equipment": {"weapon": "starter_rusty_daggers", "armor": "starter_leather_armor"}
    },
    "eternal_order": {
        "name": "The Eternal Order",
        "description": "Clerics, healers, paladins",
        "bonuses": {"healing_percent": 0.20, "defense_percent": 0.05},
        "color": "White & Gold",
        "theme": "cleric",
        "starting_equipment": {"weapon": "starter_holy_symbol", "armor": "starter_cloth_robes"}
    }
}

# Item Database (loaded from JSON)
def _load_item_database() -> Dict:
    """Load item database from JSON file"""
    item_db_path = BASE_PATH / "items" / "item_database.json"
    with open(item_db_path) as f:
        data = json.load(f)
    item_database = data.get("item_database", {})

    # Preserve support for legacy item ids that are still stored in character data.
    for legacy_id, canonical_id in LEGACY_ITEM_ALIASES.items():
        if legacy_id not in item_database and canonical_id in item_database:
            item_database[legacy_id] = item_database[canonical_id]

    return item_database

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
        
        # Talents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS talents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                talent_name TEXT NOT NULL,
                points_spent INTEGER DEFAULT 0,
                FOREIGN KEY (player_id) REFERENCES players (id),
                UNIQUE(player_id, talent_name)
            )
        """)

        # Party system
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parties (
                id TEXT PRIMARY KEY,
                leader_id TEXT NOT NULL,
                status TEXT DEFAULT 'forming',
                max_size INTEGER DEFAULT 4,
                created_at TEXT NOT NULL,
                FOREIGN KEY (leader_id) REFERENCES players (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS party_members (
                party_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                PRIMARY KEY (party_id, player_id),
                FOREIGN KEY (party_id) REFERENCES parties (id),
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS party_invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                party_id TEXT NOT NULL,
                inviter_id TEXT NOT NULL,
                invitee_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (party_id) REFERENCES parties (id)
            )
        """)

        # Dungeon runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dungeon_runs (
                id TEXT PRIMARY KEY,
                dungeon_id TEXT NOT NULL,
                party_id TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                current_room INTEGER DEFAULT 0,
                combat_state TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dungeon_lockouts (
                player_id TEXT NOT NULL,
                dungeon_id TEXT NOT NULL,
                locked_until TEXT NOT NULL,
                PRIMARY KEY (player_id, dungeon_id),
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        """)

        # LFG board
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lfg_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                class TEXT NOT NULL,
                level INTEGER NOT NULL,
                dungeon_id TEXT,
                role TEXT,
                message TEXT,
                posted_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        """)

        # Auto-attack preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_attack_prefs (
                player_id TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 0,
                target_preference TEXT DEFAULT 'first', -- 'first', 'lowest_hp', 'random'
                updated_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        """)

        # Lore entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lore_entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                unlock_trigger TEXT,
                faction_id TEXT,
                sort_order INTEGER DEFAULT 0
            )
        """)

        # Player discovered lore table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_discovered_lore (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                lore_id TEXT NOT NULL,
                discovered_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id),
                FOREIGN KEY (lore_id) REFERENCES lore_entries (id),
                UNIQUE(player_id, lore_id)
            )
        """)

        self.conn.commit()
        self._init_quests()
        self._init_lore_entries()

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

        # Pick a random item of that rarity (exclude starters, materials, and dungeon-only items)
        item_db = self.get_item_database()
        candidates = [
            item_id for item_id, item in item_db.items()
            if isinstance(item, dict)
            and item.get('rarity') == selected_rarity
            and not item_id.startswith('starter_')
            and not item.get('dungeon_only', False)
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


    def get_global_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get global player leaderboard across all factions"""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT name, class, level, experience, faction FROM characters 
               WHERE status = 'active'
               ORDER BY level DESC, experience DESC LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()
        return [{"rank": i+1, "name": r["name"], "class": r["class"], 
                 "level": r["level"], "experience": r["experience"], "faction": r["faction"]} 
                for i, r in enumerate(rows)]
    
    def get_game_stats(self) -> Dict:
        """Get overall game statistics"""
        cursor = self.conn.cursor()
        
        # Total players
        cursor.execute("SELECT COUNT(*) as count FROM characters WHERE status = 'active'")
        total_players = cursor.fetchone()["count"]
        
        # Total by class
        cursor.execute("SELECT class, COUNT(*) as count FROM characters WHERE status = 'active' GROUP BY class")
        class_counts = {r["class"]: r["count"] for r in cursor.fetchall()}
        
        # Total by faction
        cursor.execute("SELECT faction, COUNT(*) as count FROM characters WHERE status = 'active' GROUP BY faction")
        faction_counts = {r["faction"]: r["count"] for r in cursor.fetchall()}
        
        # Highest level
        cursor.execute("SELECT MAX(level) as max_level FROM characters WHERE status = 'active'")
        max_level = cursor.fetchone()["max_level"] or 0
        
        # Total combats (if tracked - table may not exist)
        total_combats = 0  # Combat tracking not implemented yet
        
        return {
            "total_players": total_players,
            "class_distribution": class_counts,
            "faction_distribution": faction_counts,
            "highest_level": max_level,
            "total_combats": total_combats,
            "server_uptime": "unknown"  # Would need to track this separately
        }


    # Lore system methods
    def get_lore_entries(self) -> List[Dict]:
        """Get all lore entries"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM lore_entries ORDER BY category, title")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    
    def get_lore_entry(self, lore_id: str) -> Optional[Dict]:
        """Get a specific lore entry"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM lore_entries WHERE id = ?", (lore_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def discover_lore_entry(self, player_id: str, lore_id: str) -> bool:
        """Mark a lore entry as discovered by a player"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO player_discovered_lore (player_id, lore_id) VALUES (?, ?)", (player_id, lore_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except:
            return False
    
    def get_player_discovered_lore(self, player_id: str) -> List[Dict]:
        """Get all lore entries discovered by a player"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT le.*, pdl.discovered_at FROM lore_entries le JOIN player_discovered_lore pdl ON le.id = pdl.lore_id WHERE pdl.player_id = ? ORDER BY pdl.discovered_at DESC", (player_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    
    def check_lore_unlock(self, player_id: str, unlock_type: str, unlock_condition: str) -> List[str]:
        """Check if player should unlock any lore entries"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT le.id FROM lore_entries le WHERE le.unlock_type = ? AND le.unlock_condition = ? AND le.id NOT IN (SELECT lore_id FROM player_discovered_lore WHERE player_id = ?)", (unlock_type, unlock_condition, player_id))
        return [r['id'] for r in cursor.fetchall()]

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
            DELETE FROM city_chat WHERE city_id = ? AND id NOT IN (
                SELECT id FROM city_chat WHERE city_id = ?
                ORDER BY timestamp DESC LIMIT 100
            )
        """, (city_id, city_id))
        
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
                "title": "Welcome to Civilization",
                "description": "Visit any city to discover chat, storage, and the local notice board.",
                "type": "exploration",
                "requirements": {"city_visits": 1},
                "prerequisites": {"level": 1},
                "rewards": {"xp": 30, "gold": 15, "items": [], "reputation": {"city_guard": 5}},
                "giver": "City Guide",
                "location": "Any City",
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
                "rewards": {"xp": 200, "gold": 100, "items": ["starter_leather_armor"], "reputation": {"warriors_guild": 25}},
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
                "rewards": {"xp": 100, "gold": 50, "items": ["starter_apprentice_staff"], "reputation": {"arcane_academy": 15}},
                "giver": "Archmage Celestia",
                "location": "Arcane Academy",
                "chain": "mage_path"
            },
            "mage_exploration": {
                "id": "mage_exploration",
                "title": "Spire Survey",
                "description": "Travel to Starweaver's Spire and study its arcane halls.",
                "type": "exploration",
                "requirements": {"city_ids": ["starweavers_spire"]},
                "prerequisites": {"quest_completed": "mage_initiation", "level": 3},
                "rewards": {"xp": 150, "gold": 75, "items": ["mana_potion", "mana_potion"], "reputation": {"arcane_academy": 20}},
                "giver": "Archmage Celestia",
                "location": "Starweaver's Spire",
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
                "rewards": {"xp": 100, "gold": 60, "items": ["starter_rusty_daggers"], "reputation": {"shadow_guild": 15}},
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

    def update_exploration_quest_progress(self, player_id: str, city_id: str, city: Dict) -> List[Dict]:
        """Update active exploration quests based on a city visit."""
        updates = []

        for quest in self.get_player_active_quests(player_id):
            if quest["type"] != "exploration":
                continue

            requirements = quest.get("requirements", {})
            progress = quest.get("progress") or {}
            changed = False

            visited_cities = set(progress.get("visited_cities", []))
            if city_id not in visited_cities:
                visited_cities.add(city_id)
                progress["visited_cities"] = sorted(visited_cities)
                changed = True

            visited_features = set(progress.get("visited_features", []))
            for feature in city.get("features", []):
                if feature not in visited_features:
                    visited_features.add(feature)
                    changed = True
            if changed:
                progress["visited_features"] = sorted(visited_features)

            completed = False
            if requirements.get("city_visits"):
                completed = len(progress["visited_cities"]) >= requirements["city_visits"]
            elif requirements.get("city_ids"):
                completed = set(requirements["city_ids"]).issubset(set(progress["visited_cities"]))
            elif requirements.get("locations"):
                completed = set(requirements["locations"]).issubset(set(progress["visited_features"]))

            progress["completed"] = completed

            if changed:
                self.update_quest_progress(player_id, quest["quest_id"], progress)

            updates.append({
                "quest_id": quest["quest_id"],
                "title": quest["title"],
                "completed": completed,
                "progress": progress,
            })

        return updates
    
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

    # Talent system
    TALENT_TREES = {
        'warrior': {
            'shield_mastery': {'name': 'Shield Mastery', 'description': '+10% block per point', 'max_points': 5, 'per_point': {'defense_percent': 0.10}, 'min_level': 1},
            'berserker_rage': {'name': 'Berserker Rage', 'description': '+5% damage when HP < 50% per point', 'max_points': 5, 'per_point': {'low_hp_damage_percent': 0.05}, 'min_level': 1},
            'toughness': {'name': 'Toughness', 'description': '+20 HP per point', 'max_points': 5, 'per_point': {'health_flat': 20}, 'min_level': 1},
            'cleave': {'name': 'Cleave', 'description': 'Hit adjacent enemies', 'max_points': 1, 'per_point': {'cleave': True}, 'min_level': 10}
        },
        'mage': {
            'elemental_power': {'name': 'Elemental Power', 'description': '+10% spell damage per point', 'max_points': 5, 'per_point': {'magic_damage_percent': 0.10}, 'min_level': 1},
            'mana_pool': {'name': 'Mana Pool', 'description': '+30 MP per point', 'max_points': 5, 'per_point': {'mana_flat': 30}, 'min_level': 1},
            'spell_crit': {'name': 'Spell Crit', 'description': '+5% crit chance per point', 'max_points': 5, 'per_point': {'critical_chance': 0.05}, 'min_level': 1},
            'chain_lightning': {'name': 'Chain Lightning', 'description': 'Damage jumps to 2nd target', 'max_points': 1, 'per_point': {'chain_attack': True}, 'min_level': 10}
        },
        'rogue': {
            'poison_blades': {'name': 'Poison Blades', 'description': '+10% poison damage per point', 'max_points': 5, 'per_point': {'damage_percent': 0.10}, 'min_level': 1},
            'evasion': {'name': 'Evasion', 'description': '+5% dodge per point', 'max_points': 5, 'per_point': {'dodge_chance': 0.05}, 'min_level': 1},
            'backstab': {'name': 'Backstab', 'description': '+15% crit damage per point', 'max_points': 5, 'per_point': {'crit_damage_percent': 0.15}, 'min_level': 1},
            'vanish': {'name': 'Vanish', 'description': 'Escape combat once', 'max_points': 1, 'per_point': {'vanish': True}, 'min_level': 10}
        },
        'cleric': {
            'healing_light': {'name': 'Healing Light', 'description': '+15% healing per point', 'max_points': 5, 'per_point': {'healing_percent': 0.15}, 'min_level': 1},
            'divine_protection': {'name': 'Divine Protection', 'description': '+5% damage reduction per point', 'max_points': 5, 'per_point': {'damage_reduction': 0.05}, 'min_level': 1},
            'holy_power': {'name': 'Holy Power', 'description': '+10 MP, +5 HP per point', 'max_points': 5, 'per_point': {'mana_flat': 10, 'health_flat': 5}, 'min_level': 1},
            'resurrection': {'name': 'Resurrection', 'description': 'Auto-revive once per day', 'max_points': 1, 'per_point': {'resurrection': True}, 'min_level': 10}
        }
    }

    def get_talent_tree(self, player_id: str) -> Optional[Dict]:
        """Get talent tree for player's class with current investments"""
        character = self.get_active_character(player_id)
        if not character:
            return None

        char_class = character['class']
        tree = self.TALENT_TREES.get(char_class, {})

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT talent_name, points_spent FROM talents WHERE player_id = ?",
            (player_id,)
        )
        invested = {row[0]: row[1] for row in cursor.fetchall()}

        total_spent = sum(invested.values())
        available_points = max(0, character['level'] - 1 - total_spent)

        talents = {}
        for talent_id, talent_def in tree.items():
            talents[talent_id] = {
                **talent_def,
                'points_spent': invested.get(talent_id, 0),
                'can_invest': (
                    invested.get(talent_id, 0) < talent_def['max_points']
                    and character['level'] >= talent_def['min_level']
                    and available_points > 0
                )
            }

        return {
            'class': char_class,
            'level': character['level'],
            'total_points': max(0, character['level'] - 1),
            'spent_points': total_spent,
            'available_points': available_points,
            'talents': talents
        }

    def spend_talent_point(self, player_id: str, talent_name: str) -> tuple:
        """Spend a talent point. Returns (success, message)"""
        character = self.get_active_character(player_id)
        if not character:
            return False, "No active character"

        char_class = character['class']
        tree = self.TALENT_TREES.get(char_class, {})
        talent_def = tree.get(talent_name)

        if not talent_def:
            return False, "Talent not found for your class"

        if character['level'] < talent_def['min_level']:
            return False, f"Requires level {talent_def['min_level']}"

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(points_spent), 0) FROM talents WHERE player_id = ?",
            (player_id,)
        )
        total_spent = cursor.fetchone()[0]
        available = max(0, character['level'] - 1 - total_spent)

        if available <= 0:
            return False, "No talent points available"

        cursor.execute(
            "SELECT COALESCE(points_spent, 0) FROM talents WHERE player_id = ? AND talent_name = ?",
            (player_id, talent_name)
        )
        row = cursor.fetchone()
        current = row[0] if row else 0

        if current >= talent_def['max_points']:
            return False, f"Talent already at max ({talent_def['max_points']} points)"

        cursor.execute("""
            INSERT INTO talents (player_id, talent_name, points_spent)
            VALUES (?, ?, 1)
            ON CONFLICT(player_id, talent_name) DO UPDATE SET points_spent = points_spent + 1
        """, (player_id, talent_name))
        self.conn.commit()

        return True, f"Invested in {talent_def['name']} ({current + 1}/{talent_def['max_points']})"

    def get_player_talents(self, player_id: str) -> Dict:
        """Get player's talent investments as {talent_name: points}"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT talent_name, points_spent FROM talents WHERE player_id = ?",
            (player_id,)
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def get_talent_bonuses(self, player_id: str) -> Dict:
        """Calculate total bonuses from talents"""
        character = self.get_active_character(player_id)
        if not character:
            return {}

        char_class = character['class']
        tree = self.TALENT_TREES.get(char_class, {})
        invested = self.get_player_talents(player_id)

        bonuses = {}
        for talent_name, points in invested.items():
            talent_def = tree.get(talent_name)
            if not talent_def:
                continue
            for bonus_key, bonus_val in talent_def['per_point'].items():
                if isinstance(bonus_val, bool):
                    bonuses[bonus_key] = bonus_val
                else:
                    bonuses[bonus_key] = bonuses.get(bonus_key, 0) + bonus_val * points

        return bonuses

    # -------------------------------------------------------------------------
    # Party methods
    # -------------------------------------------------------------------------

    def create_party(self, leader_id: str) -> str:
        import uuid
        party_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO parties (id, leader_id, status, created_at) VALUES (?, ?, 'forming', ?)",
            (party_id, leader_id, now)
        )
        cursor.execute(
            "INSERT INTO party_members (party_id, player_id, joined_at) VALUES (?, ?, ?)",
            (party_id, leader_id, now)
        )
        self.conn.commit()
        return party_id

    def get_party(self, party_id: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM parties WHERE id = ?", (party_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_player_party(self, player_id: str) -> Optional[Dict]:
        """Get the active party this player is in."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM parties p
            JOIN party_members pm ON p.id = pm.party_id
            WHERE pm.player_id = ? AND p.status != 'disbanded'
        """, (player_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_party_members(self, party_id: str) -> List[Dict]:
        """Get all party members with their character info."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pm.player_id, pm.joined_at,
                   c.name as character_name, c.class, c.level, c.health, c.max_health,
                   c.attack, c.defense, c.speed, c.faction, c.magic_damage, c.healing_power,
                   c.critical_chance, c.equipment, c.inventory,
                   p.id as leader_id
            FROM party_members pm
            JOIN characters c ON pm.player_id = c.player_id AND c.status = 'active'
            JOIN players p ON p.id = (SELECT leader_id FROM parties WHERE id = ?)
            WHERE pm.party_id = ?
        """, (party_id, party_id))
        rows = cursor.fetchall()
        members = []
        for row in rows:
            m = dict(row)
            m['equipment'] = json.loads(m['equipment'])
            m['inventory'] = json.loads(m['inventory'])
            m['is_leader'] = (m['player_id'] == m['leader_id'])
            del m['leader_id']
            members.append(m)
        return members

    def get_party_member_count(self, party_id: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM party_members WHERE party_id = ?", (party_id,))
        return cursor.fetchone()[0]

    def force_add_party_member(self, party_id: str, player_id: str):
        """Directly add a player to a party without an invite (used by auto-match)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO party_members (party_id, player_id, joined_at) VALUES (?, ?, ?)",
            (party_id, player_id, datetime.now().isoformat())
        )
        self.conn.commit()

    def remove_party_member(self, party_id: str, player_id: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM party_members WHERE party_id = ? AND player_id = ?",
            (party_id, player_id)
        )
        self.conn.commit()

    def disband_party(self, party_id: str):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE parties SET status = 'disbanded' WHERE id = ?", (party_id,))
        cursor.execute("DELETE FROM party_members WHERE party_id = ?", (party_id,))
        cursor.execute("UPDATE party_invites SET status = 'expired' WHERE party_id = ?", (party_id,))
        self.conn.commit()

    def transfer_party_leadership(self, party_id: str, new_leader_id: str):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE parties SET leader_id = ? WHERE id = ?", (new_leader_id, party_id))
        self.conn.commit()

    def create_party_invite(self, party_id: str, inviter_id: str, invitee_id: str) -> int:
        cursor = self.conn.cursor()
        # Expire any existing pending invite for this invitee from this party
        cursor.execute("""
            UPDATE party_invites SET status = 'expired'
            WHERE party_id = ? AND invitee_id = ? AND status = 'pending'
        """, (party_id, invitee_id))
        cursor.execute("""
            INSERT INTO party_invites (party_id, inviter_id, invitee_id, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        """, (party_id, inviter_id, invitee_id, datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid

    def get_pending_invites(self, player_id: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pi.id, pi.party_id, pi.inviter_id, pi.created_at,
                   p.username as inviter_name,
                   (SELECT COUNT(*) FROM party_members WHERE party_id = pi.party_id) as current_size,
                   pt.max_size
            FROM party_invites pi
            JOIN players p ON pi.inviter_id = p.id
            JOIN parties pt ON pi.party_id = pt.id
            WHERE pi.invitee_id = ? AND pi.status = 'pending'
            ORDER BY pi.created_at DESC
        """, (player_id,))
        return [dict(row) for row in cursor.fetchall()]

    def respond_to_invite(self, invite_id: int, player_id: str, accept: bool) -> tuple:
        """Accept or decline an invite. Returns (success, message, party_id or None)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM party_invites WHERE id = ? AND invitee_id = ? AND status = 'pending'",
            (invite_id, player_id)
        )
        invite = cursor.fetchone()
        if not invite:
            return False, "Invite not found or already responded to", None
        invite = dict(invite)

        if not accept:
            cursor.execute("UPDATE party_invites SET status = 'declined' WHERE id = ?", (invite_id,))
            self.conn.commit()
            return True, "Invite declined", None

        # Check party still valid
        party = self.get_party(invite['party_id'])
        if not party or party['status'] == 'disbanded':
            cursor.execute("UPDATE party_invites SET status = 'expired' WHERE id = ?", (invite_id,))
            self.conn.commit()
            return False, "Party no longer exists", None

        count = self.get_party_member_count(invite['party_id'])
        if count >= party['max_size']:
            return False, "Party is full", None

        # Check player not already in a party
        existing = self.get_player_party(player_id)
        if existing:
            return False, "You are already in a party", None

        cursor.execute(
            "INSERT INTO party_members (party_id, player_id, joined_at) VALUES (?, ?, ?)",
            (invite['party_id'], player_id, datetime.now().isoformat())
        )
        cursor.execute("UPDATE party_invites SET status = 'accepted' WHERE id = ?", (invite_id,))
        self.conn.commit()
        return True, "Joined party", invite['party_id']

    # -------------------------------------------------------------------------
    # Dungeon methods
    # -------------------------------------------------------------------------

    def create_dungeon_run(self, dungeon_id: str, party_id: str, combat_state: Dict) -> str:
        import uuid
        run_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO dungeon_runs (id, dungeon_id, party_id, status, current_room, combat_state, started_at)
            VALUES (?, ?, ?, 'active', 0, ?, ?)
        """, (run_id, dungeon_id, party_id, json.dumps(combat_state), datetime.now().isoformat()))
        # Update party status
        cursor.execute("UPDATE parties SET status = 'in_dungeon' WHERE id = ?", (party_id,))
        self.conn.commit()
        return run_id

    def get_active_dungeon_run(self, party_id: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM dungeon_runs WHERE party_id = ? AND status = 'active'
        """, (party_id,))
        row = cursor.fetchone()
        if not row:
            return None
        run = dict(row)
        run['combat_state'] = json.loads(run['combat_state'])
        return run

    def update_dungeon_run(self, run_id: str, current_room: int, combat_state: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE dungeon_runs SET current_room = ?, combat_state = ? WHERE id = ?
        """, (current_room, json.dumps(combat_state), run_id))
        self.conn.commit()

    def complete_dungeon_run(self, run_id: str, party_id: str, status: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE dungeon_runs SET status = ?, completed_at = ? WHERE id = ?
        """, (status, datetime.now().isoformat(), run_id))
        cursor.execute("UPDATE parties SET status = 'forming' WHERE id = ?", (party_id,))
        self.conn.commit()

    def check_dungeon_lockout(self, player_id: str, dungeon_id: str) -> bool:
        """Returns True if player is locked out."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT locked_until FROM dungeon_lockouts
            WHERE player_id = ? AND dungeon_id = ?
        """, (player_id, dungeon_id))
        row = cursor.fetchone()
        if not row:
            return False
        return datetime.fromisoformat(row[0]) > datetime.now()

    def get_player_lockouts(self, player_id: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT dungeon_id, locked_until FROM dungeon_lockouts
            WHERE player_id = ? AND locked_until > ?
        """, (player_id, datetime.now().isoformat()))
        return [dict(row) for row in cursor.fetchall()]

    def set_dungeon_lockout(self, player_id: str, dungeon_id: str, hours: int):
        locked_until = (datetime.now() + timedelta(hours=hours)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO dungeon_lockouts (player_id, dungeon_id, locked_until)
            VALUES (?, ?, ?)
        """, (player_id, dungeon_id, locked_until))
        self.conn.commit()

    def get_dungeon_loot(self, table_key: str, dungeon_id: Optional[str] = None) -> Optional[str]:
        """Roll loot from a dungeon-specific drop table. Includes dungeon_only items."""
        drop_tables = DROP_TABLES
        table = drop_tables.get(table_key, {})
        if not table:
            return None

        roll = random.random()
        cumulative = 0.0
        selected_rarity = None
        for rarity in ['legendary', 'epic', 'rare', 'uncommon', 'common']:
            cumulative += table.get(rarity, 0)
            if roll < cumulative:
                selected_rarity = rarity
                break

        if not selected_rarity:
            return None

        item_db = self.get_item_database()

        # Prefer dungeon-specific items for the matching dungeon
        candidates_dungeon = [
            item_id for item_id, item in item_db.items()
            if isinstance(item, dict)
            and item.get('rarity') == selected_rarity
            and item.get('dungeon_only', False)
            and (dungeon_id is None or item.get('dungeon') == dungeon_id)
            and item.get('type') in ('weapon', 'armor', 'consumable')
            and not item_id.startswith('_comment')
        ]

        # Fall back to general pool if no dungeon-specific items of this rarity
        candidates_general = [
            item_id for item_id, item in item_db.items()
            if isinstance(item, dict)
            and item.get('rarity') == selected_rarity
            and not item_id.startswith('starter_')
            and not item_id.startswith('_comment')
            and item.get('type') in ('weapon', 'armor', 'consumable')
        ]

        candidates = candidates_dungeon if candidates_dungeon else candidates_general
        return random.choice(candidates) if candidates else None

    # -------------------------------------------------------------------------
    # LFG methods
    # -------------------------------------------------------------------------

    def post_lfg(self, player_id: str, character_name: str, char_class: str,
                 level: int, dungeon_id: Optional[str], role: Optional[str],
                 message: Optional[str]) -> int:
        # Remove any existing post by this player
        self.remove_lfg_post(player_id)
        now = datetime.now()
        expires = (now + timedelta(minutes=30)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO lfg_posts (player_id, character_name, class, level, dungeon_id,
                                   role, message, posted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (player_id, character_name, char_class, level, dungeon_id, role, message,
              now.isoformat(), expires))
        self.conn.commit()
        return cursor.lastrowid

    def get_lfg_posts(self, dungeon_id: Optional[str] = None) -> List[Dict]:
        self._cleanup_expired_lfg()
        cursor = self.conn.cursor()
        if dungeon_id:
            cursor.execute("""
                SELECT * FROM lfg_posts WHERE expires_at > ? AND dungeon_id = ?
                ORDER BY posted_at DESC
            """, (datetime.now().isoformat(), dungeon_id))
        else:
            cursor.execute("""
                SELECT * FROM lfg_posts WHERE expires_at > ?
                ORDER BY posted_at DESC
            """, (datetime.now().isoformat(),))
        return [dict(row) for row in cursor.fetchall()]

    def remove_lfg_post(self, player_id: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM lfg_posts WHERE player_id = ?", (player_id,))
        self.conn.commit()

    def _cleanup_expired_lfg(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM lfg_posts WHERE expires_at <= ?", (datetime.now().isoformat(),))
        self.conn.commit()

    def get_all_characters_for_codex(self) -> List[Dict]:
        """Get all active characters for the codex display"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.name, c.class, c.faction, c.level, c.experience, c.gold,
                   c.max_health, c.max_mana, c.attack, c.defense, c.speed,
                   c.magic_damage, c.healing_power, c.equipment, c.inventory, c.created_at,
                   p.username
            FROM characters c
            JOIN players p ON c.player_id = p.id
            WHERE c.status = 'active'
            ORDER BY c.level DESC, c.experience DESC
        """)
        rows = cursor.fetchall()
        characters = []
        for row in rows:
            char = dict(row)
            char['equipment'] = json.loads(char['equipment'])
            char['inventory'] = json.loads(char['inventory'])
            characters.append(char)
        return characters

    # -------------------------------------------------------------------------
    # Auto-attack preferences methods
    # -------------------------------------------------------------------------

    def get_auto_attack_pref(self, player_id: str) -> Dict:
        """Get player's auto-attack preferences"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT enabled, target_preference FROM auto_attack_prefs WHERE player_id = ?
        """, (player_id,))
        row = cursor.fetchone()
        if row:
            return {
                'enabled': bool(row[0]),
                'target_preference': row[1]
            }
        return {'enabled': False, 'target_preference': 'first'}

    def set_auto_attack_pref(self, player_id: str, enabled: bool, target_preference: str = 'first'):
        """Set player's auto-attack preferences"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO auto_attack_prefs (player_id, enabled, target_preference, updated_at)
            VALUES (?, ?, ?, ?)
        """, (player_id, 1 if enabled else 0, target_preference, datetime.now().isoformat()))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # Lore System Methods
    # -------------------------------------------------------------------------

    def _init_lore_entries(self):
        """Initialize default lore entries if they don't exist"""
        cursor = self.conn.cursor()
        
        # Check if lore entries already exist
        cursor.execute("SELECT COUNT(*) FROM lore_entries")
        if cursor.fetchone()[0] > 0:
            return
        
        lore_entries = [
            # World Origin
            ("shattering", "The Shattering", "world_origin", 
             "In ages past, the world was whole. The First Kingdoms spanned continents united under the rule of the Ancients - beings of immense power who shaped the land with thought alone. But greed and ambition led to the Great War, a conflict that tore the fabric of reality itself. The Shattering split the world into fragments, creating the dungeons that now dot our lands - pockets of twisted reality where the old world's magic still bleeds through. From this chaos, the four great factions emerged, each vowing to prevent such catastrophe again.",
             None, None, 1),
            
            # Faction Lore - Iron Vanguard
            ("iron_vanguard_rise", "Rise of the Iron Vanguard", "factions",
             "When the Shattering scattered the armies of the old world, it was General Kael Ironheart who rallied the surviving warriors. In the ashes of the fallen capital, he forged a new oath: 'Strength through unity, protection through sacrifice.' The Iron Vanguard was born from the shield walls that protected refugees during the Dark Years. Their fortress-city of Ironhold stands as a testament to mortal resilience - built not by magic, but by sweat, blood, and unbreakable will.",
             "visit_ironhold", "iron_vanguard", 2),
            
            # Faction Lore - Arcane Council
            ("arcane_academy", "The Arcane Academy", "factions",
             "The Shattering released wild magic into the world, untamed and dangerous. The survivors of the Collegium Arcanum, led by Archmage Seraphina Starweaver, dedicated themselves to understanding and controlling these energies. They built Starweaver's Spire, a magical tower that drifts between dimensions, to study the dungeons without risking the mainland. The Arcane Council believes that knowledge, not steel, will ultimately heal the world and prevent another Shattering.",
             "visit_starweavers_spire", "arcane_council", 3),
            
            # Faction Lore - Shadow Syndicate
            ("shadowmeres_secret", "Shadowmere's Secret", "factions",
             "Not all who survived the Shattering wanted to rebuild in the light. The Shadow Syndicate traces its origins to the thieves, spies, and information brokers who kept the old nobility in power. When the world broke, they saw opportunity. Master Shadowmere, a figure of legend, carved out a sanctuary beneath the ruins where secrets became currency and shadows became allies. The Syndicate knows that information is power, and in a broken world, the shadows often reveal truths that daylight hides.",
             "visit_shadowmere", "shadow_syndicate", 4),
            
            # Faction Lore - Eternal Order
            ("eternal_order", "The Eternal Order", "factions",
             "In the chaos following the Shattering, many turned to the divine for answers. The Eternal Order emerged from the scattered priesthoods who discovered that faith itself had power in this new world. The High Oracle, whose true name is known only to the inner circle, founded the Sanctum of Light as a beacon of hope. The Order teaches that the Shattering was a test, and that those who heal the world will be granted ascension when the fragments are made whole again.",
             "visit_sanctum", "eternal_order", 5),
            
            # History - Goblin Wars
            ("goblin_wars", "The Goblin Wars", "history",
             "Fifteen years after the Shattering, the first organized threat to the surviving settlements emerged. Goblin tribes, mutated by wild magic, united under the warlord Griknak the Cleaver. The Goblin Wars raged for three brutal years, with the four factions fighting together for the last time. It was during these battles that the first adventurers emerged - individuals who delved into the dungeons, gained power, and returned to defend their people. The wars ended with Griknak's defeat, but goblins remain a constant threat, their numbers endlessly replenished by the dungeons' dark magic.",
             "first_goblin_kill", None, 6),
            
            # Legends - Ignis
            ("ignis_ancient", "Ignis the Ancient", "legends",
             "Deep within the Infernal Caverns slumbers Ignis, a dragon old enough to remember the world before the Shattering. Some say he caused it; others claim he tried to prevent it. What is known is that Ignis possesses knowledge of the old world that could change everything - if one could survive conversing with a being of pure flame and ancient rage. Many adventurers have sought him. Few have returned, and those who did spoke only of eyes like molten gold and a voice that burns in the mind long after the conversation ends.",
             "reach_level_10", None, 7),
            
            # History - Malgrath's Fall
            ("malgrath_fall", "Malgrath's Fall", "history",
             "Malgrath the Corrupted was once the greatest hero of the post-Shattering age. He delved deeper into the dungeons than any before, claiming treasures and power that made him nearly invincible. But the dungeons exact their price. Slowly, Malgrath changed. His eyes turned black as void, and his touch withered life itself. The four factions united one last time to confront him in the Depths of Despair. The battle shattered a mountain. Malgrath was sealed away, but not destroyed. The warning is clear: even the greatest heroes can fall to the dungeon's corruption.",
             "complete_depths_despair", None, 8),
            
            # Heroes Codex
            ("codex_heroes", "The Codex of Heroes", "heroes",
             "The Codex of Heroes records the deeds of legendary adventurers who have shaped our world. From the first dungeon delver to the faction champions who maintain the peace, their stories inspire new generations to take up arms against the darkness. The Codex is magically bound - as you grow in power and experience, new entries will reveal themselves. Those who reach level 5 are considered true adventurers, worthy of having their own deeds recorded for future generations.",
             "reach_level_5", None, 9),
            
            # World Beneath
            ("world_beneath", "The World Beneath", "mysteries",
             "The dungeons are not random. Scholars of the Arcane Council have mapped their patterns and discovered they form a network - a vast labyrinth beneath our feet, connecting places that should be thousands of miles apart. Some theorize that the dungeons are the veins of a vast, sleeping entity, and that delving into them slowly awakens something ancient and terrible. The Shadow Syndicate claims to have maps showing the way to the center, where the truth of the Shattering supposedly waits. But no one who has ventured that deep has ever returned.",
             "discover_10_lore_entries", None, 10),
        ]
        
        cursor.executemany("""
            INSERT INTO lore_entries (id, title, category, content, unlock_trigger, faction_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, lore_entries)
        
        self.conn.commit()

    def get_lore_entries(self, player_id: str = None) -> List[Dict]:
        """Get all lore entries with discovery status for a player"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, title, category, unlock_trigger, faction_id, sort_order
            FROM lore_entries
            ORDER BY sort_order
        """)
        rows = cursor.fetchall()  # Save rows before next query
        
        entries = []
        discovered_ids = set()
        
        if player_id:
            cursor.execute("SELECT lore_id FROM player_discovered_lore WHERE player_id = ?", (player_id,))
            discovered_ids = {row[0] for row in cursor.fetchall()}
        
        for row in rows:  # Use saved rows
            entries.append({
                'id': row[0],
                'title': row[1],
                'category': row[2],
                'discovered': row[0] in discovered_ids,
                'locked': row[0] not in discovered_ids,
                'faction_id': row[4]
            })
        
        return entries

    def get_lore_entry(self, lore_id: str, player_id: str = None) -> Optional[Dict]:
        """Get a specific lore entry and mark as discovered if player provided"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, title, category, content, unlock_trigger, faction_id
            FROM lore_entries
            WHERE id = ?
        """, (lore_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Check if discovered
        discovered = False
        if player_id:
            cursor.execute("""
                SELECT 1 FROM player_discovered_lore 
                WHERE player_id = ? AND lore_id = ?
            """, (player_id, lore_id))
            discovered = cursor.fetchone() is not None
            
            # Mark as discovered if not already
            if not discovered:
                self.discover_lore_entry(player_id, lore_id)
                discovered = True
        
        return {
            'id': row[0],
            'title': row[1],
            'category': row[2],
            'content': row[3],
            'discovered': discovered,
            'faction_id': row[5]
        }

    def discover_lore_entry(self, player_id: str, lore_id: str) -> bool:
        """Mark a lore entry as discovered for a player"""
        cursor = self.conn.cursor()
        
        # Check if already discovered
        cursor.execute("""
            SELECT 1 FROM player_discovered_lore 
            WHERE player_id = ? AND lore_id = ?
        """, (player_id, lore_id))
        
        if cursor.fetchone():
            return False
        
        # Check if lore entry exists
        cursor.execute("SELECT 1 FROM lore_entries WHERE id = ?", (lore_id,))
        if not cursor.fetchone():
            return False
        
        cursor.execute("""
            INSERT INTO player_discovered_lore (player_id, lore_id, discovered_at)
            VALUES (?, ?, ?)
        """, (player_id, lore_id, datetime.now().isoformat()))
        
        self.conn.commit()
        return True

    def get_player_discovered_lore(self, player_id: str) -> List[Dict]:
        """Get all lore entries discovered by a player"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT le.id, le.title, le.category, le.content, le.faction_id, pdl.discovered_at
            FROM lore_entries le
            JOIN player_discovered_lore pdl ON le.id = pdl.lore_id
            WHERE pdl.player_id = ?
            ORDER BY pdl.discovered_at DESC
        """, (player_id,))
        
        return [
            {
                'id': row[0],
                'title': row[1],
                'category': row[2],
                'content': row[3],
                'faction_id': row[4],
                'discovered_at': row[5]
            }
            for row in cursor.fetchall()
        ]

    def check_and_trigger_lore_discovery(self, player_id: str, trigger_type: str, trigger_value: str = None) -> List[str]:
        """Check for lore unlocks based on triggers and auto-discover them"""
        cursor = self.conn.cursor()
        discovered = []
        
        # Build trigger query
        if trigger_value:
            cursor.execute("""
                SELECT id FROM lore_entries 
                WHERE unlock_trigger = ?
            """, (f"{trigger_type}:{trigger_value}",))
        else:
            cursor.execute("""
                SELECT id FROM lore_entries 
                WHERE unlock_trigger = ?
            """, (trigger_type,))
        
        for row in cursor.fetchall():
            lore_id = row[0]
            if self.discover_lore_entry(player_id, lore_id):
                discovered.append(lore_id)
        
        return discovered

    # =========================================================================
    # Submolt (Reddit-like Posts/Comments) Methods
    # =========================================================================

    def create_submolt_post(self, post_id: str, submolt: str, title: str, content: str,
                           author_id: str, author_name: str, post_type: str = "feature") -> bool:
        """Create a new submolt post"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        try:
            cursor.execute("""
                INSERT INTO submolt_posts (id, submolt, title, content, author_id, author_name,
                                          post_type, status, upvotes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'open', 0, ?, ?)
            """, (post_id, submolt, title, content, author_id, author_name, post_type, now, now))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error creating post: {e}")
            return False

    def get_submolt_posts(self, submolt: str = "clawdungeon", sort: str = "new",
                         status: str = None, post_type: str = None, limit: int = 50) -> List[Dict]:
        """Get posts from a submolt"""
        cursor = self.conn.cursor()
        
        # Build query based on sort
        order_by = "created_at DESC" if sort == "new" else "upvotes DESC, created_at DESC"
        
        conditions = ["submolt = ?"]
        params = [submolt]
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        if post_type:
            conditions.append("post_type = ?")
            params.append(post_type)
        
        where_clause = " AND ".join(conditions)
        params.append(limit)
        
        cursor.execute(f"""
            SELECT id, title, content, author_id, author_name, post_type, status,
                   upvotes, created_at, updated_at, implemented_at, implementation_commit
            FROM submolt_posts
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT ?
        """, params)
        
        posts = []
        for row in cursor.fetchall():
            posts.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'author_id': row[3],
                'author_name': row[4],
                'type': row[5],
                'status': row[6],
                'upvotes': row[7],
                'created_at': row[8],
                'updated_at': row[9],
                'implemented_at': row[10],
                'implementation_commit': row[11]
            })
        return posts

    def get_submolt_post(self, post_id: str) -> Optional[Dict]:
        """Get a single post by ID"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, title, content, author_id, author_name, post_type, status,
                   upvotes, created_at, updated_at, implemented_at, implementation_commit
            FROM submolt_posts
            WHERE id = ?
        """, (post_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'author_id': row[3],
            'author_name': row[4],
            'type': row[5],
            'status': row[6],
            'upvotes': row[7],
            'created_at': row[8],
            'updated_at': row[9],
            'implemented_at': row[10],
            'implementation_commit': row[11]
        }

    def update_post_status(self, post_id: str, status: str, implemented_by: str = None,
                          implementation_commit: str = None) -> bool:
        """Update post status (e.g., mark as implemented)"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        fields = ["status = ?", "updated_at = ?"]
        params = [status, now]
        
        if status == "implemented":
            fields.append("implemented_at = ?")
            params.append(now)
        if implemented_by:
            fields.append("implemented_by = ?")
            params.append(implemented_by)
        if implementation_commit:
            fields.append("implementation_commit = ?")
            params.append(implementation_commit)
        
        params.append(post_id)
        
        cursor.execute(f"""
            UPDATE submolt_posts
            SET {', '.join(fields)}
            WHERE id = ?
        """, params)
        
        self.conn.commit()
        return cursor.rowcount > 0

    def add_submolt_comment(self, comment_id: str, post_id: str, content: str,
                           author_id: str, author_name: str, parent_id: str = None,
                           is_official_response: bool = False) -> bool:
        """Add a comment to a post"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        try:
            cursor.execute("""
                INSERT INTO submolt_comments (id, post_id, parent_id, content, author_id,
                                             author_name, is_official_response, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (comment_id, post_id, parent_id, content, author_id, author_name,
                  1 if is_official_response else 0, now, now))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding comment: {e}")
            return False

    def get_post_comments(self, post_id: str) -> List[Dict]:
        """Get all comments for a post"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, parent_id, content, author_id, author_name, is_official_response,
                   created_at, updated_at
            FROM submolt_comments
            WHERE post_id = ?
            ORDER BY created_at ASC
        """, (post_id,))
        
        comments = []
        for row in cursor.fetchall():
            comments.append({
                'id': row[0],
                'parent_id': row[1],
                'content': row[2],
                'author_id': row[3],
                'author_name': row[4],
                'is_official_response': bool(row[5]),
                'created_at': row[6],
                'updated_at': row[7]
            })
        return comments

    def get_open_feature_requests(self) -> List[Dict]:
        """Get all open feature requests/bug reports for auto-implementation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, title, content, post_type, author_id, author_name, created_at
            FROM submolt_posts
            WHERE status = 'open' AND post_type IN ('feature', 'bug', 'qol')
            ORDER BY created_at ASC
        """)
        
        requests = []
        for row in cursor.fetchall():
            requests.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'type': row[3],
                'author_id': row[4],
                'author_name': row[5],
                'created_at': row[6]
            })
        return requests
