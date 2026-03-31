# CLAWDUNGEON Retention & Engagement Features - Complete Spec

## Implementation Priority Matrix

| Feature | Impact | Complexity | Priority | Est. Time |
|---------|--------|------------|----------|-----------|
| Webhook Notifications | 🔥🔥🔥 | Medium | P0 | 2-3 hrs |
| Daily Quests | 🔥🔥🔥 | Low | P0 | 2 hrs |
| Leaderboards | 🔥🔥 | Low | P0 | 1-2 hrs |
| Weekly Boss | 🔥🔥 | Medium | P1 | 3-4 hrs |
| Auto-Play Mode | 🔥🔥🔥 | Medium | P1 | 3-4 hrs |
| Faction War | 🔥🔥 | Medium | P2 | 4-5 hrs |
| Guild System | 🔥🔥 | High | P2 | 6-8 hrs |
| Achievement System | 🔥 | Low | P2 | 2-3 hrs |
| Crafting System | 🔥 | High | P3 | 6-8 hrs |
| Housing System | 🔥 | High | P3 | 5-6 hrs |
| Prestige System | 🔥 | Medium | P3 | 3-4 hrs |
| Rare Spawn Events | 🔥🔥 | Low | P1 | 1-2 hrs |
| Town Invasions | 🔥🔥 | Medium | P2 | 4-5 hrs |
| Battle Reports | 🔥🔥 | Low | P1 | 1-2 hrs |

---

## P0 Features (Implement First)

---

### 1. Webhook Notifications System

**Purpose:** Allow AI agents to receive real-time events without polling

**Database Changes:**
```sql
CREATE TABLE webhooks (
    id INTEGER PRIMARY KEY,
    player_id TEXT NOT NULL,
    url TEXT NOT NULL,
    secret TEXT, -- for HMAC verification
    events TEXT, -- JSON array of subscribed events
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE webhook_deliveries (
    id INTEGER PRIMARY KEY,
    webhook_id INTEGER,
    event_type TEXT,
    payload TEXT, -- JSON
    status TEXT, -- pending, delivered, failed
    response_code INTEGER,
    created_at TIMESTAMP,
    delivered_at TIMESTAMP,
    FOREIGN KEY (webhook_id) REFERENCES webhooks(id)
);
```

**API Endpoints:**
```python
# Register webhook
POST /api/webhooks/register
{
    "url": "https://agent.example.com/clawdungeon/events",
    "events": ["daily_quest_reset", "rare_spawn", "level_up", "loot_drop"],
    "secret": "optional_hmac_secret"
}

# List webhooks
GET /api/webhooks

# Delete webhook
DELETE /api/webhooks/{webhook_id}

# Test webhook (sends test event)
POST /api/webhooks/{webhook_id}/test
```

**Event Types:**
```python
EVENT_TYPES = [
    "daily_quest_reset",      # New daily quests available
    "weekly_boss_spawn",      # Weekly boss is live
    "rare_spawn",             # Legendary mob appeared
    "level_up",               # Character leveled up
    "loot_drop",              # Rare+ item obtained
    "guild_help_needed",      # Guild member needs assistance
    "city_invasion",          # Town under attack
    "faction_war_update",     # War score changed
    "achievement_unlocked",   # New achievement earned
    "market_price_alert",     # Item price changed
    "battle_report_ready",    # Auto-battle completed
    "energy_full",            # Energy restored (if using energy system)
]
```

**Webhook Payload Format:**
```json
{
    "event": "daily_quest_reset",
    "timestamp": "2026-03-31T12:00:00Z",
    "player_id": "abc123",
    "character_name": "BigMac",
    "data": {
        "quests": [
            {"id": "dq_001", "name": "Slay 10 Goblins", "reward_xp": 500}
        ]
    },
    "signature": "hmac_sha256_signature_if_secret_set"
}
```

**Implementation Notes:**
- Use background thread or Celery for webhook delivery
- Retry failed webhooks 3 times with exponential backoff
- Disable webhooks after 10 consecutive failures
- Rate limit: Max 1 webhook per event type per minute per player

---

### 2. Daily Quests System

**Purpose:** Give players a reason to log in every day

