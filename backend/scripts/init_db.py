from dotenv import load_dotenv

load_dotenv()

from pymongo import MongoClient  # noqa: E402

from app.config import Config  # noqa: E402
from app.utils.database import crear_indices, seed_usuarios  # noqa: E402


def main():
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client[Config.MONGO_DB]
    db.command("ping")
    crear_indices(db)
    creados = seed_usuarios(db)
    print(f"Base '{Config.MONGO_DB}' lista. Usuarios demo creados: {creados}")


if __name__ == "__main__":
    main()