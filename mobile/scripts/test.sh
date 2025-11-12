#!/bin/bash

# Kalshi Agent Mobile Test Script
# This script runs tests for the React Native mobile app

set -e

echo "🧪 Running Kalshi Agent Mobile Tests..."

# Parse command line arguments
TEST_TYPE="all"
COVERAGE=false
WATCH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            TEST_TYPE="$2"
            shift 2
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --watch)
            WATCH=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--type <unit|integration|e2e|all>] [--coverage] [--watch]"
            echo ""
            echo "Options:"
            echo "  --type     Type of tests to run (default: all)"
            echo "  --coverage Generate coverage report"
            echo "  --watch    Run tests in watch mode"
            echo "  --help     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo "🔍 Test type: $TEST_TYPE"
echo "📊 Coverage: $COVERAGE"
echo "👀 Watch mode: $WATCH"

# Install dependencies
echo "📦 Installing dependencies..."
if command -v yarn &> /dev/null; then
    yarn install
else
    npm install
fi

# Prepare Jest arguments
JEST_ARGS=""

if [ "$COVERAGE" = true ]; then
    JEST_ARGS="$JEST_ARGS --coverage"
fi

if [ "$WATCH" = true ]; then
    JEST_ARGS="$JEST_ARGS --watch"
fi

# Run tests based on type
case $TEST_TYPE in
    unit)
        echo "🧪 Running unit tests..."
        npx jest $JEST_ARGS --testPathPattern=__tests__/unit
        ;;
    integration)
        echo "🔗 Running integration tests..."
        npx jest $JEST_ARGS --testPathPattern=__tests__/integration
        ;;
    e2e)
        echo "🎭 Running end-to-end tests..."
        if [ "$WATCH" = true ]; then
            echo "⚠️  Watch mode is not supported for e2e tests"
            JEST_ARGS=$(echo $JEST_ARGS | sed 's/--watch//')
        fi
        npx detox test $JEST_ARGS
        ;;
    all)
        echo "🧪 Running all tests..."
        npx jest $JEST_ARGS
        ;;
    *)
        echo "❌ Invalid test type: $TEST_TYPE"
        echo "Valid types: unit, integration, e2e, all"
        exit 1
        ;;
esac

echo ""
echo "✅ Tests completed successfully!"

if [ "$COVERAGE" = true ]; then
    echo ""
    echo "📊 Coverage report generated in coverage/ directory"
    echo "Open coverage/lcov-report/index.html in your browser to view the report"
fi