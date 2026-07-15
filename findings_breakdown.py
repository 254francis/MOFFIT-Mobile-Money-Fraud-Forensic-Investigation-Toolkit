import sqlite3

conn = sqlite3.connect("cases.db")
case_id = "c8a9c5fb-9c31-47f0-a43b-372881364f08"

print(f"{'pattern':<24}{'count':>10}{'avg_conf':>10}")
print("-" * 44)
total = 0
for pattern, count, conf in conn.execute(
    "SELECT finding_type, COUNT(*), ROUND(AVG(confidence),2) "
    "FROM findings WHERE case_id=? "
    "GROUP BY finding_type ORDER BY COUNT(*) DESC",
    (case_id,),
):
    print(f"{pattern:<24}{count:>10}{conf:>10}")
    total += count
print("-" * 44)
print(f"{'TOTAL':<24}{total:>10}")