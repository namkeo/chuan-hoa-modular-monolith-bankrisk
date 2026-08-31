import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Backend Tính Điểm Bộ Tiêu Chí"
    API_V1_STR: str = ""
    MONGO_URI: str = os.getenv("MONGO_URI") or os.getenv("MONGODB_URL") or "mongodb://admin:12345678@localhost:27018/"
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME") or os.getenv("MONGODB_DB_NAME") or "credit_scoring_db"

    class Config:
        case_sensitive = True

settings = Settings()
