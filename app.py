from flask import Flask, render_template, request, redirect,send_file
import sqlite3
import io
from datetime import datetime, timedelta
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY,
        item TEXT,
        amount REAL,
        payment_mode TEXT,
        sale_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY,
        amount REAL,
        reason TEXT,
        expense_date TEXT
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add-sale', methods=['POST'])
def add_sale():
    item = request.form['item']
    amount = float(request.form['amount'])
    mode = request.form['mode']
    today = date.today().isoformat()

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("INSERT INTO sales (item, amount, payment_mode, sale_date) VALUES (?, ?, ?, ?)",
              (item, amount, mode, today))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/add-expense', methods=['POST'])
def add_expense():
    amount = float(request.form['expense_amount'])
    reason = request.form['reason']
    today = date.today().isoformat()

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("INSERT INTO expenses (amount, reason, expense_date) VALUES (?, ?, ?)",
              (amount, reason, today))
    conn.commit()
    conn.close()
    return redirect('/')

from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import date

# ... existing routes above ...

@app.route('/summary', methods=['GET', 'POST'])
def summary():
    selected_date = request.form.get('selected_date') if request.method == 'POST' else date.today().isoformat()

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    c.execute("SELECT SUM(amount) FROM sales WHERE sale_date = ? AND payment_mode = 'Cash'", (selected_date,))
    cash_total = c.fetchone()[0] or 0.0

    c.execute("SELECT SUM(amount) FROM sales WHERE sale_date = ? AND payment_mode = 'UPI'", (selected_date,))
    upi_total = c.fetchone()[0] or 0.0

    c.execute("SELECT SUM(amount) FROM expenses WHERE expense_date = ?", (selected_date,))
    expense_total = c.fetchone()[0] or 0.0

    remaining = (cash_total + upi_total) - expense_total

    conn.close()

    return render_template('summary.html',
                           cash_total=cash_total,
                           upi_total=upi_total,
                           expense_total=expense_total,
                           remaining=remaining,
                           selected_date=selected_date)



@app.route('/report', methods=['GET', 'POST'])
def report():
    view_type = request.form.get('view_type', 'week')  # default is week
    today = date.today()

    if view_type == 'month':
        start_date = today.replace(day=1)
    else:  # week
        start_date = today - timedelta(days=today.weekday())  # Monday

    end_date = today

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    c.execute("""
        SELECT SUM(amount) FROM sales 
        WHERE sale_date BETWEEN ? AND ? AND payment_mode = 'Cash'
    """, (start_date, end_date))
    cash_total = c.fetchone()[0] or 0.0

    c.execute("""
        SELECT SUM(amount) FROM sales 
        WHERE sale_date BETWEEN ? AND ? AND payment_mode = 'UPI'
    """, (start_date, end_date))
    upi_total = c.fetchone()[0] or 0.0

    c.execute("""
        SELECT SUM(amount) FROM expenses 
        WHERE expense_date BETWEEN ? AND ?
    """, (start_date, end_date))
    expense_total = c.fetchone()[0] or 0.0

    remaining = (cash_total + upi_total) - expense_total

    return render_template('report.html',
                           view_type=view_type,
                           start_date=start_date,
                           end_date=end_date,
                           cash_total=cash_total,
                           upi_total=upi_total,
                           expense_total=expense_total,
                           remaining=remaining)


@app.route('/export_report', methods=['POST'])
def export_report():
    view_type = request.form.get('view_type', 'week')
    today = date.today()

    if view_type == 'month':
        start_date = today.replace(day=1)
    else:  # week
        start_date = today - timedelta(days=today.weekday())

    end_date = today

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    c.execute("""
        SELECT SUM(amount) FROM sales 
        WHERE sale_date BETWEEN ? AND ? AND payment_mode = 'Cash'
    """, (start_date, end_date))
    cash_total = c.fetchone()[0] or 0.0

    c.execute("""
        SELECT SUM(amount) FROM sales 
        WHERE sale_date BETWEEN ? AND ? AND payment_mode = 'UPI'
    """, (start_date, end_date))
    upi_total = c.fetchone()[0] or 0.0

    c.execute("""
        SELECT SUM(amount) FROM expenses 
        WHERE expense_date BETWEEN ? AND ?
    """, (start_date, end_date))
    expense_total = c.fetchone()[0] or 0.0

    remaining = (cash_total + upi_total) - expense_total

    conn.close()

    export_type = request.form.get('export_type')

    # Export Excel
    if export_type == 'excel':
        df = pd.DataFrame({
            'Category': ['Cash Sales', 'UPI Sales', 'Expenses', 'Remaining Profit'],
            'Amount (₹)': [cash_total, upi_total, expense_total, remaining]
        })

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
        output.seek(0)

        return send_file(output, download_name=f"{view_type}_report.xlsx",
                         as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Export PDF
    elif export_type == 'pdf':
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, f"{view_type.capitalize()} Report")
        p.setFont("Helvetica", 12)
        p.drawString(50, height - 80, f"Period: {start_date} to {end_date}")

        y = height - 120
        line_height = 20

        p.drawString(50, y, f"Cash Sales: ₹{cash_total:.2f}")
        y -= line_height
        p.drawString(50, y, f"UPI Sales: ₹{upi_total:.2f}")
        y -= line_height
        p.drawString(50, y, f"Expenses: ₹{expense_total:.2f}")
        y -= line_height
        p.drawString(50, y, f"Remaining Profit: ₹{remaining:.2f}")

        p.showPage()
        p.save()
        buffer.seek(0)

        return send_file(buffer, download_name=f"{view_type}_report.pdf",
                         as_attachment=True, mimetype='application/pdf')

    else:
        return "Invalid export type", 400


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
