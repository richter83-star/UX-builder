#!/bin/bash

# Kalshi Agent Mobile Setup Script
# This script sets up the React Native mobile development environment

set -e

echo "🚀 Setting up Kalshi Agent Mobile Development Environment..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js v16 or higher."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js version $NODE_VERSION is not supported. Please install Node.js v16 or higher."
    exit 1
fi

echo "✅ Node.js v$(node -v) detected"

# Check if npm or yarn is available
if command -v yarn &> /dev/null; then
    PACKAGE_MANAGER="yarn"
    echo "✅ Yarn detected"
elif command -v npm &> /dev/null; then
    PACKAGE_MANAGER="npm"
    echo "✅ npm detected"
else
    echo "❌ Neither npm nor yarn is installed. Please install one of them."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
if [ "$PACKAGE_MANAGER" = "yarn" ]; then
    yarn install
else
    npm install
fi

# Install iOS dependencies (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v xcodebuild &> /dev/null; then
        echo "📱 Installing iOS dependencies..."
        cd ios && pod install && cd ..
        echo "✅ iOS dependencies installed"
    else
        echo "⚠️  Xcode is not installed. iOS development will not be available."
    fi
fi

# Check for Android development requirements
if command -v java &> /dev/null; then
    echo "✅ Java detected"
else
    echo "⚠️  Java is not installed. Android development may not work properly."
fi

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cat > .env << EOF
# Kalshi Agent Mobile Environment Variables

# API Configuration
API_BASE_URL=http://localhost:8000
WEBSOCKET_URL=ws://localhost:8000

# Development Configuration
DEV_MODE=true
DEBUG_MODE=true

# Optional: Kalshi API Keys (for development)
# KALSHI_API_KEY=your_api_key_here
# KALSHI_PRIVATE_KEY=your_private_key_here

# Optional: Analytics
# ANALYTICS_API_KEY=your_analytics_key_here
EOF
    echo "✅ Environment file created"
fi

# Setup complete
echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Update the .env file with your configuration"
echo "2. Start the backend server: cd ../backend && python -m uvicorn app.main:app --reload"
echo "3. Run the mobile app:"
echo "   - iOS: npx react-native run-ios"
echo "   - Android: npx react-native run-android"
echo ""
echo "For more information, see the mobile README.md file."