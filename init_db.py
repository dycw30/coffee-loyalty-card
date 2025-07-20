import sqlite3

conn = sqlite3.connect('loyalty_card.db')
c = conn.cursor()

c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, unique_id TEXT, total_orders INTEGER, tokens_earned INTEGER, tokens_redeemed INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS drinks (id INTEGER PRIMARY KEY, name TEXT)')

conn.commit()
conn.close()
