import requests

BASE = "http://127.0.0.1:5000"

endpoints = [
    ("GET", "/"),
    ("GET", "/track"),
    ("GET", "/qrcode/test"),
    ("GET", "/getparcel/UNKNOWN"),
    ("POST", "/admin_login", {"username":"admin","password":"admin123"}),
]

for entry in endpoints:
    method = entry[0]
    path = entry[1]
    body = entry[2] if len(entry) > 2 else None
    url = BASE + path
    try:
        if method == "GET":
            r = requests.get(url, timeout=5)
        else:
            r = requests.post(url, json=body, timeout=5)

        print(f"{method} {path} -> {r.status_code}")
        text = r.text
        snippet = text[:400].replace('\n', ' ')
        print("Body snippet:", snippet)
    except Exception as e:
        print(f"{method} {path} -> ERROR: {e}")
    print("-"*60)
