from db.base import Base
from db.session import engine

# Import models trước khi create_all để SQLAlchemy nhận đủ metadata.
from db import models  # noqa: F401


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