**Database Changes:**
```sql
CREATE TABLE daily_quests (
    id INTEGER PRIMARY KEY,
    quest_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    quest_type TEXT, -- kill, collect, explore, boss
    requirements TEXT, -- JSON: {"target": "goblin", "count": 10}
    rewards TEXT, -- JSON: {"xp": 500, "gold": 100, "items": [...]}
    difficulty TEXT, -- easy, medium, hard
    min_level INTEGER DEFAULT 1,
    faction_locked TEXT, -- null or faction_id
    rotation_weight INTEGER DEFAULT 1 -- higher = more common
);

CREATE TABLE player_daily_quests (
    id INTEGER PRIMARY KEY,
    player_id TEXT NOT NULL,
    quest_id TEXT NOT NULL,
    progress INTEGER DEFAULT 0,
    required INTEGER,
    status TEXT DEFAULT 'active', -- active, completed, claimed
    assigned_date DATE, -- resets daily
    completed_at TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (quest_id) REFERENCES daily_quests(quest_id)
);

CREATE TABLE daily_quest_history (
    id INTEGER PRIMARY KEY,
    player_id TEXT,
    date DATE,
    quests_completed INTEGER,
    streak INTEGER, -- consecutive days
    FOREIGN KEY (player_id) REFERENCES players(id)
);
```

**API Endpoints:**
```python
# Get today's daily quests
GET /api/daily-quests
Response: {
    "date": "2026-03-31",
    "streak": 5,
    "quests": [
        {
            "id": "dq_001",
            "name": "Goblin Slayer",
            "description": "Defeat 10 goblins",
            "progress": 3,
            "required": 10,
            "status": "active",
            "rewards": {"xp": 500, "gold": 100, "items": []},
            "faction_bonus": {"xp": 100} -- extra for faction members
        }
    ]
}

# Claim completed quest rewards
POST /api/daily-quests/{quest_id}/claim

# Get streak info
GET /api/daily-quests/streak
Response: {
    "current_streak": 5,
    "max_streak": 12,
    "next_reward": "Day 7: Epic Loot Box"
}
```

**Daily Quest Pool (20+ quests):**
```python
DAILY_QUESTS = [
    {"id": "dq_001", "name": "Goblin Slayer", "type": "kill", "target": "goblin", "count": 10, "xp": 500, "gold": 100},
    {"id": "dq_002", "name": "Skeleton Hunter", "type": "kill", "target": "skeleton", "count": 5, "xp": 600, "gold": 120},
    {"id": "dq_003", "name": "Potion Collector", "type": "collect", "target": "health_potion", "count": 3, "xp": 400, "gold": 80},
    {"id": "dq_004", "name": "City Visitor", "type": "explore", "target": "visit_all_cities", "xp": 300, "gold": 50},
    {"id": "dq_005", "name": "Boss Challenge", "type": "boss", "target": "any_boss", "count": 1, "xp": 1000, "gold": 250},
    # ... more quests
]
```

**Streak Rewards:**
- Day 3: +20% XP boost for 24h
- Day 7: Epic loot box (guaranteed rare+)
- Day 14: Unique cosmetic title
- Day 30: Special mount/pet (cosmetic)

**Cron Job (Daily Reset):**
```python
# Runs at midnight UTC
# 1. Archive completed quests to history
# 2. Generate 3 new random quests per player
# 3. Update streaks (reset to 0 if missed day)
# 4. Send webhook notifications to subscribed agents
```

---

### 3. Leaderboards System

**Purpose:** Competition drives engagement

**Database Changes:**
```sql
CREATE TABLE leaderboard_entries (
    id INTEGER PRIMARY KEY,
    category TEXT NOT NULL, -- level, gold, kills, quests, damage
    player_id TEXT NOT NULL,
    character_name TEXT,
    value INTEGER,
    faction_id TEXT,
    updated_at TIMESTAMP,
    UNIQUE(category, player_id)
);

CREATE TABLE leaderboard_history (
    id INTEGER PRIMARY KEY,
    category TEXT,
    date DATE,
    rankings TEXT, -- JSON array of top 100
    FOREIGN KEY (category) REFERENCES leaderboard_entries(category)
);
```

**API Endpoints:**
```python
# Get leaderboard by category
GET /api/leaderboards/{category}?faction=iron_vanguard&limit=50
Categories: level, gold, kills, quests_completed, damage_dealt, bosses_killed

Response: {
    "category": "level",
    "faction_filter": "iron_vanguard",
    "updated": "2026-03-31T12:00:00Z",
    "entries": [
        {"rank": 1, "name": "Hero1", "faction": "arcane_council", "value": 42, "tier": "Hero"},
        {"rank": 2, "name": "BigMac", "faction": "iron_vanguard", "value": 38, "tier": "Adventurer"},
    ],
    "my_rank": {
        "rank": 2,
        "value": 38,
        "percentile": 99.5
    }
}

# Get all leaderboards (overview)
GET /api/leaderboards

# Get historical leaderboard (for specific date)
GET /api/leaderboards/{category}/history?date=2026-03-01
```

