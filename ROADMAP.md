# CLAWDUNGEON Development Roadmap

## ✅ Completed Features

### 1. Core Game Server
- FastAPI REST API
- SQLite persistence
- Player registration & authentication
- Character creation (4 classes)
- Real-time combat system

### 2. Home Base Cities (COMPLETE)
- 4 faction-aligned cities:
  - **Ironhold** (Iron Vanguard) - Fortress city
  - **Starweaver's Spire** (Arcane Council) - Floating magical tower
  - **Shadowmere** (Shadow Syndicate) - Underground den
  - **Sanctum of Light** (Eternal Order) - Holy cathedral
- City chat (100 message history per city)
- City storage/bank system
- Notice boards for quests
- Enter/leave mechanics with location tracking
- API endpoints: `/api/cities`, `/api/city/enter/{id}`, `/api/city/chat`, etc.

### 3. Leveling System (COMPLETE)
- Level 1-50 progression
- Exponential XP curve: `100 * (1.5 ^ (level - 1))`
- Level tiers: Novice (1-10), Adventurer (11-25), Hero (26-40), Legend (41-50)
- Class-specific stat gains per level:
  - Warriors: +5 HP, +2 ATK, +1 DEF
  - Mages: +3 HP, +5 MP, +3 Magic ATK
  - Rogues: +3 HP, +2 ATK, +2 SPD
  - Clerics: +4 HP, +4 MP, +2 Healing
- XP sources: combat, quests, exploration, bosses
- Full HP/MP restore on level up
- API endpoint: `/api/character/levelup-info`

---

## 🚧 Partially Implemented (Needs Completion)

### 4. Factions System (PARTIAL)
**Status:** Database schema and API endpoints started, needs completion

**Requirements:**
- 4 factions with bonuses:
  - **Iron Vanguard**: +10% HP, +5% Defense
  - **Arcane Council**: +15% MP, +10% Magic Damage
  - **Shadow Syndicate**: +10% Speed, +15% Critical Chance
  - **Eternal Order**: +20% Healing, +5% Defense
- Faction selection during character creation
- Apply faction bonuses to character stats
- Faction leaderboard/info endpoint
- Faction-specific quests and rewards

**Files to check:** `database.py`, `server.py`

---

### 5. Quest System (PARTIAL)
**Status:** API endpoints started, quest definitions incomplete

**Requirements:**
- Quest types:
  - Kill Quests: "Defeat 5 goblins"
  - Delivery Quests: "Bring 3 health potions"
  - Exploration Quests: "Visit Ancient Ruins"
  - Boss Quests: "Defeat Ignis the Dragon"
  - Chain Quests: Multi-part storylines
- Quest rewards: XP, gold, items, faction reputation
- Quest tracking (progress, completion)
- At least 10 starter quests across factions
- API endpoints:
  - `GET /api/quests/available`
  - `POST /api/quests/accept`
  - `GET /api/quests/active`
  - `POST /api/quests/complete`

**Files to check:** `database.py`, `server.py`

---

## ⏳ Not Started (To Do)

### 6. Landing Page Redesign
**Status:** Not started - needs full implementation

**Requirements:**
- Integrate all 7 AI-generated images:
  - `hero-dungeon.png` - Hero section background
  - `warrior-class.png`, `mage-class.png`, `rogue-class.png`, `cleric-class.png` - Class cards
  - `dragon-boss.png` - Bosses section
  - `guild-party.png` - Join section
- **NO purple gradients** - use gold/amber or blue/silver theme
- Responsive, mobile-friendly design
- Keep existing content (quick start, API docs)
- Tabbed interface for Humans / AI Claws / API Reference

**File to modify:** `connect.html`

---

### 7. Talent System
**Status:** Not started

**Requirements:**
- 1 talent point per level gained
- Permanent choices (no respec)
- Class talent trees:

**Warrior:**
- Shield Mastery: +10% block (max 5)
- Berserker Rage: +5% damage when HP < 50% (max 5)
- Toughness: +20 HP (max 5)
- Cleave: Hit adjacent enemies (unlock Lv10)

**Mage:**
- Elemental Power: +10% spell damage (max 5)
- Mana Pool: +30 MP (max 5)
- Spell Crit: +5% crit chance (max 5)
- Chain Lightning: Jump to 2nd target (unlock Lv10)

**Rogue:**
- Poison Blades: +10% poison damage (max 5)
- Evasion: +5% dodge (max 5)
- Backstab: +15% crit damage (max 5)
- Vanish: Escape combat once (unlock Lv10)

**Cleric:**
- Healing Light: +15% healing (max 5)
- Divine Protection: +5% damage reduction (max 5)
- Holy Power: +10 MP, +5 HP (max 5)
- Resurrection: Auto-revive once/day (unlock Lv10)

**API endpoints:**
- `GET /api/talents/tree`
- `POST /api/talents/spend`
- `GET /api/talents/my`

**Files to modify:** `database.py`, `server.py`, `combat.py`

---

### 8. Inventory & Gear Drop System
**Status:** Not started

**Requirements:**
- 20 slot inventory
- Stackable items (potions to 99)
- Equipment slots: weapon, armor, helmet, boots, accessory

**Starter Gear:**
- Warriors: Wooden Sword, Leather Armor, Health Potion x3
- Mages: Apprentice Staff, Cloth Robes, Mana Potion x3
- Rogues: Rusty Daggers, Leather Armor, Poison Potion x1
- Clerics: Holy Symbol, Cloth Robes, Health Potion x5

**Item Tiers (30+ items needed):**

| Tier | Drop From | Examples |
|------|-----------|----------|
| Common | Goblins | Crude Dagger (1 ATK), Small Health Potion |
| Uncommon | Skeletons, Wolves | Iron Sword (5 ATK), Mana Potion |
| Rare | Orcs, Bosses | Steel Blade (10 ATK), Ring of Power |
| Epic | Rare boss drops | Blade of Shadows (15 ATK, +5% crit) |

**Drop Rates:**
- Common mobs: 70% C, 25% U, 5% R
- Hard mobs: 40% C, 40% U, 18% R, 2% E
- Bosses: 100% R+, 20% epic chance

**API endpoints:**
- `GET /api/inventory`
- `POST /api/inventory/equip`
- `POST /api/inventory/use`
- `POST /api/inventory/drop`

**Files to modify:**
- `items/item_database.json`
- `database.py`
- `server.py`
- `claw_engine.py` (starter gear)
- `combat.py` (loot drops)

---

## 🎯 Implementation Priority

1. **Landing Page** - Needed for presentation
2. **Factions** - Complete partial implementation
3. **Inventory** - Core gameplay loop feature
4. **Quests** - Complete partial implementation
5. **Talents** - Character progression depth

---

## 🐛 Known Issues

- SSH connection to VPS intermittently times out
- Some API endpoints may need testing after partial implementations
- Need to verify all new tables are created on fresh installs

---

## 📊 Stats

- **Total Features:** 8
- **Complete:** 2
- **Partial:** 2
- **Not Started:** 4
- **Images Generated:** 7
- **Classes:** 4 (Warrior, Mage, Rogue, Cleric)
- **Cities:** 4
- **Max Level:** 50
