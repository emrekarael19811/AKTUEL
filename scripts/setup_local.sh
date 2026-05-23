#!/bin/bash
# AKTUEL Local Kurulum Scripti
# Kullanim: bash scripts/setup_local.sh

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}=== AKTUEL Local Kurulum ===${NC}"

# --- Python kontrolu ---
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3.11+ gerekli. https://python.org adresinden indirin.${NC}"; exit 1
fi
PY_VER=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PY_VER" -lt 11 ]; then
    echo -e "${RED}Python 3.11+ gerekli (mevcut: 3.$PY_VER)${NC}"; exit 1
fi

# --- Node.js kontrolu ---
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js 20+ gerekli. https://nodejs.org adresinden indirin.${NC}"; exit 1
fi

# --- Docker kontrolu ---
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker bulunamadi. Redis ve Elasticsearch icin Docker oneriliyor.${NC}"
    echo -e "${YELLOW}https://docs.docker.com/get-docker/ adresinden indirin.${NC}"
fi

# --- .env kontrolu ---
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}.env dosyasi bulunamadi, .env.example kopyalaniyor...${NC}"
    cp .env.example .env
    echo -e "${RED}ONEMLI: .env dosyasini acip Supabase bilgilerinizi doldurun!${NC}"
    echo "  DATABASE_URL=postgresql://postgres.mxzklnsaddxvldwckwir:SIFRENIZ@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    echo "  SUPABASE_URL=https://mxzklnsaddxvldwckwir.supabase.co"
    echo "  SUPABASE_ANON_KEY=eyJ..."
    echo "  SUPABASE_SERVICE_KEY=eyJ..."
    exit 1
fi

echo -e "${GREEN}[1/5] Python sanal ortam olusturuluyor...${NC}"
cd backend
python3 -m venv .venv
source .venv/bin/activate || source .venv/Scripts/activate

echo -e "${GREEN}[2/5] Python bagimliliklar yukleniyor...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo -e "${GREEN}[3/5] Sistem bagimliliklari kontrol ediliyor...${NC}"
if ! command -v tesseract &> /dev/null; then
    echo -e "${YELLOW}Tesseract OCR bulunamadi.${NC}"
    echo "  Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-tur"
    echo "  macOS:         brew install tesseract tesseract-lang"
    echo "  Windows:       https://github.com/UB-Mannheim/tesseract/wiki"
fi

echo -e "${GREEN}[4/5] Frontend bagimliliklar yukleniyor...${NC}"
cd ../frontend/web
npm install --silent

echo -e "${GREEN}[5/5] Redis ve Elasticsearch baslatiliyor (Docker)...${NC}"
cd ../..
if command -v docker &> /dev/null; then
    docker run -d --name aktuel-redis -p 6379:6379 redis:7-alpine 2>/dev/null || \
        docker start aktuel-redis 2>/dev/null || echo "Redis zaten calisiyor."
    docker run -d --name aktuel-es \
        -p 9200:9200 \
        -e "discovery.type=single-node" \
        -e "xpack.security.enabled=false" \
        -e "ES_JAVA_OPTS=-Xms256m -Xmx256m" \
        docker.elastic.co/elasticsearch/elasticsearch:8.16.0 2>/dev/null || \
        docker start aktuel-es 2>/dev/null || echo "Elasticsearch zaten calisiyor."
    echo -e "${GREEN}Redis ve Elasticsearch baslatildi.${NC}"
fi

echo ""
echo -e "${GREEN}=== Kurulum Tamamlandi! ===${NC}"
echo ""
echo "Servisleri baslatmak icin:"
echo ""
echo -e "${YELLOW}# Terminal 1 - FastAPI Backend${NC}"
echo "cd backend && source .venv/bin/activate"
echo "uvicorn app.main:app --reload --port 8000"
echo ""
echo -e "${YELLOW}# Terminal 2 - Celery Worker${NC}"
echo "cd backend && source .venv/bin/activate"
echo "celery -A celeryconfig.celery_app worker --loglevel=info"
echo ""
echo -e "${YELLOW}# Terminal 3 - Next.js Frontend${NC}"
echo "cd frontend/web && npm run dev"
echo ""
echo -e "${YELLOW}# Ilk BIM scraping testini calistir:${NC}"
echo "cd backend && source .venv/bin/activate"
echo "python scripts/test_scraper.py bim"
echo ""
echo -e "${GREEN}API Docs: http://localhost:8000/docs${NC}"
echo -e "${GREEN}Web App:  http://localhost:3000${NC}"
