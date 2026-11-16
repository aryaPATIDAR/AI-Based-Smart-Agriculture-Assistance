from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./kisansmart.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

Base = declarative_base()


def _add_email_column():
    """
    Purani DB mein 'email' column nahi hota. Ye function use apne aap jod deta hai,
    taaki DB file delete na karni pade.
    - Agar table abhi bani hi nahi hai, to kuch nahi karta (create_all nayi table
      email ke saath bana dega).
    - Agar email column pehle se hai, to kuch nahi karta.
    """
    insp = inspect(engine)
    for table in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns(table)]
        # users wali table: Kisan (user_id + mobile hota hai; reviews table mein mobile nahi)
        if "user_id" in cols and "mobile" in cols and "email" not in cols:
            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN email VARCHAR'))
                conn.execute(text(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS ix_{table}_email ON "{table}"(email)'
                ))
            print(f"[db] '{table}' table mein 'email' column jod diya gaya")


try:
    _add_email_column()
except Exception as e:
    print("[db] email column migration fail hua:", e)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()