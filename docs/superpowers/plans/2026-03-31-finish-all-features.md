# CLAWDUNGEON: Complete All Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all 5 remaining features from the ROADMAP: Landing Page, Factions completion, Inventory & Gear, Quest System, and Talent System.

**Architecture:** All backend features add endpoints to `server.py` and DB methods to `database.py`. Combat integration modifies the attack endpoint in `server.py`. The landing page is a standalone HTML rewrite of `connect.html`. No new Python files are needed.

**Tech Stack:** Python 3, FastAPI, SQLite, Pydantic, HTML/CSS/JS

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `server.py` | Modify | Add inventory, quest, talent endpoints; update combat loot; update character creation starter gear |
| `database.py` | Modify | Add talents table, inventory helpers, load full item DB from JSON |
| `connect.html` | Rewrite | Landing page with images, tabs, gold/amber theme |
| `items/item_database.json` | Read-only | Already has 40+ items and drop tables |

---

### Task 1: Landing Page Redesign (`connect.html`)

**Files:**
- Rewrite: `connect.html`
- Reference images: `hero-dungeon.png`, `warrior-class.png`, `mage-class.png`, `rogue-class.png`, `cleric-class.png`, `dragon-boss.png`, `guild-party.png`

- [ ] **Step 1: Rewrite `connect.html` with full landing page**

Replace the entire file with a complete landing page that includes:

**Structure:**
- Hero section with `hero-dungeon.png` as background, game title, tagline, CTA buttons
- Classes section with 4 cards using class images (`warrior-class.png`, etc.) showing class name, description, base stats
- Bosses/Dungeons section with `dragon-boss.png`
- Tabbed content area: "For Humans" (quick start CLI guide), "For AI Claws" (API usage), "API Reference" (endpoint list)
- Join/Community section with `guild-party.png`
- Footer

**Styling requirements:**
- Gold/amber (`#d4a853`) + dark blue (`#0d1117`) theme — NO purple gradients
- Use existing CSS variables from current `connect.html` `:root` block
- Responsive: mobile-friendly with CSS grid/flexbox
- Dark fantasy aesthetic: `Cinzel` for headings, `Inter` for body, `Fira Code` for code
- Subtle animations (fade-in on scroll, hover effects on cards)
- All images referenced as relative paths (same directory)

**Tab content:**
- Humans tab: `pip install`, register, create character, fight commands
- AI Claws tab: curl examples for register, create character, start combat, attack
- API Reference tab: table of all endpoints with methods and descriptions

```html
<!-- Key structure (implement fully with all CSS inline in <style>) -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CLAWDUNGEON - Multiplayer Dungeon RPG</title>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Inter:wght@300;400;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <!-- All styles inline in <style> tag -->
</head>
<body>
    <nav><!-- Logo + nav links --></nav>
    <section class="hero"><!-- hero-dungeon.png bg, title, CTA --></section>
    <section class="classes"><!-- 4 class cards with images --></section>
    <section class="bosses"><!-- dragon-boss.png showcase --></section>
    <section class="content-tabs"><!-- 3-tab interface --></section>
    <section class="join"><!-- guild-party.png, call to action --></section>
    <footer><!-- Links, credits --></footer>
    <script><!-- Tab switching JS, scroll animations --></script>
</body>
</html>
```

- [ ] **Step 2: Verify the page renders correctly**

Open in browser or verify HTML structure is valid:
```bash
python3 -c "
from html.parser import HTMLParser
class Validator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
    def handle_starttag(self, tag, attrs): pass
    def handle_endtag(self, tag): pass
v = Validator()
with open('connect.html') as f:
    v.feed(f.read())
print('HTML parsed successfully')
"
```

- [ ] **Step 3: Commit**

```bash
git add connect.html
git commit -m "feat: redesign landing page with game images and tabbed interface"
```

---

### Task 2: Load Full Item Database from JSON

**Files:**
- Modify: `database.py` (around line 51-61, the `ITEM_DATABASE` dict and `get_item_database` method at line 394)

- [ ] **Step 1: Replace static ITEM_DATABASE with JSON loader**

In `database.py`, replace the hardcoded `ITEM_DATABASE` dict (lines 52-61) with a function that loads from `items/item_database.json`:

