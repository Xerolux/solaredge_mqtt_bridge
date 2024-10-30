
import joblib
import pandas as pd
from sklearn.linear_model import SGDRegressor
from sklearn.metrics import mean_squared_error
import logging

logger = logging.getLogger("ForecastService")

class ForecastService:
    def __init__(self, model_path="energy_model.pkl", learning_rate=0.01, drift_threshold=100):
        self.model_path = model_path
        self.learning_rate = learning_rate
        self.drift_threshold = drift_threshold
        self.model = self._load_or_initialize_model()

    def _load_or_initialize_model(self):
        try:
            model = joblib.load(self.model_path)
            logger.info("Loaded existing prediction model.")
        except FileNotFoundError:
            model = SGDRegressor(learning_rate='constant', eta0=self.learning_rate)
            logger.info("Initialized new model with learning rate %s", self.learning_rate)
        return model

    def train_model(self, recent_data, current_error):
        if recent_data.empty:
            logger.warning("No recent data for training.")
            return

        recent_data['timestamp'] = pd.to_datetime(recent_data['time']).map(datetime.timestamp)
        X = recent_data[['timestamp']]
        y = recent_data['value']
        self.model.partial_fit(X, y)
        if current_error > self.drift_threshold:
            joblib.dump(self.model, self.model_path)
            logger.info("Model drift detected. Model retrained and saved.")

    def detect_drift(self, recent_data):
        if recent_data.empty:
            return 0
        recent_data['timestamp'] = pd.to_datetime(recent_data['time']).map(datetime.timestamp)
        X = recent_data[['timestamp']]
        y_true = recent_data['value']
        y_pred = self.model.predict(X)
        error = mean_squared_error(y_true, y_pred)
        return error
