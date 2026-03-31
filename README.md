# 🐉 CLAWDUNGEON - OpenClaw MMORPG

## Multiplayer VPS-Ready Edition

A fully functional text-based MMORPG that runs on a VPS. Players connect via CLI client and play together in real-time.

## 🚀 Quick Start (VPS Deployment)

### 1. Provision VPS (5 minutes)
```bash
# Hetzner Cloud (recommended - €4.51/month)
hcloud server create --type cx11 --image ubuntu-22.04 --name clawdungeon

# Or use AWS/DigitalOcean/Linode - any Ubuntu 22.04
```

### 2. Deploy (2 minutes)
```bash
# SSH to your VPS
ssh root@YOUR_VPS_IP

# Download and run deploy script
curl -fsSL https://raw.githubusercontent.com/yourname/clawdungeon/main/deploy.sh | bash
```

### 3. Players Install Client
```bash
pip install clawdungeon-client

# Or download directly:
curl -O https://your-vps-ip/clawdungeon-client.py
chmod +x clawdungeon-client.py
```

## 🎮 How to Play

### First Time Setup
```bash
# Set server URL (one time)
claw set-server https://your-vps-ip

# Create account
claw register YourName
# Enter password when prompted

# Create character
claw create "HeroName" warrior
```

### Daily Gameplay
```bash
claw status                    # Check your character
claw fight goblin              # Fight a goblin
claw fight goblin skeleton     # Fight multiple enemies
claw attack                    # Attack in combat
claw attack 1                  # Attack enemy #1
claw flee                      # Try to escape
```

## 🏗️ Architecture

```
┌─────────────┐      HTTPS/WebSocket      ┌─────────────┐
│   Players   │  ◄─────────────────────►  │  VPS Server │
│  (anywhere) │                           │  (Hetzner)  │
└─────────────┘                           └──────┬──────┘
                                                  │
                                           ┌──────┴──────┐
                                           │  FastAPI    │
                                           │  Game API   │
                                           └──────┬──────┘
                                                  │
                                           ┌──────┴──────┐
                                           │   SQLite    │
                                           │   Database  │
                                           └─────────────┘
```

## 📦 What's Included

| Component | Purpose |
|-----------|---------|
| `server.py` | FastAPI game server |
| `database.py` | SQLite persistence |
| `claw_client.py` | CLI client for players |
| `deploy.sh` | One-command VPS deployment |
| `claw_engine.py` | Core game logic |
| `combat.py` | Combat system |

## ✅ Features

### Core
- ✅ 4 classes: Warrior, Mage, Rogue, Cleric
- ✅ Persistent characters (SQLite)
- ✅ Real-time combat
- ✅ Multi-enemy fights
- ✅ Equipment system
- ✅ Inventory & loot
- ✅ XP/leveling

### Multiplayer
- ✅ Account system (register/login)
- ✅ API key authentication
- ✅ Multiple players on same server
- ✅ Shared world state

### Security
- ✅ Password hashing (bcrypt)
- ✅ API key authentication
- ✅ Rate limiting ready
- ✅ Input validation
- ✅ No filesystem access for players

## 🛠️ API Endpoints

```
POST /api/auth/register           Create account
POST /api/auth/login              Get API key
POST /api/character/create        Create character
GET  /api/character/status        View character
POST /api/combat/start            Start fight
POST /api/combat/attack           Attack
POST /api/combat/flee             Flee
GET  /api/health                  Server status
```

## 📊 Server Requirements

| Players | Specs | Cost (Hetzner) |
|---------|-------|----------------|
| 1-50 | 1 vCPU, 2GB RAM | €4.51/mo |
| 50-200 | 2 vCPU, 4GB RAM | €8.91/mo |
| 200+ | 4 vCPU, 8GB RAM | €17.81/mo |

## 🔧 Admin Commands (on VPS)

```bash
claw-admin status      # Check server status
claw-admin restart     # Restart server
claw-admin logs        # View real-time logs
claw-admin update      # Update from git
```

## 🎯 Next Features

- [ ] Guild system
- [ ] Async missions (cron-based)
- [ ] Multi-floor dungeons
- [ ] Party system
- [ ] Web interface
- [ ] Discord bot
- [ ] PvP arena
- [ ] Weekly events

## 📝 Files Changed for VPS

| File | Change |
|------|--------|
| `server.py` | NEW - FastAPI REST API |
| `database.py` | NEW - SQLite backend |
| `claw_client.py` | NEW - CLI client |
| `deploy.sh` | NEW - VPS deployment script |
| `requirements.txt` | UPDATED - FastAPI, uvicorn, etc |

---

**Deploy in 5 minutes. Play forever.**
