import os
import threading
import time
import requests
from bot.bot import BugBountyBot
from ai_manager.server import app as ai_app
from monitoring.dashboard import app as dash_app
import subprocess

def run_bot():
    bot = BugBountyBot()
    bot.run()

def run_ai():
    ai_app.run(host='0.0.0.0', port=5000, debug=False)

def run_dashboard():
    dash_app.run_server(host='0.0.0.0', port=8050, debug=False)

def ping_self():
    while True:
        try:
            requests.get("http://localhost:5000/health", timeout=5)
            requests.get("http://localhost:8050", timeout=5)
            print("✅ Ping successful")
        except Exception as e:
            print("❌ Ping failed:", e)
        time.sleep(300)

def setup_mongo():
    try:
        subprocess.run(["mongod", "--fork", "--logpath", "/tmp/mongod.log"], check=True)
    except:
        print("⚠️ MongoDB already running or not available")

if __name__ == "__main__":
    setup_mongo()
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=run_ai, daemon=True).start()
    threading.Thread(target=run_dashboard, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()
    while True:
        time.sleep(1)
