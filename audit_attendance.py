"""
Attendance Audit & Cleanup Tool
Run this to see all logs and optionally delete suspicious entries.
"""
import sqlite3
import datetime

DB = 'attendance.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=" * 60)
print("  ATTENDANCE AUDIT REPORT")
print("=" * 60)

# Show all logs from today
today = datetime.date.today().strftime("%Y-%m-%d")
c.execute("""
    SELECT a.student_id, s.name, a.timestamp, a.status
    FROM attendance_logs a
    JOIN students s ON a.student_id = s.student_id
    WHERE date(a.timestamp) = ?
    ORDER BY a.timestamp
""", (today,))
rows = c.fetchall()

print(f"\n📅 TODAY's logs ({today}): {len(rows)} entries\n")
for r in rows:
    print(f"  [{r[2]}]  {r[0]:>4} | {r[1][:35]:<35} | {r[3]}")

# Check for suspicious students (A65, B09, B13)
print("\n" + "=" * 60)
print("  SUSPICIOUS STUDENTS CHECK (A65, B09, B13)")
print("=" * 60)
c.execute("""
    SELECT a.student_id, s.name, a.timestamp, a.status
    FROM attendance_logs a
    JOIN students s ON a.student_id = s.student_id
    WHERE a.student_id IN ('A65', 'B09', 'B13')
    ORDER BY a.timestamp DESC
    LIMIT 20
""")
suspect_rows = c.fetchall()
if suspect_rows:
    for r in suspect_rows:
        print(f"  [{r[2]}]  {r[0]:>4} | {r[1][:35]:<35} | {r[3]}")
else:
    print("  ✅ No entries found for these students.")

# Ask to clean today's ghost entries
print("\n" + "=" * 60)
ans = input("\n❓ Do you want to DELETE today's logs for A65, B09, B13? (yes/no): ").strip().lower()
if ans == 'yes':
    c.execute("""
        DELETE FROM attendance_logs
        WHERE student_id IN ('A65', 'B09', 'B13')
        AND date(timestamp) = ?
    """, (today,))
    conn.commit()
    print(f"  🗑️  Deleted {c.rowcount} entries for today.")
else:
    print("  ✅ No changes made.")

conn.close()
print("\nDone.\n")
