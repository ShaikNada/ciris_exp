
import sqlite3

conn = sqlite3.connect('ciris.db')
cursor = conn.execute("PRAGMA table_info(firs)")
cols = [row[1] for row in cursor.fetchall()]
print(f"Columns: {cols}")
conn.close()
