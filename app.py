from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import sqlite3
import requests
import os
import qrcode
from io import BytesIO, StringIO
import csv
from datetime import datetime
import json
from dotenv import load_dotenv
from functools import wraps
import hashlib
from twilio.rest import Client
import hmac

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-change-this")

# ---------- EMAIL CONFIGURATION ----------
app.config['MAIL_SERVER'] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config['MAIL_PORT'] = int(os.environ.get("MAIL_PORT", 587))
app.config['MAIL_USE_TLS'] = os.environ.get("MAIL_USE_TLS", True)
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@smartpostoffice.com")

mail = Mail(app)

# ---------- LOGIN SETUP ----------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

class AdminUser(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return AdminUser(user_id)

# ---------- DATABASE ----------
def get_db():
    db = sqlite3.connect("parcels.db")
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS parcels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking TEXT UNIQUE NOT NULL,
        parcelStatus TEXT,
        city TEXT,
        phone TEXT,
        email TEXT,
        sender_name TEXT,
        weight TEXT,
        price REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    db.execute("""
    CREATE TABLE IF NOT EXISTS parcel_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking TEXT NOT NULL,
        status TEXT,
        city TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tracking) REFERENCES parcels(tracking)
    )
    """)
    
    db.execute("""
    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking TEXT NOT NULL,
        amount REAL,
        status TEXT DEFAULT 'pending',
        payment_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tracking) REFERENCES parcels(tracking)
    )
    """)

    # lightweight schema evolution for Razorpay fields
    try:
        db.execute("ALTER TABLE payments ADD COLUMN order_id TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE payments ADD COLUMN signature TEXT")
    except Exception:
        pass
    
    db.commit()
    db.close()

init_db()

# ---------- ADMIN AUTHENTICATION ----------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        username = data.get("username")
        password = data.get("password")
        
        # Simple auth - use env vars
        correct_user = os.environ.get("ADMIN_USERNAME", "admin")
        correct_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
        
        if username == correct_user and password == correct_pass:
            admin = AdminUser(username)
            login_user(admin)
            return jsonify({"message": "Login successful"}), 200
        return jsonify({"error": "Invalid credentials"}), 401
    
    return render_template("admin_login.html")

@app.route("/admin_logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('home'))

# ---------- SMS FUNCTION (TWILIO) ----------
def send_sms(phone, message):
    try:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
        
        if not account_sid or not auth_token or not twilio_phone:
            print("⚠️ Twilio credentials not configured")
            return False
        
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Format phone number - ensure it has country code
        if not phone.startswith('+'):
            phone = f"+91{phone}" if len(phone) == 10 else f"+{phone}"
        
        # Send SMS
        msg = client.messages.create(
            body=message,
            from_=twilio_phone,
            to=phone
        )
        
        print(f"✅ SMS sent via Twilio: {msg.sid}")
        return True
    except Exception as e:
        print(f"❌ SMS Error: {e}")
        return False

# ---------- EMAIL FUNCTION ----------
def send_email(recipient, subject, body):
    try:
        msg = Message(subject=subject, recipients=[recipient], html=body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"❌ Email Error: {e}")
        return False

# ---------- QR CODE FUNCTION ----------
def generate_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

def build_public_track_url(tracking: str) -> str:
    """Build a QR-safe tracking URL.

    If PUBLIC_BASE_URL (or APP_BASE_URL) is set, we use it so phone scans work on LAN / production.
    Otherwise we fall back to Flask's _external URL (often http://127.0.0.1:5000 locally).
    """
    base = (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("APP_BASE_URL") or "").strip()
    if base:
        base = base.rstrip('/')
        return f"{base}{url_for('track', code=tracking)}"

    return url_for('track', code=tracking, _external=True)

def build_public_pay_url(tracking: str) -> str:
    """Build a QR-safe payment URL.

    Uses PUBLIC_BASE_URL/APP_BASE_URL when set so phone scans work on LAN / production.
    """
    base = (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("APP_BASE_URL") or "").strip()
    if base:
        base = base.rstrip('/')
        return f"{base}{url_for('pay', tracking=tracking)}"

    return url_for('pay', tracking=tracking, _external=True)

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Validate required fields
        required = ["tracking", "parcelStatus", "city", "phone"]
        for field in required:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({"error": f"{field} is required!"}), 400
        
        db = get_db()
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # If tracking already exists, update the record instead of inserting
            existing = db.execute("SELECT 1 FROM parcels WHERE tracking=?", (data["tracking"],)).fetchone()
            if existing:
                db.execute(
                    """UPDATE parcels SET parcelStatus=?, city=?, phone=?, email=?, sender_name=?, weight=?, price=?, updated_at=? WHERE tracking=?""",
                    (data["parcelStatus"], data["city"], data["phone"], data.get("email"), data.get("sender_name"), data.get("weight"), data.get("price", 0), current_time, data["tracking"]) 
                )
            else:
                db.execute(
                    """INSERT INTO parcels 
                    (tracking, parcelStatus, city, phone, email, sender_name, weight, price, created_at, updated_at) 
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (data["tracking"], data["parcelStatus"], data["city"], data["phone"], 
                     data.get("email"), data.get("sender_name"), data.get("weight"), data.get("price", 0), current_time, current_time)
                )
            db.commit()

            # Add to history (always record a new history row)
            db.execute(
                "INSERT INTO parcel_history (tracking, status, city, timestamp) VALUES (?,?,?,?)",
                (data["tracking"], data["parcelStatus"], data["city"], current_time)
            )
            db.commit()
        except Exception as e:
            db.close()
            return jsonify({"error": str(e)}), 400

        # close DB before sending notifications
        db.close()

        # Send SMS
        try:
            send_sms(data["phone"], f"📦 Parcel {data['tracking']} is {data['parcelStatus']} at {data['city']} on {current_time}")
        except Exception:
            pass

        # Send Email if provided
        if data.get("email"):
            track_link = build_public_track_url(data['tracking'])
            email_body = f"""
            <h3>Parcel Update</h3>
            <p><strong>Tracking:</strong> {data['tracking']}</p>
            <p><strong>Status:</strong> {data['parcelStatus']}</p>
            <p><strong>Location:</strong> {data['city']}</p>
            <p><strong>Time:</strong> {current_time}</p>
            <p>Track your parcel: <a href='{track_link}'>Click here</a></p>
            """
            try:
                send_email(data["email"], f"Parcel {data['tracking']} Update", email_body)
            except Exception:
                pass

        return jsonify({"message": "✅ Parcel updated & notifications sent"}), 200
    
    return render_template("admin.html")

@app.route("/admin_dashboard")
@login_required
def admin_dashboard():
    db = get_db()
    parcels = db.execute("SELECT * FROM parcels ORDER BY created_at DESC").fetchall()
    total = db.execute("SELECT COUNT(*) FROM parcels").fetchone()[0]
    in_transit = db.execute("SELECT COUNT(*) FROM parcels WHERE parcelStatus='In Transit'").fetchone()[0]
    delivered = db.execute("SELECT COUNT(*) FROM parcels WHERE parcelStatus='Delivered'").fetchone()[0]
    db.close()
    
    return render_template("admin_dashboard.html", 
                         parcels=parcels, 
                         total=total, 
                         in_transit=in_transit, 
                         delivered=delivered)

@app.route("/track")
def track():
    code = (request.args.get("code") or request.args.get("tracking") or "").strip()
    return render_template("tracking.html", code=code)

@app.route("/parcel_history/<tracking>")
def parcel_history(tracking):
    db = get_db()
    history = db.execute(
        "SELECT * FROM parcel_history WHERE tracking=? ORDER BY timestamp DESC",
        (tracking,)
    ).fetchall()
    db.close()
    
    return jsonify({"history": [dict(h) for h in history]})

@app.route("/qrcode/<tracking>")
def qrcode_route(tracking):
    """Backward-compatible QR endpoint.

    Historically this endpoint was used for tracking QR. It is now used for payment QR.
    Use /qrcode_track/<tracking> or /qrcode_pay/<tracking> for explicit behavior.
    """
    pay_url = build_public_pay_url(tracking)
    img_io = generate_qr(pay_url)
    return send_file(img_io, mimetype="image/png")

@app.route("/qrcode_track/<tracking>")
def qrcode_track(tracking):
    track_url = build_public_track_url(tracking)
    img_io = generate_qr(track_url)
    return send_file(img_io, mimetype="image/png")

@app.route("/qrcode_pay/<tracking>")
def qrcode_pay(tracking):
    pay_url = build_public_pay_url(tracking)
    img_io = generate_qr(pay_url)
    return send_file(img_io, mimetype="image/png")

@app.route("/qr_link/<purpose>/<tracking>")
@login_required
def qr_link(purpose, tracking):
    purpose = (purpose or "").strip().lower()
    if purpose == "track":
        return jsonify({"url": build_public_track_url(tracking)})
    if purpose == "pay":
        return jsonify({"url": build_public_pay_url(tracking)})
    return jsonify({"error": "purpose must be 'track' or 'pay'"}), 400

@app.route("/qr_link/<tracking>")
@login_required
def qr_link_compat(tracking):
    """Backward-compatible helper for older UI code; defaults to payment."""
    return jsonify({"url": build_public_pay_url(tracking)})

@app.route("/pay")
def pay():
    tracking = (request.args.get("tracking") or "").strip()
    if not tracking:
        return render_template("pay.html", error="Missing tracking number.")

    db = get_db()
    parcel = db.execute("SELECT * FROM parcels WHERE tracking=?", (tracking,)).fetchone()
    if not parcel:
        db.close()
        return render_template("pay.html", error="Tracking number not found.")

    amount = parcel[8] or 0
    if amount <= 0:
        db.close()
        return render_template("pay.html", error="No payable amount configured for this parcel.")

    # Ensure a payment row exists
    db.execute(
        "INSERT INTO payments (tracking, amount, status) VALUES (?,?,?)",
        (tracking, float(amount), "pending"),
    )
    db.commit()
    db.close()

    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        return render_template(
            "pay.html",
            error="Payment gateway not configured (missing RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET).",
        )

    return render_template(
        "pay.html",
        tracking=tracking,
        amount=float(amount),
        key_id=key_id,
        email=parcel[5],
        phone=parcel[4],
    )

@app.route("/create_razorpay_order", methods=["POST"])
def create_razorpay_order():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    tracking = (data.get("tracking") or "").strip()
    if not tracking:
        return jsonify({"error": "tracking is required"}), 400

    db = get_db()
    parcel = db.execute("SELECT * FROM parcels WHERE tracking=?", (tracking,)).fetchone()
    if not parcel:
        db.close()
        return jsonify({"error": "Parcel not found"}), 404

    amount = parcel[8] or 0
    if amount <= 0:
        db.close()
        return jsonify({"error": "No payable amount configured"}), 400

    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        db.close()
        return jsonify({"error": "Payment gateway not configured"}), 400

    order_payload = {
        "amount": int(float(amount) * 100),
        "currency": "INR",
        "receipt": tracking,
        "notes": {"tracking": tracking},
    }

    try:
        r = requests.post(
            "https://api.razorpay.com/v1/orders",
            auth=(key_id, key_secret),
            json=order_payload,
            timeout=15,
        )
        resp = r.json()
    except Exception as e:
        db.close()
        return jsonify({"error": f"Failed to contact Razorpay: {e}"}), 502

    if r.status_code >= 400:
        db.close()
        return jsonify({"error": "Razorpay order creation failed", "details": resp}), 400

    order_id = resp.get("id")
    if not order_id:
        db.close()
        return jsonify({"error": "Razorpay order response missing id", "details": resp}), 400

    db.execute(
        "UPDATE payments SET order_id=?, status='pending' WHERE tracking=?",
        (order_id, tracking),
    )
    db.commit()
    db.close()

    return jsonify(
        {
            "order_id": order_id,
            "amount": int(float(amount) * 100),
            "currency": "INR",
        }
    )

@app.route("/export_csv")
@login_required
def export_csv():
    try:
        db = get_db()
        parcels = db.execute("SELECT * FROM parcels ORDER BY created_at DESC").fetchall()
        db.close()
        
        # Create CSV in memory
        csv_data = "ID,Tracking,Status,City,Phone,Email,Sender,Weight,Price,Created\n"
        
        for p in parcels:
            row = [str(p[i]) if p[i] is not None else "" for i in range(10)]
            csv_data += ",".join(row) + "\n"
        
        # Convert to bytes
        output = BytesIO(csv_data.encode('utf-8'))
        output.seek(0)
        
        return send_file(output, mimetype="text/csv", 
                        download_name=f"parcels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    except Exception as e:
        print(f"CSV Export Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/analytics")
@login_required
def analytics():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM parcels").fetchone()[0]
    in_transit = db.execute("SELECT COUNT(*) FROM parcels WHERE parcelStatus='In Transit'").fetchone()[0]
    delivered = db.execute("SELECT COUNT(*) FROM parcels WHERE parcelStatus='Delivered'").fetchone()[0]
    total_revenue = db.execute("SELECT SUM(price) FROM parcels").fetchone()[0] or 0
    
    daily_stats = db.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count 
        FROM parcels 
        GROUP BY DATE(created_at) 
        ORDER BY date DESC LIMIT 7
    """).fetchall()
    
    db.close()
    
    return render_template("analytics.html",
                         total=total,
                         in_transit=in_transit,
                         delivered=delivered,
                         total_revenue=total_revenue,
                         daily_stats=daily_stats)

@app.route("/getparcel/<tracking>")
def getparcel(tracking):
    db = get_db()
    cur = db.execute(
        "SELECT * FROM parcels WHERE tracking=?",
        (tracking,)
    )
    row = cur.fetchone()
    db.close()
    
    if row:
        return jsonify({
            "parcelStatus": row[2],
            "city": row[3],
            "phone": row[4],
            "email": row[5],
            "sender_name": row[6],
            "weight": row[7],
            "price": row[8],
            "created_at": row[9]
        })
    return jsonify({"error": "Not found"}), 404

@app.route("/update", methods=["POST"])
def update():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Validate required fields
    required = ["tracking", "parcelStatus", "city"]
    for field in required:
        if not data.get(field) or not str(data.get(field)).strip():
            return jsonify({"error": f"{field} is required!"}), 400
    
    db = get_db()
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Update parcel
        db.execute(
            """UPDATE parcels 
               SET parcelStatus=?, city=?, updated_at=? 
               WHERE tracking=?""",
            (data["parcelStatus"], data["city"], current_time, data["tracking"])
        )
        db.commit()
        
        # Add to history
        db.execute(
            "INSERT INTO parcel_history (tracking, status, city, timestamp) VALUES (?,?,?,?)",
            (data["tracking"], data["parcelStatus"], data["city"], current_time)
        )
        db.commit()
        
        # Get parcel for notifications
        parcel = db.execute("SELECT phone, email FROM parcels WHERE tracking=?", 
                           (data["tracking"],)).fetchone()
        db.close()
        
        if parcel:
            # Send SMS
            send_sms(parcel[0], f"📦 Parcel {data['tracking']} is {data['parcelStatus']} at {data['city']} on {current_time}")
            
            # Send Email
            if parcel[1]:
                email_body = f"""
                <h3>Parcel Status Update</h3>
                <p><strong>Tracking:</strong> {data['tracking']}</p>
                <p><strong>Status:</strong> {data['parcelStatus']}</p>
                <p><strong>Location:</strong> {data['city']}</p>
                <p><strong>Time:</strong> {current_time}</p>
                """
                send_email(parcel[1], f"Parcel {data['tracking']} Updated", email_body)
        
        return jsonify({"message": "✅ Parcel updated & notifications sent"}), 200
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400

@app.route("/delete_parcel/<tracking>", methods=["POST"])
@login_required
def delete_parcel(tracking):
    db = get_db()
    db.execute("DELETE FROM parcel_history WHERE tracking=?", (tracking,))
    db.execute("DELETE FROM parcels WHERE tracking=?", (tracking,))
    db.commit()
    db.close()
    
    return jsonify({"message": "✅ Parcel deleted"}), 200

@app.route("/initiate_payment", methods=["POST"])
def initiate_payment():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    tracking = data.get("tracking")
    amount = data.get("amount", 0)
    
    db = get_db()
    parcel = db.execute("SELECT * FROM parcels WHERE tracking=?", (tracking,)).fetchone()
    
    if not parcel:
        return jsonify({"error": "Parcel not found"}), 404
    
    # Create payment record
    db.execute("INSERT INTO payments (tracking, amount, status) VALUES (?,?,?)",
              (tracking, amount, "pending"))
    db.commit()
    db.close()
    
    # Use Razorpay if configured
    razorpay_key = os.environ.get("RAZORPAY_KEY_ID")
    razorpay_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    
    if razorpay_key and razorpay_secret:
        return jsonify({
            "key": razorpay_key,
            "amount": int(amount * 100),  # Convert to paise
            "tracking": tracking,
            "email": parcel[5],
            "phone": parcel[4]
        })
    
    return jsonify({"error": "Payment gateway not configured"}), 400

@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    tracking = (data.get("tracking") or "").strip()
    payment_id = (data.get("razorpay_payment_id") or data.get("payment_id") or "").strip()
    order_id = (data.get("razorpay_order_id") or "").strip()
    signature = (data.get("razorpay_signature") or "").strip()

    if not tracking or not payment_id or not order_id or not signature:
        return jsonify({"error": "tracking, razorpay_payment_id, razorpay_order_id, razorpay_signature are required"}), 400

    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_secret:
        return jsonify({"error": "Payment gateway not configured"}), 400

    expected = hmac.new(
        key_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return jsonify({"error": "Invalid payment signature"}), 400

    db = get_db()
    db.execute(
        "UPDATE payments SET status=?, payment_id=?, order_id=?, signature=? WHERE tracking=?",
        ("success", payment_id, order_id, signature, tracking),
    )
    db.commit()
    db.close()

    return jsonify({"message": "✅ Payment verified"}), 200

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    app.run(host=host, port=port, debug=True)