```python
# Replace lines 52-61 in database.py with:
def _load_item_database() -> Dict:
    """Load item database from JSON file"""
    item_db_path = BASE_PATH / "items" / "item_database.json"
    with open(item_db_path) as f:
        data = json.load(f)
    return data.get("item_database", {})

ITEM_DATABASE = _load_item_database()
```

Also load the drop tables:

```python
def _load_drop_tables() -> Dict:
    """Load drop tables from JSON file"""
    item_db_path = BASE_PATH / "items" / "item_database.json"
    with open(item_db_path) as f:
        data = json.load(f)
    return data.get("drop_tables", {})

DROP_TABLES = _load_drop_tables()
```

- [ ] **Step 2: Verify items load correctly**

```bash
cd /Users/69348/git/clawd && python3 -c "
from database import ITEM_DATABASE, DROP_TABLES
print(f'Items loaded: {len(ITEM_DATABASE)}')
print(f'Drop tables: {list(DROP_TABLES.keys())}')
print(f'Sample item: {ITEM_DATABASE.get(\"steel_blade\", \"NOT FOUND\")}')
"
```
Expected: Items loaded: ~40, drop tables: common_mobs, hard_mobs, bosses

- [ ] **Step 3: Commit**

```bash
git add database.py
git commit -m "feat: load item database from JSON instead of hardcoded dict"
```

---

### Task 3: Inventory & Gear System — Database Methods

**Files:**
- Modify: `database.py` — add helper methods after the existing `get_item_database` method (line ~395)

- [ ] **Step 1: Add inventory helper methods to Database class**

Add these methods to the `Database` class in `database.py` after `get_item_database`:

```python
    def get_inventory_with_details(self, player_id: str) -> Dict:
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
        for slot, item_id in character['equipment'].items():
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
        # Determine which drop table to use
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
            if item.get('rarity') == selected_rarity
            and not item_id.startswith('starter_')
            and item.get('type') in ('weapon', 'armor', 'consumable')
        ]

        if not candidates:
            return None

        return random.choice(candidates)
```

Note: Add `import random` to database.py imports at the top if not already there.

- [ ] **Step 2: Verify methods work**

```bash
cd /Users/69348/git/clawd && python3 -c "
from database import Database
db = Database()
db.init()
# Test loot drop (just verify it doesn't crash)
for _ in range(10):
    drop = db.get_loot_drop('goblin')
    if drop:
        print(f'Drop: {drop}')
print('Loot system working')
db.close()
"
```

- [ ] **Step 3: Commit**

```bash
git add database.py
git commit -m "feat: add inventory helpers and loot drop system to database"
```

---

### Task 4: Inventory & Gear System — Server Endpoints

**Files:**
- Modify: `server.py` — add Pydantic models and 4 new endpoints, update character creation and combat victory

- [ ] **Step 1: Add Pydantic models for inventory**

Add after the existing `NoticeBoardCreateRequest` model (around line 74):

```python
class EquipRequest(BaseModel):
    item_id: str
    slot: str = Field(..., pattern="^(weapon|armor|helmet|boots|accessory)$")

class UseItemRequest(BaseModel):
    item_id: str

class DropItemRequest(BaseModel):
    item_id: str
```

- [ ] **Step 2: Add inventory endpoints**

Add these endpoints after the city storage endpoint (before `if __name__`):

