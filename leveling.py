#!/usr/bin/env python3
"""
CLAWDUNGEON - Leveling System
Experience, level-ups, and stat progression
"""
import math
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# Level configuration
MAX_LEVEL = 50

# Base XP formula: 100 * (1.5 ^ (level - 1))
def xp_for_level(level: int) -> int:
    """Calculate XP required to reach a specific level"""
    if level <= 1:
        return 0
    return int(100 * (1.5 ** (level - 1)))

def xp_for_next_level(current_level: int) -> int:
    """Get XP needed for the next level"""
    if current_level >= MAX_LEVEL:
        return 0
    return xp_for_level(current_level + 1)

def xp_progress(current_level: int, current_xp: int) -> Tuple[int, int, float]:
    """Get XP progress info: (current_xp_in_level, xp_needed_for_level, percentage)"""
    if current_level >= MAX_LEVEL:
        return (0, 0, 100.0)
    
    xp_for_current = xp_for_level(current_level)
    xp_for_next = xp_for_level(current_level + 1)
    
    xp_in_level = current_xp - xp_for_current
    xp_needed = xp_for_next - xp_for_current
    percentage = min(100.0, (xp_in_level / xp_needed) * 100) if xp_needed > 0 else 100.0
    
    return (xp_in_level, xp_needed, percentage)

# Level tiers
LEVEL_TIERS = {
    'Novice': (1, 10),
    'Adventurer': (11, 25),
    'Hero': (26, 40),
    'Legend': (41, 50)
}

def get_level_tier(level: int) -> str:
    """Get the tier name for a level"""
    for tier, (min_lvl, max_lvl) in LEVEL_TIERS.items():
        if min_lvl <= level <= max_lvl:
            return tier
    return 'Unknown'

# Stat gains per class per level
STAT_GAINS = {
    'warrior': {
        'max_health': 5,
        'attack': 2,
        'defense': 1,
        'speed': 0,
        'max_mana': 0
    },
    'mage': {
        'max_health': 3,
        'max_mana': 5,
        'magic_attack': 3,
        'attack': 0,
        'defense': 0,
        'speed': 0
    },
    'rogue': {
        'max_health': 3,
        'attack': 2,
        'speed': 2,
        'defense': 0,
        'max_mana': 0
    },
    'cleric': {
        'max_health': 4,
        'max_mana': 4,
        'healing_power': 2,
        'attack': 0,
        'defense': 0,
        'speed': 0
    }
}

@dataclass
class LevelUpResult:
    """Result of a level up operation"""
    leveled_up: bool
    levels_gained: int
    new_level: int
    stat_increases: Dict[str, int]
    tier_changed: bool
    new_tier: Optional[str]
    old_tier: Optional[str]
    messages: list

def apply_level_up(character: Dict, levels_to_gain: int = 1) -> LevelUpResult:
    """Apply level up gains to a character"""
    old_level = character['level']
    old_tier = get_level_tier(old_level)
    char_class = character['class']
    
    gains = STAT_GAINS.get(char_class, STAT_GAINS['warrior'])
    stat_increases = {}
    messages = []
    
    for _ in range(levels_to_gain):
        if character['level'] >= MAX_LEVEL:
            break
        
        character['level'] += 1
        
        # Apply stat increases
        for stat, increase in gains.items():
            if increase > 0:
                if stat in character:
                    character[stat] += increase
                    if stat not in stat_increases:
                        stat_increases[stat] = 0
                    stat_increases[stat] += increase
                
                # Also update current health/mana (full heal on level up)
                if stat == 'max_health':
                    character['health'] = character['max_health']
                elif stat == 'max_mana':
                    character['mana'] = character['max_mana']
    
    new_level = character['level']
    new_tier = get_level_tier(new_level)
    tier_changed = new_tier != old_tier
    
    # Build messages
    if levels_to_gain > 0:
        messages.append(f"🎉 LEVEL UP! You are now level {new_level}!")
        messages.append(f"📊 Stats increased: {', '.join(f'+{v} {k.replace('_', ' ').title()}' for k, v in stat_increases.items())}")
        messages.append(f"❤️ HP and Mana fully restored!")
        
        if tier_changed:
            messages.append(f"🏆 TIER ADVANCEMENT! You are now a {new_tier}!")
    
    return LevelUpResult(
        leveled_up=levels_to_gain > 0,
        levels_gained=new_level - old_level,
        new_level=new_level,
        stat_increases=stat_increases,
        tier_changed=tier_changed,
        new_tier=new_tier if tier_changed else None,
        old_tier=old_tier if tier_changed else None,
        messages=messages
    )

