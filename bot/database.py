import os
import time
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timedelta
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.client = None
        self.db = None
        self.connect_with_retry()
        self._create_indexes()

    def connect_with_retry(self, max_retries=5, retry_delay=2):
        for attempt in range(max_retries):
            try:
                self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
                self.db = self.client.bug_bounty_db
                self.client.admin.command('ping')
                logger.info("✅ Connected to database")
                return True
            except Exception as e:
                logger.error(f"DB connect attempt {attempt+1} failed: {e}")
                time.sleep(retry_delay * (attempt + 1))
        raise Exception("All DB connect attempts failed")

    def _create_indexes(self):
        try:
            self.db.bounties.create_index([("title", ASCENDING)])
            self.db.scan_results.create_index([("bounty_id", ASCENDING)])
            self.db.vulnerabilities.create_index([("type", ASCENDING)])
            logger.info("✅ Indexes created")
        except Exception as e:
            logger.error(f"Index creation error: {e}")

    def get_all_bounties(self):
        return list(self.db.bounties.find({}).sort("title", ASCENDING))

    def get_bounty_by_id(self, bounty_id):
        return self.db.bounties.find_one({"_id": ObjectId(bounty_id)})

    def save_scan_result(self, result_data):
        result_data['timestamp'] = datetime.utcnow()
        return self.db.scan_results.insert_one(result_data)

    def save_vulnerability(self, vuln_data):
        vuln_data['discovered_at'] = datetime.utcnow()
        return self.db.vulnerabilities.insert_one(vuln_data)

    def update_bounty_stats(self, bounty_id, vulnerabilities_found):
        return self.db.bounties.update_one(
            {"_id": ObjectId(bounty_id)},
            {"$set": {"last_scan": datetime.utcnow()}, "$inc": {"vulnerabilities_found": vulnerabilities_found, "total_scans": 1}}
        )

    def get_system_stats(self):
        try:
            total_bounties = self.db.bounties.count_documents({})
            total_scans = self.db.scan_results.count_documents({})
            total_vulnerabilities = self.db.vulnerabilities.count_documents({})
            successful_scans = self.db.scan_results.count_documents({"vulnerabilities_found": {"$gt": 0}})
            success_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0
            active_users = self.db.scan_results.distinct("chat_id", {"timestamp": {"$gte": datetime.utcnow() - timedelta(hours=24)}})
            return {
                "total_bounties": total_bounties,
                "total_scans": total_scans,
                "total_vulnerabilities": total_vulnerabilities,
                "success_rate": round(success_rate, 2),
                "active_users": len(active_users)
            }
        except Exception as e:
            logger.error(f"System stats error: {e}")
            return {"total_bounties": 0, "total_scans": 0, "total_vulnerabilities": 0, "success_rate": 0, "active_users": 0}

    def get_active_users_count(self):
        try:
            active_users = self.db.scan_results.distinct("chat_id", {"timestamp": {"$gte": datetime.utcnow() - timedelta(hours=24)}})
            return len(active_users)
        except Exception as e:
            return 0