```python
# ============================================
# INVENTORY ENDPOINTS
# ============================================

@app.get("/api/inventory")
async def get_inventory(player_id: str = Depends(get_current_player)):
    """Get player's inventory and equipment"""
    result = db.get_inventory_with_details(player_id)
    if not result:
        raise HTTPException(status_code=404, detail="No active character")
    return result

@app.post("/api/inventory/equip")
async def equip_item(
    request: EquipRequest,
    player_id: str = Depends(get_current_player)
):
    """Equip an item from inventory"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    if request.item_id not in character['inventory']:
        raise HTTPException(status_code=400, detail="Item not in inventory")

    item_db = db.get_item_database()
    item = item_db.get(request.item_id)
    if not item:
        raise HTTPException(status_code=400, detail="Unknown item")

    if item['type'] not in ('weapon', 'armor'):
        raise HTTPException(status_code=400, detail="Item cannot be equipped")

    # Determine slot
    if item['type'] == 'weapon':
        slot = 'weapon'
    else:
        slot = item.get('slot', 'armor')

    if slot != request.slot:
        raise HTTPException(status_code=400, detail=f"Item goes in '{slot}' slot, not '{request.slot}'")

    # Ensure equipment has all slots
    for s in ('weapon', 'armor', 'helmet', 'boots', 'accessory'):
        if s not in character['equipment']:
            character['equipment'][s] = None

    # Unequip current item in that slot (put back in inventory)
    old_item = character['equipment'].get(slot)
    if old_item:
        character['inventory'].append(old_item)

    # Equip new item
    character['inventory'].remove(request.item_id)
    character['equipment'][slot] = request.item_id

    db.update_character(player_id, character)

    old_name = item_db.get(old_item, {}).get('name', 'Nothing') if old_item else 'Nothing'
    return {
        "message": f"Equipped {item['name']} in {slot} slot",
        "unequipped": old_name,
        "equipped": item['name'],
        "slot": slot
    }

@app.post("/api/inventory/use")
async def use_item(
    request: UseItemRequest,
    player_id: str = Depends(get_current_player)
):
    """Use a consumable item"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    if request.item_id not in character['inventory']:
        raise HTTPException(status_code=400, detail="Item not in inventory")

    item_db = db.get_item_database()
    item = item_db.get(request.item_id)
    if not item:
        raise HTTPException(status_code=400, detail="Unknown item")

    if item.get('type') != 'consumable':
        raise HTTPException(status_code=400, detail="Item is not consumable")

    # Apply effect
    effect = item.get('effect')
    amount = item.get('amount', 0)
    result_msg = ""

    if effect == 'heal':
        old_hp = character['health']
        character['health'] = min(character['max_health'], character['health'] + amount)
        healed = character['health'] - old_hp
        result_msg = f"Restored {healed} HP ({character['health']}/{character['max_health']})"
    elif effect == 'restore_mana':
        old_mp = character['mana']
        character['mana'] = min(character['max_mana'], character['mana'] + amount)
        restored = character['mana'] - old_mp
        result_msg = f"Restored {restored} MP ({character['mana']}/{character['max_mana']})"
    else:
        result_msg = f"Used {item['name']}"

    # Remove from inventory
    character['inventory'].remove(request.item_id)
    db.update_character(player_id, character)

    return {
        "message": result_msg,
        "item_used": item['name'],
        "effect": effect,
        "amount": amount
    }

@app.post("/api/inventory/drop")
async def drop_item(
    request: DropItemRequest,
    player_id: str = Depends(get_current_player)
):
    """Drop an item from inventory"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    if request.item_id not in character['inventory']:
        raise HTTPException(status_code=400, detail="Item not in inventory")

    item_db = db.get_item_database()
    item_name = item_db.get(request.item_id, {}).get('name', request.item_id)

    character['inventory'].remove(request.item_id)
    db.update_character(player_id, character)

    return {
        "message": f"Dropped {item_name}",
        "item_dropped": item_name,
        "inventory_count": len(character['inventory'])
    }
```

- [ ] **Step 3: Update character creation to give class-specific starter gear**

In the `create_character` endpoint (around line 220 where `inventory` is set), replace the generic starter inventory:

```python
    # Replace the inventory line with class-specific starter gear
    starter_inventory = {
        'warrior': ['health_potion', 'health_potion', 'health_potion'],
        'mage': ['mana_potion', 'mana_potion', 'mana_potion'],
        'rogue': ['health_potion', 'poison_potion'],
        'cleric': ['health_potion', 'health_potion', 'health_potion', 'health_potion', 'health_potion']
    }

    # Ensure equipment has all 5 slots
    equipment = {
        'weapon': faction_equip.get('weapon'),
        'armor': faction_equip.get('armor'),
        'helmet': None,
        'boots': None,
        'accessory': None
    }
```

And update the `character` dict to use `starter_inventory.get(request.class_type, ['health_potion', 'health_potion'])` for inventory.

- [ ] **Step 4: Update combat victory loot to use drop tables**

In the `combat_attack` endpoint (around line 590 where loot is generated), replace the simple 30% potion drop:

```python
        # Replace the simple loot logic with proper drop system
        loot = []
        for e in state['enemies']:
            drop = db.get_loot_drop(e['type'])
            if drop:
                loot.append(drop)
```

