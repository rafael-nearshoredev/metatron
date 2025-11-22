# Project Structure Fix Guide

## Current Problem

Your project has a triple-nested structure that confuses Python tooling:

```
metatron/                          # Repo root
├── metatron/                      # Outer package folder
│   ├── pyproject.toml            # ❌ Should be at root
│   ├── uv.lock                   # ❌ Should be at root
│   └── metatron/                 # ❌ Inner package (triple nesting!)
│       ├── __init__.py
│       ├── api/
│       ├── cli/
│       └── ...
```

## Target Structure (Standard Python Project)

```
metatron/                          # Repo root
├── pyproject.toml                # ✅ At root
├── uv.lock                       # ✅ At root
├── .env                          # ✅ At root
├── test.py                       # ✅ At root
├── README.md
├── metatron/                     # ✅ Source package
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── closer.py
│   │   ├── voice_agent.py
│   │   └── elevenlabs_tts.py
│   ├── utils/
│   └── files/
├── tests/
└── frontend/
```

## Solution Options

### Option 1: Automated Script (Recommended)

Run the provided script:

```bash
cd /Users/jackcres/Programming/coding-adventure/metatron
chmod +x fix_structure.sh
./fix_structure.sh
```

This will:
1. Move `pyproject.toml` to root
2. Move `uv.lock` to root
3. Flatten the triple nesting
4. Run `uv sync` to reinstall
5. Create proper `.gitignore`

### Option 2: Manual Steps

If you prefer to do it manually:

#### Step 1: Backup First
```bash
cd /Users/jackcres/Programming/coding-adventure/metatron
cp -r metatron metatron_backup
```

#### Step 2: Move Configuration Files
```bash
# Move pyproject.toml to root
mv metatron/pyproject.toml ./pyproject.toml

# Move uv.lock to root
mv metatron/uv.lock ./uv.lock

# Copy .env to root (if exists)
if [ -f metatron/.env ]; then
    cp metatron/.env ./.env
fi
```

#### Step 3: Flatten Directory Structure
```bash
# Create temporary directory
mkdir temp_metatron

# Move inner metatron contents to temp
mv metatron/metatron/* temp_metatron/

# Move other files from outer metatron
find metatron -maxdepth 1 -type f -exec mv {} temp_metatron/ \;

# Remove old structure
rm -rf metatron

# Rename temp to metatron
mv temp_metatron metatron
```

#### Step 4: Reinstall Package
```bash
# Sync dependencies
uv sync

# Or install in editable mode
uv pip install -e .
```

#### Step 5: Update pyproject.toml (if needed)

Ensure `pyproject.toml` has correct package path:

```toml
[tool.hatch.build.targets.wheel]
packages = ["metatron"]  # ✅ Should point to metatron/ folder
```

## Verification

After restructuring, verify it works:

```bash
# Check structure
ls -la

# Should show:
# - pyproject.toml (at root)
# - metatron/ (package folder)
# - test.py (at root)
# - .env (at root)

# Test commands
uv run metatron api-server --help
uv run metatron voice-worker --help
uv run python test.py
```

## Why This Structure?

### ✅ Benefits

1. **Standard Layout**: Follows Python packaging best practices
2. **Tool Compatibility**: Works with `uv`, `pip`, `poetry`, etc.
3. **Clear Separation**: Root for config, `metatron/` for code
4. **Easier Imports**: Clean import paths (`from metatron.api import ...`)
5. **Better Testing**: Test files can import package easily

### 📚 References

- [Python Packaging User Guide](https://packaging.python.org/)
- [UV Project Structure](https://docs.astral.sh/uv/)
- [Structuring Your Project (Hitchhiker's Guide)](https://docs.python-guide.org/writing/structure/)

## Common Issues After Restructuring

### Issue: "No module named 'metatron'"

**Solution**: Run `uv sync` or `uv pip install -e .`

### Issue: Import errors

**Solution**: Make sure all `__init__.py` files exist in package directories

### Issue: Config not loading

**Solution**: Move `.env` file to repository root

## Running After Fix

Once restructured, you can run:

### API Server
```bash
# Method 1: CLI command
uv run metatron api-server

# Method 2: Python module
uv run python -m metatron.main

# Method 3: Uvicorn direct
uv run uvicorn metatron.main:app --host 0.0.0.0 --port 5885
```

### Voice Worker
```bash
# Method 1: CLI command
uv run metatron voice-worker

# Method 2: Python module
uv run python -m metatron.agents.voice_agent
```

### Test Script
```bash
uv run python test.py
```

## Need Help?

If you encounter issues:

1. Check that `pyproject.toml` is at repo root
2. Verify `metatron/` folder exists with `__init__.py`
3. Run `uv sync` to ensure dependencies are installed
4. Check `.env` file is at root with proper values
5. Look for error messages in terminal output

## Rollback

If something goes wrong:

```bash
# Remove new structure
rm -rf metatron pyproject.toml uv.lock

# Restore backup
mv metatron_backup metatron

# You're back to the original state
```

