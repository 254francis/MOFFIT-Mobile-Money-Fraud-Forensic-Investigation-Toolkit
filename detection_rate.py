import sqlite3
import json
import pandas as pd

# Ground truth: labelled fraud rows
df = pd.read_csv("data/samples/paysim.csv")
fraud = df[df["isFraud"] == 1][["step", "nameOrig", "nameDest"]]
print(f"Labelled fraud rows: {len(fraud)}")

# Findings: account + step ranges
conn = sqlite3.connect("cases.db")
rows = conn.execute(
    "SELECT account_ids, step_start, step_end FROM findings "
    "WHERE case_id='c8a9c5fb-9c31-47f0-a43b-372881364f08' "
    "AND finding_type != 'balance_inconsistency'"
).fetchall()
print(f"Findings loaded: {len(rows)}")

flagged = {}  # account -> list of (start, end)
for acc_json, s, e in rows:
    for acc in json.loads(acc_json):
        flagged.setdefault(acc, []).append((s, e))

def covered(account, step):
    for s, e in flagged.get(account, ()):
        if s <= step <= e:
            return True
    return False

hits = 0
for _, r in fraud.iterrows():
    if covered(r["nameOrig"], r["step"]) or covered(r["nameDest"], r["step"]):
        hits += 1

rate = hits / len(fraud)
print(f"Fraud rows covered by findings: {hits} / {len(fraud)} = {rate:.1%}")