- [ ] **Step 5: Update character status to show all 5 equipment slots**

In `get_character_status` endpoint (around line 274), update equipment calculation to include all slots:

```python
    # Calculate totals with all equipment slots
    item_db = db.get_item_database()
    total_attack = character['attack']
    total_defense = character['defense']
    total_speed = character['speed']
    total_health_bonus = 0
    total_mana_bonus = 0

    equipment_display = {}
    for slot in ('weapon', 'armor', 'helmet', 'boots', 'accessory'):
        item_id = character['equipment'].get(slot)
        if item_id:
            item = item_db.get(item_id, {})
            total_attack += item.get('attack', 0)
            total_defense += item.get('defense', 0)
            total_speed += item.get('speed', 0)
            total_health_bonus += item.get('health', 0)
            total_mana_bonus += item.get('mana', 0)
            equipment_display[slot] = item.get('name', item_id)
        else:
            equipment_display[slot] = 'None'
```

And update the response to use `equipment_display` and `total_speed`.

- [ ] **Step 6: Update combat attack to use all equipment stats**

In `combat_attack` (around line 556), update attack power calculation:

```python
    # Calculate attack with all equipment bonuses
    item_db = db.get_item_database()
    attack_power = character['attack']
    defense_power = character['defense']
    for slot in ('weapon', 'armor', 'helmet', 'boots', 'accessory'):
        item_id = character['equipment'].get(slot)
        if item_id:
            item = item_db.get(item_id, {})
            attack_power += item.get('attack', 0)
            defense_power += item.get('defense', 0)
```

And use `defense_power` for enemy damage calculation instead of just armor.

- [ ] **Step 7: Verify server starts and endpoints work**

```bash
cd /Users/69348/git/clawd && python3 -c "
from server import app
from fastapi.testclient import TestClient
client = TestClient(app)
r = client.get('/api/health')
print(r.json())
print('Server starts OK')
"
```

- [ ] **Step 8: Commit**

```bash
git add server.py
git commit -m "feat: add inventory/equip/use/drop endpoints and proper loot drops"
```

---

### Task 5: Quest System — Server Endpoints

**Files:**
- Modify: `server.py` — add 4 quest endpoints

- [ ] **Step 1: Add quest endpoints**

Add after the inventory endpoints section (before `if __name__`):

