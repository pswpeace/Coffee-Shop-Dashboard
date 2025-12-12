import sqlite3
from flask import Flask, render_template, jsonify, g

# Initialize Flask
# template_folder='.' tells Flask the HTML is in the current directory
# static_folder='.' tells Flask the JS/CSS files are also here
app = Flask(__name__, template_folder='.', static_folder='.')

DATABASE = 'coffee_shop.db'

def get_db():
    """Connect to the database."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # This allows us to access columns by name (row['date'])
        db.row_factory = sqlite3.Row 
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection when the request is done."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- ROUTES ---

@app.route('/')
def index():
    """Serves the index.html page."""
    return render_template('index.html')

@app.route('/api/sales-data')
def get_sales_data():
    """
    API Endpoint: Queries the database and returns JSON data for the dashboard.
    NOTE: You will need to change 'transactions' and column names 
    to match your actual CSV/Database schema.
    """
    try:
        cur = get_db().cursor()
        
        # EXAMPLE QUERY: Get total sales by product category
        # Change 'category' and 'total_amount' to match your DB columns
        query = "SELECT category, SUM(total_amount) as total FROM transactions GROUP BY category"
        
        cur.execute(query)
        rows = cur.fetchall()
        
        # Convert database rows to a list of dictionaries
        data = [dict(row) for row in rows]
        return jsonify(data)
    
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)