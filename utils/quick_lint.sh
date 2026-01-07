#!/bin/bash
# Quick lint check - run after every change
# OPTIMIZED: Batches pylint for 10x speed improvement!
# Usage: ./utils/quick_lint.sh [--fix]

cd "$(dirname "$0")/.." || exit 1

# Auto-fix trailing whitespace if --fix flag is provided
if [[ "$1" == "--fix" ]]; then
    echo "🔧 Auto-fixing trailing whitespace..."
    find custom_components/kidschores -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} +
    find tests -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} +
    echo "✓ Trailing whitespace fixed"
    echo ""
fi

# Run the comprehensive linting check on both integration and tests
echo "🔍 Running comprehensive lint check..."
echo ""
python utils/lint_check.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ Ready to commit!"
else
    echo ""
    echo "❌ Fix issues before committing"
    echo ""
    echo "Quick fixes:"
    echo "  ./utils/quick_lint.sh --fix    # Auto-fix trailing whitespace"
    echo "  # Then manually fix remaining issues"
fi

exit $exit_code
