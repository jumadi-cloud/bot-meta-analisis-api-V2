#!/bin/bash

# Nginx configuration script for Meta Analytics API
# Usage: bash configure_nginx.sh

set -e

VPS_HOST="31.97.51.154"
VPS_USER="root"
VPS_PATH="/root/project/python/bot-meta-analisis-api-V2"

echo "================================"
echo "Nginx Configuration"
echo "================================"
echo ""

echo "Do you want to configure a domain name? (y/n)"
read -r use_domain

if [ "$use_domain" = "y" ]; then
    echo "Enter your domain name (e.g., api.example.com):"
    read -r domain_name
    server_name="$domain_name"
    
    echo "Do you want to enable SSL with Let's Encrypt? (y/n)"
    read -r use_ssl
else
    server_name="$VPS_HOST"
    use_ssl="n"
fi

echo ""
echo "Creating Nginx configuration..."

ssh $VPS_USER@$VPS_HOST << ENDSSH
set -e

# Create Nginx configuration
cat > /etc/nginx/sites-available/meta-analytics << 'EOF'
server {
    listen 80;
    server_name $server_name;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeout settings for long-running requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        access_log off;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/meta-analytics /etc/nginx/sites-enabled/

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Restart Nginx
systemctl restart nginx
systemctl enable nginx

echo "✓ Nginx configured and started"
ENDSSH

if [ "$use_ssl" = "y" ]; then
    echo ""
    echo "Configuring SSL with Let's Encrypt..."
    
    ssh $VPS_USER@$VPS_HOST << ENDSSH
set -e

# Obtain SSL certificate
certbot --nginx -d $domain_name --non-interactive --agree-tos --email admin@$domain_name --redirect

# Auto-renewal
systemctl enable certbot.timer

echo "✓ SSL certificate installed"
ENDSSH
fi

echo ""
echo "================================"
echo "Nginx Configuration Complete!"
echo "================================"
echo ""

if [ "$use_domain" = "y" ]; then
    if [ "$use_ssl" = "y" ]; then
        echo "Your API is now available at: https://$domain_name"
    else
        echo "Your API is now available at: http://$domain_name"
    fi
    echo ""
    echo "⚠️  Make sure your domain DNS points to: $VPS_HOST"
else
    echo "Your API is now available at: http://$VPS_HOST"
fi

echo ""
echo "Test endpoints:"
echo "  curl http://$server_name/health"
echo "  curl -X POST http://$server_name/chat -H 'Content-Type: application/json' -d '{\"query\":\"test\"}'"
echo ""
