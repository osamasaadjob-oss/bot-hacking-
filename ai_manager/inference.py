import numpy as np
from stable_baselines3 import PPO
import os
import json
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

class AdvancedInferenceEngine:
    def __init__(self):
        self.model = None
        self.model_version = "v1.0"
        self.model_path = os.getenv('MODEL_PATH', 'models/ppo_bug_bounty')
        self.fallback_mode = True
        self.load_model()

    def load_model(self):
        try:
            model_file = f"{self.model_path}.zip"
            if os.path.exists(model_file):
                self.model = PPO.load(model_file)
                self.fallback_mode = False
                logger.info("✅ Model loaded")
            else:
                logger.warning("⚠️ No model found, using fallback")
        except Exception as e:
            logger.error(f"Model load error: {e}")

    def suggest(self, data):
        try:
            target = data.get('target', '')
            method = data.get('method', 'GET')
            param = data.get('param', '')
            state = np.array([
                len(target) / 100,
                1 if target.startswith('https') else 0,
                1 if '?' in target else 0,
                hash(method) % 10 / 10,
                0.5,
                0.5,
                len(param) / 100
            ])
            if self.model and not self.fallback_mode:
                action, _ = self.model.predict(state, deterministic=True)
                return self.action_to_scan_params(action)
            return self.get_fallback_params()
        except Exception:
            return self.get_fallback_params()

    def action_to_scan_params(self, action):
        return {
            'rate': int(500 + float(action[0]) * 4500),
            'intensity': float(action[1]),
            'accuracy': float(action[2]),
            'timeout': int(30 + float(action[0]) * 60),
            'model_version': self.model_version
        }

    def get_fallback_params(self):
        return {
            'rate': 1000,
            'intensity': 0.5,
            'accuracy': 0.5,
            'timeout': 45,
            'model_version': 'fallback'
        }

    def get_model_version(self):
        return self.model_version
