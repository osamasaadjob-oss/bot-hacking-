import os
import logging
import time
from telebot import TeleBot, types
from bot.database import DatabaseManager
from bot.tasks import run_scan_task

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BugBountyBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN not found")
        self.bot = TeleBot(self.token)
        self.db = DatabaseManager()
        self.setup_handlers()
        self.auto_heal()

    def auto_heal(self):
        try:
            self.db.get_all_bounties()
            logger.info("✅ Database connected")
        except Exception as e:
            logger.error(f"❌ DB error: {e}")
            self.retry_database_connection()

    def retry_database_connection(self, max_retries=5):
        for attempt in range(max_retries):
            try:
                time.sleep(2 ** attempt)
                self.db = DatabaseManager()
                self.db.get_all_bounties()
                logger.info("✅ DB reconnected")
                return True
            except Exception as e:
                logger.error(f"Retry {attempt+1} failed: {e}")
        return False

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            self.show_main_menu(message.chat.id)

        @self.bot.message_handler(commands=['report'])
        def handle_report(message):
            self.handle_manual_report(message)

        @self.bot.message_handler(commands=['status'])
        def handle_status(message):
            self.show_system_status(message.chat.id)

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            self.handle_callback_query(call)

    def show_main_menu(self, chat_id):
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton("🔎 Bug Bounty Challenges", callback_data="list_bounties"),
            types.InlineKeyboardButton("➕ Add New Challenge", callback_data="add_bounty"),
            types.InlineKeyboardButton("📊 Stats", callback_data="stats"),
            types.InlineKeyboardButton("🔄 Refresh Model", callback_data="refresh_model"),
            types.InlineKeyboardButton("⚙️ System Status", callback_data="system_status")
        ]
        keyboard.add(*buttons)
        self.bot.send_message(chat_id, "Welcome! Choose from the menu:", reply_markup=keyboard)

    def list_bounties(self, call):
        try:
            bounties = self.db.get_all_bounties()
            if not bounties:
                self.bot.edit_message_text("No challenges yet. Tap ➕ to add one.", call.message.chat.id, call.message.message_id)
                return
            keyboard = types.InlineKeyboardMarkup()
            for bounty in bounties:
                btn = types.InlineKeyboardButton(bounty['title'], callback_data=f"bounty_{bounty['_id']}")
                keyboard.add(btn)
            keyboard.add(types.InlineKeyboardButton("🏠 Home", callback_data="main_menu"))
            self.bot.edit_message_text("Select a challenge:", call.message.chat.id, call.message.message_id, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"List bounties error: {e}")

    def show_bounty_details(self, call):
        try:
            bounty_id = call.data.split("_", 1)[1]
            bounty = self.db.get_bounty_by_id(bounty_id)
            if not bounty:
                self.bot.answer_callback_query(call.id, "❌ Challenge not found")
                return
            text = (
                f"🔰 {bounty['title']}\n\n"
                f"🎯 Target: {bounty['target']}\n"
                f"📋 Method: {bounty['method']}\n"
                f"⚙️ Param: {bounty['param']}\n"
                f"📝 Instructions: {bounty['instructions']}\n\n"
                f"⏱ Last scan: {bounty.get('last_scan', 'Never')}\n"
                f"✅ Vulnerabilities found: {bounty.get('vulnerabilities_found', 0)}"
            )
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("✅ Start Smart Scan", callback_data=f"scan_{bounty_id}"))
            keyboard.add(types.InlineKeyboardButton("🔙 Back", callback_data="list_bounties"), types.InlineKeyboardButton("🏠 Home", callback_data="main_menu"))
            self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Show bounty details error: {e}")

    def start_scan(self, call):
        try:
            bounty_id = call.data.split("_", 1)[1]
            bounty = self.db.get_bounty_by_id(bounty_id)
            if not bounty:
                self.bot.answer_callback_query(call.id, "❌ Challenge not found")
                return
            run_scan_task.delay(call.message.chat.id, bounty)
            self.bot.edit_message_text("🔄 Smart scan started...", call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.error(f"Start scan error: {e}")

    def show_system_status(self, chat_id):
        try:
            services_status = self.check_services_status()
            text = "🟢 System Status:\n\n"
            for service, status in services_status.items():
                text += f"{'✅' if status['status'] else '❌'} {service}: {status['message']}\n"
            self.bot.send_message(chat_id, text)
        except Exception as e:
            logger.error(f"System status error: {e}")

    def check_services_status(self):
        import requests
        services = {
            'MongoDB': lambda: self.db.client.admin.command('ping'),
            'Redis': lambda: self.bot.get_me() is not None,
            'AI Manager': lambda: requests.get(f"{os.getenv('AI_MANAGER_URL')}/health", timeout=5).status_code == 200
        }
        status = {}
        for service, test_func in services.items():
            try:
                test_func()
                status[service] = {'status': True, 'message': 'Healthy'}
            except Exception:
                status[service] = {'status': False, 'message': 'Error'}
        return status

    def run(self):
        import time
        start_time = time.time()
        logger.info("Starting Bug Bounty Bot...")
        self.bot.infinity_polling()