```python
# ============================================
# QUEST ENDPOINTS
# ============================================

@app.get("/api/quests/available")
async def get_available_quests(player_id: str = Depends(get_current_player)):
    """Get quests available to the player"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    all_quests = db.get_all_quests()
    available = []

    for quest in all_quests:
        is_available, reason = db.check_quest_available(player_id, quest, character)
        if is_available:
            available.append({
                "id": quest['id'],
                "title": quest['title'],
                "description": quest['description'],
                "type": quest['type'],
                "requirements": quest['requirements'],
                "rewards": quest['rewards'],
                "giver": quest['giver'],
                "location": quest['location'],
                "chain": quest['chain']
            })

    return {"available_quests": available, "count": len(available)}

@app.post("/api/quests/accept/{quest_id}")
async def accept_quest(
    quest_id: str,
    player_id: str = Depends(get_current_player)
):
    """Accept a quest"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    quest = db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    is_available, reason = db.check_quest_available(player_id, quest, character)
    if not is_available:
        raise HTTPException(status_code=400, detail=reason)

    success = db.accept_quest(player_id, quest_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not accept quest")

    return {
        "message": f"Quest accepted: {quest['title']}",
        "quest": {
            "id": quest['id'],
            "title": quest['title'],
            "description": quest['description'],
            "type": quest['type'],
            "requirements": quest['requirements'],
            "rewards": quest['rewards'],
            "giver": quest['giver']
        }
    }

@app.get("/api/quests/active")
async def get_active_quests(player_id: str = Depends(get_current_player)):
    """Get player's active quests with progress"""
    active = db.get_player_active_quests(player_id)

    return {
        "active_quests": [
            {
                "quest_id": q['quest_id'],
                "title": q['title'],
                "description": q['description'],
                "type": q['type'],
                "requirements": q['requirements'],
                "progress": q['progress'],
                "rewards": q['rewards'],
                "giver": q['giver'],
                "accepted_at": q['accepted_at']
            }
            for q in active
        ],
        "count": len(active)
    }

@app.post("/api/quests/complete/{quest_id}")
async def complete_quest(
    quest_id: str,
    player_id: str = Depends(get_current_player)
):
    """Complete a quest and claim rewards"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    quest = db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # Check quest is active for player
    active_quests = db.get_player_active_quests(player_id)
    player_quest = None
    for q in active_quests:
        if q['quest_id'] == quest_id:
            player_quest = q
            break

    if not player_quest:
        raise HTTPException(status_code=400, detail="Quest is not active")

    # Validate completion based on quest type
    requirements = quest['requirements']
    progress = player_quest['progress']

    if quest['type'] == 'kill':
        needed = requirements.get('count', 1)
        current = progress.get('kills', 0)
        if current < needed:
            raise HTTPException(
                status_code=400,
                detail=f"Kill requirement not met: {current}/{needed}"
            )

    elif quest['type'] == 'delivery':
        required_items = requirements.get('items', {})
        for item_id, count in required_items.items():
            have = character['inventory'].count(item_id)
            if have < count:
                item_db = db.get_item_database()
                item_name = item_db.get(item_id, {}).get('name', item_id)
                raise HTTPException(
                    status_code=400,
                    detail=f"Need {count} {item_name}, have {have}"
                )
        # Remove delivered items
        for item_id, count in required_items.items():
            for _ in range(count):
                character['inventory'].remove(item_id)

    elif quest['type'] == 'boss':
        if progress.get('kills', 0) < 1:
            raise HTTPException(status_code=400, detail="Boss not yet defeated")

    # Grant rewards
    rewards = quest['rewards']
    reward_summary = []

    if rewards.get('xp', 0) > 0:
        level_result = add_experience(character, rewards['xp'], source=f"quest: {quest['title']}")
        reward_summary.append(f"+{rewards['xp']} XP")

    if rewards.get('gold', 0) > 0:
        character['gold'] += rewards['gold']
        reward_summary.append(f"+{rewards['gold']} gold")

    if rewards.get('items'):
        for item_id in rewards['items']:
            if len(character['inventory']) < 20:
                character['inventory'].append(item_id)
                item_db = db.get_item_database()
                item_name = item_db.get(item_id, {}).get('name', item_id)
                reward_summary.append(f"+{item_name}")

    # Grant reputation
    if rewards.get('reputation'):
        for faction, amount in rewards['reputation'].items():
            db.modify_reputation(player_id, faction, amount)
            reward_summary.append(f"+{amount} {faction} reputation")

    # Mark quest complete and save character
    db.complete_quest(player_id, quest_id)
    db.update_character(player_id, character)

    response = {
        "message": f"Quest completed: {quest['title']}!",
        "rewards": reward_summary,
        "quest": quest['title']
    }

    # Add level-up info if applicable
    if rewards.get('xp', 0) > 0 and level_result.leveled_up:
        response["level_up"] = {
            "new_level": level_result.new_level,
            "stat_increases": level_result.stat_increases,
            "messages": level_result.messages
        }

    return response
```

- [ ] **Step 2: Add quest progress tracking to combat victory**

In `combat_attack` endpoint, after awarding XP and loot on victory (around line 598), add quest progress update:

```python
        # Update kill quest progress
        active_quests = db.get_player_active_quests(player_id)
        for quest in active_quests:
            if quest['type'] == 'kill':
                reqs = quest['requirements']
                progress = quest['progress']
                # Check if quest tracks specific enemy type or total kills
                if 'enemy_type' in reqs:
                    killed_count = sum(
                        1 for e in state['enemies']
                        if e['health'] <= 0 and e['type'] == reqs['enemy_type']
                    )
                    if killed_count > 0:
                        progress['kills'] = progress.get('kills', 0) + killed_count
                        db.update_quest_progress(player_id, quest['quest_id'], progress)
                elif 'total_kills' in reqs:
                    total_killed = sum(1 for e in state['enemies'] if e['health'] <= 0)
                    progress['kills'] = progress.get('kills', 0) + total_killed
                    db.update_quest_progress(player_id, quest['quest_id'], progress)
```

- [ ] **Step 3: Verify quest endpoints**

