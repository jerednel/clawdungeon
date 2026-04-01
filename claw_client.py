#!/usr/bin/env python3
"""
CLAWDUNGEON - CLI Client
Connect to VPS-hosted game server
"""
import os
import sys
import json
import getpass
from pathlib import Path
import requests
from typing import Optional

# Config
CONFIG_DIR = Path.home() / ".clawdungeon"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_SERVER = "http://localhost:8000"  # Change to your VPS IP/domain
DEFAULT_FACTIONS = {
    'warrior': 'iron_vanguard',
    'mage': 'arcane_council',
    'rogue': 'shadow_syndicate',
    'cleric': 'eternal_order',
}

class ClawDungeonClient:
    def __init__(self, server_url: str = None):
        self.server_url = server_url or self._load_config().get('server', DEFAULT_SERVER)
        self.api_key = self._load_config().get('api_key')
    
    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                return json.load(f)
        return {}
    
    def _save_config(self, config: dict):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        url = f"{self.server_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to server at {self.server_url}")
            print("   Is the server running? Check the URL.")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
                return {"error": error_data.get('detail', str(e))}
            except:
                return {"error": str(e)}
    
    def register(self, username: str, password: str):
        """Register a new account"""
        result = self._request('POST', '/api/auth/register', {
            'username': username,
            'password': password
        })
        
        if 'error' in result:
            print(f"❌ Registration failed: {result['error']}")
            return False
        
        # Save API key
        config = self._load_config()
        config['api_key'] = result['api_key']
        config['server'] = self.server_url
        self._save_config(config)
        self.api_key = result['api_key']
        
        print(f"✅ Registration successful!")
        print(f"   API Key saved to {CONFIG_FILE}")
        print(f"   Player ID: {result['player_id']}")
        return True
    
    def login(self, username: str, password: str):
        """Login to existing account"""
        result = self._request('POST', '/api/auth/login', {
            'username': username,
            'password': password
        })
        
        if 'error' in result:
            print(f"❌ Login failed: {result['error']}")
            return False
        
        # Save API key
        config = self._load_config()
        config['api_key'] = result['api_key']
        config['server'] = self.server_url
        self._save_config(config)
        self.api_key = result['api_key']
        
        print(f"✅ Login successful!")
        print(f"   Welcome back, {result['username']}!")
        return True
    
    def create_character(self, name: str, class_type: str, faction: Optional[str] = None):
        """Create a character"""
        faction = faction or DEFAULT_FACTIONS.get(class_type)
        result = self._request('POST', '/api/character/create', {
            'name': name,
            'class_type': class_type,
            'faction': faction
        })
        
        if 'error' in result:
            print(f"❌ {result['error']}")
            return
        
        char = result['character']
        print(f"🎉 Character created!")
        print(f"   Name: {char['name']}")
        print(f"   Class: {char['class']}")
        print(f"   Health: {char['health']}")
        if faction:
            print(f"   Faction: {faction}")
        for action in result.get('next_actions', []):
            print(f"   Next: {action['method']} {action['endpoint']}")
    
    def status(self):
        """Check character status"""
        result = self._request('GET', '/api/character/status')
        
        if 'error' in result:
            print(f"❌ {result['error']}")
            return
        
        c = result['character']
        print(f"""
🐉 CLAWDUNGEON 🐉

👤 {c['name']} | Level {c['level']} {c['class']}
{'='*40}
❤️  {c['health_bar']}
🔮 {c['mana']}

⚔️ Attack: {c['attack']} | 🛡️ Defense: {c['defense']} | ⚡ Speed: {c['speed']}
💰 Gold: {c['gold']} | ⭐ XP: {c['experience']['progress_bar']}

🎒 Equipment:
   Weapon: {c['equipment']['weapon']}
   Armor: {c['equipment']['armor']}

📦 Inventory:
   {', '.join(c['inventory']) or 'Empty'}
""")
    
    def fight(self, *enemies):
        """Start combat"""
        result = self._request('POST', '/api/combat/start', {'enemies': list(enemies)})
        
        if 'error' in result:
            print(f"❌ {result['error']}")
            return
        
        self._print_combat(result)
    
    def attack(self, target: int = 0):
        """Attack in combat"""
        result = self._request('POST', '/api/combat/attack', {'target': target})
        
        if 'error' in result:
            print(f"❌ {result['error']}")
            return
        
        if result.get('result') == 'victory':
            print("\n🎉 VICTORY!")
            print(f"⭐ XP: +{result['rewards']['xp']}")
            print(f"💰 Gold: +{result['rewards']['gold']}")
            if result['rewards']['loot']:
                print(f"📦 Loot: {', '.join(result['rewards']['loot'])}")
        elif result.get('result') == 'defeat':
            print("\n☠️ DEFEAT!")
            print("You have been defeated!")
        else:
            self._print_combat(result)
    
    def flee(self):
        """Attempt to flee"""
        result = self._request('POST', '/api/combat/flee')
        
        if 'error' in result:
            print(f"❌ {result['error']}")
            return
        
        if result['result'] == 'fled':
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
            if 'combat' in result:
                self._print_combat(result['combat'])
    
    def _print_combat(self, state):
        """Print combat state"""
        print(f"""
🗡️ COMBAT - Turn {state['turn']}
{'='*40}

👤 {state['player']['name']}
   {state['player']['health_bar']}
""")
        print("👹 Enemies:")
        for enemy in state['enemies']:
            if 'status' in enemy:
                print(f"   [💀] {enemy['name']} {enemy['status']}")
            else:
                print(f"   [{enemy['index']}] {enemy['name']}")
                print(f"       {enemy['health_bar']}")
        
        if state.get('recent_logs'):
            print("\n📜 Recent events:")
            for log in state['recent_logs']:
                print(f"   {log}")
    
    def set_server(self, url: str):
        """Change server URL"""
        config = self._load_config()
        config['server'] = url
        self._save_config(config)
        self.server_url = url
        print(f"✅ Server set to: {url}")


def main():
    if len(sys.argv) < 2:
        print("""
🐉 CLAWDUNGEON Client 🐉

Usage: claw <command> [args...]

Account:
  claw register <username>          Register new account
  claw login <username>             Login to existing account
  claw set-server <url>             Set server URL

Character:
  claw create <name> <class> [faction]
                                    Create character; faction is optional
  claw status                       View character status

Combat:
  claw fight <enemy1> [enemy2...]   Start combat (goblin/skeleton/orc/wolf/spider)
  claw attack [target]              Attack (default target: 0)
  claw flee                         Attempt to flee

Examples:
  claw register Jeremy
  claw create "Jeremy" warrior iron_vanguard
  claw fight goblin skeleton
  claw attack 0
""")
        sys.exit(0)
    
    client = ClawDungeonClient()
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd == 'register' and args:
        password = getpass.getpass("Password: ")
        client.register(args[0], password)
    elif cmd == 'login' and args:
        password = getpass.getpass("Password: ")
        client.login(args[0], password)
    elif cmd == 'set-server' and args:
        client.set_server(args[0])
    elif cmd == 'create' and len(args) >= 2:
        faction = args[2] if len(args) >= 3 else None
        client.create_character(args[0], args[1], faction)
    elif cmd == 'status':
        client.status()
    elif cmd == 'fight' and args:
        client.fight(*args)
    elif cmd == 'attack':
        target = int(args[0]) if args else 0
        client.attack(target)
    elif cmd == 'flee':
        client.flee()
    else:
        print(f"❌ Unknown command: {cmd}")
        print("Run 'claw' without arguments for help.")

if __name__ == '__main__':
    main()
