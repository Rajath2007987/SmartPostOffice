# Smart Post Office

This is a Flask-based parcel tracking and admin app.

Quick start (local):

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
python app.py
```

Run with Gunicorn (production):

```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

Build and run Docker image:

```bash
docker build -t smart-post-office .
docker run -p 8000:8000 --env-file .env smart-post-office
```

Notes:
- Configure email and other secrets in a `.env` file.
- The app creates a local SQLite `parcels.db` on first run.

QR code notes (phone scanning):
- If you scan a QR code on your phone while the server is running on your laptop, `127.0.0.1` / `localhost` links will NOT work.
- Set `PUBLIC_BASE_URL` (example: `http://<your-laptop-lan-ip>:5000`) so the QR encodes a phone-reachable link.
- If you want your phone to reach the laptop server over Wi-Fi, set `FLASK_HOST=0.0.0.0` before running `python app.py`.
# admin
