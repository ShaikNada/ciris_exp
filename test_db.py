
import sys
import os

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.database import engine, Base, SessionLocal
from app.models import FIR

try:
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
    
    db = SessionLocal()
    count = db.query(FIR).count()
    print(f"Current FIR count: {count}")
    db.close()
except Exception as e:
    import traceback
    traceback.print_exc()
