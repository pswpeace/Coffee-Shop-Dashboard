import sqlite3
from flask import Flask, render_template, jsonify, request, g

app = Flask(__name__, template_folder='.', static_folder='.')

DATABASE = 'coffee_shop.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row 
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dashboard_data')
def dashboard_data():
    db = get_db()
    
    selected_shop = request.args.get('shop', 'Overall')
    selected_month = request.args.get('month', 'Overall')

    # --- FILTERS ---
    # Filter A: Time Only (For Charts)
    time_conditions = []
    time_params = []
    if selected_month != 'Overall':
        # Handles dates like '2023-01-01' or '01/01/2023' roughly
        time_conditions.append("CAST(strftime('%m', transaction_date) AS INTEGER) = ?")
        time_params.append(selected_month)
    time_where = "WHERE " + " AND ".join(time_conditions) if time_conditions else ""

    # Filter B: Time + Shop (For Table & Metrics)
    strict_conditions = time_conditions.copy()
    strict_params = time_params.copy()
    if selected_shop != 'Overall':
        strict_conditions.append("store_location = ?")
        strict_params.append(selected_shop)
    strict_where = "WHERE " + " AND ".join(strict_conditions) if strict_conditions else ""

    # --- 1. PIE CHART DATA (Safe Handling) ---
    sql_pie = f"""
        SELECT store_location, 
               SUM(unit_price * transaction_qty) as total_sales, 
               SUM(transaction_qty) as total_qty
        FROM transactions
        {time_where}
        GROUP BY store_location
    """
    pie_rows = db.execute(sql_pie, time_params).fetchall()
    
    # SAFETY FIX: Convert None to 0
    pie_labels = []
    pie_sales = []
    pie_qty = []
    
    for row in pie_rows:
        pie_labels.append(row['store_location'] if row['store_location'] else 'Unknown')
        pie_sales.append(row['total_sales'] if row['total_sales'] is not None else 0)
        pie_qty.append(row['total_qty'] if row['total_qty'] is not None else 0)

    # --- 2. LINE CHART DATA ---
    sql_line = f"""
        SELECT transaction_date, store_location, SUM(unit_price * transaction_qty) as daily_sales
        FROM transactions
        {time_where}
        GROUP BY transaction_date, store_location
        ORDER BY transaction_date
    """
    line_rows = db.execute(sql_line, time_params).fetchall()
    
    all_dates = sorted(list(set(r['transaction_date'] for r in line_rows)))
    store_names = ['Astoria', 'Lower Manhattan', "Hell's Kitchen"]
    store_data_map = {name: [0] * len(all_dates) for name in store_names}
    
    for row in line_rows:
        if row['transaction_date'] in all_dates:
            d_idx = all_dates.index(row['transaction_date'])
            s_name = row['store_location']
            val = row['daily_sales'] if row['daily_sales'] is not None else 0
            if s_name in store_data_map:
                store_data_map[s_name][d_idx] = val

    # --- 3. TABLE DATA ---
    sql_table = f"""
        SELECT product_category, 
               SUM(transaction_qty) as total_qty,
               AVG(unit_price) as avg_price,
               SUM(unit_price * transaction_qty) as total_sales
        FROM transactions
        {strict_where}
        GROUP BY product_category
        ORDER BY total_sales DESC
    """
    table_rows = db.execute(sql_table, strict_params).fetchall()

    grand_total_sales = sum((r['total_sales'] or 0) for r in table_rows) or 1
    grand_total_qty = sum((r['total_qty'] or 0) for r in table_rows) or 1

    table_data = []
    for row in table_rows:
        sales = row['total_sales'] or 0
        qty = row['total_qty'] or 0
        table_data.append({
            'category': row['product_category'] or 'Uncategorized',
            'sales': sales,
            'percent_sales': (sales / grand_total_sales) * 100,
            'avg_price': row['avg_price'] or 0,
            'qty': qty,
            'percent_qty': (qty / grand_total_qty) * 100
        })

    # --- 4. METRICS ---
    sql_total = f"SELECT SUM(unit_price * transaction_qty) as rev FROM transactions {strict_where}"
    total_rev = db.execute(sql_total, strict_params).fetchone()['rev']
    total_rev = total_rev if total_rev is not None else 0

    return jsonify({
        'metrics': {'total_revenue': total_rev},
        'pie_data': {
            'labels': pie_labels,
            'sales': pie_sales,
            'qty': pie_qty
        },
        'line_data': {
            'dates': all_dates,
            'datasets': [
                {'label': s, 'data': d, 'borderColor': c} 
                for s, d, c in zip(store_names, store_data_map.values(), ['#FF6384', '#36A2EB', '#FFCE56'])
            ]
        },
        'table_data': table_data
    })

if __name__ == '__main__':
    app.run(debug=True)