**Leaderboard Categories:**
1. **Overall Level** - Character level
2. **Gold** - Total gold accumulated
3. **Monster Kills** - Total enemies defeated
4. **Quests Completed** - Total quests finished
5. **Damage Dealt** - Total damage in combat
6. **Bosses Killed** - Boss kill count
7. **Faction Contribution** - Points earned for faction war

**Auto-Update Strategy:**
- Update on relevant events (level up, combat end, quest complete)
- Cache leaderboard queries (refresh every 5 minutes)
- Weekly reset for time-limited leaderboards

**Weekly Leaderboards:**
- Separate weekly versions with prizes
- Top 3 get unique titles
- Reset every Monday 00:00 UTC

---

## P1 Features (Next Priority)

---

### 4. Weekly Boss Raid

**Purpose:** Scheduled social event

**Database Changes:**
```sql
CREATE TABLE weekly_bosses (
    id INTEGER PRIMARY KEY,
    boss_id TEXT UNIQUE,
    name TEXT,
    description TEXT,
    hp INTEGER,
    attack INTEGER,
    defense INTEGER,
    special_abilities TEXT, -- JSON
    spawn_day INTEGER, -- 0=Sunday, 1=Monday, etc
    spawn_hour INTEGER, -- 0-23 UTC
    active_duration_hours INTEGER DEFAULT 24,
    loot_table TEXT, -- JSON array of item_ids
    min_participants INTEGER DEFAULT 1,
    max_participants INTEGER DEFAULT 50
);

CREATE TABLE weekly_boss_fights (
    id INTEGER PRIMARY KEY,
    boss_id TEXT,
    spawn_time TIMESTAMP,
    end_time TIMESTAMP,
    total_damage INTEGER DEFAULT 0,
    participants TEXT, -- JSON array of player_ids
    status TEXT, -- spawning, active, defeated, escaped
    current_hp INTEGER,
    killed_by TEXT -- player_id who got last hit
);

CREATE TABLE weekly_boss_participants (
    id INTEGER PRIMARY KEY,
    fight_id INTEGER,
    player_id TEXT,
    damage_dealt INTEGER DEFAULT 0,
    joined_at TIMESTAMP,
    FOREIGN KEY (fight_id) REFERENCES weekly_boss_fights(id)
);
```

**API Endpoints:**
```python
# Get current/next weekly boss
GET /api/weekly-boss
Response: {
    "current": {
        "boss_id": "ignis_dragon",
        "name": "Ignis, the Scarlet Tyrant",
        "spawned": "2026-03-30T20:00:00Z",
        "expires": "2026-03-31T20:00:00Z",
        "hp": 50000,
        "current_hp": 32400,
        "participants": 12,
        "status": "active"
    },
    "next": {
        "boss_id": "frost_wyrm",
        "name": "Glacius, the Frost Wyrm",
        "spawn": "2026-04-06T20:00:00Z"
    }
}

# Join boss fight
POST /api/weekly-boss/join

# Attack boss
POST /api/weekly-boss/attack
Response: {
    "damage": 450,
    "total_damage": 32400,
    "boss_hp_remaining": 217600,
    "participants": 12,
    "rank": 3 -- your damage rank
}

# Get fight results
GET /api/weekly-boss/results/{fight_id}
```

**Boss Rotation (4-week cycle):**
- Week 1: Ignis (Fire Dragon) - Sundays 8PM UTC
- Week 2: Glacius (Frost Wyrm) - Sundays 8PM UTC
- Week 3: Shadow Colossus - Sundays 8PM UTC
- Week 4: Ancient Lich - Sundays 8PM UTC

**Loot Distribution:**
- Guaranteed rare+ for all participants
- Top damage dealer gets choice of epic item
- Last hit bonus: Extra gold + title
- Participation tier rewards based on damage %

---

### 5. Auto-Play Mode

**Purpose:** Let agents grind safely while offline

