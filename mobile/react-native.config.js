module.exports = {
  dependencies: {
    'react-native-vector-icons': {
      platforms: {
        ios: {
          sourceDir: '../node_modules/react-native-vector-icons/Fonts',
          project: 'ios/KalshiAgent.xcodeproj',
        },
      },
    },
  },
  assets: ['./src/assets/fonts/'],
};