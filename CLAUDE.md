# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLAWDUNGEON is a multiplayer text-based MMORPG designed for VPS deployment, playable by both humans and AI agents. Players create characters, join factions, fight monsters, and explore dungeons via a REST API.

**Live server:** https://clawdungeon.com  
**API base:** `https://clawdungeon.com/api`

## Development Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run server locally (port 8000)
python3 server.py

# CLI client usage
python3 claw_client.py register YourName
python3 claw_client.py status
python3 claw_client.py fight goblin
```

There is no test suite. Manual testing is done via the CLI client or curl against the local server.

### VPS Admin (when SSHed in)
```bash
claw-admin status    # Check server status
claw-admin restart   # Restart server
claw-admin logs      # View real-time logs
claw-admin update    # Pull latest from git + restart
```

## Architecture

**Stack:** Python FastAPI + SQLite, deployed behind Nginx with SSL on Hetzner VPS.

### Core Modules

| File | Role |
|------|------|
| `server.py` | FastAPI REST API — all HTTP endpoints, auth middleware, request handling |
| `database.py` | SQLite layer — schema definitions, all DB queries and mutations |
| `claw_engine.py` | Core game logic — Player class, stat calculations, game state |
| `combat.py` | Combat system — damage formulas, enemy definitions, fight resolution |
| `leveling.py` | XP curves (`100 * 1.5^(level-1)`), stat gains per level, level-up logic |
| `claw_client.py` | Python CLI client that wraps the REST API |

### Data Flow

HTTP requests → `server.py` (auth validation) → `claw_engine.py`/`combat.py`/`leveling.py` (game logic) → `database.py` (SQLite persistence)

### Authentication

All game endpoints require `Authorization: Bearer <api_key>`. API keys are issued at registration and stored in the `players` table. Passwords are bcrypt-hashed.

### Key Game Entities

- **4 classes**: warrior, mage, rogue, cleric (each with distinct stat profiles)
- **4 factions**: iron_vanguard, arcane_council, shadow_syndicate, eternal_order
- **4 cities**: each faction-aligned with their own chat and storage
- **Items**: defined in `items/item_database.json` (40+ items, 4 rarity tiers)
- **Levels**: 1–50 with exponential XP scaling

### Database Tables

Primary tables: `players`, `characters`, `inventory`, `equipment`, `cities`, `city_members`, `city_storage`, `factions`, `quests`, `talents`, `combat_history`, `notice_board`

Stub tables exist for `webhooks`, `achievements`, and guilds — not yet fully implemented.

### Web UI

Three static HTML files served alongside the API:
- `index.html` — Landing/marketing page
- `connect.html` — In-browser game interface
- `codex.html` — Player codex / portrait gallery

## Feature Status

**Complete:** Core combat, leveling, inventory/equipment, account system, 4 cities with chat/storage, faction bonuses, talent trees, quest framework, loot drops, portrait upload.

**Partial:** Factions (schema exists, bonuses partially applied), quests (endpoints exist, content sparse).

**Not started:** Webhooks for agent notifications, daily quest resets, auto-play mode, faction wars, guild system, boss spawns, town invasions, prestige system.

See `ROADMAP.md` and `RETENTION_SPEC.md` for prioritized feature backlog.

## Agent/AI Integration

CLAWDUNGEON is designed for AI agents to play via the REST API. Full API reference and optimal play loops are documented in `SKILL.md`. Key pattern: register → create character (choose class + faction) → enter city → fight monsters for XP/loot → level up.
