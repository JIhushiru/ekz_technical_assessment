from pydantic import BaseModel
import os

class Settings(BaseModel):
    api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
    api_key: str = os.getenv("API_KEY", "")
    db_url: str = os.getenv("DB_URL", "sqlite:///your_pipeline/data.db")

settings = Settings()