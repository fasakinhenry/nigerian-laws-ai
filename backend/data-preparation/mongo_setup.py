from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NigerianLawsDatabase:
    
    def __init__(self, mongo_uri: str, db_name: str):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        
        self.collections = {
            'raw_documents': 'raw_documents',
        }
        
        self.client = None
        self.db = None
    
    def connect(self):
        """
        Establish connection to MongoDB and returns True if successful or False if otherwise
        """
        try:
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info(f"Successfully connected to MongoDB: {self.db_name}")
            return True

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            logger.error("Please ensure MongoDb is running")
            return False

        except Exception as e:
            logger.error(f"Unexpected error during MongoDB connection: {e}")
            return False
        
    def get_collection(self, collection_name: str):
        
        if not self.db:
            if not self.connect():
                logger.error(f"Failed to get collection '{collection_name}': No database connection.")
                return None
        
        return self.db[collection_name]

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")