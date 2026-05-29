#!/bin/bash

# IMEI Vision - Development Script

set -e

echo "🔧 IMEI Vision - Development Setup"
echo "===================================="
echo ""

# Backend
echo "📦 Configurando Backend..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate || . venv/Scripts/activate

pip install -r requirements.txt --quiet

# Retornar à raiz
cd ..

echo "✅ Backend configurado"
echo ""

# Frontend
echo "📦 Configurando Frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    npm install
fi

cd ..

echo "✅ Frontend configurado"
echo ""

# Criar .env se não existir
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Arquivo .env criado"
fi

echo ""
echo "🚀 Para iniciar desenvolvimento:"
echo "===================================="
echo ""
echo "Backend:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python -m uvicorn main:app --reload"
echo ""
echo "Frontend (em outro terminal):"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "Banco de dados (opcional, use Docker Compose):"
echo "  docker-compose up db"
echo ""
