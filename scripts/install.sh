#!/bin/bash

# IMEI Vision - Quick Start Script
# Este script instala e configura a aplicação completa

set -e

echo "🚀 IMEI Vision - Quick Installation"
echo "===================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não está instalado${NC}"
    echo "Visite https://docs.docker.com/install para instalar"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose não está instalado${NC}"
    echo "Visite https://docs.docker.com/compose/install para instalar"
    exit 1
fi

echo -e "${GREEN}✅ Docker e Docker Compose detectados${NC}"
echo ""

# Criar arquivo .env
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    
    # Gerar SECRET_KEY
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/your-secret-key-change-in-production-min-32-chars/$SECRET_KEY/" .env
    
    echo -e "${GREEN}✅ Arquivo .env criado${NC}"
else
    echo -e "${YELLOW}⚠️  Arquivo .env já existe${NC}"
fi

echo ""
echo "🐳 Iniciando containers Docker..."
echo "===================================="

# Build e up
docker-compose down 2>/dev/null || true
docker-compose build
docker-compose up -d

# Aguardar serviços
echo ""
echo "⏳ Aguardando serviços iniciarem..."
sleep 10

# Verificar saúde
echo ""
echo "🔍 Verificando saúde da aplicação..."
echo "===================================="

# Verificar banco de dados
if docker exec imei_vision_db pg_isready -U imei_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL rodando${NC}"
else
    echo -e "${RED}❌ PostgreSQL não respondendo${NC}"
fi

# Aguardar backend
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}✅ Backend rodando${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend não respondendo${NC}"
    fi
    sleep 1
done

# Aguardar frontend
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null; then
        echo -e "${GREEN}✅ Frontend rodando${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Frontend não respondendo${NC}"
    fi
    sleep 1
done

echo ""
echo "🎉 Instalação Completa!"
echo "===================================="
echo ""
echo -e "${GREEN}URLs disponíveis:${NC}"
echo "  • Frontend:     http://localhost:3000"
echo "  • Backend:      http://localhost:8000"
echo "  • API Docs:     http://localhost:8000/docs"
echo "  • Health Check: http://localhost:8000/health"
echo ""
echo -e "${GREEN}Usuário padrão (para criar):${NC}"
echo "  • Email:    teste@exemplo.com"
echo "  • Senha:    SenhaForte123!"
echo ""
echo "Para parar: docker-compose down"
echo "Para logs:  docker-compose logs -f"
echo ""
