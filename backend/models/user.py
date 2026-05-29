from sqlalchemy import Column, String, Boolean, DateTime
from database import Base
import uuid
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email           = Column(String, unique=True, nullable=False, index=True)
    username        = Column(String, unique=True, nullable=False)
    full_name       = Column(String, default="")
    hashed_password = Column(String, nullable=False)
    role            = Column(String, default="developer")   # "admin" | "developer"
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    last_login      = Column(DateTime, nullable=True)
