from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# ----------- LOGIN ROUTES -----------

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT password, role FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        conn.close()
        if result and check_password_hash(result[0], password):
            session['username'] = username
            session['role'] = result[1]
            if result[1] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('order'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------- ADMIN PANEL -----------

@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    users = c.fetchall()
    c.execute("SELECT id, name, unique_id, total_orders, tokens_earned, tokens_redeemed FROM customers")
    customers = c.fetchall()
    c.execute("SELECT id, name FROM drinks")
    drinks = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users, customers=customers, drinks=drinks)


@app.route('/add_user', methods=['POST'])
def add_user():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    username = request.form['username']
    password = generate_password_hash(request.form['password'])
    role = request.form['role']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/add_customer', methods=['POST'])
def add_customer():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    name = request.form['name']
    unique_id = str(request.form['unique_id']).zfill(4)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, unique_id, total_orders, tokens_earned, tokens_redeemed) VALUES (?, ?, 0, 0, 0)", (name, unique_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/add_drink', methods=['POST'])
def add_drink():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    drink = request.form['drink']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO drinks (name) VALUES (?)", (drink,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/export_data')
def export_data():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    users_df = pd.read_sql_query("SELECT username, role FROM users", conn)
    customers_df = pd.read_sql_query("SELECT name, unique_id, total_orders, tokens_earned, tokens_redeemed FROM customers", conn)
    customers_df['token_balance'] = customers_df['tokens_earned'] - customers_df['tokens_redeemed']
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        users_df.to_excel(writer, sheet_name='Users', index=False)
        customers_df.to_excel(writer, sheet_name='Customers', index=False)
    output.seek(0)
    return send_file(output, download_name="loyalty_data.xlsx", as_attachment=True)

@app.route('/upload_customers', methods=['POST'])
def upload_customers():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    file = request.files.get('customer_file')
    if not file:
        return redirect(url_for('admin'))
    df = pd.read_excel(file)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    for _, row in df.iterrows():
        c.execute('''
            INSERT INTO customers (name, unique_id, total_orders, tokens_earned, tokens_redeemed)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            row['name'],
            str(row['unique_id']).zfill(4),
            int(row['total_orders']),
            int(row['tokens_earned']),
            int(row['tokens_redeemed'])
        ))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# ----------- ORDER PANEL -----------

@app.route('/order', methods=['GET', 'POST'])
def order():
    if 'username' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT name FROM drinks")
    drinks = [row[0] for row in c.fetchall()]
    conn.close()
    message = session.pop('message', '')
    return render_template('order.html', drinks=drinks, message=message)

@app.route('/get_customers_by_uid', methods=['GET'])
def get_customers_by_uid():
    uid = request.args.get('uid')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM customers WHERE unique_id = ?", (uid,))
    matches = [{"id": row[0], "name": row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(customers=matches)

@app.route('/get_customer_summary', methods=['GET'])
def get_customer_summary():
    customer_id = request.args.get('customer_id')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT total_orders, tokens_earned, tokens_redeemed FROM customers WHERE id = ?", (customer_id,))
    row = c.fetchone()
    conn.close()
    if row:
        total_orders, earned, redeemed = row
        return jsonify({
            "total_orders": total_orders,
            "tokens_earned": earned,
            "tokens_redeemed": redeemed,
            "token_balance": earned - redeemed
        })
    return jsonify({})

@app.route('/submit_order', methods=['POST'])
def submit_order():
    if 'username' not in session:
        return redirect(url_for('login'))
    customer_id = request.form['customer_id']
    quantity = int(request.form['quantity'])
    redeem = int(request.form['redeem'])
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Get current tokens
    c.execute("SELECT tokens_earned, tokens_redeemed FROM customers WHERE id = ?", (customer_id,))
    row = c.fetchone()
    earned, redeemed = row
    balance = earned - redeemed
    if redeem > balance:
        conn.close()
        session['message'] = 'Error: Cannot redeem more tokens than available.'
        return redirect(url_for('order'))
    # Update stats
    tokens_earned = quantity // 9
    c.execute('''
        UPDATE customers
        SET total_orders = total_orders + ?,
            tokens_earned = tokens_earned + ?,
            tokens_redeemed = tokens_redeemed + ?
        WHERE id = ?
    ''', (quantity, tokens_earned, redeem, customer_id))
    conn.commit()
    conn.close()
    session['message'] = 'Order submitted successfully!'
    return redirect(url_for('order'))

if __name__ == '__main__':
    app.run(debug=True)
