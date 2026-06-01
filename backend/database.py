from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models.user import User  # noqa: F401 — registers model with Base
    Base.metadata.create_all(bind=engine)
    _seed_default_admin()


def _seed_default_admin():
    """Create the default admin account if no users exist yet."""
    from models.user import User
    from services.auth_service import hash_password

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                email="admin@cpi.local",
                username="admin",
                full_name="Administrator",
                hashed_password=hash_password("admin123"),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("[startup] Default admin created: admin@cpi.local / admin123")
            print("[startup] Change the password after first login!")
    except Exception as e:
        print(f"[startup] Could not seed default admin: {e}")
    finally:
        db.close()
