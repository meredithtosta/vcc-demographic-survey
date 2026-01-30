#!/bin/bash

echo "🚀 VCC Demographic Survey - Quick Start"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --break-system-packages

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "from app import init_db; init_db()"

if [ $? -ne 0 ]; then
    echo "❌ Failed to initialize database"
    exit 1
fi

echo "✅ Database initialized"
echo ""

# Run tests
echo "🧪 Running system tests..."
python3 test_system.py

if [ $? -ne 0 ]; then
    echo "❌ Tests failed"
    exit 1
fi

echo ""
echo "========================================"
echo "✨ Setup complete!"
echo "========================================"
echo ""
echo "To start the application:"
echo "  python3 app.py"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:5000"
echo ""
echo "⚠️  IMPORTANT: Before deploying to production:"
echo "  1. Set ENCRYPTION_KEY environment variable"
echo "  2. Set SECRET_KEY environment variable"
echo "  3. Switch to PostgreSQL/MySQL"
echo "  4. Enable HTTPS"
echo "  5. Add authentication"
echo ""
echo "See README.md for detailed instructions."
echo ""