def check_level_up(character: Dict) -> LevelUpResult:
    """Check if character should level up based on current XP"""
    current_level = character['level']
    current_xp = character['experience']
    
    if current_level >= MAX_LEVEL:
        return LevelUpResult(
            leveled_up=False,
            levels_gained=0,
            new_level=current_level,
            stat_increases={},
            tier_changed=False,
            new_tier=None,
            old_tier=None,
            messages=[]
        )
    
    # Check how many levels we can gain
    levels_to_gain = 0
    check_level = current_level
    
    while check_level < MAX_LEVEL:
        xp_needed = xp_for_level(check_level + 1)
        if current_xp >= xp_needed:
            levels_to_gain += 1
            check_level += 1
        else:
            break
    
    if levels_to_gain > 0:
        return apply_level_up(character, levels_to_gain)
    
    return LevelUpResult(
        leveled_up=False,
        levels_gained=0,
        new_level=current_level,
        stat_increases={},
        tier_changed=False,
        new_tier=None,
        old_tier=None,
        messages=[]
    )

def add_experience(character: Dict, xp_amount: int, source: str = "") -> LevelUpResult:
    """Add experience to character and check for level up"""
    character['experience'] += xp_amount
    
    result = check_level_up(character)
    
    if xp_amount > 0 and not result.leveled_up:
        # Add XP message if no level up
        current, needed, pct = xp_progress(character['level'], character['experience'])
        result.messages.append(f"⭐ Gained {xp_amount} XP{f' from {source}' if source else ''}! ({current}/{needed} to next level)")
    elif xp_amount > 0 and result.leveled_up:
        # Insert XP gain message before level up messages
        result.messages.insert(0, f"⭐ Gained {xp_amount} XP{f' from {source}' if source else ''}!")
    
    return result

def get_level_info(character: Dict) -> Dict:
    """Get complete level progress information for a character"""
    level = character['level']
    xp = character['experience']
    
    current, needed, percentage = xp_progress(level, xp)
    tier = get_level_tier(level)
    next_tier = None
    
    for t_name, (min_lvl, max_lvl) in LEVEL_TIERS.items():
        if max_lvl > level:
            next_tier = {'name': t_name, 'level_required': min_lvl}
            break
    
    # XP sources info
    xp_sources = {
        'enemy_defeat': 'Defeat enemies (varies by difficulty)',
        'quest_complete': 'Complete quests',
        'exploration': 'Discover new areas',
        'boss_kill': 'Defeat bosses (bonus XP)'
    }
    
    return {
        'level': level,
        'tier': tier,
        'experience': xp,
        'xp_for_next_level': xp_for_next_level(level),
        'xp_in_current_level': current,
        'xp_needed_for_level': needed,
        'progress_percentage': round(percentage, 1),
        'max_level': MAX_LEVEL,
        'is_max_level': level >= MAX_LEVEL,
        'next_tier': next_tier,
        'xp_sources': xp_sources,
        'xp_table': {lvl: xp_for_level(lvl) for lvl in range(1, min(level + 5, MAX_LEVEL + 1))}
    }

# Experience rewards for enemies (base values, scaled by level)
ENEMY_XP_REWARDS = {
    'goblin': 15,
    'skeleton': 25,
    'orc': 40,
    'spider': 20,
    'slime': 10,
    'wolf': 30,
    'boss_goblin_king': 200,
    'boss_lich': 500,
    'boss_dragon': 1000
}

def calculate_enemy_xp(enemy_type: str, enemy_level: int = 1, is_boss: bool = False) -> int:
    """Calculate XP reward for defeating an enemy"""
    base_xp = ENEMY_XP_REWARDS.get(enemy_type, 15)
    
    # Level scaling
    level_multiplier = 1 + (enemy_level - 1) * 0.2
    
    # Boss bonus
    boss_multiplier = 2.0 if is_boss else 1.0
    
    return int(base_xp * level_multiplier * boss_multiplier)

# Quest XP rewards
QUEST_XP_REWARDS = {
    'easy': 50,
    'medium': 100,
    'hard': 200,
    'epic': 500
}

def calculate_quest_xp(difficulty: str, player_level: int = 1) -> int:
    """Calculate XP reward for completing a quest"""
    base_xp = QUEST_XP_REWARDS.get(difficulty, 50)
    level_multiplier = 1 + (player_level - 1) * 0.1
    return int(base_xp * level_multiplier)

# Exploration XP
EXPLORATION_XP = {
    'new_room': 10,
    'new_floor': 25,
    'secret_found': 30,
    'landmark': 50
}

def calculate_exploration_xp(discovery_type: str) -> int:
    """Calculate XP for exploration discoveries"""
    return EXPLORATION_XP.get(discovery_type, 10)
