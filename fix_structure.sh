#!/bin/bash
# Script to fix the project structure
# Run from: /Users/jackcres/Programming/coding-adventure/metatron

set -e  # Exit on error

echo "🔧 Fixing Metatron Project Structure"
echo "======================================"
echo ""

# Check we're in the right place
if [ ! -d "metatron/metatron" ]; then
    echo "❌ Error: Run this script from the repository root"
    echo "   Expected: /Users/jackcres/Programming/coding-adventure/metatron"
    exit 1
fi

echo "📋 Current structure:"
echo "   metatron/"
echo "   └── metatron/"
echo "       ├── pyproject.toml"
echo "       └── metatron/"
echo ""

echo "✨ Target structure:"
echo "   metatron/"
echo "   ├── pyproject.toml"
echo "   └── metatron/"
echo ""

read -p "Continue with restructuring? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting migration..."
echo ""

# Step 1: Move pyproject.toml to root
echo "1️⃣  Moving pyproject.toml to root..."
if [ -f "metatron/pyproject.toml" ]; then
    mv metatron/pyproject.toml ./pyproject.toml
    echo "   ✅ Moved pyproject.toml"
else
    echo "   ⚠️  pyproject.toml not found in metatron/"
fi

# Step 2: Move uv.lock to root
echo "2️⃣  Moving uv.lock to root..."
if [ -f "metatron/uv.lock" ]; then
    mv metatron/uv.lock ./uv.lock
    echo "   ✅ Moved uv.lock"
else
    echo "   ⚠️  uv.lock not found"
fi

# Step 3: Flatten the metatron/metatron structure
echo "3️⃣  Flattening metatron/metatron -> metatron..."

# Create temp directory
mkdir -p temp_metatron

# Move inner metatron contents to temp
if [ -d "metatron/metatron" ]; then
    mv metatron/metatron/* temp_metatron/ 2>/dev/null || true
    mv metatron/metatron/.* temp_metatron/ 2>/dev/null || true
    
    # Remove old directories
    rm -rf metatron/metatron
    
    # Move everything else from outer metatron to temp (like .env, run.py, etc)
    find metatron -maxdepth 1 -mindepth 1 -exec mv {} temp_metatron/ \;
    
    # Remove outer metatron
    rm -rf metatron
    
    # Rename temp to metatron
    mv temp_metatron metatron
    
    echo "   ✅ Flattened structure"
else
    echo "   ⚠️  metatron/metatron not found"
fi

# Step 4: Move .env to root if it exists
echo "4️⃣  Checking for .env file..."
if [ -f "metatron/.env" ]; then
    if [ ! -f ".env" ]; then
        cp metatron/.env ./.env
        echo "   ✅ Copied .env to root"
    else
        echo "   ⚠️  .env already exists at root"
    fi
fi

# Step 5: Create .gitignore if needed
echo "5️⃣  Creating/updating .gitignore..."
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
.venv/
venv/
.uv/

# Environment
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Testing
.pytest_cache/
.coverage
htmlcov/
EOF
echo "   ✅ Created .gitignore"

echo ""
echo "🔄 Installing package in development mode..."
uv sync

echo ""
echo "✅ Structure fixed successfully!"
echo ""
echo "📁 New structure:"
tree -L 2 -I '__pycache__|*.pyc|.venv' . || ls -la

echo ""
echo "🎯 You can now run:"
echo "   uv run metatron api-server"
echo "   uv run metatron voice-worker"
echo "   uv run python test.py"
echo ""
echo "Or install in editable mode:"
echo "   uv pip install -e ."
echo ""

