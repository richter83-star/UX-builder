# Kalshi Agent Mobile

A React Native mobile application for the Kalshi Probability Analysis Agent, providing real-time trading, analysis, and portfolio management on iOS and Android devices.

## Features

### Core Features
- **Authentication**: Secure login and registration with JWT tokens
- **Dashboard**: Real-time portfolio overview and trading opportunities
- **Markets**: Browse and search available prediction markets
- **Analysis**: Ensemble analysis with multiple prediction models
- **Trading**: Execute trades with real-time risk assessment
- **Portfolio**: Track positions, performance, and risk metrics
- **Settings**: Customize preferences and risk management

### Mobile-Specific Features
- **Biometric Authentication**: Face ID / Touch ID support
- **Push Notifications**: Real-time alerts for trades and opportunities
- **Offline Mode**: Basic functionality when offline
- **Background Sync**: Automatic data synchronization
- **Dark/Light Theme**: System theme support
- **Real-time Updates**: WebSocket integration for live data

## Architecture

The mobile app follows the same architecture as the web application:

```
src/
├── components/     # Reusable UI components
├── contexts/       # React contexts for state management
├── navigation/     # Navigation configuration
├── screens/        # Screen components
│   ├── auth/      # Authentication screens
│   ├── main/      # Main app screens
│   ├── detail/    # Detail screens
│   └── settings/  # Settings screens
├── services/       # API and business logic services
├── types/          # TypeScript type definitions
├── utils/          # Utility functions
└── assets/         # Images, fonts, etc.
```

## Technology Stack

- **React Native**: Cross-platform mobile development
- **TypeScript**: Type-safe development
- **React Navigation**: Navigation and routing
- **React Native Vector Icons**: Icon library
- **React Native Reanimated**: Animations
- **React Native Gesture Handler**: Touch gestures
- **React Native Charts**: Data visualization
- **AsyncStorage**: Local data persistence
- **WebSocket**: Real-time communication
- **Axios**: HTTP client for API calls

## Getting Started

### Prerequisites

- Node.js 16+
- npm or yarn
- Xcode (for iOS development) - macOS only
- Android Studio (for Android development)
- React Native CLI

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd UX-builder/mobile
   ```

2. **Run the setup script**
   ```bash
   ./scripts/setup.sh
   ```

3. **Start the backend server**
   ```bash
   cd ../backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Run the mobile app**

   For iOS:
   ```bash
   npx react-native run-ios
   ```

   For Android:
   ```bash
   npx react-native run-android
   ```

### Manual Setup

1. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

2. **iOS setup** (macOS only)
   ```bash
   cd ios
   pod install
   cd ..
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the app**
   ```bash
   # iOS
   npx react-native run-ios

   # Android
   npx react-native run-android
   ```

## Development

### Scripts

- `./scripts/setup.sh` - Set up development environment
- `./scripts/build.sh` - Build for production
- `./scripts/test.sh` - Run tests

### Development Commands

```bash
# Start Metro bundler
npx react-native start

# Run on iOS simulator
npx react-native run-ios

# Run on Android emulator
npx react-native run-android

# Run tests
npm test

# Build for production
npm run build

# Lint code
npm run lint

# Type check
npm run type-check
```

### Environment Variables

Create a `.env` file in the root directory:

```env
# API Configuration
API_BASE_URL=http://localhost:8000
WEBSOCKET_URL=ws://localhost:8000

# Development Configuration
DEV_MODE=true
DEBUG_MODE=true

# Optional: Kalshi API Keys
KALSHI_API_KEY=your_api_key_here
KALSHI_PRIVATE_KEY=your_private_key_here
```

## Building for Production

### iOS

1. **Build the app**
   ```bash
   ./scripts/build.sh --platform ios --env production
   ```

2. **Archive in Xcode**
   - Open `ios/KalshiAgent.xcworkspace`
   - Select device "Any iOS Device"
   - Product → Archive

3. **Upload to App Store**
   - Use Xcode Organizer to upload to App Store Connect

### Android

1. **Generate signing key**
   ```bash
   keytool -genkey -v -keystore kalshi-agent-release.keystore -alias kalshi-agent -keyalg RSA -keysize 2048 -validity 10000
   ```

2. **Configure signing**
   - Edit `android/app/build.gradle`
   - Add signing configuration

3. **Build the app**
   ```bash
   ./scripts/build.sh --platform android --env production
   ```

4. **Upload to Google Play**
   - Upload `android/app/build/outputs/apk/release/app-release.apk` to Google Play Console

## Testing

### Unit Tests
```bash
npm test -- --type unit
```

### Integration Tests
```bash
npm test -- --type integration
```

### End-to-End Tests
```bash
npm test -- --type e2e
```

### Coverage
```bash
npm test -- --coverage
```

## Troubleshooting

### Common Issues

1. **Metro bundler issues**
   ```bash
   npx react-native start --reset-cache
   ```

2. **iOS build issues**
   ```bash
   cd ios && pod install && cd ..
   ```

3. **Android build issues**
   ```bash
   cd android && ./gradlew clean && cd ..
   ```

4. **Node modules issues**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

### Getting Help

- Check the [React Native documentation](https://reactnative.dev/docs/getting-started)
- Review the [troubleshooting guide](https://reactnative.dev/docs/troubleshooting)
- Open an issue in the project repository

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Contact the development team