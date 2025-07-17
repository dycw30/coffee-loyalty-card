import sqlite3

def init_db():
    conn = sqlite3.connect('database/loyalty.db')
    cursor = conn.cursor()
    
    # Create customers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            points INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
