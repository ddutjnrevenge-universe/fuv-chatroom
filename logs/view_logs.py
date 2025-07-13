import time
import os
from db_logger import cursor, conn  # Ensure conn is imported too

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def tail_logs(interval=2):
    last_seen_id = 0
    while True:
        cursor.execute("SELECT * FROM logs WHERE id > ? ORDER BY timestamp ASC", (last_seen_id,))
        new_rows = cursor.fetchall()
        if new_rows:
            for row in new_rows:
                print(row)
            last_seen_id = new_rows[-1][0]  # Update to last seen ID
        time.sleep(interval)

if __name__ == "__main__":
    clear_terminal()
    print("📜 Live log viewer started. Press Ctrl+C to exit.\n")
    try:
        tail_logs()
    except KeyboardInterrupt:
        print("\nExiting viewer...")
    finally:
        conn.close()