```bash
cd /Users/69348/git/clawd && python3 -c "
from server import app
from fastapi.testclient import TestClient
client = TestClient(app)

# Register and create character
r = client.post('/api/auth/register', json={'username': 'questtest', 'password': 'testpass123'})
api_key = r.json()['api_key']
headers = {'Authorization': f'Bearer {api_key}'}

r = client.post('/api/character/create', json={'name': 'QuestHero', 'class_type': 'warrior', 'faction': 'iron_vanguard'}, headers=headers)
print('Character:', r.json()['message'])

r = client.get('/api/quests/available', headers=headers)
print(f'Available quests: {r.json()[\"count\"]}')
for q in r.json()['available_quests'][:3]:
    print(f'  - {q[\"title\"]} ({q[\"type\"]})')

# Accept a quest
r = client.post('/api/quests/accept/tutorial_first_battle', headers=headers)
print(f'Accept: {r.json()[\"message\"]}')

r = client.get('/api/quests/active', headers=headers)
print(f'Active quests: {r.json()[\"count\"]}')
print('Quest system working!')
"
```

- [ ] **Step 4: Commit**

```bash
git add server.py
git commit -m "feat: add quest accept/complete/track endpoints with combat integration"
```

---

### Task 6: Talent System — Database

**Files:**
- Modify: `database.py` — add talents table and methods

- [ ] **Step 1: Add talents table creation**

In `_create_tables` method (after the reputation table creation, around line 266), add:

```python
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
```

- [ ] **Step 2: Add talent tree definitions and database methods**

Add after the `check_quest_available` method at the end of the Database class:

```python
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

        # Get current investments
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

    def spend_talent_point(self, player_id: str, talent_name: str) -> tuple[bool, str]:
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

        # Check available points
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(points_spent), 0) FROM talents WHERE player_id = ?",
            (player_id,)
        )
        total_spent = cursor.fetchone()[0]
        available = max(0, character['level'] - 1 - total_spent)

        if available <= 0:
            return False, "No talent points available"

        # Check max points for this talent
        cursor.execute(
            "SELECT COALESCE(points_spent, 0) FROM talents WHERE player_id = ? AND talent_name = ?",
            (player_id, talent_name)
        )
        row = cursor.fetchone()
        current = row[0] if row else 0

        if current >= talent_def['max_points']:
            return False, f"Talent already at max ({talent_def['max_points']} points)"

        # Spend the point
        cursor.execute("""
            INSERT INTO talents (player_id, talent_name, points_spent)
            VALUES (?, ?, 1)
            ON CONFLICT(player_id, talent_name) DO UPDATE SET points_spent = points_spent + 1
        """, (player_id, talent_name))
        self.conn.commit()

        return True, f"Invested in {talent_def['name']} ({current + 1}/{talent_def['max_points']})"

    def get_player_talents(self, player_id: str) -> Dict[str, int]:
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
```

- [ ] **Step 3: Verify talent DB**

```bash
cd /Users/69348/git/clawd && python3 -c "
from database import Database
db = Database()
db.init()
print(f'Talent trees defined for: {list(db.TALENT_TREES.keys())}')
print(f'Warrior talents: {list(db.TALENT_TREES[\"warrior\"].keys())}')
db.close()
print('Talent system DB ready')
"
```

- [ ] **Step 4: Commit**

```bash
git add database.py
git commit -m "feat: add talent system database table, trees, and methods"
```

---

### Task 7: Talent System — Server Endpoints and Combat Integration

**Files:**
- Modify: `server.py` — add 3 talent endpoints, integrate bonuses into combat

- [ ] **Step 1: Add Pydantic model for talent spending**

Add with the other Pydantic models:

```python
class SpendTalentRequest(BaseModel):
    talent_name: str
```

- [ ] **Step 2: Add talent endpoints**

Add after quest endpoints (before `if __name__`):