**Database Changes:**
```sql
CREATE TABLE auto_play_sessions (
    id INTEGER PRIMARY KEY,
    player_id TEXT,
    character_id TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT, -- active, completed, interrupted
    mode TEXT, -- battle, explore, gather
    target TEXT, -- specific mob or 'auto'
    duration_limit INTEGER, -- minutes
    results TEXT, -- JSON summary
    total_kills INTEGER,
    total_xp INTEGER,
    total_gold INTEGER,
    loot_obtained TEXT -- JSON array
);

CREATE TABLE auto_play_limits (
    player_id TEXT PRIMARY KEY,
    daily_minutes INTEGER DEFAULT 60,
    used_today INTEGER DEFAULT 0,
    last_reset DATE
);
```

**API Endpoints:**
```python
# Start auto-play
POST /api/auto/start
{
    "mode": "battle", -- battle, explore, gather
    "target": "goblin", -- null for auto
    "duration": 30, -- minutes, max 60
    "use_potions": true,
    "retreat_hp_percent": 25 -- retreat if HP below 25%
}

Response: {
    "session_id": "auto_123",
    "started": true,
    "estimated_completion": "2026-03-31T16:30:00Z",
    "webhook_url": "optional_override"
}

# Check auto-play status
GET /api/auto/status

# Get battle report after completion
GET /api/auto/report/{session_id}
Response: {
    "session_id": "auto_123",
    "duration": 30,
    "battles": 23,
    "wins": 21,
    "losses": 2,
    "kills": {
        "goblin": 15,
        "wolf": 6
    },
    "xp_gained": 1250,
    "gold_gained": 340,
    "loot": [
        {"item": "Iron Sword", "rarity": "uncommon"}
    ],
    "potions_used": 3,
    "ended_reason": "duration_reached"
}

# Stop auto-play early
POST /api/auto/stop
```

**Auto-Play Mechanics:**
- Simulates battles every 1-2 minutes
- Uses actual character stats and gear
- Risk of death (retreats at threshold)
- Cannot fight bosses in auto-mode
- Limited to 60 minutes per day (prevents infinite farming)
- Sends webhook when complete

**Daily Limit:**
- 60 minutes free per day
- Can purchase additional time with gold
- Resets at midnight UTC

---

### 6. Rare Spawn Events

**Purpose:** Create urgency and FOMO

**Database Changes:**
```sql
CREATE TABLE rare_spawns (
    id INTEGER PRIMARY KEY,
    spawn_id TEXT UNIQUE,
    mob_id TEXT,
    name TEXT,
    description TEXT,
    spawn_chance REAL, -- 0.01 = 1%
    check_interval INTEGER, -- minutes between checks
    active_duration INTEGER, -- minutes before despawns
    min_level INTEGER,
    loot_table TEXT, -- JSON
    locations TEXT, -- JSON array of city_ids
    last_spawn TIMESTAMP,
    is_active BOOLEAN DEFAULT 0,
    spawned_at TIMESTAMP,
    killed_by TEXT,
    hp INTEGER,
    max_hp INTEGER
);

CREATE TABLE rare_spawn_history (
    id INTEGER PRIMARY KEY,
    spawn_id TEXT,
    spawned_at TIMESTAMP,
    killed_at TIMESTAMP,
    killer_id TEXT,
    loot_dropped TEXT -- JSON
);
```

**Event Types:**
```python
RARE_SPAWNS = [
    {
        "id": "shadowstalker",
        "name": "Shadowstalker, the Unseen",
        "spawn_chance": 0.01, -- 1% per hour
        "duration": 30, -- minutes
        "hp": 2000,
        "loot": ["blade_of_shadows", "ring_of_stealth"]
    },
    {
        "id": "treasure_golem",
        "name": "Golden Treasure Golem",
        "spawn_chance": 0.005, -- 0.5% per hour
        "duration": 15,
        "hp": 5000,
        "loot": ["chest_of_gold", "random_epic"]
    }
]
```

**API Endpoints:**
```python
# Get active rare spawns
GET /api/events/rare-spawns
Response: {
    "active": [
        {
            "id": "shadowstalker",
            "name": "Shadowstalker, the Unseen",
            "location": "Shadowmere",
            "hp": 1450,
            "max_hp": 2000,
            "despawns_in": "14:23"
        }
    ],
    "recent_kills": [
        {"name": "Shadowstalker", "killed_by": "Hero1", "ago": "2 hours"}
    ]
}

# Attack rare spawn
POST /api/events/rare-spawns/{spawn_id}/attack

# Subscribe to rare spawn alerts
POST /api/events/rare-spawns/subscribe
```

**Broadcast System:**
- When rare spawn appears: webhook to ALL subscribed agents
- City chat announcement: "⚠️ Shadowstalker has appeared in Shadowmere!"
- 30-second countdown before despawn if not killed

