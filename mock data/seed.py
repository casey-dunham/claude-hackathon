import sqlite3

DB_PATH = "health.db"

ENTRIES = [
    ("a1b2c3d4-0001-4000-8000-000000000001", "Oatmeal with banana", 320, 8, 62, 5, "2026-04-12T08:15:00Z"),
    ("a1b2c3d4-0001-4000-8000-000000000002", "Greek yogurt", 150, 17, 9, 4, "2026-04-12T10:30:00Z"),
    ("a1b2c3d4-0001-4000-8000-000000000003", "Chicken Caesar salad", 480, 38, 18, 28, "2026-04-12T13:00:00Z"),
    ("a1b2c3d4-0001-4000-8000-000000000004", "Apple", 95, 0, 25, 0, "2026-04-12T15:45:00Z"),
    ("a1b2c3d4-0001-4000-8000-000000000005", "Grilled salmon with rice", 620, 45, 55, 18, "2026-04-12T19:00:00Z"),

    ("a1b2c3d4-0002-4000-8000-000000000006", "Scrambled eggs and toast", 380, 22, 30, 18, "2026-04-13T08:00:00Z"),
    ("a1b2c3d4-0002-4000-8000-000000000007", "Protein bar", 210, 20, 24, 7, "2026-04-13T11:00:00Z"),
    ("a1b2c3d4-0002-4000-8000-000000000008", "Turkey sandwich", 450, 30, 48, 12, "2026-04-13T12:30:00Z"),
    ("a1b2c3d4-0002-4000-8000-000000000009", "Handful of almonds", 170, 6, 6, 15, "2026-04-13T16:00:00Z"),
    ("a1b2c3d4-0002-4000-8000-000000000010", "Beef stir fry with noodles", 710, 40, 72, 22, "2026-04-13T19:30:00Z"),

    ("a1b2c3d4-0003-4000-8000-000000000011", "Smoothie (spinach, banana, protein powder)", 340, 28, 40, 6, "2026-04-14T07:45:00Z"),
    ("a1b2c3d4-0003-4000-8000-000000000012", "Cheese and crackers", 260, 9, 28, 13, "2026-04-14T10:15:00Z"),
    ("a1b2c3d4-0003-4000-8000-000000000013", "Burrito bowl", 750, 42, 85, 20, "2026-04-14T13:15:00Z"),
    ("a1b2c3d4-0003-4000-8000-000000000014", "Orange juice", 110, 2, 26, 0, "2026-04-14T16:30:00Z"),
    ("a1b2c3d4-0003-4000-8000-000000000015", "Pasta with tomato sauce", 580, 20, 95, 10, "2026-04-14T19:00:00Z"),

    ("a1b2c3d4-0004-4000-8000-000000000016", "Avocado toast with egg", 420, 18, 38, 22, "2026-04-15T08:30:00Z"),
    ("a1b2c3d4-0004-4000-8000-000000000017", "Latte", 190, 7, 24, 7, "2026-04-15T09:00:00Z"),
    ("a1b2c3d4-0004-4000-8000-000000000018", "Grilled chicken wrap", 520, 38, 44, 18, "2026-04-15T12:45:00Z"),
    ("a1b2c3d4-0004-4000-8000-000000000019", "Banana", 105, 1, 27, 0, "2026-04-15T15:30:00Z"),
    ("a1b2c3d4-0004-4000-8000-000000000020", "Pizza (2 slices)", 560, 24, 68, 20, "2026-04-15T19:45:00Z"),

    ("a1b2c3d4-0005-4000-8000-000000000021", "Pancakes with maple syrup", 490, 10, 88, 12, "2026-04-16T09:00:00Z"),
    ("a1b2c3d4-0005-4000-8000-000000000022", "Mixed nuts", 180, 5, 8, 16, "2026-04-16T11:30:00Z"),
    ("a1b2c3d4-0005-4000-8000-000000000023", "Tuna salad sandwich", 430, 32, 40, 14, "2026-04-16T13:00:00Z"),
    ("a1b2c3d4-0005-4000-8000-000000000024", "Chocolate milk", 200, 8, 34, 5, "2026-04-16T16:00:00Z"),
    ("a1b2c3d4-0005-4000-8000-000000000025", "Steak with roasted potatoes", 780, 55, 50, 35, "2026-04-16T19:00:00Z"),

    ("a1b2c3d4-0006-4000-8000-000000000026", "Cereal with milk", 290, 10, 52, 5, "2026-04-17T07:30:00Z"),
    ("a1b2c3d4-0006-4000-8000-000000000027", "Hard boiled eggs (2)", 140, 12, 1, 10, "2026-04-17T10:00:00Z"),
    ("a1b2c3d4-0006-4000-8000-000000000028", "Veggie burger", 410, 22, 50, 12, "2026-04-17T12:30:00Z"),
    ("a1b2c3d4-0006-4000-8000-000000000029", "Hummus with pita", 320, 10, 44, 12, "2026-04-17T15:00:00Z"),
    ("a1b2c3d4-0006-4000-8000-000000000030", "Shrimp tacos (3)", 540, 34, 56, 18, "2026-04-17T19:15:00Z"),
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS food_entries (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            calories    INTEGER NOT NULL,
            protein_g   REAL NOT NULL,
            carbs_g     REAL NOT NULL,
            fat_g       REAL NOT NULL,
            logged_at   TEXT NOT NULL
        )
    """)

    cur.executemany("""
        INSERT OR IGNORE INTO food_entries
            (id, name, calories, protein_g, carbs_g, fat_g, logged_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ENTRIES)

    conn.commit()
    print(f"Seeded {cur.rowcount} rows into food_entries (skipped duplicates).")
    conn.close()

if __name__ == "__main__":
    seed()
