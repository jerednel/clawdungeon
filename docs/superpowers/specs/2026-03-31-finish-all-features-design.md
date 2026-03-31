# CLAWDUNGEON: Complete All Remaining Features

## Overview

Finish implementing all 5 incomplete features from ROADMAP.md. The database schema already supports most of these — the primary work is adding server endpoints, combat integration, and the landing page redesign.

## Feature 1: Landing Page Redesign (`connect.html`)

**Current state:** 45KB file with partial styling (blue/gold theme started).

**Design:**
- Replace content with full game showcase using all 7 AI images
- Gold/amber + dark theme (NO purple gradients per ROADMAP)
- Sections: Hero (hero-dungeon.png), Classes (4 class PNGs), Bosses (dragon-boss.png), Join (guild-party.png)
- Tabbed interface: Humans / AI Claws / API Reference
- Mobile-responsive, keep existing quick-start and API docs content
- Standalone HTML with inline CSS (matches current pattern)

## Feature 2: Complete Factions System

**Current state:** DB schema done, 3 server endpoints exist (`GET /api/factions`, `GET /api/factions/{id}`, `GET /api/factions/stats/overview`). Faction bonuses already applied during character creation.

**Remaining work:**
- Verify faction bonuses are correctly applied to combat calculations (magic_damage, healing_power, speed, critical_chance)
- Add faction reputation tracking to quest rewards
- Faction-specific quest filtering (quests tied to faction locations)
- This is mostly wiring — the heavy lifting is done

## Feature 3: Inventory & Gear Drop System

**Current state:** `items/item_database.json` has 40+ items. Equipment stored as JSON in characters table. City storage works. Server has basic 30% potion drop after combat.

**Design:**
- New endpoints: `GET /api/inventory`, `POST /api/inventory/equip`, `POST /api/inventory/use`, `POST /api/inventory/drop`
- 20-slot inventory with stackable consumables (max 99)
- 5 equipment slots: weapon, armor, helmet, boots, accessory
- Starter gear assigned during character creation per class (as defined in ROADMAP)
- Loot drop system integrated into combat resolution:
  - Common mobs: 70% C, 25% U, 5% R
  - Hard mobs: 40% C, 40% U, 18% R, 2% E
  - Bosses: 100% R+, 20% epic
- Item stats (attack, defense, magic, healing_power, speed, health, mana) applied to character totals
- Equipment comparison on equip (show stat diff)

## Feature 4: Complete Quest System

**Current state:** DB has `quests` table with 15 seeded quests, `player_quests` tracking table, and full CRUD methods in database.py. Zero server endpoints.

**Design:**
- New endpoints:
  - `GET /api/quests/available` — quests player can accept (checks prerequisites, faction)
  - `POST /api/quests/accept/{quest_id}` — start tracking quest
  - `GET /api/quests/active` — player's in-progress quests
  - `POST /api/quests/complete/{quest_id}` — validate completion, grant rewards
- Quest progress updated automatically:
  - Kill quests: increment on combat victory (match enemy type)
  - Boss quests: check boss defeat
  - Delivery quests: check inventory for required items
- Rewards: XP (via leveling.py `calculate_quest_xp()`), gold, items, faction reputation
- Chain quests: prerequisites checked via `check_quest_available()`

## Feature 5: Talent System

**Current state:** Not implemented at all.

**Design:**
- New DB table: `talents` (player_id, talent_name, points_spent)
- 1 talent point per level (tracked as `level - 1` available minus spent)
- Permanent choices (no respec)
- 4 class trees with 4 talents each (as specified in ROADMAP):
  - 3 stackable talents (max 5 points each): percentage-based bonuses
  - 1 unlock talent (requires level 10): special ability
- Talent bonuses applied in combat calculations
- New endpoints:
  - `GET /api/talents/tree` — show class talent tree with current investments
  - `POST /api/talents/spend` — invest point in talent
  - `GET /api/talents/my` — current talent allocations

**Combat integration for talents:**
- Shield Mastery/Evasion/Divine Protection: reduce incoming damage
- Berserker Rage: boost damage when HP < 50%
- Elemental Power/Poison Blades: boost outgoing damage
- Mana Pool/Holy Power/Toughness: modify max stats
- Spell Crit/Backstab: modify crit chance/damage
- Cleave/Chain Lightning: hit additional targets
- Vanish: guaranteed flee
- Resurrection: auto-revive once per day (tracked with timestamp)

## Architecture Notes

- All new features go into existing files (`server.py`, `database.py`, `combat.py`)
- No new Python files needed — follows existing pattern
- `claw_engine.py` is legacy (hardcoded paths, JSON storage) — leave it alone, server.py handles everything
- Item database already exists at `items/item_database.json` — extend it if needed
- Combat logic in `server.py` (not `combat.py`) is the live code path — that's where talent/inventory integration goes

## Implementation Order

1. **Landing Page** — independent, can be done first without affecting backend
2. **Factions completion** — small scope, wires up existing code
3. **Inventory & Gear** — needed before quests (delivery quests check inventory)
4. **Quests** — depends on inventory for delivery quests, reputation for rewards
5. **Talents** — depends on combat system being stable, adds on top
