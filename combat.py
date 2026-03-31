#!/usr/bin/env python3
"""
CLAWDUNGEON - Combat & Dungeon System
"""
import json
import random
from pathlib import Path
from typing import Dict, List, Optional
from claw_engine import Player, load_item_db, BASE_PATH
from leveling import add_experience, calculate_enemy_xp, get_level_info, get_level_tier

class Enemy:
    ENEMY_TYPES = {
        'goblin': {'name': 'Goblin Scout', 'health': 25, 'attack': 8, 'defense': 3, 'xp': 15, 'gold': 5},
        'skeleton': {'name': 'Skeleton Warrior', 'health': 40, 'attack': 12, 'defense': 5, 'xp': 25, 'gold': 10},
        'orc': {'name': 'Orc Berserker', 'health': 60, 'attack': 15, 'defense': 8, 'xp': 40, 'gold': 15},
        'spider': {'name': 'Giant Spider', 'health': 35, 'attack': 10, 'defense': 4, 'xp': 20, 'gold': 8},
        'slime': {'name': 'Acid Slime', 'health': 50, 'attack': 6, 'defense': 2, 'xp': 10, 'gold': 3},
        'wolf': {'name': 'Dire Wolf', 'health': 45, 'attack': 14, 'defense': 6, 'xp': 30, 'gold': 12},
    }
    
    def __init__(self, enemy_type: str, level: int = 1):
        base = self.ENEMY_TYPES.get(enemy_type, self.ENEMY_TYPES['goblin'])
        self.type = enemy_type
        self.name = base['name']
        self.max_health = int(base['health'] * (1 + (level - 1) * 0.2))
        self.health = self.max_health
        self.attack = int(base['attack'] * (1 + (level - 1) * 0.15))
        self.defense = int(base['defense'] * (1 + (level - 1) * 0.1))
        # Use leveling system for XP calculation
        self.xp_reward = calculate_enemy_xp(enemy_type, level)
        self.gold_reward = int(base['gold'] * (1 + (level - 1) * 0.2))
        self.level = level


class CombatEncounter:
    def __init__(self, player: Player, enemies: List[Enemy]):
        self.player = player
        self.enemies = enemies
        self.turn = 1
        self.log = []
    
    def calculate_damage(self, attacker_attack: int, defender_defense: int) -> int:
        base_damage = max(1, attacker_attack - defender_defense)
        variance = random.uniform(0.8, 1.2)
        crit_chance = 0.15
        
        damage = int(base_damage * variance)
        
        if random.random() < crit_chance:
            damage = int(damage * 1.5)
            return damage, True
        return damage, False
    
    def player_attack(self, target_idx: int = 0) -> str:
        if target_idx >= len(self.enemies) or self.enemies[target_idx].health <= 0:
            return "❌ Invalid target!"
        
        enemy = self.enemies[target_idx]
        damage, is_crit = self.calculate_damage(
            self.player.get_total_attack(),
            enemy.defense
        )
        
        enemy.health -= damage
        
        result = f"⚔️ You attack {enemy.name}!"
        if is_crit:
            result += " 💥 CRITICAL HIT!"
        result += f" (-{damage} HP)"
        
        if enemy.health <= 0:
            result += f"\n💀 {enemy.name} defeated!"
        
        self.log.append(result)
        return result
    
    def enemy_turn(self) -> List[str]:
        results = []
        for enemy in self.enemies:
            if enemy.health <= 0:
                continue
            
            damage, is_crit = self.calculate_damage(
                enemy.attack,
                self.player.get_total_defense()
            )
            
            self.player.health -= damage
            
            result = f"💢 {enemy.name} attacks you!"
            if is_crit:
                result += " 🎯 CRITICAL!"
            result += f" (-{damage} HP)"
            results.append(result)
            
            if self.player.health <= 0:
                results.append("☠️ You have been defeated!")
                break
        
        self.log.extend(results)
        return results
    
    def get_status(self) -> str:
        status = f"""
🗡️ COMBAT - Turn {self.turn}
{'='*40}
"""
        # Player status
        health_pct = self.player.health / self.player.max_health
        health_bar = "█" * int(health_pct * 10) + "░" * (10 - int(health_pct * 10))
        status += f"\n👤 {self.player.name} [{health_bar}] {max(0, self.player.health)}/{self.player.max_health} HP\n"
        
        # Enemy status
        status += "\n👹 Enemies:\n"
        for i, enemy in enumerate(self.enemies):
            if enemy.health > 0:
                enemy_pct = enemy.health / enemy.max_health
                enemy_bar = "█" * int(enemy_pct * 8) + "░" * (8 - int(enemy_pct * 8))
                status += f"   [{i}] {enemy.name} [{enemy_bar}] {enemy.health}/{enemy.max_health} HP\n"
            else:
                status += f"   [💀] {enemy.name} DEFEATED\n"
        
        status += "\n🎮 Actions: /claw attack [target] | /claw use [item] | /claw flee"
        return status
    
    def is_combat_over(self) -> tuple:
        player_dead = self.player.health <= 0
        all_enemies_dead = all(e.health <= 0 for e in self.enemies)
        return player_dead or all_enemies_dead, player_dead
    
    def get_rewards(self) -> Optional[Dict]:
        total_xp = sum(e.xp_reward for e in self.enemies if e.health <= 0)
        total_gold = sum(e.gold_reward for e in self.enemies if e.health <= 0)
        
        # Loot drops
        loot = []
        item_db = load_item_db()
        for e in self.enemies:
            if e.health <= 0 and random.random() < 0.3:
                possible_loot = ['health_potion', 'mana_potion']
                loot.append(random.choice(possible_loot))
        
        return {
            'xp': total_xp,
            'gold': total_gold,
            'loot': loot
        }


