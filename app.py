from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# Database helper function
def get_db_connection():
    conn = sqlite3.connect('database/loyalty.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/order', methods=['POST'])
def order():
    customer_id = request.form['customer_id']
    order_amount = float(request.form['order_amount'])

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM customers WHERE customer_id = ?', (customer_id,))
    customer = cursor.fetchone()

    if customer:
        # Update loyalty points based on order amount
        new_points = customer['points'] + int(order_amount // 10)
        cursor.execute('UPDATE customers SET points = ? WHERE customer_id = ?', (new_points, customer_id))
        conn.commit()

    conn.close()
    return redirect(url_for('home'))

@app.route('/admin')
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers')
    customers = cursor.fetchall()
    conn.close()
    return render_template('admin.html', customers=customers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
