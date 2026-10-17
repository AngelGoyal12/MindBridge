import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

load_dotenv()

TESTING = os.getenv("MINDBRIDGE_TESTING") == "1"

if TESTING:
    DATABASE_URL = URL.create(
        drivername="sqlite",
        database=":memory:",
    )
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "mindbridge")

    if not DB_USER or DB_PASSWORD is None:
        raise RuntimeError(
            "DB_USER or DB_PASSWORD is missing from the .env file"
        )

    DATABASE_URL = URL.create(
        drivername="mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
    )
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()
