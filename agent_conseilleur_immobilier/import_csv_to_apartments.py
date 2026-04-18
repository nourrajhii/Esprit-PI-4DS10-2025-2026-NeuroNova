import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "real_estate_advisor_db")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

CSV_PATH = "ai_ready_listings.csv"

df = pd.read_csv(CSV_PATH)

print("Colonnes trouvées dans le CSV :", df.columns.tolist())

df = df[
    [
        "id",
        "title",
        "price",
        "city",
        "property_type",
        "surface_m2",
        "rooms",
        "bathrooms",
        "transaction_type",
        "url",
    ]
].copy()

df["title"] = df["title"].fillna("")
df["city"] = df["city"].fillna("")
df["property_type"] = df["property_type"].fillna("")
df["transaction_type"] = df["transaction_type"].fillna("")
df["url"] = df["url"].fillna("")

df["price"] = pd.to_numeric(df["price"], errors="coerce")
df["surface_m2"] = pd.to_numeric(df["surface_m2"], errors="coerce")
df["rooms"] = pd.to_numeric(df["rooms"], errors="coerce").fillna(0).astype(int)
df["bathrooms"] = pd.to_numeric(df["bathrooms"], errors="coerce").fillna(0).astype(int)

df = df.dropna(subset=["id", "price"])

df.to_sql("apartments", con=engine, if_exists="append", index=False)

print("Import terminé avec succès.")
print(f"Nombre de lignes importées : {len(df)}")