from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
import os
import certifi

load_dotenv()

uri = os.getenv("DATABASE_URL")
client = MongoClient(uri, tlsCAFile=certifi.where())

try:
    client.admin.command("ping")
    print("Connexion reussie !")
except Exception as e:
    print(f"Erreur : {e}")