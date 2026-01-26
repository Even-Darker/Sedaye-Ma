
import sqlite3
import os

DB_PATH = "/Users/iliya/Dev/Sedaye_Ma/data/sedaye_ma.db"

def migrate():
    print(f"📂 CWD: {os.getcwd()}")
    data_dir = os.path.join(os.getcwd(), "data")
    db_file = os.path.join(data_dir, "sedaye_ma.db")
    
    if os.path.exists(db_file):
        print(f"✅ Found DB at {db_file}")
        DB_PATH = db_file
    else:
        print(f"❌ DB not found at {db_file}")
        # Try to find any db file
        files = os.listdir(data_dir)
        db_files = [f for f in files if f.endswith(".db")]
        if db_files:
            print(f"⚠️ Found other DB files: {db_files}")
            DB_PATH = os.path.join(data_dir, db_files[0])
            print(f"⚠️ Using {DB_PATH}")
        else:
            return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(petitions)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "visit_count" in columns:
            print("✅ Column 'visit_count' already exists.")
        else:
            print("⏳ Adding 'visit_count' column...")
            cursor.execute("ALTER TABLE petitions ADD COLUMN visit_count INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Migration successful!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
