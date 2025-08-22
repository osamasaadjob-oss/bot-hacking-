from flask import Flask, request, jsonify
from ai_manager.inference import AdvancedInferenceEngine
from ai_manager.trainer import MetaLearningTrainer
from ai_manager.self_evolution_manager import SelfEvolutionManager
import os
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
inference_engine = AdvancedInferenceEngine()
trainer = MetaLearningTrainer()
evolution_manager = SelfEvolutionManager()

def auto_training_loop():
    while True:
        try:
            time.sleep(86400)
            stats = trainer.get_training_data_stats()
            if stats['total_samples'] >= 100:
                logger.info("Starting automatic training cycle")
                trainer.continuous_learning({})
                metrics = trainer.evaluate_performance()
                evolution_manager.analyze_performance(metrics)
        except Exception as e:
            logger.error(f"Auto-training loop error: {e}")
            time.sleep(3600)

threading.Thread(target=auto_training_loop, daemon=True).start()

@app.route('/suggest', methods=['POST'])
def suggest_scan_params():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        suggestion = inference_engine.suggest(data)
        return jsonify(suggestion)
    except Exception as e:
        logger.error(f"Suggest error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/train', methods=['POST'])
def train_model():
    try:
        data = request.json or {}
        force_retrain = data.get('force_retrain', False)
        if force_retrain or trainer.should_retrain():
            trainer.continuous_learning(data)
            return jsonify({"status": "training_started", "message": "Training completed"})
        return jsonify({"status": "not_needed", "message": "No retraining needed"})
    except Exception as e:
        logger.error(f"Train error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.getenv('AI_MANAGER_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
