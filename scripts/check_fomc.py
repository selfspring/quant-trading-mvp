import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()
cur.execute("""
    SELECT event_type, COUNT(*), MIN(event_date), MAX(event_date)
    FROM macro_events
    WHERE event_type IN ('FOMC_MINUTES','FOMC')
    GROUP BY event_type ORDER BY event_type
""")
for r in cur.fetchall():
    print(f"{r[0]}: {r[1]} rows, {r[2]} ~ {r[3]}")

print("\n--- FOMC_MINUTES sample (first 3 + last 3) ---")
cur.execute("""
    SELECT event_date, description FROM macro_events
    WHERE event_type='FOMC_MINUTES'
    ORDER BY event_date
""")
rows = cur.fetchall()
for r in rows[:3]:
    print(f"  {r[0]}  {r[1]}")
print("  ...")
for r in rows[-3:]:
    print(f"  {r[0]}  {r[1]}")

conn.close()
