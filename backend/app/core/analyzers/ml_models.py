import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import os
from loguru import logger

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("TensorFlow not available - LSTM models will be disabled")

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("Statsmodels not available - ARIMA models will be disabled")

from app.core.kalshi_client import kalshi_client
from app.models.enums import MarketCategory, AnalyzerType

class MLModelsAnalyzer:
    """
    Machine learning analysis engine that uses multiple ML models to predict
    market outcomes based on historical data patterns and features.
    """

    def __init__(self):
        self.model_save_dir = "saved_models"
        os.makedirs(self.model_save_dir, exist_ok=True)

        # Model parameters
        self.random_forest_params = {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'random_state': 42
        }

        self.gradient_boosting_params = {
            'n_estimators': 100,
            'learning_rate': 0.1,
            'max_depth': 6,
            'random_state': 42
        }

        self.lstm_params = {
            'sequence_length': 20,
            'epochs': 50,
            'batch_size': 32,
            'validation_split': 0.2
        }

        self.arima_params = {
            'max_p': 5,
            'max_d': 2,
            'max_q': 5
        }

        # Feature engineering parameters
        self.feature_window = 30
        self.target_horizon = 7  # Predict 7 days ahead

        # Model storage
        self.models = {}
        self.scalers = {}

    def _create_features(self, prices: List[float], volumes: List[float] = None) -> pd.DataFrame:
        """Create features for machine learning models"""
        try:
            df = pd.DataFrame({'price': prices})

            if volumes:
                df['volume'] = volumes

            # Price-based features
            df['returns'] = df['price'].pct_change()
            df['log_returns'] = np.log(df['price']).diff()
            df['price_change'] = df['price'].diff()

            # Moving averages
            for window in [5, 10, 20, 50]:
                if len(df) >= window:
                    df[f'ma_{window}'] = df['price'].rolling(window=window).mean()
                    df[f'price_vs_ma_{window}'] = df['price'] / df[f'ma_{window}'] - 1

            # Volatility features
            df['volatility_5'] = df['returns'].rolling(window=5).std()
            df['volatility_10'] = df['returns'].rolling(window=10).std()
            df['volatility_20'] = df['returns'].rolling(window=20).std()

            # Momentum features
            for period in [1, 3, 7, 14]:
                if len(df) >= period:
                    df[f'momentum_{period}'] = df['price'].pct_change(period)

            # RSI
            if len(df) >= 14:
                delta = df['price'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))

            # Bollinger Bands
            if len(df) >= 20:
                df['bb_middle'] = df['price'].rolling(window=20).mean()
                df['bb_std'] = df['price'].rolling(window=20).std()
                df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
                df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
                df['bb_position'] = (df['price'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

            # Lag features
            for lag in [1, 2, 3, 5, 10]:
                if len(df) > lag:
                    df[f'price_lag_{lag}'] = df['price'].shift(lag)
                    df[f'return_lag_{lag}'] = df['returns'].shift(lag)

            # Volume features (if available)
            if volumes:
                df['volume_ma_5'] = df['volume'].rolling(window=5).mean()
                df['volume_ma_10'] = df['volume'].rolling(window=10).mean()
                df['price_volume'] = df['price'] * df['volume']
                df['volume_ratio'] = df['volume'] / df['volume_ma_5']

            # Remove rows with NaN values
            df = df.dropna()

            return df

        except Exception as e:
            logger.error(f"Error creating features: {str(e)}")
            return pd.DataFrame()

    def _create_classification_target(self, prices: List[float]) -> np.ndarray:
        """Create binary classification target (price up/down)"""
        try:
            if len(prices) <= self.target_horizon:
                return np.array([])

            target = []
            for i in range(len(prices) - self.target_horizon):
                current_price = prices[i]
                future_price = prices[i + self.target_horizon]

                if future_price > current_price:
                    target.append(1)  # Price goes up
                else:
                    target.append(0)  # Price goes down or stays same

            return np.array(target)

        except Exception as e:
            logger.error(f"Error creating classification target: {str(e)}")
            return np.array([])

    def _create_regression_target(self, prices: List[float]) -> np.ndarray:
        """Create regression target (future price change)"""
        try:
            if len(prices) <= self.target_horizon:
                return np.array([])

            target = []
            for i in range(len(prices) - self.target_horizon):
                current_price = prices[i]
                future_price = prices[i + self.target_horizon]

                if current_price != 0:
                    price_change = (future_price - current_price) / current_price * 100
                    target.append(price_change)
                else:
                    target.append(0.0)

            return np.array(target)

        except Exception as e:
            logger.error(f"Error creating regression target: {str(e)}")
            return np.array([])

    def _train_random_forest(self, X: pd.DataFrame, y: np.ndarray) -> Tuple[Any, float]:
        """Train Random Forest classifier"""
        try:
            # Remove any remaining NaN values
            X_clean = X.dropna()
            y_clean = y[:len(X_clean)]

            if len(X_clean) < 10:
                return None, 0.0

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_clean, y_clean, test_size=0.2, random_state=42
            )

            # Train model
            model = RandomForestClassifier(**self.random_forest_params)
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)

            # Cross-validation
            cv_scores = cross_val_score(model, X_clean, y_clean, cv=5, scoring='accuracy')
            cv_accuracy = np.mean(cv_scores)

            logger.info(f"Random Forest trained - Test accuracy: {accuracy:.3f}, CV accuracy: {cv_accuracy:.3f}")

            return model, cv_accuracy

        except Exception as e:
            logger.error(f"Error training Random Forest: {str(e)}")
            return None, 0.0

    def _train_gradient_boosting(self, X: pd.DataFrame, y: np.ndarray) -> Tuple[Any, float]:
        """Train Gradient Boosting classifier"""
        try:
            # Remove any remaining NaN values
            X_clean = X.dropna()
            y_clean = y[:len(X_clean)]

            if len(X_clean) < 10:
                return None, 0.0

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_clean, y_clean, test_size=0.2, random_state=42
            )

            # Train model
            model = GradientBoostingClassifier(**self.gradient_boosting_params)
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)

            # Cross-validation
            cv_scores = cross_val_score(model, X_clean, y_clean, cv=5, scoring='accuracy')
            cv_accuracy = np.mean(cv_scores)

            logger.info(f"Gradient Boosting trained - Test accuracy: {accuracy:.3f}, CV accuracy: {cv_accuracy:.3f}")

            return model, cv_accuracy

        except Exception as e:
            logger.error(f"Error training Gradient Boosting: {str(e)}")
            return None, 0.0

    def _train_lstm(self, X: pd.DataFrame, y: np.ndarray) -> Tuple[Any, float]:
        """Train LSTM neural network for time series prediction"""
        if not TENSORFLOW_AVAILABLE:
            return None, 0.0

        try:
            # Prepare sequences for LSTM
            sequence_length = self.lstm_params['sequence_length']

            if len(X) < sequence_length + 10:
                return None, 0.0

            # Select numerical features only
            feature_cols = X.select_dtypes(include=[np.number]).columns
            X_numeric = X[feature_cols].values

            # Create sequences
            X_sequences, y_sequences = [], []
            for i in range(sequence_length, len(X_numeric)):
                X_sequences.append(X_numeric[i-sequence_length:i])
                y_sequences.append(y[i-1])  # Target aligns with sequence end

            X_sequences = np.array(X_sequences)
            y_sequences = np.array(y_sequences)

            if len(X_sequences) < 20:
                return None, 0.0

            # Split data
            split_idx = int(len(X_sequences) * 0.8)
            X_train, X_test = X_sequences[:split_idx], X_sequences[split_idx:]
            y_train, y_test = y_sequences[:split_idx], y_sequences[split_idx:]

            # Build LSTM model
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(sequence_length, X_numeric.shape[1])),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25, activation='relu'),
                Dense(1, activation='sigmoid')
            ])

            model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy'])

            # Train with early stopping
            early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

            history = model.fit(
                X_train, y_train,
                epochs=self.lstm_params['epochs'],
                batch_size=self.lstm_params['batch_size'],
                validation_split=self.lstm_params['validation_split'],
                callbacks=[early_stopping],
                verbose=0
            )

            # Evaluate
            _, accuracy = model.evaluate(X_test, y_test, verbose=0)

            logger.info(f"LSTM trained - Test accuracy: {accuracy:.3f}")

            return model, accuracy

        except Exception as e:
            logger.error(f"Error training LSTM: {str(e)}")
            return None, 0.0

    def _train_arima(self, prices: List[float]) -> Tuple[Any, float]:
        """Train ARIMA model for time series forecasting"""
        if not STATSMODELS_AVAILABLE:
            return None, 0.0

        try:
            if len(prices) < 50:
                return None, 0.0

            # Check for stationarity
            result = adfuller(prices)
            is_stationary = result[1] < 0.05

            # Find best ARIMA parameters using grid search
            best_aic = float('inf')
            best_model = None
            best_order = (1, 1, 1)

            max_p, max_d, max_q = self.arima_params['max_p'], self.arima_params['max_d'], self.arima_params['max_q']

            for p in range(max_p + 1):
                for d in range(max_d + 1):
                    for q in range(max_q + 1):
                        try:
                            model = ARIMA(prices, order=(p, d, q))
                            fitted = model.fit()

                            if fitted.aic < best_aic:
                                best_aic = fitted.aic
                                best_model = fitted
                                best_order = (p, d, q)

                        except Exception:
                            continue

            if best_model is None:
                # Fallback to simple ARIMA(1,1,1)
                try:
                    best_model = ARIMA(prices, order=(1, 1, 1)).fit()
                    best_order = (1, 1, 1)
                except Exception as e:
                    logger.error(f"Error training fallback ARIMA: {str(e)}")
                    return None, 0.0

            # Calculate forecast accuracy using in-sample predictions
            predictions = best_model.fittedvalues
            actuals = prices[-len(predictions):]

            if len(predictions) > 0 and len(actuals) > 0:
                mae = np.mean(np.abs(predictions - actuals))
                rmse = np.sqrt(np.mean((predictions - actuals) ** 2))

                # Simple accuracy metric (within 5% of actual price)
                accuracy = np.mean(np.abs(predictions - actuals) / actuals < 0.05) * 100
            else:
                accuracy = 0.0

            logger.info(f"ARIMA({best_order[0]},{best_order[1]},{best_order[2]}) trained - Accuracy: {accuracy:.1f}%")

            return best_model, accuracy

        except Exception as e:
            logger.error(f"Error training ARIMA: {str(e)}")
            return None, 0.0

    def _predict_with_model(self, model: Any, features: pd.DataFrame, model_type: str) -> Tuple[float, float]:
        """Make prediction with a trained model"""
        try:
            if model is None or features.empty:
                return 0.0, 0.0

            if model_type in ['random_forest', 'gradient_boosting']:
                # Get probability predictions
                prediction_proba = model.predict_proba(features.tail(1))[0]
                prediction = prediction_proba[1]  # Probability of class 1 (price up)
                confidence = max(prediction_proba) * 100

            elif model_type == 'lstm' and TENSORFLOW_AVAILABLE:
                # Prepare sequence for LSTM
                sequence_length = self.lstm_params['sequence_length']

                if len(features) >= sequence_length:
                    feature_cols = features.select_dtypes(include=[np.number]).columns
                    sequence = features[feature_cols].tail(sequence_length).values
                    sequence = np.array([sequence])  # Add batch dimension

                    prediction_proba = model.predict(sequence, verbose=0)[0][0]
                    prediction = float(prediction_proba)
                    confidence = max(prediction, 1 - prediction) * 100
                else:
                    return 0.0, 0.0

            elif model_type == 'arima' and STATSMODELS_AVAILABLE:
                # Make forecast with ARIMA
                forecast = model.forecast(steps=1)
                current_price = features['price'].iloc[-1] if 'price' in features.columns else 1.0

                if current_price > 0:
                    prediction = (forecast[0] - current_price) / current_price
                    # Convert to probability (simplified)
                    prediction_prob = 1 / (1 + np.exp(-prediction * 10))  # Sigmoid
                    prediction = prediction_prob
                    confidence = 60.0  # Fixed confidence for ARIMA
                else:
                    return 0.0, 0.0

            else:
                return 0.0, 0.0

            # Convert prediction to -100 to 100 scale
            prediction_scaled = (prediction - 0.5) * 200

            return prediction_scaled, confidence

        except Exception as e:
            logger.error(f"Error making prediction with {model_type}: {str(e)}")
            return 0.0, 0.0

    async def train_models(self, market_id: str, historical_data: List[Dict]) -> Dict[str, Any]:
        """Train all ML models for a specific market"""
        try:
            logger.info(f"Training ML models for market {market_id}")

            # Extract price and volume data
            prices = [float(point.get('price', 0)) for point in historical_data if point.get('price')]
            volumes = [float(point.get('volume', 0)) for point in historical_data if point.get('volume')]

            if len(prices) < 50:
                logger.warning(f"Insufficient data for training models: {len(prices)} points")
                return {}

            # Create features
            features_df = self._create_features(prices, volumes)
            if features_df.empty:
                logger.warning("No features created for training")
                return {}

            # Create targets
            classification_target = self._create_classification_target(prices)
            regression_target = self._create_regression_target(prices)

            # Ensure features and targets have matching lengths
            min_length = min(len(features_df), len(classification_target), len(regression_target))
            if min_length < 20:
                logger.warning(f"Insufficient samples after feature creation: {min_length}")
                return {}

            features_aligned = features_df.iloc[:min_length]
            classification_target_aligned = classification_target[:min_length]

            # Train models
            models = {}
            model_accuracies = {}

            # Random Forest
            rf_model, rf_accuracy = self._train_random_forest(features_aligned, classification_target_aligned)
            if rf_model is not None:
                models['random_forest'] = rf_model
                model_accuracies['random_forest'] = rf_accuracy

            # Gradient Boosting
            gb_model, gb_accuracy = self._train_gradient_boosting(features_aligned, classification_target_aligned)
            if gb_model is not None:
                models['gradient_boosting'] = gb_model
                model_accuracies['gradient_boosting'] = gb_accuracy

            # LSTM (if TensorFlow available)
            lstm_model, lstm_accuracy = self._train_lstm(features_aligned, classification_target_aligned)
            if lstm_model is not None:
                models['lstm'] = lstm_model
                model_accuracies['lstm'] = lstm_accuracy

            # ARIMA (if statsmodels available)
            arima_model, arima_accuracy = self._train_arima(prices)
            if arima_model is not None:
                models['arima'] = arima_model
                model_accuracies['arima'] = arima_accuracy

            # Save models for this market
            market_models_dir = os.path.join(self.model_save_dir, market_id.replace('-', '_'))
            os.makedirs(market_models_dir, exist_ok=True)

            for model_name, model in models.items():
                model_path = os.path.join(market_models_dir, f"{model_name}.joblib")
                joblib.dump(model, model_path)

            logger.info(f"Trained {len(models)} models for market {market_id}")

            return {
                'models_trained': list(models.keys()),
                'model_accuracies': model_accuracies,
                'training_samples': min_length,
                'features_count': len(features_aligned.columns)
            }

        except Exception as e:
            logger.error(f"Error training models for market {market_id}: {str(e)}")
            return {}

    async def predict_with_models(self, market_id: str, recent_data: List[Dict]) -> Dict[str, Any]:
        """Make predictions using trained models"""
        try:
            logger.info(f"Making predictions for market {market_id}")

            # Extract recent price and volume data
            prices = [float(point.get('price', 0)) for point in recent_data if point.get('price')]
            volumes = [float(point.get('volume', 0)) for point in recent_data if point.get('volume')]

            if len(prices) < 10:
                return self._empty_ml_result("Insufficient recent data")

            # Create features
            features_df = self._create_features(prices, volumes)
            if features_df.empty:
                return self._empty_ml_result("No features created")

            # Load trained models
            market_models_dir = os.path.join(self.model_save_dir, market_id.replace('-', '_'))
            if not os.path.exists(market_models_dir):
                return self._empty_ml_result("No trained models found")

            predictions = {}
            confidences = {}

            # Load and predict with each model
            model_types = ['random_forest', 'gradient_boosting', 'lstm', 'arima']

            for model_type in model_types:
                model_path = os.path.join(market_models_dir, f"{model_type}.joblib")
                if os.path.exists(model_path):
                    try:
                        model = joblib.load(model_path)
                        prediction, confidence = self._predict_with_model(model, features_df, model_type)

                        predictions[model_type] = prediction
                        confidences[model_type] = confidence

                        logger.debug(f"{model_type} prediction: {prediction:.2f} (confidence: {confidence:.1f}%)")

                    except Exception as e:
                        logger.warning(f"Error loading/predicting with {model_type}: {str(e)}")
                        continue

            if not predictions:
                return self._empty_ml_result("No models could be loaded")

            # Calculate ensemble prediction
            ensemble_prediction = np.mean(list(predictions.values()))
            ensemble_confidence = np.mean(list(confidences.values()))

            # Determine signal classification
            if ensemble_prediction > 10:
                signal_classification = "strong_buy"
            elif ensemble_prediction > 5:
                signal_classification = "buy"
            elif ensemble_prediction > -5:
                signal_classification = "hold"
            elif ensemble_prediction > -15:
                signal_classification = "sell"
            else:
                signal_classification = "strong_sell"

            return {
                'ensemble_prediction': ensemble_prediction,
                'confidence': ensemble_confidence,
                'signal_classification': signal_classification,
                'individual_predictions': predictions,
                'individual_confidences': confidences,
                'details': {
                    'models_used': list(predictions.keys()),
                    'data_points': len(prices),
                    'features_count': len(features_df.columns),
                    'prediction_range': [min(predictions.values()), max(predictions.values())]
                }
            }

        except Exception as e:
            logger.error(f"Error making predictions for market {market_id}: {str(e)}")
            return self._empty_ml_result(f"Prediction error: {str(e)}")

    def _empty_ml_result(self, error_message: str) -> Dict[str, Any]:
        """Return empty ML result with error"""
        return {
            'ensemble_prediction': 0.0,
            'confidence': 0.0,
            'signal_classification': 'error',
            'individual_predictions': {},
            'individual_confidences': {},
            'details': {
                'error': error_message,
                'processing_failed': True
            }
        }

# Global ML models analyzer instance
ml_models_analyzer = MLModelsAnalyzer()