def start_combat(player_name: str, enemy_types: List[str]) -> str:
    """Start a combat encounter"""
    player = Player.load_by_name(player_name)
    if not player:
        return "❌ Character not found!"
    
    if player.health <= 0:
        return "❌ You are defeated! Rest to recover."
    
    enemies = [Enemy(et, level=player.level) for et in enemy_types]
    encounter = CombatEncounter(player, enemies)
    
    # Save encounter state
    save_encounter(player.id, encounter)
    
    return encounter.get_status()


def process_turn(player_name: str, action: str, target: int = 0) -> str:
    """Process a combat turn"""
    player = Player.load_by_name(player_name)
    if not player:
        return "❌ Character not found!"
    
    encounter = load_encounter(player.id)
    if not encounter:
        return "❌ No active combat!"
    
    result = ""
    
    if action == 'attack':
        result = encounter.player_attack(target)
    elif action == 'flee':
        if random.random() < 0.5:
            result = "🏃 You successfully fled!"
            clear_encounter(player.id)
            return result
        else:
            result = "❌ Failed to flee!"
    else:
        result = "❌ Unknown action!"
    
    # Check if combat over
    is_over, player_dead = encounter.is_combat_over()
    
    if not is_over:
        # Enemy turn
        enemy_results = encounter.enemy_turn()
        result += "\n" + "\n".join(enemy_results)
        encounter.turn += 1
        save_encounter(player.id, encounter)
        result += encounter.get_status()
    else:
        if player_dead:
            result += "\n☠️ GAME OVER"
            player.health = 1  # Barely survived
        else:
            rewards = encounter.get_rewards()
            # Use leveling system to add XP
            level_result = add_experience(player.__dict__, rewards['xp'], source="combat victory")
            player.gold += rewards['gold']
            player.inventory.extend(rewards['loot'])
            
            result += f"""
🎉 VICTORY!
⭐ XP Gained: {rewards['xp']}
💰 Gold Gained: {rewards['gold']}
📦 Loot: {', '.join(rewards['loot']) or 'None'}
"""
            # Add level-up messages if applicable
            if level_result.leveled_up:
                result += "\n" + "\n".join(level_result.messages)
            else:
                # Show XP progress
                level_info = get_level_info(player.__dict__)
                result += f"\n📊 XP: {level_info['in_current_level']}/{level_info['xp_needed_for_level']} ({level_info['progress_percentage']}% to level {player.level + 1})"
        
        player.save()
        clear_encounter(player.id)
    
    return result


def save_encounter(player_id: str, encounter: CombatEncounter):
    """Save combat state"""
    path = BASE_PATH / 'dungeons' / f'{player_id}_combat.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'player_id': player_id,
        'enemies': [e.__dict__ for e in encounter.enemies],
        'turn': encounter.turn,
        'log': encounter.log
    }
    with open(path, 'w') as f:
        json.dump(data, f)


def load_encounter(player_id: str) -> Optional[CombatEncounter]:
    """Load combat state"""
    path = BASE_PATH / 'dungeons' / f'{player_id}_combat.json'
    if not path.exists():
        return None
    
    player = Player.load(player_id)
    if not player:
        return None
    
    with open(path) as f:
        data = json.load(f)
    
    enemies = []
    for e_data in data['enemies']:
        e = Enemy.__new__(Enemy)
        e.__dict__.update(e_data)
        enemies.append(e)
    
    encounter = CombatEncounter(player, enemies)
    encounter.turn = data['turn']
    encounter.log = data['log']
    return encounter


def clear_encounter(player_id: str):
    """Clear combat state"""
    path = BASE_PATH / 'dungeons' / f'{player_id}_combat.json'
    if path.exists():
        path.unlink()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: combat.py <command> [args...]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'fight' and len(sys.argv) >= 3:
        name = sys.argv[2]
        enemies = sys.argv[3:]
        print(start_combat(name, enemies))
    elif cmd == 'attack' and len(sys.argv) >= 3:
        name = sys.argv[2]
        target = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        print(process_turn(name, 'attack', target))
    elif cmd == 'flee' and len(sys.argv) >= 3:
        name = sys.argv[2]
        print(process_turn(name, 'flee'))
    else:
        print("Unknown command")
