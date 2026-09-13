from pathlib import Path
import sqlite3

db_path = Path(r".\extracted\futwc_db\futwc_ng_db.db")

con = sqlite3.connect(db_path)
cur = con.cursor()

rows = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

for (name,) in rows:
    print(name)

con.close()