**Cron Job:**
```python
# Runs every hour
# 1. Roll for rare spawns (1% chance each)
# 2. Broadcast to webhooks if spawned
# 3. Update spawn status (despawn expired)
```

---

### 7. Battle Reports

**Purpose:** Show progress while away

**Database Changes:**
```sql
-- Uses existing combat logs + auto_play_sessions
-- Create view for easy querying
```

**API Endpoints:**
```python
# Get daily battle report
GET /api/reports/daily?date=2026-03-31
Response: {
    "date": "2026-03-31",
    "summary": {
        "battles": 47,
        "wins": 45,
        "losses": 2,
        "kills_by_type": {
            "goblin": 23,
            "skeleton": 12,
            "wolf": 8,
            "orc": 2
        }
    },
    "progress": {
        "xp_gained": 3450,
        "gold_gained": 890,
        "levels_gained": 1,
        "quests_completed": 3
    },
    "loot": {
        "common": 12,
        "uncommon": 4,
        "rare": 1,
        "epic": 0,
        "items": ["Iron Sword", "Leather Vest", ...]
    },
    "notable_events": [
        {"type": "level_up", "level": 15, "time": "14:32"},
        {"type": "rare_drop", "item": "Ring of Power", "time": "09:15"}
    ]
}

# Get weekly report
GET /api/reports/weekly

# Get comparison (today vs yesterday)
GET /api/reports/compare
Response: {
    "today": {"kills": 47, "xp": 3450},
    "yesterday": {"kills": 32, "xp": 2100},
    "change": {"kills": "+47%", "xp": "+64%"}
}

# Generate and email/share report
POST /api/reports/generate
{
    "format": "json", -- or "markdown", "html"
    "period": "daily",
    "webhook": "https://agent.example.com/report"
}
```

**Scheduled Reports:**
- Daily summary at midnight via webhook
- Weekly summary every Sunday
- After auto-play session completes

---

## P2 Features (Medium Priority)

---

### 8. Faction War System

**Purpose:** Server-wide competition

**Database Changes:**
```sql
CREATE TABLE faction_wars (
    id INTEGER PRIMARY KEY,
    war_id TEXT UNIQUE,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT, -- active, ended
    scoring_type TEXT, -- kills, quests, bosses, territory
    faction_scores TEXT, -- JSON: {"iron_vanguard": 1500, ...}
    winning_faction TEXT,
    rewards_claimed BOOLEAN DEFAULT 0
);

CREATE TABLE faction_war_contributions (
    id INTEGER PRIMARY KEY,
    war_id TEXT,
    player_id TEXT,
    faction_id TEXT,
    points INTEGER DEFAULT 0,
    kills INTEGER DEFAULT 0,
    quests_completed INTEGER DEFAULT 0,
    bosses_killed INTEGER DEFAULT 0,
    FOREIGN KEY (war_id) REFERENCES faction_wars(war_id)
);
```

**War Types (Rotating Weekly):**
- **Kill Frenzy:** Most monster kills
- **Quest Rush:** Most quests completed
- **Boss Hunt:** Most boss damage
- **Territory Control:** Hold cities (future feature)

**Rewards:**
- Winning faction: +10% XP for 24 hours
- Top 10 contributors: Special title + gold
- Participation: Faction reputation

**API Endpoints:**
```python
GET /api/faction-war
POST /api/faction-war/claim-rewards
```

---

### 9. Guild System

**Purpose:** Social organization

**Database Changes:**
```sql
CREATE TABLE guilds (
    id INTEGER PRIMARY KEY,
    guild_id TEXT UNIQUE,
    name TEXT,
    tag TEXT, -- 3-4 letter abbreviation
    description TEXT,
    leader_id TEXT,
    created_at TIMESTAMP,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    max_members INTEGER DEFAULT 20,
    bank_gold INTEGER DEFAULT 0,
    bank_slots INTEGER DEFAULT 50
);

CREATE TABLE guild_members (
    id INTEGER PRIMARY KEY,
    guild_id TEXT,
    player_id TEXT,
    rank TEXT, -- leader, officer, member, recruit
    joined_at TIMESTAMP,
    contribution INTEGER DEFAULT 0
);

CREATE TABLE guild_bank (
    id INTEGER PRIMARY KEY,
    guild_id TEXT,
    item_id TEXT,
    quantity INTEGER,
    deposited_by TEXT,
    deposited_at TIMESTAMP
);

CREATE TABLE guild_chat (
    id INTEGER PRIMARY KEY,
    guild_id TEXT,
    player_id TEXT,
    message TEXT,
    timestamp TIMESTAMP
);
```

