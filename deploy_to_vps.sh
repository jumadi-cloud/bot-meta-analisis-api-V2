#!/bin/bash

# Deployment script for Meta Analytics API to VPS
# Target: root@31.97.51.154:/root/project/python
# Usage: bash deploy_to_vps.sh

set -e  # Exit on error

echo "================================"
echo "Meta Analytics API - VPS Deployment"
echo "================================"
echo ""

VPS_HOST="31.97.51.154"
VPS_USER="root"
VPS_PASSWORD="Mesonvps123@"
VPS_PATH="/root/project/python/bot-meta-analisis-api-V2"
LOCAL_PATH="."

echo "Target VPS: $VPS_USER@$VPS_HOST"
echo "Target Path: $VPS_PATH"
echo ""

# Function to run SSH command with password
ssh_cmd() {
    sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_HOST "$@"
}

# Function to run SCP with password
scp_cmd() {
    sshpass -p "$VPS_PASSWORD" scp -o StrictHostKeyChecking=no "$@"
}

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "Installing sshpass..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y sshpass
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install hudochenkov/sshpass/sshpass
    else
        echo "Please install sshpass manually or use SSH key authentication"
        exit 1
    fi
fi

# Check if we can connect to VPS
echo "[1/7] Testing SSH connection..."
if ssh_cmd "echo 'Connection successful'"; then
    echo "✓ SSH connection successful"
else
    echo "✗ Cannot connect to VPS. Please check:"
    echo "  - VPS IP address is correct"
    echo "  - Password is correct"
    echo "  - Firewall allows SSH (port 22)"
    exit 1
fi

echo ""
echo "[2/7] Creating project directory on VPS..."
ssh_cmd "mkdir -p $VPS_PATH"

echo ""
echo "[3/7] Syncing project files to VPS..."
sshpass -p "$VPS_PASSWORD" rsync -avz --progress -e "ssh -o StrictHostKeyChecking=no" \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'venv' \
    --exclude '.env' \
    --exclude 'node_modules' \
    --exclude '.pytest_cache' \
    $LOCAL_PATH/ $VPS_USER@$VPS_HOST:$VPS_PATH/

echo ""
echo "[4/7] Installing system dependencies..."
ssh_cmd << 'ENDSSH'
set -e

# Update system
apt-get update

# Install Python 3.11+ and required packages
apt-get install -y python3.11 python3.11-venv python3-pip nginx supervisor

# Install certbot for SSL (optional)
apt-get install -y certbot python3-certbot-nginx

echo "✓ System dependencies installed"
ENDSSH

echo ""
echo "[5/7] Setting up Python environment..."
ssh_cmd << ENDSSH
set -e
cd $VPS_PATH

# Create virtual environment
python3.11 -m venv venv

# Activate and install requirements
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Python environment ready"
ENDSSH

echo ""
echo "[6/7] Configuring environment variables..."
echo ""
echo "⚠️  IMPORTANT: You need to create .env file on VPS with:"
echo ""
echo "Required environment variables:"
echo "  - GOOGLE_API_KEY=your_gemini_api_key"
echo "  - GOOGLE_SHEETS_CREDENTIALS=path_to_credentials_json"
echo "  - SHEET_IDS=your_sheet_ids"
echo "  - WORKSHEET_WHITELIST=your_worksheets"
echo ""
echo "Do you want to upload .env file now? (y/n)"
read -r upload_env

if [ "$upload_env" = "y" ]; then
    if [ -f ".env" ]; then
        echo "Uploading .env file..."
        scp_cmd .env $VPS_USER@$VPS_HOST:$VPS_PATH/.env
        echo "✓ .env file uploaded"
    else
        echo "✗ .env file not found in current directory"
        echo "Please create it manually on VPS later"
    fi
else
    echo "⚠️  Remember to create .env file on VPS before running the app"
fi

echo ""
echo "[7/7] Creating systemd service..."
ssh_cmd << 'ENDSSH'
set -e

# Create systemd service file
cat > /etc/systemd/system/meta-analytics.service << 'EOF'
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
EOF

# Reload systemd
systemctl daemon-reload

echo "✓ Systemd service created"
ENDSSH

echo ""
echo "================================"
echo "Deployment Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure .env file on VPS (if not uploaded):"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   cd $VPS_PATH"
echo "   nano .env"
echo ""
echo "2. Upload Google Sheets credentials JSON:"
echo "   scp path/to/credentials.json $VPS_USER@$VPS_HOST:$VPS_PATH/"
echo ""
echo "3. Start the service:"
echo "   ssh $VPS_USER@$VPS_HOST 'systemctl start meta-analytics'"
echo "   ssh $VPS_USER@$VPS_HOST 'systemctl enable meta-analytics'"
echo ""
echo "4. Check service status:"
echo "   ssh $VPS_USER@$VPS_HOST 'systemctl status meta-analytics'"
echo ""
echo "5. View logs:"
echo "   ssh $VPS_USER@$VPS_HOST 'journalctl -u meta-analytics -f'"
echo ""
echo "6. Configure Nginx (optional, for domain/SSL):"
echo "   Run: bash configure_nginx.sh"
echo ""
echo "7. Test the API:"
echo "   curl http://$VPS_HOST:5000/health"
echo ""
