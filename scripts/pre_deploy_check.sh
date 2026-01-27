#!/bin/bash
# PRE-DEPLOYMENT CHECKLIST
# Run this BEFORE every deployment to catch recurring issues
# Created: Jan 27, 2026

echo "============================================"
echo "  PRE-DEPLOYMENT CHECKLIST"
echo "============================================"
echo ""

ERRORS=0
WARNINGS=0

# 1. Check .gitignore corruption (CRITICAL - has happened multiple times)
echo "1. Checking .gitignore for corruption..."
if grep -q "^\-e\|^\*\.env$\|^\*\.env\.\*$" /app/.gitignore 2>/dev/null; then
    echo "   ❌ CRITICAL: .gitignore is corrupted with *.env entries or -e flags!"
    echo "   FIX: Remove duplicate *.env and -e entries from .gitignore"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ .gitignore is clean"
fi

# 2. Check .env files exist
echo ""
echo "2. Checking .env files..."
if [ -f /app/backend/.env ]; then
    echo "   ✅ backend/.env exists"
else
    echo "   ❌ CRITICAL: backend/.env missing!"
    ERRORS=$((ERRORS + 1))
fi

if [ -f /app/frontend/.env ]; then
    echo "   ✅ frontend/.env exists"
else
    echo "   ❌ CRITICAL: frontend/.env missing!"
    ERRORS=$((ERRORS + 1))
fi

# 3. Check required env vars
echo ""
echo "3. Checking required environment variables..."
for key in MONGO_URL DB_NAME JWT_SECRET; do
    if grep -q "^$key=" /app/backend/.env 2>/dev/null; then
        echo "   ✅ $key is set"
    else
        echo "   ❌ CRITICAL: $key missing from backend/.env"
        ERRORS=$((ERRORS + 1))
    fi
done

if grep -q "^REACT_APP_BACKEND_URL=" /app/frontend/.env 2>/dev/null; then
    echo "   ✅ REACT_APP_BACKEND_URL is set"
else
    echo "   ❌ CRITICAL: REACT_APP_BACKEND_URL missing from frontend/.env"
    ERRORS=$((ERRORS + 1))
fi

# 4. Check requirements.txt exists and has key packages
echo ""
echo "4. Checking requirements.txt..."
if [ -f /app/backend/requirements.txt ]; then
    for pkg in fastapi uvicorn motor pydantic; do
        if grep -qi "^$pkg" /app/backend/requirements.txt; then
            echo "   ✅ $pkg in requirements.txt"
        else
            echo "   ⚠️ WARNING: $pkg might be missing from requirements.txt"
            WARNINGS=$((WARNINGS + 1))
        fi
    done
else
    echo "   ❌ CRITICAL: requirements.txt missing!"
    ERRORS=$((ERRORS + 1))
fi

# 5. Check package.json exists
echo ""
echo "5. Checking package.json..."
if [ -f /app/frontend/package.json ]; then
    echo "   ✅ package.json exists"
else
    echo "   ❌ CRITICAL: package.json missing!"
    ERRORS=$((ERRORS + 1))
fi

# 6. Check for syntax errors in Python files
echo ""
echo "6. Checking Python syntax..."
SYNTAX_ERRORS=$(find /app/backend -name "*.py" -exec python3 -m py_compile {} \; 2>&1 | grep -c "Error")
if [ "$SYNTAX_ERRORS" -eq 0 ]; then
    echo "   ✅ No Python syntax errors"
else
    echo "   ❌ CRITICAL: Python syntax errors found!"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "============================================"
echo "  SUMMARY"
echo "============================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ All critical checks passed!"
    if [ $WARNINGS -gt 0 ]; then
        echo "⚠️  $WARNINGS warning(s) - review recommended"
    fi
    echo ""
    echo "Ready for deployment."
    exit 0
else
    echo "❌ $ERRORS critical error(s) found!"
    echo "⚠️  $WARNINGS warning(s)"
    echo ""
    echo "FIX ERRORS BEFORE DEPLOYING!"
    exit 1
fi
