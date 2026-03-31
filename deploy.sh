#!/bin/bash
# CLAWDUNGEON VPS Deployment Script
# Run on fresh Ubuntu 22.04 VPS

set -e

echo "🐉 CLAWDUNGEON VPS Deployment"
echo "=============================="

# Configuration
GAME_USER="clawdungeon"
GAME_DIR="/opt/clawdungeon"
REPO_URL="${REPO_URL:-https://github.com/yourname/clawdungeon.git}"
DOMAIN="${DOMAIN:-}"

# Update system
echo "📦 Updating system..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "📦 Installing dependencies..."
apt-get install -y python3-pip python3-venv git nginx sqlite3 certbot python3-certbot-nginx

# Create user
echo "👤 Creating game user..."
if ! id "$GAME_USER" &>/dev/null; then
    useradd -r -s /bin/false -d $GAME_DIR $GAME_USER
fi

# Create directory
echo "📁 Setting up game directory..."
mkdir -p $GAME_DIR
chown $GAME_USER:$GAME_USER $GAME_DIR

# Clone repository (or copy files)
echo "📥 Installing game files..."
if [ -d "$GAME_DIR/.git" ]; then
    cd $GAME_DIR
    sudo -u $GAME_USER git pull
else
    sudo -u $GAME_USER git clone $REPO_URL $GAME_DIR
fi

# Create virtual environment
echo "🐍 Setting up Python environment..."
cd $GAME_DIR
sudo -u $GAME_USER python3 -m venv venv
sudo -u $GAME_USER $GAME_DIR/venv/bin/pip install -r requirements.txt

# Create systemd service
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/clawdungeon.service << 'EOF'
[Unit]
Description=CLAWDUNGEON Game Server
After=network.target

[Service]
Type=simple
User=clawdungeon
Group=clawdungeon
WorkingDirectory=/opt/clawdungeon
Environment=PYTHONPATH=/opt/clawdungeon
ExecStart=/opt/clawdungeon/venv/bin/python /opt/clawdungeon/server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl daemon-reload
systemctl enable clawdungeon
systemctl start clawdungeon

# Configure Nginx
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/clawdungeon << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

ln -sf /etc/nginx/sites-available/clawdungeon /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# Setup SSL if domain provided
if [ -n "$DOMAIN" ]; then
    echo "🔒 Setting up SSL with Let's Encrypt..."
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN
    systemctl enable certbot.timer
fi

# Firewall
echo "🛡️ Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Create admin script
cat > /usr/local/bin/claw-admin << 'EOF'
#!/bin/bash
case "$1" in
    status)
        systemctl status clawdungeon
        ;;
    restart)
        systemctl restart clawdungeon
        echo "✅ Server restarted"
        ;;
    logs)
        journalctl -u clawdungeon -f
        ;;
    update)
        cd /opt/clawdungeon
        sudo -u clawdungeon git pull
        systemctl restart clawdungeon
        echo "✅ Updated and restarted"
        ;;
    *)
        echo "Usage: claw-admin {status|restart|logs|update}"
        ;;
esac
EOF
chmod +x /usr/local/bin/claw-admin

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ CLAWDUNGEON deployed successfully!"
echo ""
echo "🎮 Server Details:"
echo "   HTTP:  http://$SERVER_IP"
if [ -n "$DOMAIN" ]; then
    echo "   HTTPS: https://$DOMAIN"
fi
echo ""
echo "🔧 Admin Commands:"
echo "   claw-admin status    - Check server status"
echo "   claw-admin restart   - Restart server"
echo "   claw-admin logs      - View logs"
echo "   claw-admin update    - Update from git"
echo ""
echo "👥 Players can connect with:"
echo "   claw set-server http://$SERVER_IP"
if [ -n "$DOMAIN" ]; then
    echo "   claw set-server https://$DOMAIN"
fi
echo ""
echo "📁 Game files: $GAME_DIR"
echo "🗄️  Database: $GAME_DIR/clawdungeon.db"
echo ""