```python
# ============================================
# TALENT ENDPOINTS
# ============================================

@app.get("/api/talents/tree")
async def get_talent_tree(player_id: str = Depends(get_current_player)):
    """Get your class talent tree with current investments"""
    tree = db.get_talent_tree(player_id)
    if not tree:
        raise HTTPException(status_code=404, detail="No active character")
    return tree

@app.post("/api/talents/spend")
async def spend_talent_point(
    request: SpendTalentRequest,
    player_id: str = Depends(get_current_player)
):
    """Spend a talent point"""
    success, message = db.spend_talent_point(player_id, request.talent_name)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Return updated tree
    tree = db.get_talent_tree(player_id)
    return {"message": message, "talent_tree": tree}

@app.get("/api/talents/my")
async def get_my_talents(player_id: str = Depends(get_current_player)):
    """Get your current talent allocations and bonuses"""
    character = db.get_active_character(player_id)
    if not character:
        raise HTTPException(status_code=404, detail="No active character")

    talents = db.get_player_talents(player_id)
    bonuses = db.get_talent_bonuses(player_id)

    return {
        "talents": talents,
        "bonuses": bonuses,
        "available_points": max(0, character['level'] - 1 - sum(talents.values()))
    }
```

- [ ] **Step 3: Integrate talent bonuses into combat attack**

In the `combat_attack` endpoint, after calculating `attack_power` and `defense_power` from equipment, add talent bonus application:

```python
    # Apply talent bonuses
    talent_bonuses = db.get_talent_bonuses(player_id)

    # Damage bonuses (poison_blades for rogue, elemental_power for mage)
    damage_multiplier = 1.0 + talent_bonuses.get('damage_percent', 0) + talent_bonuses.get('magic_damage_percent', 0)

    # Berserker rage (warrior) - bonus damage when HP < 50%
    if state['player_health'] < character['max_health'] * 0.5:
        damage_multiplier += talent_bonuses.get('low_hp_damage_percent', 0)

    # Crit chance from talents
    crit_chance = character.get('critical_chance', 0.15) + talent_bonuses.get('critical_chance', 0)
    crit = random.random() < crit_chance

    # Crit damage bonus (backstab for rogue)
    crit_multiplier = 1.5 + talent_bonuses.get('crit_damage_percent', 0)

    base_damage = max(1, attack_power - enemy['defense'])
    variance = random.uniform(0.8, 1.2)
    damage = int(base_damage * variance * damage_multiplier * (crit_multiplier if crit else 1))
```

For enemy damage to player, add dodge and damage reduction:

```python
            # Dodge check (rogue evasion talent)
            if random.random() < talent_bonuses.get('dodge_chance', 0):
                state['log'].append(f"You dodged {e['name']}'s attack!")
                continue

            # Damage reduction (cleric divine protection)
            reduction = 1.0 - talent_bonuses.get('damage_reduction', 0)
            enemy_damage = max(1, int((e['attack'] - defense_power) * random.uniform(0.8, 1.2) * reduction))
```

For cleave/chain lightning (hit additional targets on attack):

```python
    # Cleave / Chain Lightning - hit additional enemy after primary target
    if talent_bonuses.get('cleave') or talent_bonuses.get('chain_attack'):
        for i, extra_enemy in enumerate(state['enemies']):
            if extra_enemy['health'] > 0 and i != request.target:
                splash_damage = damage // 2
                extra_enemy['health'] -= splash_damage
                state['log'].append(f"{'Cleave' if talent_bonuses.get('cleave') else 'Chain Lightning'} hits {extra_enemy['name']}! (-{splash_damage} HP)")
                if extra_enemy['health'] <= 0:
                    state['log'].append(f"{extra_enemy['name']} defeated!")
                break  # Only hit one additional target
```

- [ ] **Step 4: Add vanish talent to flee endpoint**

In `combat_flee`, check for vanish talent:

```python
    # Check for vanish talent (guaranteed flee)
    talent_bonuses = db.get_talent_bonuses(player_id)
    flee_chance = 0.6
    if talent_bonuses.get('vanish'):
        flee_chance = 1.0  # Guaranteed escape with vanish talent
```

- [ ] **Step 5: Verify full server works**

