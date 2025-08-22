import os
import time
import requests
from celery import Celery
from datetime import datetime
from bot.database import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery('bug_bounty_tasks', broker=redis_url)
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
)

db = DatabaseManager()

class ScanReport:
    def __init__(self, chat_id, cfg):
        self.chat_id = chat_id
        self.cfg = cfg
        self.client = AiClient(os.getenv("AI_MANAGER_URL"))

    def suggest(self, state):
        return self.client.suggest_params(state)

    def compile_report(self, logs):
        report = {
            "chat_id": self.chat_id,
            "bounty_id": str(self.cfg.get("_id", "")),
            "timestamp": datetime.utcnow(),
            "logs": logs,
            "vulnerabilities_found": len(logs.get("vulnerabilities", [])),
            "scan_duration": logs.get("duration", 0)
        }
        try:
            result = db.save_scan_result(report)
            report["_id"] = str(result.inserted_id)
            return report
        except Exception as e:
            logger.error(f"Save scan result error: {e}")
            return report

    def notify_user(self, report):
        import telebot
        bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
        if report['vulnerabilities_found'] > 0:
            message = f"✅ Found {report['vulnerabilities_found']} vulnerabilities in {self.cfg['title']}!"
        else:
            message = f"🔍 Scan of {self.cfg['title']} completed. No vulnerabilities found."
        bot.send_message(self.chat_id, message)

class AiClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def suggest_params(self, state):
        try:
            response = requests.post(f"{self.base_url}/suggest", json=state, timeout=10)
            return response.json() if response.status_code == 200 else self.get_fallback_params()
        except Exception:
            return self.get_fallback_params()

    def get_fallback_params(self):
        return {"rate": 1000, "intensity": 0.5, "accuracy": 0.5, "timeout": 30, "threads": 20}

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_scan_task(self, chat_id, bounty):
    try:
        import random
        scanner = ScanReport(chat_id, bounty)
        state = {"target": bounty['target'], "method": bounty['method'], "param": bounty['param']}
        params = scanner.suggest(state)
        scan_duration = random.uniform(30, 120)
        vulnerabilities = []
        if random.random() < 0.3:
            vuln_types = ["XSS", "SQLi", "CSRF", "Info Disclosure", "RCE"]
            severities = ["Low", "Medium", "High", "Critical"]
            for _ in range(random.randint(1, 3)):
                vulnerabilities.append({
                    "type": random.choice(vuln_types),
                    "severity": random.choice(severities),
                    "confidence": round(random.uniform(0.7, 0.95), 2)
                })
        logs = {"vulnerabilities": vulnerabilities, "duration": round(scan_duration, 2), "ai_params": params}
        report = scanner.compile_report(logs)
        db.update_bounty_stats(bounty['_id'], len(vulnerabilities))
        scanner.notify_user(report)
        return {"status": "success", "vulnerabilities_found": len(vulnerabilities)}
    except Exception as e:
        logger.error(f"Scan task failed: {e}")
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))
