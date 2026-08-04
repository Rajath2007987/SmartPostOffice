import sqlite3
from datetime import datetime, timedelta
import requests
import time

DB = 'parcels.db'
TRACK = 'TEST12345'

# Insert parcel and history
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Upsert parcel
now = datetime.now()
created = now - timedelta(days=1)
cur.execute("DELETE FROM parcels WHERE tracking=?", (TRACK,))
cur.execute("DELETE FROM parcel_history WHERE tracking=?", (TRACK,))
conn.commit()

cur.execute(
    "INSERT INTO parcels (tracking, parcelStatus, city, phone, email, sender_name, weight, price, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
    (TRACK, 'In Transit', 'Mumbai', '9999999999', 'test@example.com', 'Dev Sender', '1kg', 50.0, created.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S'))
)
conn.commit()

# Add history entries (chronological older -> newer)
entries = [
    ('Picked Up', 'Pune', created + timedelta(hours=1)),
    ('In Transit', 'Lonavala', created + timedelta(hours=6)),
    ('Arrived at Hub', 'Mumbai', created + timedelta(hours=18)),
    ('Out for Delivery', 'Mumbai', now - timedelta(hours=1)),
    ('Delivered', 'Mumbai', now)
]
for status, city, ts in entries:
    cur.execute("INSERT INTO parcel_history (tracking, status, city, timestamp) VALUES (?,?,?,?)", (TRACK, status, city, ts.strftime('%Y-%m-%d %H:%M:%S')))

conn.commit()
conn.close()

# Give server a moment
time.sleep(1)

# Fetch via running Flask app
url = f'http://127.0.0.1:5000/parcel_history/{TRACK}'
print('Requesting', url)
try:
    r = requests.get(url, timeout=5)
    print('Status code:', r.status_code)
    print('Response JSON:')
    print(r.json())
except Exception as e:
    print('Error fetching:', e)
