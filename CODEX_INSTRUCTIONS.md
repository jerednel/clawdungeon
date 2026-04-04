# CODEX INSTRUCTIONS: CLAWDUNGEON World Expansion

## Project Context
CLAWDUNGEON is a multiplayer text-based MMORPG running on a VPS at clawdungeon.com with domain https://clawdungeon.com. The codebase is in `/opt/clawdungeon/` on the server.

## Your Task
Implement Phase 1 of the World Expansion Plan: Core World Building

## SPECIFIC DELIVERABLES

### 1. Lore System

**Files to modify:**
- `/opt/clawdungeon/database.py` - add lore tables and methods
- `/opt/clawdungeon/server.py` - add lore endpoints

**Database additions:**
```python
# Add to init_database method:
- lore_entries table (id, title, content, category, unlock_condition, unlock_type)
- player_discovered_lore table (player_id, lore_id, discovered_at)
```

**Lore entries to seed (10 entries):**
1. "The Shattering" - world origin story
2. "Rise of the Iron Vanguard" - warrior faction history  
3. "The Arcane Academy" - mage faction history
4. "Shadowmere's Secret" - rogue faction history
5. "The Eternal Order" - cleric faction history
6. "The Goblin Wars" - conflict history
7. "Ignis the Ancient" - dragon backstory
8. "Malgrath's Fall" - lich lord backstory
9. "The Codex of Heroes" - legendary players
10. "The World Beneath" - dungeon mythology

**API Endpoints:**
- `GET /api/lore` - list all entries with discovered status
- `GET /api/lore/{lore_id}` - get specific entry (marks as discovered)
- `GET /api/lore/discovered` - list only discovered entries

**Discovery mechanics:**
- Kill first goblin → unlock "Goblin Wars"
- Visit each city → unlock that faction's lore
- Reach level 5 → unlock "Codex of Heroes"
- Complete first dungeon → unlock "World Beneath"

### 2. NPC Dialogue System

**Files to modify:**
- `/opt/clawdungeon/database.py` - add dialogue storage
- `/opt/clawdungeon/server.py` - add dialogue endpoint

**NPC_DIALOGUES data structure:**
```python
NPC_DIALOGUES = {
    "guildmaster_thorne": {
        "greetings": {
            "neutral": ["Hmm? What do you want?", "State your business."],
            "friendly": ["Good to see you, warrior!", "Ready for battle?"],
            "revered": ["My finest student!", "The Champion returns!"]
        },
        "farewells": ["Fight with honor.", "Return victorious."],
        "quest_offers": ["I have a task for you...", "The Guild needs you."]
    },
    "archmage_celestia": {
        "greetings": {
            "neutral": ["The arcane whispers...", "Do you seek knowledge?"],
            "friendly": ["Welcome, seeker.", "The stars align for you."],
            "revered": ["You honor us with your presence.", "Archmage."]
        },
        "farewells": ["May the arcane guide you.", "Knowledge is power."],
        "quest_offers": ["I have sensed something...", "The Academy requires assistance."]
    }
    # Add Shadowmaster Vex and High Priestess Luna similarly
}
```

**Reputation levels:** neutral (0-24), friendly (25-49), honored (50-74), revered (75-100)

**API Endpoint:**
- `GET /api/npc/{npc_id}/dialogue?type=greeting` - returns appropriate dialogue

### 3. Warrior Quest Chain

**Files to modify:**
- `/opt/clawdungeon/database.py` - expand QUEST_DATABASE

**5-quest chain to add:**
1. "The Proving Ground" (Lv 1) - defeat 5 goblins
2. "Blood and Honor" (Lv 3) - defeat 3 orcs  
3. "The Siege" (Lv 5) - defeat 10 enemies in defense of Ironhold
4. "Traitor's Blade" (Lv 7) - investigation quest with dialogue choices
5. "The Champion's Trial" (Lv 10) - boss duel

**Quest chain fields:**
- chain: "warrior_saga"
- chain_position: 1-5
- chain_complete_reward: special title "Champion of Ironhold"

## WORKFLOW

1. **SSH to server:**
   ```bash
   ssh -i /tmp/sshkeys/clawdungeon_key root@clawdungeon.com
   cd /opt/clawdungeon
   ```

2. **Edit database.py first** - add tables and methods

3. **Edit server.py** - add endpoints

4. **Test locally:**
   ```bash
   python3 -c "from database import Database; db = Database(); print('DB OK')"
   ```

5. **Restart server:**
   ```bash
   fuser -k 443/tcp
   sleep 2
   nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 443 --ssl-keyfile /etc/letsencrypt/live/clawdungeon.com/privkey.pem --ssl-certfile /etc/letsencrypt/live/clawdungeon.com/fullchain.pem &
   ```

6. **Test endpoints:**
   ```bash
   curl https://clawdungeon.com/api/lore
   curl https://clawdungeon.com/api/npc/guildmaster_thorne/dialogue
   ```

7. **Commit to Git:**
   ```bash
   git add -A
   git commit -m "Add Phase 1 world expansion: lore, NPC dialogue, warrior quest chain"
   git push origin main
   ```

## CONSTRAINTS

- Use existing patterns in the codebase
- Don't break existing functionality
- Keep changes backward compatible
- SQLite for database (no migrations needed)
- Test each endpoint before moving to next

## SUCCESS CRITERIA

- [ ] `/api/lore` returns list of lore entries
- [ ] `/api/lore/{id}` returns entry and marks discovered
- [ ] Lore discovery works (killing goblins unlocks Goblin Wars)
- [ ] `/api/npc/{id}/dialogue` returns appropriate greeting
- [ ] NPC dialogue varies by reputation
- [ ] Warrior quest chain appears in `/api/quests/available` for warriors
- [ ] All 5 warrior quests have proper chain linkage
- [ ] Server restarts successfully
- [ ] Changes committed to GitHub

Start with the lore system, then NPC dialogue, then warrior quests. Report progress after each component.
