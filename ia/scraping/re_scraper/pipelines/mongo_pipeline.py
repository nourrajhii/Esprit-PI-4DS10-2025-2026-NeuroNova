from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from itemadapter import ItemAdapter


class MongoUpsertPipeline:
    def __init__(self, mongo_uri, mongo_db, mongo_collection):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_collection = mongo_collection

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_db=crawler.settings.get("MONGO_DB"),
            mongo_collection=crawler.settings.get("MONGO_COLLECTION", "listings"),
        )

    def open_spider(self, spider):
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.col = self.db[self.mongo_collection]

        # ✅ Créer l'index UNE SEULE FOIS, avec le bon nom
        try:
            self.col.create_index(
                [("source", 1), ("source_listing_id", 1)],
                unique=True,
                name="uniq_source_listing",
            )
        except OperationFailure as e:
            # 85 = IndexOptionsConflict
            if getattr(e, "code", None) != 85:
                raise

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        a = ItemAdapter(item)
        now = datetime.now(timezone.utc)

        source = a.get("source")
        sid = a.get("source_listing_id")
        if not source or not sid:
            return item

        doc_set = dict(a.asdict())
        doc_set["last_seen"] = now

        update = {"$set": doc_set, "$setOnInsert": {"first_seen": now}}

        # ✅ Upsert (insert si nouveau, update sinon)
        self.col.update_one(
            {"source": source, "source_listing_id": sid},
            update,
            upsert=True,
        )

        return item
