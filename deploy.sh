#!/bin/bash
# Skrypt wdrożeniowy środowiska TeamFlow dla Ubuntu 26.04+ (i nowszych)

set -e # Zatrzymanie skryptu w przypadku błędu krytycznego

# Zapobieganie blokowaniu skryptu przez interaktywne okienka i 'needrestart'
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export NEEDRESTART_SUSPEND=1

echo "======================================================="
echo " Rozpoczęcie wdrożenia infrastruktury TeamFlow"
echo "======================================================="

# 1. Aktualizacja systemu i instalacja pakietów
echo -e "\n[1/6] Aktualizacja systemu..."
sudo -E apt-get update
sudo -E apt-get upgrade -yq
sudo -E apt-get install -yq curl wget git openssl apt-transport-https ca-certificates software-properties-common
sudo -E apt-get autoremove -yq

# 2. Instalacja Docker i Docker Compose
echo -e "\n[2/6] Weryfikacja środowiska Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo -E sh get-docker.sh
    sudo systemctl enable docker
    sudo systemctl start docker
    rm get-docker.sh
fi

# 3. Instalacja i konfiguracja Ollama
echo -e "\n[3/6] Instalacja silnika Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo "Konfigurowanie bindowania 0.0.0.0..."
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo '[Service]
Environment="OLLAMA_HOST=0.0.0.0"' | sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null

sudo systemctl daemon-reload
sudo systemctl restart ollama

# DODANO: Konfiguracja UFW dla komunikacji Docker -> Host
echo "Otwieranie portu 11434 w UFW dla komunikacji z kontenerami..."
sudo ufw allow 11434/tcp comment 'Ollama for Docker' || true

echo "Pobieranie modelu..."
ollama pull llama3 # LUB qwen2.5:1.5b (jeśli brakuje RAM)

# 4. Przygotowanie Nginx i SSL
echo -e "\n[4/6] Przygotowywanie SSL..."
sudo mkdir -p /DOCKER/nginx/ssl
if [ ! -f /DOCKER/nginx/ssl/nginx.crt ]; then
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /DOCKER/nginx/ssl/nginx.key \
        -out /DOCKER/nginx/ssl/nginx.crt \
        -subj "/C=PL/ST=Lubelskie/L=Lublin/O=TeamFlow/OU=IT/CN=app.local" \
        -addext "subjectAltName=DNS:app.local"
fi

echo "Generowanie nginx.conf..."
# DODANO: Zwiększone limity czasowe dla zapytań AI (proxy_timeout = 300s)
cat << 'EOF' | sudo tee /DOCKER/nginx/nginx.conf > /dev/null
events { worker_connections 1024; }
http {
    server {
        listen 80;
        server_name app.local;
        return 301 https://$host$request_uri;
    }
    server {
        listen 443 ssl;
        server_name app.local;
        ssl_certificate /etc/nginx/ssl/nginx.crt;
        ssl_certificate_key /etc/nginx/ssl/nginx.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        location / {
            proxy_read_timeout 6000;
            proxy_connect_timeout 6000;
            proxy_send_timeout 60000;
            
            proxy_pass http://web:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 5. Aktualizacja hosts
echo -e "\n[5/6] Aktualizacja /etc/hosts..."
if ! grep -q "app.local" /etc/hosts; then
    echo "127.0.0.1 app.local" | sudo tee -a /etc/hosts
fi

# 6. Start
echo -e "\n[6/6] Uruchamianie kontenerów..."
sudo docker compose down --remove-orphans || true
sudo docker rm -f teamflow_db2 teamflow_web teamflow_nginx 2>/dev/null || true
sudo docker compose up -d --build

echo "Wdrożenie zakończone! Aby sprawdzić dodaj do pliku hosts IP + adress domenowy"
echo "Otwóż w przegłądarce adress https://app.local i zakceptuj certyfikat"
echo "Konto do logowania:'
echo "Login: admin@teamflow.pl"
echo "Hasło: admin123" 
