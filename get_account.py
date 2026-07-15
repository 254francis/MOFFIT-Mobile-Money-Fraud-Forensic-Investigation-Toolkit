import sqlite3
import json

conn = sqlite3.connect("cases.db")
row = conn.execute(
    "SELECT account_ids FROM findings "
    "WHERE case_id='b346e603-dca6-41b4-95fb-7b83b43c8523' "
    "AND finding_type='rapid_drain' LIMIT 1"
).fetchone()
print(json.loads(row[0])[0])