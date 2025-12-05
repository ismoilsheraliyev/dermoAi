#!/bin/bash
echo "🚀 DermAI Bot o'rnatilmoqda..."

# Python ni tekshirish
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 topilmadi!"
    echo "Python3 ni o'rnating: https://www.python.org/downloads/"
    exit 1
fi

# Kutubxonalarni o'rnatish
echo "📦 Kutubxonalar o'rnatilmoqda..."
pip3 install -r requirements.txt

# .env faylni yaratish
if [ ! -f ".env" ]; then
    echo "🔧 .env fayl yaratilmoqda..."
    cp .env.example .env
    echo "✏️ .env faylga BOT_TOKEN ni kiriting!"
fi

echo "✅ Tayyor! Botni ishga tushirish: python3 run.py"