# VPS Deployment Guide - Meta Analytics API

## Target Server
- **IP**: 31.97.51.154
- **User**: root
- **Path**: /root/project/python/bot-meta-analisis-api-V2

## Prerequisites
1. SSH access to VPS (password or SSH key)
2. `.env` file with required credentials
3. Google Sheets credentials JSON file

## Quick Deployment (Automated)

### Option 1: One-Command Deployment
```bash
bash deploy_to_vps.sh
```

This script will:
- Test SSH connection
- Create project directory
- Sync all files (excluding .git, venv, __pycache__)
- Install system dependencies (Python 3.11, Nginx, Supervisor)
- Create Python virtual environment
- Install Python packages from requirements.txt
- Create systemd service
- Guide you through .env setup

### Option 2: Manual Deployment

#### Step 1: Connect to VPS
```bash
ssh root@31.97.51.154
```

#### Step 2: Create Project Directory
```bash
mkdir -p /root/project/python
cd /root/project/python
```

#### Step 3: Upload Files
From your local machine:
```bash
rsync -avz --progress \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'venv' \
    --exclude '.env' \
    ./ root@31.97.51.154:/root/project/python/bot-meta-analisis-api-V2/
```

#### Step 4: Install System Dependencies
On VPS:
```bash
apt-get update
apt-get install -y python3.11 python3.11-venv python3-pip nginx supervisor
```

#### Step 5: Setup Python Environment
```bash
cd /root/project/python/bot-meta-analisis-api-V2
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 6: Configure Environment Variables
```bash
nano .env
```

Add the following:
```env
# Google Gemini API
GOOGLE_API_KEY=your_gemini_api_key_here

# Google Sheets Credentials
GOOGLE_SHEETS_CREDENTIALS=/root/project/python/bot-meta-analisis-api-V2/credentials.json

# Sheet Configuration
SHEET_IDS=your_sheet_id_1,your_sheet_id_2
WORKSHEET_WHITELIST=msa age gender,msa region,msa placement,msa adset ad

# Flask Configuration (optional)
FLASK_ENV=production
PORT=5000
```

#### Step 7: Upload Google Credentials
From your local machine:
```bash
scp path/to/credentials.json root@31.97.51.154:/root/project/python/bot-meta-analisis-api-V2/
```

#### Step 8: Create Systemd Service
On VPS:
```bash
nano /etc/systemd/system/meta-analytics.service
```

Add:
```ini
[Unit]
Description=Meta Analytics API
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=/root/project/python/bot-meta-analisis-api-V2
Environment="PATH=/root/project/python/bot-meta-analisis-api-V2/venv/bin"
ExecStart=/root/project/python/bot-meta-analisis-api-V2/venv/bin/gunicorn --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Step 9: Start Service
```bash
systemctl daemon-reload
systemctl start meta-analytics
systemctl enable meta-analytics
systemctl status meta-analytics
```

#### Step 10: Configure Nginx (Optional)
```bash
bash configure_nginx.sh
```

Or manually:
```bash
nano /etc/nginx/sites-available/meta-analytics
```

Add:
```nginx
server {
    listen 80;
    server_name 31.97.51.154;  # or your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

Enable and restart:
```bash
ln -s /etc/nginx/sites-available/meta-analytics /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## Testing

### Test Health Endpoint
```bash
curl http://31.97.51.154:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-05T..."
}
```

### Test Chat Endpoint
```bash
curl -X POST "http://31.97.51.154:5000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "Berapa total cost dari msa age gender?"}'
```

Expected response time: 15-20 seconds for 9001 rows

## Monitoring

### View Service Logs
```bash
journalctl -u meta-analytics -f
```

### Check Service Status
```bash
systemctl status meta-analytics
```

### Check Resource Usage
```bash
htop
```

### Restart Service
```bash
systemctl restart meta-analytics
```

## Performance Optimization

### Current Configuration
- **Workers**: 2 Gunicorn workers
- **Threads**: 4 threads per worker
- **Timeout**: 120 seconds
- **Expected Performance**: 15-20 seconds for 9001 rows (vs 35-45s on Render)

### Tuning Tips
1. **Increase workers** if you have more CPU cores:
   ```bash
   # Edit service file
   nano /etc/systemd/system/meta-analytics.service
   # Change: --workers 4
   systemctl daemon-reload
   systemctl restart meta-analytics
   ```

2. **Increase timeout** for very large datasets:
   ```bash
   # Change: --timeout 180
   ```

3. **Add memory limit** to prevent OOM:
   ```bash
   # Add to [Service] section:
   MemoryLimit=1G
   ```

## Firewall Configuration

### Allow HTTP/HTTPS
```bash
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 5000/tcp  # Flask (if not using Nginx)
ufw enable
```

## SSL Certificate (Optional)

### Using Let's Encrypt
```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

## Troubleshooting

### Service won't start
```bash
# Check logs
journalctl -u meta-analytics -n 50 --no-pager

# Check if port is in use
netstat -tlnp | grep 5000

# Test app manually
cd /root/project/python/bot-meta-analisis-api-V2
source venv/bin/activate
python app.py
```

### Permission errors
```bash
chown -R root:root /root/project/python/bot-meta-analisis-api-V2
chmod +x /root/project/python/bot-meta-analisis-api-V2/venv/bin/*
```

### Google Sheets API errors
```bash
# Verify credentials file exists
ls -la /root/project/python/bot-meta-analisis-api-V2/credentials.json

# Check environment variables
systemctl show meta-analytics | grep Environment
```

### High memory usage
```bash
# Check memory
free -h

# Restart service
systemctl restart meta-analytics
```

## Updating Code

### Pull latest changes
```bash
cd /root/project/python/bot-meta-analisis-api-V2
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart meta-analytics
```

### Or re-sync from local
From your local machine:
```bash
bash deploy_to_vps.sh
ssh root@31.97.51.154 'systemctl restart meta-analytics'
```

## Backup & Restore

### Backup configuration
```bash
tar -czf meta-analytics-backup.tar.gz \
    /root/project/python/bot-meta-analisis-api-V2/.env \
    /root/project/python/bot-meta-analisis-api-V2/credentials.json \
    /etc/systemd/system/meta-analytics.service \
    /etc/nginx/sites-available/meta-analytics
```

### Restore from backup
```bash
tar -xzf meta-analytics-backup.tar.gz -C /
systemctl daemon-reload
systemctl restart meta-analytics
systemctl restart nginx
```

## Support

For issues or questions:
1. Check logs: `journalctl -u meta-analytics -f`
2. Verify environment variables in `.env`
3. Test Google Sheets API credentials
4. Check VPS resource usage (CPU, RAM)

## Summary

✅ **Deployment Benefits**:
- 10x faster than Render free tier (1 dedicated vCPU vs 0.1 shared)
- No 30-second timeout limitation
- Full control over configuration
- Estimated response time: 15-20 seconds for 9001 rows

✅ **Next Steps**:
1. Run `bash deploy_to_vps.sh`
2. Configure `.env` with credentials
3. Test with `/health` endpoint
4. Test with actual query (9001 rows)
5. Monitor performance and adjust workers if needed