```bash
cd /Users/69348/git/clawd && python3 -c "
from server import app
from fastapi.testclient import TestClient
client = TestClient(app)

# Register and create character
r = client.post('/api/auth/register', json={'username': 'talenttest', 'password': 'testpass123'})
api_key = r.json()['api_key']
headers = {'Authorization': f'Bearer {api_key}'}

r = client.post('/api/character/create', json={'name': 'TalentHero', 'class_type': 'warrior', 'faction': 'iron_vanguard'}, headers=headers)
print('Character created')

# Check talent tree
r = client.get('/api/talents/tree', headers=headers)
data = r.json()
print(f'Class: {data[\"class\"]}, Available points: {data[\"available_points\"]}')
print(f'Talents: {list(data[\"talents\"].keys())}')

# Check inventory
r = client.get('/api/inventory', headers=headers)
print(f'Inventory slots: {r.json()[\"inventory_count\"]}/{r.json()[\"max_slots\"]}')
print(f'Equipment: {list(r.json()[\"equipment\"].keys())}')

# Check quests
r = client.get('/api/quests/available', headers=headers)
print(f'Available quests: {r.json()[\"count\"]}')

print('All systems operational!')
"
```

- [ ] **Step 6: Commit**

```bash
git add server.py
git commit -m "feat: add talent endpoints and integrate talent bonuses into combat"
```

---

### Task 8: Final Integration and Cleanup

**Files:**
- Modify: `server.py` — serve landing page via FastAPI static files

- [ ] **Step 1: Add static file serving for the landing page**

Near the top of `server.py`, after the FastAPI app creation, add:

```python
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Serve static files (images)
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def serve_landing():
    return FileResponse("connect.html")
```

- [ ] **Step 2: Run full integration test**

```bash
cd /Users/69348/git/clawd && python3 -c "
from server import app
from fastapi.testclient import TestClient
client = TestClient(app)

# Test landing page
r = client.get('/')
assert r.status_code == 200
print('Landing page: OK')

# Test health
r = client.get('/api/health')
assert r.status_code == 200
print('Health check: OK')

# Full gameplay flow
r = client.post('/api/auth/register', json={'username': 'finaltest', 'password': 'testpass123'})
api_key = r.json()['api_key']
h = {'Authorization': f'Bearer {api_key}'}

r = client.post('/api/character/create', json={'name': 'FinalHero', 'class_type': 'rogue', 'faction': 'shadow_syndicate'}, h)
assert r.status_code == 200
print('Character created: OK')

r = client.get('/api/character/status', headers=h)
assert r.status_code == 200
print('Status: OK')

r = client.get('/api/inventory', headers=h)
assert r.status_code == 200
assert r.json()['max_slots'] == 20
print(f'Inventory: OK ({r.json()[\"inventory_count\"]} items)')

r = client.get('/api/quests/available', headers=h)
assert r.status_code == 200
print(f'Quests: OK ({r.json()[\"count\"]} available)')

r = client.get('/api/talents/tree', headers=h)
assert r.status_code == 200
assert 'poison_blades' in r.json()['talents']
print(f'Talents: OK ({r.json()[\"available_points\"]} points)')

r = client.get('/api/factions', headers=h)
assert r.status_code == 200
assert len(r.json()['factions']) == 4
print('Factions: OK')

r = client.get('/api/cities', headers=h)
assert r.status_code == 200
print('Cities: OK')

# Combat flow
r = client.post('/api/combat/start?enemies=goblin&enemies=goblin', headers=h)
assert r.status_code == 200
print('Combat started: OK')

r = client.post('/api/combat/attack', json={'target': 0}, headers=h)
assert r.status_code == 200
print('Attack: OK')

print()
print('=== ALL SYSTEMS OPERATIONAL ===')
"
```

- [ ] **Step 3: Commit all remaining changes**

```bash
git add -A
git commit -m "feat: add static file serving and complete all 5 CLAWDUNGEON features

Implemented: landing page redesign, factions completion, inventory/gear system,
quest system with tracking, and talent trees with combat integration."
```

---

## Summary of All New Endpoints

| Method | Endpoint | Feature |
|--------|----------|---------|
| GET | `/api/inventory` | Inventory |
| POST | `/api/inventory/equip` | Inventory |
| POST | `/api/inventory/use` | Inventory |
| POST | `/api/inventory/drop` | Inventory |
| GET | `/api/quests/available` | Quests |
| POST | `/api/quests/accept/{quest_id}` | Quests |
| GET | `/api/quests/active` | Quests |
| POST | `/api/quests/complete/{quest_id}` | Quests |
| GET | `/api/talents/tree` | Talents |
| POST | `/api/talents/spend` | Talents |
| GET | `/api/talents/my` | Talents |
| GET | `/` | Landing Page |
