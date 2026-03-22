#!/bin/bash
set -e

echo "========================================="
echo "  MarkazEdu Deploy Script"
echo "========================================="

# ---- CONFIGURATION ----
DOMAIN="markazedu.uz"
EMAIL="davronovtatu@gmail.com"
PROJECT_DIR="/root/markazedu"
BACKEND_REPO="https://github.com/davronovuz/edvora_backend.git"
FRONTEND_REPO="https://github.com/davronovuz/edvora_frontend.git"

# ---- STEP 1: System update & install Docker ----
echo ""
echo "[1/8] Tizimni yangilaymiz va Docker o'rnatamiz..."
apt-get update -y
apt-get install -y curl git

if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
fi

# ---- STEP 2: Clone repos ----
echo ""
echo "[2/8] Loyihani GitHub dan yuklaymiz..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

if [ -d "edvora_backend" ]; then
    cd edvora_backend && git pull && cd ..
else
    git clone $BACKEND_REPO edvora_backend
fi

if [ -d "edvora_frontend" ]; then
    cd edvora_frontend && git pull && cd ..
else
    git clone $FRONTEND_REPO edvora_frontend
fi

# ---- STEP 3: Build frontend ----
echo ""
echo "[3/8] Frontend build qilamiz..."
cd $PROJECT_DIR/edvora_frontend

# Install Node.js if needed
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

npm install
npm run build

# Copy built files to backend for nginx
mkdir -p $PROJECT_DIR/edvora_backend/frontend_dist
cp -r dist/* $PROJECT_DIR/edvora_backend/frontend_dist/

# ---- STEP 4: Setup environment ----
echo ""
echo "[4/8] Production muhitni sozlaymiz..."
cd $PROJECT_DIR/edvora_backend

# Generate a secure SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 50)
DB_PASS=$(openssl rand -base64 20 | tr -dc 'a-zA-Z0-9' | head -c 20)

cat > .env.production <<EOF
# Django
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,144.91.118.72,localhost
DJANGO_SETTINGS_MODULE=config.settings.production

# Database
DB_NAME=markazedu
DB_USER=markazedu_user
DB_PASSWORD=$DB_PASS
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# CORS
CORS_ALLOWED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
EOF

# Export DB_PASSWORD for docker-compose
export DB_PASSWORD=$DB_PASS

# ---- STEP 5: Initial nginx (HTTP only for certbot) ----
echo ""
echo "[5/8] Nginx ni HTTP rejimda ishga tushiramiz (SSL uchun)..."

# Use initial config (no SSL)
cp nginx/conf.d/initial.conf nginx/conf.d/active.conf
rm -f nginx/conf.d/default.conf

# Temporarily rename default.conf so only initial is used
cd $PROJECT_DIR/edvora_backend

# Build and start
docker compose up -d --build db redis
echo "DB va Redis tayyor bo'lishini kutamiz..."
sleep 10

docker compose up -d --build backend
sleep 5

# Run migrations and collect static
echo "Migratsiyalarni ishga tushiramiz..."
docker compose exec -T backend python manage.py migrate_schemas --shared
docker compose exec -T backend python manage.py collectstatic --noinput

# Start nginx
docker compose up -d nginx

# ---- STEP 6: SSL Certificate ----
echo ""
echo "[6/8] SSL sertifikat olamiz (Let's Encrypt)..."
sleep 3

docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    -d $DOMAIN \
    -d www.$DOMAIN \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --force-renewal

# ---- STEP 7: Switch to HTTPS nginx config ----
echo ""
echo "[7/8] HTTPS ga o'tamiz..."

# Replace with SSL config
cat > nginx/conf.d/active.conf <<'NGINXEOF'
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name markazedu.uz www.markazedu.uz;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name markazedu.uz www.markazedu.uz;

    ssl_certificate /etc/letsencrypt/live/markazedu.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/markazedu.uz/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;

        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /admin/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /app/media/;
        expires 7d;
    }
}
NGINXEOF

# Reload nginx with SSL
docker compose restart nginx

# ---- STEP 8: Start remaining services ----
echo ""
echo "[8/8] Celery va boshqa servislarni ishga tushiramiz..."
docker compose up -d celery_worker celery_beat certbot

# Create superuser prompt
echo ""
echo "========================================="
echo "  DEPLOY MUVAFFAQIYATLI YAKUNLANDI!"
echo "========================================="
echo ""
echo "  Sayt: https://$DOMAIN"
echo "  Admin: https://$DOMAIN/admin/"
echo "  API: https://$DOMAIN/api/v1/"
echo "  API Docs: https://$DOMAIN/api/docs/"
echo ""
echo "  Superuser yaratish uchun:"
echo "  docker compose exec backend python manage.py createsuperuser"
echo ""
echo "  Tenant yaratish uchun:"
echo "  docker compose exec backend python manage.py shell"
echo "  >>> from apps.shared.models import Tenant, Domain"
echo "  >>> t = Tenant(schema_name='demo', name='Demo Markaz')"
echo "  >>> t.save()"
echo "  >>> Domain(domain='demo.markazedu.uz', tenant=t, is_primary=True).save()"
echo ""
echo "========================================="
