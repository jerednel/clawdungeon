# CLAWDUNGEON VPS Deployment Guide

## Architecture

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

## Server Specs (Minimum)
- **1 vCPU, 2GB RAM** - Enough for 100+ concurrent players
- **20GB SSD** - Plenty for SQLite + logs
- **Ubuntu 22.04 LTS**
- **Domain** (optional) - Or use IP + SSL

## Estimated Cost
- **Hetzner CX11**: €4.51/month
- **AWS t3.small**: ~$15/month
- **DigitalOcean**: $6/month

## Security Model
- Each player has unique API key
- Rate limiting (prevent spam)
- Input validation
- No direct file system access
- SQLite for persistence

## API Endpoints

### Authentication
```
POST /api/auth/register
  { "username": "Jeremy", "password": "***" }
  → { "api_key": "claw_abc123", "player_id": "uuid" }

POST /api/auth/login
  { "username": "Jeremy", "password": "***" }
  → { "api_key": "claw_abc123" }
```

### Character
```
POST /api/character/create
  Headers: X-API-Key: claw_abc123
  Body: { "name": "Jeremy", "class": "warrior" }
  → Character created

GET /api/character/status
  Headers: X-API-Key: claw_abc123
  → { name, level, class, stats, equipment, inventory }
```

### Combat
```
POST /api/combat/start
  Body: { "enemies": ["goblin", "skeleton"] }
  → Combat state

POST /api/combat/attack
  Body: { "target": 0 }
  → Combat result + updated state

POST /api/combat/flee
  → Flee result
```

### Guilds
```
POST /api/guild/create
  Body: { "name": "Data Dragons" }

POST /api/guild/join
  Body: { "guild_id": "..." }

GET /api/guild/members
```

## Deployment Steps

### 1. Provision VPS
```bash
# Hetzner example
hcloud server create --type cx11 --image ubuntu-22.04 --name clawdungeon
```

### 2. Install Dependencies
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nginx sqlite3
```

### 3. Deploy Code
```bash
git clone https://github.com/yourname/clawdungeon.git
cd clawdungeon
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run with Systemd
```bash
sudo systemctl enable clawdungeon
sudo systemctl start clawdungeon
```

### 5. Configure Nginx + SSL
```bash
sudo certbot --nginx -d clawdungeon.yourdomain.com
```

## Client Options

### Option A: Python CLI Client
Players install a small client:
```bash
pip install clawdungeon-client
claw login
claw status
claw fight goblin
```

### Option B: Web Interface
Browser-based game with ASCII art terminal

### Option C: Discord Bot
Discord server integration:
```
/claw create Jeremy warrior
/claw status
/claw fight goblin
```

### Option D: Telegram Bot
Same as Discord but via Telegram

## Scaling Path

| Players | Setup |
|---------|-------|
| 1-100 | Single VPS, SQLite |
| 100-1000 | Single VPS, PostgreSQL |
| 1000+ | Multiple VPS, Redis, load balancer |

## Next Steps

1. **Build the FastAPI server**
2. **Create client CLI**
3. **Write deployment scripts**
4. **Test on VPS**
5. **Invite friends**

Want me to build the FastAPI server now?
