import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

engine = create_engine(os.environ["DATABASE_URL"])

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

if __name__ == "__main__":
    from sqlalchemy import text
    session = next(get_session())
    result = session.execute(text("SELECT 1;"))
    print("Session works:", result.scalar())        