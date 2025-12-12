#!/bin/bash
# Sprint 3.4 Task 4 — One-command local validation script
# Runs pytest, PII scan, and basic linting for development confidence

set -e  # Exit on first error

echo "🧪 Sprint 3.4 Validation Suite"
echo "=============================="
echo ""

# 1. Run pytest integration tests
echo "1️⃣  Running pytest integration tests..."
if command -v pytest &> /dev/null; then
    pytest tests/test_sprint_3_4_integration.py -v --asyncio-mode=auto || {
        echo "❌ Integration tests failed"
        exit 1
    }
    echo "✅ Integration tests passed"
else
    echo "⚠️  pytest not found - skipping tests"
fi
echo ""

# 2. Run PII/secrets scan
echo "2️⃣  Running PII/secrets scan..."

# Check for detect-secrets
if command -v detect-secrets &> /dev/null; then
    detect-secrets scan > /tmp/ds_scan.json 2>/dev/null || true
    if grep -qi "true" /tmp/ds_scan.json; then
        echo "⚠️  detect-secrets found potential secrets - review manually"
        cat /tmp/ds_scan.json
    else
        echo "✅ detect-secrets: no secrets detected"
    fi
else
    echo "⚠️  detect-secrets not installed - install with: pip install detect-secrets"
fi

# Check for TruffleHog
if command -v trufflehog &> /dev/null; then
    trufflehog filesystem . --only-verified --fail --exclude-paths trufflehog_ignore.txt 2>/dev/null && {
        echo "✅ TruffleHog: no verified secrets found"
    } || {
        echo "⚠️  TruffleHog found potential secrets - review manually"
    }
else
    echo "⚠️  TruffleHog not installed - install with: brew install trufflesecurity/trufflehog/trufflehog"
fi

# Check for git-secrets
if command -v git &> /dev/null && git secrets --scan 2>/dev/null; then
    echo "✅ git-secrets: no secrets detected"
else
    echo "⚠️  git-secrets not configured - install with: brew install git-secrets"
fi
echo ""

# 3. Basic Python linting
echo "3️⃣  Running basic linting checks..."

# Check for common Python syntax errors
if command -v python3 &> /dev/null; then
    echo "  Checking Python syntax..."
    find . -name "*.py" \
        -not -path "./venv/*" \
        -not -path "./.venv/*" \
        -not -path "./audio_organizer_source/*" \
        -not -path "./node_modules/*" | while read file; do
        python3 -m py_compile "$file" 2>/dev/null || {
            echo "  ❌ Syntax error in: $file"
            exit 1
        }
    done
    echo "✅ Python syntax check passed"
else
    echo "⚠️  Python 3 not found"
fi
echo ""

# 4. Summary
echo "=============================="
echo "🎉 All validation checks completed!"
echo ""
echo "Next steps:"
echo "  - Review any warnings above"
echo "  - Commit changes: git add . && git commit -m 'your message'"
echo "  - Push safely: git push (pre-push hook will run automatically)"
echo ""
