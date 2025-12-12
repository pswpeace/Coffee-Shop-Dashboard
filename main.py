import sqlite3
from flask import Flask, render_template, jsonify, request, g

app = Flask(__name__, template_folder='.', static_folder='.')

DATABASE = 'coffee_shop.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Use sqlite3.Row for dictionary-like access to rows
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
    # Filter A: Time Only (For Pie/Line Charts when not overall shop)
    time_conditions = []
    time_params = []
    if selected_month != 'Overall':
        # FIX: Use REPLACE to format date for SQLite strftime
        time_conditions.append("CAST(strftime('%m', REPLACE(transaction_date, '/', '-')) AS INTEGER) = ?")
        time_params.append(selected_month)
    time_where = "WHERE " + " AND ".join(time_conditions) if time_conditions else ""

    # Filter B: Time + Shop (For Table & Metrics)
    strict_conditions = time_conditions.copy()
    strict_params = time_params.copy()
    if selected_shop != 'Overall':
        strict_conditions.append("store_location = ?")
        strict_params.append(selected_shop)
    strict_where = "WHERE " + " AND ".join(strict_conditions) if strict_conditions else ""

    # --- 1. PIE / HEATMAP DATA ---
    
    heatmap_data = None
    if selected_shop != 'Overall':
        # Condition: Specific shop selected -> get data for heatmap (Transaction Count)
        
        # FIX: Use REPLACE to format date for SQLite strftime
        sql_heatmap = f"""
            SELECT CAST(strftime('%w', REPLACE(transaction_date, '/', '-')) AS INTEGER) AS day_of_week, 
                   CAST(strftime('%H', transaction_time) AS INTEGER) AS hour_of_day,
                   COUNT(transaction_id) AS total_transactions
            FROM transactions
            {strict_where}
            GROUP BY day_of_week, hour_of_day
            HAVING hour_of_day >= 6 AND hour_of_day <= 20 -- Assuming 6 AM to 8 PM operating hours
            ORDER BY day_of_week, hour_of_day
        """
        heatmap_rows = db.execute(sql_heatmap, strict_params).fetchall()
        
        # Data structure for the heatmap frontend
        transaction_matrix = {}
        max_transactions = 0
        
        for row in heatmap_rows:
            key = f"{row['day_of_week']}:{row['hour_of_day']}"
            transactions = row['total_transactions'] if row['total_transactions'] is not None else 0
            
            transaction_matrix[key] = transactions
            max_transactions = max(max_transactions, transactions)

        heatmap_data = {
            'transaction_matrix': transaction_matrix,
            'max_transactions': max_transactions
        }
        
        pie_labels = []
        pie_sales = []
        pie_qty = []
        
    else:
        # Condition: Overall shop selected -> use original pie chart logic
        sql_pie = f"""
            SELECT store_location, 
                   SUM(unit_price * transaction_qty) as total_sales, 
                   SUM(transaction_qty) as total_qty
            FROM transactions
            {time_where}
            GROUP BY store_location
        """
        pie_rows = db.execute(sql_pie, time_params).fetchall()
        
        pie_labels = []
        pie_sales = []
        pie_qty = []
        
        for row in pie_rows:
            pie_labels.append(row['store_location'] if row['store_location'] else 'Unknown')
            pie_sales.append(row['total_sales'] if row['total_sales'] is not None else 0)
            pie_qty.append(row['total_qty'] if row['total_qty'] is not None else 0)


    # --- 2. LINE CHART DATA ---
    store_names = ['Astoria', 'Lower Manhattan', "Hell's Kitchen"]
    
    if selected_month == 'Overall':
        # Use monthly aggregation 
        # FIX: Use REPLACE to format date for SQLite strftime
        sql_line = f"""
            SELECT CAST(strftime('%m', REPLACE(transaction_date, '/', '-')) AS INTEGER) AS month, 
                   store_location, 
                   SUM(unit_price * transaction_qty) as monthly_sales,
                   SUM(transaction_qty) as monthly_qty
            FROM transactions
            GROUP BY month, store_location
            ORDER BY month
        """
        line_rows = db.execute(sql_line).fetchall()
        
        all_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        
        store_sales_map = {name: [0] * 6 for name in store_names}
        store_qty_map = {name: [0] * 6 for name in store_names}
        
        for row in line_rows:
            month_idx = row['month'] - 1 
            s_name = row['store_location']
            monthly_sales = row['monthly_sales'] if row['monthly_sales'] is not None else 0
            monthly_qty = row['monthly_qty'] if row['monthly_qty'] is not None else 0
            
            if 0 <= month_idx < 6 and s_name in store_names:
                store_sales_map[s_name][month_idx] = monthly_sales
                store_qty_map[s_name][month_idx] = monthly_qty
        
    else:
        # Use weekly aggregation for specific month (Weeks 1-4)
        # FIX: Use REPLACE to format date for SQLite strftime
        sql_line = f"""
            SELECT CASE
                       WHEN CAST(strftime('%d', REPLACE(transaction_date, '/', '-')) AS INTEGER) BETWEEN 1 AND 7 THEN 1
                       WHEN CAST(strftime('%d', REPLACE(transaction_date, '/', '-')) AS INTEGER) BETWEEN 8 AND 14 THEN 2
                       WHEN CAST(strftime('%d', REPLACE(transaction_date, '/', '-')) AS INTEGER) BETWEEN 15 AND 21 THEN 3
                       ELSE 4 -- Days 22 through 31 are all grouped into Week 4
                   END AS week_of_month,
                   store_location, 
                   SUM(unit_price * transaction_qty) as weekly_sales,
                   SUM(transaction_qty) as weekly_qty
            FROM transactions
            {time_where}
            GROUP BY week_of_month, store_location
            ORDER BY week_of_month
        """
        line_rows = db.execute(sql_line, time_params).fetchall()
        
        all_labels = ["Week 1", "Week 2", "Week 3", "Week 4"]
        
        store_sales_map = {name: [0] * 4 for name in store_names}
        store_qty_map = {name: [0] * 4 for name in store_names}
        
        for row in line_rows:
            week_idx = row['week_of_month'] - 1 # Week 1 is index 0
            s_name = row['store_location']
            weekly_sales = row['weekly_sales'] if row['weekly_sales'] is not None else 0
            weekly_qty = row['weekly_qty'] if row['weekly_qty'] is not None else 0
            
            if 0 <= week_idx < 4 and s_name in store_sales_map: 
                store_sales_map[s_name][week_idx] = weekly_sales
                store_qty_map[s_name][week_idx] = weekly_qty 

    # Prepare datasets for BOTH Sales and Quantity line charts
    line_datasets_sales = [
        {'label': s, 'data': d, 'borderColor': c} 
        for s, d, c in zip(store_names, store_sales_map.values(), ['#FF6384', '#36A2EB', '#FFCE56'])
    ]
    
    line_datasets_qty = [
        {'label': s, 'data': d, 'borderColor': c} 
        for s, d, c in zip(store_names, store_qty_map.values(), ['#27ae60', '#9b59b6', '#f39c12']) 
    ]

    # --- 3. TABLE DATA (No Change) ---
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

    # --- 4. METRICS (No Change) ---
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
            'dates': all_labels, 
            'sales_datasets': line_datasets_sales, 
            'qty_datasets': line_datasets_qty      
        },
        'heatmap_data': heatmap_data, 
        'table_data': table_data
    })

if __name__ == '__main__':
    app.run(debug=True)