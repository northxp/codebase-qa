import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings(database_url=os.environ["DATABASE_URL"])
