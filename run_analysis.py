"""Runs every query in analysis.sql, prints the results and saves each as a CSV in results/ (for Power BI)."""
import csv, os, sys
from db import connect
sys.stdout.reconfigure(errors="replace")

conn, _ = connect(); cur = conn.cursor(); os.makedirs("results", exist_ok=True)
blocks, title, buf = [], None, []
for line in open("analysis.sql", encoding="utf-8"):
    if line.startswith("-- Q"):
        if title: blocks.append((title, "".join(buf)))
        title, buf = line[3:].strip(), []
    elif not line.startswith("--"):
        buf.append(line)
if title: blocks.append((title, "".join(buf)))

for n, (title, sql) in enumerate(blocks, 1):
    cur.execute(sql.strip().rstrip(";"))
    rows = [tuple(float(v) if type(v).__name__ == "Decimal" else v for v in r) for r in cur.fetchall()]
    cols = [d[0] for d in cur.description]
    with open(f"results/Q{n}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    print(f"\n{title}\n{cols}")
    for r in rows[:15]: print(r)
    if len(rows) > 15: print(f"... {len(rows) - 15} more rows in results/Q{n}.csv")
    if not rows: print("(no rows)")
conn.close()
print("\nAll results saved in results/ - open them in Power BI for the dashboard.")
