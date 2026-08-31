from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from app.core.database import get_database
from app.utils.mongo_utils import clean_mongo_doc

class BaseRepository:
    collection_name: str = ""

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self._db = db

    @property
    def collection(self) -> AsyncIOMotorCollection:
        db = self._db if self._db is not None else get_database()
        return db[self.collection_name]

    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"_id": doc_id})
        return clean_mongo_doc(doc)

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one(query)
        return clean_mongo_doc(doc)

    async def find_many(
        self,
        query: Dict[str, Any],
        sort: Optional[List[tuple]] = None,
        skip: int = 0,
        limit: int = 0
    ) -> List[Dict[str, Any]]:
        cursor = self.collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        if skip > 0:
            cursor = cursor.skip(skip)
        if limit > 0:
            cursor = cursor.limit(limit)
        docs = await cursor.to_list(length=None)
        return [clean_mongo_doc(doc) for doc in docs]

    async def count(self, query: Dict[str, Any]) -> int:
        return await self.collection.count_documents(query)

    async def create(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        if "_id" in doc and doc["_id"] is None:
            del doc["_id"]
        await self.collection.insert_one(doc)
        return clean_mongo_doc(doc)

    async def update(self, doc_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        clean_update = {k: v for k, v in update_data.items() if v is not None}
        if not clean_update:
            return await self.get_by_id(doc_id)
        await self.collection.update_one(
            {"_id": doc_id},
            {"$set": clean_update}
        )
        return await self.get_by_id(doc_id)

    async def soft_delete(self, doc_id: str) -> bool:
        res = await self.collection.update_one(
            {"_id": doc_id},
            {"$set": {"is_active": 0}}
        )
        return res.modified_count > 0

    async def delete_permanently(self, doc_id: str) -> bool:
        res = await self.collection.delete_one({"_id": doc_id})
        return res.deleted_count > 0