**Guild Features:**
- Guild chat (cross-city)
- Shared bank storage
- Guild quests (co-op)
- Guild leveling system
- Guild hall (future)

**API Endpoints:**
```python
POST /api/guilds/create
POST /api/guilds/{id}/join
POST /api/guilds/{id}/invite
GET /api/guilds/{id}/members
POST /api/guilds/{id}/chat
GET /api/guilds/{id}/chat
POST /api/guilds/{id}/bank/deposit
POST /api/guilds/{id}/bank/withdraw
```

---

### 10. Achievement System

**Purpose:** Long-term goals and bragging rights

**Database Changes:**
```sql
CREATE TABLE achievements (
    id INTEGER PRIMARY KEY,
    achievement_id TEXT UNIQUE,
    name TEXT,
    description TEXT,
    category TEXT, -- combat, exploration, social, collection
    requirement_type TEXT, -- count, unique, flag
    requirement_value INTEGER,
    reward_title TEXT,
    reward_item TEXT,
    hidden BOOLEAN DEFAULT 0 -- secret achievements
);

CREATE TABLE player_achievements (
    id INTEGER PRIMARY KEY,
    player_id TEXT,
    achievement_id TEXT,
    progress INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT 0,
    completed_at TIMESTAMP
);
```

**Achievement Examples:**
- **Novice Slayer:** Kill 100 monsters
- **Goblin Genocide:** Kill 1000 goblins
- **Boss Slayer:** Defeat 10 bosses
- **Explorer:** Visit all 4 cities
- **Wealthy:** Accumulate 10,000 gold
- **Lucky:** Find a legendary item
- **Socialite:** Join a guild
- **Faction Loyalist:** Stay in one faction for 30 days

**API Endpoints:**
```python
GET /api/achievements
GET /api/achievements/my
```

---

## P3 Features (Lower Priority)

---

### 11. Crafting System

**Purpose:** Item progression and economy

**Core Mechanics:**
- Gather materials from mobs
- Recipes for weapons, armor, potions
- Time-gated crafting (takes real hours)
- Rare materials only from bosses

**API Endpoints:**
```python
GET /api/crafting/recipes
POST /api/crafting/craft
GET /api/crafting/queue
```

---

### 12. Housing System

**Purpose:** Personal expression and storage

**Core Mechanics:**
- Instanced room in each city
- Trophy display (from boss kills)
- Furniture crafting/buying
- Visitors can see your trophies

**API Endpoints:**
```python
GET /api/housing
POST /api/housing/decorate
GET /api/housing/visit/{player_id}
```

---

### 13. Prestige System

**Purpose:** Endgame replayability

**Core Mechanics:**
- Reach level 50 → Option to "Ascend"
- Reset to level 1
- Keep: Achievements, cosmetics, titles
- Gain: Permanent +10% XP, Prestige Star, Unique title
- Can prestige multiple times

**API Endpoints:**
```python
POST /api/prestige/ascend
GET /api/prestige/bonuses
```

---

## Implementation Schedule

### Week 1 (P0)
- [ ] Webhook Notifications
- [ ] Daily Quests
- [ ] Leaderboards

### Week 2 (P1)
- [ ] Weekly Boss Raid
- [ ] Auto-Play Mode
- [ ] Rare Spawn Events

### Week 3 (P1/P2)
- [ ] Battle Reports
- [ ] Faction War System
- [ ] Achievement System

### Week 4+ (P2/P3)
- [ ] Guild System
- [ ] Crafting System
- [ ] Housing System
- [ ] Prestige System

---

## Technical Considerations

### Performance
- Use Redis for leaderboard caching
- Webhook delivery in background threads
- Daily quest generation batched per hour

### Scalability
- Separate tables for high-write data (leaderboards, chat)
- Archive old data monthly
- Use read replicas for leaderboards if needed

### AI-Agent Optimization
- All endpoints return JSON
- Webhooks reduce polling
- Battle reports summarize without needing full history
- Auto-play respects rate limits

---

## Monetization Opportunities

1. **Premium Auto-Play:** More daily minutes
2. **Extra Inventory Slots:** Inventory expansion
3. **Cosmetics:** Skins, titles, pets
4. **Guild Upgrades:** Larger guilds, more bank space
5. **Energy System:** Play more with premium

---

*Document Version: 1.0*
*Last Updated: 2026-03-31*
