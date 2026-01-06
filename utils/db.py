import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")

client = MongoClient(mongo_uri)
db = client["SathyabamaChronicles"]   # database name

# Collections
users_collection = db["users"]
blogs_collection = db["blogs"]
chatlogs_collection = db["chatlogs"]