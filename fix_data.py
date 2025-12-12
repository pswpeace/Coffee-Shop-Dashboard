import sqlite3
import pandas as pd

# 1. Connect to the database
db_name = 'coffee_shop.db'
conn = sqlite3.connect(db_name)

print("Reading data...")
# 2. Read all tables
df_trans = pd.read_sql("SELECT * FROM transactions", conn)
df_stores = pd.read_sql("SELECT * FROM stores", conn)
df_prods = pd.read_sql("SELECT * FROM products", conn)
df_types = pd.read_sql("SELECT * FROM product_types", conn)

# 3. Merge them into one single 'flat' table
#    Join Transactions -> Stores
df_merged = df_trans.merge(df_stores, on='store_id', how='left')
#    Join Transactions -> Products
df_merged = df_merged.merge(df_prods, on='product_id', how='left')
#    Join Products -> Product Types (to get 'product_category')
df_merged = df_merged.merge(df_types, on='product_type_id', how='left')

# 4. Fix the Date Format
#    Converts '1/1/2023' to '2023-01-01' so SQL date functions work
print("Fixing date formats...")
# Old line (delete this):
# df_merged['transaction_date'] = pd.to_datetime(df_merged['transaction_date']).dt.strftime('%Y-%m-%d')

# New line (paste this instead):
df_merged['transaction_date'] = pd.to_datetime(df_merged['transaction_date'], dayfirst=True).dt.strftime('%Y-%m-%d')
# 5. Save back to database
#    We overwrite the 'transactions' table with this new combined version
print("Updating database...")
df_merged.to_sql('transactions', conn, if_exists='replace', index=False)

conn.close()
print("Success! Your database is now compatible with your dashboard code.")