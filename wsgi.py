from app import app

# Expose the Flask `app` for WSGI servers (gunicorn)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
