from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, pandas as pd
from functools import wraps
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'
DATABASE = 'loyalty_card.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(role=None):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'username' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (request.form['username'],)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], request.form['password']):
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('admin' if user['role'] == 'admin' else 'order'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required(role='admin')
def admin():
    conn = get_db()
    users = conn.execute('SELECT * FROM users').fetchall()
    customers = conn.execute('SELECT * FROM customers').fetchall()
    drinks = conn.execute('SELECT * FROM drinks').fetchall()
    conn.close()
    return render_template('admin.html', users=users, customers=customers, drinks=drinks)

@app.route('/add_user', methods=['POST'])
@login_required(role='admin')
def add_user():
    conn = get_db()
    conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (
        request.form['username'],
        generate_password_hash(request.form['password']),
        request.form['role']
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete_user', methods=['POST'])
@login_required(role='admin')
def delete_user():
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?', (request.form['user_id'],))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/add_customer', methods=['POST'])
@login_required(role='admin')
def add_customer():
    conn = get_db()
    conn.execute('INSERT INTO customers (name, unique_id, total_orders, tokens_earned, tokens_redeemed) VALUES (?, ?, 0, 0, 0)', (
        request.form['name'],
        request.form['unique_id']
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete_customer', methods=['POST'])
@login_required(role='admin')
def delete_customer():
    conn = get_db()
    conn.execute('DELETE FROM customers WHERE id = ?', (request.form['customer_id'],))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/add_drink', methods=['POST'])
@login_required(role='admin')
def add_drink():
    conn = get_db()
    conn.execute('INSERT INTO drinks (name) VALUES (?)', (request.form['drink_name'],))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete_drink', methods=['POST'])
@login_required(role='admin')
def delete_drink():
    conn = get_db()
    conn.execute('DELETE FROM drinks WHERE id = ?', (request.form['drink_id'],))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/order')
@login_required(role='barista')
def order():
    conn = get_db()
    drinks = conn.execute('SELECT * FROM drinks').fetchall()
    conn.close()
    return render_template('order.html', drinks=drinks)

@app.route('/get_customers_by_uid', methods=['POST'])
def get_customers_by_uid():
    uid = request.json.get('uid')
    conn = get_db()
    customers = conn.execute('SELECT id, name FROM customers WHERE unique_id = ?', (uid,)).fetchall()
    conn.close()
    return jsonify([{'id': c['id'], 'name': c['name']} for c in customers])

@app.route('/get_customer_summary', methods=['POST'])
def get_customer_summary():
    customer_id = request.json.get('customer_id')
    conn = get_db()
    c = conn.execute('SELECT total_orders, tokens_earned, tokens_redeemed FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()
    balance = c['tokens_earned'] - c['tokens_redeemed']
    return jsonify({'total_orders': c['total_orders'], 'tokens_earned': c['tokens_earned'], 'tokens_redeemed': c['tokens_redeemed'], 'balance': balance})

@app.route('/submit_order', methods=['POST'])
@login_required(role='barista')
def submit_order():
    customer_id = int(request.form['customer_id'])
    drink = request.form['drink']
    quantity = int(request.form['quantity'])
    redeem = int(request.form.get('redeem', 0))
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    tokens_earned = customer['tokens_earned']
    tokens_redeemed = customer['tokens_redeemed']
    balance = tokens_earned - tokens_redeemed
    if redeem > balance:
        redeem = 0
    total_orders = customer['total_orders'] + quantity
    earned = quantity // 9
    conn.execute('UPDATE customers SET total_orders = ?, tokens_earned = ?, tokens_redeemed = ? WHERE id = ?', (
        total_orders,
        tokens_earned + earned,
        tokens_redeemed + redeem,
        customer_id
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('order'))

if __name__ == '__main__':
    app.run(debug=True)
