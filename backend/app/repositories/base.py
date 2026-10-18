from bson import ObjectId

class BaseRepository:
    def __init__(self, collection):
        self.col = collection

    def get_by_id(self, id_):
        return self.col.find_one({"_id": ObjectId(id_)})

    def insert(self, doc: dict) -> str:
        return str(self.col.insert_one(doc).inserted_id)

    def update(self, id_, campos: dict):
        self.col.update_one({"_id": ObjectId(id_)}, {"$set": campos})

    def delete(self, id_):
        self.col.delete_one({"_id": ObjectId(id_)})