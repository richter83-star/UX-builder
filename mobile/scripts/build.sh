#!/bin/bash

# Kalshi Agent Mobile Build Script
# This script builds the React Native mobile app for production

set -e

echo "🏗️  Building Kalshi Agent Mobile App..."

# Parse command line arguments
PLATFORM=""
ENVIRONMENT="production"
CLEAN_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 --platform <ios|android> [--env <development|staging|production>] [--clean]"
            echo ""
            echo "Options:"
            echo "  --platform    Platform to build (required): ios or android"
            echo "  --env         Environment (default: production)"
            echo "  --clean       Perform a clean build"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

# Validate platform
if [ -z "$PLATFORM" ]; then
    echo "❌ Platform is required. Use --platform ios or --platform android"
    exit 1
fi

if [ "$PLATFORM" != "ios" ] && [ "$PLATFORM" != "android" ]; then
    echo "❌ Invalid platform. Use ios or android"
    exit 1
fi

echo "📱 Platform: $PLATFORM"
echo "🌍 Environment: $ENVIRONMENT"
echo "🧹 Clean build: $CLEAN_BUILD"

# Clean previous builds if requested
if [ "$CLEAN_BUILD" = true ]; then
    echo "🧹 Cleaning previous builds..."
    if [ "$PLATFORM" = "ios" ]; then
        rm -rf ios/build
        rm -rf ios/Pods
        rm -rf ios/Podfile.lock
    else
        cd android && ./gradlew clean && cd ..
    fi
    echo "✅ Clean completed"
fi

# Install dependencies
echo "📦 Installing dependencies..."
if command -v yarn &> /dev/null; then
    yarn install --frozen-lockfile
else
    npm ci
fi

# Install iOS pods if building for iOS
if [ "$PLATFORM" = "ios" ]; then
    echo "📱 Installing iOS dependencies..."
    cd ios && pod install && cd ..
fi

# Build the app
echo "🏗️  Building app for $PLATFORM..."

case $PLATFORM in
    ios)
        echo "🍎 Building iOS app..."

        # Set environment variables
        export ENVIRONMENT="$ENVIRONMENT"

        # Build for iOS
        if [ "$ENVIRONMENT" = "production" ]; then
            npx react-native run-ios --configuration Release
        else
            npx react-native run-ios --configuration Debug
        fi
        ;;
    android)
        echo "🤖 Building Android app..."

        # Set environment variables
        export ENVIRONMENT="$ENVIRONMENT"

        # Build for Android
        if [ "$ENVIRONMENT" = "production" ]; then
            cd android && ./gradlew assembleRelease && cd ..
            echo "✅ APK built: android/app/build/outputs/apk/release/app-release.apk"
        else
            cd android && ./gradlew assembleDebug && cd ..
            echo "✅ APK built: android/app/build/outputs/apk/debug/app-debug.apk"
        fi
        ;;
esac

echo ""
echo "🎉 Build completed successfully!"
echo ""
echo "Build artifacts:"
if [ "$PLATFORM" = "ios" ]; then
    echo "iOS: Check Xcode Organizer or connected device"
else
    if [ "$ENVIRONMENT" = "production" ]; then
        echo "Android: android/app/build/outputs/apk/release/app-release.apk"
    else
        echo "Android: android/app/build/outputs/apk/debug/app-debug.apk"
    fi
fi