#!/bin/bash
cd /opt/clawdungeon
python3 -m uvicorn server:app \
  --host 0.0.0.0 \
  --port 443 \
  --ssl-keyfile /etc/letsencrypt/live/clawdungeon.com/privkey.pem \
  --ssl-certfile /etc/letsencrypt/live/clawdungeon.com/fullchain.pem \
  > server.log 2>&1 &
echo "Server started on HTTPS port 443"
